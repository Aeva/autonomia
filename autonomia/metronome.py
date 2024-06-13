
import multiprocessing
import time
import os

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"
import warnings
warnings.simplefilter("ignore")
import pygame.midi
warnings.resetwarnings()


# measures per minute, not beats per minute!
meter = 4


_proc = None
_queue = None


def metronome_proc(queue):
    """
    Entry point for the metronome subprocess.
    """

    cadence = 0
    volume = 0

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
                command = packet[0]
                if command == "reset" or command == "tweak":
                    _, new_cadence, new_volume = packet

                    if command == "reset":
                        i = 0
                        next_beat = time.time_ns()
                        next_rest = None

                    cadence, volume = new_cadence, new_volume
                    interval = 60_000_000_000 // cadence
                    beat = interval // meter
                    half_beat = beat // 2

                    new_next = time.time_ns() + beat
                    if command == "tweak" and new_next < next_beat:
                        next_beat = new_next
                        if next_rest:
                            next_rest = next_beat - half_beat

                elif command == "prog":
                    _, new_program, _ = packet
                    program = min(max(new_program, 0), 255)
                    m.write_short(0xC0, program, 0)

                elif command == "halt":
                    m.close()
                    return

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
    """
    Start the metronome subprocess if one is not running.
    """
    global _proc
    global _queue

    if not (_proc and _queue):
        ctx = multiprocessing.get_context('spawn')
        _queue = ctx.Queue()
        _proc = ctx.Process(target=metronome_proc, args=(_queue,))
        _proc.start()


def stop():
    """
    Halt the metronome subprocess if one is running.
    """
    global _proc
    global _queue
    if _proc and _queue:
        _queue.put(("halt", 0, 0), True)
        _proc.join()

        _queue = None
        _proc = None


def reset(cadence, volume):
    """
    Set the current tempo and volume.  This resets the measure counter making
    the next beat the on-beat.  The `cadence` parameter is the number of
    measures per minute, not beats per minute.
    """
    if _queue:
        try:
            _queue.put(("reset", cadence, volume), False)
        except:
            pass


def tweak(cadence, volume):
    """
    Set the current tempo and volume.  This will not reset the measure counter.
    The `cadence` parameter is the number of measures per minute, not beats per
    minute.
    """
    if _queue:
        try:
            _queue.put(("tweak", cadence, volume), False)
        except:
            pass


def prog(program):
    """
    The program numbers for timidity all are general midi, but they index
    from 0 instead of 1, whereas general midi tables are often written indexing
    from 1 like https://en.wikipedia.org/wiki/General_MIDI#Program_change_events

    Here's some values that sound nice or at least interesting:
     - 4 sounds ok (some kind of rhodes piano)
     - 10 sounds great (music box?)
     - 11 and 12 are alright (vibraphone and marimba)
     - 21 kinda nice but needs to send note offs (accordion)
     - 75 acceptable pan flute
     - 79 alright ocarina
     - 92 sounds decent at higher octaves (glass armonica pad)
     - 108 kalimba
     - 115 wood block
     - 116 taiko drum
     - 122 ocean
     - 123 weirdass bird siren
    """
    if _queue:
        try:
            _queue.put(("prog", program, 0), False)
        except:
            pass
