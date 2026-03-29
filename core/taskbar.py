"""
core/taskbar.py — Windows taskbarini yashirish va ko'rsatish
"""

import ctypes

_taskbar_hwnd = None
_taskbar_notify_hwnd = None


def hide_taskbar():
    """Asosiy va ikkilamchi taskbarni yashiradi."""
    global _taskbar_hwnd, _taskbar_notify_hwnd
    try:
        u32 = ctypes.windll.user32
        _taskbar_hwnd = u32.FindWindowW("Shell_TrayWnd", None)
        if _taskbar_hwnd:
            u32.ShowWindow(_taskbar_hwnd, 0)
        _taskbar_notify_hwnd = u32.FindWindowW("Shell_SecondaryTrayWnd", None)
        if _taskbar_notify_hwnd:
            u32.ShowWindow(_taskbar_notify_hwnd, 0)
    except Exception as e:
        print(f"[taskbar hide] {e}")


def show_taskbar():
    """Yashirilgan taskbarni qayta ko'rsatadi."""
    try:
        u32 = ctypes.windll.user32
        if _taskbar_hwnd:
            u32.ShowWindow(_taskbar_hwnd, 5)
        if _taskbar_notify_hwnd:
            u32.ShowWindow(_taskbar_notify_hwnd, 5)
    except Exception as e:
        print(f"[taskbar show] {e}")
