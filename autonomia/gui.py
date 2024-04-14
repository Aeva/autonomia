

import pygame
import time
import math
import sys


class Display:
    def __init__(self):
        pygame.init()
        pygame.font.init()

        font_name = "don't care"

        self.fonts = {
            "smol" : pygame.font.SysFont(font_name, 64),
            "regular" : pygame.font.SysFont(font_name, 96),
            "big" : pygame.font.SysFont(font_name, 200),
            "bigger" : pygame.font.SysFont(font_name, 400),
        }

        self.screen = pygame.display.set_mode(flags = pygame.FULLSCREEN | pygame.NOFRAME)
        self.w = self.screen.get_width()
        self.h = self.screen.get_height()
        self.w_over_100 = self.w / 100

        pygame.mouse.set_visible(False)


    def pump_events(self):
        keys = []
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit(0)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    sys.exit(0)
                else:
                    keys.append(event.key)
        return keys


    def present(self):
        pygame.display.flip()


    def clear(self, color):
        self.screen.fill(color)

    def draw_text(self, msg, x, y, color=(255, 255, 255), font="regular"):
        surface = self.fonts[font].render(str(msg), True, color)
        if x is None:
            x = (self.w - surface.get_width()) * .5
        if y is None:
            y = (self.h - surface.get_height()) * .5
        self.screen.blit(surface, (x, y))


    def draw_stat(self, label, value, col, row, value_color=(255, 255, 255), label_color=(255, 255, 255)):
        cols = [200, 900, 1600]
        rows = [200, 600]
        label_x = cols[col]
        label_y = rows[row]
        value_x = cols[col]
        value_y = rows[row] + 96
        self.draw_text(label, label_x, label_y, label_color, "regular")
        self.draw_text(value, value_x, value_y, value_color, "bigger")
