#!/usr/bin/env bash
# Pair/connect a Bluetooth speaker on the host PulseAudio (what pba-ms-robotics uses).
# Default device: Thinkplus-K3-pro (Lenovo; BlueZ may show "联想Thinkplus-K3 pro").
set -euo pipefail

DEFAULT_NAME="${RONE_BT_DEVICE:-Thinkplus-K3-pro}"
STATE_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/rone"
STATE_FILE="${STATE_DIR}/bluetooth-device"
TEST_WAV="/usr/share/sounds/alsa/Front_Center.wav"

usage() {
  cat <<EOF
Uso:
  ./scripts/bt-up.sh scan
  ./scripts/bt-up.sh status
  ./scripts/bt-up.sh connect ["nombre"]
  ./scripts/bt-up.sh disconnect ["nombre"]

connect     Escanea, empareja (si falta), conecta A2DP y deja el parlante como salida
disconnect  Corta el audio Bluetooth
scan        Lista dispositivos visibles (el parlante debe estar en modo emparejar)
status      Adapter, emparejados, sink de Pulse

Sin nombre, usa ${DEFAULT_NAME} (o el último MAC guardado).
El contenedor de robótica usa Pulse del host: no hace falta GUI.
EOF
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: falta $1" >&2
    exit 1
  }
}

ensure_audio() {
  systemctl --user start pulseaudio.socket pulseaudio.service 2>/dev/null || true
  pactl info >/dev/null
  if ! pactl list short modules | grep -q module-bluetooth-discover; then
    pactl load-module module-bluetooth-policy >/dev/null 2>&1 || true
    pactl load-module module-bluetooth-discover >/dev/null 2>&1 || true
  fi
  bluetoothctl power on >/dev/null
}

norm_name() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9'
}

mac_from_info() {
  local needle mac rest
  needle="$(norm_name "$1")"
  while read -r _ mac rest; do
    [[ "$mac" =~ ^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$ ]] || continue
    if [[ "$(norm_name "$rest")" == *"$needle"* ]]; then
      echo "$mac"
      return 0
    fi
  done < <(bluetoothctl devices 2>/dev/null)
  if [[ -f "$STATE_FILE" ]]; then
    cat "$STATE_FILE"
    return 0
  fi
  return 1
}

prefer_a2dp() {
  local card sink
  card="$(pactl list cards short 2>/dev/null | awk '/bluez/{print $2; exit}')"
  if [[ -n "$card" ]]; then
    pactl set-card-profile "$card" a2dp_sink >/dev/null 2>&1 || \
      pactl set-card-profile "$card" a2dp-sink >/dev/null 2>&1 || true
  fi
  sink="$(pactl list short sinks 2>/dev/null | awk '/bluez/ && /a2dp/{print $2; exit}')"
  if [[ -z "$sink" ]]; then
    sink="$(pactl list short sinks 2>/dev/null | awk '/bluez/{print $2; exit}')"
  fi
  if [[ -n "$sink" ]]; then
    pactl set-default-sink "$sink" >/dev/null
    echo "$sink"
    return 0
  fi
  return 1
}

wait_bt_sink() {
  local i
  for i in $(seq 1 20); do
    if prefer_a2dp >/dev/null; then
      prefer_a2dp
      return 0
    fi
    sleep 1
  done
  echo "WARNING: conectado por Bluetooth pero Pulse aún no muestra un sink. ¿pulseaudio-module-bluetooth?" >&2
  return 1
}

pair_and_connect() {
  local want="$1"
  python3 - "$want" <<'PY'
import re, select, subprocess, sys, time

want = sys.argv[1]
needle = re.sub(r"[^a-z0-9]", "", want.lower())

p = subprocess.Popen(
    ["bluetoothctl"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)

def send(cmd: str) -> None:
    assert p.stdin is not None
    print(f">>> {cmd}", flush=True)
    p.stdin.write(cmd + "\n")
    p.stdin.flush()

def read_for(seconds: float) -> str:
    assert p.stdout is not None
    chunks = []
    end = time.time() + seconds
    while time.time() < end:
        r, _, _ = select.select([p.stdout], [], [], max(0.05, end - time.time()))
        if not r:
            continue
        line = p.stdout.readline()
        if not line:
            break
        sys.stdout.write(line)
        sys.stdout.flush()
        chunks.append(line)
    return "".join(chunks)

def find_mac(buf: str) -> str | None:
    ansi = re.compile(r"\x1b\[[0-9;]*m")
    for raw in buf.splitlines():
        line = ansi.sub("", raw)
        m = re.search(r"Device\s+(([0-9A-F]{2}:){5}[0-9A-F]{2})\s+(.+)", line, re.I)
        if not m:
            m2 = re.search(r"(([0-9A-F]{2}:){5}[0-9A-F]{2})", line, re.I)
            if m2 and needle in re.sub(r"[^a-z0-9]", "", line.lower()):
                return m2.group(1)
            continue
        mac, name = m.group(1), m.group(3)
        if needle in re.sub(r"[^a-z0-9]", "", name.lower()):
            return mac
    return None

send("power on")
send("pairable on")
send("agent NoInputNoOutput")
send("default-agent")
buf = read_for(2)
mac = find_mac(buf)
if not mac:
    send("scan on")
    buf += read_for(18)
    mac = find_mac(buf)
if not mac:
    send("scan off")
    send("quit")
    read_for(1)
    sys.exit("ERROR: no apareció el parlante. Póngalo en modo emparejar e intente de nuevo.")

send(f"pair {mac}")
read_for(15)
send(f"trust {mac}")
read_for(2)
send(f"connect {mac}")
out = read_for(12)
send("scan off")
send("quit")
read_for(1)
if "Failed to connect" in out and "Connection successful" not in out:
    # Trusted devices often connect on a second try after pairing drops.
    subprocess.run(["bluetoothctl", "connect", mac], check=False)
print(f"MAC={mac}", flush=True)
PY
}

print_status() {
  echo "Adapter:"
  bluetoothctl show | grep -E 'Name:|Powered:|Discovering:' || true
  echo
  echo "Dispositivos:"
  bluetoothctl devices || true
  echo
  echo "Pulse sinks:"
  pactl list short sinks || true
  echo
  echo "Default sink: $(pactl get-default-sink 2>/dev/null || pactl info | awk -F': ' '/Default Sink/{print $2}')"
  if [[ -f "$STATE_FILE" ]]; then
    echo "Último R-ONE: $(cat "$STATE_FILE")"
  fi
}

cmd="${1:-}"
case "$cmd" in
  ""|-h|--help|help)
    usage
    exit 0
    ;;
esac

need_cmd bluetoothctl
need_cmd pactl
need_cmd python3
ensure_audio

case "$cmd" in
  scan)
    echo "Escaneando 20 s (el parlante debe estar visible / en emparejar)…"
    bluetoothctl --timeout 20 scan on || true
    echo
    bluetoothctl devices
    ;;
  status)
    print_status
    ;;
  connect)
    name="${2:-$DEFAULT_NAME}"
    echo "Conectando Bluetooth: ${name}"
    mac="$(mac_from_info "$name" || true)"
    if [[ -n "${mac:-}" ]] && bluetoothctl info "$mac" 2>/dev/null | grep -q "Paired: yes"; then
      bluetoothctl connect "$mac" || pair_and_connect "$name"
    else
      pair_and_connect "$name"
      mac="$(mac_from_info "$name" || true)"
    fi
    if [[ -z "${mac:-}" ]]; then
      mac="$(bluetoothctl devices | awk 'tolower($0) ~ /thinkplus/ {print $2; exit}')"
    fi
    if [[ -n "${mac:-}" ]]; then
      mkdir -p "$STATE_DIR"
      echo "$mac" > "$STATE_FILE"
      bluetoothctl trust "$mac" >/dev/null || true
    fi
    sink="$(wait_bt_sink || true)"
    echo "Sink: ${sink:-ninguno}"
    if [[ -n "${sink:-}" && -f "$TEST_WAV" ]]; then
      paplay "$TEST_WAV" >/dev/null 2>&1 || true
      echo "Reproduje un tono de prueba en el parlante."
    fi
    echo "Listo. El turno de R-ONE usa este sink (bluez) automáticamente."
    echo "Si la voz ya estaba en marcha: docker compose restart pba-ms-robotics"
    ;;
  disconnect)
    name="${2:-$DEFAULT_NAME}"
    mac="$(mac_from_info "$name" || true)"
    if [[ -z "${mac:-}" && -f "$STATE_FILE" ]]; then
      mac="$(cat "$STATE_FILE")"
    fi
    if [[ -z "${mac:-}" ]]; then
      echo "ERROR: no hay MAC guardado. Pase el nombre o ejecute connect antes." >&2
      exit 1
    fi
    bluetoothctl disconnect "$mac"
    echo "Desconectado $mac"
    ;;
  *)
    usage
    exit 1
    ;;
esac
