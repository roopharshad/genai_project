"""End-to-end test of every Document AI feature through the running website API.

Usage: python scripts/feature_test.py [document image]
Uploads the document, runs restoration (damage detection + model selection), then tests
damage analysis, OCR read/save, quality evaluation, Gemini chat and LaMa reconstruction.
"""
import json
import sys
import time

import httpx

f = sys.argv[1] if len(sys.argv) > 1 else "samples/faded_document.jpg"
c = httpx.Client(base_url="http://127.0.0.1:8000", timeout=600)
tok = c.post("/api/v1/auth/login", json={"email": "demo@docrestore.ai", "password": "docrestore123"}).json()
c.headers["Authorization"] = "Bearer " + tok["access_token"]
results = {}


def check(name, ok, detail=""):
    results[name] = "PASS" if ok else "FAIL"
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}", flush=True)


st = c.get("/api/v1/document-ai/status").json()
check("status endpoint", "gemini_configured" in st, json.dumps(st))

proj = c.get("/api/v1/projects/").json()[0]["id"]
mime = "image/png" if f.endswith(".png") else "image/jpeg"
a = c.post("/api/v1/assets/upload", data={"project_id": proj}, files={"file": (f.split("/")[-1], open(f, "rb"), mime)}).json()
aid = a["id"]

t = time.time()
r = c.get(f"/api/v1/document-ai/{aid}/damage")
d = r.json()
check("damage detection", r.status_code == 200 and "damages" in d,
      f"{time.time() - t:.1f}s score={d.get('damage_score')} "
      + ", ".join(f"{k}={v['level']}" for k, v in d.get("damages", {}).items()))
check("damage map image", c.get(d.get("damage_map_url", "/x")).status_code == 200, d.get("damage_map_url", ""))
check("model selection plan", bool(d.get("plan")), " | ".join(f"{p['stage']}={'run' if p['run'] else 'skip'}" for p in d.get("plan", [])))

t = time.time()
j = c.post("/api/v1/restorations/jobs", json={"project_id": proj, "asset_id": aid, "model_id": "recommended", "config_params": {}}).json()
last = ""
while j["status"] not in ("completed", "failed"):
    time.sleep(3)
    try:
        j = c.get(f"/api/v1/restorations/jobs/{j['id']}").json()
    except httpx.HTTPError as exc:
        print("    (poll retry:", type(exc).__name__, ")", flush=True)
        continue
    if j["stage"] != last:
        print(f"    {j['progress']}% {j['stage']}", flush=True)
        last = j["stage"]
dt = time.time() - t
check("restoration job", j["status"] == "completed", f"{dt:.0f}s {j.get('error_message') or ''}")
check("enhancement step ran", "nhancement" in j["stage"], j["stage"])
print("    enhancement applied:", "enhancement completed" in j["stage"])

cmp_ = c.get(f"/api/v1/comparisons/{aid}").json()
rv = cmp_["restored_version"]
op = rv["config_summary"]["operational"]
print("    steps:\n      " + "\n      ".join(op["steps"]))
tr = op.get("text_report", {})
print("    timings:", tr.get("timings"), "chosen:", tr.get("chosen_stage"))
check("restored image served", c.get(rv["url"]).status_code == 200, rv["url"])

t = time.time()
q = c.get(f"/api/v1/document-ai/{aid}/quality")
qd = q.json()
check("quality evaluation", q.status_code == 200 and "quality_score" in qd,
      f"{time.time() - t:.1f}s score={qd.get('quality_score')} damage {qd.get('damage_score_before')}->{qd.get('damage_score_after')} "
      f"strokes={qd.get('stroke_preservation')} psnr={qd.get('psnr_vs_original')} ssim={qd.get('ssim_vs_original')} ocr={qd.get('ocr')}")

t = time.time()
o = c.get(f"/api/v1/document-ai/{aid}/ocr")
od = o.json()
check("OCR extraction", o.status_code == 200 and "lines" in od,
      f"{time.time() - t:.1f}s {len(od.get('lines', []))} lines, {od.get('unreadable_lines')} unreadable, conf {od.get('mean_confidence')}, source {od.get('source')}")
lines = [l["text"] for l in od.get("lines", [])]
if lines:
    edited = lines[:]
    edited[0] = edited[0] + " "  # whitespace-only edit keeps the text correct
    s = c.put(f"/api/v1/document-ai/{aid}/ocr", json={"lines": edited, "version_id": od["version_id"], "approve": True})
    check("OCR save/approve", s.status_code == 200 and s.json()["status"] == "approved", json.dumps(s.json()))
    again = c.get(f"/api/v1/document-ai/{aid}/ocr").json()
    check("OCR saved text reloads", again.get("status") == "approved" and again.get("edited_text"), "")
    ex = c.get(f"/api/v1/document-ai/{aid}/ocr/export")
    check("OCR text export", ex.status_code == 200 and len(ex.text) > 0, f"{len(ex.text)} chars")
    q2 = c.get(f"/api/v1/document-ai/{aid}/quality").json()
    check("OCR accuracy vs approved text", (q2.get("ocr") or {}).get("kind") == "accuracy_vs_approved_text", json.dumps(q2.get("ocr")))

t = time.time()
ch = c.post(f"/api/v1/document-ai/{aid}/chat", json={"question": "Summarise this document in two sentences.", "history": []})
cd = ch.json()
check("Gemini chat", ch.status_code == 200 and bool(cd.get("answer")),
      f"{time.time() - t:.1f}s model={cd.get('model')} answer={str(cd.get('answer') or cd.get('detail'))[:300]!r}")
if ch.status_code == 200:
    ch2 = c.post(f"/api/v1/document-ai/{aid}/chat", json={"question": "What year is mentioned?",
                                                            "history": [{"role": "user", "content": "Summarise this document in two sentences."},
                                                                        {"role": "assistant", "content": cd["answer"]}]})
    check("Gemini follow-up with history", ch2.status_code == 200, str(ch2.json().get("answer") or ch2.json().get("detail"))[:200])

t = time.time()
rc = c.post(f"/api/v1/document-ai/{aid}/reconstruct", json={"include_text_areas": True})
rd = rc.json()
ok = rc.status_code == 200 and rd.get("status") in ("ok", "nothing_to_reconstruct")
check("LaMa reconstruction", ok, f"{time.time() - t:.1f}s {rd.get('status')} {rd.get('ai_generated_pct', '')}% "
      f"regions={len(rd.get('regions', []))} {rd.get('message', rd.get('detail', ''))}")
if rd.get("status") == "ok":
    check("AI regions marked image", c.get(rd["marked_url"]).status_code == 200, rd["marked_url"])
    cmp2 = c.get(f"/api/v1/comparisons/{aid}").json()["restored_version"]
    check("comparison shows AI version", cmp2["version_type"] == "ai_reconstructed" and bool(cmp2.get("ai_marked_url")), cmp2.get("ai_marked_url"))

print("\nSUMMARY:", sum(v == "PASS" for v in results.values()), "/", len(results), "passed")
for k, v in results.items():
    if v != "PASS":
        print("  FAILED:", k)
