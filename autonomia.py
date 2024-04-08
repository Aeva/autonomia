
# todo: install PyRow properly somewhere
import os, sys
sys.path.append(os.path.join(os.getcwd(), "PyRow"))
from PyRow import pyrow

import pygame
import time
import math
import datetime

# An interval consists of an active BPM calibration phase,
# followed by steady state phase, followed by a cooldown phase
INTERVALS = 2

# time in minutes
CALIBRATION_TIME = 1
STEADY_TIME = 7
COOLDOWN_TIME = 0.5

TARGET_LOW = 10
TARGET_HIGH = 15


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

    logged_stats = []

    def record(phase, bpm, cadence = 0, watts = 0, distance = 0):
        row = (phase, time.time(), bpm, cadence, watts, distance)
        logged_stats.append(row)

    erg = None
    print("Searching for erg...")
    while erg is None:
        poll_events()
        for available_erg in pyrow.find():
            erg = pyrow.pyrow(available_erg)
            print("erg found!")
            break
        if not erg:
            screen.fill("gray")
            text_surface = font.render('Searching for erg...', True, (255, 255, 255))
            screen.blit(text_surface, (0, 0))
            pygame.display.flip()
            time.sleep(.5)

    erg.send(['CSAFE_RESET_CMD'])

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

        record(0, current_bpm)

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

        pygame.draw.lines(screen, "blue", False, [(200, 900), (700, 900)], 16)
        text_surface = font.render("Average:", True, (255, 255, 255))
        screen.blit(text_surface, (200, 600))
        text_surface = bigger_font.render(f"{resting_bpm_average}", True, (255, 255, 255))
        screen.blit(text_surface, (200, 696))

        pygame.draw.lines(screen, "pink", False, [(900, 900), (1400, 900)], 16)
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
        time.sleep(.25)
        if not poll_events(pygame.KEYDOWN, pygame.K_SPACE):
            break
        time.sleep(.25)
        if not poll_events(pygame.KEYDOWN, pygame.K_SPACE):
            break
        time.sleep(.25)
        if not poll_events(pygame.KEYDOWN, pygame.K_SPACE):
            break
        time.sleep(.25)

    screen.fill((96, 64, 128))
    pygame.display.flip()

    workout = erg.get_workout()
    while workout['state'] == 0 and poll_events(pygame.KEYDOWN, pygame.K_SPACE):
        poll_events()
        screen.fill((96, 96, 128))

        current_bpm = erg.send(query)["CSAFE_GETHRCUR_CMD"][0]
        record(1, current_bpm)

        text_surface = font.render("Current BPM:", True, (255, 255, 255))
        screen.blit(text_surface, (200, 200))
        text_surface = bigger_font.render(f"{current_bpm}", True, (255, 255, 255))
        screen.blit(text_surface, (200, 296))

        text_surface = font.render("Resting BPM:", True, (255, 255, 255))
        screen.blit(text_surface, (900, 200))
        text_surface = bigger_font.render(f"{resting_bpm}", True, (255, 255, 255))
        screen.blit(text_surface, (900, 296))

        text_surface = big_font.render("please begin", True, (255, 255, 255))
        screen.blit(text_surface, (700, screen_height * .5 - 100))
        pygame.display.flip()

        time.sleep(1)
        workout = erg.get_workout()

    target_bpm = (resting_bpm + TARGET_LOW, resting_bpm + TARGET_HIGH)
    target_cadence = 0
    target_watts = 0
    samples = 0
    distance = 0

    workout_start_time = time.time()

    for interval in range(INTERVALS):
        interval_start_time = time.time()

        calibration_stop_time = interval_start_time + CALIBRATION_TIME * 60

        while time.time() < calibration_stop_time and poll_events(pygame.KEYDOWN, pygame.K_BACKSPACE):
            query = [
                "CSAFE_PM_GET_WORKDISTANCE",
                "CSAFE_GETCADENCE_CMD",
                "CSAFE_GETPOWER_CMD",
                "CSAFE_GETHRCUR_CMD",
                "CSAFE_PM_GET_STROKESTATE"]
            reply = erg.send(query)

            distance = reply["CSAFE_PM_GET_WORKDISTANCE"][0] + reply["CSAFE_PM_GET_WORKDISTANCE"][1] / 10.0
            cadence = reply["CSAFE_GETCADENCE_CMD"][0]
            watts = reply["CSAFE_GETPOWER_CMD"][0]
            current_bpm = reply["CSAFE_GETHRCUR_CMD"][0]
            state = reply["CSAFE_PM_GET_STROKESTATE"]

            record(2, current_bpm, cadence, watts, distance)

            alpha = 1
            reading_color = (255, 255, 255)

            if current_bpm < target_bpm[0]:
                alpha = math.sin(time.time() * 5) * .5 + .5
                reading_color = (255, 255 * alpha, 255 * alpha)
                screen.fill((0, 128, 0))
                text_surface = bigger_font.render("increase speed", True, (alpha, alpha, alpha))
                screen.blit(text_surface, (100, 1200))
            elif current_bpm > target_bpm[1]:
                alpha = math.sin(time.time() * 5) * .5 + .5
                reading_color = (255 * alpha, 255 * alpha, 255)
                screen.fill((128, 0, 0))
                text_surface = bigger_font.render("decrease speed", True, (alpha, alpha, alpha))
                screen.blit(text_surface, (100, 1200))
            else:
                screen.fill((96, 64, 128))
                text_surface = big_font.render("perfect.  hold.", True, (255, 255, 255))
                screen.blit(text_surface, (100, 1200))
                target_cadence += cadence
                target_watts += watts
                samples += 1

            remaining_seconds = max(int(calibration_stop_time - time.time()), 0)
            remaining_minutes = zero_pad(remaining_seconds // 60)
            remaining_seconds = zero_pad(remaining_seconds % 60)
            remaining_time = f"{remaining_minutes}:{remaining_seconds}"

            text_surface = font.render(f"Remaining Calibration Time {remaining_time}", True, (255, 255, 255))
            screen.blit(text_surface, (0, 0))


            text_surface = font.render("Current Cadence:", True, (255, 255, 255))
            screen.blit(text_surface, (200, 200))
            text_surface = bigger_font.render(f"{cadence}", True, reading_color)
            screen.blit(text_surface, (200, 296))

            if samples > 0:
                text_surface = font.render("Target Cadence:", True, (255, 255, 255))
                screen.blit(text_surface, (900, 200))
                text_surface = bigger_font.render(f"{int(target_cadence / samples)}", True, (255, 255, 255))
                screen.blit(text_surface, (900, 296))

            text_surface = font.render("Current Watts:", True, (255, 255, 255))
            screen.blit(text_surface, (200, 600))
            text_surface = bigger_font.render(f"{watts}", True, reading_color)
            screen.blit(text_surface, (200, 696))

            if samples > 0:
                text_surface = font.render("Target Watts:", True, (255, 255, 255))
                screen.blit(text_surface, (900, 600))
                text_surface = bigger_font.render(f"{int(target_watts / samples)}", True, (255, 255, 255))
                screen.blit(text_surface, (900, 696))

            pygame.display.flip()
            time.sleep(.1)

        if samples > 0:
            target_cadence //= samples
            target_watts //= samples
        else:
            target_cadence = 15
            target_watts = 8
        samples = 1

        steady_stop_time = time.time() + STEADY_TIME * 60

        while time.time() < steady_stop_time and poll_events(pygame.KEYDOWN, pygame.K_BACKSPACE):
            query = [
                "CSAFE_PM_GET_WORKDISTANCE",
                "CSAFE_GETCADENCE_CMD",
                "CSAFE_GETPOWER_CMD",
                "CSAFE_GETHRCUR_CMD",
                "CSAFE_PM_GET_STROKESTATE"]
            reply = erg.send(query)

            distance = reply["CSAFE_PM_GET_WORKDISTANCE"][0] + reply["CSAFE_PM_GET_WORKDISTANCE"][1] / 10.0
            cadence = reply["CSAFE_GETCADENCE_CMD"][0]
            watts = reply["CSAFE_GETPOWER_CMD"][0]
            current_bpm = reply["CSAFE_GETHRCUR_CMD"][0]
            state = reply["CSAFE_PM_GET_STROKESTATE"]

            record(3, current_bpm, cadence, watts, distance)

            alpha = 1
            reading_color = (255, 255, 255)

            if cadence < target_cadence - 1 or watts < target_watts - 1:
                alpha = math.sin(time.time() * 5) * .5 + .5
                reading_color = (255, 255 * alpha, 255 * alpha)
                screen.fill((0, 128, 0))
                text_surface = bigger_font.render("increase speed", True, (alpha, alpha, alpha))
                screen.blit(text_surface, (100, 1200))
            elif cadence > target_cadence + 1 or watts > target_watts + 1:
                alpha = math.sin(time.time() * 5) * .5 + .5
                reading_color = (255 * alpha, 255 * alpha, 255)
                screen.fill((128, 0, 0))
                text_surface = bigger_font.render("decrease speed", True, (alpha, alpha, alpha))
                screen.blit(text_surface, (100, 1200))
            else:
                screen.fill((96, 64, 128))
                text_surface = big_font.render("perfect.  hold.", True, (255, 255, 255))
                screen.blit(text_surface, (100, 1200))

            remaining_seconds = max(int(steady_stop_time - time.time()), 0)
            remaining_minutes = zero_pad(remaining_seconds // 60)
            remaining_seconds = zero_pad(remaining_seconds % 60)
            remaining_time = f"{remaining_minutes}:{remaining_seconds}"

            text_surface = font.render(f"Remaining Time {remaining_time}", True, (255, 255, 255))
            screen.blit(text_surface, (0, 0))

            text_surface = font.render("Current Cadence:", True, (255, 255, 255))
            screen.blit(text_surface, (200, 200))
            text_surface = bigger_font.render(f"{cadence}", True, (255, 255, 255))
            screen.blit(text_surface, (200, 296))

            if samples > 0:
                text_surface = font.render("Target Cadence:", True, (255, 255, 255))
                screen.blit(text_surface, (900, 200))
                text_surface = bigger_font.render(f"{target_cadence}", True, (255, 255, 255))
                screen.blit(text_surface, (900, 296))

            text_surface = font.render("Current Watts:", True, (255, 255, 255))
            screen.blit(text_surface, (200, 600))
            text_surface = bigger_font.render(f"{watts}", True, (255, 255, 255))
            screen.blit(text_surface, (200, 696))

            if samples > 0:
                text_surface = font.render("Target Watts:", True, (255, 255, 255))
                screen.blit(text_surface, (900, 600))
                text_surface = bigger_font.render(f"{target_watts}", True, (255, 255, 255))
                screen.blit(text_surface, (900, 696))

            pygame.display.flip()
            time.sleep(.1)

        cooldown_stop_time = time.time() + COOLDOWN_TIME * 60

        while time.time() < cooldown_stop_time and poll_events(pygame.KEYDOWN, pygame.K_BACKSPACE):
            query = [
                "CSAFE_PM_GET_WORKDISTANCE",
                "CSAFE_GETCADENCE_CMD",
                "CSAFE_GETPOWER_CMD",
                "CSAFE_GETHRCUR_CMD",
                "CSAFE_PM_GET_STROKESTATE"]
            reply = erg.send(query)

            distance = reply["CSAFE_PM_GET_WORKDISTANCE"][0] + reply["CSAFE_PM_GET_WORKDISTANCE"][1] / 10.0
            cadence = reply["CSAFE_GETCADENCE_CMD"][0]
            watts = reply["CSAFE_GETPOWER_CMD"][0]
            current_bpm = reply["CSAFE_GETHRCUR_CMD"][0]
            state = reply["CSAFE_PM_GET_STROKESTATE"]

            record(4, current_bpm, cadence, watts, distance)

            screen.fill((96, 96, 128))

            remaining_seconds = max(int(cooldown_stop_time - time.time()), 0)
            remaining_minutes = zero_pad(remaining_seconds // 60)
            remaining_seconds = zero_pad(remaining_seconds % 60)
            remaining_time = f"{remaining_minutes}:{remaining_seconds}"

            text_surface = font.render(f"Cool Down {remaining_time}", True, (255, 255, 255))
            screen.blit(text_surface, (0, 0))

            pygame.display.flip()
            time.sleep(.1)


    screen.fill((96, 96, 96))

    min_t = logged_stats[0][1]
    max_t = logged_stats[-1][1]
    t_span = max_t - min_t

    bpm_line = []
    last_phase = 0

    for row in logged_stats:
        phase, t, bpm, cadence, watts, distance = row
        t_alpha = (t - min_t) / t_span
        x_plot = screen_width * t_alpha
        y_plot = screen_height * .5 - ((bpm - resting_bpm) * 20)
        bpm_line.append((x_plot, y_plot))
        if phase != last_phase:
            last_phase = phase
            phase_color = "gray"
            if phase == 2:
                phase_color = "blue"
            if phase == 3:
                phase_color = "green"
            if phase == 4:
                phase_color = "red"
            pygame.draw.lines(screen, phase_color, False, [(x_plot, 0), (x_plot, screen_height)], 2)

    pygame.draw.lines(screen, "blue", False, [(0, screen_height * .5), (screen_width, screen_height * .5)], 2)

    pygame.draw.lines(screen, "black", False,
                      [(0, screen_height * .5 - (TARGET_LOW * 20)),
                       (screen_width, screen_height * .5 - (TARGET_LOW * 20))], 2)

    pygame.draw.lines(screen, "black", False,
                      [(0, screen_height * .5 - (TARGET_HIGH * 20)),
                       (screen_width, screen_height * .5 - (TARGET_HIGH * 20))], 2)

    pygame.draw.lines(screen, "white", False, bpm_line, 1)


    pygame.display.flip()

    out_path_template = datetime.datetime.now().strftime("%Y_%m_%d_rowing_log{}.csv")
    out_path = out_path_template.format("")
    counter = 0
    while os.path.exists(out_path):
        counter += 1
        out_path = out_path_template.format(f"_{zero_pad(counter, 3)}")

    with open(out_path, "w") as out_file:
        out_file.write("time, phase, bpm, cadence, watts, meters\n")

        for row in logged_stats:
            phase, t, bpm, cadence, watts, distance = row
            t -= min_t
            out_file.write(f"{t}, {phase}, {bpm}, {cadence}, {watts}, {distance}\n")

    print("Workout complete!")

    while poll_events():
        poll_events()
        time.sleep(.1)

