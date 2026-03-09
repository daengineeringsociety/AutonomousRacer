#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/../.."
source ./scripts/deepracerAccess/_docker.sh

echo "Starting deepracer-access container"
dr_docker compose --env-file .env.deepracer -f docker-compose.deepracer.yml up -d --build

echo "Container is ready: deepracer-access"
