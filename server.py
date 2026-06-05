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


@app.get("/health")
def health():
    return {"status": "ok"}


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
