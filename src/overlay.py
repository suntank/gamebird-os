#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Battery / environment / network overlay
# + volume-OSD & hot-keys
#
# Tested on RetroPie 5 / Raspberry Pi OS Bookworm (2024-12-11),
# mk_arcade_joystick_rpi driver, ALSA (“Master”) mixer.
#
# 2025-05-01 • Austin edition

import os, re, time, subprocess, logging, logging.handlers,fcntl,errno
from datetime import datetime
from collections import deque
from statistics import median
from enum import Enum
import json  # for config persistence
import urllib.request
import base64
# ───────────────────────────────────────────────────────────────
# Logging setup (moved to top so it is available everywhere)
logfile = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'overlay.log')
my_logger = logging.getLogger("overlay")
my_logger.setLevel(logging.INFO)
fh = logging.handlers.RotatingFileHandler(logfile, maxBytes=102400, backupCount=1)
my_logger.addHandler(fh)
my_logger.addHandler(logging.StreamHandler())

# ───────────────────────────────────────────────────────────────
# ---- OPTIONAL 3rd-party python modules ----
#     sudo apt install python3-evdev python3-pil
# ───────────────────────────────────────────────────────────────
from evdev import ecodes, InputDevice, list_devices            # game-pad events
from PIL import Image, ImageDraw, ImageFont                    # build OSD PNG

# ╭────────────────────────────────────────────────────────────╮
# │  SECTION 1  -  CONFIG                                     │
# ╰────────────────────────────────────────────────────────────╯
pngview_path   = "/usr/local/bin/pngview"
dpi            = 36                                            # overlay icon size
pngview_call   = [pngview_path, "-d", "0", "-b", "0x0000",
                  "-n", "-l", "15000", "-y", "0", "-x", "0"]   # base argv
# place this near the top of the file (right after the other constants)
NAME_KEYWORDS = ("arcade", "joystick", "gamepad", "gpio", "controller")

here           = os.path.dirname(os.path.realpath(__file__))
material_icons = "/home/pi/src/material-design-icons-master/device/drawable-mdpi/"
overlay_icons  = f"{here}/overlay_icons/"                      # your custom PNGs
logfile        = f"{here}/overlay.log"

# fallback speaker icon (provide your own nicer one later)
speaker_icon   = overlay_icons + "speaker.png"
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"  # any TTF is fine

# Input-event key codes (tweak if your pad uses others)
BTN_START = ecodes.BTN_START  if hasattr(ecodes, "BTN_START") else ecodes.KEY_START

# Config file for storing preferences across reboots
CONFIG_DIR = os.path.expanduser('~/home/gamebird')
os.makedirs(CONFIG_DIR, exist_ok=True)  # ensure directory exists

config_path = os.path.join(CONFIG_DIR, 'overlay_config.json')
persisted_volume_level = None

# Default HUD position before loading config
osd_position = 'bottom'    # 'top' or 'bottom'


def load_config():
    global osd_position, persisted_volume_level
    try:
        with open(config_path, 'r') as f:
            cfg = json.load(f)
            osd_position = cfg.get('osd_position', osd_position)
            persisted_volume_level = cfg.get('volume_level')
    except FileNotFoundError:
        pass

def save_config():
    cfg = {'osd_position': osd_position, 'volume_level': vol_get()}
    try:
        with open(config_path, 'w') as f:
            json.dump(cfg, f)
    except Exception as e:
        my_logger.error(f"Failed to save config: {e}")

# Load persisted config at startup
def load_and_apply_config():
    load_config()
    # apply saved volume if present
    global persisted_volume_level
    if isinstance(persisted_volume_level, int):
        try:
            _alsa_volume(f"{persisted_volume_level}%")
        except Exception:
            pass

# GitHub update check and update notice integration
import urllib.request

def check_for_git_update():
    try:
        local_head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd="/home/pi/gamebird-os"
        ).decode().strip()
        url = "https://api.github.com/repos/suntank/gamebird-os/commits/main"
        with urllib.request.urlopen(url) as response:
            remote_data = json.loads(response.read())
            remote_head = remote_data["sha"]
            my_logger.info(f"GitHub update check: local={local_head} remote={remote_head}")
            if remote_head != local_head:
                my_logger.info("Update available!")
                return True
            else:
                my_logger.info("No update available.")
                return False
    except Exception as e:
        my_logger.warning(f"Update check failed: {e}")
    return False

def show_update_notice():
    png_path = "/tmp/update_notice.png"
    font = ImageFont.truetype(FONT_PATH, 24)
    text = "New system update available.\nGo to Settings > Update."
    # Get screen resolution (assume global 'resolution' is available)
    screen_w = int(resolution[0])
    screen_h = int(resolution[1])
    text_w, text_h = font.getsize_multiline(text)
    padding = 24
    img_w = text_w + padding * 2
    img_h = text_h + padding
    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 200))
    draw = ImageDraw.Draw(img)
    # White text, centered
    draw.multiline_text((padding, padding//2), text, font=font, fill=(255, 255, 255, 255), align="center")
    img.save(png_path)
    # Center horizontally, place at bottom with a margin
    x = (screen_w - img_w) // 2
    y = screen_h - img_h - 40  # 40px bottom margin
    spawn_overlay("update", png_path, x, y)
    time.sleep(10)
    if "update" in overlay_processes:
        overlay_processes["update"].kill()
        del overlay_processes["update"]

# ───────────────────────────────────────────────────────────────
#  SECTION 2  -  INA219, battery, Wi-Fi, Bluetooth
# ───────────────────────────────────────────────────────────────
import board, busio
from adafruit_ina219 import INA219

i2c   = busio.I2C(board.SCL, board.SDA)
ina   = INA219(i2c, addr=0x43)

vmax = {"discharging": 4.0,  "charging": 4.3}
vmin = {"discharging": 3.3,  "charging": 3.9}
icons = { "discharging": [ "alert_red","alert","20","30","30","50","60",
                           "60","80","90","90","full" ],
          "charging":    [ "charging_20","charging_30","charging_30","charging_30",
                           "charging_50","charging_50","charging_60","charging_60",
                           "charging_80","charging_90","charging_90","charging_full" ]}

# Mixer to control (amixer scontrols will list options)

def _detect_volume_control() -> str:
    out = subprocess.check_output(["amixer", "scontrols"]).decode()
    # look for any control that, when you run `amixer sget`, shows a [%] in its output
    for name in re.findall(r"'([^']+)'", out):
        sget = subprocess.check_output(["amixer", "sget", name]).decode()
        if "%" in sget:
            return name
    raise RuntimeError("No volume control found")

alsa_mixer_name = _detect_volume_control()


class InterfaceState(Enum):
    DISABLED=0; ENABLED=1; CONNECTED=2

iconpath2 = overlay_icons
iconpath  = material_icons
env_icons = { "under-voltage": iconpath2+"flash.png",
              "freq-capped":   iconpath2+"thermometer.png",
              "throttled":     iconpath2+"thermometer-lines.png" }
wifi_icons = {
  "connected": iconpath+f"ic_network_wifi_white_{dpi}dp.png",
  "disabled":  iconpath+f"ic_signal_wifi_off_white_{dpi}dp.png",
  "enabled":   iconpath+f"ic_signal_wifi_0_bar_white_{dpi}dp.png"}

icon_battery_critical_shutdown = iconpath2 + "alert-outline-red.png"
wifi_carrier   = "/sys/class/net/wlan0/carrier"
wifi_linkmode  = "/sys/class/net/wlan0/link_mode"
bt_devices_dir = "/sys/class/bluetooth"
env_cmd        = "vcgencmd get_throttled"
fbfile         = "tvservice -s"

# ───────────────────────────────────────────────────────────────
#  SECTION 3  -  Log + helpers
# ───────────────────────────────────────────────────────────────
# (re-init logger here so overlay.log goes in script dir)
my_logger = logging.getLogger("overlay")
my_logger.setLevel(logging.INFO)
fh = logging.handlers.RotatingFileHandler(logfile, maxBytes=102400, backupCount=1)
my_logger.addHandler(fh); my_logger.addHandler(logging.StreamHandler())

resolution = re.search(r"(\d{3,}x\d{3,})",
                       subprocess.check_output(fbfile.split()).decode()).group().split('x')
my_logger.info(f"FB resolution detected: {resolution}")

overlay_processes = {}
battery_history   = deque(maxlen=15)
wifi_state = bt_state = None  # Bluetooth icon overlay is hidden; state is tracked for logging only.
battery_level = None
# Track dpad state for emulated key-presses
prev_abs_x = 0
prev_abs_y = 0

# Icon visibility timers and flags
startup_time = time.time()

# Show wifi and battery for 5 seconds on app start
wifi_visible_until = startup_time + 5.0
battery_visible_until = startup_time + 5.0

wifi_always_visible = False  # set while holding START for at least 1 second

# START button timing
start_held = False
start_pressed_at = None
start_hud_shown = False  # track if we've already shown HUD for this START hold

# Track last OSD position to force overlay respawn on position change
last_osd_position = osd_position

# Helper to spawn overlays at correct position (x, y)
def spawn_overlay(name, png, x, y):
    if name in overlay_processes:
        overlay_processes[name].kill()
        del overlay_processes[name]
    call = pngview_call.copy()
    call[call.index('-x') + 1] = str(x)
    call[call.index('-y') + 1] = str(y)
    call.append(png)
    overlay_processes[name] = subprocess.Popen(call)

# ───────────────────────────────────────────────────────────────
#  SECTION 4  -  Volume control and On-Screen Display
# ───────────────────────────────────────────────────────────────
def _alsa_volume(sign_percent: str):
    """Low level call to ALSA via amixer."""
    subprocess.call(["amixer", "-q", "sset", alsa_mixer_name, sign_percent])

def vol_get() -> int:
    out = subprocess.check_output(["amixer", "get", alsa_mixer_name]).decode()
    m = re.search(r"\[(\d+)%\]", out)
    return int(m.group(1)) if m else 0

def vol_change(delta: int) -> int:
    cur = vol_get()
    new = max(0, min(100, cur + delta))
    # Avoid extra amixer calls at the clamp
    if new != cur:
        _alsa_volume(f"{new}%")
    return new

# OSD helpers
def build_volume_png(vol_pct: int, path_out="/tmp/vol_osd.png") -> str:
    """Compose 'speaker  98%' into a transparent PNG."""
    icon = Image.open(speaker_icon).convert("RGBA")
    font_size = int(dpi * 0.7)          # approx 25 px when dpi=36
    font = ImageFont.truetype(FONT_PATH, font_size)

    txt = f"{vol_pct}%"
    text_w, text_h = font.getsize(txt)

    img = Image.new("RGBA",
                    (icon.width + text_w + 12, max(icon.height, text_h) + 4),
                    (0,0,0,0))
    img.paste(icon, (0, (img.height - icon.height)//2), mask=icon)

    draw = ImageDraw.Draw(img)
    draw.text((icon.width + 8, (img.height - text_h)//2),
              txt, font=font, fill=(255,255,255,255))
    img.save(path_out)
    return path_out

vol_osd_until = 0.0                                            # epoch seconds

def build_time_png(path_out="/tmp/time_osd.png") -> str:
    """Build a transparent PNG with current time in 12-hour format."""
    font_size = int(dpi * 0.7)          # same size as volume percent
    font = ImageFont.truetype(FONT_PATH, font_size)
    
    now = datetime.now()
    hour_12 = now.hour % 12
    if hour_12 == 0:
        hour_12 = 12
    am_pm = "AM" if now.hour < 12 else "PM"
    txt = f"{hour_12}:{now.minute:02d} {am_pm}"
    
    text_w, text_h = font.getsize(txt)
    img = Image.new("RGBA", (text_w + 8, text_h + 4), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text((4, 2), txt, font=font, fill=(255, 255, 255, 255))
    img.save(path_out)
    return path_out

def show_time_osd(position='bottom'):
    """Show current time overlay in the center of the HUD."""
    png = build_time_png()
    # Center horizontally
    img = Image.open(png)
    x_pos = (int(resolution[0]) - img.width) // 2
    y_pos = 0 if position == 'top' else int(resolution[1]) - dpi - 8
    spawn_overlay('time', png, x_pos, y_pos)

def hide_time_osd():
    """Hide the time overlay."""
    if 'time' in overlay_processes:
        overlay_processes['time'].kill()
        del overlay_processes['time']

def show_volume_osd(vol_pct: int, duration=2.0, position='bottom'):
    """Create PNG plus show via pngview; auto kills after duration."""
    global vol_osd_until
    png = build_volume_png(vol_pct)
    x_pos = 0  # volume OSD always at left edge
    y_pos = 0 if position == 'top' else int(resolution[1]) - dpi - 8
    spawn_overlay('vol', png, x_pos, y_pos)
    vol_osd_until = time.time() + duration

def maybe_clear_volume_osd():
    if "vol" in overlay_processes and time.time() >= vol_osd_until:
        overlay_processes["vol"].kill()
        del overlay_processes["vol"]

# ───────────────────────────────────────────────────────────────
#  SECTION 5  -  Battery / Wi-Fi / BT / env
# ───────────────────────────────────────────────────────────────
def is_charging():
    try:
        return ina.current > 0
    except Exception:
        return False

def translate_bat(voltage):
    try:
        state = "charging" if is_charging() else "discharging"
        span  = vmax[state]-vmin[state]
        idx   = int(round(max(0.0, min(1.0,
                                    (voltage - vmin[state]) / span))
                           * (len(icons[state])-1)))
        return icons[state][idx]
    except Exception as e:
        my_logger.error(f"translate_bat(): {e}")
        return "unknown"

def battery(force=False):
    global battery_level, battery_visible_until
    try:
        value_v = ina.bus_voltage
    except Exception:
        value_v = 0.0

    battery_history.append(value_v)
    level_icon = translate_bat(median(battery_history))

    # Critical shutdown logic is unchanged
    if value_v <= 3.3:
        my_logger.warning("Battery ≤3.3 V, shutdown in 20 s")
        subprocess.Popen(pngview_call+[
            str(int(int(resolution[0]) / 2 - 64)),"-y",str(int(int(resolution[1]) / 2 - 64)),
            icon_battery_critical_shutdown])
        os.system("sleep 20 && sudo poweroff &")

    # Decide if battery icon should be "always" visible
    try:
        charging = is_charging()
    except Exception:
        charging = False

    # Conditions where battery should stay on:
    #  - red level while discharging (alert_red) - always visible
    #  - START button held
    always_on = False

    if not charging and level_icon == "alert_red":
        always_on = True

    # START held for 2+ seconds keeps battery visible
    if wifi_always_visible:
        always_on = True

    # Show for 3 seconds when reaching "alert" (second-to-last before red) or "charging_full"
    if battery_level is not None and level_icon != battery_level:
        if level_icon == "alert" or level_icon == "charging_full" or level_icon == "20":
            battery_visible_until = time.time() + 3.0

    visible = always_on or (time.time() < battery_visible_until)

    y_pos = 0 if osd_position == 'top' else int(resolution[1]) - dpi - 8
    x_bat = int(resolution[0]) - dpi
    icon = f"ic_battery_{level_icon}_white_{dpi}dp.png"

    if visible:
        if force or level_icon != battery_level or 'bat' not in overlay_processes:
            spawn_overlay('bat', iconpath+icon, x_bat, y_pos)
        battery_level = level_icon
    else:
        if 'bat' in overlay_processes:
            overlay_processes['bat'].kill()
            del overlay_processes['bat']

    return level_icon, value_v

def wifi(force=False):
    global wifi_state, wifi_visible_until, wifi_always_visible

    st_new = InterfaceState.DISABLED
    try:
        with open(wifi_carrier) as f:
            carrier = int(f.read().strip())
        if carrier == 1:
            st_new = InterfaceState.CONNECTED
        else:
            with open(wifi_linkmode) as f:
                link = int(f.read().strip())
            if link == 1:
                st_new = InterfaceState.ENABLED
    except IOError:
        pass

    # 5 second display on connect or disconnect events
    prev_state = wifi_state
    if prev_state is not None and st_new != prev_state:
        # Just connected to wifi
        if st_new == InterfaceState.CONNECTED:
            wifi_visible_until = time.time() + 5.0
        # Just disconnected from wifi
        elif prev_state == InterfaceState.CONNECTED and st_new != InterfaceState.CONNECTED:
            wifi_visible_until = time.time() + 5.0

    y_pos = 0 if osd_position == 'top' else int(resolution[1]) - dpi - 8
    x_wifi = int(resolution[0]) - dpi*2
    key  = ("connected" if st_new == InterfaceState.CONNECTED else
            "enabled"   if st_new == InterfaceState.ENABLED    else
            "disabled")

    visible = wifi_always_visible or (time.time() < wifi_visible_until)

    if visible:
        if force or st_new != wifi_state or 'wifi' not in overlay_processes:
            spawn_overlay('wifi', wifi_icons[key], x_wifi, y_pos)
    else:
        if 'wifi' in overlay_processes:
            overlay_processes['wifi'].kill()
            del overlay_processes['wifi']

    wifi_state = st_new
    return st_new

def bluetooth(force=False):
    global bt_state
    st_new = InterfaceState.DISABLED
    try:
        if "up" in subprocess.check_output("hciconfig".split()).decode():
            st_new = InterfaceState.ENABLED
    except:
        pass
    try:
        if len(os.listdir(bt_devices_dir)) > 1:
            st_new = InterfaceState.CONNECTED
    except:
        pass
    # Do not display any Bluetooth overlay icon.
    bt_state = st_new
    return st_new

def environment():
    val = int(re.search(r"0x[\da-f]+",
                        subprocess.check_output(env_cmd.split()).decode()).group(), 16)
    flags = {"under-voltage": bool(val & 0x01),
             "freq-capped":   bool(val & 0x02),
             "throttled":     bool(val & 0x04)}
    y_pos = 0 if osd_position == 'top' else int(resolution[1]) - dpi - 8
    x_env_base = int(resolution[0]) - dpi * 4
    for idx,(k,v) in enumerate(flags.items()):
        if v and k not in overlay_processes:
            x_env = x_env_base - idx * dpi
            spawn_overlay(k, env_icons[k], x_env, y_pos)
        elif not v and k in overlay_processes:
            overlay_processes[k].kill()
            del overlay_processes[k]
    return val

# Check for update at startup, but do not show overlay until main loop
show_update_notice_flag = check_for_git_update()

# ───────────────────────────────────────────────────────────────
#  SECTION 6  -  Game-pad event loop
# ───────────────────────────────────────────────────────────────
def find_pad_device(timeout_sec: float = 10.0) -> InputDevice:
    """Return a joystick-like /dev/input device, waiting timeout_sec if needed."""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        for path in list_devices():
            dev = InputDevice(path)
            if any(kw in dev.name.lower() for kw in NAME_KEYWORDS):

                # non blocking for old or new evdev
                if hasattr(dev, "set_nonblocking"):
                    dev.set_nonblocking(True)
                else:                             # evdev < 1.6
                    flags = fcntl.fcntl(dev.fd, fcntl.F_GETFL)
                    fcntl.fcntl(dev.fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
                return dev
        time.sleep(0.2)                           # wait and retry
    raise RuntimeError("Timed out waiting for a game-pad input device")

pad = find_pad_device()

# repeat handling for volume buttons
repeat_direction = 0    # -1 for down, +1 for up
repeat_start_time = 0.0
repeat_last_time = 0.0
repeat_initial_delay = 0.5  # seconds before auto-repeat
repeat_interval = 0.2       # seconds between repeats (was 0.1)
repeat_step = 2             # percent per repeat
last_status_log = 0         # timestamp for periodic status logs

load_and_apply_config()

try:
    update_notice_shown = False
    while True:
        # Show update notice overlay once, after display is ready
        if show_update_notice_flag and not update_notice_shown:
            my_logger.info("Displaying update notice overlay...")
            show_update_notice()
            update_notice_shown = True

        # 1. Handle controller events (non-blocking)
        try:
            for ev in pad.read():
                if ev.type == ecodes.EV_KEY and ev.code == BTN_START:
                    if ev.value:  # pressed
                        if not start_held:
                            start_pressed_at = time.time()
                        start_held = True
                    else:         # released
                        start_held = False
                        start_pressed_at = None
                        repeat_direction = 0
                    continue

                if not start_held:
                    continue

                # D-pad: emulate key-presses from ABS_X/ABS_Y
                if ev.type == ecodes.EV_ABS:
                    # Horizontal (left or right)
                    if ev.code == ecodes.ABS_X:
                        if prev_abs_x != ev.value:
                            if ev.value == -1:  # left pressed
                                delta = -repeat_step
                                pct = vol_change(delta)
                                show_volume_osd(pct, position=osd_position)
                                save_config()
                                repeat_direction = -1
                                repeat_start_time = time.time()
                                repeat_last_time = repeat_start_time
                            elif ev.value == 1:  # right pressed
                                delta = repeat_step
                                pct = vol_change(delta)
                                show_volume_osd(pct, position=osd_position)
                                save_config()
                                repeat_direction = 1
                                repeat_start_time = time.time()
                                repeat_last_time = repeat_start_time
                            elif ev.value == 0:
                                repeat_direction = 0
                            prev_abs_x = ev.value

                    # Vertical (up or down)
                    elif ev.code == ecodes.ABS_Y:
                        if prev_abs_y != ev.value:
                            if ev.value == -1:  # up pressed
                                osd_position = 'top'
                                save_config()
                                pct = vol_get()
                                show_volume_osd(pct, position=osd_position)

                                # When icons are moved, show wifi and battery for 5 seconds
                                t = time.time()
                                battery_visible_until = t + 5.0
                                wifi_visible_until = t + 5.0

                                # Immediately update other overlays on position change
                                battery(force=True)
                                wifi(force=True)
                                environment()

                            elif ev.value == 1:  # down pressed
                                osd_position = 'bottom'
                                save_config()
                                pct = vol_get()
                                show_volume_osd(pct, position=osd_position)

                                t = time.time()
                                battery_visible_until = t + 5.0
                                wifi_visible_until = t + 5.0

                                battery(force=True)
                                wifi(force=True)
                                environment()
                            prev_abs_y = ev.value
        except BlockingIOError:
            pass                                       # nothing to read

        # After processing input events, update wifi "hold to show" flag
        now = time.time()
        if start_held and start_pressed_at is not None and now - start_pressed_at >= 1.0:
            # Show all HUD elements together when 1 second threshold is reached
            if not start_hud_shown:
                start_hud_shown = True
                wifi_always_visible = True
                # Force spawn all elements at once for consistency
                battery(force=True)
                wifi(force=True)
                show_time_osd(position=osd_position)
                show_volume_osd(vol_get(), duration=999, position=osd_position)  # keep visible while held
            else:
                wifi_always_visible = True
        elif not start_held:
            # Reset everything when START is released
            if start_hud_shown:
                start_hud_shown = False
                wifi_always_visible = False
                hide_time_osd()
                # Clear volume OSD immediately
                if 'vol' in overlay_processes:
                    overlay_processes['vol'].kill()
                    del overlay_processes['vol']
            wifi_always_visible = False

        # Show volume OSD while START is held AND actively changing volume (dpad left/right)
        if start_held and start_hud_shown and repeat_direction != 0:
            pct = vol_get()
            show_volume_osd(pct, duration=999, position=osd_position)  # keep visible while held

        # auto-repeat while holding START + Dpad left/right
        if start_held and repeat_direction != 0:
            if now - repeat_start_time >= repeat_initial_delay and now - repeat_last_time >= repeat_interval:
                pct = vol_change(repeat_direction * repeat_step)
                show_volume_osd(pct, position=osd_position)
                save_config()
                repeat_last_time = now

        # 2. Periodic overlay updates (1 Hz)
        if now - last_status_log >= 1.0:
            force_update = False
            if osd_position != last_osd_position:
                force_update = True
                last_osd_position = osd_position
            bat_icon, v = battery(force=force_update)
            wifi(force=force_update)
            env_val = environment()  # env overlays always update as before
            last_status_log = now

        # 3. Clear volume OSD if time elapsed
        maybe_clear_volume_osd()

        time.sleep(0.01)  # tiny sleep keeps CPU usage civil
except KeyboardInterrupt:
    for p in overlay_processes.values():
        p.kill()
    raise
