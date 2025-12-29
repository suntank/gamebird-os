#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Game Bird – Hot-plug manager w/ PID-based fbcp restart

• EDID-based HDMI detection (works with hdmi_force_hotplug=1)
• Audio swap via amixer + asound.conf + ~/.asoundrc + runcommand override
• mk_arcade_joystick_rpi enable/disable
• Proper PID-based restart of fbcp-ili9341 so SPI never freezes
"""

import os
import signal
import time
import pathlib
import pwd
import shutil
import subprocess as sp
import tempfile
from glob import glob

POLL_DELAY = 2  # seconds
FBCP_CMD   = "/usr/local/bin/fbcp-ili9341"
FBCP_ARGS  = ["-x", "200", "-y", "120", "-w", "240", "-h", "240", "-noscaling"]

# -------------------------------------------------------------------------------
# HDMI detection (EDID)
# -------------------------------------------------------------------------------

def _kms_edid_present() -> bool:
    for edid in glob("/sys/class/drm/card*-HDMI-A-*/edid"):
        try:
            if pathlib.Path(edid).stat().st_size >= 128:
                return True
        except FileNotFoundError:
            pass
    return False


def _legacy_edid_present() -> bool:
    """Fallback for FKMS/DispmanX systems (tvservice)."""
    with tempfile.NamedTemporaryFile() as tmp:
        try:
            r = sp.run(
                ["/usr/bin/tvservice", "-d", tmp.name],
                stdout=sp.DEVNULL, stderr=sp.DEVNULL, timeout=3
            )
            if r.returncode == 0 and pathlib.Path(tmp.name).stat().st_size >= 128:
                return True
        except (FileNotFoundError, sp.TimeoutExpired):
            pass
    return False


def hdmi_connected() -> bool:
    return _kms_edid_present() or _legacy_edid_present()

# -------------------------------------------------------------------------------
# Audio swap + runcommand override
# -------------------------------------------------------------------------------

HDMI_CARD, HDMI_VOL_ID, HDMI_SW_ID = "0", "1", "2"
HP_CARD,   HP_VOL_ID,   HP_SW_ID   = "1", "1", "2"
DESIRED_VOL = "250"  # 0-400

ASOUND_DEFAULT = "/etc/asound.conf"
ASOUND_USER    = pathlib.Path(pwd.getpwnam("pi").pw_dir) / ".asoundrc"
ASOUND_HDMI    = "/etc/asound.hdmi.conf"
ASOUND_HP      = "/etc/asound.hp.conf"
RUNCOMMAND_CFG = "/opt/retropie/configs/all/runcommand.cfg"


def _ensure_snippets():
    default_hdmi = "defaults.pcm.card 0\ndefaults.ctl.card 0\n"
    default_hp   = "defaults.pcm.card 1\ndefaults.ctl.card 1\n"
    
    if not pathlib.Path(ASOUND_HDMI).exists():
        log("Warning: /etc/asound.hdmi.conf missing, using fallback")
        try:
            pathlib.Path("/home/pi/.asound.hdmi.conf").write_text(default_hdmi)
        except Exception:
            pass
    if not pathlib.Path(ASOUND_HP).exists():
        log("Warning: /etc/asound.hp.conf missing, using fallback")
        try:
            pathlib.Path("/home/pi/.asound.hp.conf").write_text(default_hp)
        except Exception:
            pass


def _swap_asound(to_hdmi: bool):
    _ensure_snippets()
    src = ASOUND_HDMI if to_hdmi else ASOUND_HP
    for dst in (ASOUND_DEFAULT, ASOUND_USER):
        try:
            p = pathlib.Path(dst)
            if not p.exists() or p.read_bytes() != pathlib.Path(src).read_bytes():
                shutil.copy(src, dst)
        except (PermissionError, FileNotFoundError):
            pass
    try:
        sp.run(["alsactl", "restore"], stdout=sp.DEVNULL, stderr=sp.DEVNULL, timeout=5)
    except sp.TimeoutExpired:
        pass
    
    # RetroPie runcommand audio_device override
    desired = "hdmi" if to_hdmi else "local"
    try:
        try:
            lines = pathlib.Path(RUNCOMMAND_CFG).read_text().splitlines()
        except FileNotFoundError:
            lines = []
        lines = [l for l in lines if not l.startswith("audio_device=")]
        lines.append(f"audio_device={desired}")
        pathlib.Path(RUNCOMMAND_CFG).write_text("\n".join(lines) + "\n")
    except PermissionError:
        pass


def _amixer(card: str, numid: str, value: str):
    """Robust amixer helper with up-to-three retries."""
    for _ in range(3):
        try:
            sp.run(
                ["amixer", "-q", "-c", card, "cset", f"numid={numid}", value],
                stdout=sp.DEVNULL, stderr=sp.DEVNULL, timeout=2
            )
            out = sp.check_output(
                ["amixer", "-c", card, "cget", f"numid={numid}"],
                text=True, timeout=2
            )
            if value.isdigit():
                if f"values={value}" in out:
                    break
            else:
                if f"[{value}]" in out:
                    break
        except (sp.TimeoutExpired, sp.CalledProcessError):
            pass
        time.sleep(0.1)


def set_audio(to_hdmi: bool):
    if to_hdmi:
        _amixer(HDMI_CARD, HDMI_SW_ID, "1")
        _amixer(HDMI_CARD, HDMI_VOL_ID, DESIRED_VOL)
        _amixer(HP_CARD,   HP_SW_ID,   "0")
        _amixer(HP_CARD,   HP_VOL_ID,  "0")
    else:
        _amixer(HP_CARD,   HP_SW_ID,   "1")
        _amixer(HP_CARD,   HP_VOL_ID,  DESIRED_VOL)
        _amixer(HDMI_CARD, HDMI_SW_ID, "0")
        _amixer(HDMI_CARD, HDMI_VOL_ID, "0")
    _swap_asound(to_hdmi)

# -------------------------------------------------------------------------------
# Joystick HAT toggle
# -------------------------------------------------------------------------------

def hat_loaded() -> bool:
    return pathlib.Path("/sys/module/mk_arcade_joystick_rpi").exists()


def toggle_hat(enable: bool):
    if enable and not hat_loaded():
        sp.call(["modprobe", "mk_arcade_joystick_rpi"])
    elif not enable and hat_loaded():
        sp.call(["modprobe", "-r", "mk_arcade_joystick_rpi"])

# -------------------------------------------------------------------------------
# fbcp management
# -------------------------------------------------------------------------------

def get_fbcp_pids() -> list:
    """Get list of fbcp-ili9341 PIDs."""
    try:
        out = sp.check_output(["pidof", os.path.basename(FBCP_CMD)], text=True, timeout=2).strip()
        return [int(p) for p in out.split()]
    except (sp.CalledProcessError, sp.TimeoutExpired):
        return []


def fbcp_running() -> bool:
    """Check if fbcp-ili9341 is currently running."""
    return len(get_fbcp_pids()) > 0


def kill_fbcp_pids(pids: list):
    """Kill specific fbcp PIDs."""
    # SIGTERM first
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    # Wait up to 1s for graceful exit
    for _ in range(10):
        alive = [pid for pid in pids if os.path.exists(f"/proc/{pid}")]
        if not alive:
            break
        time.sleep(0.1)
    else:
        # Force-kill survivors
        for pid in alive:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        time.sleep(0.1)


def start_fbcp():
    """Start a new fbcp instance."""
    sp.Popen([FBCP_CMD] + FBCP_ARGS, stdout=sp.DEVNULL, stderr=sp.DEVNULL)
    time.sleep(0.5)  # give DMA a moment to settle


def restart_fbcp():
    """Kill all fbcp instances and start a fresh one."""
    # Kill any running instances directly by PID (don't use systemctl)
    pids = get_fbcp_pids()
    if pids:
        kill_fbcp_pids(pids)
    
    # Start fresh instance
    start_fbcp()

# -------------------------------------------------------------------------------
# Main loop with debounce
# -------------------------------------------------------------------------------

def log(msg: str):
    print(f"[HotPlug] {time.strftime('%Y-%m-%d %H:%M:%S')} | {msg}", flush=True)


def main():
    log("hotplug_manager starting")
    
    # Check if fbcp is already running (from fbcp-early.service)
    # If so, just let it run - don't touch it, don't stop the service
    if fbcp_running():
        log("fbcp already running from fbcp-early.service, will manage from here")
    else:
        log("fbcp not running, starting it")
        start_fbcp()

    last_state = None
    stable_state = None
    stable_count = 0
    DEBOUNCE_POLLS = 3  # Require 3 consecutive same readings (6 seconds at POLL_DELAY=2)

    while True:
        conn = hdmi_connected()
        
        # Debounce: only act after stable_count consecutive same readings
        if conn == stable_state:
            stable_count += 1
        else:
            stable_state = conn
            stable_count = 1
        
        # Only act when state is stable AND different from last acted state
        if stable_count == DEBOUNCE_POLLS and stable_state != last_state:
            log(f"HDMI {'connected' if stable_state else 'disconnected'} - reconfiguring")
            set_audio(stable_state)
            toggle_hat(not stable_state)
            # Only restart fbcp on subsequent HDMI changes, not initial detection
            if last_state is not None:
                restart_fbcp()
            last_state = stable_state
        
        # Watchdog: ensure fbcp stays running
        if not fbcp_running():
            log("fbcp died, restarting")
            start_fbcp()
        
        time.sleep(POLL_DELAY)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
