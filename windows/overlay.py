"""
windows/overlay.py — Ikkilamchi monitorlar uchun overlay oynalarini boshqarish.

Har bir ikkilamchi monitor uchun alohida pywebview subprocess ishga tushiriladi
va overlay.html ko'rsatiladi.
"""

import os
import subprocess
import sys

_overlay_procs: list[subprocess.Popen] = []

# Subprocess ichida ishlaydigan skript (string sifatida yuboriladi)
_OVERLAY_SCRIPT = """
import webview, ctypes, sys, threading, time

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

x = int(sys.argv[1])
y = int(sys.argv[2])
w = int(sys.argv[3])
h = int(sys.argv[4])

MY_PID = ctypes.windll.kernel32.GetCurrentProcessId()


def _get_my_hwnd():
    user32 = ctypes.windll.user32
    found  = ctypes.c_size_t(0)
    Proc   = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_size_t, ctypes.c_size_t)

    def _cb(hwnd, _):
        pid = ctypes.c_ulong(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == MY_PID and user32.IsWindowVisible(hwnd):
            found.value = hwnd
            return False
        return True

    user32.EnumWindows(Proc(_cb), 0)
    return found.value or None


def _topmost_loop():
    user32 = ctypes.windll.user32

    HWND_TOPMOST        = -1
    SWP_FRAMECHANGED    = 0x0020
    SWP_SHOWWINDOW      = 0x0040
    GWL_STYLE           = -16
    GWL_EXSTYLE         = -20
    WS_CAPTION          = 0x00C00000
    WS_THICKFRAME       = 0x00040000
    WS_BORDER           = 0x00800000
    WS_DLGFRAME         = 0x00400000
    WS_SYSMENU          = 0x00080000
    WS_EX_DLGMODALFRAME = 0x00000001
    WS_EX_WINDOWEDGE    = 0x00000100
    WS_EX_CLIENTEDGE    = 0x00000200

    hwnd = None
    for _ in range(30):
        hwnd = _get_my_hwnd()
        if hwnd:
            break
        time.sleep(0.1)

    if not hwnd:
        print("[overlay] hwnd not found, topmost loop aborted")
        return

    try:
        style = user32.GetWindowLongW(hwnd, GWL_STYLE)
        style &= ~(WS_CAPTION | WS_THICKFRAME | WS_BORDER | WS_DLGFRAME | WS_SYSMENU)
        user32.SetWindowLongW(hwnd, GWL_STYLE, style)

        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ex_style &= ~(WS_EX_DLGMODALFRAME | WS_EX_WINDOWEDGE | WS_EX_CLIENTEDGE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
    except Exception as e:
        print(f"[overlay] style strip err: {e}")

    try:
        SWP_FLAGS = SWP_FRAMECHANGED | SWP_SHOWWINDOW
        user32.SetWindowPos(hwnd, HWND_TOPMOST, x, y, w, h, SWP_FLAGS)
        user32.MoveWindow(hwnd, x, y, w, h, True)
        WM_SIZE  = 0x0005
        lparam   = (h & 0xFFFF) << 16 | (w & 0xFFFF)
        user32.SendMessageW(hwnd, WM_SIZE, 0, lparam)
        print(f"[overlay] initial resize sent {w}x{h}")
    except Exception as e:
        print(f"[overlay] initial resize err: {e}")

    print(f"[overlay] entering topmost loop for hwnd={hwnd} @ {x},{y} {w}x{h}")

    _loop_count = 0
    while True:
        try:
            user32.SetWindowPos(hwnd, HWND_TOPMOST, x, y, w, h, SWP_FRAMECHANGED | SWP_SHOWWINDOW)
            _loop_count += 1
            if _loop_count % 10 == 0:
                lparam = (h & 0xFFFF) << 16 | (w & 0xFFFF)
                user32.PostMessageW(hwnd, 0x0005, 0, lparam)
        except Exception as e:
            print(f"[overlay] topmost loop err: {e}")
            break
        time.sleep(0.5)


def _on_shown():
    threading.Thread(target=_topmost_loop, daemon=True).start()


win = webview.create_window(
    "AD BioGuard Overlay",
    url=r"__OVERLAY_URL__",
    x=x, y=y,
    width=w, height=h,
    fullscreen=False,
    frameless=True,
    on_top=True,
    easy_drag=False,
    background_color="#020810",
)
win.events.shown += _on_shown
webview.start()
"""


def create_overlays(secondary_monitors: list, base_dir: str) -> None:
    """Har bir ikkilamchi monitor uchun overlay subprocess ishga tushiradi."""
    global _overlay_procs

    overlay_path = os.path.join(base_dir, "ui", "overlay.html")
    overlay_url  = "file:///" + overlay_path.replace("\\", "/")
    script       = _OVERLAY_SCRIPT.replace("__OVERLAY_URL__", overlay_url)

    for (x, y, w, h) in secondary_monitors:
        try:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            proc  = subprocess.Popen(
                [sys.executable, "-c", script, str(x), str(y), str(w), str(h)],
                creationflags=flags,
            )
            _overlay_procs.append(proc)
            print(f"[overlay] started pid={proc.pid} @ {x},{y} {w}x{h}")
        except Exception as e:
            print(f"[overlay] {e}")


def destroy_overlays() -> None:
    """Barcha overlay subprocess'larni to'xtatadi."""
    for p in _overlay_procs:
        try:
            p.terminate()
        except Exception:
            pass
    _overlay_procs.clear()
