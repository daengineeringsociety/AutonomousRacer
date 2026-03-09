#!/usr/bin/env python3
"""Interactive DeepRacer control helper.

Flow:
1) Ask user what to change (motor, LED, battery)
2) Validate inputs
3) Publish /cmd_vel for throttle/steering or call hardware setters for LEDs
4) Show battery level and change between reads
"""

from __future__ import annotations

import sys

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.qos import (QoSHistoryPolicy, QoSReliabilityPolicy, QoSProfile)

from deepracer_control.batteryLevel import get_bus_channel, read_battery_level
from deepracer_control.motorControl import DeepRacerHardware


class DeepracerInteractiveController(Node):
    """Single-file interactive script for manual control."""

    MAX_LINEAR_VELOCITY = 4.0 #arbitrary
    MAX_STEER_ANGLE = 0.523599 #arbitrary 

    def __init__(self):
        print("uwa!! roys super duper kawaii cool interactive control script desu~")
        super().__init__("deepracer_interactive_control")
        self._step = 0
        self._last_battery_level = None
        self._last_battery_raw = None

        qos = QoSProfile(
            depth=1,
            history=QoSHistoryPolicy.RMW_QOS_POLICY_HISTORY_KEEP_LAST,
            reliability=QoSReliabilityPolicy.RMW_QOS_POLICY_RELIABILITY_BEST_EFFORT,
        )
        self._publisher = self.create_publisher(Twist, "/cmd_vel", qos)

        self._steering = 0.0
        self._throttle = 0.0

        self._step_note("Initializing hardware interfaces for LEDs.")
        try:
            self._hardware = DeepRacerHardware()
            self._hardware_available = True
            self._step_note("LED hardware interface ready.")
        except Exception as exc:
            self._hardware_available = False
            self._hardware = None
            self._step_note(
                f"LED hardware init skipped ({exc})."
                " RGB actions will be reported but may not apply."
            )

        self._step_note("Detecting I2C bus for battery sensor.")
        try:
            self._battery_bus = get_bus_channel()
            self._step_note(f"Battery bus detected: i2c-{self._battery_bus}")
        except Exception as exc:
            self._battery_bus = None
            self._step_note(f"Battery bus detection failed: {exc}")

    def _step_note(self, message: str) -> None:
        self._step += 1
        print(f"[STEP {self._step:02d}] {message}")

    @staticmethod
    def _ask_float(prompt: str, min_value: float, max_value: float) -> float:
        while True:
            text = input(prompt).strip()
            try:
                value = float(text)
            except ValueError:
                print("bad number !! Try again.")
                continue
            if not (min_value <= value <= max_value):
                print(f"Value must be between {min_value} and {max_value}. u got this pookie.")
                continue
            return value

    @staticmethod
    def _ask_int(prompt: str, min_value: int, max_value: int) -> int:
        while True:
            text = input(prompt).strip()
            try:
                value = int(text)
            except ValueError:
                print("Invalid integer. Try again.")
                continue
            if not (min_value <= value <= max_value):
                print(f"Value must be between {min_value} and {max_value}.  u got this pookie.")
                continue
            return value

    @staticmethod
    def _parse_rgb(raw: str):
        parts = [x.strip() for x in raw.replace(",", " ").split() if x.strip()]
        if len(parts) != 3:
            raise ValueError("Need exactly three values. try again mf.")
        rgb = tuple(int(value) for value in parts)
        for channel in rgb:
            if not (0 <= channel <= 255):
                raise ValueError("RGB values must be between 0 and 255. try again mf.")
        return rgb

    def _publish_cmd_vel(self, throttle: float, steering: float) -> Twist:
        msg = Twist()
        msg.linear.x = throttle * self.MAX_LINEAR_VELOCITY
        msg.angular.z = steering * self.MAX_STEER_ANGLE
        self._step_note(
            f"Publishing /cmd_vel -> linear.x={msg.linear.x:.3f}, angular.z={msg.angular.z:.3f}"
        )
        self._publisher.publish(msg)
        rclpy.spin_once(self, timeout_sec=0.01)
        self._step_note("Publish complete.")
        return msg

    def _read_battery(self):
        self._step_note("Reading battery level from sensor.")
        if self._battery_bus is None:
            print("Battery bus is unavailable in this environment.")
            return

        raw, level = read_battery_level(self._battery_bus)
        if level == -1:
            print("Failed to read battery level.")
            return

        print(f"Battery raw hex: {hex(raw)} | level: {level}/11")

        if self._last_battery_level is not None:
            delta = level - self._last_battery_level
            raw_delta = None if self._last_battery_raw is None else raw - self._last_battery_raw
            if raw_delta is not None:
                print(f"Change since last check: level={delta:+d}, raw={raw_delta:+d}")
            else:
                print(f"Change since last check: level={delta:+d}, raw=None")
        else:
            print("No previous battery sample yet.")

        self._last_battery_level = level
        self._last_battery_raw = raw
        return raw, level

    def _set_rgb(self, r: int, g: int, b: int) -> None:
        self._step_note(f"Setting RGB to r={r}, g={g}, b={b}.")
        if not self._hardware_available:
            print("RGB hardware unavailable, skipping write.")
            return
        self._hardware.set_led(r, g, b)
        self._step_note("LED write complete.")

    def motor_control_menu(self) -> None:
        self._step_note("Entering motor control branch.")
        print("Motor options:")
        print("1) throttle only !!")
        print("2) steering only :3")
        print("3) both throttle and steering :D")
        mode = input("Select motor option (1-3): ").strip()

        if mode == "1":
            self._step_note("Requesting throttle value.")
            self._throttle = self._ask_float("Throttle (-1 reverse, 1 forward): ", -1.0, 1.0)
        elif mode == "2":
            self._step_note("Requesting steering value.")
            self._steering = self._ask_float("Steering (-1 left, 1 right): ", -1.0, 1.0)
        elif mode == "3":
            self._step_note("Requesting throttle and steering values.")
            self._throttle = self._ask_float("Throttle (-1 reverse, 1 forward): ", -1.0, 1.0)
            self._steering = self._ask_float("Steering (-1 left, 1 right): ", -1.0, 1.0)
        else:
            print("Unknown motor option.")
            return

        self._step_note(f"Normalized state -> throttle={self._throttle}, steering={self._steering}")
        self._publish_cmd_vel(self._throttle, self._steering)

    def rgb_menu(self) -> None:
        self._step_note("Entering RGB control branch.")
        print("Enter RGB as: r g b   (each 0-255)")
        while True:
            raw = input("RGB: ")
            try:
                r, g, b = self._parse_rgb(raw)
                self._set_rgb(r, g, b)
                break
            except ValueError as exc:
                print(f"{exc} Twy agwain.")

    def battery_menu(self) -> None:
        self._step_note("Entering battery check branch.")
        baseline = self._read_battery()
        if self._last_battery_level is None:
            return

        min_change = self._ask_int(
            "What level of change should I track? (0-11): ",
            0,
            11,
        )
        self._step_note(f"Configured change threshold: {min_change}")

        input("Press Enter after another update cycle to re-check battery...")
        after_raw_level = self._read_battery()
        if after_raw_level is None:
            return
        _, current_level = after_raw_level
        _, baseline_level = baseline
        change = abs(current_level - baseline_level)
        print(f"Observed level change from threshold point: {change} (last={baseline_level} -> current={current_level})")
        if change >= min_change:
            print(f"Change threshold met (>= {min_change}).")
        else:
            print(f"Change threshold not met (< {min_change}).")

    def run(self) -> None:
        self._step_note("Starting interactive control loop. Type 4 to quit.")
        try:
            while rclpy.ok():
                print("\nWhat should i do senpai change?")
                print("1) motor control (throttle/steering -> /cmd_vel)")
                print("2) RGB control (0-255 each)")
                print("3) battery level")
                print("4) exit")
                choice = input("Pick 1-4: ").strip()

                if choice == "1":
                    self.motor_control_menu()
                elif choice == "2":
                    self.rgb_menu()
                elif choice == "3":
                    self.battery_menu()
                elif choice == "4":
                    self._step_note("Exit selected.")
                    break
                else:
                    print("Invalid selection. Please choose 1, 2, 3, or 4. try again. try again. try again. try again.")
        finally:
            self._cleanup()

    def _cleanup(self):
        if self._hardware_available and self._hardware is not None:
            self._step_note("Stopping robot and clearing LEDs.")
            self._hardware.set_throttle(0.0)
            self._hardware.set_steering(0.0)
            self._hardware.set_led(0, 0, 0)
        self.destroy_node()


def main():
    rclpy.init(args=sys.argv)
    controller = DeepracerInteractiveController()
    try:
        controller.run()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received. Stopping.")
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
