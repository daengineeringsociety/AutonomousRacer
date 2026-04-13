# Autonomous ARKit Deepracer - De Anza Engineering Society 

[![ROS 2 - Foxy](https://img.shields.io/badge/ROS_2-Foxy-22314E?logo=ros)](https://docs.ros.org/en/foxy/index.html)
[![Swift - ARKit](https://img.shields.io/badge/Swift-ARKit-F05138?logo=swift)](https://developer.apple.com/augmented-reality/)
[![Docker - Dev-Containers/Deployment](https://img.shields.io/badge/Docker-DevContainers-2496ED?logo=docker)](https://www.docker.com/)
[![Linux - Ubuntu](https://img.shields.io/badge/Linux-Ubuntu-E95420?logo=ubuntu)](https://ubuntu.com/)

## Project Lead: Ayan Syed

https://github.com/user-attachments/assets/a10af9fe-2d20-4095-ba1a-e8fc7d5d6b5e


 

The **De Anza Engineering Society (DAES) AutonomousRacer** project transforms a standard AWS DeepRacer chassis into a fully autonomous, ARKit-tracked, ROS 2-driven Ackermann vehicle. 


## 🎯 Project Goal
To engineer a modular, scalable, and low-latency autonomous driving stack that seamlessly bridges edge-device perception (iOS ARKit) with heavy-duty motion planning (ROS 2 Nav2) to control physical Ackermann steering hardware in real-time.

## 🧠 System Architecture

The AutonomousRacer stack is divided into three core subsystems:

### 1. Low-Latency Perception & Localization (VIO)
* **Custom ARKit-to-ROS 2 Bridge:** A native iOS Swift application that extracts 6-DOF odometry from ARKit.
* **60Hz Telemetry:** Stripped of heavy RGB and depth payloads, the app streams pure transformation matrices over high-speed UDP, providing the ROS 2 TF tree with zero-latency, sub-millimeter positional tracking.
* **Transform Corrections:** Python bridging nodes handle Euler angle mapping between the iOS right-hand coordinate system and the ROS 2 standard base links.

* **Pre-mapping**: Before navigation can take place, the iPhone can be independently moved around the room to generate a 2D Map of the room using RTABMAP VSLAM. The iOS app has functionality to stream depth, RGB, IMU, imu and more streams of data from the iPhone. Explore https://github.com/ion206/ARKit-to-ROS-Bridge-V2 to learn more!



### 2. The Brain (Nav2 & SmacPlanner)
* **Grid-Based Dubin Planning:** Utilizes `SmacPlanner` tuned specifically for Ackermann kinematics on the Deepracer. 
* **Regulated Pure Pursuit:** Dynamically calculates lookahead distances and approach speeds to smoothly guide the chassis through tight indoor corridors.

### 3. Hardware Integration & Deadband Compensation
Moving beyond standard simulation environments, this project tackles real-world hardware integration challenges—including dynamic voltage sag, ESC deadbands, and zero-latency visual-inertial odometry (VIO)—to achieve reliable indoor autonomous navigation.

* **Direct PWM Control:** Bypasses default AWS daemons to directly write to `/sys/class/pwm/pwmchip0`, controlling the steering servo and Electronic Speed Controller (ESC).
* **Hardware Deadband Compensator:** An intelligent software layer that translates Nav2's `m/s` velocity requests into PWM duty cycles, ensuring the motor receives enough baseline torque to overcome static friction without stalling.
* **Dynamic Voltage Sag Filter:** Uses I2C (`smbus2`) to monitor the battery register. Because the motor draws heavy amps under load (causing temporary voltage drops), the node utilizes a 25-second **Rolling Maximum Filter** to calculate true battery life and dynamically scale the PWM multipliers, ensuring consistent physical speed regardless of battery charge.

## 🛠️ Development & Deployment Workflow

This project utilizes a highly reproducible **DevContainer to Docker** pipeline:
1. **DevContainers:** Development is handled inside VS Code DevContainers, ensuring every contributor has a perfectly synced ROS 2 Foxy environment without polluting their host machine. This allows devs to experiment with Navigation, VSLAM, and other ROS2 features relevant to the vehicle without worrying about resource constraints or the vehicle itself.
2. **Production Deployment:** For actual physical runs, the environment is packaged into a standalone Docker container deployed directly onto the DeepRacer's Ubuntu compute module, complete with hardware-level I2C and sysfs PWM privileges, and relevant networking ports for UDP/TCP communication in and out of the compute stack.

## 📂 Repository Structure
* All Ros2 packages are found in `src/`
* `/deepracer_control`: Core nodes for translating `cmd_vel` to PWM, deadband compensation, and I2C battery monitoring.
* `/deepracer_init`: Master launch files and AWS bridge initializers.
* `/arkit_ros2_bridge`: The high-speed UDP listener and TF tree broadcaster.

* Various Docker and Vehicle Control Scripts are found in `/scripts`.
