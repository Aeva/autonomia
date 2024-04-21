

import os
import sys
import math
import glob
import datetime
import pygame
from gui import Display
from session import RowingSession, ReplaySession, Phase, Event
from log_viewer import ResultsGraph
from resting_bpm import RestingBPM
from quiesce import FullStop
from misc import zero_pad, lerp, pretty_time


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

        wiggle_bpm = (event.bpm - session.resting_bpm) >= 10

        gui.draw_stat("Current BPM:", event.bpm, 0, 0, wiggle = wiggle_bpm)
        gui.draw_stat("Resting BPM:", session.resting_bpm, 1, 0)
        gui.draw_text("please begin", 700, None, font="big")


class IntervalRunner:
    def __init__(self, session, bpm_debug):

        self.bpm_debug = bpm_debug
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
                self.target_cadence += self.current_cadence
                self.target_watts += event.watts
                self.samples += 1
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


    def draw(self, gui, session, remaining_time):
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

            gui.draw_stat("Current Cadence:", self.current_cadence, 0, 0)
            if self.samples > 0 and hold:
                target_cadence = int(self.target_cadence / self.samples)
                gui.draw_stat("Target Cadence:", target_cadence, 1, 0, reading_color)

            gui.draw_stat("Current Watts:", self.current_watts, 0, 1)
            if self.samples > 0 and hold:
                target_watts = int(self.target_watts / self.samples)
                gui.draw_stat("Target Watts:", target_watts, 1, 1, reading_color)

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
            debug_color = (64, 64, 64)
            gui.draw_stat("Rolling BPM:", event.bpm, 2, 0, debug_color, debug_color)
            gui.draw_stat("Resting BPM:", session.resting_bpm, 2, 1, debug_color, debug_color)

            debug_outline = [
                (1500, 50),
                (1500, 1100),
                ]

            pygame.draw.lines(gui.screen, debug_color, False, debug_outline, 8)


def workout_main(gui, replay_path = None, replay_speed = None, no_save = False, bpm_debug = False):
    session = None
    if replay_path:
        assert(os.path.isfile(replay_path))
        session = ReplaySession(replay_path, replay_speed)
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
        for i in range(60):
            begin_phase(gui, session, event)
            gui.present()
            if gui.pump_events().count(pygame.K_SPACE) > 0:
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

    for interval in range(session.config.intervals):

        calibration_stop_time = session.now() + session.config.calibration_time * 60
        if session.phase == Phase.COOLDOWN:
            session.set_phase(Phase.CALIBRATION)

        while session.phase == Phase.CALIBRATION:
            event = session.advance()
            skip_requested = False
            if session.live or session.phase == event.phase:
                intervals.update(session, event)
                for i in range(15):
                    intervals.draw(gui, session, remaining_time_str(calibration_stop_time))
                    gui.present()
                    if gui.pump_events().count(pygame.K_BACKSPACE) > 0:
                        skip_requested = True
                        break
                    session.sleep(1/15)
            else:
                skip_requested = True

            if skip_requested or (session.live and session.now() > calibration_stop_time):
                session.set_phase(Phase.STEADY)

        steady_stop_time = session.now() + session.config.steady_time * 60

        while session.phase == Phase.STEADY:
            event = session.advance()
            skip_requested = False
            if session.live or session.phase == event.phase:
                intervals.update(session, event)
                for i in range(60):
                    intervals.draw(gui, session, remaining_time_str(steady_stop_time))
                    gui.present()
                    if gui.pump_events().count(pygame.K_BACKSPACE) > 0:
                        skip_requested = True
                        break
                    session.sleep(1/60)
            else:
                skip_requested = True

            if skip_requested or (session.live and session.now() > steady_stop_time):
                session.set_phase(Phase.COOLDOWN)

        cooldown_stop_time = session.now() + session.config.cooldown_time * 60

        while session.phase == Phase.COOLDOWN:
            event = session.advance()
            skip_requested = True
            if event is None:
                break
            elif session.live or session.phase == event.phase:
                intervals.update(session, event)
                intervals.draw(gui, session, remaining_time_str(cooldown_stop_time))
                skip_requested = present(pygame.K_BACKSPACE)
            if skip_requested or (session.live and session.now() > cooldown_stop_time):
                # the beginning of the interval loop will seek, as will the code following
                # said loop.
                break

    session.set_phase(Phase.FULLSTOP)
    stop_phase = FullStop()

    while session.phase == Phase.FULLSTOP:
        event = session.advance()
        stop_phase(gui, session, event or Event())
        if present(pygame.K_SPACE):
            session.set_phase(Phase.CALIBRATION)
            break

    session.set_phase(Phase.RESULTS)
    if not no_save:
        session.save_to_disk()

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
