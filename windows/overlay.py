"""
windows/overlay.py — Ikkilamchi monitorlar uchun overlay oynalarini boshqarish.
Subprocess o'rniga threading ishlatiladi (EXE build uchun mos).
"""

import threading
import ctypes
import time
import os

import webview

_overlay_windows = []
_overlay_lock = threading.Lock()


def _topmost_loop(hwnd_holder: list, x: int, y: int, w: int, h: int):
    """Oyna topmost va to'g'ri o'lchamda turishini ta'minlaydi."""
    user32 = ctypes.windll.user32
    HWND_TOPMOST     = -1
    SWP_FRAMECHANGED = 0x0020
    SWP_SHOWWINDOW   = 0x0040

    # hwnd tayyor bo'lishini kutamiz
    for _ in range(50):
        if hwnd_holder[0]:
            break
        time.sleep(0.1)

    hwnd = hwnd_holder[0]
    if not hwnd:
        return

    while True:
        try:
            user32.SetWindowPos(
                hwnd, HWND_TOPMOST, x, y, w, h,
                SWP_FRAMECHANGED | SWP_SHOWWINDOW
            )
        except Exception:
            break
        time.sleep(0.5)


def _find_hwnd_for_pid(pid: int):
    """Berilgan PID ga tegishli ko'rinadigan oynani topadi."""
    import ctypes
    user32 = ctypes.windll.user32
    found = ctypes.c_size_t(0)
    Proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_size_t, ctypes.c_size_t)

    def _cb(hwnd, _):
        pid_buf = ctypes.c_ulong(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid_buf))
        if pid_buf.value == pid and user32.IsWindowVisible(hwnd):
            found.value = hwnd
            return False
        return True

    user32.EnumWindows(Proc(_cb), 0)
    return found.value or None


def _run_overlay(x: int, y: int, w: int, h: int, overlay_url: str):
    """Bitta overlay oynasini alohida thread da ishlatadi."""
    hwnd_holder = [None]

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

    with _overlay_lock:
        _overlay_windows.append(win)

    def _on_shown():
        import os
        pid = os.getpid()
        for _ in range(30):
            hwnd = _find_hwnd_for_pid(pid)
            if hwnd:
                hwnd_holder[0] = hwnd
                break
            time.sleep(0.1)
        threading.Thread(
            target=_topmost_loop,
            args=(hwnd_holder, x, y, w, h),
            daemon=True
        ).start()

    win.events.shown += _on_shown

    webview.start(gui='edgechromium', debug=False, private_mode=False)


def create_overlays(secondary_monitors: list, base_dir: str) -> None:
    """Har bir ikkilamchi monitor uchun overlay thread ishga tushiradi."""
    overlay_path = os.path.join(base_dir, "ui", "overlay.html")
    overlay_url  = "file:///" + overlay_path.replace("\\", "/")

    for (x, y, w, h) in secondary_monitors:
        t = threading.Thread(
            target=_run_overlay,
            args=(x, y, w, h, overlay_url),
            daemon=True
        )
        t.start()
        print(f"[overlay] thread started @ {x},{y} {w}x{h}")


def destroy_overlays() -> None:
    """Barcha overlay oynalarini yopadi."""
    with _overlay_lock:
        for win in _overlay_windows:
            try:
                win.destroy()
            except Exception:
                pass
        _overlay_windows.clear()