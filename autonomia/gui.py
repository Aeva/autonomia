

import time
import math
import sys
import os
from importlib import resources
import pygame
import pygame.font
import pygame.sysfont
import pygame.display
import media
from misc import lerp
import metronome


class Display:
    def __init__(self):
        # Correct support of HiDPI on Linux requires setting both of these environment variables as well
        # as passing the desired unscaled resolution to `pygame.display.set_mode` via the `size` parameter.
        os.environ["SDL_VIDEODRIVER"] = "wayland,x11"
        os.environ["SDL_VIDEO_SCALE_METHOD"] = "letterbox"

        pygame.init()
        pygame.font.init()
        pygame.display.init()

        self.session = None

        font_name = None

        self.default_fonts = {
            "tiny" : pygame.sysfont.SysFont(font_name, 32),    # M-height is 16 px?
            "smol" : pygame.sysfont.SysFont(font_name, 64),    # M-height is 32 px?
            "regular" : pygame.sysfont.SysFont(font_name, 96), # M-height is 48 px?
            "big" : pygame.sysfont.SysFont(font_name, 200),    # M-height is 100 px?
            "bigger" : pygame.sysfont.SysFont(font_name, 400), # M-height is 200 px?
        }

        def m_height(font):
            """
            Returns the M-height of the font, hopefully in pixels.
            """
            min_x, max_x, min_y, max_y, advance = font.metrics("M")[0]
            return max_y - min_y

        def m_descent(font):
            """
            Returns the descent below the baseline for the glyph M, hopefully in pixels.
            """
            min_x, max_x, min_y, max_y, advance = font.metrics("M")[0]
            return min_y

        def m_ascent(font):
            """
            Returns the ascent above the baseline for the glyph M, hopefully in pixels.
            """
            min_x, max_x, min_y, max_y, advance = font.metrics("M")[0]
            return max_y

        font_path = resources.files(media) / "afacad" / "static" / "Afacad-Bold.ttf"

        def match_size(name):
            """
            This function takes a named invocation of pygame.sysfont.SysFont, and attempts to
            find a size that will give a compatible M height.

            Acconding to the pygame docs, the size parameter in the font constructor is meant
            to be the desired pixel size.  This, however, appears to be a lie.  As the actual
            units seem to be completely arbitrary and change wildly from font to font, we take
            a numeric approach here to force it back into the realm of logic and reason.
            """
            counterpart = self.default_fonts[name]
            target_size = m_height(counterpart)
            guess = 100
            font = None
            for i in range(500):
                font = pygame.font.Font(font_path, int(guess))
                size = m_height(font)
                if size == target_size:
                    return font
                else:
                    guess *= target_size / size
            return font

        self.fonts = {}
        if True:
            for name in self.default_fonts.keys():
                self.fonts[name] = match_size(name)
        else:
            self.fonts = self.default_fonts

        self.font_offsets = {}
        for name, font in self.fonts.items():
            counterpart = self.default_fonts[name]

            target_margin = (
                counterpart.get_ascent() - m_ascent(counterpart),
                counterpart.get_descent() - m_descent(counterpart))

            font_margin = (
                font.get_ascent() - m_ascent(counterpart),
                font.get_descent() - m_descent(counterpart))

            self.font_offsets[name] = (
                int(target_margin[0] - font_margin[0]),
                -int(target_margin[1] - font_margin[1]))

        self.screen = pygame.display.set_mode(
            size = pygame.display.list_modes()[0],
            flags = pygame.FULLSCREEN,
            vsync = True)

        pygame.display.set_caption("autonomia")

        self.w = self.screen.get_width()
        self.h = self.screen.get_height()
        self.w_over_100 = self.w / 100

        pygame.mouse.set_visible(False)

        print(f"using video driver: {pygame.display.get_driver()}")

    def request_shutdown(self):
        if self.session:
            self.session.save_to_disk(abort = True)
        pygame.display.quit()
        pygame.quit()
        metronome.stop()
        sys.exit(0)

    def pump_events(self):
        keys = []
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.request_shutdown()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.request_shutdown()
                else:
                    keys.append(event.key)
        return keys

    def present(self):
        pygame.display.flip()

    def clear(self, color):
        self.screen.fill(color)

    def draw_text(self, msg, x, y, color=(255, 255, 255), font="regular", x_align=0, y_align=0):
        surface = self.fonts[font].render(str(msg), True, color)
        if x is None:
            x = (self.w - surface.get_width()) * .5
        elif x_align > 0:
            x -= surface.get_width() * x_align
        if y is None:
            y = (self.h - surface.get_height()) * .5
        elif y_align > 0:
            y -= surface.get_height() * y_align

        if self.font_offsets:
            top, bottom = self.font_offsets.get(font)
            y += lerp(top, -bottom, y_align)

        self.screen.blit(surface, (x, y))

    def draw_x_label(self, msg, x, y, color=(255, 255, 255), font="smol", y_align=0):
        self.draw_text(msg, x, y, color, font, x_align = .5, y_align = y_align)

    def draw_y_label(self, msg, x, y, color=(255, 255, 255), font="smol", x_align=1):
        self.draw_text(msg, x, y, color, font, x_align = x_align, y_align = .5)

    def draw_stat(self, label, value, col, row,
                  value_color=(255, 255, 255),
                  label_color=(255, 255, 255),
                  wiggle=False):
        cols = [200, 900, 1600]
        rows = [200, 600]
        label_x = cols[col]
        label_y = rows[row]
        value_x = cols[col]
        value_y = rows[row] + 96

        if wiggle:
            value_y += math.sin(time.time() * math.pi * 10) * 5

        self.draw_text(label, label_x, label_y, label_color, "regular")
        self.draw_text(value, value_x, value_y, value_color, "bigger")
