#!/bin/bash
export TURTLEBOT3_MODEL=waffle
export GAZEBO_MODEL_PATH=$GAZEBO_MODEL_PATH:/opt/ros/foxy/share/turtlebot3_gazebo/models

# Crucial for Mac/Docker: Force software rendering to stop the "Bouncing"
export LIBGL_ALWAYS_SOFTWARE=1

ros2 launch nav2_bringup tb3_simulation_launch.py \
  headless:=True \
  use_rviz:=False \
  use_sim_time:=True \
  world:=/opt/ros/foxy/share/nav2_bringup/worlds/waffle.model \
  map:=/opt/ros/foxy/share/nav2_bringup/maps/turtlebot3_world.yaml