#!/usr/bin/env bash
# Pause the R-ONE stack. Containers stay created (compose stop, not down).
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

echo "Stopping R-ONE: ${DOCKER[*]} compose stop $*"
"${DOCKER[@]}" compose stop "$@"
echo "R-ONE is stopped. Containers remain. Start again with rone-restart or ./scripts/lan-restart.sh."
