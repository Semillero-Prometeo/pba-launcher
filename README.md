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

El script detecta la IPv4 de la LAN, abre reglas UFW TCP para los puertos del gateway (3000) y la web (4200) cuando es posible, ejecuta `docker compose up -d`, espera a que el puerto 4200 responda, imprime la URL LAN (`http://<LAN_IP>:4200`) y abre el navegador en el host.

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

- [ ] `./scripts/lan-up.sh` imprime `http://<LAN_IP>:4200` y abre el navegador
- [ ] Login funciona en el host
- [ ] El modal QR aparece en la primera visita al admin; el menú de perfil puede reabrirlo
- [ ] Un teléfono en la misma Wi‑Fi abre la URL/QR y puede iniciar sesión / llamar al API

---

# Para agregar preguntas u orcaciones
/home/rone/Documentos/r-one/pba-launcher/pmas-web-main/src/app/pages/robotics-chat/robotics-chat.ts

Se edita decirQuickOptions o chatQuickOptions
