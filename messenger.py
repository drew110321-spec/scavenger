"""
WiFi Messenger — run this on your PC.

On your phone: open a browser and go to  http://<your-pc-ip>:5001
The PC IP is printed to the terminal when you start this script.

Dependencies:
    pip install flask

tkinter is included with most Python installs. If it's missing:
    sudo apt install python3-tk   (Debian/Ubuntu)
    brew install python-tk        (macOS)
"""

import socket
import threading
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
import tkinter as tk

# ── Flask app ──────────────────────────────────────────────────────────────────

app = Flask(__name__)

PHONE_UI = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Send to PC</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #0f172a;
      color: #e2e8f0;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
    }
    .card {
      background: #1e293b;
      border-radius: 16px;
      padding: 28px 24px;
      width: 100%;
      max-width: 420px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.5);
    }
    h1 { font-size: 1.4rem; margin-bottom: 6px; color: #38bdf8; }
    p.sub { font-size: 0.85rem; color: #64748b; margin-bottom: 20px; }
    label { display: block; font-size: 0.8rem; color: #94a3b8; margin-bottom: 6px; margin-top: 14px; }
    input, textarea {
      width: 100%;
      background: #0f172a;
      border: 1px solid #334155;
      border-radius: 8px;
      color: #e2e8f0;
      font-size: 1rem;
      padding: 10px 14px;
      outline: none;
      transition: border-color .2s;
      resize: vertical;
    }
    input:focus, textarea:focus { border-color: #38bdf8; }
    textarea { min-height: 100px; font-family: inherit; }
    button {
      margin-top: 20px;
      width: 100%;
      padding: 13px;
      background: #0ea5e9;
      color: #fff;
      border: none;
      border-radius: 8px;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
      transition: background .2s, transform .1s;
    }
    button:hover { background: #0284c7; }
    button:active { transform: scale(0.98); }
    button:disabled { background: #334155; cursor: default; }
    #status {
      margin-top: 14px;
      font-size: 0.9rem;
      text-align: center;
      min-height: 1.2em;
    }
    .ok  { color: #4ade80; }
    .err { color: #f87171; }
  </style>
</head>
<body>
  <div class="card">
    <h1>&#128172; Send to PC</h1>
    <p class="sub">Connected on your local WiFi</p>

    <label for="name">Your name (optional)</label>
    <input id="name" type="text" placeholder="e.g. Drew" maxlength="40" />

    <label for="msg">Message</label>
    <textarea id="msg" placeholder="Type something…"></textarea>

    <button id="btn" onclick="send()">Send &#9654;</button>
    <div id="status"></div>
  </div>

  <script>
    async function send() {
      const name    = document.getElementById('name').value.trim();
      const message = document.getElementById('msg').value.trim();
      const status  = document.getElementById('status');
      const btn     = document.getElementById('btn');

      if (!message) {
        status.textContent = 'Please type a message first.';
        status.className = 'err';
        return;
      }

      btn.disabled = true;
      status.textContent = 'Sending…';
      status.className = '';

      try {
        const res = await fetch('/send', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, message })
        });
        if (res.ok) {
          document.getElementById('msg').value = '';
          status.textContent = '✓ Message sent!';
          status.className = 'ok';
        } else {
          status.textContent = 'Server error. Try again.';
          status.className = 'err';
        }
      } catch {
        status.textContent = 'Could not reach PC. Same WiFi?';
        status.className = 'err';
      }

      btn.disabled = false;
      setTimeout(() => { status.textContent = ''; status.className = ''; }, 3000);
    }

    // Send on Ctrl+Enter / Cmd+Enter
    document.getElementById('msg').addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) send();
    });
  </script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(PHONE_UI)


@app.route("/send", methods=["POST"])
def receive():
    data = request.get_json(force=True, silent=True) or {}
    text = (data.get("message") or "").strip()
    name = (data.get("name") or "Phone").strip() or "Phone"
    if text:
        overlay.push(name, text)
    return jsonify({"ok": bool(text)})


# ── Overlay window ─────────────────────────────────────────────────────────────

class MessageOverlay:
    """Borderless always-on-top window pinned to the bottom-right corner."""

    WIDTH  = 320
    HEIGHT = 220
    MARGIN = 12        # pixels from screen edge
    MAX_MSGS = 6

    BG      = "#0f172a"
    HDR_BG  = "#1e293b"
    HDR_FG  = "#38bdf8"
    MSG_FG  = "#e2e8f0"
    TIME_FG = "#64748b"
    CLOSE   = "#475569"

    def __init__(self):
        self._messages = []   # list of (timestamp_str, sender, text)
        self._root = None
        self._msg_frame = None

    # called from Flask thread
    def push(self, sender: str, text: str):
        ts = datetime.now().strftime("%H:%M")
        self._messages.insert(0, (ts, sender, text))
        if len(self._messages) > self.MAX_MSGS:
            self._messages.pop()
        if self._root:
            self._root.after(0, self._refresh)

    def run(self):
        """Block — call from the main thread."""
        root = tk.Tk()
        self._root = root

        root.title("Messages")
        root.overrideredirect(True)          # no title bar / borders
        root.attributes("-topmost", True)    # always on top
        root.attributes("-alpha", 0.93)
        root.configure(bg=self.BG)

        # Position bottom-right
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x  = sw - self.WIDTH  - self.MARGIN
        y  = sh - self.HEIGHT - self.MARGIN
        root.geometry(f"{self.WIDTH}x{self.HEIGHT}+{x}+{y}")

        # ── Header bar ────────────────────────────────────────────────────────
        hdr = tk.Frame(root, bg=self.HDR_BG, pady=5)
        hdr.pack(fill="x")

        tk.Label(
            hdr, text="  Messages", bg=self.HDR_BG, fg=self.HDR_FG,
            font=("Helvetica", 11, "bold")
        ).pack(side="left")

        close = tk.Label(
            hdr, text="  ✕  ", bg=self.HDR_BG, fg=self.CLOSE,
            font=("Helvetica", 11), cursor="hand2"
        )
        close.pack(side="right")
        close.bind("<Button-1>", lambda _: root.destroy())

        # Make the header draggable so the user can reposition the window
        def _drag_start(e):
            root._dx = e.x
            root._dy = e.y

        def _drag(e):
            nx = root.winfo_x() + e.x - root._dx
            ny = root.winfo_y() + e.y - root._dy
            root.geometry(f"+{nx}+{ny}")

        hdr.bind("<Button-1>", _drag_start)
        hdr.bind("<B1-Motion>", _drag)

        # ── Message area ──────────────────────────────────────────────────────
        canvas = tk.Canvas(root, bg=self.BG, highlightthickness=0)
        canvas.pack(fill="both", expand=True, padx=6, pady=(4, 6))

        self._msg_frame = tk.Frame(canvas, bg=self.BG)
        canvas.create_window((0, 0), window=self._msg_frame, anchor="nw", width=self.WIDTH - 12)

        root.mainloop()

    def _refresh(self):
        if not self._msg_frame:
            return
        for w in self._msg_frame.winfo_children():
            w.destroy()

        for ts, sender, text in self._messages:
            row = tk.Frame(self._msg_frame, bg=self.BG, pady=3)
            row.pack(fill="x")

            meta = tk.Label(
                row,
                text=f"{sender}  {ts}",
                bg=self.BG, fg=self.TIME_FG,
                font=("Helvetica", 8),
                anchor="w",
            )
            meta.pack(fill="x")

            msg = tk.Label(
                row,
                text=text,
                bg=self.BG, fg=self.MSG_FG,
                font=("Helvetica", 10),
                wraplength=self.WIDTH - 20,
                justify="left",
                anchor="w",
            )
            msg.pack(fill="x")

            tk.Frame(self._msg_frame, bg="#1e293b", height=1).pack(fill="x", pady=2)


# ── Entry point ────────────────────────────────────────────────────────────────

def _local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


overlay = MessageOverlay()

if __name__ == "__main__":
    port = 5001
    ip   = _local_ip()

    print()
    print("  WiFi Messenger — PC receiver")
    print("  " + "─" * 36)
    print(f"  Open on your phone:")
    print(f"  http://{ip}:{port}")
    print("  " + "─" * 36)
    print("  Close the corner window to quit.")
    print()

    # Flask runs in a daemon thread; tkinter owns the main thread
    flask_thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False),
        daemon=True,
    )
    flask_thread.start()

    overlay.run()
