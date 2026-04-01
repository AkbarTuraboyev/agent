"""
core/activation.py — Agent aktivatsiya (doc 02-bo'lim)

Org bilan oqim:
  1. activation_code + device_uuid + windows_license + public_key → server
  2. Server tekshiradi → unique PC sertifikat qaytaradi
  3. Sertifikat saqlanadi, activation code o'chadi

Orgsiz oqim:
  - Activation code shart emas
  - Email/parol bilan ro'yxatdan o'tish
"""

import json
import urllib.request

from core.config import API_BASE, DEVICE_UUID, WINDOWS_LICENSE
from core.cert import generate_keypair, save_cert, is_activated


class ActivationError(Exception):
    pass


def activate_org(activation_code: str) -> dict:
    """
    Org PC ni aktivatsiya qiladi.
    Doc 02: activation_code + device_uuid + windows_license + public_key → server
    """
    if is_activated():
        return {"status": "already_activated"}

    public_pem, private_pem = generate_keypair()

    payload = {
        "activation_code":  activation_code,
        "device_uuid":      DEVICE_UUID,
        "windows_license":  WINDOWS_LICENSE,
        "public_key":       public_pem,
    }

    body = json.dumps(payload).encode()
    req  = urllib.request.Request(
        f"{API_BASE}/api/agent/activate/",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="ignore")
        try:
            err = json.loads(body)
            raise ActivationError(err.get("detail", "Activation failed"))
        except (json.JSONDecodeError, KeyError):
            raise ActivationError(f"HTTP {e.code}: {body[:200]}")
    except Exception as e:
        raise ActivationError(str(e))

    # Server sertifikat qaytardi — saqlaymiz
    cert_data = data.get("certificate")
    if not cert_data:
        raise ActivationError("Server sertifikat qaytarmadi")

    # Offline admin creds ham serverdan kelishi mumkin
    offline_hash = data.get("offline_admin_hash")
    offline_user = data.get("offline_admin_username")
    if offline_hash and offline_user:
        from core.offline import save_offline_creds
        save_offline_creds(offline_user, offline_hash)

    save_cert(cert_data, private_pem)
    print(f"[activation] OK — cert_id={cert_data.get('cert_id', '')[:8]}...")
    return data


def activate_personal(email: str, password: str) -> dict:
    """
    Orgsiz foydalanuvchi aktivatsiyasi (doc 02).
    Activation code shart emas.
    """
    if is_activated():
        return {"status": "already_activated"}

    public_pem, private_pem = generate_keypair()

    payload = {
        "email":           email,
        "password":        password,
        "device_uuid":     DEVICE_UUID,
        "windows_license": WINDOWS_LICENSE,
        "public_key":      public_pem,
    }

    body = json.dumps(payload).encode()
    req  = urllib.request.Request(
        f"{API_BASE}/api/agent/activate/personal/",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="ignore")
        try:
            err = json.loads(body)
            raise ActivationError(err.get("detail", "Activation failed"))
        except Exception:
            raise ActivationError(f"HTTP {e.code}")
    except Exception as e:
        raise ActivationError(str(e))

    cert_data = data.get("certificate")
    if not cert_data:
        raise ActivationError("Server sertifikat qaytarmadi")

    save_cert(cert_data, private_pem)
    return data
