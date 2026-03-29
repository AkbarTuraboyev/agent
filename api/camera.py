"""
api/camera.py — Kamera mavjudligini tekshirish va Chromium ruxsatlarini yozish
"""

import json
import os


def check_camera() -> bool:
    """Kamera (index 0) ochilishini tekshiradi."""
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        ok = cap.isOpened()
        cap.release()
        return ok
    except Exception:
        return False


def write_chromium_camera_pref(data_dir: str) -> None:
    """
    Chromium Preferences fayliga kamera/mikrofon ruxsatlarini yozadi,
    shunda pywebview ichidagi sahifa kameraga so'rovsiz kira oladi.
    """
    try:
        profile_dir = os.path.join(data_dir, "Default")
        os.makedirs(profile_dir, exist_ok=True)
        pref_file = os.path.join(profile_dir, "Preferences")

        prefs = {}
        if os.path.exists(pref_file):
            try:
                with open(pref_file, "r", encoding="utf-8") as f:
                    prefs = json.load(f)
            except Exception:
                prefs = {}

        prefs.setdefault("profile", {})
        prefs["profile"].setdefault("content_settings", {})
        prefs["profile"]["content_settings"].setdefault("exceptions", {})

        camera_grant = {
            "file:///*,*": {"last_modified": "13000000000000000", "setting": 1},
            "file:///,*":  {"last_modified": "13000000000000000", "setting": 1},
        }
        prefs["profile"]["content_settings"]["exceptions"]["media_stream_camera"] = camera_grant
        prefs["profile"]["content_settings"]["exceptions"]["media_stream_mic"] = camera_grant

        with open(pref_file, "w", encoding="utf-8") as f:
            json.dump(prefs, f, separators=(",", ":"))

        print(f"[camera pref] written → {pref_file}")
    except Exception as e:
        print(f"[camera pref] failed: {e}")
