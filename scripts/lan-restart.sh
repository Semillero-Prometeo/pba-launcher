#!/usr/bin/env bash
# Stop the stack, then start it again (migrate + seed + LAN URLs).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "Restarting R-ONE…"
"${ROOT_DIR}/scripts/lan-down.sh"
exec "${ROOT_DIR}/scripts/lan-up.sh" "$@"
