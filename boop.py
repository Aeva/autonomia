import pygame
import time
import math
import datetime
import json
import os
import sys
import array
import random
import math


def poll_events(wait_type = None, wait_key = None):
    waiting = True
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            sys.exit(0)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            sys.exit(0)
        elif event.type == wait_type and event.key == wait_key:
            waiting = False
    return waiting


def lerp(x, y, alpha):
    return (1.0 - alpha) * x + y * alpha


def sign(x):
    if x >= 0:
        return 1
    else:
        return -1


def sin_hz(seconds, frequency):
    return math.sin(seconds * (math.pi * .5) * frequency)


def fract(x):
    return x - math.floor(x)


def saw_hz(seconds, frequency):
    return (1.0 - fract(seconds * frequency * .25)) * 2.0 - 1.0


def sqr_hz(seconds, frequency):
    return sign(sin_hz(seconds, frequency))


def midi_hz(note):
    return (440 / 32) * (2 ** ((note - 9) / 12))


if __name__ == "__main__":
    pygame.init()
    pygame.font.init()
    pygame.mixer.init(frequency=44100)

    #screen = pygame.display.set_mode((900, 900))
    screen = pygame.display.set_mode(flags = pygame.FULLSCREEN | pygame.NOFRAME)
    width = screen.get_width()
    height = screen.get_height();

    y_slices = 7
    y_slice_span = height / y_slices


    samples_per_second = 44100
    length = 60 * 3
    total_samples = samples_per_second * length
    samples_per_slice = (total_samples // y_slices) // 40

    with open("2024_04_12_rowing_log.json", "r") as log_file:
        log = json.loads(log_file.read())
    raw_bpms = []
    rolling_bpms = []
    for row in log["log"]:
        phase, dt, raw_bpm, cadence, watts, dist, target_cadence, target_watts, rolling_bpm = row
        raw_bpms.append(raw_bpm)
        rolling_bpms.append(rolling_bpm)

    buf = array.array('B')
    def record(sample):
        sample = int((min(max(sample * .5, -1), 1) * .5 + .5) * 255)
        buf.append(sample)

    points = [list() for s in range(y_slices)]

    for i in range(total_samples):
        t = (i / samples_per_second)
        #a = t / length
        a = t/length

        note = int(rolling_bpms[int(a * (len(rolling_bpms) - 1))] / 110 * 69) # 60 is middle c
        hz = int(rolling_bpms[int(a * (len(rolling_bpms) - 1))] / 110 * 220)

        sample = 0
        sample = sin_hz(t, hz) * .75
        sample += sqr_hz(t, midi_hz(note))

        #sample = sin_hz(t, 440)
        #sample = sin_hz(t, lerp(440, 220, t / length))
        #sample = sqr_hz(t, 440)
        #sample = lerp(saw_hz(t, 440), sqr_hz(t, 440), a)
        #sample = sqr_hz(t, lerp(440, 220, math.sin(t)))

        record(sample * .5)

        y_slice = i // samples_per_slice

        x = ((i % samples_per_slice) / samples_per_slice) * width
        y = y_slice_span * y_slice + y_slice_span * .5 + y_slice_span * .275 * sample

        if y_slice < y_slices:
            points[y_slice].append((x, y))

    with open("fnord.raw", "wb") as sound_file:
        sound_file.write(buf)


    fnord = pygame.mixer.Sound(buf)
    fnord.set_volume(.05)
    fnord.play()

    screen.fill("gray")
    for y in range(y_slices):
        pygame.draw.lines(screen, "black", False, points[y], 2)
    pygame.display.flip()

    while poll_events():
        time.sleep(.1)

