#!/bin/bash
CONTAINER_ID="autonomousracer_devcontainer_ros_dev-1"

if [ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER_ID" 2>/dev/null)" = "true" ]; then
    STATUS=$(docker inspect -f '{{.State.Status}}' $CONTAINER_ID)
    UPTIME=$(docker inspect -f '{{.State.StartedAt}}' $CONTAINER_ID)
    
    echo "--- Container Status ---"
    echo "Name:   $CONTAINER_ID"
    echo "Status: $STATUS"
    echo "Since:  $UPTIME"
    echo "------------------------"
    # Show live CPU/RAM usage once
    docker stats $CONTAINER_ID --no-stream
else
    echo "Container $CONTAINER_ID is currently DOWN."
fi