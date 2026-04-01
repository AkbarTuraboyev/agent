"""
windows/bioguard_api.py — pywebview JS API (doc bo'yicha to'liq)
"""

import json
import threading
import time

from core.config import USERNAME, DEVICE_UUID, DEV_MODE, DEMO_MODE, API_BASE
from core.cert import is_activated
from core.keyboard import stop_keyboard_block
from core.monitors import stop_fullscreen_monitor
from core.taskbar import show_taskbar
from core.autolock import start_autolock, stop_autolock
from core.offline import verify_offline, has_offline_creds
from windows.overlay import destroy_overlays
from api.client import api_post, api_get, is_online
from api.camera import check_camera


class BioGuardAPI:

    def __init__(self, window_ref):
        self._window     = window_ref
        self._session_id = None
        self._polling    = False
        self._timeout    = 300

    # ── Config ────────────────────────────────────────────────────
    def get_config(self) -> str:
        return json.dumps({
            "username":    USERNAME,
            "pc_id":       DEVICE_UUID,
            "camera_ok":   check_camera(),
            "dev_mode":    DEV_MODE,
            "demo_mode":   DEMO_MODE,
            "activated":   is_activated(),
            "online":      is_online(),
            "has_offline": has_offline_creds(),
        })

    # ── Sessiya (doc 03) ──────────────────────────────────────────
    def start_session(self):
        def _run():
            try:
                data = api_post("/api/agent/session/start/", {
                    "username":  USERNAME,
                    "pc_id":     DEVICE_UUID,
                })
                self._session_id = data.get("session_id", "")
                if "timeout" in data:
                    self._timeout = int(data["timeout"])
                self._js(f"App.onSessionReady('{self._session_id}')")
            except Exception as e:
                self._js(f"App.onError('Session failed: {self._esc(str(e))}')")
        threading.Thread(target=_run, daemon=True).start()

    # ── Yuz — webcam (doc 03) ─────────────────────────────────────
    def capture_face(self, image_b64: str):
        def _run():
            try:
                self._js("App.setStatus('verifying', 'Analyzing face...')")
                data = api_post("/api/face/agent/check/", {
                    "session_id": self._session_id,
                    "username":   USERNAME,
                    "pc_id":      DEVICE_UUID,
                    "image":      image_b64,
                })
                self._handle_auth_result(data)
            except Exception as e:
                self._js(f"App.onFaceRetry('{self._esc(str(e))}')")
        threading.Thread(target=_run, daemon=True).start()

    # ── Yuz — telefon QR (doc 03) ─────────────────────────────────
    def start_face_qr_poll(self):
        if not self._session_id:
            self._js("App.onError('No session')")
            return
        qr_url = f"{API_BASE}/agent/mobile/face/{self._session_id}/"
        self._js(f"App.renderFaceQR('{qr_url}')")
        self._polling = True
        threading.Thread(target=self._face_qr_poll_loop, daemon=True).start()

    def _face_qr_poll_loop(self):
        elapsed, limit = 0, 120
        while self._polling and elapsed < limit:
            try:
                raw    = api_get(f"/api/agent/face/phone/status/{self._session_id}/")
                status = raw if isinstance(raw, str) else raw.get("status", "")
                if status in ("completed", "verified"):
                    self._polling = False
                    self._js("App.onVerified()")
                    return
                elif status == "expired":
                    self._polling = False
                    self._js("App.onQRExpired()")
                    return
                elif status in ("blocked_user", "blocked_device"):
                    self._polling = False
                    self._handle_blocked(status)
                    return
            except Exception:
                pass
            time.sleep(2)
            elapsed += 2
            self._js(f"App.updateFaceTimer({limit - elapsed})")
        if self._polling:
            self._polling = False
            self._js("App.onQRExpired()")

    # ── Barmoq izi — telefon QR (doc 03) ──────────────────────────
    def start_finger_poll(self):
        if not self._session_id:
            self._js("App.onError('No session')")
            return
        qr_url = f"{API_BASE}/agent/mobile/fingerprint/{self._session_id}/"
        self._js(f"App.renderQR('{qr_url}')")
        self._polling = True
        threading.Thread(target=self._poll_loop, daemon=True).start()

    def stop_finger_poll(self):
        self._polling = False

    def _poll_loop(self):
        elapsed, limit = 0, 120
        while self._polling and elapsed < limit:
            try:
                raw    = api_get(f"/api/agent/fingerprint/phone/status/{self._session_id}/")
                status = raw if isinstance(raw, str) else raw.get("status", "")
                if status in ("completed", "verified"):
                    self._polling = False
                    self._js("App.onVerified()")
                    return
                elif status == "expired":
                    self._polling = False
                    self._js("App.onQRExpired()")
                    return
                elif status in ("blocked_user", "blocked_device"):
                    self._polling = False
                    self._handle_blocked(status)
                    return
            except Exception:
                pass
            time.sleep(2)
            elapsed += 2
            self._js(f"App.updateTimer({limit - elapsed})")
        if self._polling:
            self._polling = False
            self._js("App.onQRExpired()")

    # ── Offline login (doc 06) ────────────────────────────────────
    def offline_login(self, username: str, password: str):
        """Internet yo'qda admin AD parol bilan kiradi."""
        def _run():
            if verify_offline(username, password):
                self._js("App.onVerified()")
            else:
                self._js("App.onOfflineRetry('Login yoki parol noto\\'g\\'ri')")
        threading.Thread(target=_run, daemon=True).start()

    # ── Auto-lock (doc 04) ────────────────────────────────────────
    def start_autolock_monitor(self):
        def _on_warn(seconds_left):
            self._js(f"App.onAutolockWarning({seconds_left})")

        def _on_lock():
            from windows.session_monitor import relock_system
            threading.Thread(target=relock_system, daemon=True).start()

        start_autolock(self._timeout, _on_warn, _on_lock)

    def extend_session(self):
        """'Davom etish' — auto-lock timer reset."""
        stop_autolock()
        self.start_autolock_monitor()

    # ── Qulf ochish ───────────────────────────────────────────────
    def hide_lock(self):
        stop_keyboard_block()
        stop_fullscreen_monitor()
        show_taskbar()
        destroy_overlays()
        self._window.hide()
        self.start_autolock_monitor()

    def dev_unlock(self):
        if DEV_MODE:
            self.hide_lock()

    def dev_exit(self):
        if DEV_MODE:
            stop_autolock()
            stop_keyboard_block()
            stop_fullscreen_monitor()
            show_taskbar()
            destroy_overlays()
            self._window.destroy()

    # ── Internal ──────────────────────────────────────────────────
    def _handle_auth_result(self, data: dict):
        """Server javobini qayta ishlaydi (doc 03, 05)."""
        status = data.get("status", "")
        if status == "verified":
            self._js("App.onVerified()")
        elif status == "blocked_user":
            self._js("App.onBlocked('Hisobingiz bloklangan, IT ga murojaat')")
        elif status == "blocked_device":
            self._js("App.onBlocked('Bu qurilma o\\'chirilgan')")
        else:
            msg = self._esc(data.get("detail", "Biometric not recognized"))
            self._js(f"App.onFaceRetry('{msg}')")

    def _handle_blocked(self, status: str):
        if status == "blocked_user":
            self._js("App.onBlocked('Hisobingiz bloklangan, IT ga murojaat')")
        else:
            self._js("App.onBlocked('Bu qurilma o\\'chirilgan')")

    def _js(self, code: str):
        try:
            self._window.evaluate_js(code)
        except Exception:
            pass

    @staticmethod
    def _esc(s: str) -> str:
        return s.replace("'", "\\'").replace("\n", " ")
