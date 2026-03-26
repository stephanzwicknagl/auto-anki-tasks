#!/usr/bin/env bash
set -euo pipefail

# Cron runs with a minimal environment — set everything needed explicitly.
export PATH="/usr/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/gcloud/anki-tts.json"

# Wayland/Flatpak session variables (not set in cron)
export DISPLAY=":0"
export WAYLAND_DISPLAY="wayland-0"
export XDG_RUNTIME_DIR="/run/user/1000"
export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/1000/bus"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ANKI_CONNECT_URL="http://localhost:8765"

# Start Anki in the background
echo "Starting Anki..."
flatpak run net.ankiweb.Anki > /dev/null 2>&1 &
ANKI_PID=$!

# Wait for AnkiConnect to become available (up to 30s)
echo "Waiting for AnkiConnect..."
for i in $(seq 1 30); do
    if curl -sf -o /dev/null "$ANKI_CONNECT_URL"; then
        echo "AnkiConnect ready."
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "AnkiConnect did not start in time." >&2
        kill "$ANKI_PID" 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

# Sync to AnkiWeb
echo "Syncing to AnkiWeb..."
curl -s -X POST "$ANKI_CONNECT_URL" \
    -H "Content-Type: application/json" \
    -d '{"action":"sync","version":6}' > /dev/null

# Run the maintenance script
"$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/maintain_cards.py"
EXIT_CODE=$?

# Sync to AnkiWeb
echo "Syncing to AnkiWeb..."
curl -s -X POST "$ANKI_CONNECT_URL" \
    -H "Content-Type: application/json" \
    -d '{"action":"sync","version":6}' > /dev/null
sleep 5

echo "Closing Anki..."
curl -s -X POST "$ANKI_CONNECT_URL" \
    -H "Content-Type: application/json" \
    -d '{"action":"guiExitAnki","version":6}' > /dev/null
sleep 3
flatpak kill "net.ankiweb.Anki" 2>/dev/null || true

exit $EXIT_CODE
