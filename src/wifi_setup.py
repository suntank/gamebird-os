#!/usr/bin/env python3
"""
Wifi.py – Game Bird Wi-Fi setup via SNES-style GameHat controls on a 480×480 SPI display.
Features:
- Status screen with SSID and signal bars
- Filters out blank/hidden networks
- Dynamic spacing to use full screen for network list
- Virtual QWERTY keyboard with shift/select toggle
- Proper ASCII-only SSID cleaning (no mystery boxes)
- Grabs /dev/input/js0 to prevent EmulationStation bleed-through
- Runs under pi user with sudo wpa_cli
Logs to ~/gamebird/wifi_debug.log
"""

import os
import sys
import re
import time
import subprocess
import logging
import string
import fcntl
import pygame
import tempfile
from pygame.locals import *

# configure logging
LOG_PATH = os.path.join(tempfile.gettempdir(), 'wifi_debug.log')
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True) # Ensure directory exists
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s'
)
logging.debug('=== Starting Wifi.py ===')

# Force SDL driver & framebuffer
os.environ['SDL_VIDEODRIVER'] = 'rpi'
os.environ.setdefault('SDL_FBDEV', '/dev/fb1')

# CONFIG
SCREEN_WIDTH, SCREEN_HEIGHT = 480, 480
FONT_SIZE = 38
SSID_LIST_LIMIT = 6

# Buttons (adjust if your GameHat has a different mapping)
BTN_A      = 0  # Typically East face button
BTN_B      = 1  # Typically South face button
BTN_X      = 2  # Typically North face button (used for X on some layouts, not Y for West here)
BTN_Y      = 3  # Typically West face button
BTN_SELECT = 6
BTN_START  = 7
BTN_L      = 4
BTN_R      = 5

# QWERTY rows
QWERTY_ROWS = [list('qwertyuiop'), list('asdfghjkl'), list('zxcvbnm')]
SYMBOLS_ROW = list('0123456789-_.:@/')

# --- WIFI-COUNTRY DATA ----------------------------------------------------
# Two-letter ISO 3166-1 codes Raspberry Pi understands.
COUNTRIES = [
    ("US", "United States"), ("GB", "United Kingdom"), ("CA", "Canada"),
    ("AU", "Australia"), ("NZ", "New Zealand"), ("DE", "Germany"),
    ("FR", "France"), ("ES", "Spain"), ("IT", "Italy"), ("JP", "Japan"),
    ("KR", "South Korea"), ("CN", "China"), ("IN", "India"),
    ("BR", "Brazil"), ("MX", "Mexico"), ("RU", "Russia"),
]

# ASCII-only SSID cleaning
def clean_ssid(s: str) -> str:
    return ''.join(ch for ch in s if 32 <= ord(ch) <= 126).strip()

# navigation helper
def get_nav(evt):
    dx = dy = 0
    if evt.type == JOYHATMOTION:
        dx, dy = evt.value
    elif evt.type == JOYAXISMOTION:
        if evt.axis == 0: # X-axis
            dx = -1 if evt.value < -0.5 else 1 if evt.value > 0.5 else 0
        elif evt.axis == 1: # Y-axis
            dy = 1 if evt.value < -0.5 else -1 if evt.value > 0.5 else 0 
    return dx, dy

# Utility: Check if SELECT+START are held
def is_select_start_held():
    if not pygame.joystick.get_init() or pygame.joystick.get_count() == 0:
        return False
    joy = pygame.joystick.Joystick(0)
    try:
        return joy.get_button(BTN_SELECT) and joy.get_button(BTN_START)
    except pygame.error: # Can happen if joystick is disconnected suddenly
        logging.warning("Pygame error checking Select+Start buttons.")
        return False


# --- UI ENHANCEMENTS ---
def draw_header(screen, font):
    header_height = 56
    for y_pos in range(header_height):
        c = 40 + int(120 * (y_pos / header_height))
        pygame.draw.line(screen, (c, c, 255), (0, y_pos), (SCREEN_WIDTH, y_pos))
    title_surf = font.render("WiFi Setup", True, (255,255,255))
    screen.blit(title_surf, (20, 8))

def draw_signal_bars(screen, x, y, level):
    bars = sum(level > t for t in (-80,-70,-60,-50)) 
    for i in range(4):
        bar_height = (i+1)*8 
        color = (0,200,0) if i < bars else (100,100,100) 
        if i < bars: 
            if bars == 1: color = (200,0,0) 
            elif bars == 2: color = (200,200,0) 
        pygame.draw.rect(screen, color, (x+i*12, y+(32-bar_height), 10, bar_height), border_radius=3)

def draw_button_hint(screen, font, text, x, y, color, highlight=None,text_offset=0):
    main_radius = 28
    pygame.draw.circle(screen, color, (x+main_radius, y+main_radius), main_radius)
    offsets = {'north': (0, -18), 'south': (0, 18), 'west': (-18, 0), 'east': (18, 0)}
    for direction, (dx_offset, dy_offset) in offsets.items(): 
        circ_x = x + main_radius + dx_offset
        circ_y = y + main_radius + dy_offset
        circ_color = (255,200,40) if direction == highlight else (180,180,180)
        pygame.draw.circle(screen, circ_color, (circ_x, circ_y), 9)
        pygame.draw.circle(screen, (100,100,100), (circ_x, circ_y), 9, 2)
    txt_surf = font.render(text, True, (220,220,220))
    txt_rect = txt_surf.get_rect(center=(x+main_radius+70+text_offset, y+main_radius))
    screen.blit(txt_surf, txt_rect)

def draw_pill_button_hint(screen, font, action, x, y, color, label,pill_w,text_offset):
    pill_h = 32
    pill_rect = pygame.Rect(x, y, pill_w, pill_h)
    pygame.draw.rect(screen, color, pill_rect, border_radius=18)
    label_surf = font.render(label, True, (0,0,0)) 
    screen.blit(label_surf, (pill_rect.x+10, pill_rect.y+(pill_h-label_surf.get_height())//2))
    action_surf = font.render(action, True, (220,220,220)) 
    screen.blit(action_surf, (pill_rect.x+pill_w+text_offset+5, pill_rect.y+(pill_h-action_surf.get_height())//2))

def draw_network_list(screen, font, networks, selected_idx, scroll_offset=0):
    header_footer_space = 140 
    list_height = SCREEN_HEIGHT - header_footer_space
    if not networks: return 
    num_items_total = len(networks)
    num_items_to_display = min(num_items_total, SSID_LIST_LIMIT)
    if num_items_to_display == 0: return
    item_height = list_height // num_items_to_display
    y_start = 80 
    current_ssid_val = WifiManager.current_ssid()
    
    # Only show the slice of the list for scrolling
    visible_networks = networks[scroll_offset:scroll_offset+num_items_to_display]
    for i, net in enumerate(visible_networks): 
        y_pos = y_start + i * item_height
        rect_height = item_height - 8 
        rect = pygame.Rect(32, y_pos, SCREEN_WIDTH-64, rect_height)
        is_actually_selected = (i == selected_idx) 
        
        color = (60,60,100) if not is_actually_selected else (80,180,255)
        pygame.draw.rect(screen, color, rect, border_radius=16)
        if is_actually_selected:
            pygame.draw.rect(screen, (255,255,255), rect, border_radius=16, width=3)
        
        ssid_color = (255,255,0) if is_actually_selected else (220,220,220)
        ssid_surf = font.render(net['ssid'], True, ssid_color)
        is_connected_to_this = current_ssid_val and net['ssid'] == current_ssid_val
        ssid_y_offset = (rect_height - ssid_surf.get_height()) // 2
        if is_connected_to_this: ssid_y_offset -= 10 
        screen.blit(ssid_surf, (rect.x+16, rect.y + ssid_y_offset))

        if is_connected_to_this:
            conn_surf = font.render('Connected', True, (0,255,0))
            screen.blit(conn_surf, (rect.x+16, rect.y + (rect_height // 2) + 2))
        
        level = net.get('level', -100) 
        draw_signal_bars(screen, rect.right-80, rect.centery - 16, level)

    # Draw scroll indicators if needed
    if num_items_total > SSID_LIST_LIMIT:
        bar_x = SCREEN_WIDTH - 28
        bar_y = y_start
        bar_h = item_height * SSID_LIST_LIMIT
        pygame.draw.rect(screen, (100,100,100), (bar_x, bar_y, 8, bar_h), border_radius=4)
        # Calculate scroll thumb height/position
        thumb_h = max(16, bar_h * SSID_LIST_LIMIT // num_items_total)
        max_offset = num_items_total - SSID_LIST_LIMIT
        if max_offset > 0:
            thumb_y = bar_y + int((bar_h-thumb_h) * (scroll_offset / max_offset))
        else:
            thumb_y = bar_y
        pygame.draw.rect(screen, (200,200,40), (bar_x, thumb_y, 8, thumb_h), border_radius=4)
        # Optionally, draw up/down arrows
        pygame.draw.polygon(screen, (220,220,220), [(bar_x+4, bar_y-14), (bar_x, bar_y-4), (bar_x+8, bar_y-4)]) # Up
        pygame.draw.polygon(screen, (220,220,220), [(bar_x+4, bar_y+bar_h+14), (bar_x, bar_y+bar_h+4), (bar_x+8, bar_y+bar_h+4)]) # Down
# --- END UI ---

# --- VIRTUAL KEYBOARD UI ---
def draw_virtual_keyboard(screen, font, vk):
    screen.fill((20,24,40))
    draw_header(screen, font)
    input_panel = pygame.Rect(32, 70, SCREEN_WIDTH-64, 60)
    pygame.draw.rect(screen, (40,60,100), input_panel, border_radius=18)
    pygame.draw.rect(screen, (80,180,255), input_panel, border_radius=18, width=4)
    display_text = vk.text
    if (time.time() * 2) % 2 < 1: display_text += '_'
    else: display_text += ' '
    txt_surf = font.render(display_text, True, (255,255,0))

    # Truncate displayed text if too long for the input panel
    text_field_width = input_panel.width - 32 # Account for padding
    if txt_surf.get_width() > text_field_width:
        ellipsis_width = font.size("...")[0]
        available_width = text_field_width - ellipsis_width
        
        # Estimate how many characters fit (crude for proportional fonts)
        avg_char_width = font.size("A")[0] 
        if avg_char_width == 0: avg_char_width = font.size("m")[0] # Fallback
        if avg_char_width == 0: avg_char_width = 10 # Absolute fallback

        chars_that_fit = max(0, available_width // avg_char_width)
        
        if chars_that_fit > 0 :
             truncated_text = display_text[-chars_that_fit:] # Get last N chars
             txt_surf = font.render("..." + truncated_text, True, (255,255,0))
        else: # If not even "..." fits well, just show ellipsis
             txt_surf = font.render("...", True, (255,255,0))

    screen.blit(txt_surf, (input_panel.x+16, input_panel.y + (input_panel.height - txt_surf.get_height()) // 2))

    rows_to_draw = vk.get_current_layout_rows() 
    base_y_offset = 150
    available_height_for_keys = SCREEN_HEIGHT - base_y_offset - 120
    if not rows_to_draw: return 
    gap_y = available_height_for_keys // len(rows_to_draw)
    key_height = gap_y - 10 
    for r_idx, row_content in enumerate(rows_to_draw):
        row_keys_to_render = list(row_content) 
        if r_idx == len(rows_to_draw)-1: 
            row_keys_to_render.append('123' if vk.mode=='letters' else 'abc')
        if not row_keys_to_render: continue
        
        # Calculate key_w ensuring it's not too small or causes division by zero if len is 0
        num_keys_in_row = len(row_keys_to_render)
        if num_keys_in_row == 0: continue # Should not happen with current layouts

        key_w = min(54, (SCREEN_WIDTH-80)//num_keys_in_row-6) 
        total_w = num_keys_in_row*(key_w+6)-6
        x0 = (SCREEN_WIDTH-total_w)//2

        for c_idx, key_char_raw in enumerate(row_keys_to_render):
            x_pos = x0 + c_idx*(key_w+6)
            y_pos = base_y_offset + r_idx*gap_y
            rect = pygame.Rect(x_pos, y_pos, key_w, key_height)
            is_sel = (r_idx == vk.row and c_idx == vk.col)
            key_label = key_char_raw 
            if key_char_raw.isalpha() and vk.shift and vk.mode == 'letters': key_label = key_char_raw.upper()
            elif key_char_raw.isalpha() and not vk.shift and vk.mode == 'letters': key_label = key_char_raw.lower()
            if is_sel:
                pygame.draw.rect(screen, (80,180,255), rect, border_radius=10)
                pygame.draw.rect(screen, (255,255,255), rect, border_radius=10, width=4)
                char_color = (255,255,0) 
            else:
                pygame.draw.rect(screen, (60,60,100), rect, border_radius=10)
                char_color = (255,255,255) 
            ch_surf = font.render(key_label, True, char_color)
            surf_rect = ch_surf.get_rect(center=rect.center)
            screen.blit(ch_surf, surf_rect)

    draw_button_hint(screen, font, "Delete", 10, SCREEN_HEIGHT-60, (92,92,92), highlight="south") 
    draw_button_hint(screen, font, "Select", 160, SCREEN_HEIGHT-60, (92,92,92), highlight="east")  
    draw_button_hint(screen, font, "Cancel", 310, SCREEN_HEIGHT-60, (92,92,92), highlight="west", text_offset=5) 
    draw_pill_button_hint(screen, font, "Shift", 10, SCREEN_HEIGHT-120, (92,92,92), "Select", 100, 10)
    draw_pill_button_hint(screen, font, "OK", SCREEN_WIDTH - 160, SCREEN_HEIGHT-120, (92,92,92), "Start", 85, 0)
# --- END VIRTUAL KEYBOARD UI ---

class WifiManager:
    @staticmethod
    def _run_cmd(cmd_parts, check=False, timeout=5):
        try:
            logging.debug(f"Running command: {' '.join(cmd_parts)}")
            result = subprocess.run(cmd_parts, capture_output=True, text=True, check=check, timeout=timeout)
            logging.debug(f"Command stdout: {result.stdout.strip()}")
            if result.stderr: logging.debug(f"Command stderr: {result.stderr.strip()}")
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logging.error(f"Command failed: {e.cmd}, code: {e.returncode}, stdout: {e.stdout}, stderr: {e.stderr}")
            raise
        except subprocess.TimeoutExpired as e:
            logging.error(f"Command timed out: {e.cmd}")
            raise
        except Exception as e:
            logging.error(f"Error running command {' '.join(cmd_parts)}: {e}")
            raise

    @staticmethod
    def is_connected():
        try:
            out = WifiManager._run_cmd(['ip','addr','show','wlan0'], timeout=1) 
            return 'inet ' in out and 'DOWN' not in out 
        except: return False

    @staticmethod
    def current_ssid():
        try:
            raw = WifiManager._run_cmd(['iwgetid','-r'], timeout=1)
            return clean_ssid(raw) if raw else None
        except: return None

    @staticmethod
    def signal_level():
        try:
            out = WifiManager._run_cmd(['iwconfig','wlan0'], timeout=1)
            m = re.search(r'Signal level=(-?\d+)', out)
            return int(m.group(1)) if m else None
        except: return None

    @staticmethod
    def disconnect():
        logging.info("Initiating disconnect sequence.")
        try:
            WifiManager._run_cmd(['sudo','wpa_cli','-i','wlan0','disconnect'], check=False, timeout=3)
        except Exception as e:
            logging.warning(f"wpa_cli disconnect command failed or timed out: {e}")

        disconnect_timeout_s = 3 
        poll_interval_s = 0.25
        max_polls = int(disconnect_timeout_s / poll_interval_s)
        
        for i in range(max_polls):
            if not WifiManager.is_connected(): 
                logging.info(f"Disconnect confirmed by IP check after approx {i*poll_interval_s:.2f}s.")
                status_output = WifiManager.get_wpa_status() 
                if status_output and ("wpa_state=DISCONNECTED" in status_output or "wpa_state=INACTIVE" in status_output):
                    logging.info("wpa_supplicant state also confirms disconnection.")
                elif not status_output:
                     logging.warning("Could not get wpa_status, but IP is gone. Assuming disconnected.")
                else:
                    logging.info(f"IP is gone, but wpa_state is: {status_output}. Proceeding as disconnected.")
                return True 
            time.sleep(poll_interval_s) 
            logging.debug(f"Disconnect poll attempt {i+1}/{max_polls}...")

        logging.warning(f"Disconnect not fully confirmed (IP still present or check failed) after {disconnect_timeout_s}s.")
        return False 

    @staticmethod
    def scan_networks():
        try:
            WifiManager._run_cmd(['sudo','wpa_cli','-i','wlan0','scan'], check=False, timeout=5)
        except Exception as e:
            logging.error(f"wpa_cli scan command failed or timed out: {e}")
        time.sleep(3) 
        try:
            out = WifiManager._run_cmd(['sudo','wpa_cli','-i','wlan0','scan_results'], timeout=3)
        except Exception as e:
            logging.error(f"wpa_cli scan_results command failed: {e}")
            return [] 

        nets = []
        for line in out.splitlines()[1:]: 
            parts = line.split('\t')
            if len(parts) >= 5:
                ssid = clean_ssid(parts[4])
                flags = parts[3]
                level = -100 
                try: level = int(parts[2]) 
                except ValueError: logging.warning(f"Could not parse signal level for SSID {ssid}: {parts[2]}")
                if ssid: 
                    nets.append({'ssid': ssid, 'secure': 'WPA' in flags or 'WEP' in flags or 'PSK' in flags, 'level': level})
        nets.sort(key=lambda x: x['level'], reverse=True)
        logging.debug(f"Found networks: {[n['ssid'] for n in nets]}")
        return nets

    @staticmethod
    def connect(ssid, psk=None): 
        logging.info(f"Attempting to connect to SSID: {ssid}")
        net_id = WifiManager._run_cmd(['sudo','wpa_cli','-i','wlan0','add_network'], check=True)
        WifiManager._run_cmd(['sudo','wpa_cli','-i','wlan0','set_network', net_id, 'ssid', f'"{ssid}"'], check=True)
        if psk:
            WifiManager._run_cmd(['sudo','wpa_cli','-i','wlan0','set_network', net_id, 'psk', f'"{psk}"'], check=True)
        else: 
            WifiManager._run_cmd(['sudo','wpa_cli','-i','wlan0','set_network', net_id, 'key_mgmt', 'NONE'], check=True)
        WifiManager._run_cmd(['sudo','wpa_cli','-i','wlan0', 'enable_network', net_id], check=True)
        WifiManager._run_cmd(['sudo','wpa_cli','-i','wlan0', 'reassociate'], check=True, timeout=10) 
    
    @staticmethod
    def save_configuration():
        logging.info("Saving network configuration.")
        try:
            WifiManager._run_cmd(['sudo','wpa_cli','-i','wlan0', 'save_config'], check=True)
            logging.info("Network configuration saved successfully.")
        except Exception as e:
            logging.error(f"Failed to save network configuration: {e}")

    @staticmethod
    def get_wpa_status():
        try:
            return WifiManager._run_cmd(['sudo', 'wpa_cli', '-i', 'wlan0', 'status'], timeout=2)
        except Exception as e:
            logging.warning(f"Could not get wpa_cli status: {e}")
            return None

class CountryManager:
    @staticmethod
    def current():
        """
        Returns two-letter country code or None.
        We try raspi-config first (fast), fall back to parsing wpa_supplicant.
        """
        try:
            out = WifiManager._run_cmd(
                ["raspi-config", "nonint", "get_wifi_country"], timeout=2
            )
            out = out.strip()
            if out and out != "NOTSET":
                return out.upper()
        except Exception:
            pass

        # Fallback: look for 'country=' in wpa_supplicant.conf
        try:
            with open("/etc/wpa_supplicant/wpa_supplicant.conf") as f:
                for line in f:
                    if line.startswith("country="):
                        return line.split("=")[1].strip().upper()
        except Exception:
            pass
        return None

    @staticmethod
    def set(code: str):
        """
        Persistently sets the country (raspi-config handles both file edit
        and regulatory-domain reload).  Requires sudo.
        """
        WifiManager._run_cmd(
            ["sudo", "raspi-config", "nonint", "do_wifi_country", code.upper()],
            check=True,
            timeout=10,
        )


class VirtualKeyboard:
    def __init__(self, screen, font):
        self.screen = screen
        self.font = font
        self.shift = False
        self.mode = 'letters' 
        self.row = 0
        self.col = 0
        self.done = False
        self.text = ''
        self._text_cancelled = False 

    def get_current_layout_rows(self):
        if self.mode == 'letters':
            return QWERTY_ROWS 
        else: 
            half = len(SYMBOLS_ROW) // 2
            return [SYMBOLS_ROW[:half], SYMBOLS_ROW[half:]]

    def draw(self):
        draw_virtual_keyboard(self.screen, self.font, self)
        pygame.display.flip()

    def handle(self, evt):
        if is_select_start_held(): pygame.quit(); sys.exit(0)
        dx_nav, dy_nav = get_nav(evt) 
        current_layout = self.get_current_layout_rows()
        num_rows = len(current_layout)
        if num_rows == 0: return 
        row_lengths = [len(r) for r in current_layout]
        if num_rows > 0: row_lengths[-1] += 1 
        if dx_nav != 0 or dy_nav != 0:
            self.row = (self.row - dy_nav + num_rows) % num_rows 
            current_row_len = row_lengths[self.row]
            if current_row_len > 0: self.col = (self.col + dx_nav + current_row_len) % current_row_len
            else: self.col = 0
        elif evt.type == JOYBUTTONDOWN:
            selected_char_or_action = None
            row_content = current_layout[self.row]
            if self.col < len(row_content): selected_char_or_action = row_content[self.col]
            elif self.col == len(row_content) and self.row == num_rows - 1: 
                selected_char_or_action = '123' if self.mode == 'letters' else 'abc'
            if evt.button == BTN_A: 
                if selected_char_or_action:
                    if selected_char_or_action == '123': self.mode = 'symbols'; self.shift = False; self.row, self.col = 0,0 
                    elif selected_char_or_action == 'abc': self.mode = 'letters'; self.row, self.col = 0,0 
                    else: 
                        char_to_add = selected_char_or_action
                        if self.mode == 'letters' and char_to_add.isalpha():
                            char_to_add = char_to_add.upper() if self.shift else char_to_add.lower()
                        self.text += char_to_add
            elif evt.button == BTN_SELECT: self.shift = not self.shift
            elif evt.button == BTN_START: self.done = True; self._text_cancelled = False 
            elif evt.button == BTN_B: self.text = self.text[:-1]
            elif evt.button == BTN_Y: self.done = True; self._text_cancelled = True # Y (West) is cancel

    def get_input(self):
        clock = pygame.time.Clock()
        self.done = False
        self._text_cancelled = False
        while not self.done:
            for e_event in pygame.event.get(): 
                if e_event.type == QUIT: pygame.quit(); sys.exit(0)
                self.handle(e_event)
            self.draw()
            clock.tick(30) 
        return None if self._text_cancelled else self.text

def select_network(screen, font, networks):
    SSID_LIST_LIMIT = 4
    idx = 0  # Index within visible window
    scroll_offset = 0  # Index in networks of first visible item
    count = len(networks)
    if count == 0:
        return "scan"
    clock = pygame.time.Clock()
    while True:
        screen.fill((20,24,40))
        draw_header(screen, font)
        draw_network_list(screen, font, networks, idx, scroll_offset)
        draw_button_hint(screen, font, "Select", 20, SCREEN_HEIGHT-60, (92,92,92), highlight="east") 
        draw_button_hint(screen, font, "Scan", 180, SCREEN_HEIGHT-60, (92,92,92), highlight="west")
        pygame.display.flip()
        for e_event in pygame.event.get():
            if e_event.type == QUIT:
                pygame.quit(); sys.exit(0)
            if is_select_start_held():
                pygame.quit(); sys.exit(0)
            dx_nav, dy_nav = get_nav(e_event)
            if dy_nav > 0:
                # Up
                if idx > 0:
                    idx -= 1
                elif scroll_offset > 0:
                    scroll_offset -= 1
            if dy_nav < 0:
                # Down
                visible_count = min(SSID_LIST_LIMIT, count - scroll_offset)
                if idx < visible_count - 1:
                    idx += 1
                elif scroll_offset + SSID_LIST_LIMIT < count:
                    scroll_offset += 1
            if e_event.type == JOYBUTTONDOWN:
                if e_event.button == BTN_A:
                    return networks[scroll_offset + idx]  # East is Select
                if e_event.button == BTN_Y:
                    return "scan"  # West is Scan
        clock.tick(20)

def select_country(screen, font, countries, current_code=None):
    """
    Simple scrollable list re-using the same look-and-feel as your
    network picker. Returns chosen 2-letter code or None.
    """
    idx = 0
    scroll = 0
    LIST_LIMIT = 8

    # Put current country at the top for convenience
    if current_code:
        countries = sorted(countries, key=lambda c: c[0] != current_code)

    clock = pygame.time.Clock()
    while True:
        screen.fill((20, 24, 40))
        draw_header(screen, font)

        # Paint list –- very similar to draw_network_list(), but simpler
        header_h = 140
        list_h = SCREEN_HEIGHT - header_h
        item_h = list_h // LIST_LIMIT
        y0 = 80

        visible = countries[scroll : scroll + LIST_LIMIT]
        for i, (code, name) in enumerate(visible):
            y = y0 + i * item_h
            rect = pygame.Rect(32, y, SCREEN_WIDTH - 64, item_h - 6)
            selected = i == idx
            pygame.draw.rect(
                screen, (80, 180, 255) if selected else (60, 60, 100), rect, border_radius=12
            )
            if selected:
                pygame.draw.rect(screen, (255, 255, 255), rect, width=3, border_radius=12)

            txt = f"{code} – {name}"
            txt_surf = font.render(txt, True, (255, 255, 0) if selected else (220, 220, 220))
            screen.blit(
                txt_surf,
                (rect.x + 16, rect.y + (rect.height - txt_surf.get_height()) // 2),
            )

        draw_button_hint(screen, font, "Select", 20, SCREEN_HEIGHT - 60, (92, 92, 92), highlight="east")
        draw_button_hint(screen, font, "Cancel", 180, SCREEN_HEIGHT - 60, (92, 92, 92), highlight="south")
        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == QUIT:
                pygame.quit()
                sys.exit(0)
            if is_select_start_held():
                pygame.quit()
                sys.exit(0)

            dx, dy = get_nav(e)
            if dy > 0:  # UP
                if idx > 0:
                    idx -= 1
                elif scroll > 0:
                    scroll -= 1
            if dy < 0:  # DOWN
                if idx < min(LIST_LIMIT, len(countries) - scroll) - 1:
                    idx += 1
                elif scroll + LIST_LIMIT < len(countries):
                    scroll += 1

            if e.type == JOYBUTTONDOWN:
                if e.button == BTN_A:  # Select
                    return countries[scroll + idx][0]
                if e.button == BTN_B:  # Cancel
                    return None

        clock.tick(25)


def display_message_panel(screen, font, title, message, title_color, panel_bg_color, panel_border_color, duration_s=0, ack_button=None):
    screen.fill((20,24,40)) 
    draw_header(screen, font)
    panel_width = SCREEN_WIDTH - 64
    panel_height = 140 if message else 90 
    panel = pygame.Rect(32, SCREEN_HEIGHT//2 - panel_height//2, panel_width, panel_height)
    pygame.draw.rect(screen, panel_bg_color, panel, border_radius=18)
    pygame.draw.rect(screen, panel_border_color, panel, border_radius=18, width=4)
    title_surf = font.render(title, True, title_color)
    title_pos_x = panel.x + (panel.width - title_surf.get_width()) // 2
    title_pos_y = panel.y + 20 
    screen.blit(title_surf, (title_pos_x, title_pos_y))
    if message:
        MAX_CHARS_FOR_MSG = 38 
        msg_str = str(message)
        if len(msg_str) > MAX_CHARS_FOR_MSG: msg_str = msg_str[:MAX_CHARS_FOR_MSG-3] + '...'
        msg_surf = font.render(msg_str, True, (255,255,255)) 
        msg_pos_x = panel.x + (panel.width - msg_surf.get_width()) // 2
        msg_pos_y = title_pos_y + title_surf.get_height() + 10 
        screen.blit(msg_surf, (msg_pos_x, msg_pos_y))
    
    if ack_button is not None and duration_s > 0:
        dismiss_text = f"Press {'B (South)' if ack_button == BTN_B else 'Any Button'} to dismiss"
        dismiss_font_size = FONT_SIZE - 12 # Smaller for dismiss hint
        try: dismiss_font = pygame.font.Font(None, dismiss_font_size)
        except: dismiss_font = pygame.font.SysFont("sans", dismiss_font_size)
        dismiss_surf = dismiss_font.render(dismiss_text, True, (200,200,200))
        dismiss_pos_x = panel.x + (panel.width - dismiss_surf.get_width()) // 2
        dismiss_pos_y = panel.y + panel.height - dismiss_surf.get_height() - 10
        screen.blit(dismiss_surf, (dismiss_pos_x, dismiss_pos_y))
    pygame.display.flip()

    if duration_s > 0:
        start_time = time.time()
        acknowledged = False
        while not acknowledged and (time.time() - start_time < duration_s):
            for e_event in pygame.event.get(): 
                if e_event.type == QUIT: pygame.quit(); sys.exit(0)
                if is_select_start_held(): pygame.quit(); sys.exit(0)
                if ack_button is not None and e_event.type == JOYBUTTONDOWN and e_event.button == ack_button:
                    acknowledged = True; break
                elif ack_button is None and e_event.type == JOYBUTTONDOWN: # Any button if no specific ack_button
                    acknowledged = True; break
            if acknowledged: break
            pygame.time.wait(50)


def main():
    pygame.init()
    pygame.mouse.set_visible(False)
    pygame.joystick.init()
    if pygame.joystick.get_count() == 0: logging.error("No joystick found."); sys.exit(1)
    joy = pygame.joystick.Joystick(0); joy.init()
    logging.info(f"Joystick '{joy.get_name()}' initialized.")

    grabbed_fds = [] 
    try:
        js_fd = open('/dev/input/js0', 'rb')
        EVIOCGRAB = 0x40044590 
        fcntl.ioctl(js_fd.fileno(), EVIOCGRAB, 1) 
        grabbed_fds.append(js_fd)
        logging.debug('Grabbed /dev/input/js0')
        import glob
        for evdev_path in glob.glob('/dev/input/event*'):
            try:
                ev_fd = open(evdev_path, 'rb')
                fcntl.ioctl(ev_fd.fileno(), EVIOCGRAB, 1) 
                grabbed_fds.append(ev_fd)
                logging.debug(f'Grabbed {evdev_path}')
            except Exception as e_grab_ev:
                logging.warning(f'Failed to grab {evdev_path}: {e_grab_ev}.')
                if 'ev_fd' in locals() and ev_fd and not ev_fd.closed: ev_fd.close() 
    except Exception as e_grab_js:
        logging.exception('Failed to grab all input devices.')
        for fd in grabbed_fds:
            if not fd.closed: fd.close()
        grabbed_fds.clear() 

    pygame.display.init() 
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    try: font = pygame.font.Font(None, FONT_SIZE)
    except pygame.error: font = pygame.font.SysFont("sans", FONT_SIZE - 4); logging.warning("Default font failed.")

# ---- WIFI COUNTRY FIRST-TIME CHECK ---------------------------------
    current_country = CountryManager.current()
    if not current_country:
        # Force user to pick before anything else
        while not current_country:
            pick = select_country(screen, font, COUNTRIES)
            if pick:
                display_message_panel(
                    screen,
                    font,
                    "Setting Country …",
                    f"{pick}",
                    (255, 255, 255),
                    (40, 60, 100),
                    (80, 180, 255),
                    duration_s=0.1,
                )
                try:
                    CountryManager.set(pick)
                    current_country = pick
                    display_message_panel(
                        screen,
                        font,
                        "Country Set",
                        None,
                        (0, 200, 0),
                        (0, 60, 0),
                        (0, 200, 0),
                        duration_s=1.2,
                    )
                    pygame.event.clear() # Flush any leftover button presses so they don't propagate to the status screen (e.g. B cancel)
                except Exception as e:
                    logging.error(f"Failed to set Wi-Fi country: {e}")
                    display_message_panel(
                        screen,
                        font,
                        "Error",
                        str(e)[:40],
                        (255, 80, 80),
                        (80, 0, 0),
                        (255, 80, 80),
                        duration_s=3,
                        ack_button=BTN_B,
                    )
            else:
                # They cancelled – keep asking; country is required
                display_message_panel(
                    screen,
                    font,
                    "Country Required",
                    "Press Y to go back",
                    (255, 200, 0),
                    (60, 60, 80),
                    (100, 100, 120),
                    duration_s=3,
                    ack_button=BTN_B,
                )

    vk = VirtualKeyboard(screen, font)
    force_scan_next = False 

    while True: 
        pygame.event.pump() 
        if is_select_start_held(): logging.info("Select+Start detected. Exiting main loop."); break 

        force_scan_this_iteration = force_scan_next
        force_scan_next = False 

        effective_connection_status = False
        if force_scan_this_iteration:
            logging.debug("Forcing scan mode for this iteration.")
            effective_connection_status = False
        else:
            effective_connection_status = WifiManager.is_connected()
        
        if effective_connection_status:
            ssid = WifiManager.current_ssid() or 'Unknown SSID'
            lvl = WifiManager.signal_level() or -100
            screen.fill((20,24,40))
            draw_header(screen, font)
            panel = pygame.Rect(32, 80, SCREEN_WIDTH-64, 120)
            pygame.draw.rect(screen, (40,60,100), panel, border_radius=18)
            pygame.draw.rect(screen, (80,180,255), panel, border_radius=18, width=4)
            screen.blit(font.render('Connected to:', True, (255,255,255)), (panel.x+16, panel.y+16))
            
            max_ssid_width = panel.width - 32 
            ssid_display_surf = font.render(ssid, True, (0,255,0))
            if ssid_display_surf.get_width() > max_ssid_width:
                num_chars_approx = len(ssid) * max_ssid_width // (ssid_display_surf.get_width() if ssid_display_surf.get_width() > 0 else 1)
                ssid_display_surf = font.render(ssid[:max(0, num_chars_approx-3)] + "...", True, (0,255,0))
            screen.blit(ssid_display_surf, (panel.x+16, panel.y+16+FONT_SIZE))
            # Show current wifi country below SSID
            country_code = CountryManager.current() or 'Unknown'
            country_surf = font.render(f"Country: {country_code}", True, (180, 180, 255))
            screen.blit(country_surf, (panel.x+16, panel.y+12+FONT_SIZE*2))
            draw_signal_bars(screen, panel.right-90, panel.y + (panel.height // 2) - 16, lvl)
            draw_button_hint(screen, font, "Scan", 10, SCREEN_HEIGHT-60, (92,92,92), highlight="west")  # Y (West)
            draw_button_hint(screen, font, "Disconnect", 150, SCREEN_HEIGHT-60, (92,92,92), highlight="south", text_offset=40) # B (South)
            draw_button_hint(screen, font, "Select Wifi Country", 10, SCREEN_HEIGHT-120,
                 (92,92,92), highlight="east", text_offset=90)  # A

            pygame.display.flip()

            action_from_status = None
            status_event_loop_active = True
            while status_event_loop_active: 
                for e_event in pygame.event.get():
                    if e_event.type == QUIT: pygame.quit(); sys.exit(0)
                    if is_select_start_held(): 
                        logging.info("Select+Start from status screen. Exiting app.")
                        # Set flag to break outer loop as well
                        force_scan_next = True # Not strictly needed, as we sys.exit
                        status_event_loop_active = False # Break this loop
                        # Perform full exit procedure
                        for fd_clean in grabbed_fds:
                            if not fd_clean.closed: fd_clean.close()
                        if pygame.joystick.get_init(): pygame.joystick.quit()
                        if pygame.display.get_init(): pygame.display.quit()
                        pygame.quit()
                        sys.exit(0)

                    if e_event.type == JOYBUTTONDOWN:
                        if e_event.button == BTN_Y: # Scan (West)
                            logging.debug("Status Screen: Scan chosen.")
                            action_from_status = "scan"
                            status_event_loop_active = False; break 
                        if e_event.button == BTN_B: # Disconnect (South)
                            logging.debug("Status Screen: Disconnect chosen.")
                            action_from_status = "disconnect"
                            status_event_loop_active = False; break
                        if e_event.button == BTN_A:
                            chosen = select_country(screen, font, COUNTRIES, CountryManager.current())
                            if chosen:  
                                try:
                                    if chosen != CountryManager.current():
                                        display_message_panel(screen, font, "Setting Country …", chosen,
                                                             (255, 255, 255), (40, 60, 100),
                                                             (80, 180, 255), duration_s=0.1)
                                        CountryManager.set(chosen)
                                    display_message_panel(screen, font, f"Country set to {chosen}",
                                                         None, (0, 200, 0), (0, 60, 0),
                                                         (0, 200, 0), duration_s=1.5)
                                    pygame.event.clear()
                                    status_event_loop_active = False
                                    break
                                except Exception as e:
                                    display_message_panel(screen, font, "Error", str(e)[:40],
                                                         (255, 80, 80), (80, 0, 0),
                                                         (255, 80, 80), duration_s=3,
                                                         ack_button=BTN_B)
                                    pygame.event.clear()
                                    status_event_loop_active = False
                                    break
                            action_from_status = None  # Stay on status screen
                if not status_event_loop_active: break 
                pygame.time.wait(30) 
            
            if action_from_status == "scan":
                force_scan_next = True
            elif action_from_status == "disconnect":
                display_message_panel(screen, font, "Disconnecting...", None, (255,255,255), (40,60,100), (80,180,255), duration_s=0.1) 
                WifiManager.disconnect() 
            
            continue 

        else: # Not connected or forced scan
            display_message_panel(screen, font, "Scanning WiFi...", None, (255,255,255), (20,24,40), (20,24,40), duration_s=0.1)
            nets = WifiManager.scan_networks()
            if not nets:
                display_message_panel(screen, font, "No Networks Found", "Press B to rescan", (255,200,0), (60,60,80), (100,100,120), duration_s=5, ack_button=BTN_B)
                force_scan_next = True 
                continue 

            choice = select_network(screen, font, nets)
            
            if choice == "scan": force_scan_next = True; continue
            if not choice: force_scan_next = True; continue 

            selected_ssid = choice['ssid']
            psk_password = None
            if choice['secure']:
                vk.text = "" 
                psk_password = vk.get_input()
                if psk_password is None: 
                    logging.debug("Password entry cancelled.")
                    force_scan_next = True; continue 

            if WifiManager.is_connected(): 
                logging.info("Still connected before new attempt (should be rare), disconnecting first.")
                display_message_panel(screen, font, "Preparing...", "Disconnecting old network", (255,255,255), (40,60,100), (80,180,255), duration_s=0.1)
                WifiManager.disconnect()

            display_message_panel(screen, font, f"Connecting to", f"{selected_ssid}...", (255,255,255), (40,60,100), (80,180,255), duration_s=0.1)
            
            connection_successful = False
            error_message = "Connection timed out." 

            try:
                WifiManager.connect(selected_ssid, psk_password)
                logging.debug(f"Connect cmd sent for {selected_ssid}. Polling for confirmation (up to 20s)...")
                poll_start_time = time.time()
                while time.time() - poll_start_time < 20: 
                    for evt_poll in pygame.event.get(): 
                        if evt_poll.type == QUIT: pygame.quit(); sys.exit(0)
                        if is_select_start_held(): 
                            # Full exit procedure from polling loop
                            for fd_clean in grabbed_fds:
                                if not fd_clean.closed: fd_clean.close()
                            if pygame.joystick.get_init(): pygame.joystick.quit()
                            if pygame.display.get_init(): pygame.display.quit()
                            pygame.quit()
                            sys.exit(0)
                    current_ssid_polled = WifiManager.current_ssid()
                    if current_ssid_polled == selected_ssid and WifiManager.is_connected():
                        connection_successful = True
                        WifiManager.save_configuration() 
                        logging.info(f"Successfully connected to {selected_ssid}.")
                        break 
                    time.sleep(0.5) 
                
                if not connection_successful: 
                    wpa_status = WifiManager.get_wpa_status()
                    if wpa_status:
                        logging.debug(f"wpa_cli status on failure: {wpa_status}")
                        if "reason=WRONG_KEY" in wpa_status or "WPA: Invalid PSK" in wpa_status.upper(): error_message = "Wrong Password."
                        elif "state=4WAY_HANDSHAKE" in wpa_status and (time.time() - poll_start_time >= 19): error_message = "Auth Error (Handshake)."
            except subprocess.CalledProcessError as e:
                cmd_name = e.cmd[-1] if isinstance(e.cmd, list) and e.cmd else "wpa_cli"
                error_message = f"Config error ({cmd_name})"
                logging.error(f"Connection to {selected_ssid} failed (CalledProcessError): {e.stderr or e.stdout or e}")
            except subprocess.TimeoutExpired as e_to: # Renamed e to e_to
                error_message = "Connection command timed out."
                logging.error(f"Connection command for {selected_ssid} timed out: {e_to}")
            except Exception as e_exc: # Renamed e to e_exc
                error_message = f"Error: {str(e_exc)[:30]}" 
                logging.error(f"Connection to {selected_ssid} failed (Unexpected Exception): {e_exc}", exc_info=True)

            if not connection_successful:
                display_message_panel(screen, font, 'Connection Failed', error_message, (255,80,80), (80,0,0), (255,80,80), duration_s=5, ack_button=BTN_B)
                force_scan_next = True 
            else: 
                display_message_panel(screen, font, "Connected!", f"To {selected_ssid}", (0,200,0), (0,60,0), (0,200,0), duration_s=2)
            
            continue 

    # Cleanup when main loop exits (e.g. by Select+Start breaking the loop)
    for fd in grabbed_fds:
        if not fd.closed:
            # Optional: Release EVIOCGRAB: fcntl.ioctl(fd.fileno(), EVIOCGRAB, 0) 
            fd.close()
    logging.debug("Released grabbed input devices.")
    
    if pygame.joystick.get_init(): pygame.joystick.quit()
    if pygame.display.get_init(): pygame.display.quit()
    pygame.quit()
    logging.info("=== Exiting Wifi.py Gracefully ===")
    sys.exit(0)

if __name__ == '__main__':
    try:
        main()
    except SystemExit: 
        pass 
    except Exception as e:
        logging.exception('Unhandled top-level crash in Wifi.py')
        try:
            if pygame.joystick.get_init(): pygame.joystick.quit()
            if pygame.display.get_init(): pygame.display.quit()
            pygame.quit()
        except: pass 
        sys.exit(1)
