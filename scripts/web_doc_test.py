"""Upload a document through the website API, run the Recommended preset, print the text report."""
import json
import sys
import time

import httpx

f = sys.argv[1] if len(sys.argv) > 1 else "samples/faded_document.jpg"
c = httpx.Client(base_url="http://127.0.0.1:8000", timeout=120)
tok = c.post("/api/v1/auth/login", json={"email": "demo@docrestore.ai", "password": "docrestore123"}).json()
c.headers["Authorization"] = "Bearer " + (tok.get("access_token") or tok.get("token"))
proj = c.get("/api/v1/projects/").json()[0]["id"]
a = c.post("/api/v1/assets/upload", data={"project_id": proj},
           files={"file": (f.split("/")[-1], open(f, "rb"), "image/jpeg")}).json()
j = c.post("/api/v1/restorations/jobs", json={"project_id": proj, "asset_id": a["id"],
                                              "model_id": "recommended", "config_params": {}}).json()
t0 = time.time()
while j["status"] not in ("completed", "failed"):
    time.sleep(3)
    j = c.get("/api/v1/restorations/jobs/" + j["id"]).json()
print(j["status"], round(time.time() - t0, 1), "s", j.get("error_message") or "")
if j["status"] != "completed":
    sys.exit(1)
cmp = c.get("/api/v1/comparisons/" + a["id"]).json()
rv = cmp["restored_version"]
op = rv["config_summary"]["operational"]
print("size", cmp["original_version"]["width"], cmp["original_version"]["height"], "->", rv["width"], rv["height"])
print("steps:", json.dumps(op["steps"], indent=1))
print("stages:", op.get("stages_url"), op.get("stages"))
r = op.get("text_report", {})
print("chosen stage:", r.get("chosen_stage"))
for k, v in r.get("stages", {}).items():
    print(f"  {k:14} agreement={v.get('agreement_with_original_reading')} conf={v.get('mean_confidence')}")
out = "samples/web_final_" + f.split("/")[-1].rsplit(".", 1)[0] + ".png"
open(out, "wb").write(c.get(rv["url"]).content)
print("stage file http:", c.get(op["stages_url"] + "2_docres.png").status_code, "saved", out)
