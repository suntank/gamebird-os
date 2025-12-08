import pygame
from pygame.locals import *

# Button Mappings (GameHat / SNES Style)
BTN_A      = 0
BTN_B      = 1
BTN_X      = 5
BTN_Y      = 3
BTN_L      = 4
BTN_R      = 2
BTN_SELECT = 6
BTN_START  = 7

class InputManager:
    def __init__(self):
        if pygame.joystick.get_count() > 0:
            self.joy = pygame.joystick.Joystick(0)
            self.joy.init()
        else:
            self.joy = None

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
                elif event.button == BTN_X:
                    actions.append("X")
                elif event.button == BTN_Y:
                    actions.append("Y")
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
                if dy == 1: actions.append("UP")
                elif dy == -1: actions.append("DOWN")
                elif dx == -1: actions.append("LEFT")
                elif dx == 1: actions.append("RIGHT")
                
            elif event.type == JOYAXISMOTION:
                if event.axis == 1: # Vertical
                    if event.value < -0.5: actions.append("UP")
                    elif event.value > 0.5: actions.append("DOWN")
                elif event.axis == 0: # Horizontal
                    if event.value < -0.5: actions.append("LEFT")
                    elif event.value > 0.5: actions.append("RIGHT")
                    
            elif event.type == KEYDOWN:
                # Fallback for keyboard testing
                if event.key == K_UP: actions.append("UP")
                elif event.key == K_DOWN: actions.append("DOWN")
                elif event.key == K_LEFT: actions.append("LEFT")
                elif event.key == K_RIGHT: actions.append("RIGHT")
                elif event.key == K_w: actions.append("A")
                elif event.key == K_a: actions.append("B")
                elif event.key == K_s: actions.append("X")
                elif event.key == K_d: actions.append("Y")
                elif event.key == K_RETURN: actions.append("START")
                elif event.key == K_RSHIFT or event.key == K_LSHIFT: actions.append("SELECT")
                elif event.key == K_q: actions.append("L")
                elif event.key == K_e: actions.append("R")
                elif event.key == K_ESCAPE: actions.append("QUIT")

        return actions
