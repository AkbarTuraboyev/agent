"""
AD BioGuard — Desktop Biometric Lock Agent
main.py — pywebview (primary) + pywebview subprocess (secondary monitors)
"""

import win32ts
import win32con
import win32gui
import webview
import threading
import subprocess
import sys
import time
import getpass
import json
import base64
import urllib.request
import os
import ctypes

# ══════════════════════════════════════════════════════════════════
# DPI AWARENESS — ENG BIRINCHI CHAQIRILISHI KERAK
# ══════════════════════════════════════════════════════════════════
def _set_dpi_awareness():
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

_set_dpi_awareness()

# ══════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════
API_BASE = "https://sibilantly-penanceless-young.ngrok-free.dev"
DEV_MODE = True   # True: "Dev Exit" tugmasi ishlab turadi (ishlamay qolsa chiqish uchun)
USERNAME = getpass.getuser()
MAIN_WINDOW = None

# ══════════════════════════════════════════════════════════════════
# KEYBOARD BLOCK
# ══════════════════════════════════════════════════════════════════
BLOCKED_KEYS = [
    "windows","left windows","right windows",
    "alt","left alt","right alt",
    "tab","esc","escape",
    "ctrl","left ctrl","right ctrl",
    "f1","f2","f3","f4","f5","f6",
    "f7","f8","f9","f10","f11","f12",
]
_keyboard_active = False

def start_keyboard_block():
    global _keyboard_active
    try:
        import keyboard as kb
        _keyboard_active = True
        for k in BLOCKED_KEYS:
            try: kb.block_key(k)
            except: pass
    except ImportError:
        pass

def stop_keyboard_block():
    global _keyboard_active
    if not _keyboard_active: return
    try:
        import keyboard as kb
        kb.unhook_all()
        _keyboard_active = False
    except: pass

# ══════════════════════════════════════════════════════════════════
# TASKBAR
# ══════════════════════════════════════════════════════════════════
_taskbar_hwnd        = None
_taskbar_notify_hwnd = None

def hide_taskbar():
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
    try:
        u32 = ctypes.windll.user32
        if _taskbar_hwnd:
            u32.ShowWindow(_taskbar_hwnd, 5)
        if _taskbar_notify_hwnd:
            u32.ShowWindow(_taskbar_notify_hwnd, 5)
    except Exception as e:
        print(f"[taskbar show] {e}")

# ══════════════════════════════════════════════════════════════════
# MONITOR DETECTION
# ══════════════════════════════════════════════════════════════════
def get_all_monitors():
    monitors = []
    try:
        class RECT(ctypes.Structure):
            _fields_ = [("left",ctypes.c_long),("top",ctypes.c_long),
                        ("right",ctypes.c_long),("bottom",ctypes.c_long)]

        class MONITORINFO(ctypes.Structure):
            _fields_ = [("cbSize",ctypes.c_ulong),("rcMonitor",RECT),
                        ("rcWork",RECT),("dwFlags",ctypes.c_ulong)]

        MONITORINFOF_PRIMARY = 0x01
        MonitorEnumProc = ctypes.WINFUNCTYPE(
            ctypes.c_bool, ctypes.c_size_t, ctypes.c_size_t,
            ctypes.POINTER(RECT), ctypes.c_ssize_t)

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
        except:
            monitors = [(0, 0, 1920, 1080)]

    print(f"[monitors] {monitors}")
    return monitors

# ══════════════════════════════════════════════════════════════════
# SECONDARY MONITOR OVERLAYS  (overlay.html via pywebview subprocess)
# ══════════════════════════════════════════════════════════════════
_overlay_procs = []

def create_overlays(secondary_monitors):
    global _overlay_procs

    overlay_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "ui", "overlay.html")
    overlay_url = "file:///" + overlay_path.replace("\\", "/")

    _PROC_SCRIPT = """
import webview, ctypes, sys, threading, time

try:    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except:
    try: ctypes.windll.user32.SetProcessDPIAware()
    except: pass

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
        style &= ~(WS_CAPTION|WS_THICKFRAME|WS_BORDER|WS_DLGFRAME|WS_SYSMENU)
        user32.SetWindowLongW(hwnd, GWL_STYLE, style)

        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ex_style &= ~(WS_EX_DLGMODALFRAME|WS_EX_WINDOWEDGE|WS_EX_CLIENTEDGE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
    except Exception as e:
        print(f"[overlay] style strip err: {e}")

    try:
        SWP_FLAGS = SWP_FRAMECHANGED | SWP_SHOWWINDOW
        user32.SetWindowPos(hwnd, HWND_TOPMOST, x, y, w, h, SWP_FLAGS)
        user32.MoveWindow(hwnd, x, y, w, h, True)
        WM_SIZE = 0x0005
        SIZE_RESTORED = 0
        lparam = (h & 0xFFFF) << 16 | (w & 0xFFFF)
        user32.SendMessageW(hwnd, WM_SIZE, SIZE_RESTORED, lparam)
        print(f"[overlay] initial resize sent {w}x{h}")
    except Exception as e:
        print(f"[overlay] initial resize err: {e}")

    print(f"[overlay] entering topmost loop for hwnd={hwnd} @ {x},{y} {w}x{h}")

    _loop_count = 0
    while True:
        try:
            user32.SetWindowPos(hwnd, HWND_TOPMOST, x, y, w, h,
                                SWP_FRAMECHANGED | SWP_SHOWWINDOW)
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
""".replace("__OVERLAY_URL__", overlay_url)

    for (x, y, w, h) in secondary_monitors:
        try:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            proc = subprocess.Popen(
                [sys.executable, "-c", _PROC_SCRIPT,
                 str(x), str(y), str(w), str(h)],
                creationflags=flags
            )
            _overlay_procs.append(proc)
            print(f"[overlay] started pid={proc.pid} @ {x},{y} {w}x{h}")
        except Exception as e:
            print(f"[overlay] {e}")

def destroy_overlays():
    for p in _overlay_procs:
        try: p.terminate()
        except: pass
    _overlay_procs.clear()

# ══════════════════════════════════════════════════════════════════
# FORCE PRIMARY WINDOW FULLSCREEN
# ══════════════════════════════════════════════════════════════════
_monitor_running = False

def _find_bioguard_hwnd(target_title="AD BioGuard"):
    user32 = ctypes.windll.user32
    found  = ctypes.c_size_t(0)

    EnumWindowsProc = ctypes.WINFUNCTYPE(
        ctypes.c_bool, ctypes.c_size_t, ctypes.c_size_t)

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

        hwnd = _find_bioguard_hwnd()
        if not hwnd:
            return

        class RECT(ctypes.Structure):
            _fields_ = [("left",ctypes.c_long),("top",ctypes.c_long),
                        ("right",ctypes.c_long),("bottom",ctypes.c_long)]
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

        user32.SetWindowPos(
            hwnd, HWND_TOPMOST, x, y, w, h,
            SWP_FRAMECHANGED | SWP_SHOWWINDOW)
        user32.MoveWindow(hwnd, x, y, w, h, True)

        print(f"[fullscreen] applied → x={x} y={y} w={w} h={h}")

    except Exception as e:
        print(f"[fullscreen] {e}")

def start_fullscreen_monitor(x, y, w, h):
    global _monitor_running
    _monitor_running = True
    def _loop():
        time.sleep(0.5)
        for _ in range(10):
            if not _monitor_running: return
            force_primary_fullscreen(x, y, w, h)
            time.sleep(0.1)
        while _monitor_running:
            force_primary_fullscreen(x, y, w, h)
            time.sleep(0.5)
    threading.Thread(target=_loop, daemon=True).start()

def stop_fullscreen_monitor():
    global _monitor_running
    _monitor_running = False

# ══════════════════════════════════════════════════════════════════
# API LAYER
# ══════════════════════════════════════════════════════════════════
def api_post(path, payload):
    body = json.dumps(payload).encode()
    req  = urllib.request.Request(
        f"{API_BASE}{path}", data=body,
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

def api_get(path):
    with urllib.request.urlopen(f"{API_BASE}{path}", timeout=6) as r:
        raw = r.read()
        try:    return json.loads(raw)
        except: return raw.decode().strip()

# ══════════════════════════════════════════════════════════════════
# CAMERA CHECK
# ══════════════════════════════════════════════════════════════════
def check_camera():
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        ok  = cap.isOpened()
        cap.release()
        return ok
    except: return False

def _write_chromium_camera_pref(data_dir):
    try:
        profile_dir = os.path.join(data_dir, "Default")
        os.makedirs(profile_dir, exist_ok=True)
        pref_file = os.path.join(profile_dir, "Preferences")

        prefs = {}
        if os.path.exists(pref_file):
            try:
                with open(pref_file, "r", encoding="utf-8") as f:
                    prefs = json.load(f)
            except Exception:
                prefs = {}

        prefs.setdefault("profile", {})
        prefs["profile"].setdefault("content_settings", {})
        prefs["profile"]["content_settings"].setdefault("exceptions", {})
        prefs["profile"]["content_settings"]["exceptions"]["media_stream_camera"] = {
            "file:///*,*": {"last_modified": "13000000000000000", "setting": 1},
            "file:///,*":  {"last_modified": "13000000000000000", "setting": 1},
        }
        prefs["profile"]["content_settings"]["exceptions"]["media_stream_mic"] = {
            "file:///*,*": {"last_modified": "13000000000000000", "setting": 1},
            "file:///,*":  {"last_modified": "13000000000000000", "setting": 1},
        }

        with open(pref_file, "w", encoding="utf-8") as f:
            json.dump(prefs, f, separators=(",", ":"))
        print(f"[camera pref] written → {pref_file}")
    except Exception as e:
        print(f"[camera pref] failed: {e}")

# ══════════════════════════════════════════════════════════════════
# JS API
# ══════════════════════════════════════════════════════════════════
class BioGuardAPI:

    def __init__(self, window_ref):
        self._window     = window_ref
        self._session_id = None
        self._polling    = False

    def get_config(self):
        return json.dumps({
            "username":  USERNAME,
            "camera_ok": check_camera(),
            "dev_mode":  DEV_MODE,
        })

    def start_session(self):
        def _run():
            try:
                data = api_post("/api/agent/session/start/", {"username": USERNAME})
                self._session_id = data.get("session_id", "")
                self._js(f"App.onSessionReady('{self._session_id}')")
            except Exception as e:
                self._js(f"App.onError('Session failed: {self._esc(str(e))}')")
        threading.Thread(target=_run, daemon=True).start()

    def capture_face(self, image_b64):
        def _run():
            try:
                self._js("App.setStatus('verifying', 'Analyzing face...')")
                data = api_post("/api/face/agent/check/", {
                    "session_id": self._session_id,
                    "username":   USERNAME,
                    "image":      image_b64
                })
                status = data.get("status", "")
                if status == "verified":
                    self._js("App.onVerified()")
                else:
                    msg = self._esc(data.get("detail", "Face not recognized"))
                    self._js(f"App.onFaceRetry('{msg}')")
            except Exception as e:
                self._js(f"App.onFaceRetry('{self._esc(str(e))}')")
        threading.Thread(target=_run, daemon=True).start()

    def start_finger_poll(self):
        if not self._session_id:
            self._js("App.onError('No session')")
            return
        qr_url = f"{API_BASE}/agent/mobile/fingerprint/{self._session_id}/"
        self._js(f"App.renderQR('{qr_url}')")
        self._polling = True
        threading.Thread(target=self._poll_loop, daemon=True).start()

    def start_face_qr_poll(self):
        if not self._session_id:
            self._js("App.onError('No session')")
            return
        qr_url = f"{API_BASE}/agent/mobile/face/{self._session_id}/"
        self._js(f"App.renderFaceQR('{qr_url}')")
        self._polling = True
        threading.Thread(target=self._face_qr_poll_loop, daemon=True).start()

    def _face_qr_poll_loop(self):
        elapsed = 0
        limit   = 120
        while self._polling and elapsed < limit:
            try:
                raw    = api_get(f"/api/agent/face/phone/status/{self._session_id}/")
                status = raw if isinstance(raw, str) else raw.get("status", "")
                if status == "completed":
                    self._polling = False
                    self._js("App.onVerified()")
                    return
                elif status == "expired":
                    self._polling = False
                    self._js("App.onQRExpired()")
                    return
            except: pass
            time.sleep(2)
            elapsed += 2
            self._js(f"App.updateFaceTimer({limit - elapsed})")
        if self._polling:
            self._polling = False
            self._js("App.onQRExpired()")

    def stop_finger_poll(self):
        self._polling = False

    def _poll_loop(self):
        elapsed = 0
        limit   = 120
        while self._polling and elapsed < limit:
            try:
                raw    = api_get(f"/api/agent/fingerprint/phone/status/{self._session_id}/")
                status = raw if isinstance(raw, str) else raw.get("status", "")
                if status == "completed":
                    self._polling = False
                    self._js("App.onVerified()")
                    return
                elif status == "expired":
                    self._polling = False
                    self._js("App.onQRExpired()")
                    return
            except: pass
            time.sleep(2)
            elapsed += 2
            self._js(f"App.updateTimer({limit - elapsed})")
        if self._polling:
            self._polling = False
            self._js("App.onQRExpired()")

    def hide_lock(self):
        stop_keyboard_block()
        stop_fullscreen_monitor()
        show_taskbar()
        destroy_overlays()
        self._window.hide()

    def dev_exit(self):
        """DEV: biror narsa ishlamay qolsa — hammani to'liq yopish"""
        if DEV_MODE:
            stop_keyboard_block()
            stop_fullscreen_monitor()
            show_taskbar()
            destroy_overlays()
            self._window.destroy()

    def _js(self, code):
        try: self._window.evaluate_js(code)
        except: pass

    @staticmethod
    def _esc(s):
        return s.replace("'", "\\'").replace("\n", " ")

# ══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════
WM_WTSSESSION_CHANGE = 0x02B1
WTS_SESSION_LOCK = 0x7
WTS_SESSION_UNLOCK = 0x8

def relock_system():
    global MAIN_WINDOW, MAIN_API

    destroy_overlays()
    hide_taskbar()
    start_keyboard_block()

    monitors = get_all_monitors()

    if len(monitors) > 1:
        create_overlays(monitors[1:])

    px, py, pw, ph = monitors[0]

    start_fullscreen_monitor(px, py, pw, ph)

    if MAIN_WINDOW:
        try:
            MAIN_WINDOW.show()
            time.sleep(0.3)

            hwnd = _find_bioguard_hwnd()

            if hwnd:
                user32 = ctypes.windll.user32
                user32.ShowWindow(hwnd, 5)
                user32.SetForegroundWindow(hwnd)
                user32.BringWindowToTop(hwnd)

        except Exception as e:
            print("SHOW ERROR:", e)

    if MAIN_API:
        MAIN_API.start_session()

def session_monitor():
    class SessionWatcher:
        def __init__(self):
            message_map = {
                WM_WTSSESSION_CHANGE: self.on_session_change,
            }

            wc = win32gui.WNDCLASS()
            wc.lpfnWndProc = message_map
            wc.lpszClassName = "BioGuardSessionWatcher"

            self.classAtom = win32gui.RegisterClass(wc)

            self.hwnd = win32gui.CreateWindow(
                self.classAtom,
                "BioGuardSessionWatcher",
                0,
                0, 0, 0, 0,
                0, 0, 0, None
            )

            win32ts.WTSRegisterSessionNotification(
                self.hwnd,
                win32ts.NOTIFY_FOR_THIS_SESSION
            )

        def on_session_change(self, hwnd, msg, wparam, lparam):
            if wparam == WTS_SESSION_UNLOCK:
                print("UNLOCK DETECTED")

                if not _find_bioguard_hwnd():
                    os.startfile(sys.argv[0])

            elif wparam == WTS_SESSION_LOCK:
                print("LOCK DETECTED")
                relock_system()

            return 0

    watcher = SessionWatcher()
    win32gui.PumpMessages()



def main():
    hide_taskbar()
    start_keyboard_block()
    

    monitors = get_all_monitors()
    primary  = monitors[0] if monitors else (0, 0, 1920, 1080)
    px, py, pw, ph = primary
    print(f"[primary] x={px} y={py} w={pw} h={ph}")

    if len(monitors) > 1:
        create_overlays(monitors[1:])

    ui_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "ui", "index.html")
    url = "file:///" + ui_path.replace("\\", "/")

    window = webview.create_window(
        "AD BioGuard",
        url=url,
        width=800,
        height=600,
        x=px,
        y=py,
        fullscreen=False,
        frameless=True,
        on_top=True,
        easy_drag=False,
        background_color="#040812",
        min_size=(800, 500),
    )
    
    global MAIN_WINDOW
    MAIN_WINDOW = window

    def _on_closed():
        stop_keyboard_block()
        stop_fullscreen_monitor()
        show_taskbar()
        destroy_overlays()

    window.events.closed += _on_closed

    def _on_shown():
        start_fullscreen_monitor(px, py, pw, ph)

    window.events.shown += _on_shown

    api = BioGuardAPI(window)
    global MAIN_API
    MAIN_API = api
    window.expose(api.get_config)
    window.expose(api.start_session)
    window.expose(api.capture_face)
    window.expose(api.start_face_qr_poll)
    window.expose(api.start_finger_poll)
    window.expose(api.stop_finger_poll)
    window.expose(api.hide_lock)
    window.expose(api.dev_exit)

    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".webview_data")
    os.makedirs(data_dir, exist_ok=True)
    _write_chromium_camera_pref(data_dir)
    threading.Thread(target=session_monitor, daemon=True).start()
    webview.start(
        debug=DEV_MODE,
        private_mode=False,
        storage_path=data_dir,
    )


if __name__ == "__main__":
    main()