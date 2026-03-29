"""
AD BioGuard — Desktop Biometric Lock Agent
main.py — Asosiy kirish nuqtasi
"""

import os
import sys
import ctypes

# Faqat bitta instance — mutex
_mutex = ctypes.windll.kernel32.CreateMutexW(None, True, "ADBioGuardMutex")
if ctypes.windll.kernel32.GetLastError() == 183:
    sys.exit(0)

import webview

# DPI awareness ENG BIRINCHI chaqirilishi kerak
from core.dpi import set_dpi_awareness
set_dpi_awareness()

from core.config import DEV_MODE, USERNAME
from core.keyboard import start_keyboard_block, stop_keyboard_block
from core.taskbar import hide_taskbar, show_taskbar
from core.monitors import get_all_monitors, start_fullscreen_monitor, stop_fullscreen_monitor

from api.camera import write_chromium_camera_pref

from windows.bioguard_api import BioGuardAPI
from windows.overlay import create_overlays, destroy_overlays
from windows.session_monitor import start_session_monitor
import windows.session_monitor as _sm


def main():
    hide_taskbar()
    start_keyboard_block()

    monitors = get_all_monitors()
    primary  = monitors[0] if monitors else (0, 0, 1920, 1080)
    px, py, pw, ph = primary
    print(f"[primary] x={px} y={py} w={pw} h={ph}")

    base_dir = os.path.dirname(os.path.abspath(__file__))

    if len(monitors) > 1:
        create_overlays(monitors[1:], base_dir)

    ui_path = os.path.join(base_dir, "ui", "index.html")
    url     = "file:///" + ui_path.replace("\\", "/")

    window = webview.create_window(
        "AD BioGuard",
        url=url,
        width=pw,
        height=ph,
        x=px,
        y=py,
        fullscreen=False,
        frameless=True,
        on_top=True,
        easy_drag=False,
        background_color="#040812",
        min_size=(800, 500),
    )

    _sm.MAIN_WINDOW = window

    def _on_closed():
        stop_keyboard_block()
        stop_fullscreen_monitor()
        show_taskbar()
        destroy_overlays()

    def _on_shown():
        start_fullscreen_monitor(px, py, pw, ph)

    window.events.closed += _on_closed
    window.events.shown  += _on_shown

    api = BioGuardAPI(window)
    _sm.MAIN_API = api

    window.expose(api.get_config)
    window.expose(api.start_session)
    window.expose(api.capture_face)
    window.expose(api.start_face_qr_poll)
    window.expose(api.start_finger_poll)
    window.expose(api.stop_finger_poll)
    window.expose(api.hide_lock)
    window.expose(api.dev_exit)

    # Chromium kamera ruxsatlari
    data_dir = os.path.join(base_dir, ".webview_data")
    os.makedirs(data_dir, exist_ok=True)
    write_chromium_camera_pref(data_dir)

    start_session_monitor()

    # storage_path olib tashlandi — file:// URL bilan conflict qiladi
    webview.start(
        gui='edgechromium',
        debug=DEV_MODE,
        private_mode=False,
    )


if __name__ == "__main__":
    main()