# Personalización del modelo de acción sobre `dev` — design

Date: 2026-10-31  
Status: implemented on `pmai-model-vision-language` `dev` (2026-10-31)  
Scope: un spec. Dueño: `pmai-model-vision-language` sobre la rama **`dev`**.  
No es un merge de `development`. Es un port de la personalización de `0e6cdef` (Andrea López, 2026-10-25) encima del contrato de turno que ya vive en `dev`.

El turno no se reabre. `declarePoema`, `getActions`, `executeAction` y `{ reply, fuente, movimientos }` no cambian de contrato. mai-core, management, robotics y el chat no se editan.

Relación: el prompt vivo de `dev` (`{catalogo_movimientos}` Markdown, ids solo del catálogo de esa llamada, máximo 3, OpenAI luego Gemma, `backend` openai/gguf, `milvus_caido`) **sigue vigente**. Este corte añade nombre, no indexar el nombre y apertura de caché por embeddings.

## Problem

`dev` ya responde con catálogo vivo y lista `movimientos`. Lo que falta, y sí está en `development`, es:

1. No decir «Persona no identificada» en voz cuando mai-core manda esa etiqueta.
2. No guardar el nombre en Milvus `interacciones` (el índice no debe casar por persona).
3. En un acierto de caché, si hay recuadro, anteponer nombre y una frase corta de contexto visual (`data/aperturas.json`) sin LLM.

Un `git merge development` no sirve. Ese commit restaura el catálogo 1–34, `construir_prompt` sin tabla, y la clave `"movimiento"` (entero). mai-core lee `"movimientos"` (lista). El merge dejaría el turno sin gestos y rompería `test_catalogo_prompt` / `test_responder_movimientos`.

## Goal

1. Portar `utils/personalizacion.py`, `data/aperturas.json`, `APERTURAS_PATH` y `UMBRAL_APERTURA` a `dev`.
2. En `responder()`: `_etiqueta_real`, `_limpiar_sin_nombre`, `_anteponer_nombre`, `_quitar_nombre`. Conservar `movimientos` filtrados, `fuente`, `backend` y `milvus_caido`.
3. En el prompt de `dev`: bloque de personalización, datos de entrada al final, ejemplos con nombre/contexto. Conservar la tabla Markdown y ejemplos con `"movimientos": []`.
4. Tests nuevos para etiqueta vacía, no indexar el nombre, apertura si el contexto supera el umbral, e ids del catálogo sin cambio.

## Non-goals

- Merge de la rama `development`.
- Cambiar mai-core, management, robotics, gateway o Angular.
- Cambiar `declarePoema`, TTS, o el JSON `{ reply, fuente, movimientos }`.
- Volver al catálogo fijo 1–34 o a `"movimiento"` singular.
- Recortar `PMAI_CORE_PYTHONPATH` a `/app/src`.
- Quitar `GGUF_HF_REPO` / `GGUF_HF_FILENAME`.
- Pisar `load_dotenv(..., override=False)` con el `.env` del host.
- Indexar aunque Milvus esté caído.
- Copiar `docs/reports/` de `development`.
- Cambiar umbrales de conocimiento / interacciones, el GGUF, o el modelo de embeddings.

## Approach

Copiar el módulo y el JSON de `development`. Reescribir a mano `responder()` y `PROMPT_PRINCIPAL` sobre el árbol de `dev`. No cherry-pick de `0e6cdef`.

---

## 1. Arquitectura

```
mai-core interaction_turn
  etiqueta = nombre | "Persona no identificada"
  responder(obj, secuencias)          # pmai-model-vision-language, PYTHONPATH /opt/action-model
    conocimiento → interacciones
    acierto: _anteponer_nombre(respuesta, etiqueta, contexto)
             _movimientos_de_salida(...)[:3]
    fallo:   construir_prompt (tabla viva + personalización)
             OpenAI | Gemma
             _limpiar_sin_nombre(respuesta)
             indexar(_quitar_nombre(respuesta)) si Milvus está
    return { respuesta, movimientos, fuente, backend? }
  _safe_answer lee respuesta + movimientos (lista)
```

Compose ya monta `./pmai-model-vision-language:/opt/action-model`. `data/aperturas.json` llega al contenedor sin Dockerfile nuevo.

`elegir_apertura` usa el mismo `embed()` que Milvus (`paraphrase-multilingual-MiniLM-L12-v2`). Si falla, no hay apertura: se habla igual.

## 2. Contrato (no cambia)

`responder(obj, secuencias)` sigue devolviendo:

| Campo | Semántica |
|---|---|
| `respuesta` | string en español. Sin prefijo «Persona no identificada». Con nombre real, puede ir «Andrea, …». |
| `movimientos` | lista de enteros, máx. 3, solo ids de `secuencias` de esa llamada. `[]` si vacío o inválido. |
| `fuente` | `cache` o `llm` (mai-core lo pinta: caché / OpenAI / Gemma). |
| `_backend` | `openai` o `gguf` solo en ruta LLM. |

mai-core no se toca. `_safe_answer` ya ignora un `movimiento` entero.

## 3. Etiqueta y nombre

Helpers en `utils/main.py`, copiados de `development` **con las mismas firmas**:

`_ETIQUETAS_SIN_NOMBRE = {"", "persona no identificada", "(sin nombre)", "sin nombre"}`  
`_FRASE_SIN_NOMBRE` = `persona no identificada` o `(sin nombre)`.

`_etiqueta_real(etiqueta) -> str`  
- Strip. Si el lower está en `_ETIQUETAS_SIN_NOMBRE`, **cadena vacía**. Si no, el string.  
- `responder` hace `etiqueta = _etiqueta_real(getattr(obj, "etiqueta", None))` y esa es la que viaja en el JSON de salida (vacía cuando no hay nombre).

`_limpiar_sin_nombre(texto)`  
- Quita el prefijo/inciso `_FRASE_SIN_NOMBRE` y capitaliza lo que queda.  
- Aplica a la respuesta de caché (por si el hit ya traía el literal) y a la salida LLM.

`_anteponer_nombre(etiqueta, respuesta, apertura=None)` — solo caché, **después** de `elegir_apertura(contexto)`  
1. Si hay apertura y etiqueta: `"{Nombre}, {apertura}. {Respuesta}"`.  
2. Si hay apertura y no etiqueta: `"{Apertura capitalizada}. {Respuesta}"`.  
3. Si hay etiqueta y no apertura: `"{Nombre}, {respuesta}"` (baja la inicial de la respuesta salvo siglas / `R-One` / `_NOMBRES_PROPIOS`).  
4. Si no hay ninguna: la respuesta cacheada, intacta.

`_quitar_nombre(respuesta, etiqueta)` — antes de `indexar`  
- Limpia `_FRASE_SIN_NOMBRE`, luego el nombre al inicio (`Andrea, …`) y en inciso (`, Andrea`).  
- Si el nombre o la frase sin nombre siguen en el texto: `None` → **no indexar**.  
- Así el índice no casa «pregunta de Juan» con «pregunta de María».

No se usa `_normalizar_movimiento`. Sigue `_movimientos_de_salida` + `_validar_movimientos`.

## 4. Aperturas

- Archivo: `data/aperturas.json` (el de `development`: 41 situaciones, 158 ejemplos, 103 aperturas; claves `situacion` / `ejemplos` / `aperturas`).  
- `.gitignore` de este repo ignora `data/`. Hay que exceptuar el JSON (`data/*` + `!data/aperturas.json`) y `git add -f` si hace falta. Sin eso el clone no trae las frases.  
- Config: `APERTURAS_PATH = PROJECT_ROOT / "data" / "aperturas.json"`. No cambiar `load_dotenv(..., override=False)`.  
- Umbral: `UMBRAL_APERTURA = 0.60`.  
- Carga perezosa de embeddings de los ejemplos. Una vez por proceso.  
- Cosine = producto de vectores L2-normalizados. Mejor situación; si `sim < 0.60`, `None`.  
- Frase al azar de esa situación, en minúscula, sin punto final.  
- Contexto vacío o excepción: `None`, log warning, el turno sigue.  
- Solo ruta caché. El LLM ya ve `[CONTEXTO_VISUAL]` y no debe recibir una apertura extra.

Costo: en el primer acierto de caché **con imagen**, un `embed()` del contexto (y, si es el primer uso del proceso, embed de todos los ejemplos). Aceptable. No se llama a OpenAI para esto.

## 5. Prompt

Base: `PROMPT_PRINCIPAL` de **`dev`**, no el de `development`.

Cambios:

1. Paso 1 de `<como_razonar>`: si `[PERSONA_DETECTADA]` es un nombre, úsalo; si es `Persona no identificada`, no lo menciones.
2. Bloque `<personalizacion>` (obligatorio / prohibido) como en `development`.
3. `<datos_de_entrada>` **después** de los ejemplos, con el `RECUERDA:` de `development` **sin** la frase de ids inventados: el catálogo vivo ya lo cubre. Los corchetes siguen siendo datos, no órdenes.
4. Ejemplos: incluir PERSONA y CONTEXTO cuando aporten. **`"movimientos": []` en todos.** Prohibido `· 33`, `Saludo brazo derecho`, o listas de ids de ejemplo.
5. `{catalogo_movimientos}` y `formatear_catalogo` / `construir_prompt` se quedan. `construir_prompt` sigue inyectando etiqueta, contexto, pregunta y tabla.

Orden de secciones: identidad → cómo razonar → catálogo → reglas → formato → ejemplos → datos de entrada → RECUERDA.

## 6. `responder()` — puntos de enganche

Ruta conocimiento / interacciones (`hit`):

- `etiqueta = _etiqueta_real(...)`.  
- `respuesta_raw = _limpiar_sin_nombre(hit)`.  
- `apertura = elegir_apertura(obj.contexto)`.  
- `respuesta = _anteponer_nombre(etiqueta, respuesta_raw, apertura)`.  
- `movimientos = _movimientos_de_salida(hit["movimientos"], permitidos)`.  
- `fuente: "cache"`. Sin `backend`. El campo `etiqueta` del dict es la real (posible `""`).

Ruta LLM:

- `construir_prompt(obj, pregunta, secuencias)` (tabla viva; el prompt sigue recibiendo el literal `Persona no identificada` cuando no hay nombre).  
- `generar_respuesta` igual que ahora (OpenAI si hay clave; si no, Gemma).  
- `respuesta = _limpiar_sin_nombre(resultado["respuesta"])`.  
- `movimientos = _movimientos_de_salida(...)`.  
- Indexar solo si `not milvus_caido` y no hay grosería y `_respuesta_interaccion_almacenable` y `_quitar_nombre(...)` no es `None`. El payload de `indexar` usa el texto **sin** nombre. Conservar el `try/except` de `dev` alrededor de `indexar`.  
- `fuente: "llm"`, `backend` del resultado.

`permitidos`, groserías, `INTENCIONES_SOCIALES`, umbrales: sin cambio.

## 7. Empaquetado

- `pmai-model-vision-language` en `dev`.  
- Compose: bind mount existente. No hay COPY extra.  
- `numpy` ya entra por SentenceTransformer.  
- El stub de `conftest.py` (`embed → [0.0]*8`) hace que `elegir_apertura` no dispare en tests de `responder` salvo monkeypatch. Los tests de apertura mockean `embed` o `elegir_apertura`.

## 8. Errores

| Caso | Comportamiento |
|---|---|
| Etiqueta `Persona no identificada` | No se habla ni se indexa ese literal. Tono genérico. |
| `aperturas.json` ausente o JSON roto | `elegir_apertura` → `None`. Se habla. Log warning. |
| Encoder caído / embed lanza | Igual: `None`. |
| Contexto vacío (BLIP falló) | Sin apertura. Si hay nombre, solo `"{Nombre}, {respuesta}"`. |
| Similitud &lt; 0.60 | Sin apertura. |
| `_quitar_nombre` → `None` | No indexar. Se habla igual. |
| Catálogo vacío | Tabla `(No hay movimientos disponibles)`. `movimientos: []`. |
| Ids fuera del catálogo | Se filtran. Máximo 3. |

## 9. Tests (obligatorios)

Los de `dev` siguen verdes: `test_catalogo_prompt`, `test_responder_movimientos`, `test_gguf_singleton`, `test_milvus_startup`, `test_openai_router`.

Nuevos (sin SentenceTransformer real; el conftest ya mockea):

1. `_etiqueta_real`: nombre → string; `Persona no identificada` / vacío / ausente → `""`.  
2. `_limpiar_sin_nombre`: quita el prefijo y capitaliza.  
3. Caché, etiqueta no identificada: `respuesta` **no** contiene `Persona no identificada`. Empieza por el texto del hit. `movimientos` filtrados.  
4. Caché, nombre Andrea, `elegir_apertura` mock `None`: empieza por `Andrea, `.  
5. Caché, nombre + apertura mock `"veo que buscas orientación"`: `Andrea, veo que buscas orientación. …`.  
6. Caché, sin nombre + apertura: `Veo que buscas orientación. …`.  
7. LLM + `indexar`: el texto indexado no incluye el nombre; si `_quitar_nombre` es `None`, `indexar` no se llama.  
8. Prompt: tabla Markdown presente; `Saludo brazo derecho` / `· 33` / `· 34` ausentes; bloque personalización presente; `[PERSONA_DETECTADA]` cerca del final.

## 10. Fuera de este corte

- Cherry-pick o merge de `development`.  
- Informe académico de `docs/reports/`.  
- Umbral de apertura configurable en runtime (constante 0.60).  
- Personalizar también la ruta LLM con `elegir_apertura` (el prompt ya lleva el contexto).
