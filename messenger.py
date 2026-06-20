"""
Prank Messenger — fires real OS corner notifications on the PC.
Deployed on Render, controlled from iPhone Safari. Nothing on the PC
except a browser tab.

Deploy: connect this repo on render.com → New Blueprint → it reads render.yaml
        and creates the "prank-messenger" service automatically.

Then:
  PC page   → https://<app>.onrender.com/       (send to your friend)
  Send page → https://<app>.onrender.com/send   (open on your iPhone)
"""

import os
import threading
from flask import Flask, request, jsonify, render_template_string

app   = Flask(__name__)
_lock = threading.Lock()
_msgs = []


# ── PC page ────────────────────────────────────────────────────────────────────
# Looks like a harmless "enable to continue" loading screen.
# Step 1: friend clicks the button → browser asks for notification permission.
# Step 2: they click Allow → page goes blank and silently polls every 3 s.
# Step 3: you send → real OS notification pops in their bottom corner.

PC_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Loading…</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: #fff; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }

    /* Fake "loading" prompt shown before permission is granted */
    #gate {
      position: fixed; inset: 0;
      display: flex; flex-direction: column;
      align-items: center; justify-content: center; gap: 18px;
      background: #fff;
    }
    #gate svg { width: 56px; height: 56px; color: #94a3b8; }
    #gate p { color: #64748b; font-size: .95rem; }
    #gate button {
      padding: 11px 28px;
      background: #0ea5e9; color: #fff;
      border: none; border-radius: 8px;
      font-size: 1rem; font-weight: 600; cursor: pointer;
    }
    #gate button:hover { background: #0284c7; }

    /* Shown when they deny permission */
    #denied {
      display: none;
      position: fixed; inset: 0;
      align-items: center; justify-content: center;
      background: #fff;
    }
    #denied p { color: #94a3b8; font-size: .9rem; }
  </style>
</head>
<body>

<!-- Step 1: visible until permission granted -->
<div id="gate">
  <!-- generic bell icon -->
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"
       stroke-linecap="round" stroke-linejoin="round">
    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
    <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
  </svg>
  <p>Enable notifications to continue</p>
  <button onclick="askPermission()">Enable &amp; Continue</button>
</div>

<div id="denied"><p>Notifications blocked. Reload the page and click Allow.</p></div>

<script>
var seq = 0;

function askPermission() {
  if (!('Notification' in window)) {
    // Browser doesn't support it — fall back to inline alert
    document.getElementById('gate').style.display = 'none';
    startPolling();
    return;
  }
  Notification.requestPermission().then(function(result) {
    if (result === 'granted') {
      document.getElementById('gate').style.display = 'none';
      startPolling();
    } else {
      document.getElementById('gate').style.display = 'none';
      document.getElementById('denied').style.display = 'flex';
    }
  });
}

// If they've already granted permission in a previous visit, skip the gate
if (window.Notification && Notification.permission === 'granted') {
  document.getElementById('gate').style.display = 'none';
  startPolling();
}

function startPolling() {
  poll();
}

function poll() {
  fetch('/poll?seq=' + seq)
    .then(function(r){ return r.json(); })
    .then(function(d){
      if (d.msg) {
        seq = d.seq;
        fire(d.from, d.msg);
      }
    })
    .catch(function(){})
    .finally(function(){ setTimeout(poll, 3000); });
}

function fire(from, msg) {
  var title = from ? from : 'New Message';
  var n = new Notification(title, {
    body: msg,
    icon: 'https://em-content.zobj.net/source/apple/391/speech-balloon_1f4ac.png',
    requireInteraction: false   // auto-dismiss after a few seconds
  });
  // clicking the notification focuses the tab (harmless)
  n.onclick = function(){ window.focus(); n.close(); };
}
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
    label { display: block; font-size: .8rem; color: #94a3b8; margin: 12px 0 5px; }
    input, textarea {
      width: 100%; background: #0f172a; border: 1px solid #334155;
      border-radius: 8px; color: #e2e8f0; font-size: 1rem;
      padding: 10px 14px; outline: none; transition: border-color .2s; resize: vertical;
    }
    input:focus, textarea:focus { border-color: #38bdf8; }
    textarea { min-height: 100px; font-family: inherit; }
    button {
      margin-top: 18px; width: 100%; padding: 14px;
      background: #0ea5e9; color: #fff; border: none;
      border-radius: 8px; font-size: 1rem; font-weight: 700;
      cursor: pointer; transition: background .15s, transform .1s;
    }
    button:hover    { background: #0284c7; }
    button:active   { transform: scale(.98); }
    button:disabled { background: #334155; cursor: default; }
    #st { margin-top: 14px; font-size: .9rem; text-align: center; min-height: 1.2em; }
    .ok { color: #4ade80; } .er { color: #f87171; }
  </style>
</head>
<body>
<div class="card">
  <h1>Send a notification</h1>
  <p class="sub">Pops up in the corner of their PC</p>

  <label>From (appears as notification title)</label>
  <input id="name" type="text" placeholder="e.g. Your name, or leave blank"/>

  <label>Message</label>
  <textarea id="msg" placeholder="What should pop up on their screen?"></textarea>

  <button id="btn" onclick="send()">Send</button>
  <div id="st"></div>
</div>
<script>
  async function send() {
    var name = document.getElementById('name').value.trim();
    var msg  = document.getElementById('msg').value.trim();
    var st   = document.getElementById('st');
    var btn  = document.getElementById('btn');
    if (!msg) { st.textContent = 'Write a message first.'; st.className = 'er'; return; }
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
        st.textContent = 'Sent!'; st.className = 'ok';
      } else { st.textContent = 'Error, try again.'; st.className = 'er'; }
    } catch(e) { st.textContent = 'Cannot reach server.'; st.className = 'er'; }
    btn.disabled = false;
    setTimeout(function(){ st.textContent = ''; st.className = ''; }, 4000);
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
    try:
        client_seq = int(request.args.get("seq", 0))
    except ValueError:
        client_seq = 0
    with _lock:
        for item in reversed(_msgs):
            if item["seq"] > client_seq:
                return jsonify(item)
    return jsonify({"msg": None})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)
