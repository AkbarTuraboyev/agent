"""
windows/overlay.py — Ikkilamchi monitorlar uchun overlay oynalarini boshqarish.
"""

import threading
import ctypes
import time
import os

import webview

_overlay_windows = []
_overlay_threads = []
_lock = threading.Lock()


def _topmost_loop(hwnd: int, x: int, y: int, w: int, h: int, stop_event: threading.Event):
    user32 = ctypes.windll.user32
    HWND_TOPMOST     = -1
    SWP_FRAMECHANGED = 0x0020
    SWP_SHOWWINDOW   = 0x0040
    while not stop_event.is_set():
        try:
            user32.SetWindowPos(hwnd, HWND_TOPMOST, x, y, w, h,
                                SWP_FRAMECHANGED | SWP_SHOWWINDOW)
        except Exception:
            break
        time.sleep(0.5)


def _find_hwnd_by_title(title: str):
    user32 = ctypes.windll.user32
    return user32.FindWindowW(None, title)


def _run_overlay(x: int, y: int, w: int, h: int, overlay_url: str,
                 stop_event: threading.Event, win_holder: list):
    win = webview.create_window(
        "AD BioGuard Overlay",
        url=overlay_url,
        x=x, y=y,
        width=w, height=h,
        fullscreen=False,
        frameless=True,
        on_top=True,
        easy_drag=False,
        background_color="#020810",
    )
    win_holder[0] = win

    def _on_shown():
        time.sleep(0.3)
        hwnd = _find_hwnd_by_title("AD BioGuard Overlay")
        if hwnd:
            threading.Thread(
                target=_topmost_loop,
                args=(hwnd, x, y, w, h, stop_event),
                daemon=True
            ).start()

    win.events.shown += _on_shown

    webview.start(gui='edgechromium', debug=False, private_mode=False)


def create_overlays(secondary_monitors: list, base_dir: str) -> None:
    global _overlay_windows, _overlay_threads

    overlay_path = os.path.join(base_dir, "ui", "overlay.html")
    overlay_url  = "file:///" + overlay_path.replace("\\", "/")

    with _lock:
        _overlay_windows.clear()
        _overlay_threads.clear()

    for (x, y, w, h) in secondary_monitors:
        stop_event = threading.Event()
        win_holder = [None]

        t = threading.Thread(
            target=_run_overlay,
            args=(x, y, w, h, overlay_url, stop_event, win_holder),
            daemon=True
        )
        t.start()

        with _lock:
            _overlay_windows.append((win_holder, stop_event))
            _overlay_threads.append(t)

        print(f"[overlay] started @ {x},{y} {w}x{h}")


def destroy_overlays() -> None:
    with _lock:
        for (win_holder, stop_event) in _overlay_windows:
            stop_event.set()  # topmost loop ni to'xtatadi
            win = win_holder[0]
            if win:
                try:
                    win.destroy()
                except Exception:
                    pass
            # Oynani to'g'ridan-to'g'ri Win32 orqali yopamiz
            hwnd = _find_hwnd_by_title("AD BioGuard Overlay")
            if hwnd:
                ctypes.windll.user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
        _overlay_windows.clear()
        _overlay_threads.clear()