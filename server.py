#!/usr/bin/env python3
"""
Hey Claude — iPhone backend server

The iOS Shortcut POSTs your voice request here.
This calls Gemini (free), emails the result, and returns what Siri should say.
"""

import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

load_dotenv()

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
EMAIL_TO = os.environ["EMAIL_TO"]
EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SERVER_API_KEY = os.environ["SERVER_API_KEY"]

SHORT_LIMIT = 500  # characters — shorter than this gets spoken aloud by Siri

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")
security = HTTPBearer()

app = FastAPI(docs_url=None, redoc_url=None)


# ── Auth ──────────────────────────────────────────────────────────────────────

def require_token(creds: HTTPAuthorizationCredentials = Security(security)) -> None:
    if creds.credentials != SERVER_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


# ── Helpers ───────────────────────────────────────────────────────────────────

def ask_ai(prompt: str) -> str:
    response = model.generate_content(prompt)
    return response.text


def send_email(subject: str, body: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(body, "plain"))
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as srv:
        srv.login(EMAIL_FROM, EMAIL_PASSWORD)
        srv.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())


# ── Routes ────────────────────────────────────────────────────────────────────

class AskRequest(BaseModel):
    prompt: str


_BOOM_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <title>lol watch this 💀</title>
  <style>
    *{margin:0;padding:0;box-sizing:border-box}
    body{background:#0f0f0f;color:#fff;font-family:-apple-system,sans-serif;
         min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center}

    /* ── lure ── */
    #lure{width:100%;max-width:480px;padding:20px}
    .thumb{width:100%;aspect-ratio:16/9;border-radius:14px;overflow:hidden;
           position:relative;cursor:pointer;border:1px solid #333}
    .thumb-bg{position:absolute;inset:0;
              background:linear-gradient(135deg,#1a1a2e,#16213e,#0f3460)}
    .thumb-text{position:absolute;bottom:12px;left:14px;font-size:13px;
                color:rgba(255,255,255,.6);font-style:italic}
    .play{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
          width:68px;height:68px;background:rgba(255,30,30,.92);border-radius:50%;
          display:flex;align-items:center;justify-content:center;
          font-size:26px;padding-left:5px;
          box-shadow:0 0 30px rgba(255,30,30,.5)}
    .title{margin-top:14px;font-size:16px;font-weight:600}
    .meta{margin-top:5px;font-size:13px;color:#888}

    /* ── alarm overlay ── */
    #alarm{display:none;position:fixed;inset:0;z-index:9999;
           align-items:center;justify-content:center;flex-direction:column;
           animation:bg .4s infinite}
    #alarm.on{display:flex}
    @keyframes bg{0%,100%{background:#ff0000}50%{background:#aa0000}}
    .icon{font-size:72px;animation:pop .4s infinite}
    @keyframes pop{0%,100%{transform:scale(1)}50%{transform:scale(1.15)}}
    .label{font-size:38px;font-weight:900;letter-spacing:5px;margin:18px 0 0}
    #timer{font-size:110px;font-weight:900;line-height:1;margin-top:10px}
    .sub{font-size:15px;opacity:.75;margin-top:6px}
  </style>
</head>
<body>

<div id="lure">
  <div class="thumb" onclick="go()">
    <div class="thumb-bg"></div>
    <div class="thumb-text">via iMessage</div>
    <div class="play">&#9654;</div>
  </div>
  <div class="title">bro you HAVE to see this 💀</div>
  <div class="meta">2.4M views &nbsp;·&nbsp; tap to play</div>
</div>

<div id="alarm">
  <div class="icon">&#128680;</div>
  <div class="label">ALARM</div>
  <div id="timer">60</div>
  <div class="sub">seconds remaining</div>
</div>

<script>
function go(){
  /* audio — two oscillators + LFO sweep = siren wail */
  var ctx=new(window.AudioContext||window.webkitAudioContext)();
  var master=ctx.createGain(); master.gain.value=1; master.connect(ctx.destination);
  [
    {type:'sawtooth',freq:880},
    {type:'square', freq:660}
  ].forEach(function(p){
    var osc=ctx.createOscillator(),lfo=ctx.createOscillator(),lg=ctx.createGain();
    osc.type=p.type; osc.frequency.value=p.freq;
    lfo.type='sine'; lfo.frequency.value=2.5; lg.gain.value=280;
    lfo.connect(lg); lg.connect(osc.frequency);
    osc.connect(master); lfo.start(); osc.start();
    setTimeout(function(){osc.stop();lfo.stop();},60000);
  });

  /* fullscreen (ignored silently on iOS Safari — overlay still fills screen) */
  var el=document.documentElement;
  (el.requestFullscreen||el.webkitRequestFullscreen||function(){}
  ).call(el);

  /* swap views */
  document.getElementById('lure').style.display='none';
  var alarm=document.getElementById('alarm');
  alarm.classList.add('on');

  /* countdown */
  var t=60, el2=document.getElementById('timer');
  var iv=setInterval(function(){
    el2.textContent=--t;
    if(t<=0){
      clearInterval(iv);
      alarm.classList.remove('on');
      document.getElementById('lure').style.display='block';
      ctx.close();
    }
  },1000);
}
</script>
</body>
</html>"""


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/boom", response_class=HTMLResponse)
def boom():
    return _BOOM_PAGE


@app.get("/alarm")
def alarm(_=Depends(require_token)):
    return {
        "speak": "Alarm started. Buckle up — 60 seconds of pure pain.",
        "action": "alarm",
        "duration": 60,
    }


@app.post("/ask")
def ask(req: AskRequest, _=Depends(require_token)):
    try:
        answer = ask_ai(req.prompt)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AI error: {exc}") from exc

    short = len(answer) <= SHORT_LIMIT
    speak = answer if short else "Sent to your email."

    subject = f"Assistant: {req.prompt[:60]}{'...' if len(req.prompt) > 60 else ''}"
    body = (
        f"You asked:\n{req.prompt}\n\n"
        f"{'─' * 60}\n\n"
        f"{answer}\n\n"
        f"{'─' * 60}\n"
        f"Answered at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    try:
        send_email(subject, body)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Email error: {exc}") from exc

    return {"speak": speak, "answer": answer, "short": short}
