#!/usr/bin/env python3
"""
show_changelog.py – Game Bird styled changelog viewer.
Reads a CHANGELOG.md file and displays it in a smooth scrolling UI.
"""
import os
import sys
import pygame
from pygame.locals import *

SCREEN_WIDTH, SCREEN_HEIGHT = 480, 480
FONT_SIZE = 22
TITLE_FONT_SIZE = 28
CHANGELOG_PATH = '/home/pi/gamebird-os/CHANGELOG.md'

# Colors (matching nest-frontend style)
BG_COLOR = (20, 24, 40)
TEXT_COLOR = (220, 220, 220)
HEADER_COLOR = (80, 180, 255)
ACCENT_COLOR = (255, 255, 0)
DIM_COLOR = (120, 120, 140)

# Button Mappings (GameHat / SNES Style)
BTN_A      = 0
BTN_B      = 1
BTN_X      = 5
BTN_Y      = 3
BTN_L      = 4
BTN_R      = 2
BTN_SELECT = 6
BTN_START  = 7

# Scroll settings
SCROLL_SPEED = 8        # pixels per input
SCROLL_FAST = 40        # pixels for L/R page scroll
MARGIN_X = 20
MARGIN_Y = 50
CONTENT_HEIGHT = SCREEN_HEIGHT - MARGIN_Y - 30


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

            elif event.type == JOYHATMOTION:
                dx, dy = event.value
                if dy == 1:
                    actions.append("UP")
                    self.held_directions.add("UP")
                elif dy == -1:
                    actions.append("DOWN")
                    self.held_directions.add("DOWN")
                else:
                    self.held_directions.discard("UP")
                    self.held_directions.discard("DOWN")

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

            elif event.type == KEYDOWN:
                if event.key == K_UP:
                    actions.append("UP")
                    self.held_directions.add("UP")
                elif event.key == K_DOWN:
                    actions.append("DOWN")
                    self.held_directions.add("DOWN")
                elif event.key == K_PAGEUP:
                    actions.append("L")
                elif event.key == K_PAGEDOWN:
                    actions.append("R")
                elif event.key == K_ESCAPE or event.key == K_a:
                    actions.append("B")
                elif event.key == K_q:
                    actions.append("QUIT")

            elif event.type == KEYUP:
                if event.key == K_UP:
                    self.held_directions.discard("UP")
                elif event.key == K_DOWN:
                    self.held_directions.discard("DOWN")

        return actions

    def is_select_start_held(self):
        if self.joy:
            try:
                return self.joy.get_button(BTN_SELECT) and self.joy.get_button(BTN_START)
            except pygame.error:
                pass
        return False


def read_changelog():
    """Read changelog and return as list of (text, is_header) tuples."""
    if not os.path.exists(CHANGELOG_PATH):
        return [("No changelog found.", False)]
    
    lines = []
    with open(CHANGELOG_PATH, "r") as f:
        for line in f:
            text = line.rstrip()
            if text.startswith("# "):
                lines.append((text[2:], "h1"))
            elif text.startswith("## "):
                lines.append((text[3:], "h2"))
            elif text.startswith("### "):
                lines.append((text[4:], "h3"))
            elif text.startswith("- "):
                lines.append(("• " + text[2:], "bullet"))
            elif text.strip():
                lines.append((text, "text"))
            else:
                lines.append(("", "blank"))
    return lines


def render_changelog_surface(lines, font, title_font, width):
    """Pre-render the entire changelog to a surface for smooth scrolling."""
    line_height = font.get_linesize() + 4
    title_height = title_font.get_linesize() + 8
    
    # Calculate total height
    total_height = 20  # top padding
    for text, style in lines:
        if style in ("h1", "h2"):
            total_height += title_height
        elif style == "blank":
            total_height += line_height // 2
        else:
            total_height += line_height
    total_height += 40  # bottom padding
    
    # Create surface
    surface = pygame.Surface((width, total_height), pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0))
    
    y = 20
    for text, style in lines:
        if style == "h1":
            surf = title_font.render(text, True, HEADER_COLOR)
            surface.blit(surf, (0, y))
            y += title_height
        elif style == "h2":
            surf = title_font.render(text, True, ACCENT_COLOR)
            surface.blit(surf, (0, y))
            y += title_height
        elif style == "h3":
            surf = font.render(text, True, HEADER_COLOR)
            surface.blit(surf, (10, y))
            y += line_height
        elif style == "bullet":
            surf = font.render(text, True, TEXT_COLOR)
            surface.blit(surf, (20, y))
            y += line_height
        elif style == "blank":
            y += line_height // 2
        else:
            surf = font.render(text, True, TEXT_COLOR)
            surface.blit(surf, (0, y))
            y += line_height
    
    return surface


def draw_screen(screen, content_surface, scroll_y, font):
    """Draw the changelog viewer screen."""
    screen.fill(BG_COLOR)
    
    # Draw title bar
    title_text = "Change Log"
    title_surf = font.render(title_text, True, TEXT_COLOR)
    screen.blit(title_surf, (MARGIN_X, 15))
    
    # Draw separator line
    pygame.draw.line(screen, DIM_COLOR, (MARGIN_X, 42), (SCREEN_WIDTH - MARGIN_X, 42), 1)
    
    # Create clipping rect for content area
    content_rect = pygame.Rect(MARGIN_X, MARGIN_Y, SCREEN_WIDTH - MARGIN_X * 2, CONTENT_HEIGHT)
    
    # Blit the content surface with scroll offset
    screen.set_clip(content_rect)
    screen.blit(content_surface, (MARGIN_X, MARGIN_Y - scroll_y))
    screen.set_clip(None)
    
    # Draw scroll indicators
    max_scroll = max(0, content_surface.get_height() - CONTENT_HEIGHT)
    if max_scroll > 0:
        # Scrollbar track
        track_x = SCREEN_WIDTH - 12
        track_y = MARGIN_Y
        track_height = CONTENT_HEIGHT
        pygame.draw.rect(screen, (40, 44, 60), (track_x, track_y, 6, track_height), border_radius=3)
        
        # Scrollbar thumb
        thumb_height = max(20, int(track_height * (CONTENT_HEIGHT / content_surface.get_height())))
        thumb_y = track_y + int((track_height - thumb_height) * (scroll_y / max_scroll)) if max_scroll > 0 else track_y
        pygame.draw.rect(screen, HEADER_COLOR, (track_x, thumb_y, 6, thumb_height), border_radius=3)
    
    # Draw hint bar at bottom
    hint_y = SCREEN_HEIGHT - 22
    pygame.draw.line(screen, DIM_COLOR, (MARGIN_X, hint_y - 8), (SCREEN_WIDTH - MARGIN_X, hint_y - 8), 1)
    hint_font = pygame.font.Font(None, 18)
    hint_text = "↑↓ Scroll   L/R Page   B Back"
    hint_surf = hint_font.render(hint_text, True, DIM_COLOR)
    screen.blit(hint_surf, ((SCREEN_WIDTH - hint_surf.get_width()) // 2, hint_y))
    
    pygame.display.flip()


def main():
    pygame.init()
    pygame.joystick.init()
    pygame.mouse.set_visible(False)

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Change Log")
    
    font = pygame.font.Font(None, FONT_SIZE)
    title_font = pygame.font.Font(None, TITLE_FONT_SIZE)
    
    input_mgr = InputManager()
    
    # Load and render changelog
    lines = read_changelog()
    content_width = SCREEN_WIDTH - MARGIN_X * 2 - 20  # leave room for scrollbar
    content_surface = render_changelog_surface(lines, font, title_font, content_width)
    
    scroll_y = 0
    max_scroll = max(0, content_surface.get_height() - CONTENT_HEIGHT)
    
    clock = pygame.time.Clock()
    running = True
    hold_timer = 0

    while running:
        actions = input_mgr.get_events()
        
        for action in actions:
            if action == "QUIT":
                running = False
            elif action == "B":
                running = False
            elif action == "UP":
                scroll_y = max(0, scroll_y - SCROLL_SPEED)
            elif action == "DOWN":
                scroll_y = min(max_scroll, scroll_y + SCROLL_SPEED)
            elif action == "L":
                scroll_y = max(0, scroll_y - SCROLL_FAST)
            elif action == "R":
                scroll_y = min(max_scroll, scroll_y + SCROLL_FAST)
        
        # Handle held directions for continuous scrolling
        if "UP" in input_mgr.held_directions:
            hold_timer += 1
            if hold_timer > 10:  # delay before repeat
                scroll_y = max(0, scroll_y - SCROLL_SPEED // 2)
        elif "DOWN" in input_mgr.held_directions:
            hold_timer += 1
            if hold_timer > 10:
                scroll_y = min(max_scroll, scroll_y + SCROLL_SPEED // 2)
        else:
            hold_timer = 0
        
        # Check SELECT+START combo to exit
        if input_mgr.is_select_start_held():
            running = False
        
        draw_screen(screen, content_surface, scroll_y, title_font)
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
