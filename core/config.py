"""
core/config.py — Global sozlamalar
"""

import getpass
import subprocess
import uuid as _uuid
import os

API_BASE  = "https://sibilantly-penanceless-young.ngrok-free.dev"
DEV_MODE  = True   # Production da False
DEMO_MODE = False
USERNAME  = getpass.getuser()


def get_device_uuid() -> str:
    """Windows MachineGUID — PC ning noyob identifikatori."""
    try:
        out = subprocess.check_output(
            ["reg", "query",
             r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Cryptography",
             "/v", "MachineGuid"],
            stderr=subprocess.DEVNULL
        ).decode(errors="ignore")
        for line in out.splitlines():
            if "MachineGuid" in line:
                return line.strip().split()[-1]
    except Exception:
        pass
    # Fallback — APPDATA da saqlangan UUID
    path = os.path.join(os.environ.get("APPDATA", ""), "ADBioGuard", "uuid.txt")
    if os.path.exists(path):
        return open(path).read().strip()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    uid = str(_uuid.uuid4())
    open(path, "w").write(uid)
    return uid


def get_windows_license() -> str:
    """Windows Product ID — litsenziya identifikatori."""
    try:
        out = subprocess.check_output(
            ["reg", "query",
             r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion",
             "/v", "ProductId"],
            stderr=subprocess.DEVNULL
        ).decode(errors="ignore")
        for line in out.splitlines():
            if "ProductId" in line:
                return line.strip().split()[-1]
    except Exception:
        pass
    return "UNKNOWN"


DEVICE_UUID     = get_device_uuid()
WINDOWS_LICENSE = get_windows_license()
