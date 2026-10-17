# Ruta de respuesta, importar pares y estudio — design

Date: 2026-10-17  
Status: approved by user on 2026-10-17  
Scope: un spec, tres cortes en el mismo ciclo. Dueños: `pba-ms-management`, `pba-ms-gateway`, `pmai-mai-core`, `pmas-web-main`, `pmas-web-motion-studio`. Robótica no cambia de contrato; el ingest ya acepta `blocks_neutro` vacío o lleno.

Relación: el spec `2026-10-16-legacy-sequence-import-design.md` sigue vigente para **aceptar la lista de 7-tuplas**, categoría a mano y descripción vacía. Este corte **anula** de ese spec: omitir archivos `NEUTRO`, generar neutro al importar, y el sheet inferior. El turno por dentro no se reabre. `declarePoema` sigue en OpenAI y habla.

## Problem

1. Chat y micrófono solo disparan el turno de mai-core. El camino viejo (`chatStructured` + `speak`) existe pero solo lo usa `declarePoema`. No hay forma de apagar la automatización de turnos ni de elegir modelo como en un IDE.
2. El neutro generado por rebobinado no es fiable en el androide. Los JSON Qt vienen en pares (`ABRAZOIZQ 7.1.json` + `ABRAZOIZQ NEUTRO 7.1.json`) y el importador omite el segundo.
3. En el panel, Neutro aparece aunque la secuencia no tenga pista. En el estudio, los nombres largos se cortan, la card del bloque no muestra todos los parámetros, y generar neutro no avisa que hay que revisarlo. Arduino conectado no se ve ni en el panel ni en el estudio.

## Goal

1. Interruptor de sistema **Turnos automáticos** (ADMIN). Picker de modelo del chat como elección del sistema (cualquiera con chat). Chat y micrófono usan la misma regla. Básico siempre habla.
2. Diálogo grande de importación: emparejar gesto + archivo NEUTRO por nombre; el operador confirma, cambia o deja sin neutro; se puede seguir cargando. No se genera neutro al importar.
3. Panel: sin `blocks_neutro` no hay botón Neutro. Pastilla de Arduino conectado.
4. Estudio: lista agrupada por categoría, sin Play; cards con todos los campos del bloque; aviso de revisión humana al generar neutro; misma pastilla de Arduino.

## Non-goals

- Websocket / live-update del picker entre pestañas.
- Tabla Prisma nueva en management.
- Cambiar `responder()`, BLIP, Milvus, Gemma, `getActions` o la cola Normal → 1 s → neutro.
- Reconectar `declarePoema` al turno.
- Autoguardar el neutro generado.
- Inferir categoría del nombre del archivo.
- Editar `interfaz_record9_5_1.py`.

## Approach

Opción A aprobada: **un enrutador en management**. El JSON de ruta vive en disco. `chat()` elige Básico (`chatStructured` + `speak`) o Complejo (`maiCore.ask`). El micrófono deja `turn.ask_async` y llama al mismo `MANAGEMENT_MS.chatService.chat`.

---

## 1. Ruta de respuesta

### Estado

Archivo JSON (no Prisma). Ruta por env `MS_MANAGEMENT_CHAT_ROUTE_PATH`, por defecto `data/chat-route.json` relativo al cwd del servicio. Si falta o está corrupto, se recrea:

```json
{ "automationEnabled": true, "selectedModel": "complejo" }
```

Valores de `selectedModel`: `basico` | `complejo`.

### Decisión en `ChatService.chat`

| automationEnabled | selectedModel | Camino |
|---|---|---|
| false | (se ignora; queda `basico`) | `chatStructured` + `speak` |
| true | `basico` | `chatStructured` + `speak` |
| true | `complejo` | `maiCore.ask` |

Básico responde `{ reply, fuente: "OpenAI", movimientos: [] }`. Complejo deja `fuente` y `movimientos` al turno (`caché`, `OpenAI`, `Gemma (local)`, `ocupado`, `voz corta`, `disculpa`).

Si OpenAI básico falla: 502 como hoy; **no** se cae al turno. Si el turno falla: se propaga el error de `maiCore.ask`.

`declarePoema` no lee este JSON.

### Micrófono

`AudioService._dispatch_transcript` llama `ManagementMsService.chat(transcript)` (NATS `MANAGEMENT_MS.chatService.chat`) y no `turn.ask_async`. En básico, management habla. En complejo, el turno habla y mueve. No se llama `speak` dos veces.

### Contratos NATS (management)

| Subject | Quién | Cuerpo | Efecto |
|---|---|---|---|
| `chatService.getRoute` | autenticado | — | Lee el JSON |
| `chatService.setAutomation` | ADMIN | `{ enabled: boolean }` | Escribe `automationEnabled`. Si `enabled` es false, `selectedModel` pasa a `basico`. Al volver a encender no se restaura Complejo: sigue `basico` hasta que alguien lo elija |
| `chatService.setModel` | autenticado | `{ model: "basico" \| "complejo" }` | Escribe `selectedModel`. Si `model` es `complejo` y `automationEnabled` es false: **409** |

### HTTP (gateway, JWT)

| Método | Ruta | Rol |
|---|---|---|
| GET | `/chat/route` | autenticado |
| PATCH | `/chat/route/automation` | ADMIN (`X-Active-Role`) |
| PATCH | `/chat/route/model` | autenticado |

`POST /chat/question` no cambia de forma. El cuerpo sigue siendo el mensaje; la ruta se lee en el servidor, no la manda el cliente.

### Interfaz (Chatbot IA)

Solo en la pestaña **Chatbot IA**, no en Decir ni en el panel.

- Interruptor **Turnos automáticos** a la derecha de las pestañas. Lo ve y lo mueve solo ADMIN.
- Picker junto al campo de mensaje: `Básico (OpenAI)` y, si los turnos están on, `Complejo (turno)`. Si los turnos están off, Complejo no aparece.
- Al cargar: `GET /chat/route`. Cambios: PATCH y refresco. Sin websocket: otro usuario no se entera hasta recargar.
- Cada respuesta sigue mostrando `Fuente`.
- El STT del recuadro del chat sigue mandando texto a `POST /chat/question`.

---

## 2. Importar pares y panel

### Diálogo

Reemplaza el sheet inferior (60 %). Ocupa casi toda la pantalla. Se pueden seguir eligiendo archivos o carpetas sin cerrarlo.

### Emparejado

1. Cada JSON se parsea (lista de 7-tuplas u objeto origen). JSON inválido: error de esa fila; no se envía.
2. Si el nombre (sin `.json`) contiene `\bneutro\b` (sin distinguir mayúsculas): es **candidato a neutro**, no una fila de gesto.
3. Clave de par: nombre sin extensión, en minúsculas, se quita `\bneutro\b`, se colapsan espacios. `ABRAZOIZQ 7.1` y `ABRAZOIZQ NEUTRO 7.1` comparten clave. `BRAZOIZQ CON GUINO 7.3` y `… NEUTRO 7.0` **no** auto-empatan (la versión queda en la clave); el operador los une a mano.
4. Un archivo neutro no puede quedar asignado a dos gestos.
5. Por fila de gesto: nombre editable, categoría, Arduino, selector de neutro (sugerido, otro del lote, o **Sin neutro**).
6. **No** se llama `generateNeutroFrom` en el importador.
7. POST: `blocks` del gesto; `blocks_neutro` del archivo emparejado o `[]`. Descripción `""`. Categoría y Arduino obligatorios para enviar esa fila.
8. Objeto origen que ya trae `blocks_neutro` y cuyo nombre **no** es neutro: se usa esa pista; el selector puede sustituirla por un archivo del lote o dejarla.

`shouldSkipLegacyNeutroFile` deja de omitir: esos archivos alimentan el selector.

### Panel de control

- Botón **Neutro** solo si `blocks_neutro.length > 0`. Si no, un solo botón **Normal** (el grid de dos columnas no reserva hueco vacío).
- Pastilla junto al título: cada ~5 s `GET /sequence/arduinos`.
  - Uno: punto verde + `Arduino #id · puerto`.
  - Varios: punto verde + `N conectados`.
  - Lista vacía o error de red: punto apagado + `Sin Arduino`. No se finge conectado.
- Sin endpoint nuevo.

---

## 3. Motion Studio

- Lista de secuencias **agrupada por `category`**. Sin categoría: grupo **Sin categoría**. El nombre se muestra entero (varias líneas si hace falta).
- Se quita el botón **Play** de cada fila de esa lista. Abrir la secuencia se queda. Play del timeline / hardware no se toca.
- Pastilla de Arduino igual que en el panel (`GET /sequence/arduinos` cada ~5 s), junto al estado Acoplado / Suelto o encima de la lista.
- Card del bloque en la línea de tiempo: hoy `nombre Pos vel`. Debe mostrar **nombre, pca, servo, inicio, dur, pos, vel** y `arduino_id` si no es 0. El inspector no cambia.
- Junto a **Generar neutro**, aviso fijo (antes y después de pulsar): *El neutro generado debe revisarlo una persona. En el androide no es fiable.* El rewind no cambia. No se auto-guarda.

---

## Error handling

| Caso | Resultado |
|---|---|
| Turnos off o modelo básico | OpenAI + speak; `fuente: OpenAI` |
| OpenAI básico cae | 502; no se usa el turno |
| Turnos on + complejo | `maiCore.ask` |
| `setModel: complejo` con turnos off | 409 |
| JSON de ruta corrupto | Defaults on + complejo |
| Mic + básico | Management habla una vez |
| Mic + complejo | El turno habla y mueve |
| JSON de importación inválido | Fila en error; el resto sigue |
| Neutro ya asignado a otro gesto | No se puede elegir de nuevo |
| Importar sin par | `blocks_neutro: []`; panel sin botón Neutro |
| `/sequence/arduinos` falla | Pastilla «Sin Arduino» |

## Testing

`pba-ms-management`:

- `chat()` con automation off → `chatStructured` + `speak`; no llama `maiCore.ask`.
- automation on + `basico` → igual.
- automation on + `complejo` → `maiCore.ask`; no `speak` extra.
- `setAutomation(false)` deja `selectedModel` en `basico`.
- `setModel("complejo")` con automation off → 409.
- Archivo corrupto → defaults.

`pmai-mai-core`:

- `_dispatch_transcript` llama `chatService.chat`, no `ask_async`.

`pmas-web-main` (Vitest):

- Empareja `ABRAZOIZQ 7.1` con `ABRAZOIZQ NEUTRO 7.1`.
- `7.3` y `NEUTRO 7.0` no auto-empatan.
- Nombre con NEUTRO ya no se omite; entra al pool de neutros.
- Lista de 7-tuplas sin generar `blocksNeutro` (vacío hasta emparejar).
- Panel: `hasNeutro` falso si `blocks_neutro` vacío.

`pmas-web-motion-studio`:

- `renderLibrary` agrupa por categoría y no pinta Play.
- Card del bloque incluye pca, servo, inicio, dur, pos, vel.
- El botón de generar neutro tiene el aviso de revisión humana.

## Docs

`AGENTS.md` y la regla corta del turno: el chat y el micrófono pasan por `chatService.chat`; la ruta (Básico / Complejo) la decide management. No se vuelve a conectar `chat` a OpenAI a ciegas: solo si la ruta es básica. `declarePoema` no cambia.

## Decisions locked

- Un enrutador en management; estado en JSON; defaults on + complejo.
- El picker del chat es la elección del sistema; el micrófono la sigue.
- ADMIN: interruptor. Quien chatea: modelo.
- Importar empareja archivos; no genera neutro.
- Neutro en panel solo si hay pista.
- Estudio: grupos, sin Play en la lista, cards completas, aviso al generar, pastilla de Arduino (panel y estudio).
