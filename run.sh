#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="ros:humble-teleop"
CONTAINER_NAME="humble-teleop-joy"
BIND_ADDRESS="0.0.0.0"
CONTAINER_PORT="8000"
HOST_PORT="8080"
LAUNCH_FILE="/usr/local/share/humble_teleop/browser_teleop.launch.py"

die() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

command -v docker >/dev/null 2>&1 || die "docker command not found."
docker info >/dev/null 2>&1 || die "Docker daemon is not reachable. Start Docker or check your Docker permissions."

if docker container inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
  die "container '$CONTAINER_NAME' already exists. Stop or remove it before running this script."
fi

if ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
  printf "Docker image '%s' not found. Building it now...\n" "$IMAGE_NAME"
  docker build -t "$IMAGE_NAME" "$SCRIPT_DIR"
fi

printf "Starting '%s'. Open http://%s:%s/ after the launch is ready.\n" "$CONTAINER_NAME" "$BIND_ADDRESS" "$HOST_PORT"

docker run --rm -it \
  --name "$CONTAINER_NAME" \
  -p "${BIND_ADDRESS}:${HOST_PORT}:${CONTAINER_PORT}" \
  "$IMAGE_NAME" \
  ros2 launch "$LAUNCH_FILE" \
  bind_address:="$BIND_ADDRESS" \
  http_port:="$CONTAINER_PORT"
