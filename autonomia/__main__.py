

import os
import sys
from gui import Display
from workout import workout_main


if __name__ == "__main__":
    replay_path = "2024_04_12_rowing_log.json"

    gui = Display()
    workout_main(gui, replay_path)
