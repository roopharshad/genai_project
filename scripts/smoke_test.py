"""End-to-end smoke test against a running server (http://127.0.0.1:8000)."""
import io
import sys
import zipfile

import httpx
from PIL import Image, ImageDraw

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
SAMPLE = "GFPGAN-master/inputs/whole_imgs/Blake_Lively.jpg"
c = httpx.Client(base_url=BASE, timeout=400)
fails = 0


def check(name, cond, extra=""):
    global fails
    fails += not cond
    print(("PASS " if cond else "FAIL ") + name, extra)


r = c.get("/"); check("frontend index", r.status_code == 200 and "DocRestore AI" in r.text)
for p in ("/css/styles.css", "/js/app.js", "/assets/logo.svg"):
    check(f"static {p}", c.get(p).status_code == 200)
h = c.get("/api/health").json(); check("health", h["status"] == "ok", h)
o = c.get("/api/options").json(); check("options", [m["id"] for m in o["restoration_modes"]] == ["balanced", "fidelity", "detail"])
check("no third-party names in options", not any(w in str(o).lower() for w in ("gfpgan", "hugging", "restoreformer", "v1.")))

# --- validation errors
r = c.post("/api/restore", files={"file": ("x.txt", b"hello", "text/plain")}); check("reject non-image", r.status_code == 400, r.json())
r = c.post("/api/restore", files={"file": ("big.png", b"0" * (11 * 1024 * 1024), "image/png")}); check("reject >10MB", r.status_code == 413, r.json())
gif = io.BytesIO(); Image.new("RGB", (20, 20)).save(gif, "GIF")
r = c.post("/api/restore", files={"file": ("a.gif", gif.getvalue(), "image/gif")}); check("reject GIF", r.status_code == 400, r.json())
r = c.post("/api/restore", files={"file": ("a.jpg", open(SAMPLE, "rb"), "image/jpeg")}, data={"mode": "bogus"}); check("reject bad mode", r.status_code == 400, r.json())
check("path traversal blocked", c.get("/api/files/..%2F..%2Fbackend/app.py").status_code == 404)

# --- real restoration
r = c.post("/api/restore", files={"file": ("Blake_Lively.jpg", open(SAMPLE, "rb"), "image/jpeg")}, data={"mode": "balanced", "scale": "2"})
check("restore", r.status_code == 200, r.text[:300])
if r.status_code == 200:
    j = r.json()
    orig = c.get(j["original"]["url"]); res = c.get(j["result"]["url"] + "?download=true")
    check("original preserved byte-for-byte", orig.content == open(SAMPLE, "rb").read())
    im = Image.open(io.BytesIO(res.content))
    check("restored image 2x", im.size == (j["original"]["width"] * 2, j["original"]["height"] * 2), f"{j['original']} -> {im.size} in {j['duration']}s")
    check("download header", "attachment" in res.headers.get("content-disposition", ""))

# --- UI reconstruction (classical, offline)
ui = Image.new("RGB", (320, 200), "#d4d0c8"); d = ImageDraw.Draw(ui)
d.rectangle((0, 0, 319, 18), fill="#000080"); d.text((6, 4), "Legacy App", fill="white")
d.rectangle((20, 60, 110, 84), fill="#c0c0c0", outline="black"); d.text((40, 66), "OK", fill="black")
buf = io.BytesIO(); ui.save(buf, "PNG")
r = c.post("/api/ui/reconstruct", files={"file": ("ui.png", buf.getvalue(), "image/png")}, data={"engine": "classical", "scale": "2"})
check("ui reconstruct classical", r.status_code == 200 and r.json()["result"]["width"] == 640, r.text[:200])

# --- asset recovery: screenshot + docx-like zip + html
sheet = Image.new("RGB", (400, 200), "white"); d = ImageDraw.Draw(sheet)
d.ellipse((20, 20, 60, 60), fill="red"); d.rectangle((120, 30, 360, 70), fill="#315F49"); d.rectangle((40, 120, 200, 180), fill="navy")
buf = io.BytesIO(); sheet.save(buf, "PNG")
r = c.post("/api/assets/recover", files={"file": ("sheet.png", buf.getvalue(), "image/png")}).json()
check("assets from screenshot = 3", len(r["assets"]) == 3, [(a["width"], a["height"], a["category"]) for a in r["assets"]])
z = io.BytesIO()
with zipfile.ZipFile(z, "w") as zf:
    zf.writestr("word/document.xml", "<doc/>"); zf.writestr("word/media/image1.png", buf.getvalue())
r = c.post("/api/assets/recover", files={"file": ("legacy.docx", z.getvalue())}).json()
check("assets from docx = 1", len(r["assets"]) == 1)
zz = c.get(r["zip_url"]); check("assets zip download", zipfile.ZipFile(io.BytesIO(zz.content)).namelist() == ["asset_001.png"])
import base64  # noqa: E402
html = f'<img src="data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}">'.encode()
r = c.post("/api/assets/recover", files={"file": ("page.html", html)}).json(); check("assets from html = 1", len(r["assets"]) == 1)
r = c.post("/api/assets/recover", files={"file": ("x.exe", b"MZ")}); check("reject unsupported asset file", r.status_code == 400)

s = c.get("/api/stats").json(); check("stats recorded", s["total_jobs"] >= 1, s)
check("history", len(c.get("/api/history").json()) >= 1)
print("\nFAILURES:", fails)
sys.exit(1 if fails else 0)
