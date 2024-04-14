

import datetime
import time
import json
import os
from enum import IntEnum
import config
from misc import zero_pad
import PyRow


class Phase(IntEnum):
    INVALID = -1
    RESTING_BPM = 0
    PENDING = 1
    CALIBRATION = 2
    STEADY = 3
    COOLDOWN = 4
    RESULTS = 5
    SHUTDOWN = 6


class Event:
    def __init__(self):
        self.phase = Phase.INVALID
        self.time = 0

        self.bpm = 0
        self.bpm_rolling_average = 0

        self.cadence = 0
        self.target_cadence = 0

        self.watts = 0
        self.target_watts = 0

        self.distance = 0

        self.error = False


class Session:
    """
    This class represents all of the data in a typical workout session.
    """

    def __init__(self):
        self.config = config.Config()

        now = datetime.datetime.now()
        self.date = now.strftime("%Y_%m_%d")
        self.start_time = now.strftime("%I:%M %p")
        self.resting_bpm = 0
        self.log = []
        self.phase = Phase.INVALID
        self.live = False

        self.speed = 1

    def now(self):
        return time.time()

    def sleep(self, seconds):
        time.sleep(seconds)

    def set_resting_bpm(self, resting_bpm):
        self.resting_bpm = resting_bpm

    def set_phase(self, phase):
        assert(type(phase) == Phase)
        self.phase = phase

    def advance(self):
        return 0

    def save_to_disk(self):
        prefix = ""
        if not self.live:
            prefix = "REPLAY_"
        out_path_template = f"{prefix}{self.date}_rowing_log{{}}.json"
        out_path = out_path_template.format("")

        counter = 0
        while os.path.exists(out_path):
            counter += 1
            out_path = out_path_template.format(f"_{zero_pad(counter, 3)}")

        log_headers = [
            "phase", "elapsed_time", "bpm", "cadence", "watts", "distance",
            "target cadence", "target watts", "bpm_rolling_average"]

        logged_stats = []
        for e in self.log:
            phase = int(e.phase)
            t = e.time
            bpm = e.bpm
            cadence = e.cadence
            watts = e.watts
            distance = e.distance
            target_cadence = e.target_cadence
            target_watts = e.target_watts
            weighted_bpm = e.bpm_rolling_average
            row = (phase, t, bpm, cadence, watts, distance, target_cadence, target_watts, weighted_bpm)
            logged_stats.append(row)

        # should probably just dump all of this into a sqlite database
        with open(out_path, "w") as out_file:
            log_blob = {
                "date" : self.date,
                "start_time" : self.start_time,
                "resting_bpm" : self.resting_bpm,
                "intervals" : self.config.intervals,
                "calibration_time" : self.config.calibration_time,
                "steady_time" : self.config.steady_time,
                "cooldown_time" : self.config.cooldown_time,
                "target_low" : self.config.target_bpm_low,
                "target_high" : self.config.target_bpm_high,
                "log_headers" : log_headers,
                "log" : logged_stats,
            }
            out_file.write(json.dumps(log_blob))

        print("Workout complete!")



class RowingSession:
    """
    This class represents all of the data in a typical workout session.
    """

    def __init__(self):
        Session.__init__(self)
        self.live = True


class ReplaySession(Session):
    def __init__(self, replay_path):
        Session.__init__(self)

        with open(replay_path, "r") as infile:
            self.replay = json.loads(infile.read())

        self.seek = 0

        self.date = self.replay["date"]
        self.start_time = self.replay["start_time"]

        self.config.intervals = self.replay["intervals"]
        self.config.calibration_time = self.replay["calibration_time"]
        self.config.steady_time = self.replay["steady_time"]
        self.config.cooldown_time = self.replay["cooldown_time"]
        self.config.target_bpm_low = self.replay["target_low"]
        self.config.target_bpm_high = self.replay["target_high"]

        self.replay_log = []
        for row in self.replay["log"]:
            phase, t, bpm, cadence, watts, distance, target_cadence, target_watts, weighted_bpm = row
            e = Event()
            e.phase = Phase(phase)
            e.time = t
            e.bpm = bpm
            e.cadence = cadence
            e.watts = watts
            e.distance = distance
            e.target_cadence = target_cadence
            e.target_watts = target_watts
            e.bpm_rolling_average = weighted_bpm
            self.replay_log.append(e)

    def now(self):
        return time.time()

    def sleep(self, seconds):
        if self.speed > 0:
            time.sleep(seconds * self.speed)

    def update_speed(self):
        if self.phase < Phase.CALIBRATION:
            self.speed = .001
        elif self.phase < Phase.RESULTS:
            self.speed = 0
        else:
            self.speed = 1

    def set_resting_bpm(self, resting_bpm):
        self.resting_bpm = self.replay["resting_bpm"]

    def set_phase(self, phase):
        assert(type(phase) == Phase)

        if phase == Phase.RESULTS:
            while self.advance(drain=True) is not None:
                pass
            self.phase = Phase.RESULTS
            self.update_speed()

        elif phase != self.phase:
            cursor = self.seek
            for event in self.replay_log[cursor:]:
                if event.phase == phase:
                    self.phase = phase
                    self.update_speed()
                    return
                else:
                    self.log.append(event)
                    self.seek += 1
            self.phase = Phase.RESULTS
            self.update_speed()

    def advance(self, drain=False):
        if self.seek < len(self.replay_log):
            event = self.replay_log[self.seek]
            self.log.append(event)
            self.seek += 1
            if event.phase != self.phase and not drain:
                self.phase = event.phase
                self.update_speed()
                self.seek -= 1
            return event
        else:
            return None
