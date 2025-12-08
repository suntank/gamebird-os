#!/bin/bash
LOG=/tmp/nest-frontend.log
{
    echo "---- LAUNCH $(date) ----"
    env | grep -E '^(LANG|PYTHON|SDL)'     # show env differences
    
    # Change to the game directory so relative paths work
    cd /home/pi/gamebird/settings/nest-frontend || exit 1
    
    # run the script unbuffered so every print is flushed immediately
    /usr/bin/python3 -u /home/pi/gamebird/settings/nest-frontend/main.py "$@"
    echo "---- EXIT CODE $? at $(date) ----"
} >> "$LOG" 2>&1

