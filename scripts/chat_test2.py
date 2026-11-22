"""Chatbot edge cases: follow-up with history, an unrestored upload, empty question, no auth."""
import time

import httpx

B = "http://127.0.0.1:8000/api/v1"
c = httpx.Client(timeout=300)
tok = c.post(f"{B}/auth/login", json={"email": "demo@docrestore.ai", "password": "docrestore123"}).json()["access_token"]
h = {"Authorization": "Bearer " + tok}
restored = "98882aef-eba0-4181-8d33-1c793fca27e0"

# 1. follow-up that depends on history
hist = [{"role": "user", "content": "Who is the letter addressed to?"},
        {"role": "assistant", "content": "It is addressed to John."}]
t = time.time()
r = c.post(f"{B}/document-ai/{restored}/chat", headers=h, json={"question": "And where was he asked to come back to?", "history": hist})
print("follow-up:", r.status_code, f"{time.time() - t:.1f}s", (r.json().get("answer") or r.json().get("detail"))[:250].encode("ascii", "replace").decode())

# 2. fresh upload never restored (chat must still work from the original image)
proj = c.get(f"{B}/projects/", headers=h).json()[0]["id"]
a = c.post(f"{B}/assets/upload", headers=h, data={"project_id": proj},
           files={"file": ("letter_newyork.png", open("samples/docs/letter_newyork.png", "rb"), "image/png")}).json()
t = time.time()
r = c.post(f"{B}/document-ai/{a['id']}/chat", headers=h, json={"question": "Who signed this letter and when was it written?"})
print("unrestored upload:", r.status_code, f"{time.time() - t:.1f}s", (r.json().get("answer") or r.json().get("detail"))[:250].encode("ascii", "replace").decode())

# 3. empty question -> 400, 4. no login -> 401
print("empty question:", c.post(f"{B}/document-ai/{restored}/chat", headers=h, json={"question": "  "}).status_code)
print("no auth:", c.post(f"{B}/document-ai/{restored}/chat", json={"question": "hi"}).status_code)
print("status:", c.get(f"{B}/document-ai/status").json())
