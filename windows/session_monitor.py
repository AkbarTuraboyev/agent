"""
windows/session_monitor.py — Windows sessiya hodisalarini kuzatish.

Lock / Unlock hodisalari ushlab olinadi va BioGuard qayta ishga tushiriladi.
"""

import os
import sys
import ctypes
import time
import threading

import win32gui
import win32ts

from core.keyboard import start_keyboard_block
from core.taskbar import hide_taskbar
from core.monitors import get_all_monitors, start_fullscreen_monitor, find_bioguard_hwnd
from windows.overlay import create_overlays, destroy_overlays

WM_WTSSESSION_CHANGE = 0x02B1
WTS_SESSION_LOCK     = 0x7
WTS_SESSION_UNLOCK   = 0x8

# Asosiy oyna va API ob'ektlari tashqaridan o'rnatiladi
MAIN_WINDOW = None
MAIN_API    = None


def relock_system():
    """Tizim qulflanganda ekranni yana BioGuard bilan to'sib qo'yadi."""
    destroy_overlays()
    hide_taskbar()
    start_keyboard_block()

    monitors = get_all_monitors()

    if len(monitors) > 1:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        create_overlays(monitors[1:], base_dir)

    px, py, pw, ph = monitors[0]
    start_fullscreen_monitor(px, py, pw, ph)

    if MAIN_WINDOW:
        try:
            MAIN_WINDOW.show()
            time.sleep(0.3)
            hwnd = find_bioguard_hwnd()
            if hwnd:
                user32 = ctypes.windll.user32
                user32.ShowWindow(hwnd, 5)
                user32.SetForegroundWindow(hwnd)
                user32.BringWindowToTop(hwnd)
        except Exception as e:
            print("SHOW ERROR:", e)

    if MAIN_API:
        MAIN_API.start_session()


def run_session_monitor():
    """
    Sessiya hodisalarini tinglovchi oynani yaratadi va xabar loopini ishga tushiradi.
    Bu funksiya alohida daemon thread'da chaqirilishi kerak.
    """

    class SessionWatcher:
        def __init__(self):
            message_map = {WM_WTSSESSION_CHANGE: self.on_session_change}

            wc = win32gui.WNDCLASS()
            wc.lpfnWndProc  = message_map
            wc.lpszClassName = "BioGuardSessionWatcher"

            self.classAtom = win32gui.RegisterClass(wc)
            self.hwnd = win32gui.CreateWindow(
                self.classAtom, "BioGuardSessionWatcher",
                0, 0, 0, 0, 0, 0, 0, 0, None,
            )
            win32ts.WTSRegisterSessionNotification(
                self.hwnd, win32ts.NOTIFY_FOR_THIS_SESSION
            )

        def on_session_change(self, hwnd, msg, wparam, lparam):
            if wparam == WTS_SESSION_UNLOCK:
                print("UNLOCK DETECTED")
                if not find_bioguard_hwnd():
                    os.startfile(sys.argv[0])
            elif wparam == WTS_SESSION_LOCK:
                print("LOCK DETECTED")
                relock_system()
            return 0

    SessionWatcher()
    win32gui.PumpMessages()


def start_session_monitor():
    """Sessiya monitorini fon thread'da ishga tushiradi."""
    threading.Thread(target=run_session_monitor, daemon=True).start()
