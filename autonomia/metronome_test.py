
import time
import metronome
import bluetooth


def metronome_test_main(bluetooth_addr):
    metronome.start()
    metronome.prog(11)

    bluetooth.start(bluetooth_addr)
    try:
        pending = []

        def pump_events():
            nonlocal pending
            for stamp, message_type, data in bluetooth.read():
                if message_type == "pulse":
                    _, rr_intervals = data
                    pending += rr_intervals
                else:
                    print(message_type, data)

        while len(pending) == 0:
            pump_events()
        interval = pending.pop(0)
        bpm = 60_000 // interval
        metronome.reset(bpm // metronome.meter, 1)
        print(bpm)
        time.sleep(interval / 1000)

        while True:
            while len(pending) == 0:
                pump_events()
            interval = pending.pop(0)
            bpm = 60_000 // interval
            metronome.tweak(bpm // metronome.meter, 1)
            print(bpm)
            time.sleep(interval / 1000)

    except KeyboardInterrupt:
        pass

    metronome.stop()
    bluetooth.stop()
