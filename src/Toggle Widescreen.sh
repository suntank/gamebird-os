#!/bin/bash
LOG=/tmp/toggle_widescreen.log
{
    echo "---- TOGGLE LAUNCH $(date) ----"
    env | grep -E '^(LANG|PYTHON|SDL|XDG)'  # Debug: show ES environment

    # Use full paths to all commands
    CONFIG_FILE="/boot/config.txt"
    REBOOT_CMD="/sbin/reboot"
    SED_CMD="/bin/sed"
    GREP_CMD="/bin/grep"
    CUT_CMD="/usr/bin/cut"
    ECHO_CMD="/bin/echo"

    # Run as root or escalate
    if [[ "$EUID" -ne 0 ]]; then
        $ECHO_CMD "Re-launching with sudo"
        exec sudo "$0" "$@"
    fi

    # Ensure both lines exist
    $GREP_CMD -q "^hdmi_mode=" "$CONFIG_FILE" || $ECHO_CMD "hdmi_mode=87" >> "$CONFIG_FILE"
    $GREP_CMD -q "^hdmi_group=" "$CONFIG_FILE" || $ECHO_CMD "hdmi_group=2" >> "$CONFIG_FILE"

    CURRENT_MODE=$($GREP_CMD "^hdmi_mode=" "$CONFIG_FILE" | $CUT_CMD -d= -f2)
    CURRENT_GROUP=$($GREP_CMD "^hdmi_group=" "$CONFIG_FILE" | $CUT_CMD -d= -f2)

    if [[ "$CURRENT_MODE" == "4" ]]; then
        $SED_CMD -i 's/^hdmi_mode=4/hdmi_mode=87/' "$CONFIG_FILE"
        $SED_CMD -i 's/^hdmi_group=1/hdmi_group=2/' "$CONFIG_FILE"
        $ECHO_CMD "Switched to hdmi_mode=87 / hdmi_group=2 (widescreen)"
    elif [[ "$CURRENT_MODE" == "87" ]]; then
        $SED_CMD -i 's/^hdmi_mode=87/hdmi_mode=4/' "$CONFIG_FILE"
        $SED_CMD -i 's/^hdmi_group=2/hdmi_group=1/' "$CONFIG_FILE"
        $ECHO_CMD "Switched to hdmi_mode=4 / hdmi_group=1 (safe mode)"
    else
        $ECHO_CMD "Unknown hdmi_mode=$CURRENT_MODE — skipping toggle"
        exit 1
    fi

    $ECHO_CMD "Rebooting now..."
    $REBOOT_CMD

    echo "---- EXIT at $(date) ----"
} >> "$LOG" 2>&1
