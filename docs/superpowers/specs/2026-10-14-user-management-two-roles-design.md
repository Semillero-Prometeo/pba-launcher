# Gestión de usuarios: dos roles y ficha de persona — design

Date: 2026-10-14  
Status: approved by user on 2026-10-14  
Scope: un corte. Enum de roles solo `ADMIN` y `USER`; migración STUDENT/TEACHER → USER; alta y edición escriben `user` + `person` + `user_role`; contraseña igual a la actual no bloquea el guardado; selector de rol al entrar solo si hay más de uno; se quitan la página de Roles y el grupo Gestión. Dueños: `pmas-web-main`, `pba-ms-gateway`, `pba-ms-auth`, y `PRODUCT.md` / `DESIGN.md` en la raíz del lanzador.

Relación: el spec `2026-10-14-auth-session-admin-gate-vision-layout-design.md` sigue vigente para sesión, `HasRoles(ADMIN)` y visión. Este corte **lo corrige** en tres puntos que ese archivo dejó fuera: (1) sí hay ficha de persona, (2) el enum deja de incluir STUDENT/TEACHER, (3) no hay CRUD de roles ni ítem Gestión. No reabre paleta, chat, estudio, turno ni el pipeline de visión.

## Problem

El alta reciente no crea `person`. `findAll` exige `person_id: { not: null }`, así que el usuario “se crea” y no aparece en la tabla.

Editar manda la contraseña si el campo no está vacío. El API compara con el hash actual y responde «Esta contraseña ya ha sido utilizada…». El navegador suele autocompletar el campo aunque el operador no quisiera cambiarla. El formulario no tiene nombres, documento ni teléfono.

Siguen existiendo STUDENT y TEACHER en Prisma, seed y checkboxes. La página `/admin/roles` es un CRUD de mentira. El grupo **Gestión** del sidebar redirige a usuarios. `login.ts` abre el selector de rol aunque `AuthService` ya haya autoelegido el único. `create` exige `FRONT_END_URL` o responde 500. `person.email` admite 40 caracteres y `username` 120. La baja se llama «Eliminar» y traga el error del API. La tabla duplica el correo y conserva `industrial-grid` / `slate-*` / `9px`.

## Goal

1. Solo dos roles: `ADMIN` y `USER`. Un usuario puede tener uno o los dos; al menos uno es obligatorio. STUDENT y TEACHER pasan a USER y se borran.
2. ADMIN (rol **activo**) gestiona usuarios y opera el robot. USER solo opera (lo ya implementado).
3. Crear y editar cargan correo, nombres, apellidos, tipo y número de documento, teléfono opcional, contraseña y roles. La lista muestra a quien se acaba de crear.
4. Editar con contraseña vacía o igual a la actual guarda el resto y no error. Contraseña nueva queda usable al entrar (`is_first_login = false`).
5. Al entrar: un rol se selecciona solo y no hay modal; dos roles, se elige cuál usar.
6. Sin página de Roles. Sin grupo Gestión en el sidebar.

## Non-goals

- Registro público (`/register`).
- Reactivar dados de baja, CRUD de tipos de documento, o página nueva de «Panel» de gestión.
- Cambiar JWT, `X-Active-Role` (sigue siendo el UUID del rol elegido), `HasRoles` del corte anterior, o el turno.
- Reconectar `chatService.chat` a OpenAI. `declarePoema` se queda.
- Motion Studio, paleta, pestañas del chat, pipeline de visión.

## Approach

Opción A aprobada: arreglar el flujo actual. Una pantalla de usuarios. El API de `POST`/`PUT /users` escribe persona y cuenta. El enum y el seed se reducen a dos roles. Se quitan Roles y Gestión del menú. Login usa `needsRoleSelection`.

## Roles fijos

Prisma enum `Roles` en `pba-ms-auth` y `pba-ms-gateway`: `ADMIN`, `USER`. El seed solo crea esas dos filas.

Migración de datos, en este orden:

1. Resolver el id del rol `USER`.
2. Cada `user_role` cuyo `role.name` sea `STUDENT` o `TEACHER`: si el usuario ya tiene `USER`, borrar la fila; si no, cambiar `role_id` al de `USER`.
3. Borrar las filas `role` `STUDENT` y `TEACHER`.
4. Alterar el enum de Postgres para dejar solo `ADMIN` y `USER`.

`GET /roles` se queda (ADMIN, para los checkboxes). La UI Angular de CRUD de roles y la ruta `/admin/roles` se eliminan. Los endpoints de escribir roles en el API pueden quedar; este corte no los usa.

Un usuario puede tener ADMIN, USER o ambos. `role_ids: []` en alta o edición es 400. No se puede dejar el sistema sin ningún usuario activo (`deleted_at` null) con rol ADMIN: ni quitándole el rol, ni dándolo de baja.

## Entrada

`AuthService.login` ya autoelige si `user_role.length === 1`. `login.ts` deja de abrir el modal cuando `availableRoles().length !== 0`. Usa `needsRoleSelection`: más de un rol y aún no elegido. Un rol o cero: navega a `/control-panel`. El aspecto del modal de rol no cambia. `X-Active-Role` sigue siendo el UUID.

## Alta, edición y persona

Payload de `POST /users` y `PUT /users/:id` (gateway y auth MS):

| Campo | Alta | Edición |
|---|---|---|
| `username` | correo, obligatorio, ≤ 120 | opcional |
| `password` | obligatorio, mismas reglas (≥ 8, mayúscula, minúscula, número o especial, sin espacios) | opcional; vacío o omitido = no cambiar |
| `role_ids` | UUID[], mínimo 1, solo ids de ADMIN o USER | mínimo 1 si viene; reemplaza con `setRoles` |
| `person.first_name` | obligatorio, ≤ 50 | obligatorio si viene `person` |
| `person.last_name` | obligatorio, ≤ 50 | igual |
| `person.document_type_id` | UUID de `GET /document-types`, obligatorio | igual |
| `person.document_number` | obligatorio, ≤ 11 | igual |
| `person.phone` | opcional, ≤ 15 | opcional |

El servidor pone `person.email = username`. El cliente no manda email duplicado.

`POST /users` en una transacción: crea `person`, crea `user` conectado, crea `user_role`. No consulta `FRONT_END_URL`. Duplicado de correo o de `(document_number, document_type_id)` → 400 con mensaje claro.

`PUT /users/:id` (`updateAuthUser`):

- Si hay `person` en el usuario, actualiza esos campos. Si no hay (huérfanos del corte anterior), crea la ficha y la conecta.
- `username` cambia `user.username` y `person.email`.
- Contraseña: omitida/vacía → no tocar. Si `bcrypt.compare` con el hash actual es verdadero → no tocar, no error. Si es distinta → hashear, `is_first_login = false`.
- Deja de exigir «al menos username, password o role_ids»: actualizar solo persona es válido.
- `autocomplete="new-password"` en el input de contraseña del modal.

`person.email` en Prisma y DTO pasa de 40 a 120 caracteres, alineado con `username`.

`findAll`: quitar `person_id: { not: null }`. Añadir `deleted_at: null`. `GET /users?take=50` y `GET /roles?take=50` (no 10).

Baja: sigue `PATCH /users/inactive`. El diálogo dice «Dar de baja», no «no se puede deshacer». Si el API falla, el diálogo permanece y muestra el mensaje. Un admin no se da de baja a sí mismo (400).

## Angular — usuarios y menú

Formulario único crear/editar con los campos de la tabla. Select de tipo de documento desde `GET /document-types`. Checkboxes solo de los roles que devuelve `GET /roles` (quedarán ADMIN y USER).

Tabla: Nombre, Correo, Documento, Roles, Acciones. Sin columna que duplique el correo. Identidad de `DESIGN.md`: sin `industrial-grid`, `text-slate-*`, `border-white/5`, `text-[9px]`/`text-[10px]`. Tipografía ≥ 12 px etiquetas, ≥ 14 px cuerpo.

Sidebar: grupo Autenticación solo con Usuarios, visible si `activeRoleName === 'ADMIN'`. Se eliminan el ítem Roles, el grupo Gestión y `openGroups` de `gestion`. Rutas: se quitan `/admin/roles` y `/admin/management`. `roleGuard` sigue en `/admin/users`.

## PRODUCT / DESIGN

`PRODUCT.md` principio 5: Usuarios es de ADMIN; los roles del producto son ADMIN y USER; la ficha incluye nombre y documento. Evidence añade esta spec. Roles deja de nombrarse como pantalla.

`DESIGN.md` Layout: un bullet para `/admin/users` (tabla Nombre / Correo / Documento / Roles; modal con persona, contraseña y checkboxes). El selector de login solo aparece con más de un rol.

## Pruebas

Estilo del corte anterior (Vitest spec-as-file-read, `node --test` en gateway/auth).

- Enum Prisma (auth y gateway) y seed: no contienen STUDENT ni TEACHER.
- `users.service.create` no llama `FRONT_END_URL`. Create incluye creación de `person`.
- `updateAuthUser`: `bcrypt.compare` verdadero no lanza; `is_first_login` no se pone `true` al cambiar clave.
- `findAll`: no filtra `person_id: { not: null }`; sí `deleted_at: null`.
- Sidebar: no lista Roles ni Gestión.
- `app.routes.ts`: no existe `/admin/roles`.
- `login.ts`: navega sin modal si no `needsRoleSelection`.
- `users.ts` / HTML: campos `first_name`, `document_number`; `autocomplete="new-password"`; no `industrial-grid` ni `text-slate-`.
- `person.email` MaxLength / VarChar 120.

Verificación humana: ADMIN crea un usuario USER con nombre y cédula; aparece en la lista; entra con un rol sin selector; editar sin tocar contraseña guarda; editar con la misma contraseña autocompletada guarda; un usuario con ADMIN+USER ve el selector.

## Error handling

| Fallo | Tratamiento |
|---|---|
| Correo ya usado | 400; el modal no cierra |
| Documento + tipo ya usados | 400; el modal no cierra |
| Contraseña de alta inválida | validación local + DTO; no cierra |
| Contraseña de edición igual a la actual | no-op; se guardan el resto de campos |
| Contraseña de edición vacía | no se manda; no se toca el hash |
| `role_ids` vacío | 400 |
| Quitar el último ADMIN o darlo de baja | 400 |
| Darse de baja a sí mismo | 400 |
| Baja con error de API | diálogo abierto + mensaje |
| `FRONT_END_URL` ausente | no afecta el alta de este corte |
| USER abre `/admin/users` | redirect a `/control-panel` (corte anterior) |

## Lo que no se toca

`pmai-mai-core`, `pmai-model-vision-language`, `pmai-model-context`, `pba-ms-robotics`, `pba-ms-management`, `pmas-web-motion-studio`, `interaction_turn.py`, `declarePoema`. No se reconecta `chatService.chat` a OpenAI.
