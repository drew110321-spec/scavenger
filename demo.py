#!/usr/bin/env python3
"""
Roadside Assistance AI Demo — stdlib only (no FastAPI required)
Run: python3 demo.py
Then open: http://localhost:8000
"""

import json
import os
import random
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

# ── Mock job database ──────────────────────────────────────────────────────────

MOCK_JOBS = {
    "JOB-001": {
        "id": "JOB-001",
        "problem": "accident",
        "description": "Rear-end collision on I-95, airbags deployed",
        "location": "I-95 North, Mile Marker 42, center median",
        "vehicle": "2019 Honda Civic",
        "member": "Sarah K.",
        "status": "on_site",
        "priority": 1,
        "priority_label": "CRITICAL",
        "driver": "Mike Torres",
        "driver_eta_min": 0,
        "driver_dist_mi": 0.0,
        "assigned_at": (datetime.now() - timedelta(minutes=18)).isoformat(),
        "safe": False,
        "injury": True,
    },
    "JOB-002": {
        "id": "JOB-002",
        "problem": "flat",
        "description": "Flat tire on highway on-ramp, car partially blocking",
        "location": "Hwy 1 on-ramp at Exit 7, right shoulder",
        "vehicle": "2021 Ford F-150",
        "member": "James R.",
        "status": "en_route",
        "priority": 2,
        "priority_label": "HIGH",
        "driver": "Lisa Chen",
        "driver_eta_min": 12,
        "driver_dist_mi": 4.1,
        "assigned_at": (datetime.now() - timedelta(minutes=8)).isoformat(),
        "safe": True,
        "injury": False,
    },
    "JOB-003": {
        "id": "JOB-003",
        "problem": "battery",
        "description": "Dead battery, car won't start",
        "location": "Target parking lot, 500 Oak St, Bayview",
        "vehicle": "2018 Toyota Camry",
        "member": "Maria G.",
        "status": "en_route",
        "priority": 3,
        "priority_label": "NORMAL",
        "driver": "Dave Park",
        "driver_eta_min": 23,
        "driver_dist_mi": 7.8,
        "assigned_at": (datetime.now() - timedelta(minutes=3)).isoformat(),
        "safe": True,
        "injury": False,
    },
    "JOB-004": {
        "id": "JOB-004",
        "problem": "lockout",
        "description": "Locked keys in car",
        "location": "221 Pine Ave, Eastside",
        "vehicle": "2022 Chevy Equinox",
        "member": "Tom B.",
        "status": "assigned",
        "priority": 4,
        "priority_label": "NORMAL",
        "driver": "Amy Reyes",
        "driver_eta_min": 31,
        "driver_dist_mi": 10.2,
        "assigned_at": (datetime.now() - timedelta(minutes=1)).isoformat(),
        "safe": True,
        "injury": False,
    },
    "JOB-005": {
        "id": "JOB-005",
        "problem": "gas",
        "description": "Ran out of gas",
        "location": "Corner of Main & 5th, Downtown",
        "vehicle": "2020 Subaru Outback",
        "member": "Rachel T.",
        "status": "done",
        "priority": 5,
        "priority_label": "NORMAL",
        "driver": "Carlos M.",
        "driver_eta_min": 0,
        "driver_dist_mi": 0.0,
        "assigned_at": (datetime.now() - timedelta(minutes=45)).isoformat(),
        "safe": True,
        "injury": False,
    },
}

SURVEYS = []


# ── Triage (deterministic) ─────────────────────────────────────────────────────

def triage_priority(job):
    problem = job.get("problem", "")
    safe = job.get("safe", True)
    injury = job.get("injury", False)
    location = job.get("location", "").lower()

    if injury:
        return 1, "CRITICAL", "Injury reported — hard rule, AI has no vote here"
    if problem == "accident" and not safe:
        return 1, "CRITICAL", "Accident at unsafe location — hard rule"
    if problem in ("accident", "won_start", "flat") and any(k in location for k in ("highway", "i-", "hwy", "i95", "i-95")):
        return 2, "HIGH", "Disabled vehicle on highway — elevated risk"
    if problem == "accident":
        return 2, "HIGH", "Accident, safe location"
    return 3, "NORMAL", "Safe location, standard service"


# ── Mock intake (LLM simulation) ───────────────────────────────────────────────

def mock_intake(message):
    msg = message.lower()
    if any(w in msg for w in ["battery", "dead", "jump", "won't start", "wont start"]):
        reply = "Sounds like a dead battery — we can get you a jump start. Where are you located right now, and what's the year/make/model of your vehicle?"
        problem = "battery"
        safe, injury = True, False
    elif any(w in msg for w in ["flat", "tire", "tyre", "blowout"]):
        reply = "Got it, flat tire — we'll get a tech out to you. What's your exact location, and are you safely off the road?"
        problem = "flat"
        safe, injury = True, False
    elif any(w in msg for w in ["lock", "keys", "locked"]):
        reply = "Locked out — no problem, we handle that all the time. What's your location and the make/model of your vehicle?"
        problem = "lockout"
        safe, injury = True, False
    elif any(w in msg for w in ["gas", "fuel", "empty"]):
        reply = "Out of gas — we'll bring you enough to get to the nearest station. Where are you?"
        problem = "gas"
        safe, injury = True, False
    elif any(w in msg for w in ["accident", "crash", "hit", "collision", "airbag"]):
        reply = "Are you okay? Safety first — if anyone is hurt, please call 911 immediately. Once you're safe, I'll get a tech dispatched to you right away. What's your location?"
        problem = "accident"
        safe, injury = False, True
    else:
        reply = "I've got your request — can you give me a bit more detail? What's going on with the vehicle, and where are you right now?"
        problem = "other"
        safe, injury = True, False

    # Try to extract location hint
    location = None
    for kw in ["at ", "on ", "near ", "in ", "parking", "highway", "street", "ave", "blvd"]:
        if kw in msg:
            idx = msg.find(kw)
            location = message[idx:idx + 40].strip()
            break

    extracted = {"problem": problem, "location": location, "vehicle": None, "safe": safe, "injury": injury}
    priority, label, reason = triage_priority(extracted)
    return {
        "extracted": extracted,
        "reply": reply,
        "triage": {"priority": priority, "label": label, "reason": reason},
    }


def mock_status(job):
    status = job["status"]
    driver = job["driver"]
    eta = job["driver_eta_min"]
    dist = job["driver_dist_mi"]
    if status == "assigned":
        return f"{driver} has been assigned and is getting ready to head your way — you should see movement soon."
    elif status == "en_route":
        return f"Good news — {driver} is on the way! They're about {dist} miles out and should reach you in roughly {eta} minutes."
    elif status == "on_site":
        return f"{driver} is on site with you right now. If you don't see them, look for the service vehicle."
    elif status == "done":
        return "Your service is complete! We hope you're back on the road safely. You'll receive a survey shortly."
    return "We're working on your request — hang tight."


# ── HTTP Handler ───────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"  {args[0]} {args[1]}")

    def send_json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path, mime="text/html"):
        content = Path(path).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self.send_file("static/index.html")
        elif path == "/api/queue":
            jobs = sorted(MOCK_JOBS.values(), key=lambda j: (j["priority"], j["assigned_at"]))
            self.send_json({"jobs": jobs, "total": len(jobs)})
        elif path == "/api/surveys":
            avg = sum(s["rating"] for s in SURVEYS) / len(SURVEYS) if SURVEYS else None
            self.send_json({"surveys": SURVEYS, "avg_rating": avg})
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path
        body = self.read_body()

        if path == "/api/intake":
            msg = body.get("message", "")
            self.send_json(mock_intake(msg))

        elif path == "/api/status":
            job_id = body.get("job_id", "")
            question = body.get("question", "")
            job = MOCK_JOBS.get(job_id)
            if not job:
                self.send_json({"error": "Job not found"}, 404)
                return
            reply = mock_status(job)
            self.send_json({
                "job_id": job_id,
                "raw_status": {
                    "status": job["status"],
                    "driver": job["driver"],
                    "eta_min": job["driver_eta_min"],
                    "dist_mi": job["driver_dist_mi"],
                },
                "reply": reply,
            })

        elif path == "/api/survey":
            rating = body.get("rating", 0)
            if not (1 <= rating <= 5):
                self.send_json({"error": "Rating must be 1-5"}, 400)
                return
            entry = {
                "job_id": body.get("job_id", ""),
                "rating": rating,
                "comment": body.get("comment", ""),
                "submitted_at": datetime.now().isoformat(),
            }
            SURVEYS.append(entry)
            self.send_json({"ok": True, "message": "Thanks for your feedback!", "entry": entry})

        elif path == "/api/dispatch":
            job_id = f"JOB-{random.randint(100, 999)}"
            priority, label, reason = triage_priority(body)
            drivers = ["Mike Torres", "Lisa Chen", "Dave Park", "Amy Reyes", "Carlos M."]
            driver = random.choice(drivers)
            eta = random.randint(8, 35)
            job = {
                "id": job_id,
                "problem": body.get("problem", "other"),
                "description": body.get("description", ""),
                "location": body.get("location", ""),
                "vehicle": body.get("vehicle", ""),
                "member": body.get("member", "Demo Member"),
                "status": "assigned",
                "priority": priority,
                "priority_label": label,
                "driver": driver,
                "driver_eta_min": eta,
                "driver_dist_mi": round(eta * 0.35, 1),
                "assigned_at": datetime.now().isoformat(),
                "safe": body.get("safe", True),
                "injury": body.get("injury", False),
            }
            MOCK_JOBS[job_id] = job
            self.send_json({"job": job, "triage": {"priority": priority, "label": label, "reason": reason}})

        else:
            self.send_response(404)
            self.end_headers()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"\n  RoadAI Demo  →  http://localhost:{port}\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
