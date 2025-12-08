#!/usr/bin/env python3
"""
show_changelog.py – Game Bird styled changelog viewer.
Reads a CHANGELOG.md file and displays it in a scrollable SNES-style UI.
"""
import os
import sys
import pygame
from pygame.locals import *

SCREEN_WIDTH, SCREEN_HEIGHT = 480, 480
FONT_SIZE = 28
CHANGELOG_PATH = '/home/pi/gamebird-os/CHANGELOG.md'

BTN_A      = 0  # Typically East
BTN_B      = 1  # South
BTN_SELECT = 6
BTN_START  = 7

def is_select_start_held(joy):
    try:
        return joy.get_button(BTN_SELECT) and joy.get_button(BTN_START)
    except pygame.error:
        return False

def read_changelog_lines():
    if not os.path.exists(CHANGELOG_PATH):
        return ["No changelog found."]
    with open(CHANGELOG_PATH, "r") as f:
        return f.readlines()

def draw_changelog(screen, font, lines, scroll):
    screen.fill((20, 24, 40))
    y_offset = 20
    line_height = font.get_linesize()
    max_lines = (SCREEN_HEIGHT - 40) // line_height
    visible_lines = lines[scroll:scroll + max_lines]
    for i, line in enumerate(visible_lines):
        text_surf = font.render(line.strip(), True, (255, 255, 255))
        screen.blit(text_surf, (20, y_offset + i * line_height))
    pygame.display.flip()

def main():
    pygame.init()
    pygame.joystick.init()
    pygame.mouse.set_visible(False)

    if pygame.joystick.get_count() == 0:
        print("No joystick found.")
        sys.exit(1)
    joy = pygame.joystick.Joystick(0)
    joy.init()

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    font = pygame.font.Font(None, FONT_SIZE)
    lines = read_changelog_lines()
    scroll = 0
    max_scroll = max(0, len(lines) - (SCREEN_HEIGHT // font.get_linesize()) + 1)

    clock = pygame.time.Clock()
    running = True

    while running:
        draw_changelog(screen, font, lines, scroll)
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            if is_select_start_held(joy):
                running = False
            if event.type == JOYHATMOTION:
                dx, dy = event.value
                if dy == 1 and scroll > 0:
                    scroll -= 1
                elif dy == -1 and scroll < max_scroll:
                    scroll += 1
            if event.type == JOYBUTTONDOWN and event.button == BTN_B:
                running = False
        clock.tick(30)

    pygame.quit()

if __name__ == "__main__":
    main()
