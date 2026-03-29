"""
api/client.py — Backend serverga HTTP so'rovlar yuborish
"""

import json
import urllib.request

from core.config import API_BASE


def api_post(path: str, payload: dict) -> dict:
    """JSON POST so'rov yuboradi va javobni qaytaradi."""
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def api_get(path: str):
    """GET so'rov yuboradi; JSON yoki satr qaytaradi."""
    with urllib.request.urlopen(f"{API_BASE}{path}", timeout=6) as r:
        raw = r.read()
        try:
            return json.loads(raw)
        except Exception:
            return raw.decode().strip()
