"""
WiFi Prank Messenger

Run this secretly on your friend's PC first, then send a message from
your phone — a window will suddenly pop up on their screen.

Setup (run this once on the PC):
    pip install flask

Start it on the PC (no window appears yet):
    Windows  →  pythonw messenger.py          (totally invisible)
    Mac/Linux→  python3 messenger.py &        (runs in background)

Get the phone URL:
    python3 messenger.py --ip
    Then open  http://<that-ip>:5001  on your phone.
"""

import sys
import os
import socket
import threading
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
import tkinter as tk
import logging


PORT = 5001


def _local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


# ── Phone web UI ───────────────────────────────────────────────────────────────

PHONE_UI = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Send Message</title>
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
      box-shadow: 0 20px 60px rgba(0,0,0,.5);
    }
    h1    { font-size: 1.4rem; margin-bottom: 6px; color: #38bdf8; }
    p.sub { font-size: .85rem; color: #64748b; margin-bottom: 20px; }
    label { display:block; font-size:.8rem; color:#94a3b8; margin: 14px 0 6px; }
    input, textarea {
      width: 100%; background: #0f172a; border: 1px solid #334155;
      border-radius: 8px; color: #e2e8f0; font-size: 1rem;
      padding: 10px 14px; outline: none; transition: border-color .2s; resize: vertical;
    }
    input:focus, textarea:focus { border-color: #38bdf8; }
    textarea { min-height: 110px; font-family: inherit; }
    button {
      margin-top: 20px; width: 100%; padding: 13px;
      background: #0ea5e9; color: #fff; border: none;
      border-radius: 8px; font-size: 1rem; font-weight: 600;
      cursor: pointer; transition: background .2s, transform .1s;
    }
    button:hover   { background: #0284c7; }
    button:active  { transform: scale(.98); }
    button:disabled{ background: #334155; cursor: default; }
    #st { margin-top: 14px; font-size: .9rem; text-align: center; min-height: 1.2em; }
    .ok { color: #4ade80; } .er { color: #f87171; }
  </style>
</head>
<body>
<div class="card">
  <h1>&#128172; Send to PC</h1>
  <p class="sub">They have no idea &#128516;</p>

  <label for="name">From (optional)</label>
  <input id="name" type="text" placeholder="Your name" maxlength="40"/>

  <label for="msg">Message</label>
  <textarea id="msg" placeholder="Type your prank message…"></textarea>

  <button id="btn" onclick="send()">Send &#9654;</button>
  <div id="st"></div>
</div>
<script>
  async function send() {
    const name = document.getElementById('name').value.trim();
    const msg  = document.getElementById('msg').value.trim();
    const st   = document.getElementById('st');
    const btn  = document.getElementById('btn');
    if (!msg) { st.textContent='Type something first.'; st.className='er'; return; }
    btn.disabled = true;
    st.textContent = 'Sending…'; st.className = '';
    try {
      const r = await fetch('/send', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name, message: msg})
      });
      if (r.ok) {
        document.getElementById('msg').value = '';
        st.textContent = '✓ Sent! Watch their reaction 😂'; st.className = 'ok';
      } else { st.textContent='Error. Try again.'; st.className='er'; }
    } catch { st.textContent='Cannot reach PC — same WiFi?'; st.className='er'; }
    btn.disabled = false;
    setTimeout(()=>{ st.textContent=''; st.className=''; }, 4000);
  }
  document.getElementById('msg').addEventListener('keydown', e => {
    if (e.key==='Enter' && (e.ctrlKey||e.metaKey)) send();
  });
</script>
</body>
</html>"""


# ── Pop-up window ──────────────────────────────────────────────────────────────

class PopupMessenger:
    """
    Stays invisible until the first message arrives, then suddenly
    pops up on screen. Each new message flashes the window to the front.
    """

    WIDTH  = 340
    HEIGHT = 180   # grows with messages
    MARGIN = 20

    def __init__(self):
        self._messages = []
        self._root     = None
        self._visible  = False
        self._frame    = None

    def push(self, sender: str, text: str):
        ts = datetime.now().strftime("%H:%M")
        self._messages.append((ts, sender, text))
        if self._root:
            self._root.after(0, self._show_or_update)

    def _show_or_update(self):
        if not self._visible:
            self._position()
            self._root.deiconify()            # appear from nowhere
            self._root.attributes("-topmost", True)
            self._root.lift()
            self._visible = True
        else:
            # flash to front on every new message
            self._root.attributes("-topmost", True)
            self._root.lift()
        self._rebuild()

    def _position(self):
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        x  = sw - self.WIDTH  - self.MARGIN
        y  = sh - self.HEIGHT - self.MARGIN - 40   # above taskbar
        self._root.geometry(f"{self.WIDTH}x{self.HEIGHT}+{x}+{y}")

    def _rebuild(self):
        for w in self._frame.winfo_children():
            w.destroy()

        for ts, sender, text in reversed(self._messages[-5:]):
            row = tk.Frame(self._frame, bg="#1e293b", padx=10, pady=6)
            row.pack(fill="x", pady=2)

            tk.Label(
                row, text=f"{sender}  ·  {ts}",
                bg="#1e293b", fg="#64748b", font=("Helvetica", 8),
                anchor="w"
            ).pack(fill="x")

            tk.Label(
                row, text=text,
                bg="#1e293b", fg="#f1f5f9", font=("Helvetica", 11),
                wraplength=self.WIDTH - 30, justify="left", anchor="w"
            ).pack(fill="x")

        # Resize window height to fit content
        self._root.update_idletasks()
        needed = self._frame.winfo_reqheight() + 46   # 46 = header height
        self._root.geometry(f"{self.WIDTH}x{needed}")

    def run(self):
        root = tk.Tk()
        self._root = root

        root.title("Message")
        root.overrideredirect(True)      # no title bar
        root.configure(bg="#0f172a")
        root.withdraw()                  # HIDDEN at startup — nothing visible yet

        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(root, bg="#0ea5e9", pady=6)
        hdr.pack(fill="x")

        tk.Label(
            hdr, text="  📨  New Message",
            bg="#0ea5e9", fg="white", font=("Helvetica", 11, "bold")
        ).pack(side="left")

        x_btn = tk.Label(
            hdr, text="  ✕  ", bg="#0ea5e9", fg="white",
            font=("Helvetica", 11), cursor="hand2"
        )
        x_btn.pack(side="right")
        x_btn.bind("<Button-1>", lambda _: self._dismiss())

        # Drag support
        def _ds(e): root._dx, root._dy = e.x, e.y
        def _dm(e):
            root.geometry(f"+{root.winfo_x()+e.x-root._dx}+{root.winfo_y()+e.y-root._dy}")
        hdr.bind("<Button-1>", _ds)
        hdr.bind("<B1-Motion>", _dm)

        # ── Message area ──────────────────────────────────────────────────────
        self._frame = tk.Frame(root, bg="#0f172a")
        self._frame.pack(fill="both", expand=True, pady=(4, 8))

        root.mainloop()

    def _dismiss(self):
        self._root.withdraw()
        self._visible  = False
        self._messages = []


# ── Flask server ───────────────────────────────────────────────────────────────

popup = PopupMessenger()
app   = Flask(__name__)

logging.getLogger("werkzeug").setLevel(logging.ERROR)   # silence access log


@app.route("/")
def index():
    return render_template_string(PHONE_UI)


@app.route("/send", methods=["POST"])
def receive():
    data = request.get_json(force=True, silent=True) or {}
    text = (data.get("message") or "").strip()
    name = (data.get("name")    or "???").strip() or "???"
    if text:
        popup.push(name, text)
    return jsonify({"ok": bool(text)})


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if "--ip" in sys.argv:
        print(f"http://{_local_ip()}:{PORT}")
        sys.exit()

    flask_thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False),
        daemon=True,
    )
    flask_thread.start()

    popup.run()   # blocks on main thread (required by tkinter)
