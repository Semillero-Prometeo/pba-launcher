#!/usr/bin/env bash
# Apply Prisma migrations and seed admin users. Safe to re-run.
# Users: admin-prometeo@unilibre.edu.co (and 2/3) / Prometeo2026*
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DOCKER=(docker)
if ! docker info >/dev/null 2>&1; then
  if command -v sudo >/dev/null 2>&1; then
    DOCKER=(sudo docker)
  else
    echo "ERROR: cannot talk to Docker daemon." >&2
    exit 1
  fi
fi

if ! "${DOCKER[@]}" compose exec -T db pg_isready -U postgres >/dev/null 2>&1; then
  echo "ERROR: Postgres is not ready. Start the stack first (./scripts/lan-up.sh)." >&2
  exit 1
fi

echo "Applying auth migrations…"
"${DOCKER[@]}" compose exec -T pba-ms-auth npx prisma migrate deploy
echo "Seeding admin users…"
"${DOCKER[@]}" compose exec -T pba-ms-auth npx prisma db seed
echo "Done. Login: admin-prometeo@unilibre.edu.co"
