#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist


class CmdVelPublisher(Node):



    def __init__(self):
        super().__init__('cmd_vel_input_node')

        self.publisher = self.create_publisher(Twist, '/cmd_vel', 10)

        self.get_logger().info("CmdVel input node started")
        self.get_logger().info("Commands:")
        self.get_logger().info("  forward <speed>")
        self.get_logger().info("  back <speed>")
        self.get_logger().info("  left <speed>")
        self.get_logger().info("  right <speed>")
        self.get_logger().info("  stop")
        self.get_logger().info("  quit")

    def publish_twist(self, lin_x=0.0, ang_z=0.0):
        msg = Twist()
        msg.linear.x = lin_x
        msg.angular.z = ang_z
        self.publisher.publish(msg)

    def run(self):
        angle = 0
        while rclpy.ok():

            cmd = input("> ").strip().lower().split()

            SteeringOffset = -0.025
            LinearOffset = 0.0
            

            if not cmd:
                continue

            if cmd[0] == "quit":
                break

            elif cmd[0] == "stop":
                self.publish_twist(0.0, 0.0)
                print("Robot stopped")

            elif cmd[0] == "forward":
                speed = float(cmd[1]) if len(cmd) > 1 else 0.5
                self.publish_twist((speed+LinearOffset), SteeringOffset+angle)

            elif cmd[0] == "back":
                speed = float(cmd[1]) if len(cmd) > 1 else 0.5
                self.publish_twist((-speed+LinearOffset), SteeringOffset+angle)

            elif cmd[0] == "left":
                speed = float(cmd[1]) if len(cmd) > 1 else 0.5
                angle = speed
                self.publish_twist(LinearOffset, (speed+SteeringOffset))

            elif cmd[0] == "right":
                speed = float(cmd[1]) if len(cmd) > 1 else 0.5
                angle = speed
                self.publish_twist(LinearOffset, (-speed+SteeringOffset))

            else:
                print("Unknown command")


def main(args=None):

    rclpy.init(args=args)

    node = CmdVelPublisher()

    try:
        node.run()
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
