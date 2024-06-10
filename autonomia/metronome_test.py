
import asyncio
from bleak import BleakClient
from bleak.exc import BleakError

import pygame.midi

import heart

next_t = 0


async def metronome(queue):
    pygame.midi.init()
    device_id = 0
    device_info = pygame.midi.get_device_info(device_id)
    while device_info != None:
        _, name, _, is_output, is_opened = device_info
        if name.startswith(b"TiMidity") and is_output == 1 and is_opened == 0:
            break
        else:
            device_id += 1
            device_info = pygame.midi.get_device_info(device_id)

    if not device_info:
        print("Can't find timidity.  Run `timidity -iA -Os` and try again.")
        return

    m = pygame.midi.Output(device_id, latency=5000, buffer_size=1024)

    async def play(note, velocity, rest=1):
        global next_t
        m.write([[[0x90, note, velocity], next_t]])
        next_t += rest
        m.write([[[0x80, note, 0], next_t - 1]])
        await asyncio.sleep(rest / 1000)

    # I think the program numbers all are general midi, but indexing from 0 instead of 1
    # so subtract 1 from everything on https://en.wikipedia.org/wiki/General_MIDI#Program_change_events

    # 4 sounds ok (some kind of rhodes piano)
    # 10 sounds great (music box?)
    # 11 and 12 are alright (vibraphone and marimba)
    # 21 kinda nice but needs to send note offs (accordion)
    # 75 acceptable pan flute
    # 79 alright ocarina
    # 92 sounds decent at higher octaves (glass armonica pad)
    # 116 taiko drum
    # 122 ocean
    # 123 weirdass bird siren
    program = 11
    m.write_short(0xC0, program, 0)

    meter = 4
    interval = int(1000 * (60 / 15))
    beat = interval // meter

    i = 0
    while True:
        interval = await queue.get()

        if i < meter * 2:
            if i == 0:
                next_t = pygame.midi.time()
            await play(60, 1, interval)
            print(" ", interval)

        elif i % meter == 0:
            await play(69, 127, interval)
            print("#", interval)

        else:
            await play(60, 90, interval)
            print("+", interval)

        i += 1


async def heart_monitor(queue, device_address):
    first_connection = True
    reconnect = True

    async def callback(sender, packet):
        bpm, rr_intervals = heart.decode(packet)
        if rr_intervals:
            for rest in rr_intervals:
                await queue.put(rest)
        else:
            print("RR interval missing.")
            reconnect = True

    while reconnect == True:
        reconnect = False
        if first_connection:
            first_connection = False
        else:
            print("Attempting to reconnect.")

        try:
            async with BleakClient(device_address) as client:

                await client.start_notify(heart.HRM_CHARACTERISTIC, callback)
                try:
                    while not reconnect:
                        await asyncio.sleep(1.0)
                        if not client.is_connected:
                            print("Connection to heart monitor lost.")
                            reconnect = True
                except KeyboardInterrupt:
                    reconnect = False
                if client.is_connected:
                    await client.stop_notify(HRM_CHARACTERISTIC)
        except BleakError as error:
            print(error)
            await asyncio.sleep(0.1)


async def metronome_setup(bluetooth_addr):
    queue = asyncio.Queue()
    player = asyncio.create_task(metronome(queue))

    await heart_monitor(queue, bluetooth_addr)
    await queue.join()
    player.cancel()


def metronome_test_main(bluetooth_addr):
    if bluetooth_addr:
        asyncio.run(metronome_setup(bluetooth_addr))
    else:
        print("no bluetooth address specified")
