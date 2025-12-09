#!/bin/bash
set -e

REPO_DIR="/home/pi/gamebird-os"
LOG_FILE="/home/pi/gamebird-os/update.log"
VERSION_FILE="/home/pi/gamebird-os/.last_update_commit"
CHANGELOG_FILE="/home/pi/gamebird-os/CHANGELOG.md"

PNGVIEW="/usr/local/bin/pngview"
UPDATE_MSG="/home/pi/gamebird/settings/update_os_msg.png"
# Show update overlay (layer 19999 = topmost, bottom center)
$PNGVIEW -d 0 -n -b 0x0000 -l 19999 -x 480 -y 640 $UPDATE_MSG &
PNG_PID=$!
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

echo "[4/5] Running installer..." | tee -a "$LOG_FILE"
if [ -x install.sh ]; then
    /home/pi/gamebird-os/install.sh >> "$LOG_FILE" 2>&1
else
    echo "No install.sh found or not executable." | tee -a "$LOG_FILE"
fi

echo "[5/5] Rebooting..." | tee -a "$LOG_FILE"
sleep 2

kill $PNG_PID
rm "$UPDATE_MSG"

sudo reboot