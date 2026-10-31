# Personalización del modelo de acción sobre `dev` — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port cache-name / no-name-index / visual openings from `pmai-model-vision-language` `development` (`0e6cdef`) onto current `dev`, without restoring the hardcoded 1–34 catalog or the singular `"movimiento"` key.

**Architecture:** Keep `dev` `responder()` contract (`movimientos` list, live Markdown catalog, OpenAI then Gemma, `milvus_caido`, `backend`). Copy `utils/personalizacion.py` + `data/aperturas.json`. Wire `_etiqueta_real` / `_limpiar_sin_nombre` / `_anteponer_nombre` / `_quitar_nombre` in `utils/main.py`. Extend `PROMPT_PRINCIPAL` with the personalization block and move `<datos_de_entrada>` after examples. Do **not** merge or cherry-pick `development`.

**Tech Stack:** Python 3.12+ (`pmai-model-vision-language`), pytest, numpy (already transitive via sentence-transformers). Compose bind-mount `./pmai-model-vision-language:/opt/action-model`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-31-action-model-personalization-port-design.md`.
- Owner repo: `pmai-model-vision-language` branch **`dev`**. Spec/plan live in the launcher `docs/superpowers/`.
- Do **not** `git merge development` and do **not** cherry-pick `0e6cdef`.
- Do not edit mai-core, management, robotics, gateway, or Angular.
- Do not change `declarePoema`, TTS, `{ reply, fuente, movimientos }`, `_movimientos_de_salida`, `formatear_catalogo`, `GGUF_HF_*`, or `load_dotenv(..., override=False)`.
- Do not recortar `PMAI_CORE_PYTHONPATH`.
- Prompt examples keep `"movimientos": []`. Forbidden in the prompt: `Saludo brazo derecho`, `· 33`, `· 34`, and any example list of live ids.
- `.gitignore` has `data/`. Track `data/aperturas.json` with a negation rule + `git add -f` if needed.
- Existing tests stay green: `tests/test_catalogo_prompt.py`, `test_responder_movimientos.py`, `test_gguf_singleton.py`, `test_milvus_startup.py`, `test_openai_router.py`.
- Run tests from `pmai-model-vision-language`: `PYTHONPATH=. python -m pytest tests/ -v`. `conftest.py` already stubs `sentence_transformers`, `openai`, `pymilvus`, `spanlp`, and `utils.encoder.encoder.embed → [0.0] * 8`.

## File structure

| File | Responsibility |
|---|---|
| `pmai-model-vision-language/.gitignore` | Un-ignore `data/aperturas.json` |
| `pmai-model-vision-language/data/aperturas.json` | 41 situaciones from `development` |
| `pmai-model-vision-language/utils/config.py` | `APERTURAS_PATH`, `UMBRAL_APERTURA = 0.60` |
| `pmai-model-vision-language/utils/personalizacion.py` | `elegir_apertura` (copy from `development`) |
| `pmai-model-vision-language/utils/main.py` | Name helpers + wire cache/LLM/index |
| `pmai-model-vision-language/prompt/principal.py` | Personalization block; datos al final; live table stays |
| `pmai-model-vision-language/tests/test_personalizacion.py` | Helpers, apertura, cache, index, prompt |

---

### Task 1: Aperturas file, config, and `elegir_apertura`

**Files:**
- Modify: `pmai-model-vision-language/.gitignore`
- Create: `pmai-model-vision-language/data/aperturas.json`
- Modify: `pmai-model-vision-language/utils/config.py`
- Create: `pmai-model-vision-language/utils/personalizacion.py`
- Create: `pmai-model-vision-language/tests/test_personalizacion.py`

**Interfaces:**
- Consumes: `embed(texto) -> list[float]` (L2-normalized). `APERTURAS_PATH`, `UMBRAL_APERTURA`.
- Produces: `elegir_apertura(contexto: str | None) -> str | None`. Lazy `_SITUACIONES`. Exceptions → `None` + warning.

- [ ] **Step 1: Write the failing apertura tests**

Create `pmai-model-vision-language/tests/test_personalizacion.py`:

```python
import numpy as np

import utils.personalizacion as pers


def _reset_situaciones(monkeypatch, vectores, aperturas=("veo que buscas orientacion",)):
    matriz = np.array(vectores, dtype=np.float32)
    monkeypatch.setattr(
        pers,
        "_SITUACIONES",
        [("confusion_orientacion", list(aperturas), matriz)],
    )


def test_elegir_apertura_empty_context_is_none():
    assert pers.elegir_apertura("") is None
    assert pers.elegir_apertura(None) is None


def test_elegir_apertura_above_threshold(monkeypatch):
    unit = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    _reset_situaciones(monkeypatch, [unit])
    monkeypatch.setattr(pers, "UMBRAL_APERTURA", 0.60)

    def fake_embed(texto):
        return unit

    monkeypatch.setattr("utils.encoder.encoder.embed", fake_embed)
    assert pers.elegir_apertura("person looking at a map") == "veo que buscas orientacion"


def test_elegir_apertura_below_threshold(monkeypatch):
    unit = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    ortho = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    _reset_situaciones(monkeypatch, [unit])
    monkeypatch.setattr(pers, "UMBRAL_APERTURA", 0.60)
    monkeypatch.setattr("utils.encoder.encoder.embed", lambda texto: ortho)
    assert pers.elegir_apertura("unrelated blur") is None


def test_elegir_apertura_embed_failure_is_none(monkeypatch):
    _reset_situaciones(monkeypatch, [[1.0] * 8])

    def boom(texto):
        raise RuntimeError("encoder down")

    monkeypatch.setattr("utils.encoder.encoder.embed", boom)
    assert pers.elegir_apertura("person smiling") is None
```

The first run fails: `ModuleNotFoundError: utils.personalizacion`.

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd pmai-model-vision-language
PYTHONPATH=. python -m pytest tests/test_personalizacion.py -v
```

Expected: FAIL — cannot import `utils.personalizacion`.

- [ ] **Step 3: Copy aperturas, config, and the module**

In `.gitignore`, replace the bare `data/` line with:

```
data/*
!data/aperturas.json
```

Copy the JSON from the other branch (do not merge):

```bash
cd pmai-model-vision-language
git checkout development -- data/aperturas.json
git add -f data/aperturas.json
```

If `git checkout development --` is blocked, `git show development:data/aperturas.json > data/aperturas.json` and `git add -f`.

In `utils/config.py`, after `MOVIMIENTOS_PATH`:

```python
APERTURAS_PATH = PROJECT_ROOT / "data" / "aperturas.json"
```

After `UMBRAL_INTERACCIONES`:

```python
UMBRAL_APERTURA = 0.60
```

Leave `load_dotenv(PROJECT_ROOT / ".env", override=False)` and `GGUF_HF_REPO` / `GGUF_HF_FILENAME` untouched.

Create `utils/personalizacion.py` as a verbatim copy of `development` (`git show development:utils/personalizacion.py`). Do not edit its public contract.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd pmai-model-vision-language
PYTHONPATH=. python -m pytest tests/test_personalizacion.py -v
```

Expected: PASS (4 tests). If `numpy` is missing in the local interpreter, install project deps first (`uv sync` or the Compose image). Do not add a new direct dependency.

- [ ] **Step 5: Commit in the owner repo**

```bash
cd pmai-model-vision-language
git add -f data/aperturas.json
git add .gitignore utils/config.py utils/personalizacion.py tests/test_personalizacion.py
git commit -m "$(cat <<'EOF'
Add cache openings catalog without changing the turn contract.

Track aperturas.json despite data/ ignore so Compose bind-mounts the phrases the cache uses.
EOF
)"
```

---

### Task 2: Name helpers (unit tests, no `responder` yet)

**Files:**
- Modify: `pmai-model-vision-language/utils/main.py`
- Modify: `pmai-model-vision-language/tests/test_personalizacion.py`

**Interfaces:**
- Produces: `_ETIQUETAS_SIN_NOMBRE`, `_FRASE_SIN_NOMBRE`, `_etiqueta_real`, `_limpiar_sin_nombre`, `_anteponer_nombre(etiqueta, respuesta, apertura=None)`, `_terminos_nombre`, `_quitar_nombre`. Copy bodies from `development` (`utils/main.py` around lines 97–185). Do not wire `responder` in this task.

- [ ] **Step 1: Write the failing helper tests**

Append to `tests/test_personalizacion.py`:

```python
import utils.main as main_module


def test_etiqueta_real_keeps_a_name():
    assert main_module._etiqueta_real("Andrea") == "Andrea"
    assert main_module._etiqueta_real("  Pedro  ") == "Pedro"


def test_etiqueta_real_drops_placeholder():
    assert main_module._etiqueta_real("Persona no identificada") == ""
    assert main_module._etiqueta_real("") == ""
    assert main_module._etiqueta_real(None) == ""
    assert main_module._etiqueta_real("(sin nombre)") == ""


def test_limpiar_sin_nombre_strips_prefix():
    assert (
        main_module._limpiar_sin_nombre("Persona no identificada, el semillero Prometeo.")
        == "El semillero Prometeo."
    )


def test_anteponer_nombre_with_and_without_apertura():
    assert (
        main_module._anteponer_nombre("Andrea", "El semillero Prometeo.")
        == "Andrea, el semillero Prometeo."
    )
    assert (
        main_module._anteponer_nombre(
            "Andrea",
            "El semillero Prometeo.",
            "veo que buscas orientacion",
        )
        == "Andrea, veo que buscas orientacion. El semillero Prometeo."
    )
    assert (
        main_module._anteponer_nombre(
            "",
            "El semillero Prometeo.",
            "veo que buscas orientacion",
        )
        == "Veo que buscas orientacion. El semillero Prometeo."
    )
    assert main_module._anteponer_nombre("", "El semillero Prometeo.") == "El semillero Prometeo."


def test_anteponer_nombre_keeps_sigla_and_r_one():
    assert main_module._anteponer_nombre("Andrea", "R-One está listo.") == "Andrea, R-One está listo."
    assert main_module._anteponer_nombre("Andrea", "UNAL tiene sede aquí.") == "Andrea, UNAL tiene sede aquí."


def test_quitar_nombre_strips_prefix_and_skips_embedded():
    assert (
        main_module._quitar_nombre("Andrea, el semillero Prometeo.", "Andrea")
        == "El semillero Prometeo."
    )
    assert main_module._quitar_nombre("Hola Andrea, ¿cómo estás?", "Andrea") is None
    assert (
        main_module._quitar_nombre("El semillero Prometeo.", "Persona no identificada")
        == "El semillero Prometeo."
    )
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd pmai-model-vision-language
PYTHONPATH=. python -m pytest tests/test_personalizacion.py -v
```

Expected: FAIL — `AttributeError: _etiqueta_real`.

- [ ] **Step 3: Copy the helpers into `utils/main.py`**

After the `_RESPUESTAS_GENERICAS` set, paste from `development` (do not take `_normalizar_movimiento`):

```python
from utils.personalizacion import elegir_apertura
```

Place that import with the other `utils` imports at the top.

Then the constants and five functions exactly as in `development`: `_ETIQUETAS_SIN_NOMBRE`, `_FRASE_SIN_NOMBRE`, `_etiqueta_real`, `_limpiar_sin_nombre`, `_NOMBRES_PROPIOS`, `_anteponer_nombre`, `_terminos_nombre`, `_quitar_nombre`.

Do not change `responder()` yet.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd pmai-model-vision-language
PYTHONPATH=. python -m pytest tests/test_personalizacion.py tests/test_responder_movimientos.py -v
```

Expected: PASS. Cache test still expects `Andrea, ` because current `responder` prefixes the raw etiqueta.

- [ ] **Step 5: Commit**

```bash
cd pmai-model-vision-language
git add utils/main.py tests/test_personalizacion.py
git commit -m "$(cat <<'EOF'
Add name helpers for cache replies without wiring the turn yet.

Keep placeholder labels out of speech and out of the interacciones index.
EOF
)"
```

---

### Task 3: Wire `responder()` cache, LLM, and index

**Files:**
- Modify: `pmai-model-vision-language/utils/main.py`
- Modify: `pmai-model-vision-language/tests/test_personalizacion.py`

**Interfaces:**
- Consumes: existing `search` / `generar_respuesta` / `indexar` / `_movimientos_de_salida`.
- Changes `responder` only. Keep keys `movimientos` (list), `fuente`, `backend` on LLM, `etiqueta` (now possibly `""`). Keep `milvus_caido` so a down Milvus does not index.

- [ ] **Step 1: Write the failing `responder` tests**

Append to `tests/test_personalizacion.py`:

```python
from models.schemas import GlobalObjectForContext


def _hit(respuesta="El semillero Prometeo.", movimientos=None):
    return {
        "hit": True,
        "data": {"respuesta": respuesta, "movimientos": movimientos if movimientos is not None else [4]},
    }


def test_cache_unidentified_does_not_speak_placeholder(monkeypatch):
    monkeypatch.setattr(main_module, "search", lambda *args, **kwargs: _hit("El semillero Prometeo."))
    monkeypatch.setattr(main_module, "elegir_apertura", lambda contexto: None)
    monkeypatch.setattr(
        main_module,
        "generar_respuesta",
        lambda prompt: (_ for _ in ()).throw(AssertionError("llm must not run")),
    )
    obj = GlobalObjectForContext(
        id_global="g",
        etiqueta="Persona no identificada",
        confianza=0.1,
        question="¿Qué es Prometeo?",
    )
    catalogo = [{"id": 4, "name": "Saludo", "arduino_id": 1, "description": ""}]
    salida = main_module.responder(obj, catalogo)
    assert "Persona no identificada" not in salida["respuesta"]
    assert salida["respuesta"] == "El semillero Prometeo."
    assert salida["movimientos"] == [4]
    assert salida["fuente"] == "cache"
    assert salida["etiqueta"] == ""


def test_cache_name_without_apertura(monkeypatch):
    monkeypatch.setattr(main_module, "search", lambda *args, **kwargs: _hit("El semillero Prometeo."))
    monkeypatch.setattr(main_module, "elegir_apertura", lambda contexto: None)
    obj = GlobalObjectForContext(id_global="g", etiqueta="Andrea", confianza=0.9, question="dato")
    obj.contexto = None
    salida = main_module.responder(obj, [{"id": 4, "name": "Saludo", "arduino_id": 1, "description": ""}])
    assert salida["respuesta"].startswith("Andrea, ")
    assert "El semillero Prometeo." in salida["respuesta"] or "el semillero Prometeo." in salida["respuesta"]


def test_cache_name_with_apertura(monkeypatch):
    monkeypatch.setattr(main_module, "search", lambda *args, **kwargs: _hit("El semillero Prometeo."))
    monkeypatch.setattr(main_module, "elegir_apertura", lambda contexto: "veo que buscas orientacion")
    obj = GlobalObjectForContext(id_global="g", etiqueta="Andrea", confianza=0.9, question="dato")
    obj.contexto = "person looking at a map"
    salida = main_module.responder(obj, [{"id": 4, "name": "Saludo", "arduino_id": 1, "description": ""}])
    assert salida["respuesta"] == "Andrea, veo que buscas orientacion. El semillero Prometeo."


def test_cache_apertura_without_name(monkeypatch):
    monkeypatch.setattr(main_module, "search", lambda *args, **kwargs: _hit("El semillero Prometeo."))
    monkeypatch.setattr(main_module, "elegir_apertura", lambda contexto: "veo que buscas orientacion")
    obj = GlobalObjectForContext(
        id_global="g",
        etiqueta="Persona no identificada",
        confianza=0.1,
        question="dato",
    )
    obj.contexto = "person looking at a map"
    salida = main_module.responder(obj, [{"id": 4, "name": "Saludo", "arduino_id": 1, "description": ""}])
    assert salida["respuesta"] == "Veo que buscas orientacion. El semillero Prometeo."


def test_llm_strips_placeholder_and_does_not_index_name(monkeypatch):
    monkeypatch.setattr(main_module, "search", lambda *args, **kwargs: {"hit": False})
    monkeypatch.setattr(
        main_module,
        "generar_respuesta",
        lambda prompt: {
            "respuesta": "Andrea, el semillero Prometeo.",
            "movimientos": [4],
            "_backend": "gguf",
        },
    )
    captured = {}

    def fake_indexar(pregunta, respuesta, movimientos, collection_name=None):
        captured["respuesta"] = respuesta
        captured["movimientos"] = movimientos

    monkeypatch.setattr(main_module, "indexar", fake_indexar)
    obj = GlobalObjectForContext(id_global="g", etiqueta="Andrea", confianza=0.9, question="info sobre prometeo")
    salida = main_module.responder(obj, [{"id": 4, "name": "Saludo", "arduino_id": 1, "description": ""}])
    assert salida["respuesta"] == "Andrea, el semillero Prometeo."
    assert salida["movimientos"] == [4]
    assert salida["fuente"] == "llm"
    assert captured["respuesta"] == "El semillero Prometeo."


def test_llm_skips_index_when_name_cannot_be_stripped(monkeypatch):
    monkeypatch.setattr(main_module, "search", lambda *args, **kwargs: {"hit": False})
    monkeypatch.setattr(
        main_module,
        "generar_respuesta",
        lambda prompt: {
            "respuesta": "Hola Andrea, el semillero Prometeo te espera.",
            "movimientos": [4],
            "_backend": "gguf",
        },
    )
    indexed = {"called": False}

    def no_index(*args, **kwargs):
        indexed["called"] = True

    monkeypatch.setattr(main_module, "indexar", no_index)
    obj = GlobalObjectForContext(id_global="g", etiqueta="Andrea", confianza=0.9, question="info sobre prometeo")
    salida = main_module.responder(obj, [{"id": 4, "name": "Saludo", "arduino_id": 1, "description": ""}])
    assert "Andrea" in salida["respuesta"]
    assert indexed["called"] is False


def test_llm_unidentified_placeholder_is_stripped(monkeypatch):
    monkeypatch.setattr(main_module, "search", lambda *args, **kwargs: {"hit": False})
    monkeypatch.setattr(
        main_module,
        "generar_respuesta",
        lambda prompt: {
            "respuesta": "Persona no identificada, el semillero Prometeo.",
            "movimientos": [],
            "_backend": "gguf",
        },
    )
    monkeypatch.setattr(main_module, "indexar", lambda *args, **kwargs: None)
    obj = GlobalObjectForContext(
        id_global="g",
        etiqueta="Persona no identificada",
        confianza=0.1,
        question="info",
    )
    salida = main_module.responder(obj, [])
    assert salida["respuesta"] == "El semillero Prometeo."
    assert "Persona no identificada" not in salida["respuesta"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd pmai-model-vision-language
PYTHONPATH=. python -m pytest tests/test_personalizacion.py -v
```

Expected: FAIL — unidentified cache still starts with `Persona no identificada, `.

- [ ] **Step 3: Wire `responder()`**

Replace the current etiqueta assignment and both return paths. Keep `permitidos` and `milvus_caido`. Do **not** use `_normalizar_movimiento`.

```python
    etiqueta = _etiqueta_real(getattr(obj, "etiqueta", None))

    if cache["hit"]:
        respuesta_raw = _limpiar_sin_nombre(str(cache["data"]["respuesta"]))
        apertura = elegir_apertura(getattr(obj, "contexto", None))
        logger.info("accion_respuesta fuente=cache")
        return {
            "respuesta": _anteponer_nombre(etiqueta, respuesta_raw, apertura),
            "movimientos": _movimientos_de_salida(
                cache["data"].get("movimientos"), permitidos
            ),
            "fuente": "cache",
            "etiqueta": etiqueta,
        }

    logger.info("accion_llm_start")
    prompt = construir_prompt(obj, pregunta_limpia, secuencias)
    salida = generar_respuesta(prompt)
    salida["respuesta"] = _limpiar_sin_nombre(str(salida.get("respuesta") or ""))
    logger.info(
        "accion_respuesta fuente=llm backend=%s", salida.get("_backend", "gguf")
    )

    if (
        not milvus_caido
        and not tenia_groseria
        and _respuesta_interaccion_almacenable(salida.get("respuesta"))
    ):
        respuesta_sin_nombre = _quitar_nombre(salida["respuesta"], etiqueta)
        if respuesta_sin_nombre:
            try:
                indexar(
                    pregunta_limpia,
                    respuesta_sin_nombre,
                    salida.get("movimientos"),
                    collection_name=COL_INTERACCIONES,
                )
            except Exception:
                logger.exception("No se pudo indexar la interacción en Milvus")

    return {
        "respuesta": salida["respuesta"],
        "movimientos": _movimientos_de_salida(salida.get("movimientos"), permitidos),
        "fuente": "llm",
        "backend": salida.get("_backend", "gguf"),
        "etiqueta": etiqueta,
    }
```

Keep the knowledge/interacciones search blocks exactly as on `dev`.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd pmai-model-vision-language
PYTHONPATH=. python -m pytest tests/test_personalizacion.py tests/test_responder_movimientos.py -v
```

Expected: PASS. `test_cache_hit_parses_movimientos_json_string` still matches `startswith("Andrea, ")`. `test_search_failure_falls_through_to_the_model` still asserts `indexar` is not called (`milvus_caido`).

- [ ] **Step 5: Commit**

```bash
cd pmai-model-vision-language
git add utils/main.py tests/test_personalizacion.py
git commit -m "$(cat <<'EOF'
Personalize cache replies and strip names before indexing.

Unidentified speakers no longer hear the placeholder label; the turn still returns a filtered movimientos list.
EOF
)"
```

---

### Task 4: Prompt personalization on the live catalog

**Files:**
- Modify: `pmai-model-vision-language/prompt/principal.py`
- Modify: `pmai-model-vision-language/tests/test_catalogo_prompt.py`
- Modify: `pmai-model-vision-language/tests/test_personalizacion.py`

**Interfaces:**
- `construir_prompt` still `.format(etiqueta, contexto, pregunta, catalogo_movimientos=formatear_catalogo(secuencias))`.
- Do not copy `development`'s hardcoded 1–34 list into `PROMPT_PRINCIPAL`.

- [ ] **Step 1: Write the failing prompt tests**

Append to `tests/test_catalogo_prompt.py`:

```python
def test_prompt_personalization_and_datos_at_end():
    prompt = construir_prompt(Obj(), "Hola", [{"id": 4, "name": "Saludo", "arduino_id": 1, "description": ""}])
    assert "PERSONALIZACIÓN OBLIGATORIA" in prompt
    assert "NUNCA la menciones ni la repitas" in prompt
    assert prompt.rfind("[PERSONA_DETECTADA]") > prompt.rfind("<ejemplos>")
    assert '"movimientos": []' in prompt
    assert '"movimientos": [34' not in prompt
    assert "Saludo brazo derecho" not in prompt
```

Keep `test_prompt_has_no_fixed_gesture_ids` as it is.

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd pmai-model-vision-language
PYTHONPATH=. python -m pytest tests/test_catalogo_prompt.py -v
```

Expected: FAIL — `PERSONALIZACIÓN OBLIGATORIA` missing; `[PERSONA_DETECTADA]` currently appears before `<ejemplos>`.

- [ ] **Step 3: Edit `PROMPT_PRINCIPAL` on `dev`**

Work on the current `dev` prompt, not the `development` file.

1. In `<como_razonar>` Paso 1, after the existing sentence, add: if `[PERSONA_DETECTADA]` is `Persona no identificada`, do not mention it.

2. Inside `<reglas>`, **before** `FORMATO`, insert the `PERSONALIZACIÓN OBLIGATORIA` four bullets from `development` (`git show development:prompt/principal.py`, the block starting `PERSONALIZACIÓN OBLIGATORIA`). Do not take that file's FORMAT line about inventing ids.

3. Cut the whole `<datos_de_entrada>…</datos_de_entrada>` block from its current place (before `<catalogo_movimientos>`) and paste it **after** `</ejemplos>`. Then add:

```
RECUERDA: dirígete a "{etiqueta}" por su nombre (solo si es un nombre real; si es "Persona no identificada", no la menciones en la respuesta), refleja el contexto visual si aporta algo, responde en español y devuelve SOLO el JSON.
```

Do **not** add «no inventes ids» here: the live table already covers that.

4. Examples: you may add `PERSONA:` / `CONTEXTO:` labels like `development` (Andrea, Daniel, mapa). Every `SALIDA` keeps `"movimientos": []`. If you copy an example from `development` that has `[34, 30]` or any ids, replace them with `[]`.

5. Leave `{catalogo_movimientos}`, `formatear_catalogo`, and `construir_prompt` signatures unchanged. Section order must be: identidad → como_razonar → catalogo_movimientos → reglas → formato_salida → ejemplos → datos_de_entrada → RECUERDA.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd pmai-model-vision-language
PYTHONPATH=. python -m pytest tests/test_catalogo_prompt.py tests/test_personalizacion.py tests/test_responder_movimientos.py -v
```

Expected: PASS. `test_prompt_has_no_fixed_gesture_ids` still forbids `· 33` / `Saludo brazo derecho`.

- [ ] **Step 5: Commit**

```bash
cd pmai-model-vision-language
git add prompt/principal.py tests/test_catalogo_prompt.py tests/test_personalizacion.py
git commit -m "$(cat <<'EOF'
Put personalization rules in the live-catalog prompt.

Keep example movimiento lists empty and the Markdown table as the only id source.
EOF
)"
```

---

### Task 5: Full suite and launcher pointer

**Files:**
- Modify: launcher submodule pointer for `pmai-model-vision-language` only after the owner commits exist.
- Do not bump robotics/web-main.

- [ ] **Step 1: Run the whole action-model suite**

```bash
cd pmai-model-vision-language
PYTHONPATH=. python -m pytest tests/ -v
```

Expected: PASS, including `test_gguf_singleton`, `test_milvus_startup`, `test_openai_router`.

- [ ] **Step 2: Sanity grep (must be empty / must exist)**

```bash
cd pmai-model-vision-language
rg -n '"movimiento"|_normalizar_movimiento|Saludo brazo derecho|· 33|· 34' prompt/principal.py utils/main.py
rg -n 'APERTURAS_PATH|UMBRAL_APERTURA' utils/config.py
test -f data/aperturas.json && python -c "import json; d=json.load(open('data/aperturas.json')); assert len(d)==41"
```

`utils/main.py` / `prompt/principal.py` must not contain `_normalizar_movimiento` or the hardcoded catalog phrases. Config must contain the two new names.

- [ ] **Step 3: Commit the launcher pointer (only if the user asked to update the launcher)**

```bash
cd /home/personal/Projects/ulibre-prometeo/pba-launcher
git add pmai-model-vision-language
git commit -m "$(cat <<'EOF'
Point action-model at the personalization port on dev.

Keep the live catalog and movimientos list; openings and name handling land with the bind mount.
EOF
)"
```

Do not push unless asked.

---

## Self-review

1. Spec coverage: openings JSON, helpers, cache/LLM/index, prompt order, gitignore, tests, non-merge.  
2. Placeholders: none. Commands are `cd pmai-model-vision-language` + `PYTHONPATH=. python -m pytest …`.  
3. Type consistency: `movimientos` remains `list[int]`; `elegir_apertura` remains `str | None`; `_etiqueta_real` remains `str` (possibly empty).  
4. Existing tests named and kept.  
5. No mai-core / chat / robotics edits.

## Execution options

Plan complete and saved to `docs/superpowers/plans/2026-10-31-action-model-personalization-port.md`.

Two execution options:

**1. Subagent-Driven (this session)** — dispatch a fresh subagent per task, review between tasks.

**2. Inline Execution (this session)** — implement here, commit in `pmai-model-vision-language` after each task.

Which approach?
