from autonomia.gui import Display
import pygame
import math
import time


def main():
    gui = Display()

    x1 = 0
    y1 = 0

    x2 = gui.w
    y2 = gui.h

    def draw_line(color, points, width):
        pygame.draw.lines(gui.screen, color, False, points, width)

    def flow_y(color, points, width):
        points = [(int(x), int(y)) for (x, y) in points]
        draw_line(color, points, width)

    start = time.time()

    i = 0
    while True:
        keys = gui.pump_events()
        gui.clear((0, 0, 0))

        lanes = 7
        inv_lanes = 1 / lanes

        t = time.time() - start
        t = abs(math.sin(t * 2 * math.pi * (60 / 120))) * 1.5
        t = t*t*t

        i = (i + t) % gui.h

        c = 5
        s = gui.h / c
        w = math.ceil(s / 2)

        for n in range(-c * 2, c):
            y = int(n * s)

            flow_y(
                (255, 255, 0),
                [(x1, y1 + i + y),
                 (x2 * .5, y2 + i + y),
                 (x2, y1 + i + y)],
                width = w)

        r = pygame.Rect(((x2 - x2 * inv_lanes) * .5, y1), (gui.w * inv_lanes, gui.h))

        subsurf = gui.screen.subsurface(r).copy()
        for lane in range(lanes):
            gui.screen.blit(subsurf, (x2 * inv_lanes * lane, y1))

        gui.present()


if __name__ == "__main__":
    main()
