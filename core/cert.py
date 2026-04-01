"""
core/cert.py — PC Sertifikat boshqaruvi (doc 10-bo'lim)

Oqim:
  O'rnatish:
    1. RSA keypair yaratiladi
    2. Public key + activation_code + device_uuid + windows_license → server
    3. Server → unique PC sertifikat qaytaradi
    4. Sertifikat + private key shifrlangan holda saqlanadi (TPM yo'q bo'lsa APPDATA)

  Har so'rovda:
    - Timestamp + pc_id → private key bilan HMAC imzolanadi
    - Server imzoni tekshiradi
"""

import os
import json
import hmac
import hashlib
import time
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend


CERT_DIR  = os.path.join(os.environ.get("APPDATA", ""), "ADBioGuard")
CERT_FILE = os.path.join(CERT_DIR, "cert.json")
KEY_FILE  = os.path.join(CERT_DIR, "private.pem")


def _ensure_dir():
    os.makedirs(CERT_DIR, exist_ok=True)


def generate_keypair() -> tuple[str, str]:
    """RSA keypair yaratadi. (public_pem, private_pem) qaytaradi."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode()
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    return public_pem, private_pem


def save_cert(cert_data: dict, private_pem: str):
    """Serverdan kelgan sertifikat va private key ni saqlaydi."""
    _ensure_dir()
    with open(CERT_FILE, "w") as f:
        json.dump(cert_data, f)
    with open(KEY_FILE, "w") as f:
        f.write(private_pem)
    # Faqat owner o'qiy olsin
    try:
        os.chmod(KEY_FILE, 0o600)
    except Exception:
        pass


def load_cert() -> dict | None:
    """Saqlangan sertifikatni yuklaydi. Yo'q bo'lsa None."""
    if not os.path.exists(CERT_FILE):
        return None
    try:
        with open(CERT_FILE) as f:
            return json.load(f)
    except Exception:
        return None


def is_activated() -> bool:
    """Agent aktivatsiyadan o'tganmi?"""
    return load_cert() is not None


def sign_request(pc_id: str) -> dict:
    """
    Har so'rovga qo'shiladigan imzo (doc 10-bo'lim):
    Timestamp + pc_id → HMAC-SHA256 bilan imzolanadi.
    Server replay attack dan himoyalanadi.
    """
    if not os.path.exists(KEY_FILE):
        return {}
    try:
        cert = load_cert()
        timestamp = str(int(time.time()))
        message = f"{pc_id}:{timestamp}".encode()

        with open(KEY_FILE, "rb") as f:
            private_key = serialization.load_pem_private_key(
                f.read(), password=None, backend=default_backend()
            )
        signature = private_key.sign(message, padding.PKCS1v15(), hashes.SHA256())

        import base64
        return {
            "pc_id":     pc_id,
            "timestamp": timestamp,
            "signature": base64.b64encode(signature).decode(),
            "cert_id":   cert.get("cert_id", ""),
        }
    except Exception as e:
        print(f"[cert] sign error: {e}")
        return {}


def delete_cert():
    """Sertifikatni o'chiradi (deactivation)."""
    for f in [CERT_FILE, KEY_FILE]:
        try:
            os.remove(f)
        except Exception:
            pass
