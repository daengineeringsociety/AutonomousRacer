#!/bin/bash
CONTAINER_ID="autonomousracer_devcontainer-ros_dev-1"

if [ "$(docker ps -q -f name=$CONTAINER_ID)" ]; then
    echo "Stopping $CONTAINER_ID..."
    docker stop $CONTAINER_ID
    echo "Container stopped."
else
    echo "Container $CONTAINER_ID is not running."
fi