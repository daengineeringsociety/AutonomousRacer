#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/../.."
source ./scripts/deepracerAccess/_docker.sh

if [ ! -f .env.deepracer ]; then
  echo "Missing .env.deepracer. Copy .env.deepracer.example and set DEEPRACER_HOST first."
  exit 1
fi

set -a
. ./.env.deepracer
set +a

: "${DEEPRACER_HOST:?DEEPRACER_HOST must be set in .env.deepracer}"
DEEPRACER_USER="${DEEPRACER_USER:-ubuntu}"
DEEPRACER_PORT="${DEEPRACER_PORT:-22}"
DEEPRACER_KEY="${DEEPRACER_KEY:-}"

if [ "$(dr_docker inspect -f '{{.State.Running}}' deepracer-access 2>/dev/null)" != "true" ]; then
  echo "Container deepracer-access is not running. Start it with scripts/deepracerAccess/up.sh"
  exit 1
fi

SSH_CMD="ssh -o StrictHostKeyChecking=accept-new -p ${DEEPRACER_PORT}"
if [ -n "$DEEPRACER_KEY" ]; then
  SSH_CMD+=" -i ${DEEPRACER_KEY}"
fi
SSH_CMD+=" ${DEEPRACER_USER}@${DEEPRACER_HOST}"

# shellcheck disable=SC2086
dr_docker exec -it deepracer-access bash -lc "$SSH_CMD"
