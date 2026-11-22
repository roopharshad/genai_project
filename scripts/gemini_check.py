"""Check that GEMINI_API_KEY in .env works, without printing the key."""
import os
import sys
from pathlib import Path

import httpx
import truststore
from dotenv import load_dotenv

truststore.inject_into_ssl()
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
key = os.getenv("GEMINI_API_KEY", "").strip()
model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
if not key:
    sys.exit("GEMINI_API_KEY is not set")
print("key prefix:", key[:3], "length:", len(key), "model:", model)
url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
body = {"contents": [{"parts": [{"text": "Reply with exactly: OK"}]}]}
for name, kwargs in [("x-goog-api-key header", {"headers": {"x-goog-api-key": key}}),
                     ("Bearer token", {"headers": {"Authorization": f"Bearer {key}"}})]:
    r = httpx.post(url, json=body, timeout=60, **kwargs)
    msg = r.text[:300].replace(key, "***")
    print(f"{name}: HTTP {r.status_code} {msg}")
    if r.status_code == 200:
        break
