#!/bin/bash
# Move to the project root (where .devcontainer/ resides)
cd "$(dirname "$0")/../.."

echo "Starting Container on DeepRacer using Docker Compose..."

# 1. Pull the latest image if you've updated it on Docker Hub
# docker-compose -f .devcontainer/docker-compose.yml pull

# 2. Start the container in detached mode
# We use -f to point to the compose file inside the .devcontainer folder

docker-compose -p autonomousracer_devcontainer -f .devcontainer/docker-compose.yml up -d

echo "Container is UP. Use your enter script to jump in."