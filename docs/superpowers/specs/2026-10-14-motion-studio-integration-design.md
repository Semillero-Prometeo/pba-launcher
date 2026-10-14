# Estudio de movimiento en R-ONE — design

Date: 2026-10-14  
Status: approved by user on 2026-10-14  
Scope: acoplar `pmas-web-motion-studio` al lanzador y a `pmas-web-main` sin reescribir el turno. El estudio crea secuencias (legacy + descripción); robótica las convierte a la estructura canónica con `id` y las expone por `getActions` / `executeAction`.

## Problem

El estudio es un editor PyQt de escritorio, desordenado, que guarda JSON de 7-tuplas en disco. No forma parte de Compose ni de la interfaz. Las secuencias que produce no tienen frase semántica.

El turno ya pide `getActions`, arma `| id | nombre | arduino_id | descripcion |` y ejecuta hasta tres ids con `executeAction`. Esa descripción iba a salir de `ACTION_DESCRIPTIONS_PATH` y de una pantalla en `pmas-web-main` que no existe. `pmas-web-main` sí tiene un editor Angular de secuencias y un importador legacy; eso duplica al estudio, que debía ser el único software de creación.

Hay que integrar el estudio sin mezclar su código en Angular, sin romper el contrato del turno y con la descripción escrita en el momento de crear.

## Goal

1. El estudio es un servicio web propio en Compose. `pmas-web-main` lo muestra en `/sequences` por iframe. No se copia su código a Angular.
2. Quien crea la secuencia escribe `name` y `description`. El estudio guarda formato de origen: 7-tuplas más esos dos campos. No asigna `id`.
3. Al guardar acoplado o al importar, robótica convierte a la estructura canónica, asigna `id` y persiste en `SEQUENCES_DATA_DIR`. El panel de control, al recargar, ya la ve. No hay un segundo almacén.
4. `getActions` arma el catálogo del turno con esas secuencias convertidas (`id`, `name`, `arduino_id`, `description`). La tabla Markdown no cambia. `executeAction` conserva la firma: si el `id` es una secuencia, reproduce sus bloques; si no, escribe el número al serial.
5. El importador de JSON de la interfaz sigue existiendo para archivos hechos con el estudio suelto.
6. Suelto, el estudio no llama al gateway y guarda JSON local con descripción incluida.

## Non-goals

- Reescribir el estudio dentro de Angular.
- Gemma viendo la línea de tiempo o la escena.
- Cambiar `declarePoema`, el chat, o el rediseño visual del panel de control.
- Borrar `getActions`, `executeAction` o `ACTION_DESCRIPTIONS_PATH`.
- Cola de guardados, sincronización en vivo hacia el panel, o editor de descripciones fuera del estudio.
- Reescribir solos los JSON antiguos en disco.
- Que el estudio acoplado abra `/dev/ttyACM*` o `/dev/ttyUSB*`.

## Approach

Servicio web en `pmas-web-motion-studio`, iframe en `pmas-web-main`, almacén canónico en `pba-ms-robotics`. El estudio no entra a NATS. Acoplado, habla HTTP con el gateway (`/sequence/*`) con el JWT de la sesión Angular. El adaptador (legacy + descripción → archivo con `id`) vive en robótica, no en el estudio ni en mai-core.

mai-core y el modelo de acción no cambian de contrato: siguen llamando `getActions` y `executeAction`. Cambia de dónde robótica saca las filas y qué hace `executeAction` cuando el `id` es una secuencia.

## Arquitectura

El dueño de las secuencias es `pba-ms-robotics`: `SEQUENCES_DATA_DIR`, NATS `sequenceService.*`, HTTP del gateway. El panel de control ya lista esa carpeta.

Compose levanta `pmas-web-motion-studio` como servicio HTTP. Variable `MOTION_STUDIO_URL` para el iframe. El recuadro genérico `/iframe` de Angular no se usa para esto.

Dos modos:

| Modo | Cómo se activa | Dónde escribe | Serial |
|---|---|---|---|
| Acoplado | Compose / `GATEWAY_URL` + JWT | `POST /sequence/file` en robótica | No: previsualizar y guardar van al gateway (`/sequence/play`, `/sequence/file`) |
| Suelto | Sin gateway o sin token | JSON local (formato de origen) | El estudio puede hablar con el Arduino como hasta ahora |

Angular `/sequences` deja de ser el editor de línea de tiempo. Pasa a ser el marco del estudio más el botón de importar JSON. El panel de control sigue siendo donde se reproduce y se encadena. El chat no cambia: `movimientos` sigue `{ id, name }`.

## Formato de origen (estudio)

El estudio nunca escribe `id` ni `version`. Cada bloque es una 7-tupla `[pca, servo, inicio, dur, pos, vel, nombre]`.

```json
{
  "name": "saludo",
  "description": "Saludo con el brazo derecho",
  "arduino_id": 0,
  "blocks": [[0, 0, 0.0, 2, 0, 1, "P0_S0"]]
}
```

- `name`: 1–80 caracteres, obligatorio al guardar.
- `description`: 0–280 caracteres, una línea, sin Markdown. Vacía (`""`) no bloquea un borrador.
- `arduino_id`: opcional a nivel de archivo. Si falta, 0. El importador Angular sigue pidiendo Arduino por fila cuando importa archivos sueltos.
- `nombre` dentro de cada tupla es la etiqueta del servo en la línea de tiempo, no la frase del prompt.

JSON antiguo que es solo una lista de 7-tuplas sigue siendo válido al importar: `description` queda `""`.

## Formato canónico (robótica)

Al ingest (guardado acoplado o importación), robótica convierte y **añade el `id`**.

```json
{
  "version": 1,
  "id": 4,
  "name": "saludo",
  "description": "Saludo con el brazo derecho",
  "blocks": [
    {
      "arduino_id": 0,
      "pca": 0,
      "servo": 0,
      "inicio": 0,
      "dur": 2,
      "pos": 0,
      "vel": 1,
      "nombre": "P0_S0"
    }
  ]
}
```

Reglas de `id`:

- Lo asigna robótica. El estudio no lo elige.
- Nombre nuevo: `max(ids existentes) + 1`. Carpeta vacía: `1`. Un `id` borrado no se reutiliza.
- Mismo nombre y overwrite: se conservan `id` y `name`; se actualizan `description` y `blocks`.
- Archivos canónicos ya guardados sin `id` o sin `description`: al leerlos, `description` es `""`. No se reescriben solos. Sin `id` siguen listándose en el panel de control; **no** entran a `getActions` hasta un guardado o overwrite que les asigne `id`.

`listSequences` deja de devolver solo `{ name, file_name }`. Cada fila incluye `id` y `description`.

`MotionSequenceFile` gana `id: int` y `description: str` (default `""`). Los bloques siguen siendo objetos; las 7-tuplas se aceptan solo en el ingest, vía el validador legacy que ya existe.

## Ingest

El adaptador vive en robótica. El gateway puede reenviar el formato de origen; robótica discrimina origen vs canónico en `saveSequence`.

1. Validar `name` y al menos un bloque.
2. Convertir cada 7-tupla a `MotionBlock` con el `arduino_id` del archivo (o el que mande el importador Angular).
3. Asignar o conservar `id`.
4. Escribir el JSON canónico en `SEQUENCES_DATA_DIR`.
5. No tocar `ACTION_DESCRIPTIONS_PATH`. La frase del prompt sale de `description` en este archivo.

Nombre duplicado y `overwrite=false`: error claro; el estudio pregunta y, si el usuario acepta, reenvía con `overwrite=true`.

Si el gateway o robótica no responden, el estudio muestra el error y no finge el guardado. No escribe un JSON local de consuelo en modo acoplado.

## Turno y catálogo

mai-core no cambia de pasos. Sigue:

1. `ROBOTICS_MS.actionService.getActions`
2. Tabla `| id | nombre | arduino_id | descripcion |`
3. `responder()` con como máximo 3 ids de esa tabla
4. `executeAction(id, arduino_id)` por cada id válido

Cambia el interior de robótica:

- `getActions` arma la lista con las secuencias canónicas. Cada una es `Command(id, name, arduino_id, description)`. `arduino_id` del comando es el del primer bloque (la reproducción usa el `arduino_id` de cada bloque).
- Sin secuencias, o si `getActions` falla: lista vacía. El turno habla y no mueve. Eso no es un fallo del turno.
- Las acciones que el firmware Arduino reporte y que no tengan archivo de secuencia **no** entran a esa tabla. El modelo solo ve secuencias ingestadas.
- Descripción vacía: la celda queda vacía; el modelo usa el nombre (regla ya existente).
- `executeAction`: si existe una secuencia con ese `id`, reproduce sus bloques (el mismo motor que `startPlayback`). Si no, escribe el número al serial como hoy.
- Un id que el modelo invente y no esté en el catálogo de esa llamada se omite. No se inventa relleno.

`ACTION_DESCRIPTIONS_PATH` sigue en el código para quien lo use fuera de estas frases. El turno, con este corte, no depende de ese JSON.

El estudio no entra en el turno. Solo deja archivos en robótica.

## Superficie

### `pmas-web-main`

- `/sequences` (sidebar «Creación de Secuencias»): iframe a `MOTION_STUDIO_URL`. Al cargar, Angular envía el JWT por `postMessage` al origen del estudio, una vez. El estudio lo guarda en memoria y lo manda en `Authorization`.
- Sin token (o token rechazado y sin renovación): el iframe avisa que no está acoplado y no llama a `/sequence/*`.
- Botón **Importar JSON** junto al iframe: el importador actual, aceptando formato de origen (`name`, `description`, 7-tuplas). Archivo inválido: se rechaza esa fila, las demás siguen. Sin `arduino_id` elegido: esa fila no se envía.
- Iframe en error (servicio caído): mensaje en `/sequences`. Panel de control, chat y turno siguen.
- Panel de control: sin rediseño. Recargar la lista muestra la secuencia nueva, con descripción. Reproducir y encadenar no cambian.
- Chat: sin cambios de contrato.

### Estudio

- Campos visibles al guardar: nombre, descripción, bloques.
- Acoplado: `POST /sequence/file` y, si previsualiza, `POST /sequence/play`. No abre puertos seriales.
- Suelto: escribe formato de origen en disco.

## Fallos

| Situación | Resultado |
|---|---|
| Gateway o robótica caídos al guardar acoplado | Error visible; no hay archivo canónico |
| Token ausente o vencido | El iframe pide el JWT otra vez; si no llega, modo suelto y aviso |
| Nombre duplicado, sin overwrite | No se toca el archivo; el estudio pregunta |
| JSON de importación que no es origen ni lista de 7-tuplas | Se rechaza esa fila |
| Descripción ausente al importar | `""` |
| Carpeta de secuencias vacía | `getActions` vacío; hay frase y voz; no hay gesto |
| `getActions` falla | Igual que carpeta vacía |
| Id fuera del catálogo | Ese id se omite |
| `executeAction` de una secuencia sin Arduino para esos bloques | Se registra, se sigue con el siguiente id, `reply` regresa |
| Estudio no levanta | `/sequences` lo dice; el resto del sistema sigue |
| Conflicto de puerto serial en modo acoplado | Fuera de este diseño: el estudio no abre el serial |

No hay cola de guardados. El panel no se actualiza solo: hay que recargar la lista.

## Dueños del cambio

| Repositorio | Qué toca |
|---|---|
| `pmas-web-motion-studio` | Servicio web, formato de origen, modo acoplado/suelto, JWT en memoria |
| `pba-ms-robotics` | Ingest, `id`, `description` en el archivo, `listSequences`, `getActions` desde secuencias, `executeAction` que reproduce si hay secuencia |
| `pba-ms-gateway` | DTO de secuencia (`id`, `description`, origen vs canónico) |
| `pmas-web-main` | `/sequences` como iframe + importador de origen; `postMessage` del JWT |
| lanzador | Servicio Compose y `MOTION_STUDIO_URL` |

No se edita el contrato de `pmai-mai-core` ni la tabla Markdown de `pmai-model-vision-language`.

## Testing

Sin Arduino y sin el iframe levantado:

- Ingest de origen (`name`, `description`, 7-tuplas) produce canónico con `id` entero y bloques con `arduino_id`.
- Segunda escritura del mismo nombre con overwrite conserva el `id` y cambia la descripción.
- Lista de 7-tuplas sin envoltorio importa con `description` `""`.
- JSON que no es lista ni origen se rechaza.
- `listSequences` incluye `id` y `description`.
- `getActions` devuelve un `Command` por secuencia canónica, no las acciones del firmware.
- Carpeta vacía: `getActions` es lista vacía.
- Canónico sin `id` en disco: aparece en `listSequences` y no en `getActions`.
- `executeAction` con `id` de secuencia llama a la reproducción de bloques, no al serial.
- `executeAction` con `id` que no es secuencia escribe al serial (doble del puerto).
- mai-core, con doble de `getActions`, sigue filtrando ids ajenos y no cambia de subject.

Con Angular:

- `/sequences` carga el iframe y, autenticado, envía el JWT al origen configurado.
- Importar un origen válido termina en `POST /sequence/file` con el Arduino elegido.

## Relación con el spec del turno (2026-10-09)

Ese spec sigue vigente para el orden del turno, BLIP, Milvus, Gemma y `speak`. Este corte **no** cambia los subjects ni la tabla Markdown.

Sí cambia la fuente de las filas de `getActions`: dejan de ser solo el firmware Arduino más `ACTION_DESCRIPTIONS_PATH`, y pasan a ser las secuencias ingestadas desde el estudio. La pantalla de descripciones prevista como no-objetivo en 2026-10-09 queda cubierta aquí: la frase se escribe en el estudio.

## Límites de este corte

PyQt de escritorio no se borra por este spec; Compose no lo lanza. No hay sincronización en vivo del panel. No hay asignación manual de `id` en el estudio.
