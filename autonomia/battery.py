
import asyncio
from bleak import BleakClient

BATTERY_LEVEL_CHARACTERISTIC = "00002a19-0000-1000-8000-00805f9b34fb"


async def query_battery(device_address):
    async with BleakClient(device_address) as client:
        print(f"bluetooth device connected: {device_address}")
        battery_level = await client.read_gatt_char(BATTERY_LEVEL_CHARACTERISTIC)
    return int.from_bytes(battery_level, byteorder='little')


def battery_main(device_address):
    if device_address:
        battery_level = asyncio.run(query_battery(device_address))
        print(f"Battery is at {battery_level}%")
    else:
        print("no bluetooth address specified")
