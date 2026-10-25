# Jetson Orin Nano — miniPC de R-ONE

Fecha de puesta en marcha: 25 de octubre de 2026  
Equipo: `jetson-w4`  
Usuario: `jetson`  
SSH (red actual del laboratorio): `ssh jetson@192.168.40.9`  
Repositorio en la placa: `/home/jetson/pba-launcher`

Este archivo es la ficha de la placa y la bitácora de lo que se configuró para que R-ONE arranque con un comando cuando cambie la red del androide.

---

## 1. Especificaciones

| Pieza | Valor |
|---|---|
| Modelo | NVIDIA Jetson Orin Nano Engineering Reference Developer Kit Super |
| Módulo | Jetson Orin Nano, 8 GB (`p3767-0003`) |
| SoC | Tegra, GPU Orin (`nvgpu`) |
| CPU | 6 × ARM Cortex-A78AE, `aarch64` |
| RAM | 7.4 GiB visibles (unos 6.2 GiB libres al dejarla configurada) |
| Swap | 8.0 GiB |
| Almacenamiento | NVMe `nvme0n1` 238.5 GB; raíz ext4 172 GB en `nvme0n1p1` |
| Disco libre tras el clon | ~30 GB (81–83 % usado; la imagen Yahboom ya ocupaba ~133 GB) |
| L4T / JetPack | R36.4.3 / JetPack 6.2 |
| Kernel | `5.15.148-tegra` |
| SO | Ubuntu 22.04.5 LTS (Jammy) |
| Zona horaria | `America/Bogota` (antes venía `Asia/Shanghai`) |
| Modo de potencia | `MAXN_SUPER` |
| CUDA | 12.6.85 (`nvidia-smi` 540.4.0) |
| cuDNN | 9.20.0.48 |
| TensorRT | 10.7.0.23 |
| VPI | 3.2.4 |
| Vulkan | 1.3.204 |
| OpenCV | 4.10.0 con CUDA |
| Python (host) | 3.10.12 |
| Node (host) | 22.23.2 |
| Git | 2.34.1 + Git LFS 3.0.2 |
| Avahi / mDNS | activo (`jetson-w4.local`) |

Ethernet: `enP8p1s0` (Realtek RTL8111/8168).  
Wi-Fi: `wlP1p1s0`.

---

## 2. Red de la placa (importante)

En el mismo cable Ethernet hay **dos IPv4**:

| Dirección | Origen | Para qué |
|---|---|---|
| `192.168.40.9/24` | DHCP de la red actual | SSH, internet, teléfonos/PCs de esta LAN |
| `192.168.1.15/24` | Dirección estática de Yahboom | Se dejó por si algún dispositivo del kit sigue en `192.168.1.0/24` |

La puerta de enlace **no** debe ser `192.168.1.1`. Esa ruta no sale a internet. La salida válida en el laboratorio es:

```text
default via 192.168.40.1 dev enP8p1s0
```

DNS: `192.168.40.1`.

El frontend de R-ONE **no se edita por IP**. Angular arma el gateway como `http://<hostname-de-la-página>:3000`. Quien abra `http://<IP-de-la-Jetson>:4200` ya apunta al API correcto. Por eso, cuando cambia el Wi-Fi, basta con unirse a la red nueva, volver a imprimir la URL y abrirla (o escanear el QR de la app).

---

## 3. Bitácora — qué se hizo el 2026-10-25

Orden real de la puesta en marcha.

### 3.1 Comprobación inicial

- Ping y SSH a `192.168.40.9` OK.
- Git ya estaba instalado.
- El usuario `jetson` ya estaba en el grupo `docker`, pero **no había motor**: faltaban `docker`, `dockerd` y `containerd`. Solo quedaban restos (`docker-ce-rootless-extras`, `docker-model-plugin`) y NVIDIA Container Toolkit 1.20.
- No existía `/home/jetson/pba-launcher`.
- `sudo` pide contraseña (usuario `jetson`).
- UFW no está instalado: los puertos 3000/4200/4210 quedan alcanzables en LAN sin reglas extra.
- Reloj del sistema: 10 de septiembre de 2026, RTC en 1970, NTP sin sincronizar. Eso rompía HTTPS (`certificate is not yet valid`).
- Zona horaria de fábrica: `Asia/Shanghai`.

### 3.2 Internet

1. Se quitó `ipv4.gateway=192.168.1.1` de la conexión NetworkManager `Wired connection 1`.
2. Se dejó la IP estática `192.168.1.15/24` (sin usarla como default).
3. Se reaplicó la NIC con `nmcli device reapply enP8p1s0` (sin cortar SSH).
4. La ruta por defecto pasó a `192.168.40.1` por DHCP.
5. Se comprobó `ping 1.1.1.1`, `ping 8.8.8.8` y `https://github.com`.

Persistencia: `ipv4.gateway` de esa conexión quedó vacío. En el próximo arranque DHCP debe volver a poner `192.168.40.1`.

### 3.3 Reloj y zona horaria

```bash
sudo timedatectl set-ntp true
sudo systemctl restart systemd-timesyncd
sudo timedatectl set-timezone America/Bogota
```

Tras eso: reloj sincronizado, `https://download.docker.com` responde 200.

### 3.4 Docker

El repo APT de Docker ya estaba en `/etc/apt/sources.list.d/docker.list`. Se instaló el motor que faltaba:

```bash
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Quedó:

- Docker Engine 29.9.2
- Compose v5.6.1
- Buildx v0.38.1
- Runtime NVIDIA en `/etc/docker/daemon.json`
- `docker` usable **sin** sudo (grupo `docker`)

Sudoers para el día a día de red (`/etc/sudoers.d/rone-lan`):

```text
jetson ALL=(root) NOPASSWD: /usr/sbin/ufw, /usr/bin/nmcli
```

### 3.5 Proyecto

```bash
cd /home/jetson
GIT_LFS_SKIP_SMUDGE=1 git clone --recurse-submodules --jobs 4 \
  https://github.com/Semillero-Prometeo/pba-launcher.git
mkdir -p /home/jetson/pba-launcher/data/milvus
```

`GIT_LFS_SKIP_SMUDGE=1` evita bajar blobs LFS enormes en el clon. Gemma se descarga solo si falta, la primera vez que arranca `pmai-core`.

Se copió el `.env` de desarrollo del lanzador (no va en git). `docker compose config` en la placa valida OK.

Imágenes base ya bajadas: `postgres:17.1-alpine`, `nats:2.12.5-alpine3.22`.

### 3.6 Arranque fácil

En `~/.bashrc` del usuario `jetson`:

```bash
export RONE_HOME="$HOME/pba-launcher"
rone-up() { (cd "$RONE_HOME" && ./scripts/lan-up.sh "$@"); }
rone-down() { (cd "$RONE_HOME" && ./scripts/lan-down.sh "$@"); }
rone-restart() { (cd "$RONE_HOME" && ./scripts/lan-restart.sh "$@"); }
rone-wifi() { (cd "$RONE_HOME" && ./scripts/wifi-up.sh "$@"); }
rone-status() { (cd "$RONE_HOME" && ./scripts/wifi-up.sh status); }
rone-seed() { (cd "$RONE_HOME" && ./scripts/seed-auth.sh "$@"); }
```

Hay que abrir una sesión SSH nueva (o `source ~/.bashrc`) para usar los alias.

Scripts en el repo:

| Script | Función |
|---|---|
| `scripts/lan-up.sh` | Detecta la IPv4 de salida, Compose, migraciones, seed, imprime URLs LAN |
| `scripts/lan-down.sh` | Detiene el stack (`compose stop`). No borra contenedores |
| `scripts/lan-restart.sh` | `compose stop` y `compose start` (los mismos contenedores) |
| `scripts/wifi-up.sh` | Une Wi-Fi o enciende el hotspot y luego llama a `lan-up.sh` |
| `scripts/seed-auth.sh` | Migraciones y usuarios admin |

`lan-up.sh` ahora:

- Reconoce nombres Jetson (`wlP1p1s0`, `enP8p1s0`).
- Prefiere la IP que el kernel usa para salir (`ip route get 1.1.1.1`), no la estática `192.168.1.15`.
- Omite `l4tbr*`, `usb0`/`usb1` y `can*`.

El hotspot de fábrica (`Hotspot`, SSID `Jetson_Orin_Hot`) tenía `ipv4.method=auto` y **no asignaba IP**. Se cambió a `ipv4.method=shared` para que los teléfonos reciban DHCP (típico `10.42.0.1`).

### 3.7 Docker 29 y la tabla `iptables raw` (25 oct 2026, segundo intento)

El primer `rone-up` falló al construir `pba-ms-robotics` / `pmai-core`:

```text
Unable to enable DIRECT ACCESS FILTERING - DROP rule:
iptables --wait -t raw -A PREROUTING ...
can't initialize iptables table `raw': Table does not exist
```

El kernel `5.15.148-tegra` de JetPack 6.2 **no incluye** `iptable_raw` (`modprobe iptable_raw` → módulo no encontrado). Docker 28+ usa esa tabla al crear el endpoint del bridge, incluso en un `RUN apt-get` del build.

No se recompila el kernel. Workaround oficial de Moby (aceptado en Jetson):

```bash
sudo mkdir -p /etc/systemd/system/docker.service.d
printf '%s\n' '[Service]' 'Environment="DOCKER_INSECURE_NO_IPTABLES_RAW=1"' \
  | sudo tee /etc/systemd/system/docker.service.d/no-iptables-raw.conf
sudo systemctl daemon-reload
sudo systemctl restart docker
```

Eso relaja el filtrado “direct access” de Docker 28: en esta LAN del androide es aceptable. Tras el reinicio, `rone-up` puede volver a construir.

### 3.8 Disco lleno y usuarios seed (25 oct 2026)

Tras el primer build el NVMe quedó al **100 %** (171/172 GB, 0 B libres). Postgres no pudo hacer `initdb` (`pg_wal: No space left on device`), el gateway salió con P1001 y no había usuarios porque **nunca existió la base**.

`lan-up.sh` ahora espera Postgres, aplica `prisma migrate deploy` y `prisma db seed` en `pba-ms-auth` antes de levantar el resto. Re-seed manual: `./scripts/seed-auth.sh`.

Limpieza hecha (no toca JetPack ni las imágenes de R-ONE ya construidas):

| Qué | ~Tamaño | Por qué es viable |
|---|---|---|
| Caché de build Docker (`docker builder prune`) | 18 GB | Las imágenes `pba-launcher-*` ya están compiladas |
| `/usr/share/ollama` | 37 GB | Modelos Ollama del kit; R-ONE usa Gemma en `pmai-core`, no Ollama |
| `workspaces/isaac_ros-dev/isaac_ros_assets` | 15 GB | Assets de Isaac ROS; no los usa el lanzador |
| `~/.cache/{huggingface,uv,pip}` | 8 GB | Caché del host; los contenedores no la montan |
| `/var/log/uvcdynctrl-udev.log` | 6.5 GB | Spam udev de la webcam, no es el sistema |
| `Templates/yahboom_ws.zip` | 1 GB | Zip duplicado de `yahboom_ws/` |
| Snaps deshabilitados | ~1 GB | Revisiones viejas (`core22/24`, `cups`, `snapd`) |

No se borra: `/usr/local/cuda*`, `/usr` de JetPack, `/home/jetson/pba-launcher`, ni las imágenes Docker en uso (`pmai-core` ~13 GB).

---

## 4. Cómo arrancar R-ONE en la Jetson

Primera vez (build largo: Node, Python, BLIP, Gemma si falta el GGUF):

```bash
ssh jetson@192.168.40.9
cd ~/pba-launcher
source ~/.bashrc
rone-up
```

Equivalente sin alias:

```bash
cd ~/pba-launcher
./scripts/lan-up.sh
```

El script imprime, por ejemplo:

```text
LAN: enP8p1s0 192.168.40.9
Frontend (LAN):      http://192.168.40.9:4200
Gateway (LAN):       http://192.168.40.9:3000
Motion Studio (LAN): http://192.168.40.9:4210
```

En un teléfono o PC de **la misma red**, abrir el frontend. Tras el login, el QR de la app comparte `window.location.origin` (no hay que parchear `environment.ts`).

Credenciales de la app (las del README del lanzador):

- Usuario: `admin-prometeo@unilibre.edu.co`
- Contraseña: la documentada en `README.md` del lanzador

Logs:

```bash
cd ~/pba-launcher
docker compose logs -f
```

Parar (sin borrar contenedores):

```bash
rone-down
```

Reiniciar los mismos contenedores:

```bash
rone-restart
```

El primer `compose up` puede tardar mucho y usar varios GB. Si el disco se acerca a 100 %, hay ~16 GB en `/home/jetson/workspaces` y ~8 GB en `/home/jetson/.cache` de la imagen Yahboom, candidatos a limpiar **después** de confirmar que no se necesitan.

---

## 5. Redes que cambian (androide en campo)

Hay dos modos. En ambos, Compose ya publica `0.0.0.0:3000/4200/4210`. No se reconstruye nada al cambiar de SSID. Lo que cambia es **la IP que hay que abrir**.

### Modo A — la Jetson se une al Wi-Fi del lugar (recomendado)

El androide, los teléfonos y los portátiles quedan en la misma red del recinto.

1. SSH a la Jetson (si ya no responde `192.168.40.9`, usar pantalla + teclado, o `ping jetson-w4.local`).
2. Escanear y unirse:

```bash
rone-wifi scan
rone-wifi join "SSID_DEL_LUGAR" "clave"
```

Eso desconecta el hotspot si estaba activo, espera IPv4 en `wlP1p1s0` y ejecuta `lan-up.sh` con `LAN_IFACE=wlP1p1s0`.

3. Copiar las tres URLs que imprime (o abrir el frontend y usar el QR).
4. Los dispositivos deben estar en **ese mismo SSID**, no en otra VLAN/guest aislada.

Si Compose ya estaba arriba, `lan-up.sh` solo refresca `up -d` y vuelve a imprimir la IP nueva.

### Modo B — la Jetson crea la red (hotspot)

Útil si el recinto no da Wi-Fi, o la red de invitados aísla clientes.

```bash
rone-wifi hotspot
```

1. Enciende la conexión NetworkManager `Hotspot` (SSID `Jetson_Orin_Hot`, IPv4 compartida).
2. Espera la IP del AP (suele ser `10.42.0.1`).
3. Arranca el stack y imprime `http://<IP-del-AP>:4200`.
4. En el teléfono: unirse a `Jetson_Orin_Hot` y abrir esa URL.

Clave del hotspot (no se guarda aquí): en la Jetson,

```bash
sudo nmcli -s -g 802-11-wireless-security.psk connection show Hotspot
```

### Ver en qué red está ahora

```bash
rone-status
```

Muestra hostname, IPv4 por interfaz, ruta por defecto y las URLs que deberían usar los teléfonos.

### Forzar una interfaz

Ethernet:

```bash
LAN_IFACE=enP8p1s0 ./scripts/lan-up.sh
```

Wi-Fi:

```bash
LAN_IFACE=wlP1p1s0 ./scripts/lan-up.sh
```

### Cómo volver a encontrarla cuando cambie la IP

1. `ping jetson-w4.local` (Avahi está activo).
2. En la propia placa: `hostname -I` o `rone-status`.
3. En el router del recinto: buscar el hostname `jetson-w4` o la MAC `74:25:54:16:46:93` (ethernet).

SSH de laboratorio (mientras siga el DHCP `192.168.40.0/24`):

```bash
ssh jetson@192.168.40.9
```

---

## 6. Qué no hay que hacer al cambiar de red

- No editar `pmas-web-main/src/environments/environment.ts`.
- No reconstruir imágenes solo porque cambió el SSID.
- No usar `192.168.1.15` como URL pública si los teléfonos están en `192.168.40.0/24` (o en el Wi-Fi del evento). Esa IP es el leftover Yahboom.

Si `192.168.1.15` estorba en otro recinto:

```bash
sudo nmcli connection modify "Wired connection 1" ipv4.addresses ""
sudo nmcli device reapply enP8p1s0
```

---

## 7. Límites de esta placa como miniPC

- **8 GB de RAM** para Postgres, NATS, varios Node, Angular (`NODE_OPTIONS=4096` en compose), robótica, BLIP y Gemma. El primer arranque va a ser lento; si hay OOM, bajar el heap de Angular o no levantar Motion Studio en demos.
- **~30 GB libres** hoy. El build de `pmai-core` y el GGUF de Gemma caben si no se llenan con imágenes Docker viejas (`docker system prune` si hace falta).
- Compose **no** pide `runtime: nvidia` en los servicios actuales (`python:3.12-slim` / Node). El runtime NVIDIA quedó configurado para cuando un servicio lo use.
- El stack de acción sigue siendo CPU/Gemma u OpenAI según `.env`. La GPU del Orin ayuda al detector nativo de JetPack, no automáticamente a los contenedores slim.

---

## 8. Comandos de comprobación

```bash
# red
ip -4 addr
ip -4 route
curl -I https://github.com

# docker
docker version
docker compose version
docker info

# proyecto
cd ~/pba-launcher
git submodule status
docker compose config -q
rone-status
```

Estado al cerrar esta puesta en marcha: red con internet, Docker listo, repo clonado con submódulos, `.env` en su sitio, scripts de LAN/Wi-Fi instalados, hotspot en modo `shared`. El primer `rone-up` es el que construye y levanta el stack.
