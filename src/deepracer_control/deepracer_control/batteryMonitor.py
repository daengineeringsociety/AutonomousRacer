import os
import smbus2

BATDEV_ID = "0000:00:17.3"
I2C_SYS_PATH = "/sys/class/i2c-dev/"
SLAVE_ADDR = 0x3f
REGISTER_ADDR = 0x03

LEVEL_MAP = [
    (0xec, 11), (0xe0, 10), (0xd9, 9), (0xd3, 8),
    (0xcf, 7),  (0xcb, 6),  (0xc8, 5), (0xc5, 4),
    (0xc3, 3),  (0xc0, 2),  (0xb4, 1), (0x8c, 0)
]

class BatteryMonitor:
    def __init__(self):
        self.bus_channel = self._get_bus_channel()

    def _get_bus_channel(self):
        """Dynamically finds the I2C bus channel."""
        bus_channel = 7  # Default fallback
        try:
            for entry in os.listdir(I2C_SYS_PATH):
                full_path = os.path.join(I2C_SYS_PATH, entry)
                if os.path.islink(full_path):
                    symlink_target = os.readlink(full_path)
                    if BATDEV_ID in symlink_target:
                        bus_channel = int(entry.split('-')[1])
                        break
        except Exception:
            pass
        return bus_channel

    def read_level(self):
        """Returns the 0-11 battery level, or -1 on error."""
        try:
            with smbus2.SMBus(self.bus_channel) as bus:
                level_byte = bus.read_byte_data(SLAVE_ADDR, REGISTER_ADDR)
                for threshold, level in LEVEL_MAP:
                    if level_byte >= threshold:
                        return level
                return 0
        except Exception:
            return -1