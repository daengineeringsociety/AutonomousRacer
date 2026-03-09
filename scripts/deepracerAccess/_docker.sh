#!/bin/bash
set -euo pipefail

resolve_docker_cmd() {
  if command -v docker >/dev/null 2>&1; then
    if docker info >/dev/null 2>&1; then
      echo "docker"
      return
    fi

    if command -v sudo >/dev/null 2>&1 && sudo -n docker info >/dev/null 2>&1; then
      echo "sudo docker"
      return
    fi

    echo "Docker CLI exists but daemon access failed. Try: sudo usermod -aG docker \$USER or use sudo docker." >&2
    exit 1
  fi

  if command -v sudo >/dev/null 2>&1 && sudo -n docker info >/dev/null 2>&1; then
    echo "sudo docker"
    return
  fi

  echo "Docker CLI not found. Run from host shell with Docker installed, or install Docker CLI in this container." >&2
  exit 1
}

DOCKER_CMD="$(resolve_docker_cmd)"

dr_docker() {
  # shellcheck disable=SC2086
  $DOCKER_CMD "$@"
}
