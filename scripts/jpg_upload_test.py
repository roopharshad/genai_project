"""Upload a JPG with each MIME type browsers use; a non-image must still be rejected."""
import httpx

c = httpx.Client(base_url="http://127.0.0.1:8000", timeout=120)
tok = c.post("/api/v1/auth/login", json={"email": "demo@docrestore.ai", "password": "docrestore123"}).json()
c.headers["Authorization"] = "Bearer " + tok["access_token"]
proj = c.get("/api/v1/projects/").json()[0]["id"]
data = open("samples/faded_document.jpg", "rb").read()
for name, mime in [("doc.jpg", "image/jpeg"), ("doc.jpg", "image/jpg"), ("doc.jpeg", "image/pjpeg"),
                   ("doc.jpg", "application/octet-stream"), ("DOC.JPG", "image/jpeg")]:
    r = c.post("/api/v1/assets/upload", data={"project_id": proj}, files={"file": (name, data, mime)})
    j = r.json()
    print(f"{name:9} {mime:26} -> HTTP {r.status_code} {j.get('stored_filename', j.get('detail'))} {j.get('width')}x{j.get('height')}")
    if r.status_code == 200:
        thumb = c.get(f"/storage/thumbnails/thumb_{j['stored_filename']}")
        print(f"{'':37} thumbnail HTTP {thumb.status_code}")
r = c.post("/api/v1/assets/upload", data={"project_id": proj}, files={"file": ("fake.jpg", b"not an image", "image/jpeg")})
print("fake.jpg (not an image) -> HTTP", r.status_code, str(r.json().get("detail"))[:80])
r = c.post("/api/v1/assets/upload", data={"project_id": proj}, files={"file": ("notes.txt", b"hello", "text/plain")})
print("notes.txt -> HTTP", r.status_code, r.json().get("detail"))
