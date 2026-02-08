#!/bin/bash

# Configuration - Matches your Mac setup
CONTAINER_NAME="autonomousracer_devcontainer-ros_dev-1"
IMAGE_NAME="your-docker-username/deepracer-foxy:latest" # Change to your image
WORKSPACE="/workspaces/deepracer_project"
LOCAL_DIR="$(pwd)" # Assumes you run this from your repo root

echo "Starting $CONTAINER_NAME on DeepRacer..."

# Check if an old stopped version exists and remove it
if [ "$(docker ps -aq -f name=$CONTAINER_NAME)" ]; then
    echo "Cleaning up old container..."
    docker rm -f $CONTAINER_NAME
fi

docker run -d \
  --name "$CONTAINER_NAME" \
  --privileged \
  --network bridge \
  --cap-add NET_ADMIN \
  --device /dev/net/tun:/dev/net/tun \
  --sysctl net.ipv6.conf.all.disable_ipv6=0 \
  -v "$LOCAL_DIR:$WORKSPACE" \
  -e ROS_DOMAIN_ID=42 \
  -w "$WORKSPACE" \
  "$IMAGE_NAME" \
  sleep infinity

echo "Container is UP. You can now use your enter script."