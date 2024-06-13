
import multiprocessing
import time

import asyncio
from bleak import BleakClient
from bleak import BleakScanner
from bleak.exc import BleakError

BATTERY_LEVEL_CHARACTERISTIC = "00002a19-0000-1000-8000-00805f9b34fb"

HRM_CHARACTERISTIC = "00002a37-0000-1000-8000-00805f9b34fb"
HEART_RATE_VALUE_FORMAT_BIT = 0b_0000_0001
SENSOR_CONTACT_STATUS_BIT   = 0b_0000_0010
SENSOR_CONTACT_SUPPORT_BIT  = 0b_0000_0100
ENERGY_EXPENDED_STATUS_BIT  = 0b_0000_1000
RR_INTERVAL_BIT             = 0b_0001_0000


_proc = None
_command_queue = None
_event_queue = None


def decode(packet):
    flags = packet[0]

    bpm_offset = 1
    bpm_bytes = 1 + (flags & HEART_RATE_VALUE_FORMAT_BIT)

    energy_offset = bpm_offset + bpm_bytes
    energy_bytes = (flags & ENERGY_EXPENDED_STATUS_BIT) >> 2

    rr_offset = energy_offset + energy_bytes
    rr_bytes = 2
    rr_count = (len(packet) - rr_offset) // rr_bytes

    bpm = int.from_bytes(packet[bpm_offset:bpm_offset + bpm_bytes], 'little')
    rr_intervals = None

    if (flags & RR_INTERVAL_BIT) == RR_INTERVAL_BIT:
        rr_intervals = [
            int.from_bytes(
                packet[rr_offset + rr_bytes * i:rr_offset + rr_bytes * (i+1)],
                'little')
            for i in range(rr_count)]

    return bpm, rr_intervals


async def heart_monitor_runner(command_queue, event_queue, device_address):
    reconnect = True

    def heart_event(sender, packet):
        nonlocal reconnect
        nonlocal event_queue
        bpm, rr_intervals = decode(packet)

        if not (rr_intervals and len(rr_intervals) > 0):
            event_queue.put((time.time(), "status", "reconnecting: missing rr_intervals"))
            reconnect = True
        else:
            event_queue.put((time.time(), "pulse", (bpm, rr_intervals)))

    while reconnect == True:
        reconnect = False
        try:
            async with BleakClient(device_address) as client:
                await client.start_notify(HRM_CHARACTERISTIC, heart_event)

                try:
                    battery_level = await client.read_gatt_char(BATTERY_LEVEL_CHARACTERISTIC)
                    battery_level = int.from_bytes(battery_level, byteorder='little')
                    event_queue.put((time.time(), "battery", battery_level))

                    while not reconnect:
                        if not client.is_connected:
                            event_queue.put((time.time(), "status", "reconnecting: connection lost"))
                            reconnect = True
                            break

                        try:
                            packet = command_queue.get_nowait()
                        except:
                            packet = None

                        if packet and packet[0] == "halt":
                            event_queue.put((time.time(), "status", "halt requested by application"))
                            reconnect = False
                            break

                        await asyncio.sleep(0.1)
                except Exception as e:
                    event_queue.put((time.time(), "fatal", e))

                if client.is_connected:
                    await client.stop_notify(HRM_CHARACTERISTIC)

        except BleakError as error:
            event_queue.put((time.time(), "fatal", error))
            await asyncio.sleep(0.1)


def heart_monitor_proc(command_queue, event_queue, device_address):
    """
    Entry point for the metronome subprocess.
    """

    loop = asyncio.get_event_loop()
    loop.run_until_complete(heart_monitor_runner(command_queue, event_queue, device_address))


def start(device_address):
    """
    Start the metronome subprocess if one is not running.
    """
    global _proc
    global _command_queue
    global _event_queue

    if not _proc:
        ctx = multiprocessing.get_context('spawn')
        _command_queue = ctx.Queue()
        _event_queue = ctx.Queue()
        _proc = ctx.Process(target=heart_monitor_proc, args=(_command_queue, _event_queue, device_address))
        _proc.start()


def stop():
    """
    Halt the metronome subprocess if one is running.
    """
    global _proc
    global _command_queue
    global _event_queue

    if _proc:
        _command_queue.put("halt")
        _proc.join()

        _command_queue = None
        _event_queue = None
        _proc = None


def read():
    global _event_queue
    messages = []
    if _event_queue:
        while True:
            try:
                event = _event_queue.get_nowait()
            except:
                break
            messages.append(event)
    return messages


def scan(timeout=5):
    device_scan = {}

    async def inner():
        def callback(device, info):
            if info.service_uuids.count("0000180d-0000-1000-8000-00805f9b34fb"):
                address = device.address
                if not device_scan.get(address):
                    device_scan[address] = info.local_name

        scanner = BleakScanner(callback)
        await scanner.start()
        await asyncio.sleep(timeout)
        await scanner.stop()

    asyncio.run(inner())
    return device_scan


def debug_main(bluetooth_addr):
    start(bluetooth_addr)
    try:
        while True:
            for event in read():
                print(event)
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    stop()
