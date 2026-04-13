import os
import time

# Constants that rarely change
PWM_CHIP_PATH = "/sys/class/pwm/pwmchip0"
PWM_PERIOD_NS = 20000000
THROTTLE_CHANNEL = 0
STEERING_CHANNEL = 1
LED_R_CHANNEL = 2
LED_G_CHANNEL = 3
LED_B_CHANNEL = 4
LED_MAX_DUTY = 20000000

class DeepRacerHardware:
    def __init__(self, 
                 throttle_neutral=1500000, throttle_safe_min=1330000, throttle_safe_max=1580000,
                 steering_neutral=1500000, steering_min=1000000, steering_max=2000000):
        
        """Initializes all PWM channels with dynamic parameters."""
        # Save bounds dynamically
        self.t_neutral = throttle_neutral
        self.t_min = throttle_safe_min
        self.t_max = throttle_safe_max
        self.s_neutral = steering_neutral
        self.s_min = steering_min
        self.s_max = steering_max

        self._init_channel(THROTTLE_CHANNEL)
        self._init_channel(STEERING_CHANNEL)
        self._init_channel(LED_R_CHANNEL)
        self._init_channel(LED_G_CHANNEL)
        self._init_channel(LED_B_CHANNEL)
        
        self.set_throttle(0.0)
        self.set_steering(0.0)
        self.set_led(0, 0, 0)
        time.sleep(2)

    def _init_channel(self, channel):
        base_path = f"{PWM_CHIP_PATH}/pwm{channel}"
        if not os.path.exists(base_path):
            with open(f"{PWM_CHIP_PATH}/export", "w") as f:
                f.write(str(channel))
        time.sleep(0.1) 
        self._write_sysfs(channel, "period", PWM_PERIOD_NS)
        self._write_sysfs(channel, "enable", 1)

    def _write_sysfs(self, channel, file, value):
        path = f"{PWM_CHIP_PATH}/pwm{channel}/{file}"
        try:
            with open(path, "w") as f:
                f.write(str(int(value)))
        except IOError as e:
            print(f"Error writing to {path}: {e}")

    def set_throttle(self, power):
        power = max(-1.0, min(1.0, power))
        forward_range = self.t_neutral - self.t_min
        reverse_range = self.t_max - self.t_neutral
        
        if power > 0:
            target_ns = self.t_neutral - (power * forward_range)
        else:
            target_ns = self.t_neutral - (power * reverse_range)
            
        safe_ns = max(self.t_min, min(self.t_max, target_ns))
        print(safe_ns)
        self._write_sysfs(THROTTLE_CHANNEL, "duty_cycle", safe_ns)

    def set_steering(self, angle):
        angle = max(-1.0, min(1.0, angle))
        range_ns = 500000 
        target_ns = self.s_neutral + (angle * range_ns)
        safe_ns = max(self.s_min, min(self.s_max, target_ns))
        self._write_sysfs(STEERING_CHANNEL, "duty_cycle", safe_ns)

    def set_led(self, r, g, b):
        r_ns = (max(0, min(255, r)) / 255.0) * LED_MAX_DUTY
        g_ns = (max(0, min(255, g)) / 255.0) * LED_MAX_DUTY
        b_ns = (max(0, min(255, b)) / 255.0) * LED_MAX_DUTY
        self._write_sysfs(LED_R_CHANNEL, "duty_cycle", r_ns)
        self._write_sysfs(LED_G_CHANNEL, "duty_cycle", g_ns)
        self._write_sysfs(LED_B_CHANNEL, "duty_cycle", b_ns)

    def cleanup(self):
        self.set_throttle(0.0)
        self.set_steering(0.0)
        self.set_led(0, 0, 0)