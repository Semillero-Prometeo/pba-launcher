## ⚙️ Configuración Inicial

### 1. Configurar Submódulos

**Primera vez - Inicializar submódulos:**

```bash
git submodule update --init --recursive
```

**Actualizar referencias a los submódulos:**

```bash
git submodule update --remote
```

### 2. Turno de interacción (mai-core, contexto y acción)

El chat web y la voz pasan por mai-core. BLIP describe la escena; Milvus y Gemma (o OpenAI, si hay clave) responden; robótica habla y ejecuta el gesto.

```bash
cp .env.template .env
mkdir -p data/milvus
sudo docker compose build pmai-core
sudo docker compose up
```

`PMAI_CORE_PYTHONPATH` en `.env` debe quedar así (ya viene en la plantilla):

```bash
PMAI_CORE_PYTHONPATH=/opt/model-context:/opt/action-model:/app/src
```

Antes del primer arranque:

- Si falta `pmai-model-vision-language/models/gguf/gemma-4-E2B-it-Q4_K_M.gguf`, mai-core lo descarga de Hugging Face al arrancar. Hace falta red esa primera vez.
- Opcional: `OPENAI_API_KEY` en `pmai-model-vision-language/.env`. Con red y clave se usa `gpt-4o-mini`; si no, Gemma.
- El catálogo del turno son las secuencias ingestadas (`id`, nombre, descripción) creadas en el estudio de movimiento. `ACTION_DESCRIPTIONS_PATH` sigue existiendo, pero el turno no usa esas frases.
- El estudio web corre en el puerto `MOTION_STUDIO_PORT` (4210). `/sequences` lo carga en un iframe. `./scripts/lan-up.sh` abre ese puerto en UFW junto con 3000 y 4200.
- Milvus Lite crea `conocimiento` e `interacciones` al arrancar mai-core. El archivo queda en `pmai-model-vision-language/utils/milvus/androide_milvus.db`.
- El primer inicio descarga BLIP y el modelo de embeddings, y carga Gemma. Tarda.
### 2. Variables de entorno

Si aún no existe `.env` en la raíz del repositorio, copie la plantilla:

```bash
cp .env.template .env
```

### 3. Inicio en red local (Ubuntu)

Comando principal para levantar el stack en LAN:

```bash
./scripts/lan-up.sh
```

Opcional: forzar la interfaz de red (por ejemplo Wi‑Fi):

```bash
LAN_IFACE=wlp2s0 ./scripts/lan-up.sh
```

El script detecta la IPv4 de la LAN, abre reglas UFW TCP para el gateway (3000), la web (4200) y el Motion Studio (4210) cuando es posible, ejecuta `docker compose up -d`, espera a que 4200 y 4210 respondan, imprime las URLs LAN (`http://<LAN_IP>:4200` y `http://<LAN_IP>:4210`) y abre el navegador en el frontend.

Tras actualizar el frontend (por ejemplo la dependencia `qrcode`), reconstruya el servicio web una vez para refrescar `node_modules` del contenedor:

```bash
docker compose up -d --build pmas-web-main
```

**Teléfonos y otros dispositivos:** use la URL impresa en consola o escanee **Código QR de red** después de iniciar sesión (en la primera visita al admin el modal aparece automáticamente; el menú de perfil puede reabrirlo).

### Credenciales de acceso

Contraseña: 12345

Usuario:
admin-prometeo@unilibre.edu.co
Prometeo2026*

### Verificación (Ubuntu nativo)

sudo ufw allow 3000/tcp
sudo ufw allow 3000/udp

sudo ufw allow 4200/tcp
sudo ufw allow 4200/udp

sudo ufw allow 4210/tcp
sudo ufw allow 4210/udp

ip a
ip a

wlp2s0
10.211.14.115

Buscar pmas-web-main
Buscar src/enviroments/ud
Se debe cambiar la IP en gatewayUrl


