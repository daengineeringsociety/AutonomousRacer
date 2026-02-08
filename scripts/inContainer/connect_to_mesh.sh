#!/bin/bash
# You get the Join Code from the Husarnet Dashboard
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file:///workspaces/deepracer_project/scripts/inContainer/husarnet_config.xml
sudo husarnet join ayanuddin2006a@gmail.com/bRqH6yMthD5WnssgLxmxye #Note add a hostname here for your computer is husarnet
sudo husarnet start

sleep 2
sudo husarnet daemon restart
sleep 2 # Give the interface time to breathe
husarnet-dds singleshot

# 3. Refresh the ROS Daemon
ros2 daemon stop
ros2 daemon start



echo "DAES Mesh Script ran"