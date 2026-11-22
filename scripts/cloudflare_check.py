"""Verify the Cloudflare token, find its account, list Workers AI image models (token never printed)."""
import os
from pathlib import Path

import httpx
import truststore
from dotenv import load_dotenv

truststore.inject_into_ssl()
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)
tok = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
H = {"Authorization": f"Bearer {tok}"}
B = "https://api.cloudflare.com/client/v4"
print("token length:", len(tok))
for url in [f"{B}/user/tokens/verify"]:
    r = httpx.get(url, headers=H, timeout=60)
    print("verify user token:", r.status_code, r.json().get("result"), r.json().get("errors"))
acc = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
r = httpx.get(f"{B}/accounts", headers=H, timeout=60)
print("accounts:", r.status_code, [(a["id"], a["name"]) for a in r.json().get("result") or []], r.json().get("errors"))
if not acc and r.json().get("result"):
    acc = r.json()["result"][0]["id"]
if acc:
    r = httpx.get(f"{B}/accounts/{acc}/tokens/verify", headers=H, timeout=60)
    print("verify account token:", r.status_code, r.json().get("result"), r.json().get("errors"))
    for task in ["Text-to-Image", "Image-to-Image"]:
        r = httpx.get(f"{B}/accounts/{acc}/ai/models/search", headers=H, params={"task": task, "per_page": 100}, timeout=60)
        print(f"{task} models:", r.status_code, r.json().get("errors"))
        for m in r.json().get("result") or []:
            props = {p["property_id"]: p["value"] for p in m.get("properties", [])}
            print("   ", m["name"], "|", (m.get("description") or "")[:110].replace("\n", " "), "|", props.get("beta", ""))
