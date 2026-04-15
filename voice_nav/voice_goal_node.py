#!/usr/bin/env python3
"""
voice_goal_node.py

Speech -> text -> command parser -> Nav2 NavigateToPose goal

Supported commands:
- "go to x 1.2 y -0.8"
- "navigate to x minus 0.5 y 2.0"
- "go to desk"
- "go home"
- "stop"
- "cancel navigation"

Optional:
- load waypoints from a YAML file
- use Google online speech recognition
- fallback test mode from terminal if audio deps are not installed

ROS 2 parameters:
- waypoint_file (str): optional YAML file
- sample_rate (int): microphone sample rate
- device (int): optional sounddevice input device index
- use_terminal_input (bool): if true, use stdin instead of microphone
- default_yaw (float): default yaw when only x,y are given
"""

import math
import os
import re
import sys
import json
import time
import queue
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, List

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.duration import Duration

from geometry_msgs.msg import PoseStamped, Quaternion
from nav2_msgs.action import NavigateToPose

# Optional imports
try:
    import yaml
except Exception:
    yaml = None

try:
    import speech_recognition as sr
except Exception:
    sr = None


# ----------------------------
# Data models
# ----------------------------

@dataclass
class Waypoint:
    x: float
    y: float
    yaw: float = 0.0


@dataclass
class VoiceConfig:
    waypoint_file: str = ""
    sample_rate: int = 16000
    device: Optional[int] = None
    use_terminal_input: bool = False
    default_yaw: float = 0.0
    command_poll_hz: float = 10.0


@dataclass
class ParsedCommand:
    kind: str
    pose: Optional[Waypoint] = None
    raw_text: str = ""


# ----------------------------
# Waypoint store
# ----------------------------

class WaypointStore:
    """
    Holds named waypoints.
    YAML format example:
    home:
      x: 0.0
      y: 0.0
      yaw: 0.0
    desk:
      x: 1.8
      y: -0.6
      yaw: 1.57
    """

    def __init__(self) -> None:
        self._waypoints: Dict[str, Waypoint] = {
            "home": Waypoint(0.0, 0.0, 0.0),
            "desk": Waypoint(1.8, -0.6, 1.57),
            "charger": Waypoint(-0.9, 2.1, 3.14),
        }

    def load_yaml(self, path: str) -> None:
        if not path:
            return
        if yaml is None:
            raise RuntimeError("PyYAML is not installed. Install with: pip install pyyaml")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Waypoint file does not exist: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        loaded: Dict[str, Waypoint] = {}
        for name, entry in data.items():
            if not isinstance(entry, dict):
                continue
            x = float(entry["x"])
            y = float(entry["y"])
            yaw = float(entry.get("yaw", 0.0))
            loaded[name.lower()] = Waypoint(x, y, yaw)

        if loaded:
            self._waypoints.update(loaded)

    def get(self, name: str) -> Optional[Waypoint]:
        return self._waypoints.get(name.lower())

    def names(self) -> List[str]:
        return sorted(self._waypoints.keys())


# ----------------------------
# Speech input backends
# ----------------------------

class BaseSpeechInput:
    """
    Produces recognized phrases asynchronously into a queue.
    """

    def __init__(self) -> None:
        self._queue: "queue.Queue[str]" = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def get_nowait(self) -> Optional[str]:
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    def _push_text(self, text: str) -> None:
        clean = text.strip()
        if clean:
            self._queue.put(clean)


class TerminalSpeechInput(BaseSpeechInput):
    """
    Simple fallback for testing:
    type commands in terminal while ros2 node is running.
    """

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                line = input("voice_nav> ").strip()
            except EOFError:
                break
            except Exception:
                time.sleep(0.1)
                continue

            if line:
                self._push_text(line)


class GoogleSpeechInput(BaseSpeechInput):
    """
    Online microphone speech recognition using Google Speech Recognition API.
    """

    def __init__(self, sample_rate: int = 16000, device: Optional[int] = None) -> None:
        super().__init__()
        if sr is None:
            raise RuntimeError("speech_recognition is not installed. Install with: pip install speechrecognition")
        self.recognizer = sr.Recognizer()
        # Note: speech_recognition uses pyaudio, device selection may be limited

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                with sr.Microphone() as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                    audio = self.recognizer.listen(source)
                    text = self.recognizer.recognize_google(audio, language='en-US')
                    self._push_text(text)
            except sr.UnknownValueError:
                pass  # Ignore unintelligible speech
            except sr.RequestError as e:
                self._push_text(f"__speech_error__ {e}")
                time.sleep(1)  # Avoid spamming API
            except Exception as e:
                self._push_text(f"__speech_error__ {e}")
                time.sleep(1)


# ----------------------------
# Command parsing
# ----------------------------

class CommandParser:
    """
    Converts recognized text into goal/cancel commands.
    """

    NUMBER_WORDS = {
        "zero": "0",
        "one": "1",
        "two": "2",
        "three": "3",
        "four": "4",
        "five": "5",
        "six": "6",
        "seven": "7",
        "eight": "8",
        "nine": "9",
        "ten": "10",
        "point": ".",
        "minus": "-",
        "negative": "-",
    }

    def __init__(self, waypoint_store: WaypointStore, default_yaw: float = 0.0) -> None:
        self.waypoint_store = waypoint_store
        self.default_yaw = default_yaw

    def parse(self, text: str) -> ParsedCommand:
        raw = text
        text = self._normalize_text(text)

        if text.startswith("__speech_error__"):
            return ParsedCommand(kind="speech_error", raw_text=raw)

        if any(phrase in text for phrase in ("stop", "cancel", "cancel navigation", "abort")):
            return ParsedCommand(kind="cancel", raw_text=raw)

        pose = self._parse_xy(text)
        if pose is not None:
            return ParsedCommand(kind="goal", pose=pose, raw_text=raw)

        for name in self.waypoint_store.names():
            # allow "go to desk", "navigate desk", etc.
            if re.search(rf"\b{name}\b", text):
                wp = self.waypoint_store.get(name)
                return ParsedCommand(kind="goal", pose=wp, raw_text=raw)

        return ParsedCommand(kind="unknown", raw_text=raw)

    def _normalize_text(self, text: str) -> str:
        text = text.lower().strip()
        text = text.replace(",", " ")
        text = text.replace("=", " ")
        text = re.sub(r"\s+", " ", text)

        # Replace number words with symbols when simple.
        # Example: "x minus 1 point 2 y 3"
        tokens = text.split()
        converted = []
        for token in tokens:
            converted.append(self.NUMBER_WORDS.get(token, token))
        text = " ".join(converted)

        # collapse spaces around signs/decimals a bit
        text = text.replace("- ", "-")
        text = text.replace(". ", ".")
        return text

    def _parse_xy(self, text: str) -> Optional[Waypoint]:
        """
        Handles:
        - go to x 1.2 y -0.8
        - navigate to x -1 y 2
        - x 0.5 y 0.25
        Optional yaw:
        - x 1 y 2 yaw 1.57
        """
        num = r"(-?\d+(?:\.\d+)?)"
        pattern = rf"\bx\s*{num}\s*\by\s*{num}(?:\s*\byaw\s*{num})?"
        m = re.search(pattern, text)
        if not m:
            return None

        x = float(m.group(1))
        y = float(m.group(2))
        yaw = float(m.group(3)) if m.group(3) is not None else self.default_yaw
        return Waypoint(x, y, yaw)


# ----------------------------
# Nav2 client wrapper
# ----------------------------

class Nav2GoalClient:
    """
    Thin wrapper around NavigateToPose action.
    """

    def __init__(self, node: Node) -> None:
        self.node = node
        self._client = ActionClient(node, NavigateToPose, "navigate_to_pose")
        self._goal_handle = None
        self._goal_lock = threading.Lock()

    def wait_for_server(self, timeout_sec: float = 5.0) -> bool:
        return self._client.wait_for_server(timeout_sec=timeout_sec)

    def send_goal(self, waypoint: Waypoint) -> None:
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = PoseStamped()
        goal_msg.pose.header.frame_id = "map"
        goal_msg.pose.header.stamp = self.node.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = waypoint.x
        goal_msg.pose.pose.position.y = waypoint.y
        goal_msg.pose.pose.position.z = 0.0
        goal_msg.pose.pose.orientation = self._yaw_to_quaternion(waypoint.yaw)

        self.node.get_logger().info(
            f"Sending Nav2 goal in map frame: x={waypoint.x:.3f}, y={waypoint.y:.3f}, yaw={waypoint.yaw:.3f}"
        )

        send_future = self._client.send_goal_async(
            goal_msg,
            feedback_callback=self._feedback_callback,
        )
        send_future.add_done_callback(self._goal_response_callback)

    def cancel_goal(self) -> None:
        with self._goal_lock:
            if self._goal_handle is None:
                self.node.get_logger().info("No active goal to cancel.")
                return
            cancel_future = self._goal_handle.cancel_goal_async()
            cancel_future.add_done_callback(self._cancel_done_callback)

    def _goal_response_callback(self, future) -> None:
        try:
            goal_handle = future.result()
        except Exception as e:
            self.node.get_logger().error(f"Failed sending goal: {e}")
            return

        if not goal_handle.accepted:
            self.node.get_logger().warn("Nav2 goal was rejected.")
            return

        with self._goal_lock:
            self._goal_handle = goal_handle

        self.node.get_logger().info("Nav2 goal accepted.")
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._result_callback)

    def _result_callback(self, future) -> None:
        try:
            result = future.result()
            status = result.status
        except Exception as e:
            self.node.get_logger().error(f"Error waiting for result: {e}")
            return

        self.node.get_logger().info(f"Navigation finished with status={status}.")
        with self._goal_lock:
            self._goal_handle = None

    def _cancel_done_callback(self, future) -> None:
        try:
            response = future.result()
            self.node.get_logger().info(f"Cancel response received: {response}")
        except Exception as e:
            self.node.get_logger().error(f"Cancel failed: {e}")

    def _feedback_callback(self, feedback_msg) -> None:
        feedback = feedback_msg.feedback
        remaining = getattr(feedback, "distance_remaining", None)
        nav_time = getattr(feedback, "navigation_time", None)

        parts = []
        if remaining is not None:
            parts.append(f"remaining={remaining:.2f}m")
        if nav_time is not None:
            secs = nav_time.sec + nav_time.nanosec * 1e-9
            parts.append(f"time={secs:.1f}s")

        if parts:
            self.node.get_logger().debug("Nav2 feedback: " + ", ".join(parts))

    @staticmethod
    def _yaw_to_quaternion(yaw: float) -> Quaternion:
        q = Quaternion()
        q.x = 0.0
        q.y = 0.0
        q.z = math.sin(yaw / 2.0)
        q.w = math.cos(yaw / 2.0)
        return q


# ----------------------------
# ROS node
# ----------------------------

class VoiceGoalNode(Node):
    def __init__(self) -> None:
        super().__init__("voice_goal_node")

        self.declare_parameter("waypoint_file", "")
        self.declare_parameter("sample_rate", 16000)
        self.declare_parameter("device", -1)
        self.declare_parameter("use_terminal_input", False)
        self.declare_parameter("default_yaw", 0.0)
        self.declare_parameter("command_poll_hz", 10.0)

        device_param = self.get_parameter("device").get_parameter_value().integer_value
        self.config = VoiceConfig(
            waypoint_file=self.get_parameter("waypoint_file").get_parameter_value().string_value,
            sample_rate=self.get_parameter("sample_rate").get_parameter_value().integer_value,
            device=None if device_param < 0 else int(device_param),
            use_terminal_input=self.get_parameter("use_terminal_input").get_parameter_value().bool_value,
            default_yaw=self.get_parameter("default_yaw").get_parameter_value().double_value,
            command_poll_hz=self.get_parameter("command_poll_hz").get_parameter_value().double_value,
        )

        self.waypoints = WaypointStore()
        if self.config.waypoint_file:
            try:
                self.waypoints.load_yaml(self.config.waypoint_file)
                self.get_logger().info(f"Loaded waypoints from: {self.config.waypoint_file}")
            except Exception as e:
                self.get_logger().error(f"Failed to load waypoint file: {e}")

        self.parser = CommandParser(self.waypoints, default_yaw=self.config.default_yaw)
        self.nav2 = Nav2GoalClient(self)

        self.speech: BaseSpeechInput = self._make_speech_backend()

        self.get_logger().info("Waiting for Nav2 action server...")
        if not self.nav2.wait_for_server(timeout_sec=10.0):
            self.get_logger().warn("NavigateToPose action server not ready yet. Node will continue waiting in background.")
        else:
            self.get_logger().info("NavigateToPose action server is available.")

        self.speech.start()

        period = 1.0 / max(self.config.command_poll_hz, 1.0)
        self.timer = self.create_timer(period, self._poll_commands)

        self.get_logger().info(f"Waypoints available: {', '.join(self.waypoints.names())}")
        if self.config.use_terminal_input:
            self.get_logger().info("Using terminal input mode.")
        else:
            self.get_logger().info("Using microphone speech mode.")

    def _make_speech_backend(self) -> BaseSpeechInput:
        if self.config.use_terminal_input:
            return TerminalSpeechInput()

        try:
            return GoogleSpeechInput(
                sample_rate=self.config.sample_rate,
                device=self.config.device,
            )
        except Exception as e:
            self.get_logger().warn(
                f"Falling back to terminal input because speech backend failed: {e}"
            )
            return TerminalSpeechInput()

    def _poll_commands(self) -> None:
        text = self.speech.get_nowait()
        if text is None:
            return

        self.get_logger().info(f"Heard: '{text}'")
        cmd = self.parser.parse(text)

        if cmd.kind == "speech_error":
            self.get_logger().error(f"Speech backend error: {cmd.raw_text}")
            return

        if cmd.kind == "cancel":
            self.get_logger().info("Cancel command received.")
            self.nav2.cancel_goal()
            return

        if cmd.kind == "goal" and cmd.pose is not None:
            if not self.nav2.wait_for_server(timeout_sec=1.0):
                self.get_logger().warn("Nav2 action server not available; cannot send goal.")
                return
            self.nav2.send_goal(cmd.pose)
            return

        self.get_logger().warn(f"Unknown command: '{cmd.raw_text}'")

    def destroy_node(self):
        try:
            self.speech.stop()
        except Exception:
            pass
        super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = VoiceGoalNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()