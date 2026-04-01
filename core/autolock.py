"""
core/autolock.py — Auto-lock (doc 04-bo'lim)

- Agent har 30 sek tekshiradi
- Timeout - 30 sek qoldi → ogohlantirish
- Foydalanuvchi "Davom etish" bosmasa → qulflanadi
"""

import threading
import time
import ctypes

_running  = False
_timeout  = 300   # soniya
_on_warn  = None  # callable(seconds_left)
_on_lock  = None  # callable()


def _get_idle_seconds() -> float:
    """Windows GetLastInputInfo orqali harakatsizlik vaqti."""
    try:
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
        millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
        return millis / 1000.0
    except Exception:
        return 0.0


def _loop():
    global _running
    warned = False
    while _running:
        time.sleep(30)
        if not _running:
            break
        idle      = _get_idle_seconds()
        remaining = _timeout - idle

        if remaining <= 30 and not warned:
            warned = True
            if _on_warn:
                try:
                    _on_warn(max(0, int(remaining)))
                except Exception:
                    pass

        if remaining <= 0:
            _running = False
            if _on_lock:
                try:
                    _on_lock()
                except Exception:
                    pass
            return

        if idle < 30:
            warned = False  # foydalanuvchi aktiv — reset


def start_autolock(timeout_seconds: int, on_warn, on_lock):
    global _running, _timeout, _on_warn, _on_lock
    stop_autolock()
    _timeout  = max(60, timeout_seconds)
    _on_warn  = on_warn
    _on_lock  = on_lock
    _running  = True
    threading.Thread(target=_loop, daemon=True).start()
    print(f"[autolock] started, timeout={_timeout}s")


def stop_autolock():
    global _running
    _running = False
