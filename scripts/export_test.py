"""Test every Export page download through the API exactly as the page calls it."""
import httpx

c = httpx.Client(base_url="http://127.0.0.1:8000", timeout=300)
tok = c.post("/api/v1/auth/login", json={"email": "demo@docrestore.ai", "password": "docrestore123"}).json()
h = {"Authorization": "Bearer " + tok["access_token"]}
proj = c.get("/api/v1/projects/", headers=h).json()[0]["id"]

r = c.get(f"/api/v1/reports/export/csv?project_id={proj}", headers=h)
print("CSV with login:", r.status_code, r.headers.get("content-type"), f"{len(r.text.splitlines())} lines")
print("CSV without login (old link behaviour):", c.get(f"/api/v1/reports/export/csv?project_id={proj}").status_code)

g = c.post("/api/v1/reports/generate", headers=h, params={"project_id": proj, "title": "Test Quality Report"}).json()
print("generate:", g.get("status"), g.get("stored_filename"))
d = c.get(f"/api/v1/reports/{g['id']}/download", headers=h)
print("PDF download:", d.status_code, d.headers.get("content-type"), len(d.content), "bytes, starts", d.content[:5],
      "|", d.headers.get("content-disposition"))
open("samples/export_test_report.pdf", "wb").write(d.content)
print("PDF without login:", c.get(f"/api/v1/reports/{g['id']}/download").status_code)

old = [x for x in c.get(f"/api/v1/reports/?project_id={proj}", headers=h).json() if x["stored_filename"].endswith(".txt")]
if old:
    o = c.get(f"/api/v1/reports/{old[0]['id']}/download", headers=h)
    print("older .txt report download:", o.status_code, o.headers.get("content-type"), len(o.content), "bytes")

assets = c.get("/api/v1/assets/", headers=h).json()
for a in assets:
    cmp_ = c.get(f"/api/v1/comparisons/{a['id']}", headers=h).json()
    rv = cmp_["restored_version"]
    if rv["version_type"] != "original":
        im = c.get(rv["url"])
        print("restored image:", a["original_filename"], im.status_code, im.headers.get("content-type"), len(im.content), "bytes")
        break
