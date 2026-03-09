#!/bin/bash
set -euo pipefail

CONTAINER_NAME="deepracer-access"
source "$(dirname "$0")/_docker.sh"

if [ "$(dr_docker inspect -f '{{.State.Running}}' "$CONTAINER_NAME" 2>/dev/null)" = "true" ]; then
  dr_docker exec -it "$CONTAINER_NAME" bash
else
  echo "Container $CONTAINER_NAME is not running. Start it first with scripts/deepracerAccess/up.sh"
  exit 1
fi
