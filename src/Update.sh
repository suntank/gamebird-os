#!/bin/bash
set -e

REPO_DIR="/home/pi/gamebird-os"
LOG_FILE="/home/pi/gamebird-os/update.log"
VERSION_FILE="/home/pi/gamebird-os/.last_update_commit"

PNGVIEW="/usr/local/bin/pngview"
UPDATE_MSG="/home/pi/gamebird/settings/update_os_msg.png"
GITHUB_TOKEN="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"
# Show update overlay (layer 19999 = topmost, bottom center)
$PNGVIEW -d 0 -n -b 0x0000 -l 19999 -x 480 -y 640 $UPDATE_MSG &
PNG_PID=$!
echo "=== Game Bird OS Updater ===" | tee -a "$LOG_FILE"
echo "Started: $(date)" | tee -a "$LOG_FILE"

cd "$REPO_DIR"

echo "[1/4] Fetching latest code..." | tee -a "$LOG_FILE"
git reset --hard HEAD >> "$LOG_FILE" 2>&1

# Use token from environment variable for security
if [ -z "$GITHUB_TOKEN" ]; then
    echo "GITHUB_TOKEN not set!" | tee -a "$LOG_FILE"
    kill $PNG_PID
    exit 1
fi
git pull https://suntank:$GITHUB_TOKEN@github.com/suntank/gamebird-os.git main >> "$LOG_FILE" 2>&1

NEW_COMMIT=$(git rev-parse HEAD)
echo "[2/4] Latest commit: $NEW_COMMIT" | tee -a "$LOG_FILE"
echo "$NEW_COMMIT" > "$VERSION_FILE"

echo "[3/4] Running installer..." | tee -a "$LOG_FILE"
if [ -x install.sh ]; then
    /home/pi/gamebird-os/install.sh >> "$LOG_FILE" 2>&1
else
    echo "No install.sh found or not executable." | tee -a "$LOG_FILE"
fi

echo "[4/4] Rebooting..." | tee -a "$LOG_FILE"
sleep 2

kill $PNG_PID
rm "$UPDATE_MSG"

sudo reboot