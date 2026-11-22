"""Gemini API client for the document chatbot (REST, no SDK dependency).

The key is read from GEMINI_API_KEY (.env). On 429/500/503 the request is retried and then
falls back to lighter models in GEMINI_FALLBACK_MODELS. The key is never logged.
"""
import logging
import os
import time

import httpx
import truststore

from .. import config  # noqa: F401  (loads .env)

truststore.inject_into_ssl()  # this machine's TLS chain is only trusted by the Windows store

log = logging.getLogger("docrestore.gemini")

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
RETRY_STATUS = {429, 500, 502, 503, 504}


class GeminiError(RuntimeError):
    pass


def _key() -> str:
    return (os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_APIKEY") or "").strip()


def available() -> tuple[bool, str]:
    return (True, "ok") if _key() else (False, "GEMINI_API_KEY is not set")


def models() -> list[str]:
    primary = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
    fallback = os.getenv("GEMINI_FALLBACK_MODELS", "gemini-3.1-flash-lite,gemini-flash-latest,gemini-3.8-flash")
    out = []
    for m in [primary] + fallback.split(","):
        m = m.strip()
        if m and m not in out:
            out.append(m)
    return out


def generate(system: str, history: list[dict], question: str, timeout: float = 45,
             images: list[tuple[str, bytes]] | None = None) -> dict:
    """history: [{"role": "user"|"assistant", "content": str}]; images: [(mime, bytes)] sent with
    the question. Returns {"text", "model"}."""
    import base64
    key = _key()
    if not key:
        raise GeminiError("GEMINI_API_KEY is not set. Add it to the .env file and restart the server.")
    contents = [{"role": "model" if h["role"] == "assistant" else "user", "parts": [{"text": h["content"]}]}
                for h in history[-12:] if h.get("content")]
    parts = [{"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode()}}
             for mime, data in (images or [])]
    parts.append({"text": question})
    contents.append({"role": "user", "parts": parts})
    body = {"systemInstruction": {"parts": [{"text": system}]}, "contents": contents,
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048}}
    last = ""
    # One quick attempt per model: on "busy" move straight to the next model instead of waiting.
    # A final pass retries the whole list once after a short pause.
    for model in models() + models()[:1]:
        for attempt in range(1):
            try:
                r = httpx.post(API.format(model=model), json=body, headers={"x-goog-api-key": key}, timeout=timeout)
            except httpx.HTTPError as exc:
                last = f"{model}: network error {type(exc).__name__}"
                time.sleep(1.5)
                continue
            if r.status_code == 200:
                data = r.json()
                parts = (data.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts).strip()
                if text:
                    return {"text": text, "model": model}
                last = f"{model}: empty response ({(data.get('candidates') or [{}])[0].get('finishReason')})"
                break
            msg = r.text[:200].replace(key, "***")
            last = f"{model}: HTTP {r.status_code} {msg}"
            log.warning("Gemini %s", last)
            if r.status_code in (401, 403):
                raise GeminiError("Gemini rejected the API key (HTTP %d)." % r.status_code)
            if r.status_code not in RETRY_STATUS:
                break  # e.g. 404 model unavailable -> next model
            time.sleep(0.5)
    raise GeminiError(f"Gemini is unavailable right now. Last error: {last}")
