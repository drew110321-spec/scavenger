#!/usr/bin/env python3
"""
RoadAI demo video generator — pure Python stdlib, no ffmpeg / no deps.

Renders the 5-stage roadside-assistance pipeline as animated slides, synthesizes
a calm ambient background-music track, and muxes both into a self-contained AVI
(uncompressed 8-bit palettized video + 16-bit PCM audio).

    python3 make_video.py        ->  roadai_demo.avi

Play with VLC (recommended) or any player that supports DIB-AVI.
"""

import math
import struct

# ── Output config ──────────────────────────────────────────────────────────────
W, H = 640, 360
FPS = 6
SR = 22050                       # audio sample rate
AUDIO_AMP = 0.20                 # background-music loudness (0..1)
OUT = "roadai_demo.avi"

# ── Palette (index -> RGB) ──────────────────────────────────────────────────────
PAL = [
    (15, 17, 23),      # 0  bg
    (32, 36, 58),      # 1  panel
    (26, 29, 39),      # 2  surface
    (45, 49, 80),      # 3  border
    (226, 232, 240),   # 4  white text
    (100, 116, 139),   # 5  muted text
    (249, 115, 22),    # 6  orange accent
    (59, 130, 246),    # 7  blue accent
    (239, 68, 68),     # 8  red
    (245, 158, 11),    # 9  yellow
    (34, 197, 94),     # 10 green
    (30, 58, 95),      # 11 blue panel
    (60, 30, 12),      # 12 orange-dark panel
    (20, 50, 30),      # 13 green-dark panel
    (70, 25, 25),      # 14 red-dark panel
]
BG, PANEL, SURF, BORDER, WHITE, MUTED, ORANGE, BLUE, RED, YELLOW, GREEN, \
    BLUEPANEL, ORANGEPANEL, GREENPANEL, REDPANEL = range(15)

# ── 5x7 bitmap font ─────────────────────────────────────────────────────────────
# Each glyph: 7 rows of 5 columns. '#' = ink.
_F = {
 ' ': ["     "]*7,
 'A': [" ### ","#   #","#   #","#####","#   #","#   #","#   #"],
 'B': ["#### ","#   #","#   #","#### ","#   #","#   #","#### "],
 'C': [" ####","#    ","#    ","#    ","#    ","#    "," ####"],
 'D': ["#### ","#   #","#   #","#   #","#   #","#   #","#### "],
 'E': ["#####","#    ","#    ","#### ","#    ","#    ","#####"],
 'F': ["#####","#    ","#    ","#### ","#    ","#    ","#    "],
 'G': [" ####","#    ","#    ","# ###","#   #","#   #"," ####"],
 'H': ["#   #","#   #","#   #","#####","#   #","#   #","#   #"],
 'I': ["#####","  #  ","  #  ","  #  ","  #  ","  #  ","#####"],
 'J': ["#####","   # ","   # ","   # ","   # ","#  # "," ##  "],
 'K': ["#   #","#  # ","# #  ","##   ","# #  ","#  # ","#   #"],
 'L': ["#    ","#    ","#    ","#    ","#    ","#    ","#####"],
 'M': ["#   #","## ##","# # #","#   #","#   #","#   #","#   #"],
 'N': ["#   #","##  #","# # #","#  ##","#   #","#   #","#   #"],
 'O': [" ### ","#   #","#   #","#   #","#   #","#   #"," ### "],
 'P': ["#### ","#   #","#   #","#### ","#    ","#    ","#    "],
 'Q': [" ### ","#   #","#   #","#   #","# # #","#  # "," ## #"],
 'R': ["#### ","#   #","#   #","#### ","# #  ","#  # ","#   #"],
 'S': [" ####","#    ","#    "," ### ","    #","    #","#### "],
 'T': ["#####","  #  ","  #  ","  #  ","  #  ","  #  ","  #  "],
 'U': ["#   #","#   #","#   #","#   #","#   #","#   #"," ### "],
 'V': ["#   #","#   #","#   #","#   #","#   #"," # # ","  #  "],
 'W': ["#   #","#   #","#   #","#   #","# # #","## ##","#   #"],
 'X': ["#   #","#   #"," # # ","  #  "," # # ","#   #","#   #"],
 'Y': ["#   #","#   #"," # # ","  #  ","  #  ","  #  ","  #  "],
 'Z': ["#####","    #","   # ","  #  "," #   ","#    ","#####"],
 '0': [" ### ","#   #","#  ##","# # #","##  #","#   #"," ### "],
 '1': ["  #  "," ##  ","  #  ","  #  ","  #  ","  #  "," ### "],
 '2': [" ### ","#   #","    #","   # ","  #  "," #   ","#####"],
 '3': ["#####","   # ","  #  ","   # ","    #","#   #"," ### "],
 '4': ["   # ","  ## "," # # ","#  # ","#####","   # ","   # "],
 '5': ["#####","#    ","#### ","    #","    #","#   #"," ### "],
 '6': [" ### ","#    ","#    ","#### ","#   #","#   #"," ### "],
 '7': ["#####","    #","   # ","  #  "," #   "," #   "," #   "],
 '8': [" ### ","#   #","#   #"," ### ","#   #","#   #"," ### "],
 '9': [" ### ","#   #","#   #"," ####","    #","    #"," ### "],
 '.': ["     ","     ","     ","     ","     ","  ## ","  ## "],
 ',': ["     ","     ","     ","     ","  ## ","  ## "," #   "],
 ':': ["     ","  ## ","  ## ","     ","  ## ","  ## ","     "],
 '-': ["     ","     ","     "," ### ","     ","     ","     "],
 '+': ["     ","  #  ","  #  ","#####","  #  ","  #  ","     "],
 '!': ["  #  ","  #  ","  #  ","  #  ","  #  ","     ","  #  "],
 '?': [" ### ","#   #","    #","   # ","  #  ","     ","  #  "],
 '/': ["    #","    #","   # ","  #  "," #   ","#    ","#    "],
 '(': ["   # ","  #  "," #   "," #   "," #   ","  #  ","   # "],
 ')': [" #   ","  #  ","   # ","   # ","   # ","  #  "," #   "],
 "'": ["  #  ","  #  ","  #  ","     ","     ","     ","     "],
 '&': [" ##  ","#  # ","#  # "," ##  ","#  ##","#  # "," ## #"],
 '%': ["##  #","##  #","   # ","  #  "," #   ","#  ##","#  ##"],
 '=': ["     ","     ","#####","     ","#####","     ","     "],
 '>': [" #   ","  #  ","   # ","    #","   # ","  #  "," #   "],
 '#': [" # # ","#####"," # # "," # # ","#####"," # # ","     "],
 '*': ["#####"]*0 + ["     "," # # ","  #  ","#####","  #  "," # # ","     "],
}
ARROW = ["     ","  #  ","  ## ","#####","  ## ","  #  ","     "]   # ->


class Frame:
    """A W*H index buffer (top-down) with simple drawing helpers."""
    __slots__ = ("buf",)

    def __init__(self, bg=BG):
        self.buf = bytearray([bg]) * (W * H)

    def rect(self, x, y, w, h, c):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(W, x + w), min(H, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes([c]) * (x1 - x0)
        b = self.buf
        for yy in range(y0, y1):
            o = yy * W + x0
            b[o:o + (x1 - x0)] = row

    def border(self, x, y, w, h, c, t=1):
        self.rect(x, y, w, t, c)
        self.rect(x, y + h - t, w, t, c)
        self.rect(x, y, t, h, c)
        self.rect(x + w - t, y, t, h, c)

    def px(self, x, y, c):
        if 0 <= x < W and 0 <= y < H:
            self.buf[y * W + x] = c

    def glyph(self, rows, x, y, c, s):
        for ry, line in enumerate(rows):
            for rx, ch in enumerate(line):
                if ch == '#':
                    if s == 1:
                        self.px(x + rx, y + ry, c)
                    else:
                        self.rect(x + rx * s, y + ry * s, s, s, c)

    def text(self, x, y, s_text, c, s=2):
        cx = x
        for ch in s_text.upper():
            if ch == '→':           # arrow
                self.glyph(ARROW, cx, y, c, s)
            else:
                self.glyph(_F.get(ch, _F[' ']), cx, y, c, s)
            cx += 6 * s
        return cx

    def text_w(self, s_text, s=2):
        return len(s_text) * 6 * s

    def ctext(self, y, s_text, c, s=2):
        x = (W - self.text_w(s_text, s)) // 2
        return self.text(x, y, s_text, c, s)


# ── Reusable chrome ──────────────────────────────────────────────────────────────

def chrome(f, stage_idx, stage_total, title, accent=ORANGE):
    """Header bar + footer progress used on every content slide."""
    # header
    f.rect(0, 0, W, 40, SURF)
    f.rect(0, 39, W, 1, BORDER)
    f.text(24, 12, "ROAD", WHITE, 3)
    f.text(24 + f.text_w("ROAD", 3), 12, "AI", accent, 3)
    f.rect(W - 150, 12, 64, 18, accent)
    f.text(W - 144, 14, "DEMO", WHITE, 2)
    # stage tabs strip
    f.rect(0, 40, W, 22, BG)
    names = ["INTAKE", "TRIAGE", "DISPATCH", "STATUS", "SURVEY"]
    tx = 24
    for i, nm in enumerate(names):
        col = accent if i == stage_idx else MUTED
        f.text(tx, 46, str(i + 1), col, 2)
        f.text(tx + 14, 46, nm, col, 2)
        if i == stage_idx:
            f.rect(tx, 60, 14 + f.text_w(nm, 2), 2, accent)
        tx += 24 + f.text_w(nm, 2)


def footer_progress(f, frac, accent=ORANGE):
    f.rect(0, H - 6, W, 6, SURF)
    f.rect(0, H - 6, int(W * frac), 6, accent)


def panel(f, x, y, w, h, fill=PANEL):
    f.rect(x, y, w, h, fill)
    f.border(x, y, w, h, BORDER)


def badge(f, x, y, label, kind):
    cols = {"CRITICAL": (REDPANEL, RED), "HIGH": (ORANGEPANEL, YELLOW),
            "NORMAL": (GREENPANEL, GREEN)}
    bg, fg = cols[kind]
    w = f.text_w(label, 2) + 16
    f.rect(x, y, w, 18, bg)
    f.border(x, y, w, 18, fg)
    f.text(x + 8, y + 3, label, fg, 2)
    return w


# ── Scene builders ───────────────────────────────────────────────────────────────
# Each returns a function(local_t in [0,1]) -> Frame, plus a duration in seconds.

def scene_title(t):
    f = Frame()
    # subtle vignette stripes
    f.rect(0, 150, W, 60, SURF)
    f.text(24, 60, "ROAD", WHITE, 5)
    f.text(24 + f.text_w("ROAD", 5), 60, "AI", ORANGE, 5)
    f.ctext(165, "ROADSIDE ASSISTANCE AI PIPELINE", MUTED, 2)
    f.ctext(190, "INTAKE  TRIAGE  DISPATCH  STATUS  SURVEY", WHITE, 2)
    # animated underline sweep
    sweep = int(W * min(1.0, t * 1.6))
    f.rect(0, 220, sweep, 3, ORANGE)
    # blinking prompt
    if int(t * 4) % 2 == 0:
        f.text(W // 2 - 70, 250, "PRESS PLAY →", GREEN, 2)
    footer_progress(f, GLOBAL_FRAC[0], ORANGE)
    return f


def scene_intake(t):
    f = Frame()
    chrome(f, 0, 5, "INTAKE", ORANGE)
    f.text(24, 78, "STAGE 1  INTAKE CHAT", WHITE, 3)
    f.text(24, 108, "LLM EXTRACTS STRUCTURED JSON - NOT A TRANSCRIPT", MUTED, 2)
    # left chat panel
    panel(f, 24, 132, 300, 200, PANEL)
    f.text(36, 142, "MEMBER CHAT", MUTED, 2)
    msgs = [
        (RED, "MY TIRE BLEW OUT ON I-95"),
        (RED, "NEAR EXIT 12, ON THE SHOULDER"),
    ]
    ai = "GOT IT - FLAT TIRE. ARE YOU SAFELY OFF THE ROAD?"
    shown = int(t * 3)
    yy = 162
    for i, (c, m) in enumerate(msgs):
        if shown > i:
            f.rect(160, yy, 152, 22, BLUEPANEL)
            f.text(166, yy + 5, m[:24], WHITE, 1)
            f.text(166, yy + 13, m[24:], WHITE, 1)
            yy += 30
    if shown >= 2:
        f.rect(36, yy, 230, 30, SURF)
        f.text(42, yy + 4, ai[:30], GREEN, 1)
        f.text(42, yy + 14, ai[30:], GREEN, 1)
    # right: extracted json
    panel(f, 340, 132, 276, 200, SURF)
    f.text(352, 142, "EXTRACTED DATA (JSON)", MUTED, 2)
    lines = ['{', '  "problem": "flat",', '  "location": "I-95 EXIT 12",',
             '  "vehicle": null,', '  "safe": true,', '  "injury": false', '}']
    reveal = int(t * len(lines) * 1.3)
    for i, ln in enumerate(lines):
        if i < reveal:
            f.text(352, 162 + i * 13, ln, (BLUE if '"' in ln else WHITE), 1)
    footer_progress(f, GLOBAL_FRAC[1], ORANGE)
    return f


def scene_triage(t):
    f = Frame()
    chrome(f, 1, 5, "TRIAGE", ORANGE)
    f.text(24, 78, "STAGE 2  TRIAGE QUEUE", WHITE, 3)
    f.text(24, 108, "AI CLASSIFIES - DETERMINISTIC RULES ORDER THE QUEUE", MUTED, 2)
    rows = [
        (RED, "CRITICAL", "1", "SARAH K", "ACCIDENT, INJURY - I-95 MEDIAN"),
        (YELLOW, "HIGH", "2", "JAMES R", "FLAT ON HIGHWAY - HWY 1 EXIT 7"),
        (GREEN, "NORMAL", "3", "MARIA G", "DEAD BATTERY - TARGET LOT"),
        (GREEN, "NORMAL", "4", "TOM B", "LOCKOUT - 221 PINE AVE"),
    ]
    appear = int(t * 6)
    y = 132
    for i, (col, lab, rank, who, loc) in enumerate(rows):
        if i < appear:
            f.rect(24, y, 380, 40, PANEL)
            f.rect(24, y, 3, 40, col)
            f.border(24, y, 380, 40, BORDER)
            f.rect(34, y + 8, 24, 24, SURF)
            f.text(42, y + 12, rank, col, 2)
            f.text(70, y + 8, who, WHITE, 2)
            f.text(70, y + 24, loc, MUTED, 1)
            badge(f, 300, y + 11, lab, lab)
        y += 46
    # rules panel
    panel(f, 420, 132, 196, 184, SURF)
    f.text(432, 142, "HARD RULES", MUTED, 2)
    rl = [(RED, "INJURY = TOP"), (RED, "ACCIDENT+UNSAFE"),
          (YELLOW, "HIGHWAY = HIGH"), (GREEN, "ELSE NORMAL")]
    for i, (c, txt) in enumerate(rl):
        f.rect(432, 164 + i * 36, 172, 28, PANEL)
        f.rect(432, 164 + i * 36, 3, 28, c)
        f.text(442, 172 + i * 36, txt, WHITE, 2)
    if int(t * 2) % 2 == 0:
        f.text(432, 305, "NO AI VOTE HERE", RED, 1)
    footer_progress(f, GLOBAL_FRAC[2], ORANGE)
    return f


def scene_dispatch(t):
    f = Frame()
    chrome(f, 2, 5, "DISPATCH", ORANGE)
    f.text(24, 78, "STAGE 3  DISPATCH BOARD", WHITE, 3)
    f.text(24, 108, "THE 80% - LOGISTICS, NOT AI", MUTED, 2)
    # state machine
    states = ["INTAKE", "ASSIGNED", "EN ROUTE", "ON SITE", "DONE"]
    active = min(4, int(t * 5))
    n = len(states)
    gap = (W - 80) // n
    for i, st in enumerate(states):
        cx = 40 + gap * i + gap // 2 - 20
        cy = 150
        col = GREEN if i < active else (ORANGE if i == active else BORDER)
        f.rect(cx, cy, 40, 40, SURF)
        f.border(cx, cy, 40, 40, col, 2)
        f.text(cx + 14, cy + 12, str(i + 1), col, 2)
        x = cx + 20 - f.text_w(st, 1) // 2
        f.text(x, cy + 48, st, (WHITE if i <= active else MUTED), 1)
        if i < n - 1:
            f.text(cx + 44, cy + 14, "→", BORDER, 2)
    # the four logistics pillars
    pillars = [("DRIVER APP", BLUE), ("GPS TRACKING", GREEN),
               ("ASSIGN ALGO", ORANGE), ("JOB STATES", YELLOW)]
    pw = 140
    for i, (p, c) in enumerate(pillars):
        x = 24 + i * (pw + 12)
        if 24 + 3 * (pw + 12) + pw > W:
            pw_ = (W - 48 - 3 * 12) // 4
        else:
            pw_ = pw
        x = 24 + i * (pw_ + 12)
        panel(f, x, 240, pw_, 80, PANEL)
        f.rect(x, 240, pw_, 3, c)
        f.text(x + 10, 256, p[:12], WHITE, 1)
        f.text(x + 10, 270, p[12:], WHITE, 1)
        f.text(x + 10, 295, "NOT AI", MUTED, 1)
    footer_progress(f, GLOBAL_FRAC[3], ORANGE)
    return f


def scene_status(t):
    f = Frame()
    chrome(f, 3, 5, "STATUS", ORANGE)
    f.text(24, 78, "STAGE 4  STATUS CHAT", WHITE, 3)
    f.text(24, 108, "DB LOOKUP WRAPPED IN FRIENDLY WORDING", MUTED, 2)
    # db record
    panel(f, 24, 132, 270, 190, SURF)
    f.text(36, 142, "RAW DB RECORD", MUTED, 2)
    rec = ['{', '  "status": "EN ROUTE",', '  "driver": "LISA CHEN",',
           '  "eta_min": 12,', '  "dist_mi": 4.1', '}']
    for i, ln in enumerate(rec):
        f.text(36, 164 + i * 16, ln, (BLUE if '"' in ln else WHITE), 1)
    # arrow
    f.text(300, 210, "→", ORANGE, 3)
    # friendly reply
    panel(f, 336, 132, 280, 190, PANEL)
    f.text(348, 142, "MEMBER ASKS", MUTED, 2)
    f.rect(420, 160, 184, 22, BLUEPANEL)
    f.text(426, 167, "WHERES MY DRIVER?", WHITE, 1)
    reply = ["GOOD NEWS - LISA IS ON THE", "WAY! ABOUT 4.1 MILES OUT,",
             "ROUGHLY 12 MINUTES AWAY."]
    rv = int(t * 4)
    f.text(348, 200, "AI REPLY", MUTED, 2)
    for i, ln in enumerate(reply):
        if i < rv:
            f.rect(348, 220 + i * 24, 256, 20, SURF)
            f.text(354, 225 + i * 24, ln, GREEN, 1)
    f.text(348, 300, "GROUNDED IN DATA - NO HALLUCINATION", MUTED, 1)
    footer_progress(f, GLOBAL_FRAC[4], ORANGE)
    return f


def scene_survey(t):
    f = Frame()
    chrome(f, 4, 5, "SURVEY", ORANGE)
    f.text(24, 78, "STAGE 5  SURVEY + IMPROVE LOOP", WHITE, 3)
    f.text(24, 108, "HUMAN-DRIVEN ITERATION - NOT SELF-TRAINING", MUTED, 2)
    # stars filling
    nstars = min(5, int(t * 6))
    for i in range(5):
        c = YELLOW if i < nstars else BORDER
        sx = 36 + i * 40
        # draw a chunky star block
        f.rect(sx, 140, 30, 30, c)
        f.rect(sx + 6, 134, 18, 6, c)
        f.rect(sx + 6, 170, 18, 6, c)
    f.text(36, 186, "POST-SERVICE RATING STORED", MUTED, 2)
    # loop steps
    steps = [(GREEN, "LOG EVERYTHING"), (BLUE, "READ 1-2 STAR CALLS"),
             (ORANGE, "FIX PROMPTS & RULES"), (YELLOW, "FINE-TUNE EVENTUALLY")]
    sx = int(t * 6)
    for i, (c, s) in enumerate(steps):
        if i < sx:
            y = 214 + i * 32
            f.rect(36, y, 360, 26, PANEL)
            f.rect(36, y, 3, 26, c)
            f.text(46, y + 7, str(i + 1) + "  " + s, WHITE, 2)
    # myth callout
    panel(f, 410, 140, 206, 158, REDPANEL)
    f.border(410, 140, 206, 158, RED)
    f.text(422, 150, "THE MYTH", RED, 2)
    myth = ['"THE AI TRAINS ITSELF', 'FROM SURVEY SCORES"', '',
            'DOESNT WORK AT THIS', 'SCALE - TOO COSTLY,', 'WRONG TOOL.', '',
            'REAL LOOP = HUMANS', 'ITERATING PROMPTS.']
    for i, ln in enumerate(myth):
        f.text(422, 172 + i * 14, ln, WHITE, 1)
    footer_progress(f, GLOBAL_FRAC[5], ORANGE)
    return f


def scene_outro(t):
    f = Frame()
    f.rect(0, 130, W, 100, SURF)
    f.ctext(60, "BUILD INTAKE + TRIAGE + STATUS FIRST", WHITE, 2)
    f.ctext(90, "DISPATCH LOGISTICS IS THE REAL 80%", MUTED, 2)
    f.text(W // 2 - f.text_w("ROADAI", 4) // 2, 150, "ROAD", WHITE, 4)
    f.text(W // 2 - f.text_w("ROADAI", 4) // 2 + f.text_w("ROAD", 4), 150,
           "AI", ORANGE, 4)
    f.ctext(210, "SPEED-TO-LEAD + REVIEW BOOSTER, FUSED", MUTED, 2)
    sweep = int(W * min(1.0, t * 1.4))
    f.rect(0, 245, sweep, 3, ORANGE)
    f.ctext(265, "RUN  PYTHON3 DEMO.PY  FOR THE LIVE APP", GREEN, 2)
    footer_progress(f, GLOBAL_FRAC[6], ORANGE)
    return f


# ── Timeline ─────────────────────────────────────────────────────────────────────
SCENES = [
    (scene_title, 4.0),
    (scene_intake, 5.0),
    (scene_triage, 5.0),
    (scene_dispatch, 5.0),
    (scene_status, 5.0),
    (scene_survey, 5.5),
    (scene_outro, 4.0),
]
TOTAL_SEC = sum(d for _, d in SCENES)
# cumulative global progress fraction at the *start* of each scene
GLOBAL_FRAC = []
_acc = 0.0
for _, _d in SCENES:
    GLOBAL_FRAC.append(_acc / TOTAL_SEC)
    _acc += _d


def render_frames():
    frames = []
    for (fn, dur), gstart in zip(SCENES, GLOBAL_FRAC):
        nf = max(1, int(round(dur * FPS)))
        for i in range(nf):
            lt = i / max(1, nf - 1)
            # update global progress live within scene
            GLOBAL_FRAC_LIVE = gstart + (dur / TOTAL_SEC) * lt
            # temporarily expose live frac to scene via module global
            _set_live(GLOBAL_FRAC, SCENES.index((fn, dur)), GLOBAL_FRAC_LIVE)
            frames.append(fn(lt).buf)
    return frames


# helper so scenes read a live progress value without big refactor
_LIVE = {}
def _set_live(arr, idx, val):
    global GLOBAL_FRAC
    GLOBAL_FRAC = list(arr)
    GLOBAL_FRAC[idx] = val


# ── Background music (calm ambient pad, Am-F-C-G) ────────────────────────────────
def synth_music(nsamples):
    import array
    out = array.array('h', bytes(2 * nsamples))
    chords = [
        [220.00, 261.63, 329.63],   # Am
        [174.61, 220.00, 261.63],   # F
        [130.81, 164.81, 196.00],   # C
        [196.00, 246.94, 293.66],   # G
    ]
    chord_len = 2.5                 # seconds per chord
    arp_notes = [523.25, 659.25, 783.99, 659.25]  # gentle high arpeggio C5 E5 G5
    for n in range(nsamples):
        ts = n / SR
        ci = int(ts / chord_len) % len(chords)
        # position within chord for soft swell
        local = (ts % chord_len) / chord_len
        swell = 0.6 + 0.4 * math.sin(math.pi * local)     # 0.6..1.0 hump
        s = 0.0
        for k, fr in enumerate(chords[ci]):
            s += math.sin(2 * math.pi * fr * ts) * (0.5 if k == 0 else 0.32)
        # soft arpeggio bell every 0.5s
        beat = ts % 0.5
        an = arp_notes[int(ts / 0.5) % len(arp_notes)]
        env = math.exp(-beat * 6.0)
        s += math.sin(2 * math.pi * an * ts) * 0.18 * env
        s *= swell
        # global fade in/out
        fade = 1.0
        if ts < 1.0:
            fade = ts
        if ts > TOTAL_SEC - 1.2:
            fade = max(0.0, (TOTAL_SEC - ts) / 1.2)
        v = int(max(-1.0, min(1.0, s * AUDIO_AMP)) * fade * 32767)
        out[n] = v
    return out.tobytes()


# ── AVI muxer (uncompressed 8-bit DIB + PCM audio) ───────────────────────────────
def fourcc(s):
    return s.encode("ascii")


def build_avi(frames, audio_bytes):
    samples_per_frame = SR // FPS
    bytes_per_audio_chunk = samples_per_frame * 2
    nframes = len(frames)

    # video frame as bottom-up rows (DIB). W is multiple of 4 so no row padding.
    def flip(buf):
        out = bytearray(len(buf))
        for y in range(H):
            src = (H - 1 - y) * W
            out[y * W:(y + 1) * W] = buf[src:src + W]
        return bytes(out)

    flipped = [flip(b) for b in frames]
    frame_size = W * H

    # ---- assemble movi chunks + index ----
    movi = bytearray()
    idx = bytearray()
    movi += fourcc("movi")
    base = 4  # offsets are relative to 'movi' fourcc; first chunk at +4
    pos = 4
    for i, fr in enumerate(flipped):
        # video chunk 00db
        movi += fourcc("00db") + struct.pack("<I", frame_size) + fr
        idx += fourcc("00db") + struct.pack("<III", 0x10, pos, frame_size)
        pos += 8 + frame_size
        # audio chunk 01wb
        a0 = i * bytes_per_audio_chunk
        a1 = a0 + bytes_per_audio_chunk
        chunk = audio_bytes[a0:a1]
        if len(chunk) < bytes_per_audio_chunk:
            chunk = chunk + bytes(bytes_per_audio_chunk - len(chunk))
        movi += fourcc("01wb") + struct.pack("<I", len(chunk)) + chunk
        idx += fourcc("01wb") + struct.pack("<III", 0x10, pos, len(chunk))
        pos += 8 + len(chunk)

    # ---- headers ----
    # avih
    usec = int(1_000_000 / FPS)
    avih = struct.pack("<IIIIIIIIIIIIIIII",
        usec, W * H * FPS, 0, 0x10,
        nframes, 0, 2, frame_size,
        W, H, 0, 0, 0, 0, 0, 0)

    # video strh (vids)
    vstrh = struct.pack("<4s4sIHHIIIIIIIIhhhh",
        b"vids", b"DIB ", 0, 0, 0, 0, 1, FPS, 0, nframes,
        frame_size, 0xFFFFFFFF & (-1), 0, 0, 0, W, H)

    # video strf = BITMAPINFOHEADER + palette
    bih = struct.pack("<IiiHHIIiiII",
        40, W, H, 1, 8, 0, frame_size, 0, 0, 256, 256)
    pal = bytearray()
    for i in range(256):
        if i < len(PAL):
            r, g, b = PAL[i]
        else:
            r = g = b = 0
        pal += struct.pack("<BBBB", b, g, r, 0)
    vstrf = bih + bytes(pal)

    # audio strh (auds)
    block_align = 2
    avg_bps = SR * block_align
    n_audio_samples = len(audio_bytes) // 2
    astrh = struct.pack("<4s4sIHHIIIIIIIIhhhh",
        b"auds", b"\x00\x00\x00\x00", 0, 0, 0, 0,
        block_align, avg_bps, 0, n_audio_samples,
        bytes_per_audio_chunk, 0xFFFFFFFF & (-1), block_align, 0, 0, 0, 0)

    # audio strf = WAVEFORMATEX
    astrf = struct.pack("<HHIIHHH", 1, 1, SR, avg_bps, block_align, 16, 0)

    def chunk(tag, data):
        d = data
        out = fourcc(tag) + struct.pack("<I", len(d)) + d
        if len(d) & 1:
            out += b"\x00"
        return out

    def lst(tag, *parts):
        body = fourcc(tag) + b"".join(parts)
        return fourcc("LIST") + struct.pack("<I", len(body)) + body

    strl_v = lst("strl", chunk("strh", vstrh), chunk("strf", vstrf))
    strl_a = lst("strl", chunk("strh", astrh), chunk("strf", astrf))
    hdrl = lst("hdrl", chunk("avih", avih), strl_v, strl_a)

    movi_list = fourcc("LIST") + struct.pack("<I", len(movi)) + bytes(movi)
    idx1 = chunk("idx1", bytes(idx))

    body = fourcc("AVI ") + hdrl + movi_list + idx1
    riff = fourcc("RIFF") + struct.pack("<I", len(body)) + body
    return riff


def main():
    print("Rendering frames...")
    frames = render_frames()
    nframes = len(frames)
    print(f"  {nframes} frames @ {FPS}fps  ({nframes/FPS:.1f}s)")

    print("Synthesizing background music...")
    nsamples = (SR // FPS) * nframes
    audio = synth_music(nsamples)

    print("Muxing AVI...")
    data = build_avi(frames, audio)
    with open(OUT, "wb") as fh:
        fh.write(data)
    mb = len(data) / 1_048_576
    print(f"Wrote {OUT}  ({mb:.1f} MB, {nframes/FPS:.1f}s, {W}x{H})")


if __name__ == "__main__":
    main()
