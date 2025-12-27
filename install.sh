#!/bin/bash
set -e

# Paths
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="$REPO_DIR/src"
TARGET_SETTINGS_DIR="/home/pi/gamebird/settings"
TARGET_OVERLAY_DIR="/home/pi/scripts/gbz_overlay"
LOG_FILE="$REPO_DIR/install.log"

ROOT_REMOUNTED=0
cleanup() {
    if [ "$ROOT_REMOUNTED" -eq 1 ]; then
        mount -o remount,ro / 2>/dev/null || true
    fi
}
trap cleanup EXIT

echo "=== Game Bird Installer ===" | tee -a "$LOG_FILE"
echo "Started: $(date)" | tee -a "$LOG_FILE"

# Ensure target directories exist
mkdir -p "$TARGET_SETTINGS_DIR"
mkdir -p "$TARGET_OVERLAY_DIR"

# 1. Copy src files to settings (except overlay.py)
if [ -d "$SRC_DIR" ]; then
    echo "Copying src files to settings..." | tee -a "$LOG_FILE"
    for file in "$SRC_DIR"/*; do
        # Skip directories and overlay.py
        [ -d "$file" ] && continue
        filename=$(basename "$file")
        [ "$filename" = "overlay.py" ] && continue
        
        target="$TARGET_SETTINGS_DIR/$filename"
        
        # Only copy if source is newer, different size, or target doesn't exist
        if [ ! -f "$target" ] || [ "$file" -nt "$target" ] || [ "$(stat -c%s "$file")" != "$(stat -c%s "$target")" ]; then
            echo "Installing: $filename" | tee -a "$LOG_FILE"
            cp "$file" "$target"
            # Make shell scripts executable
            [[ "$filename" == *.sh ]] && chmod +x "$target"
        else
            echo "Up to date: $filename" | tee -a "$LOG_FILE"
        fi
    done
else
    echo "No src directory found." | tee -a "$LOG_FILE"
fi

# 2. Copy nest-frontend directory to settings
NEST_SRC="$SRC_DIR/nest-frontend"
NEST_TARGET="$TARGET_SETTINGS_DIR/nest-frontend"
if [ -d "$NEST_SRC" ]; then
    echo "Copying nest-frontend..." | tee -a "$LOG_FILE"
    # Use find to iterate all files recursively
    find "$NEST_SRC" -type f | while read -r file; do
        # Get relative path from nest-frontend
        rel_path="${file#$NEST_SRC/}"
        target="$NEST_TARGET/$rel_path"
        target_dir=$(dirname "$target")
        
        # Create target directory if needed
        mkdir -p "$target_dir"
        
        # Only copy if source is newer, different size, or target doesn't exist
        if [ ! -f "$target" ] || [ "$file" -nt "$target" ] || [ "$(stat -c%s "$file")" != "$(stat -c%s "$target")" ]; then
            echo "Installing: nest-frontend/$rel_path" | tee -a "$LOG_FILE"
            cp "$file" "$target"
        else
            echo "Up to date: nest-frontend/$rel_path" | tee -a "$LOG_FILE"
        fi
    done
else
    echo "nest-frontend not found." | tee -a "$LOG_FILE"
fi

# 3. Copy overlay.py to gbz_overlay
if [ -f "$SRC_DIR/overlay.py" ]; then
    target="$TARGET_OVERLAY_DIR/overlay.py"
    if [ ! -f "$target" ] || [ "$SRC_DIR/overlay.py" -nt "$target" ] || [ "$(stat -c%s "$SRC_DIR/overlay.py")" != "$(stat -c%s "$target")" ]; then
        echo "Installing: overlay.py -> $TARGET_OVERLAY_DIR" | tee -a "$LOG_FILE"
        cp "$SRC_DIR/overlay.py" "$target"
    else
        echo "Up to date: overlay.py" | tee -a "$LOG_FILE"
    fi
else
    echo "overlay.py not found in src." | tee -a "$LOG_FILE"
fi

if [ -d "$REPO_DIR/services" ]; then
    if [ "$(id -u)" -eq 0 ]; then
        root_opts="$(findmnt -no OPTIONS / 2>/dev/null || true)"
        if echo ",$root_opts," | grep -q ",ro,"; then
            echo "Remounting / as rw" | tee -a "$LOG_FILE"
            mount -o remount,rw / 2>/dev/null && ROOT_REMOUNTED=1 || true
        fi
        if ls "$REPO_DIR/services/"*.service >/dev/null 2>&1; then
            echo "Installing systemd services..." | tee -a "$LOG_FILE"
            cp "$REPO_DIR/services/"*.service /etc/systemd/system/
            systemctl daemon-reload
            systemctl enable fbcp-ili9341.service
        fi
    else
        echo "Not running as root; skipping systemd service install." | tee -a "$LOG_FILE"
    fi
fi

# # 2. Copy service files EXAMPLE
# if [ -d "$REPO_DIR/services" ]; then
#     echo "[2/3] Installing systemd services..." | tee -a "$LOG_FILE"
#     cp "$REPO_DIR/services/"*.service /etc/systemd/system/
#     systemctl daemon-reexec
#     systemctl daemon-reload
#     systemctl enable gamebird-overlay.service 2>/dev/null || true
# else
#     echo "No services to install." | tee -a "$LOG_FILE"
# fi

# 3. Log version
if [ -f "$REPO_DIR/.last_update_commit" ]; then
    echo "Updated to commit:" | tee -a "$LOG_FILE"
    cat "$REPO_DIR/.last_update_commit" | tee -a "$LOG_FILE"
fi

echo "Install finished: $(date)" | tee -a "$LOG_FILE"
exit 0
