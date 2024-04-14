

import os
import sys
from gui import Display
from workout import workout_main


if __name__ == "__main__":
    if len(sys.argv) == 1:
        gui = Display()
        workout_main(gui)
        sys.exit(0)

    elif len(sys.argv) == 2 and sys.argv[1] == "--replay":
        print("Replay file not specified.")
        sys.exit(1)

    elif len(sys.argv) == 3 and sys.argv[1] == "--replay":
        replay_path = sys.argv[2]
        if os.path.isfile(replay_path):
            gui = Display()
            workout_main(gui, replay_path)
        else:
            print("Replay file not found.")
            sys.exit(1)

    else:
        print("Expected usage:")
        print(" > python autonomia")
        print("or")
        print(" > python autonomia --replay relative/path/to/rowing_log.json")
        sys.exit(1)
