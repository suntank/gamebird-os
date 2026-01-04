#!/bin/bash
set -e

# Paths
REPO_DIR="/home/pi/gamebird-os"
SRC_DIR="$REPO_DIR/src"
TARGET_SETTINGS_DIR="/home/pi/gamebird/settings"
TARGET_OVERLAY_DIR="/home/pi/scripts/gbz_overlay"
LOG_FILE="$REPO_DIR/install.log"

echo "=== Game Bird Installer ===" | tee -a "$LOG_FILE"
echo "Started: $(date)" | tee -a "$LOG_FILE"

# Check if filesystem is read-only and remount if needed
if [ ! -w / ]; then
    echo "Remounting filesystem as read-write..." | tee -a "$LOG_FILE"
    sudo mount -o remount,rw / || {
        echo "ERROR: Failed to remount filesystem as read-write" | tee -a "$LOG_FILE"
        exit 1
    }
    echo "Filesystem remounted as read-write" | tee -a "$LOG_FILE"
fi

# Ensure target directories exist
mkdir -p "$TARGET_SETTINGS_DIR"
mkdir -p "$TARGET_OVERLAY_DIR"
mkdir -p "/usr/local/bin"

# 1. Copy src files to settings (except overlay.py)oh
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

# 4. Install fbcp-ili9341 binary with tone mapping support
FBCP_BIN="$SRC_DIR/fbcp-ili9341.bin"
FBCP_TARGET="/usr/local/bin/fbcp-ili9341"

if [ -f "$FBCP_BIN" ]; then
    if [ ! -f "$FBCP_TARGET" ] || [ "$FBCP_BIN" -nt "$FBCP_TARGET" ] || [ "$(stat -c%s "$FBCP_BIN")" != "$(stat -c%s "$FBCP_TARGET")" ]; then
        echo "Installing: fbcp-ili9341 -> /usr/local/bin" | tee -a "$LOG_FILE"
        
        # Stop service before replacing binary
        sudo systemctl stop fbcp-early.service 2>/dev/null || true
        sleep 1
        
        # Backup old binary if exists
        [ -f "$FBCP_TARGET" ] && sudo mv "$FBCP_TARGET" "$FBCP_TARGET.backup" 2>/dev/null || true
        
        # Install new binary
        sudo cp "$FBCP_BIN" "$FBCP_TARGET"
        sudo chmod +x "$FBCP_TARGET"
        echo "fbcp-ili9341 installed to /usr/local/bin" | tee -a "$LOG_FILE"
        
        # Restart service
        sudo systemctl start fbcp-early.service 2>/dev/null || true
    else
        echo "Up to date: fbcp-ili9341" | tee -a "$LOG_FILE"
    fi
else
    echo "fbcp-ili9341.bin not found in src." | tee -a "$LOG_FILE"
fi

# 5. Copy dimming_client.py to overlay directory for brightness control
if [ -f "$SRC_DIR/dimming_client.py" ]; then
    target="$TARGET_OVERLAY_DIR/dimming_client.py"
    if [ ! -f "$target" ] || [ "$SRC_DIR/dimming_client.py" -nt "$target" ] || [ "$(stat -c%s "$SRC_DIR/dimming_client.py")" != "$(stat -c%s "$target")" ]; then
        echo "Installing: dimming_client.py -> $TARGET_OVERLAY_DIR" | tee -a "$LOG_FILE"
        cp "$SRC_DIR/dimming_client.py" "$target"
    else
        echo "Up to date: dimming_client.py (overlay)" | tee -a "$LOG_FILE"
    fi
fi

# 6. Update fbcp-early.service to set socket permissions
FBCP_SERVICE="/etc/systemd/system/fbcp-early.service"
FBCP_SERVICE_MODIFIED=false
if [ -f "$FBCP_SERVICE" ]; then
    # Check if ExecStartPost for socket permissions exists
    if ! grep -q "chmod 777 /run/fbcp-ili9341.sock" "$FBCP_SERVICE"; then
        echo "Updating fbcp-early.service for socket permissions..." | tee -a "$LOG_FILE"
        # Add ExecStartPost line after ExecStart if not present
        sudo sed -i '/^ExecStart=/a ExecStartPost=/bin/bash -c "sleep 2 \&\& chmod 777 /run/fbcp-ili9341.sock 2>/dev/null || true"' "$FBCP_SERVICE"
        sudo systemctl daemon-reload
        FBCP_SERVICE_MODIFIED=true
        echo "fbcp-early.service updated" | tee -a "$LOG_FILE"
    else
        echo "Up to date: fbcp-early.service" | tee -a "$LOG_FILE"
    fi
    
    # Restart service if modified to apply socket permissions
    if [ "$FBCP_SERVICE_MODIFIED" = true ]; then
        echo "Restarting fbcp-early.service to apply socket permissions..." | tee -a "$LOG_FILE"
        sudo systemctl restart fbcp-early.service 2>/dev/null || true
        sleep 3
    fi
    
    # Always ensure socket has correct permissions (handles previously failed installs)
    if [ -S "/run/fbcp-ili9341.sock" ]; then
        SOCK_PERMS=$(stat -c "%a" /run/fbcp-ili9341.sock 2>/dev/null || echo "000")
        if [ "$SOCK_PERMS" != "777" ]; then
            echo "Fixing socket permissions (was $SOCK_PERMS)..." | tee -a "$LOG_FILE"
            sudo chmod 777 /run/fbcp-ili9341.sock 2>/dev/null || true
            echo "Socket permissions fixed" | tee -a "$LOG_FILE"
        else
            echo "Socket permissions OK" | tee -a "$LOG_FILE"
        fi
    else
        echo "WARNING: Socket /run/fbcp-ili9341.sock not found" | tee -a "$LOG_FILE"
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

# 7. Log version
if [ -f "$REPO_DIR/.last_update_commit" ]; then
    echo "Updated to commit:" | tee -a "$LOG_FILE"
    cat "$REPO_DIR/.last_update_commit" | tee -a "$LOG_FILE"
fi

echo "Install finished: $(date)" | tee -a "$LOG_FILE"
exit 0
