"""
windows/bioguard_api.py — pywebview JS API klassi (BioGuardAPI).

JavaScript tomonidan chaqiriladigan barcha metodlar shu yerda joylashgan.
"""

import json
import threading
import time

from core.config import USERNAME, DEV_MODE, API_BASE
from core.keyboard import stop_keyboard_block
from core.monitors import stop_fullscreen_monitor
from core.taskbar import show_taskbar
from windows.overlay import destroy_overlays
from api.client import api_post, api_get
from api.camera import check_camera


class BioGuardAPI:
    """pywebview orqali JavaScript bilan bog'liq barcha amallar."""

    def __init__(self, window_ref):
        self._window     = window_ref
        self._session_id = None
        self._polling    = False

    # ── Konfiguratsiya ────────────────────────────────────────────
    def get_config(self) -> str:
        return json.dumps({
            "username":  USERNAME,
            "camera_ok": check_camera(),
            "dev_mode":  DEV_MODE,
        })

    # ── Sessiya ───────────────────────────────────────────────────
    def start_session(self):
        def _run():
            try:
                data = api_post("/api/agent/session/start/", {"username": USERNAME})
                self._session_id = data.get("session_id", "")
                self._js(f"App.onSessionReady('{self._session_id}')")
            except Exception as e:
                self._js(f"App.onError('Session failed: {self._esc(str(e))}')")
        threading.Thread(target=_run, daemon=True).start()

    # ── Yuz tanish (kamera orqali) ────────────────────────────────
    def capture_face(self, image_b64: str):
        def _run():
            try:
                self._js("App.setStatus('verifying', 'Analyzing face...')")
                data = api_post("/api/face/agent/check/", {
                    "session_id": self._session_id,
                    "username":   USERNAME,
                    "image":      image_b64,
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

    # ── Yuz tanish (QR / telefon orqali) ─────────────────────────
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
            except Exception:
                pass
            time.sleep(2)
            elapsed += 2
            self._js(f"App.updateFaceTimer({limit - elapsed})")
        if self._polling:
            self._polling = False
            self._js("App.onQRExpired()")

    # ── Barmoq izi (QR / telefon orqali) ─────────────────────────
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
            except Exception:
                pass
            time.sleep(2)
            elapsed += 2
            self._js(f"App.updateTimer({limit - elapsed})")
        if self._polling:
            self._polling = False
            self._js("App.onQRExpired()")

    # ── Qulfni ochish / chiqish ───────────────────────────────────
    def hide_lock(self):
        """Qulfni yashiradi va tizimni normal holatga qaytaradi."""
        stop_keyboard_block()
        stop_fullscreen_monitor()
        show_taskbar()
        destroy_overlays()
        self._window.hide()

    def dev_exit(self):
        """DEV rejimida — hammani to'liq yopadi (debug uchun)."""
        if DEV_MODE:
            stop_keyboard_block()
            stop_fullscreen_monitor()
            show_taskbar()
            destroy_overlays()
            self._window.destroy()

    # ── Yordamchi metodlar ────────────────────────────────────────
    def _js(self, code: str):
        try:
            self._window.evaluate_js(code)
        except Exception:
            pass

    @staticmethod
    def _esc(s: str) -> str:
        return s.replace("'", "\\'").replace("\n", " ")
