#!/usr/bin/env bash
# Launch Hey Claude (works with screen off on Android/Termux via wakelock)
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# On Android (Termux) acquire a CPU wakelock so it keeps running with screen off
if command -v termux-wake-lock &>/dev/null; then
    echo "→ Acquiring wakelock (screen-off mode enabled)"
    termux-wake-lock
fi

# On Linux, optionally install as a background service instead:
#   sudo cp claude-assistant.service /etc/systemd/system/
#   sudo systemctl enable --now claude-assistant

python3 voice_assistant.py
