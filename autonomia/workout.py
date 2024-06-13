

import os
import sys
import math
import glob
import datetime
import pygame
from gui import Display
from session import ManualSession, RowingSession, ReplaySession, Phase, Event
from log_viewer import ResultsGraph
from resting_bpm import RestingBPM
from quiesce import FullStop
from misc import zero_pad, lerp, pretty_time
import metronome


class ErgSearch:
    def __init__(self):
        pass

    def __call__(self, gui):
        gui.clear("gray")
        gui.draw_text('Searching for erg...', 0, 0)


class PleaseBegin:
    def __init__(self):
        pass

    def __call__(self, gui, session, event):
        gui.clear((96, 96, 128))

        if event:
            wiggle_bpm = (event.bpm - session.resting_bpm) >= 10

            gui.draw_stat("Current BPM:", round(event.bpm), 0, 0, wiggle = wiggle_bpm)
            gui.draw_stat("Resting BPM:", round(session.resting_bpm), 1, 0)
            gui.draw_text("please begin", 700, None, font="big")


class IntervalRunner:
    def __init__(self, session, bpm_debug):

        self.bpm_debug = bpm_debug
        self.current_interval = 0

        self.target_bpm_low = session.resting_bpm + session.config.target_bpm_low
        self.target_bpm_high = session.resting_bpm + session.config.target_bpm_high
        self.target_bmp_pivot = lerp(self.target_bpm_low, self.target_bpm_high, session.config.target_bpm_bias)

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

        self.current_cadence = 0
        self.current_watts = 0
        self.current_rolling_bpm = 0

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

    def update(self, session, event):
        if not event:
            return
        self.current_cadence = self.filter_cadence(event.cadence)
        self.current_watts = event.watts
        self.current_rolling_bpm = event.bpm_rolling_average

        if session.phase == Phase.CALIBRATION:
            hold = False

            if self.current_rolling_bpm < self.target_bpm_low:
                # reset the calibration targets
                self.target_cadence = self.current_cadence
                self.target_watts = event.watts
                self.samples = 1

            elif self.current_rolling_bpm > self.target_bpm_high:
                # reset the calibration targets
                self.target_cadence = self.current_cadence
                self.target_watts = event.watts
                self.samples = 1

            else:
                weight = max(self.samples + 1, 1)
                self.target_cadence += self.current_cadence * weight
                self.target_watts += event.watts * weight
                self.samples += weight
                hold = True

            if self.samples > 0 and hold:
                event.target_cadence = int(self.target_cadence / self.samples)

            if self.samples > 0 and hold:
                event.target_watts = int(self.target_watts / self.samples)

        elif session.phase == Phase.STEADY:
            if self.samples > 1:
                self.target_cadence //= self.samples
                self.target_watts //= self.samples
                self.samples = 1

            event.target_cadence = self.target_cadence
            event.target_watts = self.target_watts


    def draw(self, gui, session, current_bpm, remaining_time):
        gui.clear((96, 64, 128))

        if session.phase == Phase.CALIBRATION:
            alpha = 1
            reading_color = (255, 255, 255)
            hold = False

            if self.current_rolling_bpm < self.target_bpm_low:
                alpha = math.sin(session.now() * 5) * .5 + .5
                reading_color = (255, 255 * alpha, 255 * alpha)
                gui.clear((0, 128, 0))
                gui.draw_text("increase speed", 100, 1200, (alpha, alpha, alpha), font="bigger")


            elif self.current_rolling_bpm > self.target_bpm_high:
                alpha = math.sin(session.now() * 5) * .5 + .5
                reading_color = (255 * alpha, 255 * alpha, 255)
                gui.clear((128, 0, 0))
                gui.draw_text("decrease speed", 100, 1200, (alpha, alpha, alpha), font="bigger")

            else:
                hold = True
                gui.clear((96, 64, 128))
                gui.draw_text("perfect.  hold.", 100, 1200, font="bigger")

            gui.draw_text(f"Remaining Calibration Time {remaining_time}", 0, 0)

            nudge = 0
            if self.current_rolling_bpm <= self.target_bmp_pivot - 1:
                nudge = 1
            elif self.current_rolling_bpm > self.target_bmp_pivot + 1:
                nudge = -1

            gui.draw_stat("Current Cadence:", self.current_cadence, 0, 0)
            if self.samples > 0 and hold:
                target_cadence = int(self.target_cadence / self.samples) + nudge
                gui.draw_stat("Target Cadence:", target_cadence, 1, 0, reading_color)

            gui.draw_stat("Current Watts:", self.current_watts, 0, 1)
            if self.samples > 0 and hold:
                target_watts = int(self.target_watts / self.samples) + nudge
                gui.draw_stat("Target Watts:", target_watts, 1, 1, reading_color)

            if self.bpm_debug and nudge != 0:
                gui.draw_text(f"nudge: {nudge}", gui.w * .75, gui.h * .6,
                              "white", font="regular", x_align = 0, y_align = 0)

        elif session.phase == Phase.STEADY:
            alpha = 1
            reading_color = (255, 255, 255)

            wiggle_cadence = abs(self.current_cadence - self.target_cadence) > 1
            wiggle_watts = abs(self.current_watts - self.target_watts) > 1

            if self.current_cadence > self.target_cadence + 1 or self.current_watts > self.target_watts + 1:
                alpha = math.sin(session.now() * 5) * .5 + .5
                reading_color = (255 * alpha, 255 * alpha, 255)
                gui.clear((128, 0, 0))
                gui.draw_text("decrease speed", 100, 1200, (alpha, alpha, alpha), font="bigger")

            elif self.current_cadence < self.target_cadence - 1 or self.current_watts < self.target_watts - 1:
                alpha = math.sin(session.now() * 5) * .5 + .5
                reading_color = (255, 255 * alpha, 255 * alpha)
                gui.clear((0, 128, 0))
                gui.draw_text("increase speed", 100, 1200, (alpha, alpha, alpha), font="bigger")

            else:
                gui.clear((96, 64, 128))
                gui.draw_text("perfect.  hold.", 100, 1200, font="bigger")

            gui.draw_text(f"Remaining Time {remaining_time}", 0, 0)

            gui.draw_stat("Current Cadence:", self.current_cadence, 0, 0, wiggle=wiggle_cadence)
            gui.draw_stat("Target Cadence:", self.target_cadence, 1, 0)

            gui.draw_stat("Current Watts:", self.current_watts, 0, 1, wiggle=wiggle_watts)
            gui.draw_stat("Target Watts:", self.target_watts, 1, 1)

        elif session.phase == Phase.COOLDOWN:
            gui.clear((96, 96, 128))
            gui.draw_text(f"Cool Down {remaining_time}", 0, 0)

        if self.bpm_debug:
            debug_color = (0, 0, 0, 255 * .5)

            high_y = 150
            low_y = gui.h - 400
            target_y = lerp(low_y, high_y, session.config.target_bpm_bias)

            high_line = [(1500, high_y), (gui.w, high_y)]
            low_line = [(1500, low_y), (gui.w, low_y)]
            target_line = [(1500, target_y), (gui.w, target_y)]

            bpm_a = (current_bpm - self.target_bpm_low) / abs(self.target_bpm_high - self.target_bpm_low)
            bpm_a = max(min(bpm_a, 1.05), -.05)
            bpm_y = lerp(low_y, high_y, bpm_a)
            bpm_line = [(1500, bpm_y), (gui.w, bpm_y)]

            pygame.draw.lines(gui.screen, debug_color, False, high_line, 2)
            pygame.draw.lines(gui.screen, debug_color, False, low_line, 2)
            pygame.draw.lines(gui.screen, debug_color, False, target_line, 2)
            pygame.draw.lines(gui.screen, "white", False, bpm_line, 2)

            gui.draw_text(int(self.target_bpm_high), 1500, high_y,
                            color=debug_color, font="smol", x_align=1, y_align=.5)
            gui.draw_text(int(self.target_bpm_low), 1500, low_y,
                            color=debug_color, font="smol", x_align=1, y_align=.5)
            gui.draw_text(int(self.target_bmp_pivot), 1500, target_y,
                            color=debug_color, font="smol", x_align=1, y_align=.5)

            gui.draw_text(int(current_bpm), 1500, bpm_y,
                            color="white", font="smol", x_align=1, y_align=.5)


def workout_main(gui, volume, bluetooth_address, no_erg = False,
                 replay_path = None, replay_speed = None, no_save = False, bpm_debug = False):
    if volume > 0:
        metronome.start()

    no_erg = False

    session = None
    if replay_path:
        assert(os.path.isfile(replay_path))
        session = ReplaySession(replay_path, replay_speed)
    else:
        if bluetooth_address:
            no_erg = True # TODO

        if no_erg:
            session = ManualSession()
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

    if bluetooth_address:
        if not session.connect_bluetooth(bluetooth_address):
            return

    if not no_erg:
        lobby = ErgSearch()
        while not session.connect_erg():
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
        for i in range(60):
            begin_phase(gui, session, event)
            gui.present()
            if gui.pump_events().count(pygame.K_SPACE) > 0 or session.workout_started():
                session.set_phase(Phase.CALIBRATION)
                break
            session.sleep(1/60)

    def remaining_time_str(stop_time):
        return pretty_time(max(int(stop_time - session.now()), 0))

    intervals = IntervalRunner(session, bpm_debug)

    def interval_present(skip_key):
        gui.present()
        for i in range(4):
            keys = gui.pump_events()
            if keys.count(skip_key) > 0:
                return True
            session.sleep(.25)
        return False

    current_bpm = 0
    for interval in range(session.config.intervals):

        metronome.tweak(15, 0)

        calibration_stop_time = session.now() + session.config.calibration_time * 60
        if session.phase == Phase.COOLDOWN:
            session.set_phase(Phase.CALIBRATION)

        while session.phase == Phase.CALIBRATION:
            event = session.advance()
            if not event:
                continue
            skip_requested = False
            if session.live or session.phase == event.phase:
                intervals.update(session, event)
                current_bpm = event.bpm_rolling_average
                for i in range(15):
                    intervals.draw(gui, session, current_bpm, remaining_time_str(calibration_stop_time))
                    gui.present()
                    if gui.pump_events().count(pygame.K_BACKSPACE) > 0:
                        skip_requested = True
                        break
                    session.sleep(1/15)
            else:
                skip_requested = True

            if skip_requested or (session.live and session.now() > calibration_stop_time):
                session.set_phase(Phase.STEADY)

        cadence = intervals.target_cadence
        if intervals.samples > 0:
            cadence //= intervals.samples

        metronome.reset(cadence, 1 * volume)

        steady_stop_time = session.now() + session.config.steady_time * 60

        while session.phase == Phase.STEADY:
            event = session.advance()
            skip_requested = False
            if session.live or session.phase == event.phase:
                intervals.update(session, event)
                current_bpm = event.bpm_rolling_average
                for i in range(60):
                    intervals.draw(gui, session, current_bpm, remaining_time_str(steady_stop_time))
                    gui.present()
                    if gui.pump_events().count(pygame.K_BACKSPACE) > 0:
                        skip_requested = True
                        break
                    session.sleep(1/60)
            else:
                skip_requested = True

            if skip_requested or (session.live and session.now() > steady_stop_time):
                session.set_phase(Phase.COOLDOWN)

        metronome.tweak(10, 0)
        cooldown_stop_time = session.now() + session.config.cooldown_time * 60

        while session.phase == Phase.COOLDOWN:
            event = session.advance()
            skip_requested = True
            if event is None:
                break
            elif session.live or session.phase == event.phase:
                intervals.update(session, event)
                current_bpm = event.bpm_rolling_average
                intervals.draw(gui, session, current_bpm, remaining_time_str(cooldown_stop_time))
                skip_requested = present(pygame.K_BACKSPACE)
            if skip_requested or (session.live and session.now() > cooldown_stop_time):
                # the beginning of the interval loop will seek, as will the code following
                # said loop.
                break

    metronome.tweak(15, 0)

    session.set_phase(Phase.FULLSTOP)
    stop_phase = FullStop()

    while session.phase == Phase.FULLSTOP:
        event = session.advance()
        if not event:
            continue
        stop_phase(gui, session, event)

        gui.present()
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                session.set_phase(Phase.CALIBRATION)
                break
        #if present(pygame.K_SPACE):
        #    session.set_phase(Phase.CALIBRATION)
        #    break

    session.set_phase(Phase.RESULTS)
    if not no_save:
        session.save_to_disk()

    metronome.stop()

    # automatically open up the workout viewer
    viewer_main(gui)


def find_bpm_min_max(sessions, margin=5):
    bpm_min = math.inf
    bpm_max = 0

    for session in sessions:
        for event in session.log:
            bpm_min = min(bpm_min, min(event.bpm, event.bpm_rolling_average))
            bpm_max = max(bpm_max, max(event.bpm, event.bpm_rolling_average))

    bpm_min -= margin
    bpm_max += margin
    bpm_range = abs(bpm_max - bpm_min)

    return bpm_min, bpm_max, bpm_range


def viewer_main(gui, normalized_bpm_range = False):
    log_paths = sorted(glob.glob("????_??_??_rowing_log*.json"))

    sessions = []
    for path in log_paths:
        session = ReplaySession(path)
        session.set_phase(Phase.RESULTS)
        sessions.append(session)

    views = []
    if normalized_bpm_range:
        bpm_stats = find_bpm_min_max(sessions)
        views = [ResultsGraph(session, gui, bpm_stats, True) for session in sessions]

    else:
        for session in sessions:
            bpm_stats = find_bpm_min_max([session])
            views.append(ResultsGraph(session, gui, bpm_stats, False))


    pygame.mouse.set_visible(True)

    if len(views) == 0:
        print("No logs available.")
        return

    current_view = len(views) - 1
    current_mode = 4 # envelope mode
    mode_count = 5 # actually 6, but I don't like the bezier mode
    while True:
        view = views[current_view]
        view(gui, current_mode)

        date_label = view.session.date.replace("_", ".")
        weekday = datetime.datetime.strptime(view.session.date, "%Y_%m_%d").strftime("%A")
        parts = [date_label, weekday]
        if view.session.start_time:
            parts.append(view.session.start_time)
        date_label = "    ".join(parts)
        gui.draw_text(date_label, view.margin_x1, view.margin_y1, font="smol", y_align=1)

        gui.present()

        keys = gui.pump_events()
        if keys.count(pygame.K_RETURN):
            current_mode = (current_mode + 1) % mode_count

        elif keys.count(pygame.K_LEFT):
            current_view = max(current_view - 1, 0)

        elif keys.count(pygame.K_RIGHT):
            current_view = min(current_view + 1, len(views) -1)
