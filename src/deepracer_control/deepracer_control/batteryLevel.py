import os
import smbus2

# ==========================================
# HARDWARE CONSTANTS
# ==========================================
BATDEV_ID = "0000:00:17.3"
I2C_SYS_PATH = "/sys/class/i2c-dev/"
SLAVE_ADDR = 0x3f
REGISTER_ADDR = 0x03

# Pegatron mapping thresholds: (Hex Threshold, Battery Level 0-11)
LEVEL_MAP = [
    (0xec, 11), (0xe0, 10), (0xd9, 9), (0xd3, 8),
    (0xcf, 7),  (0xcb, 6),  (0xc8, 5), (0xc5, 4),
    (0xc3, 3),  (0xc0, 2),  (0xb4, 1), (0x8c, 0)
]

def get_bus_channel():
    """Dynamically finds the I2C bus channel associated with the battery."""
    bus_channel = 7  # Default fallback from older DeepRacer releases
    
    try:
        # Replicates the C++ directory iteration and symlink reading
        for entry in os.listdir(I2C_SYS_PATH):
            full_path = os.path.join(I2C_SYS_PATH, entry)
            
            if os.path.islink(full_path):
                symlink_target = os.readlink(full_path)
                
                # Check if the symlink points to our target PCI device
                if BATDEV_ID in symlink_target:
                    # entry is usually formatted like 'i2c-7'
                    bus_channel = int(entry.split('-')[1])
                    break
    except Exception as e:
        print(f"Error finding bus channel: {e}")
        
    return bus_channel

def read_battery_level(bus_channel):
    """Reads the raw byte via I2C and maps it to the 0-11 level."""
    try:
        with smbus2.SMBus(bus_channel) as bus:
            # Read 1 byte from the register
            level_byte = bus.read_byte_data(SLAVE_ADDR, REGISTER_ADDR)
            
            battery_level = -1
            # Iterate through the map to find the correct threshold
            for threshold, level in LEVEL_MAP:
                if level_byte >= threshold:
                    battery_level = level
                    break
                    
            return level_byte, battery_level
            
    except PermissionError:
        print("Permission denied: Run with sudo or check Docker privileges.")
        return -1, -1
    except Exception as e:
        print(f"I2C Read Error: {e}")
        return -1, -1

# ==========================================
# EXECUTION
# ==========================================
if __name__ == "__main__":
    print("Initializing Battery Monitor...")
    
    channel = get_bus_channel()
    print(f"Found battery on I2C bus channel: {channel}")
    
    raw_byte, level = read_battery_level(channel)
    
    if level != -1:
        print(f"Current battery_life byte: {hex(raw_byte)} | Level: {level}/11")
    else:
        print("Failed to read battery level.")