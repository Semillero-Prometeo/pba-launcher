# Turno de interacción de R-ONE — design

Date: 2026-10-09  
Status: pending user review of this file  
Scope: one interaction turn inside `pmai-mai-core`, using `pmai-model-context` (BLIP) and `pmai-model-vision-language` (Milvus + acción) as libraries.

## Problem

La percepción de mai-core ya produce un `GlobalObjectForContext` por identidad ReID y ahí se detiene. El captioning (BLIP) y el modelo de acción (Milvus, prompt, Gemma u OpenAI) viven en repos aparte y no reciben esa escena. La voz del micrófono y el chat de la interfaz terminan en `MANAGEMENT_MS.chatService.chat`, que responde con OpenAI y solo llama a `speak`. El gesto que devuelve el modelo de acción no llega a `actionService.executeAction`.

Hay tres copias del objeto de contexto. En mai-core, `question` no existe, `image_base64` no se llena y `contexto` viaja vacío. El prompt de acción trae un catálogo fijo de ids 1–34 que no es el que el Arduino reporta.

## Goal

Un turno en mai-core atiende la voz y la pregunta de la interfaz.

1. Elige a la persona visible, recorta su imagen y BLIP escribe `contexto`.
2. Pide los movimientos reales a robótica, con descripción (vacía si aún no hay texto), y los inyecta al prompt como tabla Markdown.
3. `responder()` devuelve la frase y hasta tres ids.
4. La frase sale por `ROBOTICS_MS.voiceService.speak` y cada id por `ROBOTICS_MS.actionService.executeAction`.
5. La interfaz sigue recibiendo `{ reply }` desde `POST /chat/question`.
6. Milvus Lite, BLIP, el embedding y Gemma quedan listos al arrancar mai-core.

## Non-goals

- Redactar descripciones desde `pmas-web-main`, y el rediseño del apartado de movimientos. El JSON de descripciones se lee si existe; si no, la columna llega vacía.
- Usar Gemma para ver imágenes. El captioning sigue siendo BLIP.
- Cambiar la página de chat, el gateway o los subjects de `speak` y `executeAction`.
- `chatService.declarePoema`. Sigue en OpenAI y sigue llamando a `speak`.
- Sustituir el router OpenAI / Gemma del modelo de acción. Con clave y red se usa OpenAI; si no, Gemma.

## Approach

Orquestador dentro del proceso de mai-core. Contexto y visión-lenguaje se importan como librerías. Voz y gestos salen por los NATS que ya existen. Management deja de ser el cerebro del chat: reenvía el texto al turno.

## Turno

El dueño es un turno de interacción en mai-core. Lo invocan dos entradas y ninguna otra:

- Voz: el despacho del micrófono programa el turno y regresa de inmediato. El hilo que captura audio no espera a BLIP ni al modelo.
- Interfaz: `POST /chat/question` sigue igual. `chatService.chat` llama por NATS a `MAI_CORE_MS.interactionService.ask` y devuelve `{ reply }`. No llama a OpenAI ni a `speak` en ese método.

Entra `{ "message": string }`. Sale `{ "reply": string }`. El subject es `MAI_CORE_MS.interactionService.ask`. Management usa un cliente NATS dedicado a esta llamada, con timeout de 120 segundos. El cliente existente, de 20 segundos, no cambia.

El controlador del subject es asíncrono. BLIP y `responder()` corren en hilos de trabajo. Las demás RPC de mai-core (cámaras, visión, salud) siguen atendiendo durante el turno.

Solo hay un turno a la vez. Si llega otra pregunta con el turno ocupado, no se encola. La voz pronuncia `Sigo respondiendo, un momento.` El chat devuelve esa misma frase en `reply` y no la pronuncia.

Pasos, en orden:

1. Texto de la pregunta. Si la voz tiene menos de `min_useful_transcript_chars` (14), se pronuncia `fallback_speak_message` y el turno termina. Esa regla no se aplica al chat de la interfaz.
2. Persona: el objeto global de mayor `confianza`. Empate: el `id_global` menor en orden lexicográfico. Se copian etiqueta, `camera_id` y bbox. Sin objetos, la etiqueta es `Persona no identificada` y no hay imagen.
3. Con bbox y frame de esa cámara, se recorta, se codifica JPEG (calidad 85) en base64 crudo y se guarda en `image_base64`. BLIP genera `contexto` en un hilo. Si el recorte o BLIP fallan, `contexto` queda vacío y el turno sigue.
4. `ROBOTICS_MS.actionService.getActions`. Si no responde, el catálogo queda vacío, se genera la frase igual y no se ejecuta ningún gesto.
5. `responder()` en un hilo, con el objeto y la tabla Markdown del catálogo. Devuelve la frase y hasta tres ids.
6. En paralelo: `voiceService.speak` con la frase, y en orden `actionService.executeAction` por cada id válido, con el `arduino_id` del catálogo. Un id ausente del catálogo se omite. Sin ids válidos, solo habla. Se espera a que terminen la voz y la secuencia de gestos.
7. `reply` es la frase. La interfaz la muestra. La voz ya salió por el parlante.

Si el modelo no produce frase, `reply` y la voz usan `Lo siento, no puedo responder en este momento.` y no hay gestos. Si `speak` falla, o falla un `executeAction`, se registra el error, se sigue con los ids restantes y `reply` igual regresa.

## Contratos

### Objeto de escena

El canónico es `GlobalObjectForContext` en mai-core. Se agrega `question: str | None`. El turno escribe `question`, `image_base64` (JPEG base64, sin obligar el prefijo `data:`) y `contexto`. Las clases homónimas en `pmai-model-context` y `pmai-model-vision-language` aceptan esos mismos campos. La etiqueta que ve el prompt es la del detector, tal cual llega.

### Catálogo de movimientos

`Command` en `pba-ms-robotics` gana `description: str`, por defecto `""`.

`getActions` sigue leyendo `id` y `name` del Arduino. Después une la descripción desde un JSON local. Ruta por defecto: `/usr/src/app/data/action-descriptions.json`, sustituible con `ACTION_DESCRIPTIONS_PATH`. Forma:

```json
[
  { "arduino_id": 1, "id": 4, "description": "Saludo con el brazo derecho" }
]
```

La clave es (`arduino_id`, `id`). Archivo ausente, JSON inválido o fila ausente: `description` es `""`. mai-core no abre ese archivo.

El validador de ids del modelo de acción deja de usar el rango fijo 1–34. Un id es válido si está en el catálogo de esa llamada.

### Prompt

`formatear_catalogo` emite una tabla Markdown y nada más:

```markdown
| id | nombre | arduino_id | descripcion |
|----|--------|------------|-------------|
| 4  | Saludo | 1          |             |
```

Sin filas, el texto es `(No hay movimientos disponibles)`.

Esa tabla reemplaza el bloque fijo que asigna significados a los ids 1–34 y reemplaza la lista `- ID n: nombre`. Los ejemplos del prompt conservan la forma JSON `respuesta` + `movimientos`, y su texto dice que los enteros se copian de la tabla de esa petición. No enseñan ids fijos.

El modelo sigue respondiendo solo ese JSON. `movimientos` tiene como máximo tres enteros.

### Resultado de `responder()`

```json
{
  "respuesta": "string",
  "movimientos": [4, 6],
  "fuente": "cache",
  "etiqueta": "string",
  "backend": "gguf"
}
```

`backend` solo va en la ruta LLM (`openai` o `gguf`). `movimientos` es la lista ya filtrada por el catálogo, en el orden del modelo, recortada a tres. El primer elemento es el que muestra la demo de Gradio. Las reglas de indexación no cambian: una interacción se guarda en `interacciones` solo si la pregunta no tenía grosería y la respuesta es almacenable. Un acierto de caché sigue anteponiendo la etiqueta a la frase, como hoy.

## Arranque

El proceso de mai-core importa los dos módulos. El contenedor `pmai-core` monta `./pmai-model-context` y `./pmai-model-vision-language` y los agrega al `PYTHONPATH`. La imagen instala las dependencias de ambos (BLIP, sentence-transformers, Milvus Lite, llama.cpp). El código no se copia dentro de mai-core.

Después de conectar NATS, y antes de aceptar preguntas, mai-core prepara:

1. Milvus Lite en archivo. Volumen escribible `./data/milvus` montado en `/data/milvus`, por encima del montaje de solo lectura de `./data`. `MILVUS_DB_PATH=/data/milvus/androide_milvus.db`. `asegurar_colecciones()` crea y carga `conocimiento` e `interacciones` en el arranque.
2. BLIP, en la caché que ya tiene el módulo de contexto.
3. El modelo de embeddings, que hoy se construye al importar el encoder. El arranque fuerza esa importación.
4. Una sola instancia de Gemma para toda la vida del proceso. Cada generación vacía la caché de tokens antes de correr. Si el texto sale vacío, se reconstruye la instancia y se reintenta solo esa llamada.

Si Milvus, BLIP, el embedding o Gemma fallan al arrancar, cámaras, ReID y NATS siguen activos. Con Milvus caído, la búsqueda cuenta como fallo, se genera con el modelo y esa interacción no se indexa. Sin modelo usable (OpenAI tampoco), el turno usa la frase de disculpa.

El JSON de descripciones lo lee robótica en cada `getActions`.

## Fallos

| Situación | Resultado |
|---|---|
| Voz más corta que 14 caracteres | Se pronuncia `No te escuche con claridad, puedes repetirlo por favor.` y no hay modelo ni gesto |
| Turno ocupado, entrada de voz | Se pronuncia `Sigo respondiendo, un momento.` |
| Turno ocupado, entrada de chat | `reply` es esa frase y no se llama a `speak` |
| Sin persona o sin frame | No se llama a BLIP; `contexto` vacío |
| BLIP falla | `contexto` vacío; el turno sigue |
| `getActions` falla | Catálogo vacío; hay frase y voz; no hay `executeAction` |
| Id fuera del catálogo | Ese id se omite |
| Un `executeAction` falla | Se sigue con el siguiente id; `reply` se devuelve |
| `speak` falla | `reply` se devuelve |
| Modelo sin frase | Disculpa fija, sin gestos |
| Milvus caído en la búsqueda | Se genera con el modelo; no se indexa |

## Testing

Sin Arduino, sin pesos de Gemma y sin la pantalla de descripciones:

- La tabla Markdown incluye `id`, nombre, `arduino_id` y descripción vacía si el JSON no existe, y el texto de la fila cuando existe.
- El prompt armado no contiene la guía fija de ids 1–34.
- `responder()`, con el modelo sustituido, devuelve hasta tres ids y descarta los que no están en el catálogo.
- El turno, con dobles: sin persona no llama a BLIP; un fallo de BLIP no corta la frase; el segundo llamado concurrente recibe la frase de ocupado; un id ajeno al catálogo no se ejecuta; sin acciones, solo se pide `speak`.
- `chatService.chat` envía `MAI_CORE_MS.interactionService.ask` y no llama a `speak` ni a OpenAI. `declarePoema` no entra en estas pruebas.
- Al arrancar contra un directorio temporal, Milvus deja cargadas `conocimiento` e `interacciones`.

## Límites de este corte

La pantalla que escribe descripciones, el rediseño de movimientos, el captioning con Gemma y cualquier cambio visual del chat quedan para otro spec.
