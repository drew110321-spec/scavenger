"""
Prank Messenger — deployed on Render, works from any browser.

No installs needed anywhere. Two URLs, that's it:

  PC page   →  https://<your-render-app>.onrender.com/
               Send this to your friend (looks like a blank page).

  Send page →  https://<your-render-app>.onrender.com/send
               Open this on your iPhone to fire the message.

When you hit Send, their entire screen gets taken over.
"""

import os
import threading
from flask import Flask, request, jsonify, render_template_string

app   = Flask(__name__)
_lock = threading.Lock()
_msgs = []   # in-memory list of {seq, from, msg}


# ── PC receiver page ───────────────────────────────────────────────────────────
# Looks 100% blank. Polls /poll every 2 seconds. When a message arrives it
# takes over the full screen with a glowing fullscreen overlay.

PC_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Loading…</title>
  <style>
    body { margin: 0; background: #fff; }

    #overlay {
      display: none;
      position: fixed; inset: 0;
      background: #0f172a;
      z-index: 9999;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      padding: 40px;
      animation: pop .35s cubic-bezier(.22,1,.36,1);
    }
    #overlay.show { display: flex; }

    @keyframes pop {
      from { opacity: 0; transform: scale(.92); }
      to   { opacity: 1; transform: scale(1); }
    }

    #from {
      font-family: -apple-system, sans-serif;
      font-size: 1rem;
      color: #38bdf8;
      letter-spacing: .12em;
      text-transform: uppercase;
      margin-bottom: 28px;
    }
    #text {
      font-family: -apple-system, sans-serif;
      font-size: clamp(2rem, 6vw, 4rem);
      font-weight: 800;
      color: #f1f5f9;
      line-height: 1.25;
      max-width: 820px;
      word-break: break-word;
      animation: glow 2s ease-in-out infinite;
    }
    @keyframes glow {
      0%,100% { text-shadow: 0 0 20px #38bdf8; }
      50%      { text-shadow: 0 0 80px #38bdf8, 0 0 160px #0ea5e9; }
    }
    #dismiss {
      margin-top: 56px;
      padding: 10px 28px;
      background: transparent;
      border: 1px solid #334155;
      border-radius: 8px;
      color: #475569;
      font-size: .85rem;
      font-family: -apple-system, sans-serif;
      cursor: pointer;
    }
    #dismiss:hover { border-color: #64748b; color: #94a3b8; }
  </style>
</head>
<body>
<div id="overlay">
  <div id="from"></div>
  <div id="text"></div>
  <button id="dismiss" onclick="close_()">dismiss</button>
</div>
<script>
  var seq = 0;

  function poll() {
    fetch('/poll?seq=' + seq)
      .then(r => r.json())
      .then(d => { if (d.msg) { seq = d.seq; show(d.from, d.msg); } })
      .catch(function(){})
      .finally(function(){ setTimeout(poll, 2000); });
  }

  function show(from, msg) {
    document.getElementById('from').textContent = from ? '📨  from ' + from : '📨  new message';
    document.getElementById('text').textContent = msg;
    document.getElementById('overlay').classList.add('show');
  }

  function close_() {
    document.getElementById('overlay').classList.remove('show');
  }

  poll();
</script>
</body>
</html>"""


# ── iPhone sender page ─────────────────────────────────────────────────────────

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
  <p class="sub">They have absolutely no idea</p>

  <label>Your name (shows on their screen)</label>
  <input id="name" type="text" placeholder="optional"/>

  <label>Message</label>
  <textarea id="msg" placeholder="Type what will take over their screen…"></textarea>

  <button id="btn" onclick="blast()">💥 BLAST IT</button>
  <div id="st"></div>
</div>
<script>
  async function blast() {
    var name = document.getElementById('name').value.trim();
    var msg  = document.getElementById('msg').value.trim();
    var st   = document.getElementById('st');
    var btn  = document.getElementById('btn');
    if (!msg) { st.textContent='Write something first!'; st.className='er'; return; }
    btn.disabled = true;
    st.textContent = 'Sending…'; st.className = '';
    try {
      var r = await fetch('/message', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name: name, message: msg})
      });
      if (r.ok) {
        document.getElementById('msg').value = '';
        st.textContent = '💥 SENT — watch their face!'; st.className = 'ok';
      } else { st.textContent = 'Error, try again.'; st.className = 'er'; }
    } catch(e) { st.textContent = 'Cannot reach server.'; st.className = 'er'; }
    btn.disabled = false;
    setTimeout(function(){ st.textContent=''; st.className=''; }, 5000);
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
            _msgs.append({"seq": len(_msgs) + 1, "from": name, "msg": text})
    return jsonify({"ok": bool(text)})


@app.route("/poll")
def poll():
    """PC page calls this every 2 s to check for new messages."""
    try:
        client_seq = int(request.args.get("seq", 0))
    except ValueError:
        client_seq = 0

    with _lock:
        for item in reversed(_msgs):
            if item["seq"] > client_seq:
                return jsonify(item)

    return jsonify({"msg": None})


# ── Local dev entry point ──────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)
