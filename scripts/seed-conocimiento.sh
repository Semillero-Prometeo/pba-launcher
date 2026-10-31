#!/usr/bin/env bash
# Load preguntas_respuestas.json into Milvus conocimiento. Safe to re-run.
# Source of truth:
#   pmai-model-vision-language/utils/webscraping/primera fase/preguntas_respuestas.json
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

seed_cmd=(python -m utils.context_builder.cargar_preguntas)

if "${DOCKER[@]}" compose ps --status running -q pmai-core | grep -q .; then
  echo "Seeding conocimiento in the running pmai-core…"
  "${DOCKER[@]}" compose exec -T pmai-core "${seed_cmd[@]}"
else
  echo "Seeding conocimiento with a one-off pmai-core…"
  "${DOCKER[@]}" compose run --rm --no-deps -T --entrypoint python pmai-core \
    -m utils.context_builder.cargar_preguntas
fi
echo "Done. Conocimiento comes from preguntas_respuestas.json."
