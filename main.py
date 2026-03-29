"""
AD BioGuard — Desktop Biometric Lock Agent
main.py — Asosiy kirish nuqtasi
"""

import os
import sys
import traceback

# Log faylga yozish (debug uchun)
_log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bioguard.log")
def log(msg):
    try:
        with open(_log_path, "a", encoding="utf-8") as f:
            import datetime
            f.write(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass

log("=== BioGuard start ===")
log(f"Python: {sys.version}")
log(f"CWD: {os.getcwd()}")

try:
    import webview
    log(f"pywebview version: {webview.__version__}")
except Exception as e:
    log(f"webview import error: {e}")
    sys.exit(1)

# DPI awareness ENG BIRINCHI chaqirilishi kerak
from core.dpi import set_dpi_awareness
set_dpi_awareness()
log("DPI set")

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
    log("main() started")

    hide_taskbar()
    start_keyboard_block()

    monitors = get_all_monitors()
    primary  = monitors[0] if monitors else (0, 0, 1920, 1080)
    px, py, pw, ph = primary
    log(f"primary monitor: x={px} y={py} w={pw} h={ph}, total monitors={len(monitors)}")

    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Ikkinchi monitor overlay — hozircha o'chirilgan (debug)
    # if len(monitors) > 1:
    #     create_overlays(monitors[1:], base_dir)

    ui_path = os.path.join(base_dir, "ui", "index.html")
    url     = "file:///" + ui_path.replace("\\", "/")
    log(f"UI url: {url}")
    log(f"UI exists: {os.path.exists(ui_path)}")

    # ui papkasidagi fayllarni log
    ui_dir = os.path.join(base_dir, "ui")
    if os.path.exists(ui_dir):
        log(f"ui/ files: {os.listdir(ui_dir)}")

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
    log("window created")

    _sm.MAIN_WINDOW = window

    def _on_closed():
        log("window closed")
        stop_keyboard_block()
        stop_fullscreen_monitor()
        show_taskbar()
        destroy_overlays()

    def _on_shown():
        log("window shown")
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

    data_dir = os.path.join(base_dir, ".webview_data")
    os.makedirs(data_dir, exist_ok=True)
    write_chromium_camera_pref(data_dir)

    start_session_monitor()

    log("calling webview.start(gui='edgechromium')")
    try:
        webview.start(
            gui='edgechromium',
            debug=False,
            private_mode=False,
            storage_path=data_dir,
        )
        log("webview.start() returned normally")
    except Exception as e:
        log(f"edgechromium FAILED: {e}")
        log(traceback.format_exc())
        log("trying default engine...")
        try:
            webview.start(
                debug=False,
                private_mode=False,
                storage_path=data_dir,
            )
        except Exception as e2:
            log(f"default also FAILED: {e2}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"FATAL: {e}")
        log(traceback.format_exc())