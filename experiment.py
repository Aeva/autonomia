import pygame
import math
import time


def lerp(x, y, a):
    return x * (1 - a) + y * a


def pump_events():
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


def main():
    screen = pygame.display.set_mode(flags = pygame.FULLSCREEN | pygame.NOFRAME, vsync=True)
    gui_w = screen.get_width()
    gui_h = screen.get_height()

    x1 = 0
    y1 = 0

    x2 = gui_w
    y2 = gui_h

    def draw_line(s, color, points, width):
        points = [(int(x), int(y)) for (x, y) in points]
        pygame.draw.lines(s, color, False, points, width)

    lanes = 7
    line_count = 11

    pages = 2

    bpm = 120
    dist = 1.5

    fg_color_1 = (255, 255, 0, 255)
    fg_color_2 = (128, 0, 192, 255)

    bg_color_1 = (0, 0, 0, 255)
    bg_color_2 = (128, 0, 0, 255)

    mask_color = (255, 255, 255, 255)
    erase_color = (0, 0, 0, 0)

    inv_lanes = 1 / lanes
    stamp_w = gui_w * inv_lanes
    stamp_h = gui_h

    line_space = gui_h / line_count
    line_width = math.ceil(line_space / 2)
    erase_width = line_width // 8

    stamp = pygame.Surface((stamp_w, stamp_h), flags=pygame.SRCALPHA)

    stamp_left = stamp_w * -1
    stamp_right = stamp_w * 2
    stamp_top = stamp_h - stamp_w * 2 * (gui_h / gui_w)
    stamp_bottom = stamp_h

    draw_line(
        stamp, mask_color,
        [(lerp(stamp_left, stamp_right, 0), stamp_top),
            (lerp(stamp_left, stamp_right, .5), stamp_bottom),
            (lerp(stamp_left, stamp_right, 1), stamp_top)],
        width = line_width)

    draw_line(
        stamp, erase_color,
        [(0, stamp_top),
            (0, stamp_bottom)],
        width=erase_width)

    draw_line(
        stamp, erase_color,
        [(stamp_w, stamp_top),
            (stamp_w, stamp_bottom)],
        width=erase_width)

    reel_w = stamp_w
    reel_h = gui_h * pages
    reel = pygame.Surface((reel_w, reel_h), flags=pygame.SRCALPHA)

    if True:
        for line in range(line_count * (pages + 1)):
            blit_x = 0
            blit_y = gui_h + int(-line * line_space)
            reel.blit(stamp, (blit_x, blit_y))

    start = time.time()
    lane_y = [0 for lane in range(lanes)]

    mask = screen.copy()
    inv_mask = screen.copy()

    fg_surf = screen.copy()
    bg_surf = screen.copy()

    def fill_gradient(surface, color_a, color_b, count = 100):
        w = surface.get_width()
        h = surface.get_height()
        stride = math.ceil(h / (count))
        half_stride = stride * .5

        for index in range(count):
            alpha = index / (count - 1)
            y = lerp(half_stride, h - half_stride, alpha)
            color = tuple([lerp(color_a[c], color_b[c], alpha) for c in range(4)])
            draw_line(
                surface, color,
                [(0, y),
                (w, y)],
                width=math.ceil(stride) + 1)

    #fg_surf.fill(fg_color_1)
    fill_gradient(fg_surf, fg_color_1, fg_color_2)

    #bg_surf.fill(bg_color)
    fill_gradient(bg_surf, bg_color_1, bg_color_2)

    while True:
        keys = pump_events()
        t = time.time() - start

        blit_seq = []

        for lane in range(lanes):
            lane_a = lane / (lanes - 1)
            lane_a = abs(lane_a * 2 - 1)
            lane_a = lane_a * lane_a
            lane_push = lerp(.04, 0, lane_a)

            a = abs(math.sin((t + lane_push) * 2 * math.pi * (60 / bpm))) * dist
            a = a*a*a
            y = lane_y[lane] = (lane_y[lane] + a) % (gui_h * max((pages // 2 - 1), 1))

            blit_x = math.floor(x2 * inv_lanes) * lane
            blit_y = reel_h / -pages + y
            blit_seq.append((reel, (blit_x, blit_y), None, pygame.BLEND_RGBA_ADD))

        mask.fill((0, 0, 0, 0))
        mask.blits(blit_seq)

        inv_mask.fill((255, 255, 255, 255))
        inv_mask.blit(mask, (0, 0), None, pygame.BLEND_RGBA_SUB)

        mask.blit(fg_surf, (0, 0), None, pygame.BLEND_RGBA_MULT)
        inv_mask.blit(bg_surf, (0, 0), None, pygame.BLEND_RGBA_MULT)

        screen.blit(mask, (0, 0))
        screen.blit(inv_mask, (0, 0), None, pygame.BLEND_RGBA_ADD)

        pygame.display.flip()


if __name__ == "__main__":
    main()
