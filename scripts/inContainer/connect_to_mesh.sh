#!/bin/bash
# You get the Join Code from the Husarnet Dashboard
sudo husarnet join ayanuddin2006a@gmail.com/bRqH6yMthD5WnssgLxmxye
sudo husarnet start

# 2. Generate the CycloneDDS XML for Husarnet
# This tool looks at the VPN and writes the correct IPv6 config to the file
husarnet-dds singleshot

# 3. Refresh the ROS Daemon
ros2 daemon stop
ros2 daemon start

echo "DAES Mesh Active. You can now talk to the DeepRacer."