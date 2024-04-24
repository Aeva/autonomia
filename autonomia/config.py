

class Config:
    def __init__(self):
        # The target BPM offset during the steady phase.  This specifies the low end of the range.
        self.target_bpm_low = 10

        # The target BPM offset during the steady phase.  This specifies the high end of the range.
        self.target_bpm_high = 20

        # Lerp value from low to high, which the calibration step should try to nudge you towards.
        self.target_bpm_bias = .5

        # An interval consists of an active BPM calibration phase, followed by steady state phase,
        # followed by a cooldown phase.
        self.intervals = 1

        # Number of minutes to find the intensity setpoint at the start of an interval.
        self.calibration_time = 2

        # Number of minutes to exercise at the calibrated setpoint.
        self.steady_time = 10

        # Number of minutes to spend cooling down after an interval.
        self.cooldown_time = 1
