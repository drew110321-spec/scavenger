"""
WiFi Prank Messenger — runs entirely on your phone.

Requirements (phone only):
    pip install flask          (in Termux or any Python terminal app)

── Start the server on your phone ────────────────────────────────────
    python3 messenger.py

── Two URLs will be printed ──────────────────────────────────────────
    PC page  →  http://<your-phone-ip>:5001/
    Send page→  http://<your-phone-ip>:5001/send

Step 1: Trick your friend into opening the PC URL in their browser.
        (Send them a "link to a game", "check this out", etc.)
        The page looks completely blank — nothing to see.

Step 2: When you're ready, open the Send URL on your own phone,
        type a message and hit Send.
        → The message BLASTS onto their screen out of nowhere.
"""

import socket
import threading
import time
from flask import Flask, request, jsonify, render_template_string

app      = Flask(__name__)
PORT     = 5001
_pending = []          # messages waiting to be picked up by PC page
_lock    = threading.Lock()


def _local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


# ── PC page — looks like a blank white page ────────────────────────────────────
# Secretly polls /poll every 2 seconds. When a message arrives it takes over
# the entire screen dramatically.

PC_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Loading…</title>
  <style>
    body { margin: 0; background: #fff; font-family: sans-serif; }

    /* Fullscreen overlay — hidden until a message arrives */
    #overlay {
      display: none;
      position: fixed; inset: 0;
      background: #0f172a;
      z-index: 9999;
      align-items: center;
      justify-content: center;
      flex-direction: column;
      text-align: center;
      padding: 40px;
      animation: fadeIn .4s ease;
    }
    #overlay.show { display: flex; }

    @keyframes fadeIn { from { opacity: 0; transform: scale(.95); } to { opacity: 1; transform: scale(1); } }

    #from {
      font-size: 1rem;
      color: #38bdf8;
      letter-spacing: .1em;
      text-transform: uppercase;
      margin-bottom: 24px;
    }
    #text {
      font-size: clamp(1.8rem, 5vw, 3.5rem);
      color: #f1f5f9;
      font-weight: 700;
      line-height: 1.3;
      max-width: 800px;
      word-break: break-word;
      animation: pulse 1.5s ease infinite;
    }
    @keyframes pulse {
      0%,100% { text-shadow: 0 0 20px #38bdf8; }
      50%      { text-shadow: 0 0 60px #38bdf8, 0 0 120px #0ea5e9; }
    }
    #close {
      margin-top: 48px;
      padding: 12px 32px;
      background: transparent;
      border: 1px solid #334155;
      border-radius: 8px;
      color: #64748b;
      font-size: .9rem;
      cursor: pointer;
    }
    #close:hover { border-color: #64748b; color: #94a3b8; }
  </style>
</head>
<body>

<div id="overlay">
  <div id="from"></div>
  <div id="text"></div>
  <button id="close" onclick="dismiss()">dismiss</button>
</div>

<script>
  let seq = 0;

  async function poll() {
    try {
      const r = await fetch('/poll?seq=' + seq);
      if (r.ok) {
        const d = await r.json();
        if (d.msg) {
          seq = d.seq;
          show(d.from, d.msg);
        }
      }
    } catch (_) {}
    setTimeout(poll, 2000);
  }

  function show(from, msg) {
    document.getElementById('from').textContent = from ? '📨  from ' + from : '📨  new message';
    document.getElementById('text').textContent = msg;
    document.getElementById('overlay').classList.add('show');
    // Also try a browser notification (only works if user granted permission before)
    if (Notification && Notification.permission === 'granted') {
      new Notification(from || 'New message', { body: msg });
    }
  }

  function dismiss() {
    document.getElementById('overlay').classList.remove('show');
  }

  poll();
</script>
</body>
</html>"""


# ── Sender page — what YOU open on your phone ──────────────────────────────────

SEND_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Send Prank</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #0f172a; color: #e2e8f0;
      min-height: 100vh; display: flex;
      align-items: center; justify-content: center; padding: 24px;
    }
    .card {
      background: #1e293b; border-radius: 16px;
      padding: 28px 24px; width: 100%; max-width: 420px;
    }
    h1    { font-size: 1.3rem; color: #38bdf8; margin-bottom: 4px; }
    p.sub { font-size: .8rem; color: #64748b; margin-bottom: 20px; }
    label { display:block; font-size:.8rem; color:#94a3b8; margin: 12px 0 5px; }
    input, textarea {
      width: 100%; background: #0f172a; border: 1px solid #334155;
      border-radius: 8px; color: #e2e8f0; font-size: 1rem;
      padding: 10px 14px; outline: none; transition: border-color .2s; resize: vertical;
    }
    input:focus, textarea:focus { border-color: #38bdf8; }
    textarea { min-height: 120px; font-family: inherit; }
    button {
      margin-top: 18px; width: 100%; padding: 14px;
      background: #dc2626; color: #fff; border: none;
      border-radius: 8px; font-size: 1.1rem; font-weight: 700;
      cursor: pointer; letter-spacing: .03em;
      transition: background .15s, transform .1s;
    }
    button:hover   { background: #b91c1c; }
    button:active  { transform: scale(.98); }
    button:disabled{ background: #334155; cursor: default; }
    #st { margin-top: 14px; font-size: .9rem; text-align: center; min-height: 1.2em; }
    .ok { color: #4ade80; } .er { color: #f87171; }
  </style>
</head>
<body>
<div class="card">
  <h1>😈 Prank Control</h1>
  <p class="sub">Your friend has NO idea what's coming</p>

  <label>Your name (shown on their screen)</label>
  <input id="name" type="text" placeholder="optional"/>

  <label>Message</label>
  <textarea id="msg" placeholder="Type the message that will take over their screen…"></textarea>

  <button id="btn" onclick="blast()">💥 BLAST IT</button>
  <div id="st"></div>
</div>
<script>
  async function blast() {
    const name = document.getElementById('name').value.trim();
    const msg  = document.getElementById('msg').value.trim();
    const st   = document.getElementById('st');
    const btn  = document.getElementById('btn');
    if (!msg) { st.textContent='Write something first!'; st.className='er'; return; }
    btn.disabled = true;
    st.textContent='Sending…'; st.className='';
    try {
      const r = await fetch('/message', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({name, message: msg})
      });
      if (r.ok) {
        document.getElementById('msg').value='';
        st.textContent='💥 SENT — watch their face!'; st.className='ok';
      } else { st.textContent='Error, try again.'; st.className='er'; }
    } catch { st.textContent='Cannot reach server.'; st.className='er'; }
    btn.disabled=false;
    setTimeout(()=>{ st.textContent=''; st.className=''; }, 5000);
  }
</script>
</body>
</html>"""


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def pc_page():
    return render_template_string(PC_PAGE)


@app.route("/send")
def send_page():
    return render_template_string(SEND_PAGE)


@app.route("/message", methods=["POST"])
def push_message():
    data = request.get_json(force=True, silent=True) or {}
    text = (data.get("message") or "").strip()
    name = (data.get("name")    or "").strip()
    if text:
        with _lock:
            _pending.append({"seq": len(_pending) + 1, "from": name, "msg": text})
    return jsonify({"ok": bool(text)})


@app.route("/poll")
def poll():
    """PC page polls this — returns the latest unread message if any."""
    try:
        client_seq = int(request.args.get("seq", 0))
    except ValueError:
        client_seq = 0

    with _lock:
        for item in reversed(_pending):
            if item["seq"] > client_seq:
                return jsonify(item)

    return jsonify({"msg": None})


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import logging
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    ip = _local_ip()
    print()
    print("  Prank Messenger running!")
    print("  " + "─" * 42)
    print(f"  1. Send this to your friend (PC):  http://{ip}:{PORT}/")
    print(f"     (tell them it's a game/video/anything)")
    print()
    print(f"  2. Open this on YOUR phone to send: http://{ip}:{PORT}/send")
    print("  " + "─" * 42)
    print("  Ctrl+C to stop.\n")

    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
