

import os
import sys
import math
import pygame
from gui import Display
from session import RowingSession, ReplaySession, Phase
from misc import zero_pad


class ErgSearch:
    def __init__(self):
        pass

    def __call__(self, gui):
        gui.clear("gray")
        gui.draw_text('Searching for erg...', 0, 0)


class RestingBPM:
    def __init__(self, session):
        self.calibration = []
        self.calibration_start_time = session.now()


    def __call__(self, gui, session, event):
        self.calibration.append(event.bpm)
        if len(self.calibration) > 100:
            self.calibration = self.calibration[-101:]

        resting_bpm_average = sum(self.calibration) // len(self.calibration)
        resting_bpm_mode = max(set(self.calibration), key=self.calibration.count)

        resting_bpm_deviation = 0
        for sample in self.calibration:
            resting_bpm_deviation += abs(resting_bpm_average - sample)
        resting_bpm_deviation /= len(self.calibration)

        session.set_resting_bpm(resting_bpm_average)

        elapsed_seconds = int(session.now() - self.calibration_start_time)
        elapsed_minutes = zero_pad(elapsed_seconds // 60)
        elapsed_seconds = zero_pad(elapsed_seconds % 60)
        elapsed_time = f"{elapsed_minutes}:{elapsed_seconds}"

        gui.clear((64, 0, 128))

        if len(self.calibration) > 1:
            graph_min = event.bpm
            graph_max = event.bpm

            for sample in self.calibration:
                graph_min = min(graph_min, sample)
                graph_max = max(graph_max, sample)

            graph_span = max(graph_max - graph_min, 1)
            graph_scale = (gui.h * .25)
            graph_points = []
            histogram = []

            x_anchor = gui.w - (len(self.calibration) - 1) * gui.w_over_100
            y_anchor = gui.h - graph_scale - 20

            def plot(index, sample):
                graph_a = (sample - graph_min) / graph_span
                graph_x = x_anchor + index * gui.w_over_100
                graph_y = y_anchor + graph_scale * (1.0 - graph_a)
                return (graph_x, graph_y)

            for index, sample in enumerate(self.calibration):
                graph_points.append(plot(index, sample))

            x_anchor = 0

            for index, sample in enumerate(sorted(self.calibration)[::-1]):
                histogram.append(plot(index, sample))

            pygame.draw.lines(gui.screen, "black", False, histogram, 8)

            if resting_bpm_average == resting_bpm_mode:
                pygame.draw.lines(gui.screen, "magenta", False, [plot(0, resting_bpm_mode), plot(101, resting_bpm_mode)], 8)
            else:
                pygame.draw.lines(gui.screen, "pink", False, [plot(0, resting_bpm_mode), plot(101, resting_bpm_mode)], 8)
                pygame.draw.lines(gui.screen, "blue", False, [plot(0, resting_bpm_average), plot(101, resting_bpm_average)], 8)
            pygame.draw.lines(gui.screen, "white", False, graph_points, 8)

            gui.draw_stat("Current BPM:", event.bpm, 0, 0)
            gui.draw_stat("Elapsed Time:", elapsed_time, 1, 0)

            pygame.draw.lines(gui.screen, "blue", False, [(200, 900), (700, 900)], 16)
            gui.draw_stat("Average:", resting_bpm_average, 0, 1)


            pygame.draw.lines(gui.screen, "pink", False, [(900, 900), (1400, 900)], 16)
            gui.draw_stat("Mode:", resting_bpm_mode, 1, 1)

            gui.draw_stat("Deviation:", f"{resting_bpm_deviation:.2f}", 2, 1)

            gui.draw_text("Press space to stop calibration", 650, 1200)


class PleaseBegin:
    def __init__(self):
        pass

    def __call__(self, gui, session, event):
        gui.clear((96, 96, 128))

        gui.draw_stat("Current BPM:", event.bpm, 0, 0)
        gui.draw_stat("Resting BPM:", session.resting_bpm, 1, 0)
        gui.draw_text("please begin", 700, None, font="big")


class Intervals:
    def __init__(self, session):

        self.current_interval = 0

        self.target_bpm_low = session.resting_bpm + session.config.target_bpm_low
        self.target_bpm_high = session.resting_bpm + session.config.target_bpm_high

        self.target_cadence = 0
        self.target_watts = 0
        self.samples = 0
        self.last_valid_cadence = None

        assert(self.filter_cadence(200) == 0)
        self.last_valid_cadence = None

        assert(self.filter_cadence(10) == 10)
        assert(self.filter_cadence(200) == 10)
        self.last_valid_cadence = None

        self.workout_start_time = session.now()

    def filter_cadence(self, cadence):
        if cadence < 35:
            self.last_valid_cadence = cadence
            return cadence
        elif self.last_valid_cadence is not None:
            if cadence < self.last_valid_cadence * 1.1:
                self.last_valid_cadence = cadence
                return cadence
            else:
                return self.last_valid_cadence
        else:
            return 0

    def __call__(self, gui, session, event, remaining_time):
        gui.clear((96, 64, 128))

        cadence = self.filter_cadence(event.cadence)

        if session.phase == Phase.CALIBRATION:
            alpha = 1
            reading_color = (255, 255, 255)

            hold = False

            if event.bpm_rolling_average < self.target_bpm_low:
                alpha = math.sin(session.now() * 5) * .5 + .5
                reading_color = (255, 255 * alpha, 255 * alpha)
                gui.clear((0, 128, 0))
                gui.draw_text("increase speed", 100, 1200, (alpha, alpha, alpha), font="bigger")

                # reset the calibration targets
                self.target_cadence = cadence
                self.target_watts = event.watts
                self.samples = 1

            elif event.bpm_rolling_average > self.target_bpm_high:
                alpha = math.sin(session.now() * 5) * .5 + .5
                reading_color = (255 * alpha, 255 * alpha, 255)
                gui.clear((128, 0, 0))
                gui.draw_text("decrease speed", 100, 1200, (alpha, alpha, alpha), font="bigger")

                # reset the calibration targets
                self.target_cadence = cadence
                self.target_watts = event.watts
                self.samples = 1

            else:
                gui.clear((96, 64, 128))
                gui.draw_text("perfect.  hold.", 100, 1200, font="bigger")

                self.target_cadence += cadence
                self.target_watts += event.watts
                self.samples += 1
                hold = True

            gui.draw_text(f"Remaining Calibration Time {remaining_time}", 0, 0)

            gui.draw_stat("Current Cadence:", cadence, 0, 0)
            if self.samples > 0 and hold:
                event.target_cadence = int(self.target_cadence / self.samples)
                gui.draw_stat("Target Cadence:", event.target_cadence, 1, 0, reading_color)

            gui.draw_stat("Current Watts:", event.watts, 0, 1)
            if self.samples > 0 and hold:
                event.target_watts = int(self.target_watts / self.samples)
                gui.draw_stat("Target Watts:", event.target_watts, 1, 1, reading_color)

        elif session.phase == Phase.STEADY:
            alpha = 1
            reading_color = (255, 255, 255)

            if self.samples > 1:
                self.target_cadence //= self.samples
                self.target_watts //= self.samples
                self.samples = 1

            event.target_cadence = self.target_cadence
            event.target_watts = self.target_watts

            if cadence > self.target_cadence + 1 or event.watts > self.target_watts + 1:
                alpha = math.sin(session.now() * 5) * .5 + .5
                reading_color = (255 * alpha, 255 * alpha, 255)
                gui.clear((128, 0, 0))
                gui.draw_text("decrease speed", 100, 1200, (alpha, alpha, alpha), font="bigger")

            elif cadence < self.target_cadence - 1 or event.watts < self.target_watts - 1:
                alpha = math.sin(session.now() * 5) * .5 + .5
                reading_color = (255, 255 * alpha, 255 * alpha)
                gui.clear((0, 128, 0))
                gui.draw_text("increase speed", 100, 1200, (alpha, alpha, alpha), font="bigger")

            else:
                gui.clear((96, 64, 128))
                gui.draw_text("perfect.  hold.", 100, 1200, font="bigger")

            gui.draw_text(f"Remaining Time {remaining_time}", 0, 0)

            gui.draw_stat("Current Cadence:", cadence, 0, 0)
            if self.samples > 0:
                gui.draw_stat("Target Cadence:", self.target_cadence, 1, 0, reading_color)

            gui.draw_stat("Current Watts:", event.watts, 0, 1)
            if self.samples > 0:
                gui.draw_stat("Target Watts:", self.target_watts, 1, 1, reading_color)

        elif session.phase == Phase.COOLDOWN:
            gui.clear((96, 96, 128))

            gui.draw_text(f"Cool Down {remaining_time}", 0, 0)

        if not session.live:
            debug_color = (64, 64, 64)
            gui.draw_stat("Rolling BPM:", event.bpm, 2, 0, debug_color, debug_color)
            gui.draw_stat("Resting BPM:", session.resting_bpm, 2, 1, debug_color, debug_color)

            debug_outline = [
                (1500, 50),
                (1500, 1100),
                ]

            pygame.draw.lines(gui.screen, debug_color, False, debug_outline, 8)


class ResultsGraph:
    def __init__(self, session, gui):
        self.min_time = session.log[0].time
        self.max_time = session.log[-1].time
        self.time_span = self.max_time - self.min_time

        self.bpm_line = []
        self.weighted_bpm_line = []
        self.phase_lines = []

        self.last_phase = 0

        for event in session.log:
            time_alpha = (event.time - self.min_time) / self.time_span
            x_plot = gui.w * time_alpha
            y_plot = gui.h * .5 - ((event.bpm - session.resting_bpm) * 20)
            self.bpm_line.append((x_plot, y_plot))

            y_plot = gui.h * .5 - ((event.bpm_rolling_average - session.resting_bpm) * 20)
            self.weighted_bpm_line.append((x_plot, y_plot))

            if event.phase != self.last_phase:
                self.last_phase = event.phase
                phase_color = "gray"
                if event.phase == 2:
                    phase_color = "blue"
                if event.phase == 3:
                    phase_color = "green"
                if event.phase == 4:
                    phase_color = "red"
                self.phase_lines.append((phase_color, [(x_plot, 0), (x_plot, gui.h)]))


    def __call__(self, gui, session):
        gui.clear((96, 96, 96))
        for phase_color, phase_line in self.phase_lines:
            pygame.draw.lines(gui.screen, phase_color, False, phase_line, 2)

        pygame.draw.lines(gui.screen, "blue", False, [(0, gui.h * .5), (gui.w, gui.h * .5)], 2)

        pygame.draw.lines(
            gui.screen, "black", False,
            [(0, gui.h * .5 - (session.config.target_bpm_low * 20)),
            (gui.w, gui.h * .5 - (session.config.target_bpm_low * 20))], 2)

        pygame.draw.lines(
            gui.screen, "black", False,
            [(0, gui.h * .5 - (session.config.target_bpm_high * 20)),
            (gui.w, gui.h * .5 - (session.config.target_bpm_high * 20))], 2)

        pygame.draw.lines(gui.screen, "red", False, self.bpm_line, 1)
        pygame.draw.lines(gui.screen, "white", False, self.weighted_bpm_line, 1)

        target_bpm = (
            session.resting_bpm + session.config.target_bpm_low,
            session.resting_bpm + session.config.target_bpm_high)

        gui.draw_text(f"active target: {target_bpm[0]} to {target_bpm[1]}", 10, gui.h - 50, font="smol")

        gui.draw_text(f"resting bpm: {session.resting_bpm}", 10, gui.h - 100, font="smol")


def workout_main(gui, replay_path = None):
    session = None
    if replay_path:
        assert(os.path.isfile(replay_path))
        session = ReplaySession(replay_path)
    else:
        session = RowingSession()

    keys = []

    session.set_phase(Phase.RESTING_BPM)

    def present(skip_key):
        gui.present()
        for i in range(4):
            keys = gui.pump_events()
            if keys.count(skip_key) > 0:
                return True
            session.sleep(.25)
        return False

    lobby = ErgSearch()
    while not session.connect():
        lobby(gui)
        if present(None):
            sys.exit(0)

    resting_phase = RestingBPM(session)

    while session.phase == Phase.RESTING_BPM:
        event = session.advance()
        resting_phase(gui, session, event)
        if present(pygame.K_SPACE):
            session.set_phase(Phase.PENDING)
            break

    begin_phase = PleaseBegin()

    while session.phase == Phase.PENDING:
        event = session.advance()
        begin_phase(gui, session, event)
        if present(pygame.K_SPACE):
            session.set_phase(Phase.CALIBRATION)
            break

    def remaining_time_str(stop_time):
        remaining_seconds = max(int(stop_time - session.now()), 0)
        remaining_minutes = zero_pad(remaining_seconds // 60)
        remaining_seconds = zero_pad(remaining_seconds % 60)
        return f"{remaining_minutes}:{remaining_seconds}"

    intervals = Intervals(session)

    for interval in range(session.config.intervals):

        calibration_stop_time = session.now() + session.config.calibration_time * 60
        if session.phase == Phase.COOLDOWN:
            session.set_phase(Phase.CALIBRATION)

        while session.phase == Phase.CALIBRATION:
            event = session.advance()
            skip_requested = True
            if session.live or session.phase == event.phase:
                intervals(gui, session, event, remaining_time_str(calibration_stop_time))
                skip_requested = present(pygame.K_BACKSPACE)
            if skip_requested or (session.live and session.now() > calibration_stop_time):
                session.set_phase(Phase.STEADY)

        steady_stop_time = session.now() + session.config.steady_time * 60

        while session.phase == Phase.STEADY:
            event = session.advance()
            skip_requested = True
            if session.live or session.phase == event.phase:
                intervals(gui, session, event, remaining_time_str(steady_stop_time))
                skip_requested = present(pygame.K_BACKSPACE)
            if skip_requested or (session.live and session.now() > steady_stop_time):
                session.set_phase(Phase.COOLDOWN)

        cooldown_stop_time = session.now() + session.config.cooldown_time * 60

        while session.phase == Phase.COOLDOWN:
            event = session.advance()
            skip_requested = True
            if event is None:
                break
            elif session.live or session.phase == event.phase:
                intervals(gui, session, event, remaining_time_str(cooldown_stop_time))
                skip_requested = present(pygame.K_BACKSPACE)
            if skip_requested or (session.live and session.now() > cooldown_stop_time):
                # the beginning of the interval loop will seek, as will the code following
                # said loop.
                break

    session.set_phase(Phase.RESULTS)
    session.save_to_disk()

    pygame.mouse.set_visible(True)
    show_results = ResultsGraph(session, gui)
    while session.phase == Phase.RESULTS:
        show_results(gui, session)
        if present(None):
            break
