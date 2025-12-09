#!/usr/bin/env python3
"""
timezone_setup.py – Game Bird timezone and time configuration.
Allows setting timezone from a list, and manual time entry when WiFi is disconnected.
"""
import os
import sys
import subprocess
import pygame
from pygame.locals import *

SCREEN_WIDTH, SCREEN_HEIGHT = 480, 480

# Colors (matching nest-frontend style)
BG_COLOR = (20, 24, 40)
TEXT_COLOR = (220, 220, 220)
HEADER_COLOR = (80, 180, 255)
ACCENT_COLOR = (255, 255, 0)
DIM_COLOR = (120, 120, 140)
SELECTED_BG = (40, 60, 100)
ERROR_COLOR = (255, 100, 100)

# Button Mappings (GameHat / SNES Style)
BTN_A = 0
BTN_B = 1
BTN_X = 5
BTN_Y = 3
BTN_L = 4
BTN_R = 2
BTN_SELECT = 6
BTN_START = 7

# Common timezones (grouped by region for easier navigation)
TIMEZONES = [
    # US
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "America/Anchorage",
    "Pacific/Honolulu",
    # Canada
    "America/Toronto",
    "America/Vancouver",
    # Europe
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Europe/Rome",
    "Europe/Madrid",
    "Europe/Amsterdam",
    "Europe/Stockholm",
    "Europe/Moscow",
    # Asia
    "Asia/Tokyo",
    "Asia/Shanghai",
    "Asia/Hong_Kong",
    "Asia/Singapore",
    "Asia/Seoul",
    "Asia/Kolkata",
    "Asia/Dubai",
    # Australia/Pacific
    "Australia/Sydney",
    "Australia/Melbourne",
    "Australia/Perth",
    "Pacific/Auckland",
    # South America
    "America/Sao_Paulo",
    "America/Buenos_Aires",
    "America/Santiago",
    # Africa
    "Africa/Cairo",
    "Africa/Johannesburg",
    "Africa/Lagos",
    # UTC
    "UTC",
]

# UI Constants
MARGIN_X = 20
MARGIN_Y = 80
ITEM_HEIGHT = 44
VISIBLE_ITEMS = 8


class InputManager:
    """Handle gamehat controller and keyboard input."""
    def __init__(self):
        if pygame.joystick.get_count() > 0:
            self.joy = pygame.joystick.Joystick(0)
            self.joy.init()
        else:
            self.joy = None
        self.held_directions = set()

    def get_events(self):
        actions = []
        for event in pygame.event.get():
            if event.type == QUIT:
                actions.append("QUIT")

            elif event.type == JOYBUTTONDOWN:
                if event.button == BTN_A:
                    actions.append("A")
                elif event.button == BTN_B:
                    actions.append("B")
                elif event.button == BTN_L:
                    actions.append("L")
                elif event.button == BTN_R:
                    actions.append("R")
                elif event.button == BTN_START:
                    actions.append("START")
                elif event.button == BTN_SELECT:
                    actions.append("SELECT")
                elif event.button == BTN_X:
                    actions.append("X")
                elif event.button == BTN_Y:
                    actions.append("Y")

            elif event.type == JOYHATMOTION:
                dx, dy = event.value
                if dy == 1:
                    actions.append("UP")
                    self.held_directions.add("UP")
                elif dy == -1:
                    actions.append("DOWN")
                    self.held_directions.add("DOWN")
                elif dx == -1:
                    actions.append("LEFT")
                    self.held_directions.add("LEFT")
                elif dx == 1:
                    actions.append("RIGHT")
                    self.held_directions.add("RIGHT")
                else:
                    self.held_directions.discard("UP")
                    self.held_directions.discard("DOWN")
                    self.held_directions.discard("LEFT")
                    self.held_directions.discard("RIGHT")

            elif event.type == JOYAXISMOTION:
                if event.axis == 1:  # Vertical
                    if event.value < -0.5:
                        actions.append("UP")
                        self.held_directions.add("UP")
                    elif event.value > 0.5:
                        actions.append("DOWN")
                        self.held_directions.add("DOWN")
                    else:
                        self.held_directions.discard("UP")
                        self.held_directions.discard("DOWN")
                elif event.axis == 0:  # Horizontal
                    if event.value < -0.5:
                        actions.append("LEFT")
                        self.held_directions.add("LEFT")
                    elif event.value > 0.5:
                        actions.append("RIGHT")
                        self.held_directions.add("RIGHT")
                    else:
                        self.held_directions.discard("LEFT")
                        self.held_directions.discard("RIGHT")

            elif event.type == KEYDOWN:
                if event.key == K_UP:
                    actions.append("UP")
                elif event.key == K_DOWN:
                    actions.append("DOWN")
                elif event.key == K_LEFT:
                    actions.append("LEFT")
                elif event.key == K_RIGHT:
                    actions.append("RIGHT")
                elif event.key == K_RETURN or event.key == K_z:
                    actions.append("A")
                elif event.key == K_ESCAPE or event.key == K_x:
                    actions.append("B")
                elif event.key == K_t:
                    actions.append("X")
                elif event.key == K_s:
                    actions.append("START")
                elif event.key == K_q:
                    actions.append("QUIT")

        return actions


def get_current_timezone():
    """Get the current system timezone."""
    try:
        result = subprocess.run(["timedatectl", "show", "--property=Timezone", "--value"],
                                capture_output=True, text=True)
        return result.stdout.strip()
    except Exception:
        # Fallback: read /etc/timezone
        try:
            with open("/etc/timezone", "r") as f:
                return f.read().strip()
        except Exception:
            return "Unknown"


def get_current_time():
    """Get current system time as formatted string."""
    try:
        result = subprocess.run(["date", "+%Y-%m-%d %H:%M:%S"], capture_output=True, text=True)
        return result.stdout.strip()
    except Exception:
        return "Unknown"


def is_wifi_connected():
    """Check if WiFi is connected."""
    try:
        with open("/sys/class/net/wlan0/carrier", "r") as f:
            return f.read().strip() == "1"
    except Exception:
        return False


def set_timezone(tz):
    """Set the system timezone."""
    try:
        subprocess.run(["sudo", "timedatectl", "set-timezone", tz], check=True)
        return True
    except Exception as e:
        print(f"Failed to set timezone: {e}")
        return False


def set_manual_time(year, month, day, hour, minute):
    """Set the system time manually."""
    try:
        # Disable NTP first
        subprocess.run(["sudo", "timedatectl", "set-ntp", "false"], check=True)
        # Set time
        time_str = f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:00"
        subprocess.run(["sudo", "timedatectl", "set-time", time_str], check=True)
        return True
    except Exception as e:
        print(f"Failed to set time: {e}")
        return False


def enable_ntp():
    """Re-enable NTP time sync."""
    try:
        subprocess.run(["sudo", "timedatectl", "set-ntp", "true"], check=True)
        return True
    except Exception:
        return False


class TimezoneApp:
    def __init__(self):
        pygame.init()
        pygame.joystick.init()
        pygame.mouse.set_visible(False)
        
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Timezone Setup")
        
        self.font = pygame.font.Font(None, 36)
        self.font_large = pygame.font.Font(None, 48)
        self.font_small = pygame.font.Font(None, 28)
        
        self.input_mgr = InputManager()
        self.clock = pygame.time.Clock()
        
        self.current_tz = get_current_timezone()
        self.selected_index = 0
        self.scroll_offset = 0
        
        # Try to select current timezone in list
        if self.current_tz in TIMEZONES:
            self.selected_index = TIMEZONES.index(self.current_tz)
            self.scroll_offset = max(0, self.selected_index - VISIBLE_ITEMS // 2)
        
        # Time edit mode
        self.time_edit_mode = False
        self.time_fields = [2025, 1, 1, 12, 0]  # year, month, day, hour, minute
        self.time_field_index = 0
        self.wifi_connected = is_wifi_connected()
        
        # Hold repeat
        self.hold_timer = 0
        
        self.running = True

    def update_time_fields_from_system(self):
        """Update time fields from current system time."""
        try:
            import datetime
            now = datetime.datetime.now()
            self.time_fields = [now.year, now.month, now.day, now.hour, now.minute]
        except Exception:
            pass

    def draw_timezone_list(self):
        """Draw the timezone selection screen."""
        self.screen.fill(BG_COLOR)
        
        # Header
        header = self.font_large.render("Timezone Setup", True, TEXT_COLOR)
        self.screen.blit(header, (MARGIN_X, 15))
        
        # Current timezone display
        tz_label = self.font_small.render("Current:", True, DIM_COLOR)
        self.screen.blit(tz_label, (MARGIN_X, 55))
        tz_value = self.font.render(self.current_tz, True, ACCENT_COLOR)
        self.screen.blit(tz_value, (MARGIN_X + 80, 52))
        
        # Separator
        pygame.draw.line(self.screen, DIM_COLOR, (MARGIN_X, 75), (SCREEN_WIDTH - MARGIN_X, 75), 1)
        
        # Timezone list
        list_y = MARGIN_Y
        for i in range(VISIBLE_ITEMS):
            idx = self.scroll_offset + i
            if idx >= len(TIMEZONES):
                break
            
            tz = TIMEZONES[idx]
            y = list_y + i * ITEM_HEIGHT
            
            # Highlight selected
            if idx == self.selected_index:
                pygame.draw.rect(self.screen, SELECTED_BG, 
                               (MARGIN_X - 5, y - 2, SCREEN_WIDTH - MARGIN_X * 2 + 10, ITEM_HEIGHT - 4),
                               border_radius=6)
                color = HEADER_COLOR
            elif tz == self.current_tz:
                color = ACCENT_COLOR
            else:
                color = TEXT_COLOR
            
            # Draw timezone name (simplified display)
            display_name = tz.replace("_", " ")
            text_surf = self.font.render(display_name, True, color)
            self.screen.blit(text_surf, (MARGIN_X + 10, y + 6))
        
        # Scroll indicators
        if self.scroll_offset > 0:
            arrow_up = self.font.render("▲", True, DIM_COLOR)
            self.screen.blit(arrow_up, (SCREEN_WIDTH // 2 - 10, list_y - 20))
        if self.scroll_offset + VISIBLE_ITEMS < len(TIMEZONES):
            arrow_down = self.font.render("▼", True, DIM_COLOR)
            self.screen.blit(arrow_down, (SCREEN_WIDTH // 2 - 10, list_y + VISIBLE_ITEMS * ITEM_HEIGHT))
        
        # Bottom hints
        hint_y = SCREEN_HEIGHT - 35
        pygame.draw.line(self.screen, DIM_COLOR, (MARGIN_X, hint_y - 10), (SCREEN_WIDTH - MARGIN_X, hint_y - 10), 1)
        
        wifi_status = "WiFi: Connected" if self.wifi_connected else "WiFi: Off"
        wifi_color = HEADER_COLOR if self.wifi_connected else ERROR_COLOR
        wifi_surf = self.font_small.render(wifi_status, True, wifi_color)
        self.screen.blit(wifi_surf, (MARGIN_X, hint_y))
        
        if not self.wifi_connected:
            hint = "A Select  X Set Time  START Exit"
        else:
            hint = "A Select  START Exit"
        hint_surf = self.font_small.render(hint, True, DIM_COLOR)
        self.screen.blit(hint_surf, (SCREEN_WIDTH - hint_surf.get_width() - MARGIN_X, hint_y))
        
        pygame.display.flip()

    def draw_time_edit(self):
        """Draw the manual time edit screen."""
        self.screen.fill(BG_COLOR)
        
        # Header
        header = self.font_large.render("Set Time Manually", True, TEXT_COLOR)
        self.screen.blit(header, (MARGIN_X, 15))
        
        # Separator
        pygame.draw.line(self.screen, DIM_COLOR, (MARGIN_X, 55), (SCREEN_WIDTH - MARGIN_X, 55), 1)
        
        # Time display
        labels = ["Year", "Month", "Day", "Hour", "Minute"]
        field_x = [60, 150, 230, 320, 410]
        
        y_label = 100
        y_value = 150
        
        for i, (label, val) in enumerate(zip(labels, self.time_fields)):
            # Label
            label_surf = self.font_small.render(label, True, DIM_COLOR)
            lx = field_x[i] - label_surf.get_width() // 2
            self.screen.blit(label_surf, (lx, y_label))
            
            # Value
            if i == 0:  # Year
                val_str = f"{val:04d}"
            else:
                val_str = f"{val:02d}"
            
            color = ACCENT_COLOR if i == self.time_field_index else TEXT_COLOR
            val_surf = self.font_large.render(val_str, True, color)
            vx = field_x[i] - val_surf.get_width() // 2
            self.screen.blit(val_surf, (vx, y_value))
            
            # Selection indicator
            if i == self.time_field_index:
                pygame.draw.rect(self.screen, HEADER_COLOR,
                               (vx - 5, y_value - 5, val_surf.get_width() + 10, val_surf.get_height() + 10),
                               width=2, border_radius=4)
        
        # Separators between date parts
        sep_y = y_value + 15
        sep_surf = self.font_large.render("-", True, DIM_COLOR)
        self.screen.blit(sep_surf, (105, y_value))
        self.screen.blit(sep_surf, (190, y_value))
        colon_surf = self.font_large.render(":", True, DIM_COLOR)
        self.screen.blit(colon_surf, (365, y_value))
        
        # Preview
        preview_y = 250
        preview_str = f"{self.time_fields[0]:04d}-{self.time_fields[1]:02d}-{self.time_fields[2]:02d} {self.time_fields[3]:02d}:{self.time_fields[4]:02d}"
        preview_surf = self.font.render(preview_str, True, HEADER_COLOR)
        px = (SCREEN_WIDTH - preview_surf.get_width()) // 2
        self.screen.blit(preview_surf, (px, preview_y))
        
        # Instructions
        inst_y = 320
        inst1 = self.font_small.render("LEFT/RIGHT: Select field", True, DIM_COLOR)
        inst2 = self.font_small.render("UP/DOWN: Change value", True, DIM_COLOR)
        inst3 = self.font_small.render("A: Apply time   B: Cancel", True, DIM_COLOR)
        self.screen.blit(inst1, ((SCREEN_WIDTH - inst1.get_width()) // 2, inst_y))
        self.screen.blit(inst2, ((SCREEN_WIDTH - inst2.get_width()) // 2, inst_y + 30))
        self.screen.blit(inst3, ((SCREEN_WIDTH - inst3.get_width()) // 2, inst_y + 60))
        
        pygame.display.flip()

    def handle_timezone_input(self, actions):
        """Handle input for timezone selection."""
        for action in actions:
            if action == "QUIT" or action == "START":
                self.running = False
            elif action == "UP":
                if self.selected_index > 0:
                    self.selected_index -= 1
                    if self.selected_index < self.scroll_offset:
                        self.scroll_offset = self.selected_index
            elif action == "DOWN":
                if self.selected_index < len(TIMEZONES) - 1:
                    self.selected_index += 1
                    if self.selected_index >= self.scroll_offset + VISIBLE_ITEMS:
                        self.scroll_offset = self.selected_index - VISIBLE_ITEMS + 1
            elif action == "L":
                # Page up
                self.selected_index = max(0, self.selected_index - VISIBLE_ITEMS)
                self.scroll_offset = max(0, self.scroll_offset - VISIBLE_ITEMS)
            elif action == "R":
                # Page down
                self.selected_index = min(len(TIMEZONES) - 1, self.selected_index + VISIBLE_ITEMS)
                self.scroll_offset = min(len(TIMEZONES) - VISIBLE_ITEMS, self.scroll_offset + VISIBLE_ITEMS)
            elif action == "A":
                # Select timezone
                new_tz = TIMEZONES[self.selected_index]
                if set_timezone(new_tz):
                    self.current_tz = new_tz
            elif action == "X" and not self.wifi_connected:
                # Enter time edit mode (only if WiFi disconnected)
                self.update_time_fields_from_system()
                self.time_edit_mode = True
                self.time_field_index = 0
            elif action == "B":
                self.running = False

    def handle_time_edit_input(self, actions):
        """Handle input for time editing."""
        # Field limits: year (2020-2099), month (1-12), day (1-31), hour (0-23), minute (0-59)
        limits = [(2020, 2099), (1, 12), (1, 31), (0, 23), (0, 59)]
        
        for action in actions:
            if action == "B":
                self.time_edit_mode = False
            elif action == "LEFT":
                self.time_field_index = (self.time_field_index - 1) % 5
            elif action == "RIGHT":
                self.time_field_index = (self.time_field_index + 1) % 5
            elif action == "UP":
                min_val, max_val = limits[self.time_field_index]
                self.time_fields[self.time_field_index] += 1
                if self.time_fields[self.time_field_index] > max_val:
                    self.time_fields[self.time_field_index] = min_val
            elif action == "DOWN":
                min_val, max_val = limits[self.time_field_index]
                self.time_fields[self.time_field_index] -= 1
                if self.time_fields[self.time_field_index] < min_val:
                    self.time_fields[self.time_field_index] = max_val
            elif action == "A":
                # Apply time
                if set_manual_time(*self.time_fields):
                    self.time_edit_mode = False

    def run(self):
        while self.running:
            actions = self.input_mgr.get_events()
            
            # Update WiFi status periodically
            self.wifi_connected = is_wifi_connected()
            
            if self.time_edit_mode:
                self.handle_time_edit_input(actions)
                self.draw_time_edit()
            else:
                self.handle_timezone_input(actions)
                self.draw_timezone_list()
            
            self.clock.tick(30)
        
        pygame.quit()


def main():
    app = TimezoneApp()
    app.run()


if __name__ == "__main__":
    main()
