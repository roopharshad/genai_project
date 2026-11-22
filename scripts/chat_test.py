"""Time one chatbot request through the website API on the most recent asset."""
import sys
import time

import httpx

c = httpx.Client(base_url="http://127.0.0.1:8000", timeout=300)
tok = c.post("/api/v1/auth/login", json={"email": "demo@docrestore.ai", "password": "docrestore123"}).json()
c.headers["Authorization"] = "Bearer " + tok["access_token"]
aid = sys.argv[1] if len(sys.argv) > 1 else c.get("/api/v1/assets/").json()[0]["id"]
for q in ["Summarise this document in two sentences.", "What is the date in this document?"]:
    t = time.time()
    r = c.post(f"/api/v1/document-ai/{aid}/chat", json={"question": q, "history": []})
    d = r.json()
    print(f"HTTP {r.status_code} in {time.time() - t:.1f}s model={d.get('model')} text_source={d.get('text_source')}")
    print("  ", (d.get("answer") or d.get("detail") or "")[:400].encode("ascii", "replace").decode())
