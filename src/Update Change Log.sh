#!/bin/bash
LOG=/tmp/changelog.log
{
    echo "---- LAUNCH $(date) ----"
    env | grep -E '^(LANG|PYTHON|SDL)'     # show env differences
    # run the script unbuffered so every print is flushed immediately
    /usr/bin/python3 -u /home/pi/gamebird/settings/show_changelog.py "$@"
    echo "---- EXIT CODE $? at $(date) ----"
} >> "$LOG" 2>&1

