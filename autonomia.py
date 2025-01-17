
# todo: install PyRow properly somewhere
import os, sys
sys.path.append(os.path.join(os.getcwd(), "PyRow"))
from PyRow import pyrow

import pygame
import time
import math
import datetime
import json

# An interval consists of an active BPM calibration phase,
# followed by steady state phase, followed by a cooldown phase
INTERVALS = 2

# time in minutes
CALIBRATION_TIME = 2
STEADY_TIME = 8
COOLDOWN_TIME = 1

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
    smol_font = pygame.font.SysFont("don't care", 64)
    font = pygame.font.SysFont("don't care", 96)
    big_font = pygame.font.SysFont("don't care", 200)
    bigger_font = pygame.font.SysFont("don't care", 400)
    screen = pygame.display.set_mode(flags = pygame.FULLSCREEN | pygame.NOFRAME)

    screen_width = screen.get_width()
    screen_height = screen.get_height();
    segment_w = screen_width / 100

    logged_stats = []

    program_start_time = time.time()

    log_headers = [
        "phase", "elapsed_time", "bpm", "cadence", "watts", "distance",
        "target cadence", "target watts", "bpm_rolling_average"]

    start_time_str = datetime.datetime.now().strftime("%I:%M %p")

    def get_weighted_bpm(index = -1):
        if len(logged_stats) > 0:
            return logged_stats[index][8]
        else:
            return 0

    def window(samples, seconds):
        if len(samples) <= 1:
            return samples
        seek_seq = samples[1:][::-1]
        last_t = samples[-1][1]
        seek = 1
        for sample in samples[::-1]:
            if last_t - sample[1] <= seconds:
                seek += 1
            else:
                break
        start = (seek + 1) * -1
        seq = samples[start:-1]
        return seq

    def log_window(seconds):
        return window(logged_stats, seconds)

    def weighted_average(rows, stat_index, exponent=0):
        if len(rows) < 1:
            return 0
        elif len(rows) == 1:
            return rows[1]
        elif exponent <= 0:
            return sum([bpm for t, bpm in rows]) / len(rows)
        else:
            acc_v = 0
            acc_w = 0
            samples = [(row[1], row[stat_index]) for row in rows]
            t1 = samples[0][0]
            tN = samples[-1][0]
            dt = tN - t1
            for t, stat in samples:
                a = (t - t1) / dt
                a_exp = a ** exponent
                acc_v += stat * a_exp
                acc_w += a_exp
            return acc_v / acc_w

    def record(phase, raw_bpm, cadence = 0, watts = 0, distance = 0, target_cadence = 0, target_watts = 0):
        elapsed_time = time.time() - program_start_time

        rolling_bpm = raw_bpm
        row = (phase, elapsed_time, raw_bpm, cadence, watts, distance,
               target_cadence, target_watts, rolling_bpm)

        window_seq = log_window(5)
        window_seq.append(row)
        if len(window_seq) > 1:
            stat_index = 2
            exponent = 2
            rolling_bpm = weighted_average(window_seq, stat_index, exponent)

            row = (phase, elapsed_time, raw_bpm, cadence, watts, distance,
                target_cadence, target_watts, rolling_bpm)
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

    last_valid_cadence = None
    def filter_cadence(cadence):
        global last_valid_cadence
        if cadence < 35:
            last_valid_cadence = cadence
            return cadence
        elif last_valid_cadence is not None:
            if cadence < last_valid_cadence * 1.1:
                last_valid_cadence = cadence
                return cadence
            else:
                return last_valid_cadence
        else:
            return 0

    assert(filter_cadence(200) == 0)
    last_valid_cadence = None

    assert(filter_cadence(10) == 10)
    assert(filter_cadence(200) == 10)
    last_valid_cadence = None

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

            distance = (reply["CSAFE_PM_GET_WORKDISTANCE"][0] + reply["CSAFE_PM_GET_WORKDISTANCE"][1]) / 10.0
            cadence = reply["CSAFE_GETCADENCE_CMD"][0]
            watts = reply["CSAFE_GETPOWER_CMD"][0]
            current_bpm = reply["CSAFE_GETHRCUR_CMD"][0]
            state = reply["CSAFE_PM_GET_STROKESTATE"]

            record(2, current_bpm, cadence, watts, distance, target_cadence, target_watts)

            # The PM5 will sometimes glitch out when rowing slowly and give you an impossibly
            # high cadence.  This filter should prevent it from disrupting the calibration step.
            cadence = filter_cadence(cadence)

            weighted_bpm = get_weighted_bpm()

            alpha = 1
            reading_color = (255, 255, 255)

            hold = False

            if weighted_bpm < target_bpm[0]:
                alpha = math.sin(time.time() * 5) * .5 + .5
                reading_color = (255, 255 * alpha, 255 * alpha)
                screen.fill((0, 128, 0))
                text_surface = bigger_font.render("increase speed", True, (alpha, alpha, alpha))
                screen.blit(text_surface, (100, 1200))

                # reset the calibration targets
                target_cadence = cadence
                target_watts = watts
                samples = 1

            elif weighted_bpm > target_bpm[1]:
                alpha = math.sin(time.time() * 5) * .5 + .5
                reading_color = (255 * alpha, 255 * alpha, 255)
                screen.fill((128, 0, 0))
                text_surface = bigger_font.render("decrease speed", True, (alpha, alpha, alpha))
                screen.blit(text_surface, (100, 1200))

                # reset the calibration targets
                target_cadence = cadence
                target_watts = watts
                samples = 1

            else:
                screen.fill((96, 64, 128))
                text_surface = big_font.render("perfect.  hold.", True, (255, 255, 255))
                screen.blit(text_surface, (100, 1200))
                target_cadence += cadence
                target_watts += watts
                samples += 1
                hold = True

            remaining_seconds = max(int(calibration_stop_time - time.time()), 0)
            remaining_minutes = zero_pad(remaining_seconds // 60)
            remaining_seconds = zero_pad(remaining_seconds % 60)
            remaining_time = f"{remaining_minutes}:{remaining_seconds}"

            text_surface = font.render(f"Remaining Calibration Time {remaining_time}", True, (255, 255, 255))
            screen.blit(text_surface, (0, 0))

            if False:
                # for debugging
                text_surface = font.render("Current BPM:", True, (255, 255, 255))
                screen.blit(text_surface, (1600, 200))
                text_surface = bigger_font.render(f"{current_bpm}", True, (255, 255, 255))
                screen.blit(text_surface, (1600, 296))

                text_surface = font.render("Target BPM (low):", True, (255, 255, 255))
                screen.blit(text_surface, (1600, 600))
                text_surface = bigger_font.render(f"{target_bpm[0]}", True, (255, 255, 255))
                screen.blit(text_surface, (1600, 696))

            text_surface = font.render("Current Cadence:", True, (255, 255, 255))
            screen.blit(text_surface, (200, 200))
            text_surface = bigger_font.render(f"{cadence}", True, reading_color)
            screen.blit(text_surface, (200, 296))

            if samples > 0 and hold:
                text_surface = font.render("Target Cadence:", True, (255, 255, 255))
                screen.blit(text_surface, (900, 200))
                text_surface = bigger_font.render(f"{int(target_cadence / samples)}", True, (255, 255, 255))
                screen.blit(text_surface, (900, 296))

            text_surface = font.render("Current Watts:", True, (255, 255, 255))
            screen.blit(text_surface, (200, 600))
            text_surface = bigger_font.render(f"{watts}", True, reading_color)
            screen.blit(text_surface, (200, 696))

            if samples > 0 and hold:
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

            distance = (reply["CSAFE_PM_GET_WORKDISTANCE"][0] + reply["CSAFE_PM_GET_WORKDISTANCE"][1]) / 10.0
            cadence = reply["CSAFE_GETCADENCE_CMD"][0]
            watts = reply["CSAFE_GETPOWER_CMD"][0]
            current_bpm = reply["CSAFE_GETHRCUR_CMD"][0]
            state = reply["CSAFE_PM_GET_STROKESTATE"]

            record(3, current_bpm, cadence, watts, distance, target_cadence, target_watts)

            # The PM5 will sometimes glitch out when rowing slowly and give you an impossibly
            # high cadence.  This filter should prevent it from disrupting the steady state phase.
            cadence = filter_cadence(cadence)

            alpha = 1
            reading_color = (255, 255, 255)

            if cadence > target_cadence + 1 or watts > target_watts + 1:
                alpha = math.sin(time.time() * 5) * .5 + .5
                reading_color = (255 * alpha, 255 * alpha, 255)
                screen.fill((128, 0, 0))
                text_surface = bigger_font.render("decrease speed", True, (alpha, alpha, alpha))
                screen.blit(text_surface, (100, 1200))
            elif cadence < target_cadence - 1 or watts < target_watts - 1:
                alpha = math.sin(time.time() * 5) * .5 + .5
                reading_color = (255, 255 * alpha, 255 * alpha)
                screen.fill((0, 128, 0))
                text_surface = bigger_font.render("increase speed", True, (alpha, alpha, alpha))
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

            distance = (reply["CSAFE_PM_GET_WORKDISTANCE"][0] + reply["CSAFE_PM_GET_WORKDISTANCE"][1]) / 10.0
            cadence = reply["CSAFE_GETCADENCE_CMD"][0]
            watts = reply["CSAFE_GETPOWER_CMD"][0]
            current_bpm = reply["CSAFE_GETHRCUR_CMD"][0]
            state = reply["CSAFE_PM_GET_STROKESTATE"]

            record(4, current_bpm, cadence, watts, distance, 0, 0)

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
    weighted_bpm_line = []
    last_phase = 0

    for row in logged_stats:
        phase, t, bpm, cadence, watts, distance, target_cadence, target_watts, weighted_bpm = row
        t_alpha = (t - min_t) / t_span
        x_plot = screen_width * t_alpha
        y_plot = screen_height * .5 - ((bpm - resting_bpm) * 20)
        bpm_line.append((x_plot, y_plot))

        y_plot = screen_height * .5 - ((weighted_bpm - resting_bpm) * 20)
        weighted_bpm_line.append((x_plot, y_plot))

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

    pygame.draw.lines(screen, "red", False, bpm_line, 1)
    pygame.draw.lines(screen, "white", False, weighted_bpm_line, 1)

    text_surface = smol_font.render(f"active target: {target_bpm[0]} to {target_bpm[1]}", True, (255, 255, 255))
    screen.blit(text_surface, (10, screen_height - 50))
    text_surface = smol_font.render(f"resting bpm: {resting_bpm}", True, (255, 255, 255))
    screen.blit(text_surface, (10, screen_height - 100))


    pygame.display.flip()

    date_stamp = datetime.datetime.now().strftime("%Y_%m_%d")
    out_path_template = f"{date_stamp}_rowing_log{{}}.json"
    out_path = out_path_template.format("")

    counter = 0
    while os.path.exists(out_path):
        counter += 1
        out_path = out_path_template.format(f"_{zero_pad(counter, 3)}")

    # should probably just dump all of this into a sqlite database
    with open(out_path, "w") as out_file:
        log_blob = {
            "date" : date_stamp,
            "start_time" : start_time_str,
            "resting_bpm" : resting_bpm,
            "intervals" : INTERVALS,
            "calibration_time" : CALIBRATION_TIME,
            "steady_time" : STEADY_TIME,
            "cooldown_time" : COOLDOWN_TIME,
            "target_low" : TARGET_LOW,
            "target_high" : TARGET_HIGH,
            "log_headers" : log_headers,
            "log" : logged_stats,
        }
        out_file.write(json.dumps(log_blob))

    print("Workout complete!")

    while poll_events():
        poll_events()
        time.sleep(.1)

