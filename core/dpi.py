"""
core/dpi.py — DPI Awareness sozlash (eng birinchi chaqirilishi kerak)
"""

import ctypes


def set_dpi_awareness():
    """Windows DPI awareness ni maksimal darajaga o'rnatadi."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
