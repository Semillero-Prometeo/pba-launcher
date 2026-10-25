#!/usr/bin/env bash
# Join a Wi-Fi network (or bring up the Jetson hotspot) and start R-ONE on that LAN.
# The Angular app already uses the page hostname, so a new SSID only needs a new URL.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAN_UP="${ROOT_DIR}/scripts/lan-up.sh"

usage() {
  cat <<'EOF'
Uso:
  ./scripts/wifi-up.sh scan
  ./scripts/wifi-up.sh status
  ./scripts/wifi-up.sh join "SSID" ["clave"]
  ./scripts/wifi-up.sh hotspot

join     Conecta la Jetson como cliente Wi-Fi, espera IPv4 y ejecuta lan-up.sh
hotspot  Activa la conexión NetworkManager "Hotspot" (SSID Jetson_Orin_Hot) y lan-up.sh
status   Muestra interfaces, IPv4 y las URLs que deberían abrir los teléfonos
scan     Lista redes Wi-Fi visibles

No hace falta editar environment.ts: el frontend llama a http://<hostname>:3000
EOF
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: falta $1" >&2
    exit 1
  }
}

wifi_device() {
  nmcli -t -f DEVICE,TYPE device status | awk -F: '$2 == "wifi" { print $1; exit }'
}

ipv4_on() {
  local name="$1"
  local prefer
  prefer="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i=1;i<=NF;i++) if ($i=="src") {print $(i+1); exit}}' || true)"
  if [[ -n "$prefer" ]] && ip -4 -o addr show dev "$name" 2>/dev/null | awk '{print $4}' | cut -d/ -f1 | grep -qx "$prefer"; then
    echo "$prefer"
    return 0
  fi
  ip -4 -o addr show dev "$name" 2>/dev/null | awk '{print $4}' | cut -d/ -f1 | grep -v '^169\.254\.' | head -n1 || true
}

nmcli_run() {
  if nmcli "$@" >/dev/null 2>&1; then
    return 0
  fi
  if command -v sudo >/dev/null 2>&1; then
    sudo nmcli "$@"
    return
  fi
  echo "ERROR: nmcli no pudo ejecutar: $*" >&2
  exit 1
}

wait_ipv4() {
  local name="$1" timeout="${2:-30}" start addr
  start="$(date +%s)"
  while true; do
    addr="$(ipv4_on "$name")"
    if [[ -n "$addr" ]]; then
      echo "$addr"
      return 0
    fi
    if (( $(date +%s) - start >= timeout )); then
      echo "ERROR: ${name} no obtuvo IPv4 en ${timeout}s" >&2
      return 1
    fi
    sleep 1
  done
}

print_status() {
  local web="${WEB_MAIN_PORT:-4200}" gw="${MS_GATEWAY_PORT:-3000}" studio="${MOTION_STUDIO_PORT:-4210}"
  echo "Hostname: $(hostname)  (mDNS: $(hostname).local)"
  echo
  echo "Interfaces IPv4:"
  ip -4 -o addr show | awk '{gsub(/\/.*/, "", $4); printf "  %-12s %s\n", $2, $4}'
  echo
  echo "Ruta por defecto:"
  ip -4 route show default || true
  echo
  echo "Wi-Fi:"
  nmcli -t -f DEVICE,STATE,CONNECTION device status | awk -F: '$1 ~ /^wl/ { printf "  %s  %s  %s\n", $1, $2, $3 }'
  echo
  echo "Si un teléfono está en la misma red, abra:"
  local name addr
  name="$(ip -4 route show default 2>/dev/null | awk '{for (i=1;i<=NF;i++) if ($i=="dev") {print $(i+1); exit}}')"
  addr="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i=1;i<=NF;i++) if ($i=="src") {print $(i+1); exit}}' || true)"
  [[ -n "$addr" ]] || addr="$(ipv4_on "${name:-}")"
  if [[ -n "$addr" ]]; then
    echo "  Frontend      http://${addr}:${web}"
    echo "  Gateway       http://${addr}:${gw}"
    echo "  Motion Studio http://${addr}:${studio}"
  else
    echo "  (sin IPv4 en la ruta por defecto; ejecute join/hotspot)"
  fi
}

cmd="${1:-}"
case "$cmd" in
  ""|-h|--help|help)
    usage
    exit 0
    ;;
esac

need_cmd nmcli
need_cmd ip

WIFI_DEV="$(wifi_device)"
if [[ -z "$WIFI_DEV" ]]; then
  echo "ERROR: no hay interfaz Wi-Fi (nmcli type wifi)." >&2
  exit 1
fi

case "$cmd" in
  scan)
    nmcli_run device wifi rescan || true
    sleep 2
    nmcli device wifi list
    ;;
  status)
    print_status
    ;;
  join)
    ssid="${2:-}"
    pass="${3:-}"
    if [[ -z "$ssid" ]]; then
      echo "ERROR: indique el SSID. Ejemplo: ./scripts/wifi-up.sh join \"RedDelEvento\" \"clave\"" >&2
      exit 1
    fi
    echo "Saliendo de hotspot/AP si está activo en ${WIFI_DEV}…"
    nmcli_run device disconnect "$WIFI_DEV" || true
    echo "Conectando a ${ssid} por ${WIFI_DEV}…"
    if [[ -n "$pass" ]]; then
      nmcli_run device wifi connect "$ssid" password "$pass" ifname "$WIFI_DEV"
    else
      nmcli_run device wifi connect "$ssid" ifname "$WIFI_DEV"
    fi
    echo "Esperando IPv4…"
    addr="$(wait_ipv4 "$WIFI_DEV" 40)"
    echo "Wi-Fi lista: ${WIFI_DEV} ${addr}"
    export LAN_IFACE="$WIFI_DEV"
    exec "$LAN_UP"
    ;;
  hotspot)
    echo "Activando hotspot en ${WIFI_DEV} (conexión NetworkManager Hotspot)…"
    nmcli_run connection up Hotspot
    echo "Esperando IPv4 del AP…"
    addr="$(wait_ipv4 "$WIFI_DEV" 40)"
    echo "Hotspot listo: ${WIFI_DEV} ${addr}"
    echo "SSID esperado: Jetson_Orin_Hot  (unirse desde el teléfono a esa red)"
    export LAN_IFACE="$WIFI_DEV"
    exec "$LAN_UP"
    ;;
  *)
    usage
    exit 1
    ;;
esac
