"""
core/offline.py — Internet uzilganda offline admin login (doc 06-bo'lim)

Org bilan:
  - Admin AD login/parol bilan kiradi
  - Local da HMAC bilan tekshiriladi (serverda saqlangan hash)
  - Internet kelsa → oddiy biometrik qayta yoqiladi

Orgsiz:
  - Foydalanuvchi o'z parolini kiritadi
  - Agent o'chiriladi / biometriksiz ishlaydi
"""

import os
import json
import hashlib
import hmac

OFFLINE_FILE = os.path.join(os.environ.get("APPDATA", ""), "ADBioGuard", "offline.json")


def has_offline_creds() -> bool:
    """Offline credentials saqlangan?"""
    return os.path.exists(OFFLINE_FILE)


def save_offline_creds(username: str, password_hash: str):
    """
    Serverdan kelgan admin parol hash ini saqlaydi.
    Faqat internet yo'qda ishlatiladi.
    """
    import os
    os.makedirs(os.path.dirname(OFFLINE_FILE), exist_ok=True)
    with open(OFFLINE_FILE, "w") as f:
        json.dump({"username": username, "hash": password_hash}, f)
    try:
        os.chmod(OFFLINE_FILE, 0o600)
    except Exception:
        pass


def verify_offline(username: str, password: str) -> bool:
    """Kiritilgan parolni saqlangan hash bilan tekshiradi."""
    if not has_offline_creds():
        return False
    try:
        with open(OFFLINE_FILE) as f:
            data = json.load(f)
        if data.get("username", "").lower() != username.lower():
            return False
        # SHA-256 hash tekshirish
        ph = hashlib.sha256(password.encode()).hexdigest()
        return hmac.compare_digest(ph, data.get("hash", ""))
    except Exception:
        return False
