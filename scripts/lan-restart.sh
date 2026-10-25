#!/usr/bin/env bash
# Stop existing containers, then start the same ones (no recreate).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DOCKER=(docker)
if ! docker info >/dev/null 2>&1; then
  if command -v sudo >/dev/null 2>&1; then
    DOCKER=(sudo docker)
  else
    echo "ERROR: cannot talk to Docker daemon. Add your user to the docker group or use sudo." >&2
    exit 1
  fi
fi

echo "Restarting R-ONE: stop, then start (same containers)…"
"${DOCKER[@]}" compose stop "$@"
"${DOCKER[@]}" compose start "$@"
echo "R-ONE is running."
