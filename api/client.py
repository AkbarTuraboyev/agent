"""
api/client.py — Backend serverga so'rovlar (sertifikat imzosi bilan)
"""

import json
import urllib.request
import urllib.error

from core.config import API_BASE, DEVICE_UUID


def _signed_headers() -> dict:
    """Har so'rovga PC sertifikat imzosini qo'shadi."""
    headers = {"Content-Type": "application/json"}
    try:
        from core.cert import sign_request, is_activated
        if is_activated():
            sig = sign_request(DEVICE_UUID)
            if sig:
                headers["X-PC-ID"]        = sig.get("pc_id", "")
                headers["X-Timestamp"]    = sig.get("timestamp", "")
                headers["X-Signature"]    = sig.get("signature", "")
                headers["X-Cert-ID"]      = sig.get("cert_id", "")
    except Exception:
        pass
    return headers


def api_post(path: str, payload: dict) -> dict:
    body = json.dumps(payload).encode()
    req  = urllib.request.Request(
        f"{API_BASE}{path}",
        data=body,
        headers=_signed_headers(),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def api_get(path: str):
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        headers=_signed_headers(),
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=6) as r:
        raw = r.read()
        try:
            return json.loads(raw)
        except Exception:
            return raw.decode().strip()


def is_online() -> bool:
    """Internet bor-yo'qligini tekshiradi."""
    try:
        urllib.request.urlopen(f"{API_BASE}/api/health/", timeout=3)
        return True
    except Exception:
        return False
