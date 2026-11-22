"""Print the Workers AI input schema for image-editing models."""
import json
import os
from pathlib import Path

import httpx
import truststore
from dotenv import load_dotenv

truststore.inject_into_ssl()
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)
H = {"Authorization": f"Bearer {os.getenv('CLOUDFLARE_API_TOKEN', '').strip()}"}
acc = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
for m in ["@cf/black-forest-labs/flux-2-klein-9b", "@cf/black-forest-labs/flux-2-dev"]:
    r = httpx.get(f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/models/schema", headers=H, params={"model": m}, timeout=60)
    print("==", m, r.status_code)
    print(json.dumps(r.json().get("result", r.json()), indent=1)[:2500])
