#!/bin/bash


CONTAINER_ID="autonomousracer_devcontainer-ros_dev-1"

if [ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER_ID" 2>/dev/null)" = "true" ]; then
    echo "Container $CONTAINER_ID is running1"
    echo "Entering Container!"
    docker exec -it -u daes -w /workspaces/deepracer_project $CONTAINER_ID "bash"
else
    echo "Container $CONTAINER_ID is not running."
fi