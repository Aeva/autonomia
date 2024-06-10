
import asyncio
from bleak import BleakClient
from bleak.exc import BleakError

HRM_CHARACTERISTIC = "00002a37-0000-1000-8000-00805f9b34fb"
HEART_RATE_VALUE_FORMAT_BIT = 0b_0000_0001
SENSOR_CONTACT_STATUS_BIT   = 0b_0000_0010
SENSOR_CONTACT_SUPPORT_BIT  = 0b_0000_0100
ENERGY_EXPENDED_STATUS_BIT  = 0b_0000_1000
RR_INTERVAL_BIT             = 0b_0001_0000

reconnect = True


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


def heart_event(sender, packet):
    global reconnect
    bpm, rr_intervals = decode(packet)

    minute = 60 * 1000

    if rr_intervals and len(rr_intervals) > 0:
        for rr_interval in rr_intervals:
            equiv_bpm = minute / rr_interval
            print(f"{rr_interval} ms -> {round(equiv_bpm, 2)} bpm vs {bpm} bpm")

    else:
        print(f"bpm = {bpm}")
        reconnect = True


async def bpm_logger(device_address):
    global reconnect

    first_connection = True

    while reconnect == True:
        reconnect = False
        if first_connection:
            first_connection = False
        else:
            print("an error occurred.  attempting to reconnect.")

        try:
            async with BleakClient(device_address) as client:

                await client.start_notify(HRM_CHARACTERISTIC, heart_event)
                try:
                    while not reconnect:
                        await asyncio.sleep(0.1)
                        if not client.is_connected:
                            print("disconnected?")
                            reconnect = True
                except KeyboardInterrupt:
                    pass
                if client.is_connected:
                    await client.stop_notify(HRM_CHARACTERISTIC)
        except BleakError as error:
            print(error)
            await asyncio.sleep(0.1)


def bpm_debug_main(device_address):
    if device_address:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(bpm_logger(device_address))
    else:
        print("no bluetooth address specified")
