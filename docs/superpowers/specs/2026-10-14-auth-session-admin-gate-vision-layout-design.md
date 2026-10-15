# Sesión, ADMIN y visión — design

Date: 2026-10-14  
Status: approved by user on 2026-10-14  
Scope: una fase, dos pistas. **Auth:** cualquier 401/403 (salvo el POST de login) cierra la sesión y en `/login` se lee «Tu sesión venció. Entra de nuevo.»; el JWT vencido no deja el cascarón; crear/editar usuarios usa `POST`/`PUT /users` con contraseña obligatoria al crear; solo el rol activo `ADMIN` ve y llama Usuarios/Roles. **Visión:** pipeline a 1 s, sin Preview, objetos observados arriba en tarjetas grandes, cámaras abajo a ~480 px, misma identidad navy/papel. Dueños: `pmas-web-main`, `pba-ms-gateway`, `pba-ms-auth`, `pmai-mai-core`, y `PRODUCT.md` / `DESIGN.md` en la raíz del lanzador.

Relación: los specs `2026-10-14-navy-chrome-chat-tabs-design.md` y `2026-10-14-motion-studio-save-modal-neutro-rewind-design.md` siguen vigentes. Este corte **no reabre** paleta, chat, estudio ni el turno. El spec de Motion Studio listaba auth y visión como cortes pendientes: este archivo los cubre.

## Problem

Cuando el JWT o la sesión en BD caducan, el interceptor de Angular solo cierra si el 401 trae el texto exacto «Esta sesión no se encuentra activa. Inicie sesión nuevamente». Un 401 «Sesión expirada…» o un JWT con `exp` pasado deja el cascarón pintado. El operador no sabe por qué dejó de funcionar.

Crear usuarios falla: la UI pega a `POST /auth/users` (no existe) con `username` + `email` + `first_name` y `id` numérico. El gateway expone `POST /users` marcado `@Public()`, el DTO pide `username` (el correo) y `person_id`, y el repositorio genera una contraseña temporal y valida el **hash** bcrypt en vez del texto. Editar usa `PATCH /auth/users/:id`; el gateway tiene `PUT /users/:id`. Borrar usa `DELETE` inexistente; el gateway tiene `PATCH /users/inactive`.

Los roles no filtran nada. `HasRoles` no se usa. `RolesGuard` no es `APP_GUARD`. `/admin/users` y `/admin/roles` solo piden `authGuard`. El menú muestra Usuarios y Roles a todo el mundo. `/admin/management` redirige a usuarios.

En visión el pipeline emite cada 5 s (`settings.toml` y default en `settings.py`). La UI pide un Preview de 640 px (segundo JPEG) y deja las cámaras en una columna estrecha con thumbs de 160 px. Los objetos observados van abajo, en tabla de 12 px y recortes de 56 px. Quedan clases `slate`, `white/5` y `text-[9px]`/`text-[10px]`.

## Goal

1. 401 o 403 en cualquier petición autenticada → `logout` → `/login` con aviso **«Tu sesión venció. Entra de nuevo.»** El POST `/auth/login` no usa esa vía: sigue mostrando credenciales incorrectas / cuenta bloqueada.
2. `isAuthenticated` es token presente **y** JWT no vencido. Guardia y `guestGuard` usan esa señal. Un token con `exp` pasado no entra al cascarón ni bloquea `/login`.
3. Crear: `POST /users` (ya no público) con correo (= `username`), contraseña (reglas actuales) y al menos un rol. Editar: `PUT /users/:id` (correo y roles; contraseña opcional). Desactivar: `PATCH /users/inactive`.
4. Solo si el rol **activo** se llama `ADMIN`: grupo Autenticación (y Gestión, que hoy alias a usuarios) en el menú; rutas `/admin/users` y `/admin/roles`; APIs `/users` y `/roles` con `HasRoles(ADMIN)`. Otro rol que navegue ahí va a `/control-panel`.
5. Pipeline `result_interval_seconds = 1.0`. Un JPEG por cámara, ancho ~480. Sin concepto Preview. Objetos arriba en tarjetas grandes; cámaras abajo a tamaño útil. Identidad navy/papel en esa página.

## Non-goals

- Cambiar el turno, `chatService.chat`, `declarePoema` o `{ reply, fuente, movimientos }`.
- Reabrir Motion Studio, paleta, pestañas del chat o el panel de ejecución.
- Alta de `person` (documento, tipo de documento). Este corte no crea ficha de persona; el correo basta para entrar.
- Página nueva de «Panel» de gestión. `/admin/management` sigue redirigiendo a usuarios; el grupo se oculta si no es ADMIN.
- Cambiar el enum de roles (`ADMIN`, `USER`, `STUDENT`, `TEACHER`) ni el picker de rol del login.
- Bump de `schemaVersion` del snapshot de visión. El campo `previewJpegBase64` puede quedar siempre `null`.
- Autenticación del WebSocket distinta de la que ya hay (`access_token` + `activeRole`). Solo: cierre `4001` también cierra la sesión de Angular.

## Approach

Opción A aprobada: un spec, dos pistas en el mismo plan. Auth cierra sesión de verdad, alinea CRUD con el gateway y pone ADMIN como candado de menú + API. Visión baja el intervalo a 1 s, deja de pixelear Preview y reordena la página. El turno no se toca.

## Pista 1 — sesión

Regla **Expired Means Login**: si el servidor rechaza la sesión o el token ya no vale, la UI no finge que sigue dentro.

### Interceptor

En `pmas-web-main/src/app/core/interceptors/auth.interceptor.ts`:

- Si la URL es `POST …/auth/login` (o restore/set-password públicos), no llamar `logout`. El `AuthService.parseError` sigue siendo la fuente del mensaje de credenciales.
- Cualquier otro `HttpErrorResponse` con status 401 o 403 llama `auth.logout('expired')`.
- Se elimina `shouldLogoutOn401` atado al texto `INACTIVE_SESSION_MESSAGE`.

### JWT y guardias

- `AuthService.isAuthenticated`: hay token en memoria/localStorage **y** el payload JWT tiene `exp` (segundos Unix) en el futuro. Token malformado = no autenticado.
- Decodificar el payload con `atob` + `JSON.parse` del segundo segmento. Sin librería nueva.
- `authGuard`: si no autenticado, `logout('expired')` cuando había token (para el aviso) y árbol `/login`.
- `guestGuard`: la misma `isAuthenticated`. Token vencido permite `/login`.
- `AdminShell` (o el `authGuard` autenticado) llama `loadProfile()` si hay token y el perfil aún es `null`, para que el nombre del rol activo exista tras recargar.
- `loadProfile()` que falle (401/403 o red) llama `logout('expired')`, no un `logout()` silencioso.

### Aviso en login

- `logout(reason?: 'expired')` escribe `sessionStorage.prometeo_login_flash = 'expired'` cuando `reason === 'expired'`, limpia token/rol, navega a `/login`.
- `/login` lee la clave al iniciar, la borra, y muestra un recuadro de error (borde `error`, texto 14 px, icono `schedule`) **encima** del formulario, no un toast: «Tu sesión venció. Entra de nuevo.»
- El texto de credenciales incorrectas no cambia.

### WebSocket de visión

Si el socket cierra con código `4001` (token/sesión inválidos en `vision.gateway.ts`), el servicio de visión llama el mismo `logout('expired')`. No reintenta en bucle.

## Pista 1 — usuarios y ADMIN

Regla **Admin Gate**: Usuarios y Roles son de ADMIN. El resto opera el robot.

### API gateway + auth MS

`POST /users`: quitar `@Public()`. `@UseGuards(JwtAuthGuard, RolesGuard)` y `@HasRoles(Roles.ADMIN)` a nivel de `UsersController` y `RolesController` (todos los métodos). `RolesGuard` deja de ser un no-op huérfano: se usa en esos controladores.

`RolesGuard` exige que el **rol activo** (`X-Active-Role`, que ya es el UUID del rol) pertenezca al usuario **y** que el `role.name` de ese rol activo esté en `HasRoles`. Tener ADMIN en la ficha pero operar como `USER` no abre `/users`.

DTO de alta (`CreateUserDto` en gateway y en `pba-ms-auth`), campos que acepta este corte:

| Campo | Alta | Edición (`UpdateAuthUserDto` / PUT) |
|---|---|---|
| `username` | correo, obligatorio | opcional |
| `password` | obligatorio, mismas reglas que el PUT actual (≥ 8, mayúscula, minúscula, número, especial, sin espacios) | opcional |
| `role_ids` | UUID[], mínimo 1 | opcional; si viene, reemplaza los roles (`setRoles`) |
| `person_id` | opcional, sin cambio | no se toca |

`assign_student_role` no se usa en el alta desde la mesa: los roles son los de `role_ids`.

Repositorio `users.repository.create`: validar la contraseña **en claro**, luego hashear. Dejar de generar temporal cuando el DTO trae `password`. Crear `user_role` por cada id de `role_ids`.

`PUT /users/:id` sigue en `updateAuthUser`. Si el body trae `role_ids`, después de actualizar correo/clave se llama a `rolesService.setRoles`.

No se añade `DELETE /users/:id`. La UI de «eliminar» llama `PATCH /users/inactive` con `{ user_id, reason }`.

### Angular

- `User.id` y `Role.id` son `string` (UUID), no `number`.
- Formulario de alta/edición: correo, contraseña (obligatoria solo en alta; vacía en edición = no cambiar), checkboxes de roles. Sin campo «usuario» distinto del correo. Sin nombre/apellido en este corte.
- Alta: `POST ${GATEWAY_URL}/users`. Edición: `PUT ${GATEWAY_URL}/users/${id}`. Desactivar: `PATCH ${GATEWAY_URL}/users/inactive`.
- Contraseña de alta: el cliente no envía si no cumple las reglas; el error del API se muestra en el modal.
- `roleGuard`: `activeRoleName === 'ADMIN'`; si el perfil no está, espera `loadProfile()`; si no es ADMIN → `/control-panel`.
- Rutas `/admin/users` y `/admin/roles`: `authGuard` + `roleGuard`.
- Sidebar: el grupo `autenticacion` y el grupo `gestion` (hoy solo redirige a usuarios) se omiten si `activeRoleName !== 'ADMIN'`. Robótica (movimientos, visión, chat, secuencias, iframe) se queda para todos los autenticados.
- `isAdmin` se deriva del **nombre** del rol activo (`ADMIN`), no del UUID.

## Pista 2 — visión

Regla **Objects First**: primero se leen las detecciones; las cámaras ocupan el ancho útil debajo. No hay Preview.

### Cadencia y encode

- `pmai-mai-core/settings.toml` `[pipeline] result_interval_seconds = 1.0`.
- Default en `PipelineSettings` = `1.0` (hoy `5.0`).
- `VisionController.get_snapshot`: un `frame_to_jpeg_base64` por cámara con `thumb_max_width`. No segundo encode de preview. `preview_jpeg_base64` siempre `null`.
- `thumb_max_width`: techo del schema a 960; el cliente pide **480**.
- Gateway WS: default `thumbMaxWidth` 480. Angular deja de enviar `setSelection` y `setQuality` con preview. Se puede seguir enviando `setQuality` solo con `thumbMaxWidth: 480`.
- El intervalo WS de 500 ms puede quedarse: el cuello real era el pipeline a 5 s. No se baja de 500 ms en este corte.

### Layout (`robotics-vision.html` / `.ts`)

Orden vertical único (móvil y escritorio):

1. Cabecera de página: icono en pozo navy + título «Visión» (Space Grotesk 24 px) + una línea de guía. Estado WS en tinta quieta ≥ 12 px. Sin `industrial-grid`.
2. **Objetos observados** a ancho completo. Tarjetas (no tabla): recorte grande (≥ 128 px de lado), etiqueta 18 px, confianza 14 px, cámaras vistas en tinta quieta. Vacío: «No hay objetos en este snapshot.»
3. **Cámaras** debajo, cuadrícula `1 / 2 (sm) / 3 (lg)`, `aspect-video`, JPEG al ancho de la celda. No son botones de Preview. Nombre y `fps` en 12–14 px.

Prohibido en esta página: la palabra «Preview», `previewSrc`, `text-slate-*`, `border-white/5`, `text-[8px]`–`text-[10px]`, `shadow-xl`, lienzo `#ffffff`.

Tokens: campo `bg-background`, tarjetas `bg-surface` + `border-outline`, tinta `text-on-surface` / `text-on-surface-variant`, acento de conexión cian.

## PRODUCT / DESIGN

`PRODUCT.md` principio 5 deja de decir que auth y visión son cortes siguientes. Evidence añade esta spec. El propósito sigue siendo operar; se añade: sesión vencida se dice en login; objetos de visión se leen antes que las cámaras.

`DESIGN.md` Layout: un bullet para `/login` (aviso de sesión vencida sobre el formulario) y uno para Visión (objetos en tarjetas grandes, cámaras debajo a ~480 px, sin Preview). No se reabre la paleta.

## Pruebas

Auth (Vitest spec-as-file-read y/o unidad):

- Interceptor: 401 genérico y 403 → `logout`; POST login 401 → no `logout`.
- `isAuthenticated` falso si `exp` pasado.
- Login HTML contiene «Tu sesión venció. Entra de nuevo.»
- `users.ts` pega a `/users` y `/users/inactive`, nunca `/auth/users`.
- `app.routes.ts`: `/admin/users` y `/admin/roles` incluyen `roleGuard`.
- Sidebar no lista Usuarios/Roles salvo ADMIN (test del filtro o del template).
- Gateway: `users.controller.ts` sin `@Public()` en `create`; aparece `HasRoles` y `Roles.ADMIN`.
- `create-user.dto.ts` (gateway y auth) declara `password`.
- Repositorio: la validación corre sobre el texto plano (test unitario si ya hay harness; si no, spec-as-file-read de que `validatePassword` recibe `createUserDto.password` antes del hash).

Visión:

- `settings.toml` y `settings.py` = `1.0`.
- `vision_controller.py` no llama `frame_to_jpeg_base64` dos veces por cámara.
- HTML de visión: «Objetos observados» aparece antes de las cámaras; no contiene `Preview`; no contiene `text-slate-` ni `text-[9px]` ni `text-[10px]`.
- `robotics-vision.ts` no define `previewSrc`.

No se añade prueba e2e de navegador obligatoria. La verificación humana: login con JWT vencido (o 401 forzado) muestra el aviso; un USER no ve Usuarios; ADMIN crea un usuario y entra con ese correo; visión refresca ~1 s, objetos arriba, cámaras grandes.

## Error handling

| Fallo | Tratamiento |
|---|---|
| JWT `exp` pasado al recargar | `/login` + aviso de sesión vencida; no cascarón |
| 401/403 de API autenticada | igual |
| 401 de POST login | «Credenciales incorrectas.» (o el mensaje del API); se queda en el formulario |
| WS visión 4001 | logout + aviso; no reconectar |
| Alta sin contraseña o reglas | el modal no cierra; muestra el mensaje del API o la validación local |
| USER abre `/admin/users` | redirect a `/control-panel`, sin 403 de API |
| USER llama `/users` a mano | 403 del gateway; el interceptor cierra sesión (pedido: cualquier 403) |
| BLIP / turno | fuera de alcance |
| Snapshot sin cámaras | mensaje «Sin cámaras en el snapshot.» bajo el bloque de objetos |

## Lo que no se toca

`pmai-model-vision-language`, `pmai-model-context`, `pba-ms-robotics`, `pba-ms-management` (el reenvío de chat), `pmas-web-motion-studio`, `interaction_turn.py`, `declarePoema`. No se reconecta `chatService.chat` a OpenAI.
