#!/usr/bin/env python3
"""
Q-Napse RFC 8910 Zero-Internet Captive SOS Portal & WebAudio LFM Chirp Homing Server
Run on Qualcomm QRB2210: python3 mpu-qrb2210/captive_sos/server.py
"""
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

app = FastAPI(title="Q-Napse RFC 8910 Captive SOS Triage Node")
TRIAGE_LOG = []

CAPTIVE_SOS_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Q-NAPSE // Emergency Search & Rescue Triage</title>
<style>
  body { background:#0b0f19; color:#f8fafc; font-family:system-ui,sans-serif; text-align:center; padding:18px; margin:0; }
  .card { max-width:420px; margin:auto; background:#111827; border:2px solid #ef4444; border-radius:14px; padding:20px; }
  h1 { color:#ef4444; font-size:1.35rem; margin-top:0; }
  .btn { display:block; width:100%; padding:16px; margin:12px 0; font-size:1.05rem; font-weight:700; border:none; border-radius:10px; cursor:pointer; color:#fff; }
  .crit { background:#dc2626; } .pin { background:#d97706; } .stab { background:#16a34a; }
  #status { margin-top:14px; font-size:0.95rem; color:#38bdf8; font-weight:600; }
</style>
</head>
<body>
  <div class="card">
    <h1>⚠️ Q-NAPSE DISASTER RESCUE BEACON</h1>
    <p>Your phone is connected to an offline Search & Rescue Triage Pod. Tap your status to emit an acoustic homing chirp:</p>
    <button class="btn crit" onclick="sendTriage('CRITICAL_INJURY')">🔴 CRITICAL / BLEEDING</button>
    <button class="btn pin" onclick="sendTriage('TRAPPED_UNDER_DEBRIS')">🟡 PINNED / TRAPPED IN RUBBLE</button>
    <button class="btn stab" onclick="sendTriage('STABLE_AWAITING_RESCUE')">🟢 STABLE / UNINJURED</button>
    <div id="status">Standby — Select Triage Status</div>
  </div>
<script>
function playLfmHomingChirp() {
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = 'sine';
  osc.frequency.setValueAtTime(2000, ctx.currentTime);
  osc.frequency.linearRampToValueAtTime(4200, ctx.currentTime + 0.25);
  gain.gain.setValueAtTime(1.0, ctx.currentTime);
  osc.connect(gain); gain.connect(ctx.destination);
  osc.start(); osc.stop(ctx.currentTime + 0.25);
}

async function sendTriage(state) {
  playLfmHomingChirp();
  setInterval(playLfmHomingChirp, 1500);
  const res = await fetch('/api/triage', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ status: state, ua: navigator.userAgent })
  });
  const data = await res.json();
  document.getElementById('status').innerText =
    '✅ BEACON LOCKED (' + data.timestamp + ') — Emitting 2.0-4.2kHz FrFT Homing Chirp...';
}
</script>
</body>
</html>
"""


@app.get("/api/captive-portal")
async def rfc8910_captive_api():
    return JSONResponse({
        "captive": True,
        "user-portal-url": "http://10.42.0.1:8080/",
        "venue-info-url": "http://10.42.0.1:8080/"
    })


@app.get("/", response_class=HTMLResponse)
@app.get("/generate_204", response_class=HTMLResponse)
@app.get("/hotspot-detect.html", response_class=HTMLResponse)
async def captive_landing():
    return CAPTIVE_SOS_HTML


@app.post("/api/triage")
async def record_triage(req: Request):
    payload = await req.json()
    entry = {
        "client_ip": req.client.host if req.client else "unknown",
        "status": payload.get("status", "UNKNOWN"),
        "timestamp": datetime.utcnow().strftime("%H:%M:%S UTC"),
    }
    TRIAGE_LOG.append(entry)
    print(f"[Q-Napse CAPTIVE SOS ALERT] {entry}")
    return entry


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
