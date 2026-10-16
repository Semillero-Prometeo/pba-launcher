# Clave OpenAI del modelo de acción — design

Date: 2026-10-16  
Status: approved by user on 2026-10-16  
Scope: un corte. Hacer que `responder()` use OpenAI cuando hay clave usable, y Gemma cuando no. Dueños: lanzador (`docker-compose.yml`, `.env.template`, README, `AGENTS.md`) y `pmai-model-vision-language` (`utils/gpt/gptapi.py`, `utils/config.py`). mai-core no cambia el turno.

Relación: el spec `2026-10-09-rone-interaction-turn-design.md` sigue vigente. Este corte **corrige** el cableado de la clave y el detector de red que hoy impiden la rama OpenAI. No reabre Milvus, el prompt, gestos, `declarePoema` ni `chatService.chat`.

## Problem

El turno está diseñado así: Milvus (`conocimiento`, luego `interacciones` exactas); si no hay hit, OpenAI si hay clave y red; si no, Gemma 4 E2B.

Eso no ocurre con la clave que el operador ya puso en el `.env` del lanzador.

1. Esa clave vive como `MS_MANAGEMENT_OPENAI_API_KEY` y `MS_ROBOTICS_OPENAI_API_KEY`. Compose las pasa a management (`declarePoema`) y a robótica (TTS). `pmai-core` no recibe `OPENAI_API_KEY`.
2. El modelo de acción hace `load_dotenv` de `pmai-model-vision-language/.env` (`OPENAI_API_KEY`). Ese archivo no existe.
3. `generar_respuesta` exige además un TCP a `8.8.8.8:53`. En Docker/WSL ese ping suele fallar, así que ni intenta la API.
4. El `.env` local del lanzador tiene `PMAI_CORE_PYTHONPATH=/app/src`. La plantilla pide `/opt/model-context:/opt/action-model:/app/src`. Sin el volumen en el `PYTHONPATH`, `load_dotenv` no ve el `.env` montado del modelo.

`fuente` en pantalla queda en `caché` o `Gemma (local)`, nunca `OpenAI`.

## Goal

1. Compose inyecta `OPENAI_API_KEY` en `pmai-core`.
2. Si Compose la deja vacía, `pmai-model-vision-language/.env` la rellena. Si Compose ya la trajo, `load_dotenv` no la pisa.
3. Sin clave → Gemma, sin llamar a la red. Con clave → se intenta OpenAI (`gpt-4o-mini`). Si la API falla → Gemma y log de warning.
4. El detector previo, si se conserva, apunta a `api.openai.com:443`. El `try/except` de la llamada es la fuente de verdad.
5. `PMAI_CORE_PYTHONPATH` en la plantilla (y el valor que debe usar el operador) es `/opt/model-context:/opt/action-model:/app/src`.
6. README y `AGENTS.md` documentan el orden Compose → `.env` del modelo → Gemma.

## Non-goals

- `declarePoema`, TTS, unificar las tres claves del stack en una sola variable.
- Cambiar Milvus, el prompt, el catálogo de gestos, o `{ reply, fuente, movimientos }`.
- Reconectar `chatService.chat` a OpenAI.
- Subir secretos a git. El `.env` real del modelo de acción, si existe, queda local.
- Cambiar el mapeo de `fuente` en mai-core (`caché` / `OpenAI` / `Gemma (local)`).

## Approach

Opción B aprobada: clave por Compose con `.env` del modelo como respaldo, y prueba de red realista (intento a la API, no ping a Google DNS).

## Resolución de la clave

Dentro del proceso de `pmai-core`, `OPENAI_API_KEY` se resuelve en este orden:

1. Variable de entorno del contenedor. Compose la define así:

   `OPENAI_API_KEY=${PMAI_OPENAI_API_KEY:-${MS_MANAGEMENT_OPENAI_API_KEY}}`

2. Si sigue vacía, `load_dotenv` en `utils/config.py` lee `/opt/action-model/.env` (el repo `pmai-model-vision-language` montado). `override` queda en el valor por defecto (`False`): no pisa lo que Compose ya inyectó.
3. Si sigue vacía, no hay OpenAI.

En `.env.template` del lanzador se documenta `PMAI_OPENAI_API_KEY`. Vacía: se reusa `MS_MANAGEMENT_OPENAI_API_KEY`. El operador no está obligado a duplicar la clave. `MS_ROBOTICS_OPENAI_API_KEY` no entra en esta cadena.

`PMAI_CORE_PYTHONPATH` debe incluir `/opt/action-model` para que `Path(__file__).parents[1]` de `utils/config.py` sea el volumen montado y no la copia instalada en site-packages.

## Router OpenAI / Gemma

`utils/gpt/gptapi.py`:

- Sin `OPENAI_API_KEY` → Gemma (`_backend=gguf`), sin cliente HTTP.
- Con clave → siempre `llamar_openai`. Éxito → `_backend=openai`. Excepción → warning y Gemma.
- Se elimina la sonda a `8.8.8.8:53`. No hay pre-check que pueda saltarse OpenAI cuando hay clave. Opcional: una sonda a `api.openai.com:443` solo para logs; no decide el backend.

`responder()` no cambia: Milvus primero; LLM solo si no hay hit. Ids de gesto: solo los del catálogo de esa llamada, máximo 3.

`_fuente_visible` en mai-core ya traduce `backend=openai` → `OpenAI` y `gguf` → `Gemma (local)`. No se toca.

## Error handling

| Caso | Resultado |
|---|---|
| Clave en Compose | OpenAI si la API responde |
| Clave solo en `.env` del modelo | Igual, si `PYTHONPATH` incluye `/opt/action-model` |
| Clave en Compose y también en el `.env` del modelo | Gana Compose |
| Sin clave | Gemma |
| Clave presente, API 401 / timeout / DNS | Gemma; se registra el fallo; el turno no muere |
| Hit de Milvus | `caché`; no se llama al LLM |
| PYTHONPATH sin `/opt/action-model` | El `.env` montado no carga; Compose sigue siendo suficiente |

## Testing

En `pmai-model-vision-language`, el estilo que ya use `utils/gpt` (pytest o file-read):

- Con clave y cliente ok → `_backend=openai`.
- Con clave y cliente que lanza → `_backend=gguf`; no se propaga.
- Sin clave → Gemma; el cliente OpenAI no se construye.
- `load_dotenv` no pisa un `OPENAI_API_KEY` ya definido.

Compose: `docker compose config` muestra `OPENAI_API_KEY` en `pmai-core` interpolado desde las variables del lanzador.

## Docs

README: dejar de decir que basta `OPENAI_API_KEY` solo en `pmai-model-vision-language/.env`. Describir el orden Compose (`PMAI_OPENAI_API_KEY` o `MS_MANAGEMENT_OPENAI_API_KEY`) → `.env` del modelo → Gemma.

`AGENTS.md` arranque: la clave del modelo de acción llega por Compose a `pmai-core`; el `.env` del modelo es respaldo. `PMAI_CORE_PYTHONPATH` no se recorta a `/app/src`.

## Decisions locked

- Cadena C: Compose, luego `.env` del modelo, luego Gemma.
- Variable propia `PMAI_OPENAI_API_KEY` con fallback a `MS_MANAGEMENT_OPENAI_API_KEY`.
- No unificar TTS ni `declarePoema`.
- Detector `8.8.8.8` fuera; la llamada a la API decide.
- PYTHONPATH canónico restaurado en plantilla y docs.
- mai-core no cambia el turno ni `fuente`.
