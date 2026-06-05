#!/usr/bin/env python3
"""
Hey Claude - Voice Activated Assistant

Say "Hey Claude" to wake it up (works with screen off).
Speak your request, and Claude's answer is emailed to you.
"""

import logging
import os
import smtplib
import threading
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import anthropic
import speech_recognition as sr
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("assistant.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# Wake word variants to handle common speech-to-text misreadings
WAKE_WORDS = {"hey claude", "hey clod", "hey cloud", "a claude", "hey claude's"}

EMAIL_TO = os.environ["EMAIL_TO"]
EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Prevent overlapping wake-word responses
_processing = False
_lock = threading.Lock()


def is_wake_word(text: str) -> bool:
    text = text.lower().strip()
    return any(w in text for w in WAKE_WORDS)


def ask_claude(prompt: str) -> str:
    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def send_email(subject: str, body: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
    log.info("Email sent to %s", EMAIL_TO)


def process_command(command: str) -> None:
    log.info("Command: %s", command)
    try:
        answer = ask_claude(command)
        log.info("Claude responded (%d chars)", len(answer))

        subject = f"Claude: {command[:60]}{'...' if len(command) > 60 else ''}"
        body = (
            f"You asked:\n{command}\n\n"
            f"{'─' * 60}\n\n"
            f"{answer}\n\n"
            f"{'─' * 60}\n"
            f"Answered at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        send_email(subject, body)
    except Exception as exc:
        log.error("Error processing command: %s", exc)
        try:
            send_email(
                "Claude Assistant Error",
                f"Sorry, I couldn't process your request:\n'{command}'\n\nError: {exc}",
            )
        except Exception:
            log.error("Also failed to send error email")


def listen_for_command(
    recognizer: sr.Recognizer,
    mic: sr.Microphone,
) -> Optional[str]:
    """Capture up to 30 s of speech after the wake word fires."""
    log.info("Listening for your command...")
    with mic as source:
        try:
            audio = recognizer.listen(source, timeout=8, phrase_time_limit=30)
        except sr.WaitTimeoutError:
            log.info("No command heard (timeout)")
            return None

    try:
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        log.info("Could not understand command")
        return None
    except sr.RequestError as exc:
        log.error("Speech recognition error: %s", exc)
        return None


def wake_callback(recognizer: sr.Recognizer, audio: sr.AudioData) -> None:
    global _processing

    with _lock:
        if _processing:
            return

    try:
        text = recognizer.recognize_google(audio)
        log.debug("Heard: %s", text)
    except (sr.UnknownValueError, sr.RequestError):
        return

    if not is_wake_word(text):
        return

    with _lock:
        _processing = True

    log.info("Wake word detected — listening for command")
    try:
        mic = sr.Microphone()
        cmd_recognizer = sr.Recognizer()
        cmd_recognizer.energy_threshold = recognizer.energy_threshold
        cmd_recognizer.dynamic_energy_threshold = True

        command = listen_for_command(cmd_recognizer, mic)
        if command:
            threading.Thread(
                target=process_command, args=(command,), daemon=True
            ).start()
        else:
            log.info("No command received after wake word")
    finally:
        with _lock:
            _processing = False


def main() -> None:
    log.info("Starting Hey Claude voice assistant")
    log.info("Wake phrase: 'Hey Claude'")
    log.info("Results emailed to: %s", EMAIL_TO)

    r = sr.Recognizer()
    r.dynamic_energy_threshold = True
    r.energy_threshold = 300

    mic = sr.Microphone()
    log.info("Calibrating for ambient noise (2 s)…")
    with mic as source:
        r.adjust_for_ambient_noise(source, duration=2)
    log.info("Calibration done. Say 'Hey Claude' to activate.")

    stop_listening = r.listen_in_background(mic, wake_callback, phrase_time_limit=5)

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        log.info("Shutting down…")
        stop_listening(wait_for_stop=False)


if __name__ == "__main__":
    main()
