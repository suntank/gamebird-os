#!/bin/bash
set -e

REPO_DIR="/home/pi/gamebird-os"
LOG_FILE="/home/pi/gamebird-os/update.log"
VERSION_FILE="/home/pi/gamebird-os/.last_update_commit"
CHANGELOG_FILE="/home/pi/gamebird-os/CHANGELOG.md"
PROGRESS_FIFO="/tmp/update_progress_fifo"
PROGRESS_SCRIPT="/home/pi/gamebird-os/src/update_progress.py"

# Start progress display
python3 "$PROGRESS_SCRIPT" &
PROGRESS_PID=$!
sleep 0.5  # Give pygame time to initialize and create FIFO

# Helper to send progress updates
send_progress() {
    if [ -p "$PROGRESS_FIFO" ]; then
        echo "$1" > "$PROGRESS_FIFO"
    fi
}

echo "=== Game Bird OS Updater ===" | tee -a "$LOG_FILE"
echo "Started: $(date)" | tee -a "$LOG_FILE"

cd "$REPO_DIR"

send_progress "MSG:Updating..."
send_progress "PCT:10"
echo "[1/5] Fetching latest code..." | tee -a "$LOG_FILE"

# Save current commit before pulling
OLD_COMMIT=$(git rev-parse HEAD)

git reset --hard HEAD >> "$LOG_FILE" 2>&1
git pull origin main >> "$LOG_FILE" 2>&1

NEW_COMMIT=$(git rev-parse HEAD)
send_progress "PCT:30"
echo "[2/5] Latest commit: $NEW_COMMIT" | tee -a "$LOG_FILE"
echo "$NEW_COMMIT" > "$VERSION_FILE"

# Generate changelog from git commits
send_progress "PCT:40"
echo "[3/5] Generating changelog..." | tee -a "$LOG_FILE"
{
    echo "# $(date '+%Y-%m-%d %H:%M')"
    echo ""
    if [ "$OLD_COMMIT" != "$NEW_COMMIT" ]; then
        # Get the latest commit's subject and body
        git log -1 --pretty=format:"## %s" "$NEW_COMMIT"
        echo ""
        BODY=$(git log -1 --pretty=format:"%b" "$NEW_COMMIT" | sed '/^$/d')
        if [ -n "$BODY" ]; then
            echo "$BODY" | while read -r line; do
                echo "- $line"
            done
        fi
    else
        git log -1 --pretty=format:"## %s"
        echo ""
        BODY=$(git log -1 --pretty=format:"%b" | sed '/^$/d')
        if [ -n "$BODY" ]; then
            echo "$BODY" | while read -r line; do
                echo "- $line"
            done
        fi
    fi
    echo ""
} > "$CHANGELOG_FILE"

send_progress "PCT:60"
echo "[4/6] Running installer..." | tee -a "$LOG_FILE"
INSTALL_SCRIPT="$REPO_DIR/install.sh"
if [ -f "$INSTALL_SCRIPT" ]; then
    chmod +x "$INSTALL_SCRIPT"
    "$INSTALL_SCRIPT" >> "$LOG_FILE" 2>&1
else
    echo "No install.sh found." | tee -a "$LOG_FILE"
fi

send_progress "PCT:80"
echo "[5/6] Setting permissions on scripts..." | tee -a "$LOG_FILE"
chmod +x /home/pi/gamebird/settings/*.sh >> "$LOG_FILE" 2>&1 || true

send_progress "PCT:100"
send_progress "MSG:Rebooting..."
echo "[6/6] Rebooting..." | tee -a "$LOG_FILE"
sleep 2

# Clean up progress display
send_progress "QUIT"
sleep 0.2
if kill -0 "$PROGRESS_PID" 2>/dev/null; then
    kill "$PROGRESS_PID"
fi

sudo reboot