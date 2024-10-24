import logging
from glucometerutils import common, driver, exceptions

class Device:
    def __init__(self, device_location, device_driver):
        try:
            self.requested_driver = driver.load_driver(device_driver)
        except ImportError as e:
            logging.error(
                'Error importing driver "%s":\n%s', device_driver, e
            )
            return

        self.device = self.requested_driver.device(device_location)

    def connect(self):
        self.device.connect()

    def disconnect(self):
        self.device.disconnect()

    def get_device_info(self):
        return self.device.get_meter_info()

    def get_readings(self):
        return self.device.get_readings()
