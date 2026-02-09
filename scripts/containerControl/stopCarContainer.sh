#!/bin/bash

CONTAINER_NAME="autonomousracer_devcontainer_ros_dev-1"

if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
    echo "Stopping $CONTAINER_NAME..."
    docker stop $CONTAINER_NAME
    echo "Container stopped."
else
    echo "Container $CONTAINER_NAME is not running."
fi