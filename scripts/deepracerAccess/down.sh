#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/../.."
source ./scripts/deepracerAccess/_docker.sh
dr_docker compose --env-file .env.deepracer -f docker-compose.deepracer.yml down

echo "Stopped deepracer-access container"
