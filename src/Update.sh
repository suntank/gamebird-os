#!/bin/bash
set -e

REPO_DIR="/home/pi/gamebird-os"
LOG_FILE="/home/pi/gamebird-os/update.log"
VERSION_FILE="/home/pi/gamebird-os/.last_update_commit"
CHANGELOG_FILE="/home/pi/gamebird-os/CHANGELOG.md"

PNGVIEW="/usr/local/bin/pngview"
UPDATE_MSG="/home/pi/gamebird/settings/update_os_msg.png"
PNG_PID=""
# Show update overlay (layer 19999 = topmost, bottom center) if PNG exists
if [ -f "$UPDATE_MSG" ]; then
    $PNGVIEW -d 0 -n -b 0x0000 -l 19999 -x 480 -y 640 "$UPDATE_MSG" &
    PNG_PID=$!
fi
echo "=== Game Bird OS Updater ===" | tee -a "$LOG_FILE"
echo "Started: $(date)" | tee -a "$LOG_FILE"

cd "$REPO_DIR"

echo "[1/5] Fetching latest code..." | tee -a "$LOG_FILE"

# Save current commit before pulling
OLD_COMMIT=$(git rev-parse HEAD)

git reset --hard HEAD >> "$LOG_FILE" 2>&1
git pull origin main >> "$LOG_FILE" 2>&1

NEW_COMMIT=$(git rev-parse HEAD)
echo "[2/5] Latest commit: $NEW_COMMIT" | tee -a "$LOG_FILE"
echo "$NEW_COMMIT" > "$VERSION_FILE"

# Generate changelog from git commits
echo "[3/5] Generating changelog..." | tee -a "$LOG_FILE"
{
    echo "# Game Bird OS Changelog"
    echo ""
    echo "## Recent Updates"
    echo ""
    if [ "$OLD_COMMIT" != "$NEW_COMMIT" ]; then
        git log --pretty=format:"- %s" "$OLD_COMMIT".."$NEW_COMMIT"
    else
        git log --pretty=format:"- %s" -10
    fi
    echo ""
    echo ""
    echo "---"
    echo "Updated: $(date '+%Y-%m-%d %H:%M')"
} > "$CHANGELOG_FILE"

echo "[4/6] Running installer..." | tee -a "$LOG_FILE"
if [ -x install.sh ]; then
    /home/pi/gamebird-os/install.sh >> "$LOG_FILE" 2>&1
else
    echo "No install.sh found or not executable." | tee -a "$LOG_FILE"
fi

echo "[5/6] Setting permissions on scripts..." | tee -a "$LOG_FILE"
chmod +x /home/pi/gamebird/settings/*.sh >> "$LOG_FILE" 2>&1 || true

echo "[6/6] Rebooting..." | tee -a "$LOG_FILE"
sleep 2

# Clean up overlay if it was started
if [ -n "$PNG_PID" ] && kill -0 "$PNG_PID" 2>/dev/null; then
    kill "$PNG_PID"
fi

sudo reboot