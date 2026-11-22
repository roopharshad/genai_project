"""Show the quota details Gemini returns for image models (key never printed)."""
import base64
import io
import json
import os
from pathlib import Path

import httpx
import truststore
from dotenv import load_dotenv
from PIL import Image

truststore.inject_into_ssl()
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)
key = os.getenv("GEMINI_API_KEY", "").strip()
buf = io.BytesIO()
Image.new("RGB", (64, 64), "white").save(buf, "PNG")
img = base64.b64encode(buf.getvalue()).decode()
for model in ["gemini-3.1-flash-image", "gemini-3.1-flash-image-preview", "gemini-2.5-flash-image", "gemini-3.1-flash-lite-image"]:
    body = {"contents": [{"parts": [{"inline_data": {"mime_type": "image/png", "data": img}}, {"text": "Return this image unchanged."}]}],
            "generationConfig": {"responseModalities": ["IMAGE"]}}
    r = httpx.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                   json=body, headers={"x-goog-api-key": key}, timeout=120)
    print(f"== {model}: HTTP {r.status_code}")
    if r.status_code != 200:
        err = r.json().get("error", {})
        print("  ", err.get("message", "")[:160].replace(key, "***"))
        for d in err.get("details", []):
            if "violations" in d:
                for v in d["violations"]:
                    print("   quota:", v.get("quotaMetric"), "| id:", v.get("quotaId"), "| limit:", v.get("quotaValue"))
            if d.get("retryDelay"):
                print("   retry after:", d["retryDelay"])
    else:
        parts = r.json()["candidates"][0]["content"]["parts"]
        print("   OK, parts:", [list(p.keys()) for p in parts])
