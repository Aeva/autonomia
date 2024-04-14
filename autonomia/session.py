

import datetime
import time
import json
from enum import IntEnum
import config
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
        return time.time() #/ self.speed

    def sleep(self, seconds):
        time.sleep(seconds * self.speed)

    def advance(self):
        return 0


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

        self.speed = .001

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

    def advance(self):
        while True:
            if self.seek >= len(self.replay["log"]):
                return Phase["SHUTDOWN"], Event()
            else:
                row = self.replay["log"][self.seek]
                self.seek += 1

                phase, t, bpm, cadence, watts, distance, target_cadence, target_watts, weighted_bpm = row
                phase = Phase(phase)

                if phase == Phase.CALIBRATION and self.phase == Phase.COOLDOWN:
                    pass
                elif phase < self.phase:
                    continue

                self.phase = phase
                e = Event()
                e.phase = self.phase
                e.time = t
                e.bpm = bpm
                e.cadence = cadence
                e.watts = watts
                e.distance = distance
                e.target_cadence = target_cadence
                e.target_watts = target_watts
                e.bpm_rolling_average = weighted_bpm

                self.log.append(e)

                return self.phase, e

