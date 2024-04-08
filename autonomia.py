
# todo: install PyRow properly somewhere
import os, sys
sys.path.append(os.path.join(os.getcwd(), "PyRow"))
from PyRow import pyrow

import pygame
import time


"""
nix-shell -p python311Packages.pyusb python311Packages.pygame
"""

"""
example output:
CSAFE_GETCADENCE_CMD : [17, 84]
CSAFE_GETHRCUR_CMD : [127]
CSAFE_GETPOWER_CMD : [8, 88]
CSAFE_GETSTATUS_CMD : [137]
CSAFE_PM_GET_STROKESTATE : [2]
CSAFE_PM_GET_WORKDISTANCE : [750, 9]
CSAFE_PM_GET_WORKTIME : [5000, 27]
-------------
CSAFE_GETCADENCE_CMD : [17, 84]
CSAFE_GETHRCUR_CMD : [126]
CSAFE_GETPOWER_CMD : [8, 88]
CSAFE_GETSTATUS_CMD : [137]
CSAFE_PM_GET_STROKESTATE : [2]
CSAFE_PM_GET_WORKDISTANCE : [760, 0]
CSAFE_PM_GET_WORKTIME : [5000, 37]
"""


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


def zero_pad(num, digits = 2):
    s = str(num)
    n = max(digits - len(s), 0)
    return ("0" * n) + s


if __name__ == '__main__':
    pygame.init()
    pygame.font.init()
    font = pygame.font.SysFont("don't care", 96)
    big_font = pygame.font.SysFont("don't care", 200)
    bigger_font = pygame.font.SysFont("don't care", 400)
    screen = pygame.display.set_mode(flags = pygame.FULLSCREEN | pygame.NOFRAME)

    screen_width = screen.get_width()
    screen_height = screen.get_height();
    segment_w = screen_width / 100

    erg = None
    print("Searching for erg...")
    while erg is None:
        poll_events()
        for available_erg in pyrow.find():
            erg = pyrow.pyrow(available_erg)
            break
        if not erg:
            screen.fill("gray")
            text_surface = font.render('Searching for erg...', True, (255, 255, 255))
            screen.blit(text_surface, (0, 0))
            pygame.display.flip()
            time.sleep(.5)

    print("erg found!")

    while poll_events(pygame.KEYDOWN, pygame.K_SPACE):
        query = ["CSAFE_GETHRCUR_CMD"]
        current_bpm = erg.send(query)["CSAFE_GETHRCUR_CMD"][0]

        screen.fill((64, 0, 128))
        text_surface = font.render("Press space to start resting BPM calibration", True, (255, 255, 255))
        screen.blit(text_surface, (0, 0))

        text_surface = font.render("Current BPM:", True, (255, 255, 255))
        screen.blit(text_surface, (200, 200))

        text_surface = bigger_font.render(f"{current_bpm}", True, (255, 255, 255))
        screen.blit(text_surface, (200, 296))

        pygame.display.flip()
        time.sleep(.1)

    calibration = []
    resting_bpm_average = 0
    resting_bpm_deviation = 0
    resting_bpm_mode = 0
    calibration_start_time = time.time()

    resting_bpm = 0

    while poll_events(pygame.KEYDOWN, pygame.K_SPACE):
        query = ["CSAFE_GETHRCUR_CMD"]
        current_bpm = erg.send(query)["CSAFE_GETHRCUR_CMD"][0]
        calibration.append(current_bpm)
        calibration = calibration[-101:]

        resting_bpm_average = sum(calibration) // len(calibration)
        resting_bpm_mode = max(set(calibration), key=calibration.count)

        resting_bpm_deviation = 0
        for sample in calibration:
            resting_bpm_deviation += abs(resting_bpm_average - sample)
        resting_bpm_deviation /= len(calibration)

        resting_bpm = resting_bpm_average

        elapsed_seconds = int(time.time() - calibration_start_time)
        elapsed_minutes = zero_pad(elapsed_seconds // 60)
        elapsed_seconds = zero_pad(elapsed_seconds % 60)
        elapsed_time = f"{elapsed_minutes}:{elapsed_seconds}"

        screen.fill((64, 0, 128))

        if len(calibration) > 1:
            graph_min = current_bpm
            graph_max = current_bpm

            for sample in calibration:
                graph_min = min(graph_min, sample)
                graph_max = max(graph_max, sample)

            graph_span = max(graph_max - graph_min, 1)
            graph_scale = (screen_height * .25)
            graph_points = []
            histogram = []

            x_anchor = screen_width - (len(calibration) - 1) * segment_w
            y_anchor = screen_height - graph_scale - 20

            def plot(index, sample):
                graph_a = (sample - graph_min) / graph_span
                graph_x = x_anchor + index * segment_w
                graph_y = y_anchor + graph_scale * (1.0 - graph_a)
                return (graph_x, graph_y)

            for index, sample in enumerate(calibration):
                graph_points.append(plot(index, sample))

            x_anchor = 0

            for index, sample in enumerate(sorted(calibration)[::-1]):
                histogram.append(plot(index, sample))

            pygame.draw.lines(screen, "black", False, histogram, 8)

            if resting_bpm_average == resting_bpm_mode:
                pygame.draw.lines(screen, "magenta", False, [plot(0, resting_bpm_mode), plot(101, resting_bpm_mode)], 8)
            else:
                pygame.draw.lines(screen, "pink", False, [plot(0, resting_bpm_mode), plot(101, resting_bpm_mode)], 8)
                pygame.draw.lines(screen, "blue", False, [plot(0, resting_bpm_average), plot(101, resting_bpm_average)], 8)
            pygame.draw.lines(screen, "white", False, graph_points, 8)


        text_surface = font.render("Current BPM:", True, (255, 255, 255))
        screen.blit(text_surface, (200, 200))
        text_surface = bigger_font.render(f"{current_bpm}", True, (255, 255, 255))
        screen.blit(text_surface, (200, 296))

        text_surface = font.render("Elapsed Time:", True, (255, 255, 255))
        screen.blit(text_surface, (900, 200))
        text_surface = bigger_font.render(f"{elapsed_time}", True, (255, 255, 255))
        screen.blit(text_surface, (900, 296))

        text_surface = font.render("Average:", True, (255, 255, 255))
        screen.blit(text_surface, (200, 600))
        text_surface = bigger_font.render(f"{resting_bpm_average}", True, (255, 255, 255))
        screen.blit(text_surface, (200, 696))

        text_surface = font.render("Mode:", True, (255, 255, 255))
        screen.blit(text_surface, (900, 600))
        text_surface = bigger_font.render(f"{resting_bpm_mode}", True, (255, 255, 255))
        screen.blit(text_surface, (900, 696))

        text_surface = font.render("Deviation:", True, (255, 255, 255))
        screen.blit(text_surface, (1600, 600))
        text_surface = bigger_font.render(f"{resting_bpm_deviation:.2f}", True, (255, 255, 255))
        screen.blit(text_surface, (1600, 696))

        text_surface = font.render("Press space to stop calibration", True, (255, 255, 255))
        screen.blit(text_surface, (650, 1200))

        pygame.display.flip()
        time.sleep(1)

    workout = erg.get_workout()
    while workout['state'] == 0:
        poll_events()
        time.sleep(1)
        workout = erg.get_workout()

    while workout['state'] == 1:
        poll_events()
        workout = erg.get_workout()

        query = [
            "CSAFE_PM_GET_WORKTIME",
            "CSAFE_PM_GET_WORKDISTANCE",
            "CSAFE_GETCADENCE_CMD",
            "CSAFE_GETPOWER_CMD",
            "CSAFE_GETHRCUR_CMD",
            "CSAFE_PM_GET_STROKESTATE"]

        reply = erg.send(query)
        for key in sorted(reply.keys()):
            value = reply[key]
            print(f"{key} : {value}")

        print("-------------")
