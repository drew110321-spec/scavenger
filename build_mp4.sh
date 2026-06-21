#!/usr/bin/env bash
# Build a phone-playable MP4 (H.264 + AAC) with the background music baked in.
#
# This needs ffmpeg, which the Claude Code sandbox does not have. Run it on any
# machine that has ffmpeg installed (macOS: `brew install ffmpeg`,
# Ubuntu/Debian: `sudo apt install ffmpeg`).
#
#   1. python3 make_video.py      # produces roadai_demo.avi (video)
#   2. python3 make_gif.py        # optional: roadai_demo.gif
#   3. ./build_mp4.sh             # produces roadai_demo.mp4 (video + music)
set -euo pipefail

[ -f roadai_demo.avi ] || { echo "roadai_demo.avi missing — run: python3 make_video.py"; exit 1; }

# Regenerate the soundtrack WAV if it isn't present.
if [ ! -f roadai_music.wav ]; then
  python3 - <<'PY'
import wave, make_video as mv
n = (mv.SR // mv.FPS) * 201
with wave.open("roadai_music.wav", "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(mv.SR)
    w.writeframes(mv.synth_music(n))
print("wrote roadai_music.wav")
PY
fi

ffmpeg -y \
  -i roadai_demo.avi \
  -i roadai_music.wav \
  -map 0:v:0 -map 1:a:0 \
  -c:v libx264 -pix_fmt yuv420p -preset medium -crf 20 \
  -c:a aac -b:a 128k \
  -movflags +faststart -shortest \
  roadai_demo.mp4

echo "Wrote roadai_demo.mp4 — plays on phones with sound."
