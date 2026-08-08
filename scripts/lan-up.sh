#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

WEB_PORT="${WEB_MAIN_PORT:-4200}"
GATEWAY_PORT="${MS_GATEWAY_PORT:-3000}"

if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  set -a
  # Export only simple KEY=VALUE lines; ignore comments/blank
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line//[[:space:]]/}" ]] && continue
    if [[ "$line" =~ ^(WEB_MAIN_PORT|MS_GATEWAY_PORT)= ]]; then
      export "$line"
    fi
  done < .env
  set +a
  WEB_PORT="${WEB_MAIN_PORT:-$WEB_PORT}"
  GATEWAY_PORT="${MS_GATEWAY_PORT:-$GATEWAY_PORT}"
fi

is_wsl() {
  grep -qi microsoft /proc/version 2>/dev/null || [[ -n "${WSL_DISTRO_NAME:-}" ]]
}

if is_wsl; then
  echo "WARNING: WSL detected. LAN exposure is supported on native Ubuntu; WSL is best-effort only." >&2
fi

iface_skipped() {
  local name="$1"
  [[ "$name" == lo ]] && return 0
  [[ "$name" == docker* ]] && return 0
  [[ "$name" == br-* ]] && return 0
  [[ "$name" == veth* ]] && return 0
  return 1
}

iface_preferred() {
  local name="$1"
  [[ "$name" == wlan* || "$name" == wlp* || "$name" == eth* || "$name" == en* ]]
}

detect_lan_ip() {
  local name addr
  if [[ -n "${LAN_IFACE:-}" ]]; then
    addr="$(ip -4 -o addr show dev "$LAN_IFACE" 2>/dev/null | awk '{print $4}' | cut -d/ -f1 | head -n1 || true)"
    if [[ -z "$addr" ]]; then
      echo "ERROR: No IPv4 on LAN_IFACE=$LAN_IFACE" >&2
      exit 1
    fi
    echo "$addr"
    return 0
  fi

  # Prefer wifi/ethernet
  while read -r name addr; do
    iface_skipped "$name" && continue
    iface_preferred "$name" || continue
    [[ -n "$addr" ]] || continue
    echo "$addr"
    return 0
  done < <(ip -4 -o addr show | awk '{gsub(/\/.*/, "", $4); print $2, $4}')

  # Fallback: any non-skipped interface
  while read -r name addr; do
    iface_skipped "$name" && continue
    [[ -n "$addr" ]] || continue
    echo "$addr"
    return 0
  done < <(ip -4 -o addr show | awk '{gsub(/\/.*/, "", $4); print $2, $4}')

  echo "ERROR: No usable LAN IPv4 found. Set LAN_IFACE=<interface> (e.g. wlp2s0) and retry." >&2
  exit 1
}

ensure_ufw() {
  if ! command -v ufw >/dev/null 2>&1; then
    echo "WARNING: ufw not found; skipping firewall rules for ${WEB_PORT}/tcp and ${GATEWAY_PORT}/tcp." >&2
    return 0
  fi
  if ! sudo -n ufw status >/dev/null 2>&1; then
    echo "Opening UFW TCP ${GATEWAY_PORT} and ${WEB_PORT} (may prompt for sudo)…"
  fi
  if ! sudo ufw allow "${GATEWAY_PORT}/tcp" >/dev/null; then
    echo "WARNING: failed to allow ${GATEWAY_PORT}/tcp via ufw; continuing." >&2
  fi
  if ! sudo ufw allow "${WEB_PORT}/tcp" >/dev/null; then
    echo "WARNING: failed to allow ${WEB_PORT}/tcp via ufw; continuing." >&2
  fi
}

wait_for_port() {
  local host="$1" port="$2" timeout="${3:-180}"
  local start
  start="$(date +%s)"
  echo "Waiting for TCP ${host}:${port} (timeout ${timeout}s)…"
  while true; do
    if (echo >/dev/tcp/"$host"/"$port") >/dev/null 2>&1; then
      echo "Port ${port} is open."
      return 0
    fi
    if command -v nc >/dev/null 2>&1 && nc -z "$host" "$port" >/dev/null 2>&1; then
      echo "Port ${port} is open."
      return 0
    fi
    if (( $(date +%s) - start >= timeout )); then
      echo "WARNING: timed out waiting for ${host}:${port}; opening the URL anyway." >&2
      return 1
    fi
    sleep 2
  done
}

LAN_IP="$(detect_lan_ip)"
FRONTEND_URL="http://${LAN_IP}:${WEB_PORT}"

ensure_ufw

DOCKER=(docker)
if ! docker info >/dev/null 2>&1; then
  if command -v sudo >/dev/null 2>&1; then
    DOCKER=(sudo docker)
  else
    echo "ERROR: cannot talk to Docker daemon. Add your user to the docker group or use sudo." >&2
    exit 1
  fi
fi

echo "Starting services: ${DOCKER[*]} compose up -d $*"
"${DOCKER[@]}" compose up -d "$@"

wait_for_port 127.0.0.1 "$WEB_PORT" 180 || true

echo
echo "Frontend (LAN): ${FRONTEND_URL}"
echo "Gateway (LAN):  http://${LAN_IP}:${GATEWAY_PORT}"
echo "Follow logs:    ${DOCKER[*]} compose logs -f"
echo

if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$FRONTEND_URL" >/dev/null 2>&1 || echo "WARNING: xdg-open failed; open ${FRONTEND_URL} manually." >&2
else
  echo "xdg-open not found; open ${FRONTEND_URL} in your browser."
fi
