from autonomia.gui import Display
import pygame
import math
import time


def lerp(x, y, a):
    return x * (1 - a) + y * a


def main():
    gui = Display()

    x1 = 0
    y1 = 0

    x2 = gui.w
    y2 = gui.h

    def draw_line(s, color, points, width):
        points = [(int(x), int(y)) for (x, y) in points]
        pygame.draw.lines(s, color, False, points, width)

    start = time.time()

    lanes = 7
    inv_lanes = 1 / lanes

    lane_y = [0 for lane in range(lanes)]

    bg_color = (0, 0, 0)
    fg_color = (255, 255, 0, 255)

    while True:
        keys = gui.pump_events()
        t = time.time() - start

        gui.clear(bg_color)

        bpm = 120
        dist = 1.5

        stamp_w = gui.w * inv_lanes
        stamp_h = gui.h

        stamp = pygame.Surface((stamp_w, stamp_h), flags=pygame.SRCALPHA)

        line_count = 11
        line_space = gui.h / line_count
        line_width = math.ceil(line_space / 2)

        if True:
            stamp_left = stamp_w * -1
            stamp_right = stamp_w * 2
            stamp_top = stamp_h - stamp_w * 2 * (gui.h / gui.w)
            stamp_bottom = stamp_h

            draw_line(
                stamp, fg_color,
                [(lerp(stamp_left, stamp_right, 0), stamp_top),
                 (lerp(stamp_left, stamp_right, .5), stamp_bottom),
                 (lerp(stamp_left, stamp_right, 1), stamp_top)],
                width = line_width)

        for lane in range(lanes):
            lane_a = lane / (lanes - 1)
            lane_a = abs(lane_a * 2 - 1)
            lane_a = lane_a * lane_a
            lane_push = lerp(.04, 0, lane_a)
            #print(lane_bpm)

            a = abs(math.sin((t + lane_push) * 2 * math.pi * (60 / bpm))) * dist
            a = a*a*a
            y = lane_y[lane] = (lane_y[lane] + a) % gui.h

            for line in range(line_count * -2, line_count):
                blit_x = math.floor(x2 * inv_lanes) * lane
                blit_y = int(line * line_space) + y
                gui.screen.blit(stamp, (blit_x, blit_y))

        gui.present()


if __name__ == "__main__":
    main()
