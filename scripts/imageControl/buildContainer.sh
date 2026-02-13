#!/bin/bash

cd /home/deepracer/deepracer/AutonomousRacer

echo "Stopping and Removing old Containers"
docker stop autonomousracer_devcontainer_ros_dev-1 
docker rm autonomousracer_devcontainer_ros_dev-1


echo "Clearing Cache for Cleaner Build"
docker system prune -a -f --volumes

echo "Building Container"
docker build --network host --add-host metadata.google.internal:127.0.0.1 -t autonomousracer_devcontainer_ros_dev -f .devcontainer/Dockerfile .


echo "Container Built"