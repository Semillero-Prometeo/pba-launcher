# Par gesto–neutro, categorías y cola de hardware — design

Date: 2026-10-14  
Status: approved by user on 2026-10-14  
Scope: cada secuencia del estudio es un gesto más su neutro editable; el panel las agrupa por categoría; robótica encola la ejecución del turno (normal → 1 s → neutro → 1 s) y expone el estado para que el panel muestre lo que va al hardware y pueda detenerlo.

Relación: el spec `2026-10-14-motion-studio-integration-design.md` sigue vigente para iframe, JWT, `id` y origen. Este corte **amplía** el JSON, `executeAction` (encola en vez de rechazar) y el panel de control. No cambia la tabla Markdown ni la firma `executeAction(action_id, arduino_id)`.

## Problem

El estudio solo guarda una pista. Los «neutros» de hoy son archivos aparte (`…NEUTRO…`). El turno llama `executeAction` por cada id sin esperar; si ya hay reproducción, robótica rechaza el siguiente. El panel agrupa por carpeta en el nombre, tiene un botón por archivo y consulta la cadena cada 60 s: no sirve para ver en vivo lo que el turno va a mandar al Arduino, ni para impedir un Play de interfaz que pise el gesto del turno.

## Goal

1. Al crear en el estudio: gesto configurado + pista neutra (generada y editable) + una categoría obligatoria de seis.
2. Un archivo, un `id`. `getActions` una fila por gesto, no por neutro.
3. Turno: por cada id, robótica ejecuta **normal → 1 s → neutro → 1 s**, encolando si ya hay trabajo. mai-core no espera ni inserta neutros.
4. Panel: seis secciones; cada secuencia con **Normal** y **Neutro**; recuadro **En hardware** con fase actual y cola; mientras `busy`, no se inicia otro gesto desde la interfaz; **Detener** sí.
5. El serial tiene un solo dueño: `pba-ms-robotics`.

## Non-goals

- Cambiar `getActions` / `executeAction` de firma, la tabla Markdown, `declarePoema` o el chat.
- WebSocket; el runtime se consulta por HTTP.
- Reescribir solos los JSON antiguos ni inferir categoría por el nombre.
- Borrar el API de cadena (`chain/start`); el panel deja de usarlo en esta vista.
- Neutro de emergencia al Stop (el robot se queda en la última posición enviada).
- Que el estudio acoplado abra el puerto serie.

## Approach

Opción 1 aprobada: un JSON con dos pistas; cola en robótica; panel por categoría; `executeAction` del turno encola el par.

## Arquitectura

| Pieza | Hace | No hace |
|---|---|---|
| `pmas-web-motion-studio` | Edita gesto y neutro; categoría; genera neutro; guarda origen | No asigna `id`; no abre serial en acoplado |
| `pba-ms-robotics` | Ingest, cola, pausas de 1 s, `getActions` solo pares completos, `GET runtime` | No habla con el modelo |
| `pba-ms-gateway` | `mode` en play; `GET /sequence/runtime` | No arma la cola |
| `pmai-mai-core` | `executeAction` por id, como hoy | No espera, no encola, no conoce el neutro |
| `pmas-web-main` panel | Seis grupos, dos botones, En hardware, Stop | No arma cadenas a mano |

`busy` = hay fase en curso o cola no vacía o espera de 1 s. Play de panel/estudio con `busy` → error. `executeAction` de turno con `busy` → se encola.

## Categorías

Exactamente una, obligatoria al guardar:

`cara` | `cuello` | `brazo_derecho` | `brazo_izquierdo` | `torso` | `cadera`

Etiquetas de panel, en este orden: Cara, Cuello, Brazo derecho, Brazo izquierdo, Torso, Cadera.

## Formato de origen (estudio)

Sin `id` ni `version`.

```json
{
  "name": "saludo",
  "description": "Saludo con el brazo derecho",
  "category": "brazo_derecho",
  "arduino_id": 0,
  "blocks": [[0, 0, 0.0, 2, 850, 5, "P0_S0"]],
  "blocks_neutro": [[0, 0, 0.0, 2, 500, 5, "P0_S0"]]
}
```

- `name` 1–80. `description` 0–280, una línea.
- `blocks` y `blocks_neutro`: cada uno al menos un 7-tupla. Pueden usar servos distintos.
- Guardar sin categoría o sin alguna pista: error; no hay archivo canónico.

**Generar neutro:** por cada `(pca, servo)` que aparezca en `blocks`, tomar la `pos` del bloque de **menor `inicio`** (empate: el primero en el arreglo). Emitir un bloque `[pca, servo, 0, 2, pos, vel, nombre]` con `vel` y `nombre` de ese bloque semilla. No se ejecuta solo al editar el gesto: hay botón **Generar neutro**. Si ya existe pista, se pide confirmación y se reemplaza.

## Formato canónico (robótica)

Ingest añade `version` e `id` (mismas reglas de `id` que el spec del estudio). Convierte ambas pistas a `MotionBlock[]` (`blocks`, `blocks_neutro`). Overwrite del mismo `name` conserva `id`.

Archivo en disco sin `category` o sin `blocks_neutro` no vacío: aparece en `listSequences`; **no** en `getActions` ni en el panel de ejecución.

## Cola

Un reproductor. La cola es una lista de **pasos**, no de ids sueltos.

Paso: `{ "id" | null, "name", "mode": "normal" | "neutro" | "espera", "source": "turno" | "panel" | "estudio" }`.  
`espera` dura 1,0 s fijos. `id` nulo solo en play de bloques crudos del estudio (`name` vacío o el del formulario).

**Turno — `executeAction(action_id, arduino_id)`:**

1. `find_by_id`. Si no hay secuencia: escritura serial como hoy.
2. Si hay secuencia pero no es par completo: omitir (no serial). Log. Respuesta ok de omisión, el turno sigue.
3. Si es par: encolar `normal`, `espera`, `neutro`, `espera` de ese id, `source=turno`. Si el reproductor está idle, arrancar. Nunca rechazar por ocupado. La llamada **regresa en cuanto los cuatro pasos están en cola** (o el primero arrancó), no cuando el par termina. El timeout de 10 s de mai-core no cubre la duración del gesto.

Orden si el turno manda `[1, 2, 3]`:  
`1 normal → 1 s → 1 neutro → 1 s → 2 normal → 1 s → 2 neutro → 1 s → 3 normal → 1 s → 3 neutro → 1 s`.

**Panel — `POST /sequence/play`:** cuerpo con `mode`: `normal` | `neutro` (default `normal`) y `name` o `blocks` de esa pista. Encola **un** paso de esa pista, `source=panel`, **sin** espera detrás. Si `busy` → error (no encolar).

**Estudio acoplado:** igual que panel, `source=estudio`. Play local (suelto) solo mueve el cabezal.

**Stop:** `POST /sequence/stop` corta la fase, cancela la espera, vacía la cola. No envía un neutro extra.

Al reiniciar el proceso: cola vacía. No se persiste.

Arduino ausente al **disparar** un paso de reproducción: se registra, se descarta ese paso, se sigue con el resto de la cola (incluida una espera que toque).

## Runtime

`GET /sequence/runtime` (gateway → NATS):

```json
{
  "busy": true,
  "source": "turno",
  "current": { "id": 1, "name": "saludo", "mode": "normal" },
  "queue": [
    { "id": 1, "name": "saludo", "mode": "espera" },
    { "id": 1, "name": "saludo", "mode": "neutro" }
  ]
}
```

Durante la pausa, `current.mode` es `espera` y `current.name` / `id` son los del gesto cuya fase acaba de terminar. `queue[0]` es lo siguiente al hardware.

Idle: `{ "busy": false, "source": null, "current": null, "queue": [] }`.

## Superficie

### Panel (`control-panel`)

Seis secciones fijas en el orden de categorías. Cada secuencia: nombre, descripción, Normal, Neutro. `busy` deshabilita Normal y Neutro. Detener visible siempre.

Columna derecha: **En hardware** (origen, fase actual, cola). Se elimina de esta vista el constructor de cadena. Logs se quedan.

Filtro: las seis categorías más «Todas». Búsqueda por nombre y descripción.

Poll: 500 ms si `busy`, 3 s si idle. Si runtime falla: mensaje «sin estado»; botones de ejecutar se tratan como ocupados hasta que vuelva o el usuario recargue. Stop se sigue ofreciendo.

### Estudio

Selector de categoría. Línea de tiempo con gesto y neutro distinguibles (conmutador o doble fila). Generar neutro. Play usa la pista activa. Guardar envía ambas. La lista lateral muestra el gesto, no un segundo ítem «neutro».

Play acoplado respeta `busy` (error, no bucle de auth).

### Importador Angular

Origen nuevo válido → ingest. Falta `category` o `blocks_neutro` → esa fila se rechaza; las demás siguen.

## Fallos

| Situación | Resultado |
|---|---|
| Guardar sin categoría o sin neutro | Error; no hay canónico |
| Play panel/estudio con `busy` | Error; cola intacta |
| `executeAction` turno con `busy` | Encola |
| Id de turno sin par o desconocido como secuencia | Omitir si era secuencia incompleta; serial si no hay secuencia |
| Stop idle | Ok, no había trabajo |
| Arduino ausente al disparar un paso | Log, descartar paso, seguir cola |
| Runtime caído | Panel: sin estado; ejecutar bloqueado; Stop disponible |
| JSON legado | `listSequences` sí; panel y `getActions` no |
| Pistas con servos distintos | Se respeta lo guardado |

mai-core no reintenta un id omitido.

## Dueños del cambio

| Repositorio | Qué toca |
|---|---|
| `pmas-web-motion-studio` | Categoría, dos pistas, generar neutro, origen con `blocks_neutro` |
| `pba-ms-robotics` | Ingest, cola, pausas, runtime, `getActions` filtrado, `executeAction` encola, play con `mode` |
| `pba-ms-gateway` | DTO `category` / `blocks_neutro` / `mode`; `GET /sequence/runtime` |
| `pmas-web-main` | Panel por categoría, Normal/Neutro, En hardware, poll; importador origen nuevo |
| `pmai-mai-core` | Sin cambio de contrato (solo se cubre con doble en pruebas) |

## Testing

Sin Arduino:

- Ingest completo → canónico con `id` y dos pistas.
- Ingest sin categoría o sin neutro → rechazo; archivo legado no entra a `getActions`.
- Generar neutro: primer `pos` por `(pca, servo)`; regenerar pide reemplazo (en UI; en unidad, función pura con flag).
- `executeAction(1)` y enseguida `(2)` con reproductor ocupado: cola de pasos del par 1 (lo que falte) más el par 2; un solo hilo.
- Tras `1 normal`, espera 1 s, `1 neutro`, espera 1 s, `2 normal`.
- Play `mode=neutro` con `busy` de turno: error, cola igual.
- Stop vacía cola y corta espera.
- `getActions`: una fila por gesto.
- mai-core (doble): tres llamadas `executeAction` en orden, sin esperar.

Con Angular: agrupación en seis secciones; Normal/Neutro off si `busy`; En hardware muestra `current` y `queue`.

## Límites

PyQt no se relanza. No hay persistencia de cola. No hay asignación manual de `id`. El chat no muestra la cola.
