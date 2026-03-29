"""
windows/session_monitor.py — Windows sessiya hodisalarini kuzatish.
"""

import os
import ctypes
import time
import threading

import win32gui
import win32ts

from core.keyboard import start_keyboard_block, stop_keyboard_block
from core.taskbar import hide_taskbar, show_taskbar
from core.monitors import get_all_monitors, start_fullscreen_monitor, stop_fullscreen_monitor, find_bioguard_hwnd
from windows.overlay import create_overlays, destroy_overlays

WM_WTSSESSION_CHANGE = 0x02B1
WTS_SESSION_LOCK     = 0x7
WTS_SESSION_UNLOCK   = 0x8

MAIN_WINDOW = None
MAIN_API    = None

_relock_lock = threading.Lock()


def relock_system():
    """Lock hodisasida ekranni to'liq qoplaydi."""
    if not _relock_lock.acquire(blocking=False):
        return  # allaqachon relock jarayonida
    try:
        # 1. Taskbarni DARHOL yashiramiz
        hide_taskbar()
        start_keyboard_block()

        # 2. Eski overlaylarni o'chiramiz
        destroy_overlays()
        time.sleep(0.4)

        # 3. Monitorlar va yangi overlaylar
        monitors = get_all_monitors()
        px, py, pw, ph = monitors[0]

        if len(monitors) > 1:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            create_overlays(monitors[1:], base_dir)
            time.sleep(0.5)

        start_fullscreen_monitor(px, py, pw, ph)

        # 4. Asosiy oynani ko'rsatamiz
        if MAIN_WINDOW:
            try:
                MAIN_WINDOW.show()
                time.sleep(0.2)
                hwnd = find_bioguard_hwnd()
                if hwnd:
                    u = ctypes.windll.user32
                    u.ShowWindow(hwnd, 5)
                    u.SetForegroundWindow(hwnd)
                    u.BringWindowToTop(hwnd)
            except Exception as e:
                print(f"[relock] show error: {e}")

        # 5. Sessiya yangilash
        if MAIN_API:
            try:
                MAIN_API.start_session()
            except Exception as e:
                print(f"[relock] session error: {e}")

    finally:
        _relock_lock.release()


def unlock_system():
    """Unlock hodisasida BioGuard ni ko'rsatadi (foydalanuvchi auth qilishi kerak)."""
    # Unlock hodisasida ham relock — foydalanuvchi avval auth qilishi kerak
    threading.Thread(target=relock_system, daemon=True).start()


def run_session_monitor():
    class SessionWatcher:
        def __init__(self):
            message_map = {WM_WTSSESSION_CHANGE: self.on_session_change}
            wc = win32gui.WNDCLASS()
            wc.lpfnWndProc   = message_map
            wc.lpszClassName = "BioGuardSessionWatcher"
            self.classAtom   = win32gui.RegisterClass(wc)
            self.hwnd = win32gui.CreateWindow(
                self.classAtom, "BioGuardSessionWatcher",
                0, 0, 0, 0, 0, 0, 0, 0, None,
            )
            win32ts.WTSRegisterSessionNotification(
                self.hwnd, win32ts.NOTIFY_FOR_THIS_SESSION
            )

        def on_session_change(self, hwnd, msg, wparam, lparam):
            if wparam == WTS_SESSION_LOCK:
                print("[monitor] LOCK")
                threading.Thread(target=relock_system, daemon=True).start()
            elif wparam == WTS_SESSION_UNLOCK:
                print("[monitor] UNLOCK → relock")
                threading.Thread(target=relock_system, daemon=True).start()
            return 0

    SessionWatcher()
    win32gui.PumpMessages()


def start_session_monitor():
    threading.Thread(target=run_session_monitor, daemon=True).start()