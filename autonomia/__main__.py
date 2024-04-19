
import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"
import warnings
warnings.simplefilter("ignore")
import pygame
warnings.resetwarnings()

import sys
import argparse
import pathlib
from gui import Display
from workout import workout_main, viewer_main


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='autonomia')

    mutually_exclusive = parser.add_mutually_exclusive_group()
    mutually_exclusive.add_argument(
        "-r", "--replay",
        action="store",
        type=pathlib.Path,
        help="replay a workout log")

    mutually_exclusive.add_argument(
        "--viewer",
        action="store_true",
        help="open the log viewer")

    parser.add_argument(
        "--bpm_debug",
        action="store_true",
        help="show bpm data when not normally allowed")

    parser.add_argument(
        "--no_save",
        action="store_true",
        help="don't save the log for this run")

    parser.add_argument(
        "--speed",
        action="store",
        type=float,
        default=None,
        help="replay speed multiplier")

    parser.add_argument(
        "--global_bpm_range",
        action="store_true",
        help="plot bpm on a global scale")

    args = parser.parse_args()

    if args.viewer:
        gui = Display()
        viewer_main(gui, normalized_bpm_range=args.global_bpm_range)
        sys.exit(0)

    elif args.replay:
        replay_path = args.replay
        if os.path.isfile(replay_path):
            speed_divisor = None
            if args.speed:
                speed_divisor = 1 / args.speed

            gui = Display()
            workout_main(
                gui,
                replay_path = replay_path,
                replay_speed = speed_divisor,
                no_save = args.no_save,
                bpm_debug = args.bpm_debug)
        else:
            print("Replay file not found.")
            sys.exit(1)

    else:
        gui = Display()
        workout_main(gui, no_save=args.no_save, bpm_debug=args.bpm_debug)
        sys.exit(0)
