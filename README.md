# AD BioGuard — Desktop Biometric Lock Agent

Premium fullscreen biometric authentication terminal built with
Python + pywebview + HTML/CSS/JS.

## Structure

```
agent/
├── main.py            ← Python backend (pywebview + API calls)
├── requirements.txt
└── ui/
    ├── index.html     ← UI shell + screen markup
    ├── style.css      ← Premium dark enterprise styling
    └── app.js         ← Frontend state machine
```

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Config (top of main.py)

| Variable    | Default               | Description                        |
|-------------|-----------------------|------------------------------------|
| `API_BASE`  | `http://localhost:8000` | Backend server URL               |
| `DEV_MODE`  | `True`                | Show dev controls (simulate/exit)  |
| `DEMO_MODE` | `True`                | Use mock API (no server needed)    |

Set `DEMO_MODE = False` when real backend is ready.

## Flow

```
Fullscreen launches
    ↓
Session created  →  Method selection screen
    ↓
User picks ONE:
  ┌─────────────────┐    ┌─────────────────┐
  │   ⬡ Face Scan  │ OR │ ◈ Fingerprint   │
  └─────────────────┘    └─────────────────┘
         ↓                       ↓
  Webcam capture          QR code + polling
  → POST /api/face/       → phone scans QR
    agent/check/          → backend confirms
         ↓                       ↓
         └──────── verified ─────┘
                      ↓
              Success screen
                      ↓
              Window closes
```

## Backend endpoints expected

```
POST /api/agent/session/start/
     body: { username }
     resp: { session_id }

POST /api/face/agent/check/
     body: { session_id, username, image }  ← base64 JPEG
     resp: { status: "verified" | "mismatch" | "not_found" }

GET  /api/fingerprint/phone/status/{session_id}/
     resp: "pending" | "completed" | "expired"
```
# agent
