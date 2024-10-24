#!/usr/bin/env python3
"""
Gluconnect Server
"""
import sys
import json
import struct
import glucolib
import uuid
import logging
import asyncio
import threading
from glucometerutils import common

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

GET_READING_CHAR = ("51ff12bb-3ed8-46e5-b4f9-d64e2fec021b")
NUM_READING_CHAR = ("bfc0c92f-317d-4ba9-976b-cc11ce77b4ca")
SERVICE_UUID = ("a07498ca-ad5b-474e-940d-16f1fbe7e8cd")

glucometer = glucolib.Device("/dev/sda", "otverio2015")

print("connecting...")
glucometer.connect()

readings = glucometer.get_readings()
reading_cache = list(readings)

print("info:", glucometer.get_device_info())

def read_request(characteristic: BlessGATTCharacteristic, **kwargs) -> bytearray:
    logger.debug(f"Reading {characteristic.uuid}")
    if (characteristic.uuid == NUM_READING_CHAR):
        logger.debug(f"CAUGHT NUM READING")
        val = len(reading_cache)
        print("val to encode:", val)

        ret = bytearray(val.to_bytes(8, byteorder="little", signed = False))
        print('returning', ret)

        return ret
    return (characteristic.value)

def write_request(characteristic: BlessGATTCharacteristic, value: Any, **kwargs):
    characteristic.value = value
    logger.debug(f"Setting char value for {characteristic.uuid}")
    if (int(value[0]) < len(reading_cache)):
        reading = reading_cache[int(value[0])]
        out = {
            "time": reading.timestamp.isoformat(),
            "value": reading.get_value_as(common.Unit.MG_DL),
            "meal": reading.meal.value,
            "comment": reading.comment,
            "measure_method": reading.measure_method.value,
            "extra_data": reading.extra_data,
        }
        characteristic.value = bytearray(json.dumps(out), "utf-8")
    else:
        characteristic.value = bytearray(b"")

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

    #await asyncio.sleep(2)
#
    #logger.debug("Updating")
    #server.get_characteristic("51FF12BB-3ED8-46E5-B4F9-D64E2FEC021B").value = bytearray(
        #b"i"
    #)
    #server.update_value(
        #"A07498CA-AD5B-474E-940D-16F1FBE7E8CD", "51FF12BB-3ED8-46E5-B4F9-D64E2FEC021B"
    #)
    #await asyncio.sleep(5)
    await server.stop()


loop = asyncio.get_event_loop()
loop.run_until_complete(run(loop))
