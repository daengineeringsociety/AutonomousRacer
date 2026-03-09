#!/bin/bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <remote_path_on_deepracer> <local_path_in_repo_or_container>"
  exit 1
fi

REMOTE_PATH="$1"
LOCAL_PATH="$2"

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

SCP_CMD="scp -o StrictHostKeyChecking=accept-new -P ${DEEPRACER_PORT}"
if [ -n "$DEEPRACER_KEY" ]; then
  SCP_CMD+=" -i ${DEEPRACER_KEY}"
fi
SCP_CMD+=" -r ${DEEPRACER_USER}@${DEEPRACER_HOST}:${REMOTE_PATH} ${LOCAL_PATH}"

# shellcheck disable=SC2086
dr_docker exec -it deepracer-access bash -lc "$SCP_CMD"
