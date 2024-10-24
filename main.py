#!/usr/bin/env python3
"""
Example for a BLE 4.0 Server using a GATT dictionary of services and
characteristics
"""
import sys
import struct
import glucolib
import uuid
import logging
import asyncio
import threading

from typing import Any, Dict, Union

from bless import (  # type: ignore
    BlessServer,
    BlessGATTCharacteristic,
    GATTCharacteristicProperties,
    GATTAttributePermissions,
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(name=__name__)

trigger: Union[asyncio.Event, threading.Event]
if sys.platform in ["darwin", "win32"]:
    trigger = threading.Event()
else:
    trigger = asyncio.Event()

GET_READING_CHAR = ("51FF12BB-3ED8-46E5-B4F9-D64E2FEC021B")
NUM_READING_CHAR = ("bfc0c92f-317d-4ba9-976b-cc11ce77b4ca")
SERVICE_UUID = ("A07498CA-AD5B-474E-940D-16F1FBE7E8CD")
glucometer = glucolib.Device("/dev/sda", "otverio2015")
print("connecting")
glucometer.connect()


readingz = [i for i in glucometer.get_readings()]
print("info:", glucometer.get_device_info())

def read_request(characteristic: BlessGATTCharacteristic, **kwargs) -> bytearray:
    logger.debug(f"Reading {characteristic.uuid}")
    if (characteristic.uuid == NUM_READING_CHAR):
        logger.debug(f"CAUGHT NUM READING")
        readingz = [i for i in glucometer.get_readings()]
        val = len(readingz)
        print("val to encode:", val)
        ret = bytearray(list(map(int, struct.pack('<Q', val))))
        print('returning', ret)
        return ret
    return (characteristic.value)

def write_request(characteristic: BlessGATTCharacteristic, value: Any, **kwargs):
    characteristic.value = value
    logger.debug(f"Setting char value for {characteristic.uuid}")
    if (int(value[0]) < len(readingz)):
        characteristic.value = bytearray(str(readingz[int(value[0])]), "utf-8")

async def run(loop):
    trigger.clear()

    # Instantiate the server
    gatt: Dict = {
        SERVICE_UUID: {
            GET_READING_CHAR: {
                "Properties": (
                    GATTCharacteristicProperties.read
                    | GATTCharacteristicProperties.write
                    | GATTCharacteristicProperties.indicate
                ),
                "Permissions": (
                    GATTAttributePermissions.readable
                    | GATTAttributePermissions.writeable
                ),
                "Value": None,
            },
            NUM_READING_CHAR: {
                "Properties": GATTCharacteristicProperties.read | GATTCharacteristicProperties.indicate,
                "Permissions": GATTAttributePermissions.readable,
                "Value": bytearray(b"\x69"),
            }
        },
    }
    my_service_name = "Gluconnect Service"
    server = BlessServer(name=my_service_name, loop=loop)
    server.read_request_func = read_request
    server.write_request_func = write_request

    await server.add_gatt(gatt)
    await server.start()

    logger.debug(server.get_characteristic(GET_READING_CHAR))
    logger.debug("Advertising")
    if trigger.__module__ == "threading":
        trigger.wait()
    else:
        await trigger.wait()
    await asyncio.sleep(2)

    logger.debug("Updating")
    server.get_characteristic("51FF12BB-3ED8-46E5-B4F9-D64E2FEC021B").value = bytearray(
        b"i"
    )
    server.update_value(
        "A07498CA-AD5B-474E-940D-16F1FBE7E8CD", "51FF12BB-3ED8-46E5-B4F9-D64E2FEC021B"
    )
    await asyncio.sleep(5)
    await server.stop()


loop = asyncio.get_event_loop()
loop.run_until_complete(run(loop))
