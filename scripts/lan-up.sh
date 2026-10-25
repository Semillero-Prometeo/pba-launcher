#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

WEB_PORT="${WEB_MAIN_PORT:-4200}"
GATEWAY_PORT="${MS_GATEWAY_PORT:-3000}"
STUDIO_PORT="${MOTION_STUDIO_PORT:-4210}"

if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  set -a
  # Export only simple KEY=VALUE lines; ignore comments/blank
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line//[[:space:]]/}" ]] && continue
    if [[ "$line" =~ ^(WEB_MAIN_PORT|MS_GATEWAY_PORT|MOTION_STUDIO_PORT)= ]]; then
      export "$line"
    fi
  done < .env
  set +a
  WEB_PORT="${WEB_MAIN_PORT:-$WEB_PORT}"
  GATEWAY_PORT="${MS_GATEWAY_PORT:-$GATEWAY_PORT}"
  STUDIO_PORT="${MOTION_STUDIO_PORT:-$STUDIO_PORT}"
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
  [[ "$name" == l4tbr* ]] && return 0
  [[ "$name" == usb0 || "$name" == usb1 ]] && return 0
  [[ "$name" == can* ]] && return 0
  return 1
}

iface_preferred() {
  local lower
  lower="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  # Jetson names look like wlP1p1s0 / enP8p1s0; compare in lowercase.
  [[ "$lower" == wlan* || "$lower" == wlp* || "$lower" == wl* || "$lower" == eth* || "$lower" == en* ]]
}

default_route_dev() {
  ip -4 route show default 2>/dev/null | awk '{for (i = 1; i <= NF; i++) if ($i == "dev") { print $(i + 1); exit }}'
}

default_route_src() {
  ip -4 route show default 2>/dev/null | awk '{for (i = 1; i <= NF; i++) if ($i == "src") { print $(i + 1); exit }}'
}

# Address the kernel would use to leave the LAN (avoids leftover static IPs on the same NIC).
outbound_src() {
  ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i = 1; i <= NF; i++) if ($i == "src") { print $(i + 1); exit }}'
}

ipv4_on_iface() {
  local name="$1"
  local prefer="${2:-}"
  local addr
  if [[ -n "$prefer" ]] && ip -4 -o addr show dev "$name" 2>/dev/null | awk '{print $4}' | cut -d/ -f1 | grep -qx "$prefer"; then
    echo "$prefer"
    return 0
  fi
  while read -r addr; do
    [[ -z "$addr" || "$addr" == 169.254.* ]] && continue
    echo "$addr"
    return 0
  done < <(ip -4 -o addr show dev "$name" 2>/dev/null | awk '{print $4}' | cut -d/ -f1)
  return 1
}

# Sets DETECTED_LAN_IFACE and DETECTED_LAN_IP (must not run in a subshell).
detect_lan_ip() {
  local name addr src
  src="$(outbound_src || true)"
  [[ -n "$src" ]] || src="$(default_route_src || true)"

  if [[ -n "${LAN_IFACE:-}" ]]; then
    addr="$(ipv4_on_iface "$LAN_IFACE" "$src" || true)"
    if [[ -z "$addr" ]]; then
      echo "ERROR: No IPv4 on LAN_IFACE=$LAN_IFACE" >&2
      exit 1
    fi
    DETECTED_LAN_IFACE="$LAN_IFACE"
    DETECTED_LAN_IP="$addr"
    return 0
  fi

  name="$(default_route_dev || true)"
  if [[ -n "$name" ]] && ! iface_skipped "$name"; then
    addr="$(ipv4_on_iface "$name" "$src" || true)"
    if [[ -n "$addr" ]]; then
      DETECTED_LAN_IFACE="$name"
      DETECTED_LAN_IP="$addr"
      return 0
    fi
  fi

  while read -r name addr; do
    iface_skipped "$name" && continue
    iface_preferred "$name" || continue
    [[ "$addr" == 169.254.* ]] && continue
    [[ -n "$addr" ]] || continue
    DETECTED_LAN_IFACE="$name"
    DETECTED_LAN_IP="$addr"
    return 0
  done < <(ip -4 -o addr show | awk '{gsub(/\/.*/, "", $4); print $2, $4}')

  while read -r name addr; do
    iface_skipped "$name" && continue
    [[ "$addr" == 169.254.* ]] && continue
    [[ -n "$addr" ]] || continue
    DETECTED_LAN_IFACE="$name"
    DETECTED_LAN_IP="$addr"
    return 0
  done < <(ip -4 -o addr show | awk '{gsub(/\/.*/, "", $4); print $2, $4}')

  echo "ERROR: No usable LAN IPv4 found. Set LAN_IFACE=<interface> (e.g. wlP1p1s0) and retry." >&2
  exit 1
}

ensure_ufw() {
  local ports=("$GATEWAY_PORT" "$WEB_PORT" "$STUDIO_PORT")
  if ! command -v ufw >/dev/null 2>&1; then
    echo "WARNING: ufw not found; skipping firewall rules for TCP ${ports[*]}." >&2
    return 0
  fi
  if ! sudo -n ufw status >/dev/null 2>&1; then
    echo "Opening UFW TCP ${ports[*]} (may prompt for sudo)…"
  fi
  local port
  for port in "${ports[@]}"; do
    if ! sudo ufw allow "${port}/tcp" >/dev/null; then
      echo "WARNING: failed to allow ${port}/tcp via ufw; continuing." >&2
    fi
  done
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

DETECTED_LAN_IFACE=""
DETECTED_LAN_IP=""
detect_lan_ip
LAN_IP="$DETECTED_LAN_IP"
FRONTEND_URL="http://${LAN_IP}:${WEB_PORT}"
echo "LAN: ${DETECTED_LAN_IFACE:-?} ${LAN_IP}"

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
wait_for_port 127.0.0.1 "$STUDIO_PORT" 180 || true

echo
echo "Frontend (LAN):      ${FRONTEND_URL}"
echo "Gateway (LAN):       http://${LAN_IP}:${GATEWAY_PORT}"
echo "Motion Studio (LAN): http://${LAN_IP}:${STUDIO_PORT}"
echo "Follow logs:         ${DOCKER[*]} compose logs -f"
echo

if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$FRONTEND_URL" >/dev/null 2>&1 || echo "WARNING: xdg-open failed; open ${FRONTEND_URL} manually." >&2
else
  echo "xdg-open not found; open ${FRONTEND_URL} in your browser."
fi
