#!/bin/bash

CONFIG_DIR="/opt/retropie/configs/all/emulationstation"
ACTIVE="$CONFIG_DIR/es_systems.cfg"
WITH="$CONFIG_DIR/es_systems_with_retropie.cfg"
WITHOUT="$CONFIG_DIR/es_systems_without_retropie.cfg"
LOG="/tmp/toggle_retropie_swap.log"

# Relaunch as sudo if needed
if [[ "$EUID" -ne 0 ]]; then
  echo "Re-running with sudo..." | tee -a "$LOG"
  exec sudo "$0" "$@"
fi

# Determine which config is active
if grep -q "<name>retropie</name>" "$ACTIVE"; then
  echo "[INFO] Found RetroPie. Switching to NO RetroPie..." | tee -a "$LOG"
  cp "$WITHOUT" "$ACTIVE"
else
  echo "[INFO] No RetroPie. Switching to WITH RetroPie..." | tee -a "$LOG"
  cp "$WITH" "$ACTIVE"
fi

echo "[INFO] Rebooting to apply menu change…" | tee -a "$LOG"
reboot



