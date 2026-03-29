"""
core/monitors.py — Monitor aniqlash va fullscreen rejim boshqaruvi
"""

import ctypes
import time
import threading

_monitor_running = False


def get_all_monitors():
    """Barcha monitorlarni (primary birinchi) ro'yxat sifatida qaytaradi."""
    monitors = []
    try:
        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long),
            ]

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_ulong), ("rcMonitor", RECT),
                ("rcWork", RECT), ("dwFlags", ctypes.c_ulong),
            ]

        MONITORINFOF_PRIMARY = 0x01
        MonitorEnumProc = ctypes.WINFUNCTYPE(
            ctypes.c_bool, ctypes.c_size_t, ctypes.c_size_t,
            ctypes.POINTER(RECT), ctypes.c_ssize_t,
        )

        primary = []
        secondary = []

        def _cb(hmon, hdc, lprect, lparam):
            mi = MONITORINFO()
            mi.cbSize = ctypes.sizeof(MONITORINFO)
            ctypes.windll.user32.GetMonitorInfoW(hmon, ctypes.byref(mi))
            r = mi.rcMonitor
            info = (r.left, r.top, r.right - r.left, r.bottom - r.top)
            if mi.dwFlags & MONITORINFOF_PRIMARY:
                primary.append(info)
            else:
                secondary.append(info)
            return True

        proc = MonitorEnumProc(_cb)
        ctypes.windll.user32.EnumDisplayMonitors(None, None, proc, 0)
        monitors = primary + secondary

    except Exception as e:
        print(f"[monitors] {e}")

    if not monitors:
        try:
            u32 = ctypes.windll.user32
            monitors = [(0, 0, u32.GetSystemMetrics(0), u32.GetSystemMetrics(1))]
        except Exception:
            monitors = [(0, 0, 1920, 1080)]

    print(f"[monitors] {monitors}")
    return monitors


def find_bioguard_hwnd(target_title="AD BioGuard"):
    """Oyna nomiga qarab HWND topadi."""
    user32 = ctypes.windll.user32
    found = ctypes.c_size_t(0)

    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_size_t, ctypes.c_size_t)

    def _cb(hwnd, _):
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            if buf.value == target_title and user32.IsWindowVisible(hwnd):
                found.value = hwnd
                return False
        return True

    user32.EnumWindows(EnumWindowsProc(_cb), 0)
    return found.value or None


def force_primary_fullscreen(x, y, w, h):
    """Asosiy oynani to'liq ekranga majburlaydi."""
    try:
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
        WS_MAXIMIZE         = 0x01000000
        WS_EX_DLGMODALFRAME = 0x00000001
        WS_EX_WINDOWEDGE    = 0x00000100
        WS_EX_CLIENTEDGE    = 0x00000200

        hwnd = find_bioguard_hwnd()
        if not hwnd:
            return

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long),
            ]

        rc = RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rc))
        if (rc.left == x and rc.top == y and
                rc.right - rc.left == w and rc.bottom - rc.top == h):
            return

        style = user32.GetWindowLongW(hwnd, GWL_STYLE)
        style &= ~(WS_CAPTION | WS_THICKFRAME | WS_BORDER |
                   WS_DLGFRAME | WS_SYSMENU | WS_MAXIMIZE)
        user32.SetWindowLongW(hwnd, GWL_STYLE, style)

        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ex_style &= ~(WS_EX_DLGMODALFRAME | WS_EX_WINDOWEDGE | WS_EX_CLIENTEDGE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)

        user32.SetWindowPos(hwnd, HWND_TOPMOST, x, y, w, h, SWP_FRAMECHANGED | SWP_SHOWWINDOW)
        user32.MoveWindow(hwnd, x, y, w, h, True)

        print(f"[fullscreen] applied → x={x} y={y} w={w} h={h}")

    except Exception as e:
        print(f"[fullscreen] {e}")


def start_fullscreen_monitor(x, y, w, h):
    """Oyna doim to'liq ekranda turishini ta'minlaydigan loop ishga tushiradi."""
    global _monitor_running
    _monitor_running = True

    def _loop():
        time.sleep(0.5)
        for _ in range(10):
            if not _monitor_running:
                return
            force_primary_fullscreen(x, y, w, h)
            time.sleep(0.1)
        while _monitor_running:
            force_primary_fullscreen(x, y, w, h)
            time.sleep(0.5)

    threading.Thread(target=_loop, daemon=True).start()


def stop_fullscreen_monitor():
    """To'liq ekran monitoring loopini to'xtatadi."""
    global _monitor_running
    _monitor_running = False
