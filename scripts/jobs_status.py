"""Print the latest restoration jobs."""
import httpx

c = httpx.Client(base_url="http://127.0.0.1:8000", timeout=60)
tok = c.post("/api/v1/auth/login", json={"email": "demo@docrestore.ai", "password": "docrestore123"}).json()
c.headers["Authorization"] = "Bearer " + tok["access_token"]
for j in c.get("/api/v1/restorations/jobs").json()[:5]:
    print(j["id"][:8], j["status"], j["progress"], "|", j["stage"], "|", (j.get("error_message") or "")[:150])
