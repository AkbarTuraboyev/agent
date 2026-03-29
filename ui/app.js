/**
 * AD BioGuard — Frontend Application
 * Navigation stack: select → face-select / finger-select → action screens
 */

const App = (() => {

  /* ── State ───────────────────────────────────────────────────── */
  let config        = {};
  let cameraStream  = null;
  let currentScreen = 'init';
  let screenStack   = [];   // navigation history for ← Back

  /* ── Boot ────────────────────────────────────────────────────── */
  async function init() {
    startClock();
    await waitForPywebview();

    try {
      const raw = await pywebview.api.get_config();
      config = JSON.parse(raw);
    } catch(e) {
      config = { username: 'demo.user', camera_ok: true,
                 dev_mode: true, demo_mode: true };
    }

    document.getElementById('header-user').textContent =
      config.username.toUpperCase();
    document.getElementById('select-username').textContent =
      `WORKSTATION LOCKED  ·  ${config.username.toUpperCase()}`;

    if (config.demo_mode)
      document.getElementById('header-mode').style.display = 'inline';
    if (config.dev_mode)
      document.getElementById('dev-bar').style.display = 'flex';

    // Face badge — show warning if no camera but keep clickable
    if (!config.camera_ok) {
      document.getElementById('face-badge-text').textContent = 'No Webcam';
      const badge = document.getElementById('face-badge');
      badge.style.color       = 'var(--amber)';
      badge.style.borderColor = 'var(--amber)';
      // webcam sub-card dim
      document.getElementById('webcam-badge-text').textContent = 'Not detected';
      const wb = document.getElementById('webcam-badge');
      wb.style.color       = 'var(--amber)';
      wb.style.borderColor = 'var(--amber)';
      const wc = document.getElementById('card-face-webcam');
      wc.style.opacity = '0.45';
      wc.style.pointerEvents = 'none';
    }

    setInitStatus('Session starting...');
    await callApi('start_session');
  }

  async function waitForPywebview() {
    for (let i = 0; i < 50; i++) {
      if (typeof pywebview !== 'undefined' && pywebview.api) return;
      await sleep(100);
    }
  }

  /* ── Screen navigation ───────────────────────────────────────── */
  function showScreen(name, pushHistory = true) {
    if (pushHistory && currentScreen !== 'init')
      screenStack.push(currentScreen);

    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    const el = document.getElementById(`screen-${name}`);
    if (el) { el.classList.add('active'); currentScreen = name; }
  }

  function goBack() {
    stopCamera();
    callApi('stop_finger_poll');
    const prev = screenStack.pop();
    if (prev) showScreen(prev, false);
    else      showScreen('select', false);
  }

  /* ── Session ────────────────────────────────────────────────────*/
  function onSessionReady(sessionId) {
    setInitStatus('Session established · ' + sessionId.slice(0, 8) + '...');
    sleep(400).then(() => showScreen('select', false));
  }

  /* ── Main method select ──────────────────────────────────────── */
  function selectMethod(method) {
    if (method === 'face')   showScreen('face-select');
    else                     showScreen('finger-select');
  }

  /* ══════════════════════════════════════════════════════════════
     FACE — WEBCAM
  ══════════════════════════════════════════════════════════════ */
  function startFaceWebcam() {
    showScreen('face');
    setFaceStatus('idle', 'Opening camera...');

    if (!config.camera_ok) {
      setFaceStatus('error', 'No webcam detected on this device');
      const wrap = document.querySelector('.cam-wrap');
      if (wrap) wrap.innerHTML = `
        <div style="display:flex;flex-direction:column;align-items:center;
             justify-content:center;height:100%;gap:10px;
             font-family:var(--font-mono);color:var(--text-muted);">
          <div style="font-size:32px;opacity:0.3">⬡</div>
          <div style="font-size:11px;letter-spacing:0.1em;text-transform:uppercase">
            No camera device found</div>
          <div style="font-size:10px;color:var(--text-dim)">
            Connect a webcam or use Phone Camera</div>
        </div>`;
      const btn = document.getElementById('capture-btn');
      if (btn) btn.disabled = true;
      return;
    }

    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' }, audio: false })
      .then(stream => {
        cameraStream = stream;
        const video = document.getElementById('camera-video');
        video.srcObject = stream;
        video.play();
        setFaceStatus('active', 'Camera active — look at the camera');
        const btn = document.getElementById('capture-btn');
        if (btn) btn.disabled = false;
      })
      .catch(err => {
        setFaceStatus('error', 'Camera denied: ' + err.message);
        const btn = document.getElementById('capture-btn');
        if (btn) btn.disabled = true;
      });
  }

  function stopCamera() {
    if (cameraStream) {
      cameraStream.getTracks().forEach(t => t.stop());
      cameraStream = null;
    }
    const video = document.getElementById('camera-video');
    if (video) video.srcObject = null;
  }

  function captureFrame() {
    const video = document.getElementById('camera-video');
    if (!video || !video.srcObject) {
      setFaceStatus('error', 'Camera not ready');
      return;
    }
    const canvas = document.getElementById('camera-canvas');
    canvas.width  = video.videoWidth  || 640;
    canvas.height = video.videoHeight || 480;
    if (!canvas.width || !canvas.height) {
      setFaceStatus('error', 'Frame not ready, try again');
      return;
    }
    const ctx = canvas.getContext('2d');
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0);
    const b64 = canvas.toDataURL('image/jpeg', 0.85).split(',')[1];

    const btn = document.getElementById('capture-btn');
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner"></div> &nbsp; Verifying...';
    setFaceStatus('verifying', 'Analyzing face...');
    stopCamera();
    callApi('capture_face', b64);
  }

  function onFaceRetry(reason) {
    const btn = document.getElementById('capture-btn');
    if (btn) { btn.disabled = false; btn.innerHTML = '⊙ &nbsp; Capture &amp; Verify'; }
    setFaceStatus('error', reason + ' — try again');
    startFaceWebcam();
  }

  function setFaceStatus(state, text) {
    const ind = document.getElementById('face-indicator');
    const txt = document.getElementById('face-status-text');
    if (ind) ind.className = `status-indicator ${state}`;
    if (txt) txt.textContent = text;
  }

  /* ══════════════════════════════════════════════════════════════
     FACE — PHONE QR
  ══════════════════════════════════════════════════════════════ */
  function startFaceQR() {
    showScreen('face-qr');
    const blink  = document.getElementById('face-qr-blink');
    const status = document.getElementById('face-qr-status');
    if (blink)  blink.style.background  = 'var(--amber)';
    if (status) status.textContent = 'Generating QR code...';
    callApi('start_face_qr_poll');
  }

  function renderFaceQR(url) {
    const loading = document.getElementById('face-qr-loading');
    const codeEl  = document.getElementById('face-qr-code');
    if (loading) loading.style.display = 'none';
    if (codeEl) {
      codeEl.style.display = 'block';
      codeEl.innerHTML = '';
      try {
        new QRCode(codeEl, {
          text: url, width: 180, height: 180,
          colorDark: '#0a0f1e', colorLight: '#ffffff',
          correctLevel: QRCode.CorrectLevel.M,
        });
      } catch(e) {
        codeEl.innerHTML = `<div style="font-size:9px;padding:8px;word-break:break-all">${url}</div>`;
      }
    }
    const status = document.getElementById('face-qr-status');
    const blink  = document.getElementById('face-qr-blink');
    if (status) status.textContent = 'Scan with your phone';
    if (blink)  blink.style.background = 'var(--accent)';
    setFaceTimerBar(120);
  }

  function setFaceTimerBar(seconds) {
    const bar   = document.getElementById('face-timer-bar');
    const label = document.getElementById('face-qr-timer');
    if (!bar) return;
    bar.style.transition = 'none';
    bar.style.width = '100%';
    updateFaceTimer(seconds);
  }

  function updateFaceTimer(remaining) {
    const bar   = document.getElementById('face-timer-bar');
    const label = document.getElementById('face-qr-timer');
    if (!bar || !label) return;
    bar.style.transition = 'width 2s linear';
    bar.style.width = Math.max(0, (remaining / 120) * 100) + '%';
    const m = Math.floor(remaining / 60);
    const s = remaining % 60;
    label.textContent = `${m}:${String(s).padStart(2,'0')}`;
    if (remaining < 30) bar.style.background = 'var(--amber)';
    if (remaining < 10) bar.style.background = 'var(--red)';
  }

  /* ══════════════════════════════════════════════════════════════
     FINGERPRINT — QR
  ══════════════════════════════════════════════════════════════ */
  function startFingerQR() {
    showScreen('finger');
    const blink  = document.getElementById('qr-blink');
    const status = document.getElementById('qr-status-text');
    if (blink)  blink.style.background  = 'var(--amber)';
    if (status) status.textContent = 'Generating QR code...';
    callApi('start_finger_poll');
  }

  function renderQR(url) {
    const loading = document.getElementById('qr-loading');
    const codeEl  = document.getElementById('qr-code');
    if (loading) loading.style.display = 'none';
    if (codeEl) {
      codeEl.style.display = 'block';
      codeEl.innerHTML = '';
      try {
        new QRCode(codeEl, {
          text: url, width: 180, height: 180,
          colorDark: '#0a0f1e', colorLight: '#ffffff',
          correctLevel: QRCode.CorrectLevel.M,
        });
      } catch(e) {
        codeEl.innerHTML = `<div style="font-size:9px;padding:8px;word-break:break-all">${url}</div>`;
      }
    }
    const status = document.getElementById('qr-status-text');
    const blink  = document.getElementById('qr-blink');
    if (status) status.textContent = 'Scan with your phone to authenticate';
    if (blink)  blink.style.background = 'var(--accent)';
    setTimerBar(120);
  }

  function setTimerBar(seconds) {
    const bar = document.getElementById('timer-bar');
    if (!bar) return;
    bar.style.background = 'linear-gradient(90deg, var(--accent), var(--cyan))';
    bar.style.transition = 'none';
    bar.style.width = '100%';
    updateTimer(seconds);
  }

  function updateTimer(remaining) {
    const bar   = document.getElementById('timer-bar');
    const label = document.getElementById('qr-timer');
    if (!bar || !label) return;
    bar.style.transition = 'width 2s linear';
    bar.style.width = Math.max(0, (remaining / 120) * 100) + '%';
    const m = Math.floor(remaining / 60);
    const s = remaining % 60;
    label.textContent = `${m}:${String(s).padStart(2,'0')}`;
    if (remaining < 30) bar.style.background = 'var(--amber)';
    if (remaining < 10) bar.style.background = 'var(--red)';
  }

  function onQRExpired() {
    const status = document.getElementById('qr-status-text');
    const blink  = document.getElementById('qr-blink');
    const bar    = document.getElementById('timer-bar');
    if (status) status.textContent = 'QR expired — go back and try again';
    if (blink)  blink.style.background = 'var(--red)';
    if (bar)    { bar.style.width = '0%'; bar.style.background = 'var(--red)'; }
  }

  /* ══════════════════════════════════════════════════════════════
     VERIFIED — any method leads here
  ══════════════════════════════════════════════════════════════ */
  function onVerified() {
    stopCamera();
    callApi('stop_finger_poll');

    const methodMap = {
      'face':       'Face · Webcam',
      'face-qr':    'Face · Phone Camera',
      'finger':     'Fingerprint · Phone',
    };
    const label = methodMap[currentScreen] || 'Biometric';
    document.getElementById('success-method').textContent =
      'Authenticated via ' + label.toUpperCase();

    showScreen('success', false);

    // 2.5s keyin lock screen yashirinadi — overlay (o'yin) davom etaveradi
    sleep(2500).then(() => callApi('hide_lock'));
  }

  /* ── Error ───────────────────────────────────────────────────── */
  function onError(msg) { setInitStatus('Error: ' + msg); }

  /* ── Dev ─────────────────────────────────────────────────────── */
  async function devUnlock() {
    try { await pywebview.api.dev_unlock(); }
    catch(e) { onVerified(); }
  }
  async function devExit() {
    try { await pywebview.api.dev_exit(); }
    catch(e) { window.close(); }
  }

  /* ── Clock ───────────────────────────────────────────────────── */
  function startClock() {
    const el = document.getElementById('header-clock');
    const tick = () => {
      el.textContent = new Date().toLocaleTimeString('en-GB',
        { hour:'2-digit', minute:'2-digit', second:'2-digit' });
    };
    tick(); setInterval(tick, 1000);
  }

  /* ── Helpers ─────────────────────────────────────────────────── */
  function setInitStatus(text) {
    const el = document.getElementById('init-status');
    if (el) el.textContent = text;
  }

  function setStatus(state, text) { setFaceStatus(state, text); }

  async function callApi(method, ...args) {
    try {
      if (typeof pywebview !== 'undefined' && pywebview.api)
        return await pywebview.api[method](...args);
    } catch(e) { console.warn('API:', method, e); }
  }

  function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

  /* ── Boot ────────────────────────────────────────────────────── */
  window.addEventListener('DOMContentLoaded', init);

  /* ── Public ──────────────────────────────────────────────────── */
  return {
    // called by Python
    onSessionReady, onFaceRetry, onVerified, onError,
    renderQR, renderFaceQR,
    updateTimer, updateFaceTimer,
    onQRExpired, setStatus,
    // called by HTML
    selectMethod,
    startFaceWebcam, startFaceQR,
    startFingerQR,
    captureFrame, goBack,
    devUnlock, devExit,
  };

})();