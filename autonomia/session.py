

import datetime
import time
import json
import os
from enum import IntEnum
import config
from misc import zero_pad

# todo: install PyRow properly somewhere
import os, sys
sys.path.append(os.path.join(os.getcwd(), "PyRow"))
from PyRow import pyrow


class Phase(IntEnum):
    INVALID = -1
    RESTING_BPM = 0
    PENDING = 1
    CALIBRATION = 2
    STEADY = 3
    COOLDOWN = 4
    FULLSTOP = 5
    RESULTS = 6
    SHUTDOWN = 7


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

    def window(self, samples, seconds):
        if len(samples) <= 1:
            return samples
        last_t = samples[-1].time
        seek = 1
        for sample in samples[::-1]:
            if last_t - sample.time <= seconds:
                seek += 1
            else:
                break
        start = (seek + 1) * -1
        frame = samples[start:-1]
        return frame

    def weighted_average(self, rows, stat_name, exponent=0):
        if len(rows) < 1:
            return 0
        elif len(rows) == 1:
            return getattr(rows[0], stat_name)
        elif exponent <= 0:
            return sum([getattr(event, stat_name) for event in rows]) / len(rows)
        else:
            acc_v = 0
            acc_w = 0
            samples = [(event.time, getattr(event, stat_name)) for event in rows]
            t1 = samples[0][0]
            tN = samples[-1][0]
            dt = tN - t1
            for t, stat in samples:
                a = (t - t1) / dt
                a_exp = a ** exponent
                acc_v += stat * a_exp
                acc_w += a_exp
            return acc_v / acc_w

    def log_window(self, seconds):
        return self.window(self.log, seconds)

    def connect(self):
        return True

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



class RowingSession(Session):
    """
    This class represents all of the data in a typical workout session.
    """

    def __init__(self):
        Session.__init__(self)
        self.live = True
        self.erg = None

    def connect(self):
        for available_erg in pyrow.find():
            self.erg = pyrow.pyrow(available_erg)
            print("erg found!")
            return True
        return False

    def advance(self):
        assert(self.erg is not None)
        query = [
            "CSAFE_PM_GET_WORKDISTANCE",
            "CSAFE_GETCADENCE_CMD",
            "CSAFE_GETPOWER_CMD",
            "CSAFE_GETHRCUR_CMD"]
            #"CSAFE_PM_GET_STROKESTATE"]
        reply = self.erg.send(query)

        event = Event()
        event.phase = self.phase
        event.time = self.now()
        event.bpm = reply["CSAFE_GETHRCUR_CMD"][0]
        event.bpm_rolling_average = 0

        event.cadence = reply["CSAFE_GETCADENCE_CMD"][0]
        event.target_cadence = 0

        event.watts = reply["CSAFE_GETPOWER_CMD"][0]
        event.target_watts = 0

        event.distance = sum(reply["CSAFE_PM_GET_WORKDISTANCE"][0:2]) / 10.0

        window_seq = self.log_window(5)
        window_seq.append(event)

        if len(window_seq) > 1:
            event.bpm_rolling_average = self.weighted_average(window_seq, "bpm", 2)
        else:
            event.bpm_rolling_average = event.bpm

        self.log.append(event)
        return event


class ReplaySession(Session):
    def __init__(self, replay_path, replay_speed):
        Session.__init__(self)

        with open(replay_path, "r") as infile:
            self.replay = json.loads(infile.read())

        self.speed_override = replay_speed
        if self.speed_override is not None:
            assert(type(self.speed_override) == float)
            self.speed = self.speed_override

        self.seek = 0

        self.date = self.replay["date"]
        self.start_time = self.replay.get("start_time", "")
        self.resting_bpm = self.replay["resting_bpm"]

        self.config.intervals = self.replay["intervals"]
        self.config.calibration_time = self.replay["calibration_time"]
        self.config.steady_time = self.replay["steady_time"]
        self.config.cooldown_time = self.replay["cooldown_time"]
        self.config.target_bpm_low = self.replay["target_low"]
        self.config.target_bpm_high = self.replay["target_high"]

        self.replay_log = []

        if len(self.replay["log"][0]) == 9:
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

        elif len(self.replay["log"][0]) == 6:
            for row in self.replay["log"]:
                phase, t, bpm, cadence, watts, distance = row
                e = Event()
                e.phase = Phase(phase)
                e.time = t
                e.bpm = bpm
                e.cadence = cadence
                e.watts = watts
                e.distance = distance
                e.target_cadence = 0
                e.target_watts = 0
                e.bpm_rolling_average = bpm
                self.replay_log.append(e)

    def now(self):
        return time.time()

    def sleep(self, seconds):
        if self.speed > 0:
            time.sleep(seconds * self.speed)

    def update_speed(self):
        if self.speed_override is None:
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
