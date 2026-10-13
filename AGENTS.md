# AGENTS.md

Mapa para trabajar en el lanzador de R-ONE. Las reglas cortas están en `.cursor/rules/`. La memoria larga del equipo está en `docs/project-docs/`.

## Qué es este directorio

Un lanzador. Cada carpeta de primer nivel, salvo `docs/`, es un repositorio propio del semillero Prometeo (Universidad Libre, Bogotá). No mezcles el código de un repositorio dentro de otro. Un cambio de interfaz va en `pmas-web-main`. Un cambio del turno va en `pmai-mai-core`. Un cambio del prompt va en `pmai-model-vision-language`.

## Repositorios

| Carpeta | Responsabilidad |
|---|---|
| `pmas-web-main` | Angular. Login, cámaras, chat, secuencias, páginas públicas |
| `pba-ms-gateway` | Única entrada HTTP de la interfaz |
| `pba-ms-auth` | Usuarios, roles, JWT |
| `pba-ms-management` | Gestión. El chat reenvía la pregunta al núcleo |
| `pba-ms-robotics` | Voz y acciones del Arduino |
| `pmai-mai-core` | Cámaras, detección, seguimiento, reidentificación, micrófono, turno |
| `pmai-model-context` | BLIP. Paquete importable: `model_context` |
| `pmai-model-vision-language` | Milvus, prompt, Gemma u OpenAI. Paquetes: `utils`, `prompt`, `models` |
| `pmai-model-vision` | Entrenamiento del detector. 802 imágenes, 25 clases, fase 2 |

`pba-arduino-codes` y `pmas-web-motion-studio` no forman parte del turno.

## El turno

Una pregunta a la vez. Entra por el micrófono o por `POST /chat/question`.

1. `interaction_turn.py` elige a la persona de mayor confianza. Empate: `id_global` menor. Sin persona: etiqueta `Persona no identificada` y sin imagen.
2. Si hay recuadro, recorte JPEG calidad 85 y BLIP. Si BLIP falla, el contexto queda vacío y se sigue.
3. `ROBOTICS_MS.actionService.getActions`. Sin `/dev/ttyACM*` ni `/dev/ttyUSB*`, la lista es vacía. Eso no es un fallo del turno.
4. `responder()` en `pmai-model-vision-language/utils/main.py`. Primero Milvus (`conocimiento`, luego `interacciones` con coincidencia estricta). Si no hay acierto, OpenAI si hay clave y red; si no, Gemma 4 E2B. Ids de gesto solo si están en el catálogo de esa llamada. Máximo 3.
5. `voiceService.speak` y, en orden, `actionService.executeAction` por cada id válido.
6. La pantalla recibe `{ reply, fuente, movimientos }`. `fuente` es `caché`, `OpenAI`, `Gemma (local)`, `ocupado`, `voz corta` o `disculpa`.

`chatService.declarePoema` no usa este turno. Sigue en OpenAI y sí llama a hablar.

## Arranque que no hay que romper

- `PMAI_CORE_PYTHONPATH=/opt/model-context:/opt/action-model:/app/src`
- La imagen de `pmai-core` se construye con el contexto en la raíz de este lanzador.
- El GGUF vive en `pmai-model-vision-language/models/gguf/gemma-4-E2B-it-Q4_K_M.gguf`. Si falta, se descarga de `unsloth/gemma-4-E2B-it-GGUF`.
- La clave de OpenAI del modelo de acción está en el `.env` de `pmai-model-vision-language`.
- Milvus Lite escribe `pmai-model-vision-language/utils/milvus/androide_milvus.db`.
- Descripciones de gestos, si existen: `ACTION_DESCRIPTIONS_PATH` en robótica, por defecto `/usr/src/app/data/action-descriptions.json`.

## Documentación larga

| Archivo | Úsalo para |
|---|---|
| `docs/project-docs/1. Documentación del Proyecto - Inteligencia Artificial Multimodal y Robótica Autonoma.md` | Memoria académica del sistema |
| `docs/project-docs/project-start-plan.png` | Los nueve hitos originales |
| `docs/project-docs/high-level-action-model.jpeg` | Descripción de escena y respuesta con gesto |
| `docs/project-docs/model-vision-project.md` | Fases del detector y las 802 imágenes |
| `docs/project-docs/informe-horas-sociales.md` | Informe de horas. No lo uses como especificación técnica |
| `README.md` | Comandos para levantar el lanzador |

## Reglas

Están en `.cursor/rules/`. La de visión general aplica siempre. Las demás aplican al abrir archivos de esa pieza.
