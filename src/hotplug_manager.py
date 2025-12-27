#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Game Bird – Hot‑plug manager w/ PID‑based fbcp restart

• EDID‑based HDMI detection (works with hdmi_force_hotplug=1)
• Audio swap via amixer + asound.conf + ~/.asoundrc + runcommand override
• mk_arcade_joystick_rpi enable/disable
• Proper PID‑based restart of fbcp‑ili9341 so SPI never freezes
"""

import os
import fcntl
import sys
import signal
import time
import pathlib
import pwd
import shutil
import subprocess as sp
import tempfile
import traceback
from typing import List, Optional
from glob import glob

POLL_DELAY = 2  # seconds
FBCP_CMD   = "/usr/local/bin/fbcp-ili9341"
FBCP_ARGS  = ["-x", "200", "-y", "120", "-w", "240", "-h", "240", "-noscaling"]

LOG_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "hotplug_manager.log")
LOCK_FILE = "/tmp/hotplug_manager.lock"
_lock_fd = None

_start_mono = time.monotonic()


def _acquire_lock() -> bool:
    global _lock_fd
    _lock_fd = open(LOCK_FILE, "w")
    try:
        fcntl.flock(_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _lock_fd.write(str(os.getpid()))
        _lock_fd.flush()
        return True
    except (OSError, IOError):
        try:
            _lock_fd.close()
        except Exception:
            pass
        return False


if not _acquire_lock():
    print("hotplug_manager.py already running, exiting.", file=sys.stderr)
    sys.exit(0)


def log(msg: str):
    line = (
        f"[HotPlug] {time.strftime('%Y-%m-%d %H:%M:%S')} "
        f"t+{(time.monotonic() - _start_mono):.1f}s pid={os.getpid()} | {msg}"
    )
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _handle_signal(signum, _frame):
    try:
        log(f"received signal {signum}; exiting")
    finally:
        raise SystemExit(0)


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGHUP, _handle_signal)


def _run(argv, timeout: float = 2.0):
    return sp.run(argv, stdout=sp.DEVNULL, stderr=sp.DEVNULL, timeout=timeout)


def _out(argv, timeout: float = 2.0) -> str:
    return sp.check_output(argv, text=True, stderr=sp.DEVNULL, timeout=timeout)


def fbcp_running() -> bool:
    base = os.path.basename(FBCP_CMD)
    try:
        out = _out(["pidof", base], timeout=1.0).strip()
        return bool(out)
    except Exception:
        return False


def _fbcp_pids() -> List[int]:
    base = os.path.basename(FBCP_CMD)
    try:
        out = _out(["pidof", base], timeout=1.0).strip()
        if not out:
            return []
        return [int(p) for p in out.split()]
    except Exception:
        return []


def _proc_cmdline(pid: int) -> Optional[List[str]]:
    try:
        raw = pathlib.Path(f"/proc/{pid}/cmdline").read_bytes()
    except FileNotFoundError:
        return None
    except Exception:
        return None
    parts = [p.decode(errors="replace") for p in raw.split(b"\0") if p]
    return parts


def fbcp_cmdline_matches() -> bool:
    expected = [FBCP_CMD] + FBCP_ARGS
    for pid in _fbcp_pids():
        cmd = _proc_cmdline(pid)
        if not cmd:
            continue
        if cmd == expected:
            return True
        if cmd and os.path.realpath(cmd[0]) == os.path.realpath(FBCP_CMD) and cmd[1:] == FBCP_ARGS:
            return True
    return False


def stop_fbcp_early():
    try:
        _run(["systemctl", "stop", "fbcp-early.service"], timeout=2.0)
    except sp.TimeoutExpired:
        log("systemctl stop fbcp-early.service timed out")
    except FileNotFoundError:
        pass
    except Exception as e:
        log(f"systemctl stop fbcp-early.service error: {e}")


def _external_fbcp_manager_present() -> bool:
    if os.environ.get("GBZ_EXTERNAL_FBCP", "").strip() == "1":
        return True
    unit = "fbcp-ili9341.service"
    for base in (
        "/etc/systemd/system",
        "/lib/systemd/system",
        "/usr/lib/systemd/system",
    ):
        try:
            if os.path.exists(os.path.join(base, unit)):
                try:
                    r = _run(["systemctl", "is-enabled", unit], timeout=1.0)
                    if getattr(r, "returncode", 1) == 0:
                        return True
                except Exception:
                    pass
                try:
                    r = _run(["systemctl", "is-active", unit], timeout=1.0)
                    if getattr(r, "returncode", 1) == 0:
                        return True
                except Exception:
                    pass
        except Exception:
            pass
    return False


def ensure_fbcp_running():
    """Start fbcp if it's not running. Avoid unnecessary restarts (screen blanking)."""
    if fbcp_running():
        return
    log("fbcp-ili9341 not running; starting")
    try:
        sp.Popen([FBCP_CMD] + FBCP_ARGS, stdout=sp.DEVNULL, stderr=sp.DEVNULL)
        time.sleep(0.25)
    except Exception as e:
        log(f"failed to start fbcp-ili9341: {e}")


def wait_for_snd(timeout_sec: float = 20.0) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if pathlib.Path("/dev/snd").exists():
            return True
        time.sleep(0.2)
    return False

# -----------------------------------------------------------------------------
# HDMI detection (EDID)
# -----------------------------------------------------------------------------

def _kms_edid_present() -> bool:
    for st in glob("/sys/class/drm/card*-HDMI-A-*/status"):
        try:
            if pathlib.Path(st).read_text().strip() == "connected":
                return True
        except FileNotFoundError:
            pass
        except Exception:
            pass
    return False


def _legacy_edid_present() -> bool:
    """Fallback for FKMS/DispmanX systems (tvservice). Safe to remove on KMS‑only
    images once you move past Buster.
    """
    with tempfile.NamedTemporaryFile() as tmp:
        try:
            r = _run(["/usr/bin/tvservice", "-d", tmp.name], timeout=3)
            if r.returncode == 0 and pathlib.Path(tmp.name).stat().st_size >= 128:
                return True
        except sp.TimeoutExpired:
            return False
        except FileNotFoundError:
            pass
    return False


def hdmi_connected() -> bool:
    status_files = glob("/sys/class/drm/card*-HDMI-A-*/status")
    if status_files:
        return _kms_edid_present()
    return _legacy_edid_present()

# -----------------------------------------------------------------------------
# Audio swap + runcommand override
# -----------------------------------------------------------------------------

HDMI_CARD, HDMI_VOL_ID, HDMI_SW_ID = "0", "1", "2"
HP_CARD,   HP_VOL_ID,   HP_SW_ID   = "1", "1", "2"
DESIRED_VOL = "250"  # 0–400

ASOUND_DEFAULT = "/etc/asound.conf"
ASOUND_USER    = pathlib.Path(pwd.getpwnam("pi").pw_dir) / ".asoundrc"
ASOUND_HDMI    = "/etc/asound.hdmi.conf"
ASOUND_HP      = "/etc/asound.hp.conf"
RUNCOMMAND_CFG = "/opt/retropie/configs/all/runcommand.cfg"


def _ensure_snippets():
    # Predefined fallback content in case source files go missing
    default_hdmi = "defaults.pcm.card 0\ndefaults.ctl.card 0\n"
    default_hp   = "defaults.pcm.card 1\ndefaults.ctl.card 1\n"

    if not pathlib.Path(ASOUND_HDMI).exists():
        print("[HotPlug] Warning: /etc/asound.hdmi.conf missing, using fallback")
        try:
            pathlib.Path("/home/pi/.asound.hdmi.conf").write_text(default_hdmi)
        except Exception:
            pass
    if not pathlib.Path(ASOUND_HP).exists():
        print("[HotPlug] Warning: /etc/asound.hp.conf missing, using fallback")
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
        except Exception as e:
            log(f"asound copy error dst={dst}: {e}")
    try:
        _run(["alsactl", "restore"], timeout=2.0)
    except sp.TimeoutExpired:
        log("alsactl restore timed out")
    except FileNotFoundError:
        log("alsactl not found")
    except Exception as e:
        log(f"alsactl restore error: {e}")

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
        log(f"PermissionError writing {RUNCOMMAND_CFG}")
    except Exception as e:
        log(f"runcommand.cfg write error: {e}")


def _amixer(card: str, numid: str, value: str):
    """Robust amixer helper with up‑to‑three retries."""
    for _ in range(3):
        try:
            _run(["amixer", "-q", "-c", card, "cset", f"numid={numid}", value], timeout=1.0)
            out = _out(["amixer", "-c", card, "cget", f"numid={numid}"], timeout=1.0)
        except sp.TimeoutExpired:
            log(f"amixer timeout card={card} numid={numid}")
            time.sleep(0.2)
            continue
        except FileNotFoundError:
            log("amixer not found")
            return
        except Exception as e:
            log(f"amixer error card={card} numid={numid}: {e}")
            time.sleep(0.2)
            continue
        if value.isdigit():
            if f"values={value}" in out:
                return
        else:
            if f"[{value}]" in out:
                return
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

# -----------------------------------------------------------------------------
# Joystick HAT toggle
# -----------------------------------------------------------------------------

def hat_loaded() -> bool:
    return pathlib.Path("/sys/module/mk_arcade_joystick_rpi").exists()


def toggle_hat(enable: bool):
    if enable and not hat_loaded():
        sp.call(["modprobe", "mk_arcade_joystick_rpi"])
    elif not enable and hat_loaded():
        sp.call(["modprobe", "-r", "mk_arcade_joystick_rpi"])

# -----------------------------------------------------------------------------
# fbcp restart: PID‑based SIGTERM→wait→SIGKILL→spawn
# -----------------------------------------------------------------------------

def restart_fbcp():
    base = os.path.basename(FBCP_CMD)
    # Kill early-started fbcp if it exists
    stop_fbcp_early()

    # Find running PIDs
    try:
        out = _out(["pidof", base], timeout=1.0).strip()
        pids = [int(p) for p in out.split()]
    except sp.CalledProcessError:
        pids = []
    except sp.TimeoutExpired:
        pids = []
    except FileNotFoundError:
        pids = []
    except Exception as e:
        log(f"pidof error: {e}")
        pids = []

    # SIGTERM running instances
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    # Wait up to 1 s for graceful exit
    for _ in range(10):
        alive = [pid for pid in pids if os.path.exists(f"/proc/{pid}")]
        if not alive:
            break
        time.sleep(0.1)
    else:
        # Force‑kill survivors
        for pid in alive:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        time.sleep(0.1)

    # Spawn fresh instance
    sp.Popen([FBCP_CMD] + FBCP_ARGS, stdout=sp.DEVNULL, stderr=sp.DEVNULL)
    time.sleep(0.25)  # give DMA a moment to settle

# -----------------------------------------------------------------------------
# Main loop
# -----------------------------------------------------------------------------


def main():

    log("hotplug_manager starting")

    manage_fbcp = not _external_fbcp_manager_present()
    external_start_failures = 0
    external_start_failure_threshold = 6
    if manage_fbcp:
        stop_fbcp_early()
        if not fbcp_running():
            log("fbcp-ili9341 not running at startup; starting")
            ensure_fbcp_running()
        elif not fbcp_cmdline_matches():
            log("fbcp-ili9341 args mismatch at startup; restarting")
            restart_fbcp()
        else:
            log("fbcp-ili9341 already running with expected args")
    else:
        log("external fbcp manager detected; hotplug_manager will not manage fbcp")
        if not fbcp_running():
            log("fbcp-ili9341 not running; attempting to start fbcp-ili9341.service")
            try:
                _run(["systemctl", "start", "fbcp-ili9341.service"], timeout=2.0)
            except Exception as e:
                log(f"failed to start fbcp-ili9341.service: {e}")

    if not wait_for_snd(20.0):
        log("/dev/snd not present after 20s; continuing")

    last_state = None
    stable = None
    stable_count = 0
    debounce_polls = 3

    last_heartbeat = 0.0
    heartbeat_sec = 30.0

    last_fbcp_service_attempt = 0.0
    fbcp_service_attempt_sec = 10.0

    while True:
        try:
            now = time.monotonic()
            if (now - last_heartbeat) >= heartbeat_sec:
                last_heartbeat = now
                log(f"heartbeat fbcp_running={fbcp_running()} hdmi={hdmi_connected()} last_state={last_state}")

            # If fbcp is owned by systemd but isn't up, ask systemd to start it.
            if (not manage_fbcp) and (not fbcp_running()) and ((now - last_fbcp_service_attempt) >= fbcp_service_attempt_sec):
                last_fbcp_service_attempt = now
                log("fbcp-ili9341 not running; asking systemd to start fbcp-ili9341.service")
                try:
                    _run(["systemctl", "start", "fbcp-ili9341.service"], timeout=2.0)
                except Exception as e:
                    log(f"failed to start fbcp-ili9341.service: {e}")

                if fbcp_running():
                    external_start_failures = 0
                else:
                    external_start_failures += 1
                    if external_start_failures >= external_start_failure_threshold:
                        log("fbcp-ili9341.service did not bring up fbcp; falling back to direct fbcp start")
                        manage_fbcp = True
                        try:
                            ensure_fbcp_running()
                        except Exception as e:
                            log(f"fallback ensure_fbcp_running failed: {e}")

            # If something else kills fbcp, bring it back.
            if manage_fbcp and not fbcp_running():
                log("fbcp-ili9341 not running; restarting")
                restart_fbcp()

            raw = hdmi_connected()
            if raw == stable:
                stable_count += 1
            else:
                stable = raw
                stable_count = 1

            if stable_count == debounce_polls and stable != last_state:
                log(f"HDMI {'connected' if stable else 'disconnected'} – reconfiguring")
                t0 = time.time()
                set_audio(stable)
                log(f"set_audio took {(time.time() - t0):.2f}s")
                toggle_hat(not stable)

                # On first stable reading we only configure audio/hat; fbcp was already restarted at startup.
                if manage_fbcp and last_state is not None:
                    t1 = time.time()
                    restart_fbcp()
                    log(f"restart_fbcp took {(time.time() - t1):.2f}s")

                last_state = stable
        except Exception:
            log("Unhandled exception in main loop:\n" + traceback.format_exc())
            time.sleep(1.0)

        time.sleep(POLL_DELAY)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        log("Unhandled exception in __main__:\n" + traceback.format_exc())
        raise
