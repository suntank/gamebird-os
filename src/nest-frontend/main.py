#!/usr/bin/env python3
"""
Game Bird Store Client
----------------------
Internal Resolution: 240x240
Physical Output:     480x480 (2x Upscale)
"""

import os
import sys
import subprocess
import pygame
import logging
from pygame.locals import *

from store_client.config import load_config
from store_client.http_client import HttpClient
from store_client.cdn_api import CdnApi
from store_client.repository import Repository
from store_client.installer import Installer
from store_client.updater import Updater
from store_client.ui.controller_input import InputManager
from store_client.ui.screens import MainMenu, CatalogList, GameDetail, DownloadScreen, InstalledList, UpdateCheck, ParentalControlsScreen, DeveloperCodeScreen, RebootScreen, FilterScreen
from store_client.parental_controls import ParentalControls

# --- CONFIGURATION ---
PHYSICAL_WIDTH, PHYSICAL_HEIGHT = 480, 480
VIRTUAL_WIDTH, VIRTUAL_HEIGHT = 240, 240
FONT_SIZE = 24 

# --- HARDWARE SETUP ---
# Only use rpi driver if the framebuffer device exists
if os.path.exists('/dev/fb1'):
    os.environ['SDL_VIDEODRIVER'] = 'rpi'
    os.environ.setdefault('SDL_FBDEV', '/dev/fb1')

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

class EmulationStationStopper:
    """
    Context manager to stop EmulationStation while the app runs.
    Since we reboot on exit, we don't need to restart ES.
    """
    def __enter__(self):
        """Stop EmulationStation if it's running."""
        import time
        
        try:
            # Check if EmulationStation is running (the actual binary, not wrappers)
            result = subprocess.run(
                ['pgrep', '-x', 'emulationstatio'],  # pgrep truncates to 15 chars
                capture_output=True,
                timeout=2
            )
            
            if result.returncode == 0:
                logging.info('EmulationStation is running, stopping it...')
                
                # Remove the restart flag file to ensure the wrapper script exits
                try:
                    os.remove('/tmp/es-restart')
                except FileNotFoundError:
                    pass
                
                # Kill the ES binary
                subprocess.run(
                    ['pkill', '-9', '-x', 'emulationstatio'],  # Exact match, truncated name
                    capture_output=True,
                    timeout=5
                )
                logging.info('Killed EmulationStation binary')
                
                # Wait for the wrapper scripts to exit naturally
                time.sleep(1.0)
                
                # Check if everything exited
                result = subprocess.run(
                    ['pgrep', '-f', 'emulationstation'],
                    capture_output=True,
                    timeout=2
                )
                if result.returncode == 0:
                    # Wrappers didn't exit, force kill everything
                    logging.warning('Wrapper scripts still running, force killing...')
                    subprocess.run(['pkill', '-9', '-f', 'emulationstation'], capture_output=True, timeout=5)
                    time.sleep(0.5)
                else:
                    logging.info('EmulationStation and wrappers exited cleanly')
            else:
                logging.info('EmulationStation is not running')
                
        except subprocess.TimeoutExpired:
            logging.warning('Timeout while checking/stopping EmulationStation')
        except Exception as e:
            logging.warning(f'Could not stop EmulationStation: {e}')
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """No-op since we reboot on exit."""
        pass

class App:
    def __init__(self):
        # Pygame Setup
        pygame.init()
        pygame.joystick.init()
        
        # Display Setup
        # Check if running on Pi or Desktop for display mode
        if os.environ.get('SDL_VIDEODRIVER') == 'rpi':
             self.screen = pygame.display.set_mode((PHYSICAL_WIDTH, PHYSICAL_HEIGHT), pygame.FULLSCREEN)
        else:
             self.screen = pygame.display.set_mode((PHYSICAL_WIDTH, PHYSICAL_HEIGHT))
        
        # Hide mouse cursor (not needed for controller-based UI)
        pygame.mouse.set_visible(False)

             
        self.canvas = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        
        try:
            self.font = pygame.font.Font(None, FONT_SIZE)
        except:
            self.font = pygame.font.SysFont("sans", FONT_SIZE)

        self.clock = pygame.time.Clock()
        self.running = True

        # Store Components Setup
        self.config = load_config()
        # API client for catalog/game details (worker)
        self.api_client = HttpClient(self.config.api_base_url, self.config.http_timeout, self.config.max_retries)
        # CDN client for downloads
        self.cdn_client = HttpClient(self.config.cdn_base_url, self.config.http_timeout, self.config.max_retries)
        self.cdn_api = CdnApi(self.api_client, self.cdn_client)
        self.repo = Repository(self.config)
        self.installer = Installer(self.cdn_api, self.repo)
        self.updater = Updater(self.repo, self.cdn_api)
        self.parental_controls = ParentalControls(self.config.data_dir)
        
        self.input_manager = InputManager()
        
        # Screens
        self.screens = {
            "MainMenu": MainMenu(self),
            "CatalogList": CatalogList(self),
            "GameDetail": GameDetail(self),
            "DownloadScreen": DownloadScreen(self),
            "InstalledList": InstalledList(self),
            "UpdateCheck": UpdateCheck(self),
            "ParentalControls": ParentalControlsScreen(self),
            "DeveloperCode": DeveloperCodeScreen(self),
            "RebootScreen": RebootScreen(self),
            "FilterScreen": FilterScreen(self)
        }
        self.current_screen_name = "MainMenu"
        self.screen_stack = [] # For simple back navigation if needed, though screens handle it mostly
        
        self.screens["MainMenu"].on_enter()

    @property
    def current_screen(self):
        return self.screens[self.current_screen_name]

    def change_screen(self, screen_name):
        if screen_name in self.screens:
            self.current_screen_name = screen_name
            self.current_screen.on_enter()
        else:
            logging.error(f"Screen {screen_name} not found")

    def show_game_detail(self, game_id):
        self.screen_stack.append(self.current_screen_name)
        self.current_screen_name = "GameDetail"
        self.screens["GameDetail"].set_game(game_id)

    def start_download(self, manifest):
        self.screen_stack.append(self.current_screen_name)
        self.current_screen_name = "DownloadScreen"
        self.screens["DownloadScreen"].start_download(manifest)

    def go_back(self):
        if self.screen_stack:
            prev = self.screen_stack.pop()
            self.change_screen(prev)
        else:
            self.change_screen("MainMenu")

    def run(self):
        logging.info('Starting Game Bird Store Client...')
        
        try:
            # Stop EmulationStation while we run
            with EmulationStationStopper():
                logging.info('Entering main loop...')
                frame_count = 0
                
                while self.running:
                    # 1. Input
                    actions = self.input_manager.get_events()
                    if "QUIT" in actions:
                        # QUIT signal (Ctrl+C, etc) - go to reboot screen
                        logging.info('Quit action received, going to reboot screen')
                        self.change_screen("RebootScreen")
                    
                    # 2. Update
                    self.current_screen.update(actions)
                    
                    # 3. Draw
                    self.current_screen.draw(self.canvas)
                    
                    # 4. Upscale and Flip
                    scaled_surface = pygame.transform.scale(self.canvas, (PHYSICAL_WIDTH, PHYSICAL_HEIGHT))
                    self.screen.blit(scaled_surface, (0, 0))
                    pygame.display.flip()
                    
                    self.clock.tick(30)
                    
                    frame_count += 1
                    if frame_count == 1:
                        logging.info('First frame rendered successfully')
                
                logging.info(f'Exited main loop after {frame_count} frames')
        
        except Exception as e:
            logging.error(f'Error in main loop: {e}', exc_info=True)
            # On error, try to reboot to ensure clean state
            pygame.quit()
            subprocess.run(['sudo', 'reboot'], check=False)

if __name__ == "__main__":
    app = App()
    app.run()