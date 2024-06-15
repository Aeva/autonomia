
import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"
import warnings
warnings.simplefilter("ignore")
import pygame
warnings.resetwarnings()

import sys
import time
import argparse
import pathlib
import traceback
from gui import Display
from workout import workout_main, viewer_main
from battery import battery_main
from metronome_test import metronome_test_main
import metronome
import bluetooth


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

    parser.add_argument(
        "--no_erg",
        action="store_true",
        help="non-rowing exercise session")

    parser.add_argument(
        "--bluetooth_address",
        action="store",
        type=str,
        help="preferred bluetooth device to connect to")

    parser.add_argument(
        "--bluetooth_scan",
        action="store_true",
        help="scan for compatible bluetooth devices")

    parser.add_argument(
        "--battery",
        action="store_true",
        help="print the bluetooth device battery level")

    parser.add_argument(
        "--bluetooth_debug",
        action="store_true",
        help="print the bluetooth device bpm stream")

    parser.add_argument(
        "--metronome",
        action="store",
        type=int,
        default=None,
        help="tempo")

    parser.add_argument(
        "--heart_metronome",
        action="store_true")

    parser.add_argument(
        "--volume",
        action="store",
        type=float,
        help="metronome volume, must be between 0 and 1")

    args = parser.parse_args()

    volume = min(max(args.volume, 0.0), 1.0) if args.volume is not None else 1.0

    try:
        if args.metronome:
            metronome.start()
            metronome.prog(115) #115)
            metronome.reset(args.metronome / metronome.meter, volume)
            try:
                while True:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                pass
            metronome.stop()
            sys.exit(0)

        device_addr = None
        if args.bluetooth_scan:
            print("Searching for compatible bluetooth devices...\n")
            found = bluetooth.scan()
            for address, name in found.items():
                print(f"\t{address} -> {name}")
            sys.exit(0)

        elif args.bluetooth_address:
            device_addr = args.bluetooth_address
        else:
            device_addr = os.environ.get("BLE_HRM_ADDRESS")

        ###
        if device_addr:
            print(f"heart monitor address: {device_addr}")
        ###

        if args.battery:
            battery_main(device_addr)
            sys.exit(0)

        if args.bluetooth_debug:
            #os.environ["PYTHONASYNCIODEBUG"] = '1'
            #os.environ["BLEAK_LOGGING"] = '1'
            bluetooth.debug_main(device_addr)
            sys.exit(0)

        if args.heart_metronome:
            metronome_test_main(device_addr)
            sys.exit(0)

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
                    volume,
                    None,
                    replay_path = replay_path,
                    replay_speed = speed_divisor,
                    no_save = args.no_save,
                    bpm_debug = args.bpm_debug)
            else:
                print("Replay file not found.")
                sys.exit(1)

        else:
            if args.no_erg:
                assert(device_addr != None)
            else:
                device_addr = None
            gui = Display()
            workout_main(gui, volume, device_addr, no_save=args.no_save, bpm_debug=args.bpm_debug)
    except Exception:
        print(traceback.format_exc())

    finally:
        metronome.stop()
        bluetooth.stop()
