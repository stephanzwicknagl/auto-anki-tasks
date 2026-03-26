#!/usr/bin/env bash
set -euo pipefail

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

# Run the maintenance script
"$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/maintain_cards.py" --dry-run
EXIT_CODE=$?

# Sync to AnkiWeb, then kill.
# guiExitAnki is unreliable headlessly (hangs on sync dialog), so we sync
# explicitly via AnkiConnect and force-kill after.
echo "Syncing to AnkiWeb..."
curl -s -X POST "$ANKI_CONNECT_URL" \
    -H "Content-Type: application/json" \
    -d '{"action":"sync","version":6}' > /dev/null
sleep 5  # sync runs async in Anki; give it time to finish before killing

echo "Closing Anki..."
flatpak kill "net.ankiweb.Anki" 2>/dev/null || true

exit $EXIT_CODE
