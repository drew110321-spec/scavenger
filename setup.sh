#!/usr/bin/env bash
# One-time setup for Hey Claude voice assistant
set -euo pipefail

echo "=== Hey Claude Setup ==="

# Install system audio libraries
if command -v apt-get &>/dev/null; then
    echo "→ Installing system deps (Debian/Ubuntu)…"
    sudo apt-get install -y python3-pip portaudio19-dev python3-pyaudio
elif command -v pacman &>/dev/null; then
    echo "→ Installing system deps (Arch)…"
    sudo pacman -S --noconfirm python-pyaudio portaudio
elif command -v brew &>/dev/null; then
    echo "→ Installing system deps (macOS)…"
    brew install portaudio
elif command -v pkg &>/dev/null; then
    # Termux (Android)
    echo "→ Installing system deps (Termux/Android)…"
    pkg install -y python portaudio
fi

echo "→ Installing Python packages…"
pip3 install -r requirements.txt

if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "✓ Created .env  ← Edit this file with your credentials before running!"
else
    echo "✓ .env already exists"
fi

echo ""
echo "=== Setup complete ==="
echo "1. Edit .env with your ANTHROPIC_API_KEY and Gmail credentials"
echo "2. Run:  python3 voice_assistant.py"
echo "3. Say:  'Hey Claude, <your request>'"
