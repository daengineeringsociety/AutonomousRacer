import os
import time

# ==========================================
# HARDWARE SAFETY & MAPPING CONSTANTS
# ==========================================
PWM_CHIP_PATH = "/sys/class/pwm/pwmchip0"
PWM_PERIOD_NS = 20000000  # 50Hz (Standard for Servos/ESCs)

# Channel Mapping
THROTTLE_CHANNEL = 0
STEERING_CHANNEL = 1
LED_R_CHANNEL = 2
LED_G_CHANNEL = 3
LED_B_CHANNEL = 4

# Throttle Calibration (Inverted Logic)
THROTTLE_NEUTRAL = 1500000
THROTTLE_SAFE_MIN = 1400000  # Max safe forward (lower is faster)
THROTTLE_SAFE_MAX = 1600000  # Max safe reverse (higher is faster)

# Steering Calibration
STEERING_NEUTRAL = 1500000
STEERING_MIN = 1000000       # Extreme bound 1
STEERING_MAX = 2000000       # Extreme bound 2

# LED Calibration
LED_MIN_DUTY = 0
LED_MAX_DUTY = 20000000      # 100% duty cycle matches the period


class DeepRacerHardware:
    def __init__(self):
        """Initializes all PWM channels safely."""
        self._init_channel(THROTTLE_CHANNEL)
        self._init_channel(STEERING_CHANNEL)
        self._init_channel(LED_R_CHANNEL)
        self._init_channel(LED_G_CHANNEL)
        self._init_channel(LED_B_CHANNEL)
        
        # Arm the ESC and zero out LEDs on startup
        self.set_throttle(0.0)
        self.set_steering(0.0)
        self.set_led(0, 0, 0)
        time.sleep(2) # Give the ESC time to recognize the neutral signal

    def _init_channel(self, channel):
        """Safely exports and enables a PWM channel."""
        base_path = f"{PWM_CHIP_PATH}/pwm{channel}"
        
        # Only export if it hasn't been exported yet to avoid I/O errors
        if not os.path.exists(base_path):
            with open(f"{PWM_CHIP_PATH}/export", "w") as f:
                f.write(str(channel))
                
        # Give the OS a tiny fraction of a second to create the directories
        time.sleep(0.1) 
        
        self._write_sysfs(channel, "period", PWM_PERIOD_NS)
        self._write_sysfs(channel, "enable", 1)

    def _write_sysfs(self, channel, file, value):
        """Helper to write values to the sysfs interface."""
        path = f"{PWM_CHIP_PATH}/pwm{channel}/{file}"
        try:
            with open(path, "w") as f:
                f.write(str(int(value)))
        except IOError as e:
            print(f"Error writing to {path}: {e}")

    def set_throttle(self, power):
        """
        Sets the ESC throttle.
        :param power: Float from -1.0 (full safe reverse) to 1.0 (full safe forward)
        """
        # Clamp input between -1.0 and 1.0
        power = max(-1.0, min(1.0, power))
        
        # Calculate available range from neutral
        forward_range = THROTTLE_NEUTRAL - THROTTLE_SAFE_MIN
        reverse_range = THROTTLE_SAFE_MAX - THROTTLE_NEUTRAL
        
        if power > 0:
            # Forward: Subtract from neutral (inverted logic)
            target_ns = THROTTLE_NEUTRAL - (power * forward_range)
        else:
            # Reverse: Add to neutral (negative power becomes positive addition)
            target_ns = THROTTLE_NEUTRAL - (power * reverse_range)
            
        # Final hardware safety clamp before writing
        safe_ns = max(THROTTLE_SAFE_MIN, min(THROTTLE_SAFE_MAX, target_ns))
        self._write_sysfs(THROTTLE_CHANNEL, "duty_cycle", safe_ns)

    def set_steering(self, angle):
        """
        Sets the steering servo.
        :param angle: Float from -1.0 (left) to 1.0 (right)
        """
        # Clamp input between -1.0 and 1.0
        angle = max(-1.0, min(1.0, angle))
        
        # 500,000ns is the max deviation from the 1.5M neutral
        range_ns = 500000 
        target_ns = STEERING_NEUTRAL + (angle * range_ns)
        
        # Final hardware safety clamp
        safe_ns = max(STEERING_MIN, min(STEERING_MAX, target_ns))
        self._write_sysfs(STEERING_CHANNEL, "duty_cycle", safe_ns)

    def set_led(self, r, g, b):
        """
        Sets the rear RGB LED color.
        :param r, g, b: Integers from 0 to 255
        """
        # Clamp RGB values safely between 0 and 255
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        
        # Convert 0-255 scale to 0-20,000,000 nanosecond duty cycle
        r_ns = (r / 255.0) * LED_MAX_DUTY
        g_ns = (g / 255.0) * LED_MAX_DUTY
        b_ns = (b / 255.0) * LED_MAX_DUTY
        
        self._write_sysfs(LED_R_CHANNEL, "duty_cycle", r_ns)
        self._write_sysfs(LED_G_CHANNEL, "duty_cycle", g_ns)
        self._write_sysfs(LED_B_CHANNEL, "duty_cycle", b_ns)

    def cleanup(self):
        """Stops the motors and turns off the LEDs. Call this on exit."""
        self.set_throttle(0.0)
        self.set_steering(0.0)
        self.set_led(0, 0, 0)


# ==========================================
# USAGE EXAMPLE
# ==========================================
if __name__ == "__main__":
    car = DeepRacerHardware()
    
    try:
        print("Hardware initialized. Testing steering...")
        car.set_steering(-1.0)
        time.sleep(0.5)
        car.set_steering(1.0)
        time.sleep(0.5)
        car.set_steering(0.0)
        
        print("Testing LEDs...")
        car.set_led(255, 0, 0) # Red
        time.sleep(0.5)
        car.set_led(0, 255, 0) # Green
        time.sleep(0.5)
        car.set_led(0, 0, 255) # Blue
        time.sleep(0.5)
        car.set_led(128, 0, 128) # Purple
        
        print("Testing throttle (wheels must be off the ground!)...")
        car.set_throttle(0.5)  # 50% of the SAFE forward speed
        time.sleep(1)
        car.set_throttle(0.0)  # Stop
        
    except KeyboardInterrupt:
        print("\n Stop Triggered.")
    finally:
        print("Cleaning up hardware state...")
        car.cleanup()