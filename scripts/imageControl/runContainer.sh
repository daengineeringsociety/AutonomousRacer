#!/bin/bash
cd /home/deepracer/deepracer/AutonomousRacer
echo "Running: autonomousracer_devcontainer_ros_dev-1"
docker run -it --rm   --name autonomousracer_devcontainer_ros_dev-1   --privileged   --network host   --cap-add NET_ADMIN   --device /dev/net/tun:/dev/net/tun   -v "$(pwd):/workspaces/deepracer_project"   -u daes   autonomousracer_devcontainer_ros_dev bash
