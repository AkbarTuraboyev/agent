"""
core/keyboard.py — Klaviatura tugmalarini bloklash / ochish
"""

BLOCKED_KEYS = [
    "windows", "left windows", "right windows",
    "alt", "left alt", "right alt",
    "tab", "esc", "escape",
    "ctrl", "left ctrl", "right ctrl",
    "f1", "f2", "f3", "f4", "f5", "f6",
    "f7", "f8", "f9", "f10", "f11", "f12",
]

_keyboard_active = False


def start_keyboard_block():
    """Barcha tizim tugmalarini bloklaydi."""
    global _keyboard_active
    try:
        import keyboard as kb
        _keyboard_active = True
        for k in BLOCKED_KEYS:
            try:
                kb.block_key(k)
            except Exception:
                pass
    except ImportError:
        pass


def stop_keyboard_block():
    """Barcha bloklangan tugmalarni ochadi."""
    global _keyboard_active
    if not _keyboard_active:
        return
    try:
        import keyboard as kb
        kb.unhook_all()
        _keyboard_active = False
    except Exception:
        pass
