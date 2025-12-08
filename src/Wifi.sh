#!/bin/bash
LOG=/tmp/wifi_setup_full.log
{
    echo "---- LAUNCH $(date) ----"
    env | grep -E '^(LANG|PYTHON|SDL)'     # show env differences
    # run the script unbuffered so every print is flushed immediately
    /usr/bin/python3 -u /home/pi/gamebird/settings/wifi_setup.py "$@"
    echo "---- EXIT CODE $? at $(date) ----"
} >> "$LOG" 2>&1

