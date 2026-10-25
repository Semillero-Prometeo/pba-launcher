#!/usr/bin/env bash
# Stop the R-ONE Compose stack. Images and database volume stay on disk.
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

echo "Stopping R-ONE: ${DOCKER[*]} compose down $*"
"${DOCKER[@]}" compose down "$@"
echo "R-ONE is stopped. Start again with ./scripts/lan-up.sh (or rone-up)."
