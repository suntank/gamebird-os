#!/usr/bin/env python3
"""
update_progress.py – Simple progress display for Game Bird OS updates.
Controlled via a named pipe for IPC with the shell script.
"""
import os
import sys
import pygame
from pygame.locals import *

SCREEN_WIDTH, SCREEN_HEIGHT = 480, 480
FIFO_PATH = "/tmp/update_progress_fifo"

# Colors
BG_COLOR = (20, 24, 40)
TEXT_COLOR = (220, 220, 220)
BAR_BG_COLOR = (40, 44, 60)
BAR_FG_COLOR = (80, 180, 255)
ACCENT_COLOR = (255, 255, 0)


def main():
    pygame.init()
    pygame.mouse.set_visible(False)
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Updating...")
    
    font_large = pygame.font.Font(None, 64)
    font_small = pygame.font.Font(None, 36)
    clock = pygame.time.Clock()
    
    # Create FIFO for receiving progress updates
    if os.path.exists(FIFO_PATH):
        os.remove(FIFO_PATH)
    os.mkfifo(FIFO_PATH)
    
    # Open FIFO in non-blocking mode
    fifo_fd = os.open(FIFO_PATH, os.O_RDONLY | os.O_NONBLOCK)
    fifo = os.fdopen(fifo_fd, 'r')
    
    message = "Updating..."
    progress = 0.0  # 0.0 to 1.0
    running = True
    
    def draw():
        screen.fill(BG_COLOR)
        
        # Draw message centered
        msg_surf = font_large.render(message, True, TEXT_COLOR)
        msg_x = (SCREEN_WIDTH - msg_surf.get_width()) // 2
        msg_y = SCREEN_HEIGHT // 2 - 60
        screen.blit(msg_surf, (msg_x, msg_y))
        
        # Draw progress bar
        bar_width = 360
        bar_height = 24
        bar_x = (SCREEN_WIDTH - bar_width) // 2
        bar_y = SCREEN_HEIGHT // 2 + 10
        
        # Background
        pygame.draw.rect(screen, BAR_BG_COLOR, (bar_x, bar_y, bar_width, bar_height), border_radius=12)
        
        # Filled portion
        fill_width = int(bar_width * progress)
        if fill_width > 0:
            pygame.draw.rect(screen, BAR_FG_COLOR, (bar_x, bar_y, fill_width, bar_height), border_radius=12)
        
        # Border
        pygame.draw.rect(screen, TEXT_COLOR, (bar_x, bar_y, bar_width, bar_height), width=2, border_radius=12)
        
        # Percentage text
        pct_text = f"{int(progress * 100)}%"
        pct_surf = font_small.render(pct_text, True, TEXT_COLOR)
        pct_x = (SCREEN_WIDTH - pct_surf.get_width()) // 2
        pct_y = bar_y + bar_height + 16
        screen.blit(pct_surf, (pct_x, pct_y))
        
        pygame.display.flip()
    
    try:
        while running:
            # Handle pygame events
            for event in pygame.event.get():
                if event.type == QUIT:
                    running = False
            
            # Read commands from FIFO
            try:
                line = fifo.readline()
                if line:
                    line = line.strip()
                    if line.startswith("MSG:"):
                        message = line[4:]
                    elif line.startswith("PCT:"):
                        try:
                            progress = float(line[4:]) / 100.0
                        except ValueError:
                            pass
                    elif line == "QUIT":
                        running = False
            except (IOError, BlockingIOError):
                pass
            
            draw()
            clock.tick(30)
    finally:
        fifo.close()
        if os.path.exists(FIFO_PATH):
            os.remove(FIFO_PATH)
        pygame.quit()


if __name__ == "__main__":
    main()
