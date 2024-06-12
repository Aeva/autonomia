
import multiprocessing
import time
import os


os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"
import warnings
warnings.simplefilter("ignore")
import pygame.midi
warnings.resetwarnings()


_proc = None
_queue = None


def inner(queue):
    cadence = 0
    volume = 0
    current_t = 0

    pygame.midi.init()
    midi_id = 0
    midi_info = pygame.midi.get_device_info(midi_id)
    while midi_info != None:
        _, name, _, is_output, is_opened = midi_info
        if name.startswith(b"TiMidity") and is_output == 1 and is_opened == 0:
            break
        else:
            midi_id += 1
            midi_info = pygame.midi.get_device_info(midi_id)

    if not midi_info:
        print("Can't find timidity.  Run `timidity -iA -Os` and try again.")
        return

    print(midi_info)

    m = pygame.midi.Output(midi_id, latency=0, buffer_size=1024)
    i = 0

    note = 0
    velocity = 0

    try:
        meter = 4
        beat = 0
        half_beat = 0

        program = 11
        m.write_short(0xC0, program, 0)

        next_beat = time.time_ns()
        next_rest = None

        while True:
            time.sleep(0.01)
            try:
                packet = queue.get_nowait()
            except:
                packet = None

            if packet:
                command, new_cadence, new_volume = packet
                if command == "halt":
                    m.close()
                    return
                elif command == "reset" or command == "tweak":
                    if command == "reset":
                        i = 0
                        next_beat = time.time_ns()
                        next_rest = None

                    cadence, volume = new_cadence, new_volume
                    interval = int(1000_000_000 * (60 / cadence))
                    beat = interval // meter
                    half_beat = beat // 2

                    new_next = time.time_ns() + beat
                    if command == "tweak" and new_next < next_beat:
                        next_beat = new_next
                        if next_rest:
                            next_rest = next_beat - half_beat

            now = time.time_ns()

            if volume > 0 and beat > 0:
                if now >= next_beat:
                    if i == 0:
                        note = 69
                        velocity = int(127 * volume)
                    else:
                        note = 60
                        velocity = int(90 * volume)

                    m.write_short(0x90, note, velocity)
                    next_beat += beat
                    next_rest = next_beat - half_beat
                    i = (i + 1) % meter

                if next_rest and now >= next_rest:
                    m.write_short(0x80, note, 0)
                    next_rest = None
    except KeyboardInterrupt:
        if note:
            m.write_short(0x80, note, 0)
        m.close()

def start():
    global _proc
    global _queue

    multiprocessing.set_start_method('spawn')
    _queue = multiprocessing.Queue()
    _proc = multiprocessing.Process(target=inner, args=(_queue,))
    _proc.start()


def stop():
    global _proc
    global _queue
    if _proc and _queue:
        _queue.put(("halt", 0, 0), True)
        _proc.join()

        _queue = None
        _proc = None


def reset(cadence, volume):
    if _queue:
        try:
            _queue.put(("reset", cadence, volume), False)
        except:
            pass


def tweak(cadence, volume):
    if _queue:
        try:
            _queue.put(("tweak", cadence, volume), False)
        except:
            pass
