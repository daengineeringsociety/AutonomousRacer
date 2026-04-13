import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

from deepracer_control.motorControl import DeepRacerHardware
from deepracer_control.batteryMonitor import BatteryMonitor

class CmdVelToHardwareNode(Node):
    def __init__(self):
        super().__init__('cmd_vel_node')
        self.get_logger().info("Loading Parameters...")

        # DECLARE PARAMETERS
        self.declare_parameter('angular_scaler', 1.12)
        self.declare_parameter('linear_multiplier', 2.0)
        self.declare_parameter('forward_deadband', 0.70)
        self.declare_parameter('reverse_deadband', 0.80)
        
        self.declare_parameter('throttle_neutral', 1500000)
        self.declare_parameter('throttle_safe_min', 1330000)
        self.declare_parameter('throttle_safe_max', 1580000)
        self.declare_parameter('steering_neutral', 1500000)
        self.declare_parameter('steering_min', 1000000)
        self.declare_parameter('steering_max', 2000000)

        # INITIALIZE HARDWARE
        self.car = DeepRacerHardware(
            throttle_neutral=self.get_parameter('throttle_neutral').value,
            throttle_safe_min=self.get_parameter('throttle_safe_min').value,
            throttle_safe_max=self.get_parameter('throttle_safe_max').value,
            steering_neutral=self.get_parameter('steering_neutral').value,
            steering_min=self.get_parameter('steering_min').value,
            steering_max=self.get_parameter('steering_max').value
        )
        
        self.battery = BatteryMonitor()
        self.battery_compensation = 1.0 # 1.0 means 100% (Full Battery, no boost needed)
        # (Inside __init__, right below self.battery_compensation = 1.0)
        self.battery_history = [11, 11, 11, 11, 11] # Assume full battery on boot
        
        # 🚀 THE BACKGROUND BATTERY CHECKER (Runs every 5 seconds)
        self.battery_timer = self.create_timer(5.0, self.update_battery_compensation)
        
        self.subscription = self.create_subscription(Twist, '/cmd_vel', self.cmdvel_callback, 10)
        self.get_logger().info("Hardware Armed. Listening to /cmd_vel...")
        self.car.set_led(0, 255, 0)

    def update_battery_compensation(self):
        """
        Calculates throttle boost while filtering out load-induced voltage sag.
        """
        raw_level = self.battery.read_level()
        
        if raw_level == -1:
            return # I2C error, skip this cycle

        # 1. THE SAGE FILTER: Add to memory, keep only the last 5 readings (25 seconds)
        self.battery_history.append(raw_level)
        if len(self.battery_history) > 5:
            self.battery_history.pop(0)
            
        # 2. Grab the highest reading in our recent memory to ignore the fake sags
        true_level = max(self.battery_history)

        # Baseline: Level 10 or 11 needs no boost (1.0x)
        if true_level >= 10:
            self.battery_compensation = 1
        # Critical: Level 6 or below gets a massive boost (2.0x) to overcome voltage drop
        elif true_level <= 6:
            self.battery_compensation = 1.05
        # Gradient: Smoothly scale between 1.0x and 2.0x for levels 7, 8, 9
        else:
            self.battery_compensation = 1 + ((10 - true_level) * 0.01)

        self.get_logger().info(f"Battery: {true_level}/11 (Raw: {raw_level}) | Applying {self.battery_compensation}x Throttle Boost")

    def cmdvel_callback(self, msg):
        target_linear = msg.linear.x
        target_angular = msg.angular.z - 0.02

        ang_scaler = self.get_parameter('angular_scaler').value
        lin_mult = self.get_parameter('linear_multiplier').value
        fwd_deadband = self.get_parameter('forward_deadband').value
        rev_deadband = self.get_parameter('reverse_deadband').value

        pwm_throttle = 0.0
        
        # Apply the battery compensation dynamically to both the multiplier AND the deadband
        # (Because lower voltage means you need a higher initial PWM kick just to start rolling)
        boosted_lin_mult = lin_mult * self.battery_compensation
        boosted_fwd_deadband = min(0.95, fwd_deadband * self.battery_compensation)
        boosted_rev_deadband = min(0.95, rev_deadband * self.battery_compensation)

        if target_linear > 0.0:
            pwm_throttle = max(boosted_fwd_deadband, target_linear * boosted_lin_mult) 
        elif target_linear < 0.0:
            pwm_throttle = min(-boosted_rev_deadband, target_linear * boosted_lin_mult)
            
        pwm_throttle = max(-1.0, min(1.0, pwm_throttle))
        pwm_angle = target_angular * ang_scaler
        
        self.car.set_throttle(pwm_throttle)
        self.car.set_steering(pwm_angle)

        if target_linear < 0:
            self.car.set_led(255, 0, 0)
        elif target_linear > 0:
            self.car.set_led(0, 0, 255)
        elif target_angular != 0:
            self.car.set_led(255, 255, 0)
        else:
            self.car.set_led(0, 50, 0)

def main(args=None):
    rclpy.init(args=args)
    node = CmdVelToHardwareNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.car.cleanup()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()