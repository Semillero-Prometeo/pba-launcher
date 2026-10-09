# R-ONE Interaction Turn Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One turn inside mai-core answers a voice transcript or a web chat question with BLIP context, the action model, robotics speech, and robotics gestures.

**Architecture:** mai-core owns `InteractionTurn`. It imports `model_context` (BLIP) and the existing vision-language package (`utils`, `prompt`, `models`) as libraries on `PYTHONPATH`. Management forwards `chatService.chat` to `MAI_CORE_MS.interactionService.ask` and does not speak. Robotics adds an optional description when it lists actions. Milvus Lite, BLIP, the embedding model, and one Gemma instance are prepared at mai-core startup.

**Tech Stack:** Python 3.12 (mai-core, both AI repos), Python 3.13 (ms-robotics), NestJS 11, NATS, Milvus Lite, BLIP, llama-cpp-python, pytest, Jest.

## Global Constraints

- Subject `MAI_CORE_MS.interactionService.ask`. In `{ "message": string }`. Out `{ "reply": string }`.
- Management uses a dedicated NATS client with timeout 120000 ms for that call. The existing client stays at 20000 ms.
- Busy phrase, exact: `Sigo respondiendo, un momento.`
- Apology, exact: `Lo siento, no puedo responder en este momento.`
- Short voice phrase, exact: `No te escuche con claridad, puedes repetirlo por favor.` Threshold: 14 characters. Chat does not use this threshold.
- Unidentified label, exact: `Persona no identificada`.
- Person choice: highest `confianza`; tie breaks to the lexicographically smaller `id_global`.
- JPEG crop quality 85. Base64 is raw (no required `data:` prefix).
- Movement ids are valid only if they appear in that call's catalog. At most 3, model order, unknown ids dropped.
- Description file default `/usr/src/app/data/action-descriptions.json`, override `ACTION_DESCRIPTIONS_PATH`. Missing file, invalid JSON, or missing row yields `description=""`.
- `MILVUS_DB_PATH=/data/milvus/androide_milvus.db`. Host volume `./data/milvus` mounted read-write at `/data/milvus`.
- `PYTHONPATH` keeps `/app/src` and adds the two library mounts.
- `chatService.declarePoema` stays on OpenAI and still calls `speak`.
- Captioning stays BLIP. OpenAI-then-Gemma routing stays.
- One Gemma instance per process. Clear the KV cache before each generation. If that call returns empty text, rebuild the instance once and retry only that call.
- Startup failures of Milvus, BLIP, embeddings, or Gemma do not stop cameras, ReID, or NATS.
- Commits for library and service code go inside that submodule. Compose, Dockerfile, and this plan commit in the launcher repo.

---

## File structure

`pmai-model-context` and `pmai-model-vision-language` both ship a top-level package named `utils`. Putting both roots on `PYTHONPATH` makes one import shadow the other. Rename the context package to `model_context` before mai-core imports either library. The vision-language package stays `utils` / `prompt` / `models`.

| File | Responsibility |
|---|---|
| `pba-ms-robotics/src/action/descriptions.py` | Load the JSON and attach `description` to commands |
| `pba-ms-robotics/src/action/interfaces/command_interface.py` | `Command.description` |
| `pba-ms-robotics/src/action/action_service.py` | Call the joiner from `get_actions` |
| `pmai-model-context/model_context/` | Former `utils/` package, unique import name |
| `pmai-model-vision-language/prompt/principal.py` | Markdown table is the only movement catalog |
| `pmai-model-vision-language/utils/main.py` | `responder()` returns at most three catalog ids |
| `pmai-model-vision-language/utils/gguf/ggufapi.py` | One Gemma instance, one empty-output rebuild |
| `pmai-mai-core/src/pmai_core/pipeline/crop.py` | BBox to JPEG base64 |
| `pmai-mai-core/src/pmai_core/pipeline/interaction_turn.py` | The turn |
| `pmai-mai-core/src/pmai_core/pipeline/runtime.py` | Startup of Milvus, BLIP, embeddings, Gemma |
| `pmai-mai-core/src/pmai_core/api/interaction/interaction_controller.py` | NATS ask handler |
| `pmai-mai-core/src/pmai_core/api/robotics_ms/robotics_ms_service.py` | `get_actions` and `execute_action` |
| `pba-ms-management/src/ms-mai-core-integration/` | 120s client and `ask()` |
| `docker-compose.yml`, `pmai-mai-core/Dockerfile.dev` | Mounts, image dependencies, Milvus volume |

---

### Task 1: Robotics action descriptions

**Files:**
- Create: `pba-ms-robotics/src/action/descriptions.py`
- Create: `pba-ms-robotics/tests/test_action_descriptions.py`
- Modify: `pba-ms-robotics/src/action/interfaces/command_interface.py`
- Modify: `pba-ms-robotics/src/action/action_service.py`
- Modify: `pba-ms-robotics/src/core/settings/env.py`

**Interfaces:**
- Consumes: Arduino commands already shaped as `Command(id, name, arduino_id)`.
- Produces: `Command.description: str = ""`. `load_descriptions(path: Path) -> dict[tuple[int, int], str]`. `apply_descriptions(commands: list[Command], descriptions: dict[tuple[int, int], str]) -> list[Command]`. `get_actions()` returns those commands with descriptions filled.

- [ ] **Step 1: Write the failing test**

```python
import json
from pathlib import Path

from src.action.descriptions import apply_descriptions, load_descriptions
from src.action.interfaces.command_interface import Command


def test_missing_file_yields_empty_map(tmp_path: Path):
    assert load_descriptions(tmp_path / "missing.json") == {}


def test_invalid_json_yields_empty_map(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")
    assert load_descriptions(path) == {}


def test_apply_descriptions_joins_on_arduino_and_id(tmp_path: Path):
    path = tmp_path / "action-descriptions.json"
    path.write_text(
        json.dumps(
            [
                {"arduino_id": 1, "id": 4, "description": "Saludo con el brazo derecho"},
                {"arduino_id": 2, "id": 4, "description": "Otro arduino"},
            ]
        ),
        encoding="utf-8",
    )
    commands = [
        Command(id=4, name="Saludo", arduino_id=1),
        Command(id=9, name="Reposo", arduino_id=1),
    ]
    described = apply_descriptions(commands, load_descriptions(path))
    assert described[0].description == "Saludo con el brazo derecho"
    assert described[1].description == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run from `pba-ms-robotics`: `pytest tests/test_action_descriptions.py -v`  
Expected: FAIL, `src.action.descriptions` cannot be imported, or `Command` has no `description`.

- [ ] **Step 3: Write minimal implementation**

`command_interface.py`:

```python
from pydantic import BaseModel, Field


class Command(BaseModel):
    id: int
    name: str
    arduino_id: int
    description: str = Field(default="")
```

`env.py` add:

```python
ACTION_DESCRIPTIONS_PATH: str = os.getenv(
    "ACTION_DESCRIPTIONS_PATH",
    "/usr/src/app/data/action-descriptions.json",
)
```

`descriptions.py`:

```python
import json
from pathlib import Path

from src.action.interfaces.command_interface import Command


def load_descriptions(path: Path) -> dict[tuple[int, int], str]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return {}
    if not isinstance(raw, list):
        return {}
    found: dict[tuple[int, int], str] = {}
    for row in raw:
        if not isinstance(row, dict):
            continue
        try:
            key = (int(row["arduino_id"]), int(row["id"]))
        except (KeyError, TypeError, ValueError):
            continue
        text = row.get("description", "")
        found[key] = text if isinstance(text, str) else ""
    return found


def apply_descriptions(
    commands: list[Command],
    descriptions: dict[tuple[int, int], str],
) -> list[Command]:
    return [
        command.model_copy(
            update={"description": descriptions.get((command.arduino_id, command.id), "")}
        )
        for command in commands
    ]
```

In `ActionService.get_actions`, after the Arduino list is built:

```python
from pathlib import Path

from src.action.descriptions import apply_descriptions, load_descriptions
from src.core.settings.env import ACTION_DESCRIPTIONS_PATH

# at the return of get_actions:
descriptions = load_descriptions(Path(ACTION_DESCRIPTIONS_PATH))
return apply_descriptions(commands, descriptions)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_action_descriptions.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd pba-ms-robotics
git add src/action/descriptions.py src/action/interfaces/command_interface.py src/action/action_service.py src/core/settings/env.py tests/test_action_descriptions.py
git commit -m "$(cat <<'EOF'
Attach optional descriptions when robotics lists actions.

EOF
)"
```

---

### Task 2: Rename the context package so both libraries can load

**Files:**
- Create: `pmai-model-context/model_context/` (move of `pmai-model-context/utils/`)
- Modify: `pmai-model-context/model_context/context.py` (the moved `generate_context_from_base64` import)
- Modify: `pmai-model-context/model_context/model.py` import path
- Create: `pmai-model-context/tests/test_package_import.py`

**Interfaces:**
- Consumes: current `utils.model.import_Blip_model` and `utils.context.generate_context_from_base64`.
- Produces: `model_context.model.import_Blip_model`, `model_context.context.generate_context_from_base64`, `model_context.local_object.GlobalObjectForContext` with `question: str | None`.

- [ ] **Step 1: Write the failing test**

```python
from model_context.local_object import GlobalObjectForContext


def test_context_object_accepts_question():
    obj = GlobalObjectForContext(
        id_global="g1",
        etiqueta="Andrea",
        confianza=0.8,
        question="Hola",
    )
    assert obj.question == "Hola"
```

- [ ] **Step 2: Run test to verify it fails**

Run from `pmai-model-context`: `python -m pytest tests/test_package_import.py -v`  
Expected: FAIL with `ModuleNotFoundError: model_context`.

- [ ] **Step 3: Move the package and fix imports**

```bash
cd pmai-model-context
git mv utils model_context
```

In `model_context/model.py` replace `from utils.cache import get_cache, update_cache` with `from model_context.cache import get_cache, update_cache`.

In `model_context/context.py` replace `from utils.decoder import base64_to_image` with `from model_context.decoder import base64_to_image`.

Leave `question` on `GlobalObjectForContext` as it already is.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_package_import.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd pmai-model-context
git add model_context tests/test_package_import.py
git commit -m "$(cat <<'EOF'
Rename the context package so it can load beside the action model.

EOF
)"
```

---

### Task 3: Markdown movement table in the action prompt

**Files:**
- Modify: `pmai-model-vision-language/prompt/principal.py`
- Create: `pmai-model-vision-language/tests/test_catalogo_prompt.py`
- Modify: `pmai-model-vision-language/pyproject.toml` (add a `dev` extra with `pytest>=8`)

**Interfaces:**
- Consumes: catalog dicts `{id, name, arduino_id, description}`.
- Produces: `formatear_catalogo(secuencias: list[dict]) -> str` as a Markdown table, or the exact text `(No hay movimientos disponibles)`. `construir_prompt` inserts that table and does not contain the fixed ids 4, 6, 33, 34.

- [ ] **Step 1: Write the failing test**

```python
from prompt.principal import construir_prompt, formatear_catalogo


class Obj:
    etiqueta = "Andrea"
    contexto = "persona de frente"


def test_empty_catalog_is_explicit():
    assert formatear_catalogo([]) == "(No hay movimientos disponibles)"


def test_catalog_is_a_markdown_table_with_blank_description():
    table = formatear_catalogo(
        [{"id": 4, "name": "Saludo", "arduino_id": 1, "description": ""}]
    )
    assert "| id | nombre | arduino_id | descripcion |" in table
    assert "| 4 | Saludo | 1 |  |" in table


def test_prompt_has_no_fixed_gesture_ids():
    prompt = construir_prompt(Obj(), "Hola", [{"id": 4, "name": "Saludo", "arduino_id": 1, "description": ""}])
    assert "Saludo brazo derecho" not in prompt
    assert "· 33" not in prompt
    assert "· 34" not in prompt
    assert "| 4 | Saludo | 1 |  |" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run from `pmai-model-vision-language`: `python -m pytest tests/test_catalogo_prompt.py -v`  
Expected: FAIL because the formatter still emits `- ID 4: Saludo` and the prompt still contains `Saludo brazo derecho`.

- [ ] **Step 3: Replace the catalog block and the formatter**

Replace the whole `<catalogo_movimientos>...</catalogo_movimientos>` element with:

```text
<catalogo_movimientos>
Elige ids EXCLUSIVAMENTE de esta tabla. La columna descripcion puede llegar vacía: en ese caso usa el nombre. No inventes ids.

{catalogo_movimientos}
</catalogo_movimientos>
```

Inside `<reglas>`, add this bullet and keep the existing JSON-only rule:

```text
- Los ejemplos muestran tono y forma JSON. Sus listas movimientos van vacías a propósito y no son ids reales. En la respuesta real, movimientos contiene de 1 a 3 enteros copiados de la tabla de esta petición, o [] si ninguno aplica.
```

In `<ejemplos>`, replace every movements array with `[]`. The current arrays are `[4, 6]`, `[7, 32]`, `[7, 2]`, `[8, 5]`, `[21, 16]`, `[3, 14]`, `[5, 12]`, `[2, 10]`, `[34, 30]`.

Replace `formatear_catalogo`:

```python
def _celda(valor: object) -> str:
    texto = "" if valor is None else str(valor)
    return texto.replace("|", "/").replace("\n", " ").strip()


def formatear_catalogo(secuencias: list[dict]) -> str:
    if not secuencias:
        return "(No hay movimientos disponibles)"
    filas = ["| id | nombre | arduino_id | descripcion |", "|----|--------|------------|-------------|"]
    for mov in secuencias:
        filas.append(
            "| {id} | {nombre} | {arduino} | {descripcion} |".format(
                id=_celda(mov.get("id")),
                nombre=_celda(mov.get("name")),
                arduino=_celda(mov.get("arduino_id")),
                descripcion=_celda(mov.get("description", "")),
            )
        )
    return "\n".join(filas)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_catalogo_prompt.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd pmai-model-vision-language
git add prompt/principal.py tests/test_catalogo_prompt.py pyproject.toml
git commit -m "$(cat <<'EOF'
Feed the action prompt a Markdown table of live movements.

EOF
)"
```

---

### Task 4: responder returns catalog-limited movement ids

**Files:**
- Modify: `pmai-model-vision-language/utils/gguf/ggufapi.py` (`_validar_movimientos` signature only in this task)
- Modify: `pmai-model-vision-language/utils/gpt/gptapi.py` (pass the allowed set through)
- Modify: `pmai-model-vision-language/utils/main.py`
- Modify: `pmai-model-vision-language/app.py` (read the first id from the list)
- Create: `pmai-model-vision-language/tests/test_responder_movimientos.py`

**Interfaces:**
- Consumes: `formatear_catalogo` from Task 3. `generar_respuesta(prompt) -> {"respuesta", "movimientos", "_backend"}`.
- Produces: `_validar_movimientos(movimientos: list, permitidos: set[int]) -> list[int]`. `responder(obj, secuencias: list[dict]) -> dict` with `movimientos: list[int]` of length at most 3. Search exceptions are a cache miss. Index exceptions are logged and ignored.

- [ ] **Step 1: Write the failing test**

```python
import utils.main as main_module
from models.schemas import GlobalObjectForContext


def test_responder_keeps_three_catalog_ids_and_drops_unknown(monkeypatch):
    monkeypatch.setattr(main_module, "search", lambda *args, **kwargs: {"hit": False})
    monkeypatch.setattr(
        main_module,
        "generar_respuesta",
        lambda prompt: {"respuesta": "Hola", "movimientos": [4, 99, 2, 7, 8], "_backend": "gguf"},
    )
    monkeypatch.setattr(main_module, "indexar", lambda *args, **kwargs: None)
    obj = GlobalObjectForContext(id_global="g", etiqueta="Andrea", confianza=0.9, question="Hola")
    catalogo = [
        {"id": 4, "name": "Saludo", "arduino_id": 1, "description": ""},
        {"id": 2, "name": "Asentir", "arduino_id": 1, "description": ""},
        {"id": 7, "name": "Pecho", "arduino_id": 1, "description": ""},
        {"id": 8, "name": "Hombros", "arduino_id": 1, "description": ""},
    ]
    salida = main_module.responder(obj, catalogo)
    assert salida["movimientos"] == [4, 2, 7]
    assert salida["respuesta"] == "Hola"
    assert salida["fuente"] == "llm"


def test_search_failure_falls_through_to_the_model(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("milvus down")

    monkeypatch.setattr(main_module, "search", boom)
    monkeypatch.setattr(
        main_module,
        "generar_respuesta",
        lambda prompt: {"respuesta": "Desde el modelo", "movimientos": [], "_backend": "gguf"},
    )
    indexed = {"called": False}

    def no_index(*args, **kwargs):
        indexed["called"] = True

    monkeypatch.setattr(main_module, "indexar", no_index)
    obj = GlobalObjectForContext(id_global="g", etiqueta="Andrea", confianza=0.9, question="dato")
    salida = main_module.responder(obj, [])
    assert salida["respuesta"] == "Desde el modelo"
    assert indexed["called"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_responder_movimientos.py -v`  
Expected: FAIL because `responder` returns `movimiento` as one int and does not accept a permit set.

- [ ] **Step 3: Filter ids in one place and keep the list**

Change `_validar_movimientos` in `utils/gguf/ggufapi.py` to:

```python
def _validar_movimientos(movimientos: list, permitidos: set[int] | None = None) -> list:
    if not movimientos or not isinstance(movimientos, list):
        return []
    validos = []
    for mov_id in movimientos:
        try:
            id_int = int(mov_id)
        except (TypeError, ValueError):
            continue
        if permitidos is not None and id_int not in permitidos:
            continue
        validos.append(id_int)
    return validos
```

`generar_respuesta` stays a router and does not filter. `responder` filters, so a `None` permit set is only for callers that do not know the catalog yet. `indexar.py` and `alimentar_basevec.py` call `_validar_movimientos` with one argument; the default `None` keeps those calls working and no longer rejects ids outside 1–34.

In `responder`, build `permitidos = {int(item["id"]) for item in secuencias}` and use it for both the cache hit and the LLM result:

```python
def _movimientos_de_salida(movimientos, permitidos: set[int]) -> list[int]:
    from utils.gguf.ggufapi import _validar_movimientos
    return _validar_movimientos(movimientos, permitidos)[:3]
```

Cache return:

```python
return {
    "respuesta": f"{etiqueta}, {respuesta_raw}",
    "movimientos": _movimientos_de_salida(cache["data"].get("movimientos"), permitidos),
    "fuente": "cache",
    "etiqueta": etiqueta,
}
```

LLM return uses `salida.get("movimientos")` the same way and still sets `backend`. Wrap each `search(...)` in `try/except Exception`. If either search raises, remember `milvus_caido = True` and use `{"hit": False}`. Call `indexar` only when `milvus_caido` is false; if `indexar` itself raises, log and continue. Delete `_normalizar_movimiento` if nothing else calls it.

In `app.py`, replace the single-id read:

```python
movs = resultado.get("movimientos") or []
mov_id = movs[0] if movs else None
mov_texto = "Sin movimiento" if mov_id is None else _formatear_movimientos(mov_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_responder_movimientos.py tests/test_catalogo_prompt.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd pmai-model-vision-language
git add utils/main.py utils/gguf/ggufapi.py app.py tests/test_responder_movimientos.py
git commit -m "$(cat <<'EOF'
Return at most three movement ids that exist in the live catalog.

EOF
)"
```

---

### Task 5: Load Gemma once

**Files:**
- Modify: `pmai-model-vision-language/utils/gguf/ggufapi.py`
- Create: `pmai-model-vision-language/tests/test_gguf_singleton.py`

**Interfaces:**
- Consumes: `_GEMMA_CHAT_TEMPLATE`, `_validar_movimientos`.
- Produces: `precargar() -> None`. `llamar_gguf(prompt: str) -> dict`. A test double can replace `_nueva_instancia`.

- [ ] **Step 1: Write the failing test**

```python
import utils.gguf.ggufapi as gguf


class FakeLlama:
    def __init__(self):
        self.resets = 0
        self.texts = [""]

    def reset(self):
        self.resets += 1

    def __call__(self, prompt, max_tokens, stop, **params):
        text = self.texts.pop(0) if self.texts else '{"respuesta":"ok","movimientos":[]}'
        return {"choices": [{"text": text}]}


def test_empty_generation_rebuilds_once(monkeypatch):
    created = []

    def factory():
        llama = FakeLlama()
        if not created:
            llama.texts = [""]
        else:
            llama.texts = ['{"respuesta":"ok","movimientos":[1]}']
        created.append(llama)
        return llama

    monkeypatch.setattr(gguf, "_LLAMA_DISPONIBLE", True)
    monkeypatch.setattr(gguf, "_nueva_instancia", factory)
    monkeypatch.setattr(gguf.os.path, "isfile", lambda path: True)
    gguf._llm = None
    salida = gguf.llamar_gguf("pregunta")
    assert salida["respuesta"] == "ok"
    assert len(created) == 2
    assert created[0].resets == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gguf_singleton.py -v`  
Expected: FAIL because each call constructs a new Llama and the empty retry uses temperature retries, so `len(created)` is not 2 under the new contract. The test fails until `reset()` exists on the shared instance path.

- [ ] **Step 3: Keep one instance and retry once**

Add a module lock and `_llm = None`. `precargar()` calls `_obtener_o_crear()` inside the lock and swallows `ImportError` and `FileNotFoundError` after logging. `_obtener_o_crear()` returns the existing instance or assigns `_nueva_instancia()`. `_descartar()` sets `_llm = None`.

`llamar_gguf` holds the lock for the whole call. It formats the Gemma template once. For attempt in `(1, 2)`: get or create the instance, call `reset()`, run one generation with `temperature=0.3`, `top_p=0.9`, `max_tokens=1024`, `stop=["<end_of_turn>"]`. If the stripped text is non-empty, parse JSON as the function already does and return. If it is empty and this was attempt 1, `_descartar()` and continue. If attempt 2 is empty, return `{"respuesta": "Lo siento, no puedo responder en este momento.", "movimientos": []}`. Missing library or missing file returns that same apology without raising.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_gguf_singleton.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd pmai-model-vision-language
git add utils/gguf/ggufapi.py tests/test_gguf_singleton.py
git commit -m "$(cat <<'EOF'
Keep one local Gemma instance and rebuild it only after an empty reply.

EOF
)"
```

---

### Task 6: Milvus collections exist before the first question

**Files:**
- Create: `pmai-model-vision-language/tests/test_milvus_startup.py`
- Modify: `pmai-model-vision-language/utils/milvus/conexion.py` only if the test cannot reset module globals. Add `reiniciar_cliente() -> None` that sets `_client = None` and `_colecciones_inicializadas = False`.

**Interfaces:**
- Consumes: `MILVUS_DB_PATH`, `COL_CONOCIMIENTO`, `COL_INTERACCIONES`.
- Produces: `get_client() -> MilvusClient` with both collections loaded. `reiniciar_cliente() -> None` for tests and for a failed startup retry.

- [ ] **Step 1: Write the failing test**

```python
import utils.milvus.conexion as conexion
from utils.config import COL_CONOCIMIENTO, COL_INTERACCIONES


def test_startup_creates_both_collections(tmp_path, monkeypatch):
    db = tmp_path / "androide_milvus.db"
    monkeypatch.setattr(conexion, "MILVUS_DB_PATH", str(db))
    conexion.reiniciar_cliente()
    client = conexion.get_client()
    assert client.has_collection(COL_CONOCIMIENTO)
    assert client.has_collection(COL_INTERACCIONES)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_milvus_startup.py -v`  
Expected: FAIL with `AttributeError: reiniciar_cliente` or a connection to the repo's real db path.

- [ ] **Step 3: Add the reset and keep creation on get_client**

```python
def reiniciar_cliente() -> None:
    global _client, _colecciones_inicializadas
    _client = None
    _colecciones_inicializadas = False
```

`get_client` already calls `asegurar_colecciones()`. No new collection schema.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_milvus_startup.py -v`  
Expected: PASS, and `tmp_path` contains the db file.

- [ ] **Step 5: Commit**

```bash
cd pmai-model-vision-language
git add utils/milvus/conexion.py tests/test_milvus_startup.py
git commit -m "$(cat <<'EOF'
Create Milvus collections when the client starts, including in tests.

EOF
)"
```

---

### Task 7: Scene crop and the interaction turn

**Files:**
- Modify: `pmai-mai-core/src/pmai_core/domain/context_object.py`
- Create: `pmai-mai-core/src/pmai_core/pipeline/crop.py`
- Create: `pmai-mai-core/src/pmai_core/pipeline/interaction_turn.py`
- Create: `pmai-mai-core/tests/test_interaction_turn.py`

**Interfaces:**
- Consumes: `GlobalObjectForContext` plus new `question: str | None = None`.
- Produces: `crop_jpeg_base64(frame: np.ndarray, bbox: tuple[int, int, int, int], quality: int = 85) -> str`. `choose_person(objects: list[GlobalObjectForContext]) -> GlobalObjectForContext | None`. `InteractionTurn.ask(message: str, source: str) -> str` where `source` is `"voice"` or `"chat"`.

- [ ] **Step 1: Write the failing test**

```python
import numpy as np

from pmai_core.domain.context_object import GlobalObjectForContext
from pmai_core.pipeline.crop import crop_jpeg_base64
from pmai_core.pipeline.interaction_turn import InteractionTurn, choose_person


def _person(gid: str, confianza: float) -> GlobalObjectForContext:
    return GlobalObjectForContext(
        id_global=gid,
        etiqueta=gid,
        confianza=confianza,
        camera_id="cam-a",
        bbox=(0, 0, 2, 2),
    )


def test_choose_person_breaks_ties_by_id():
    chosen = choose_person([_person("b", 0.5), _person("a", 0.5), _person("c", 0.4)])
    assert chosen is not None
    assert chosen.id_global == "a"


def test_turn_without_person_skips_caption_and_speaks():
    calls = {"caption": 0, "speak": [], "execute": []}

    def caption(_: str) -> str:
        calls["caption"] += 1
        return "no"

    turn = InteractionTurn(
        objects=lambda: [],
        frame=lambda camera_id: None,
        caption=caption,
        load_catalog=lambda: [{"id": 1, "name": "Reposo", "arduino_id": 1, "description": ""}],
        answer=lambda obj, catalog: {"respuesta": "Hola", "movimientos": [1, 99]},
        speak=lambda text: calls["speak"].append(text),
        execute=lambda action_id, arduino_id: calls["execute"].append((action_id, arduino_id)),
    )
    reply = turn.ask("¿Quién eres tú ahora?", source="chat")
    assert reply == "Hola"
    assert calls["caption"] == 0
    assert calls["speak"] == ["Hola"]
    assert calls["execute"] == [(1, 1)]


def test_blip_failure_still_answers():
    frame = np.zeros((4, 4, 3), dtype=np.uint8)

    def boom(_: str) -> str:
        raise RuntimeError("blip")

    turn = InteractionTurn(
        objects=lambda: [_person("a", 0.9)],
        frame=lambda camera_id: frame,
        caption=boom,
        load_catalog=lambda: [],
        answer=lambda obj, catalog: {"respuesta": f"vi:{obj.contexto}", "movimientos": []},
        speak=lambda text: None,
        execute=lambda action_id, arduino_id: None,
    )
    assert turn.ask("una pregunta larga de chat", source="chat") == "vi:None"


def test_second_call_while_busy_is_not_spoken_for_chat():
    import threading

    started = threading.Event()
    release = threading.Event()
    spoken: list[str] = []

    def answer(obj, catalog):
        started.set()
        assert release.wait(timeout=2)
        return {"respuesta": "tarde", "movimientos": []}

    turn = InteractionTurn(
        objects=lambda: [],
        frame=lambda camera_id: None,
        caption=lambda image: "",
        load_catalog=lambda: [],
        answer=answer,
        speak=lambda text: spoken.append(text),
        execute=lambda action_id, arduino_id: None,
    )
    worker = threading.Thread(target=lambda: turn.ask("pregunta suficientemente larga", source="chat"))
    worker.start()
    assert started.wait(timeout=2)
    busy = turn.ask("otra pregunta larga", source="chat")
    release.set()
    worker.join(timeout=2)
    assert busy == "Sigo respondiendo, un momento."
    assert "Sigo respondiendo, un momento." not in spoken


def test_short_voice_does_not_call_the_model():
    called = {"answer": 0}
    spoken = []
    turn = InteractionTurn(
        objects=lambda: [],
        frame=lambda camera_id: None,
        caption=lambda image: "",
        load_catalog=lambda: [],
        answer=lambda obj, catalog: called.__setitem__("answer", 1),
        speak=lambda text: spoken.append(text),
        execute=lambda action_id, arduino_id: None,
    )
    reply = turn.ask("hola", source="voice")
    assert reply == "No te escuche con claridad, puedes repetirlo por favor."
    assert spoken == [reply]
    assert called["answer"] == 0


def test_crop_is_raw_jpeg_base64():
    import base64

    frame = np.zeros((8, 8, 3), dtype=np.uint8)
    frame[:, :] = (0, 0, 255)
    encoded = crop_jpeg_base64(frame, (1, 1, 5, 5))
    raw = base64.b64decode(encoded)
    assert raw[:2] == b"\xff\xd8"
    assert not encoded.startswith("data:")
```

- [ ] **Step 2: Run test to verify it fails**

Run from `pmai-mai-core`: `pytest tests/test_interaction_turn.py -v`  
Expected: FAIL with import errors for `crop` and `interaction_turn`, and `question` missing if a later assertion needs it. Add `question` in this task even though this test file does not require a question string yet.

- [ ] **Step 3: Implement crop, choice, and the turn**

Add to `context_object.py`:

```python
question: str | None = Field(default=None, description="User question for this turn")
```

`crop.py` clips the bbox to the frame, encodes BGR with `cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, quality])`, and returns `base64.b64encode(buf).decode("ascii")`. An empty clip raises `ValueError`.

`choose_person` returns `None` for an empty list, otherwise `min(objects, key=lambda obj: (-obj.confianza, obj.id_global))`.

`InteractionTurn.__init__` stores the callables, a `threading.Lock`, `min_voice_chars=14`, and the two exact phrases from Global Constraints. `ask`:

1. For `source=="voice"`, if `len(message.strip()) < min_voice_chars`, speak the short phrase and return it.
2. `acquire(blocking=False)`. On failure: if voice, speak the busy phrase; always return the busy phrase. Chat does not speak it.
3. In `try` / `finally` (`release`): choose the person. Copy it with `question=message.strip()`. If there is a bbox and a frame, crop and call `caption`. On any exception, leave `contexto` as it was (empty / None).
4. `load_catalog()` inside `try/except`. Failure logs and uses `[]`.
5. `answer(obj, catalog)` inside `try/except`. Failure, or a blank `respuesta`, uses the apology and skips gestures.
6. Build the execution list: for each id in `movimientos` up to 3, find the catalog row with that `id`. Missing rows are skipped. Duplicate ids repeat.
7. Start `speak(reply)` on a daemon thread. On the caller thread, call `execute` per row and catch each exception. Then join the speak thread and catch its exception. Return `reply`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_interaction_turn.py -v`  
Expected: PASS. The busy test must not deadlock: the first call blocks inside `answer` until `release` is appended.

- [ ] **Step 5: Commit**

```bash
cd pmai-mai-core
git add src/pmai_core/domain/context_object.py src/pmai_core/pipeline/crop.py src/pmai_core/pipeline/interaction_turn.py tests/test_interaction_turn.py
git commit -m "$(cat <<'EOF'
Add the interaction turn that captions, answers, speaks, and gestures.

EOF
)"
```

---

### Task 8: Wire the turn to NATS, the microphone, robotics, and startup

**Files:**
- Modify: `pmai-mai-core/src/pmai_core/api/robotics_ms/robotics_ms_service.py`
- Create: `pmai-mai-core/src/pmai_core/api/interaction/interaction_controller.py`
- Create: `pmai-mai-core/src/pmai_core/pipeline/runtime.py`
- Create: `pmai-mai-core/src/pmai_core/pipeline/scene.py`
- Modify: `pmai-mai-core/src/pmai_core/core/nats/nats_subscribers.py`
- Modify: `pmai-mai-core/src/pmai_core/resources/audio/service.py`
- Modify: `pmai-mai-core/src/pmai_core/app.py`
- Create: `pmai-mai-core/tests/test_interaction_wiring.py`

**Interfaces:**
- Consumes: `InteractionTurn.ask(message: str, source: str) -> str` from Task 7. `RoboticsMsService.sync_request` via `nats_handler`. `get_actions` response shape `{ "data": [ {"id", "name", "arduino_id", "description"} ] }`.
- Produces: `RoboticsMsService.get_actions() -> list[dict]`, `RoboticsMsService.execute_action(action_id: int, arduino_id: int) -> None`. `InteractionController.ask(data: dict) -> AskReply` with `reply: str`. `prepare_runtime() -> None`. `AudioService.bind_turn(turn: InteractionTurn) -> None`. Subject `{ms_name}.interactionService.ask`.

- [ ] **Step 1: Write the failing test**

```python
import asyncio

from pmai_core.api.interaction.interaction_controller import InteractionController
from pmai_core.api.robotics_ms.robotics_ms_service import RoboticsMsService
from pmai_core.resources.audio.service import AudioService
from pmai_core.settings import Settings


class FakeNats:
    def __init__(self):
        self.calls = []

    def sync_request(self, subject, payload, timeout):
        self.calls.append((subject, payload, timeout))
        if subject.endswith("getActions"):
            return {"total": 1, "data": [{"id": 3, "name": "Negar", "arduino_id": 2, "description": ""}]}
        return {"status": "ok", "response": []}


def test_robotics_client_reads_actions_and_executes():
    service = RoboticsMsService()
    service.nats_handler = FakeNats()
    assert service.get_actions()[0]["id"] == 3
    service.execute_action(3, 2)
    assert service.nats_handler.calls[1][0].endswith("actionService.executeAction")
    assert service.nats_handler.calls[1][1] == {"action_id": 3, "arduino_id": 2}


def test_ask_controller_uses_chat_source():
    seen = {}

    class Turn:
        def ask(self, message: str, source: str) -> str:
            seen["message"] = message
            seen["source"] = source
            return "listo"

    controller = InteractionController(Turn())
    result = asyncio.run(controller.ask({"message": "hola desde la web"}))
    assert result.reply == "listo"
    assert seen == {"message": "hola desde la web", "source": "chat"}


def test_voice_dispatch_schedules_and_returns(monkeypatch):
    scheduled = {}

    def fake_submit(coro, loop):
        scheduled["coro"] = coro
        coro.close()
        return None

    monkeypatch.setattr(asyncio, "run_coroutine_threadsafe", fake_submit)
    settings = Settings()
    audio = AudioService(settings)

    class Turn:
        async def ask_async(self, message: str, source: str) -> str:
            return "voz"

    audio.bind_turn(Turn())
    audio._loop = object()
    audio._dispatch_transcript("esta transcripcion si es larga")
    assert scheduled["coro"] is not None
```

`Settings()` must stay constructible the way `AudioService` already constructs it in this repo. If `Settings()` requires `from_toml()`, the test uses `Settings.from_toml()` with the repo `settings.toml`.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_interaction_wiring.py -v`  
Expected: FAIL because `get_actions`, `InteractionController`, and `bind_turn` do not exist.

- [ ] **Step 3: Wire the edges**

`RoboticsMsService.get_actions` calls `sync_request` on `{ROBOTICS_MS}.actionService.getActions` with payload `{}` and timeout `10.0`. It returns `response.get("data", [])` when `response` is a dict, else `[]`. `execute_action` calls `{ROBOTICS_MS}.actionService.executeAction` with `{"action_id": action_id, "arduino_id": arduino_id}` and timeout `10.0`.

`scene.py` holds `IdentificationService`. `objects()` returns `get_global_objects_for_context()`. `frame(camera_id)` returns the ndarray from `get_last_annotated(camera_id)`, or `None`.

`runtime.py` `prepare_runtime()` runs four independent try/except blocks that log and continue:

1. `utils.milvus.conexion.get_client()`
2. `model_context.model.import_Blip_model()`
3. `import utils.encoder.encoder`
4. `utils.gguf.ggufapi.precargar()`

`interaction_controller.py`:

```python
class AskReply(BaseModel):
    reply: str

class InteractionController:
    def __init__(self, turn) -> None:
        self._turn = turn

    async def ask(self, data: dict) -> AskReply:
        message = str(data.get("message") or "")
        reply = await asyncio.to_thread(self._turn.ask, message, "chat")
        return AskReply(reply=reply)
```

Add the subscriber `f"{ms}.interactionService.ask"` with that controller. `create_subscribers` gains an `interaction_controller` argument.

`AudioService.bind_turn(turn)` stores it. `_dispatch_transcript` always does `asyncio.run_coroutine_threadsafe(self._turn.ask_async(transcript, "voice"), self._loop)` and returns. Add `async def ask_async(self, message, source)` on the turn as `return await asyncio.to_thread(self.ask, message, source)`. Delete the direct `management_ms_service.chat` call and the short-transcript branch; the turn owns the 14-character rule. Keep speaking the short phrase only inside the turn.

`app.py` after NATS connect: `prepare_runtime()`, build `InteractionTurn` with the scene adapter, a caption callable that calls `generate_context_from_base64` using the cached BLIP processor and model, `load_catalog=robotics.get_actions`, `answer=responder`, `speak=robotics.speak`, `execute=robotics.execute_action`. Pass the turn into `create_subscribers` and `audio_service.bind_turn`. The caption callable imports `model_context` inside the function so a missing library becomes the BLIP failure path the turn already catches.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_interaction_wiring.py tests/test_interaction_turn.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd pmai-mai-core
git add src/pmai_core/api/robotics_ms/robotics_ms_service.py src/pmai_core/api/interaction/interaction_controller.py src/pmai_core/pipeline/runtime.py src/pmai_core/pipeline/scene.py src/pmai_core/pipeline/interaction_turn.py src/pmai_core/core/nats/nats_subscribers.py src/pmai_core/resources/audio/service.py src/pmai_core/app.py tests/test_interaction_wiring.py
git commit -m "$(cat <<'EOF'
Connect voice and NATS chat to the interaction turn.

EOF
)"
```

---

### Task 9: Image dependencies, library mounts, and the Milvus volume

**Files:**
- Modify: `pmai-mai-core/Dockerfile.dev`
- Modify: `docker-compose.yml` (`pmai-core` service only)
- Modify: `.env.template` (`PMAI_CORE_PYTHONPATH`)

**Interfaces:**
- Consumes: Tasks 2–8 import names `model_context` and `utils`.
- Produces: container paths `/opt/model-context`, `/opt/action-model`, `/data/milvus`, and `PYTHONPATH=/opt/model-context:/opt/action-model:/app/src`.

- [ ] **Step 1: Write the failing check**

There is no unit test for Compose. The check is a config read:

```bash
python - <<'PY'
from pathlib import Path
text = Path("docker-compose.yml").read_text()
assert "./data/milvus:/data/milvus" in text
assert "./pmai-model-context:/opt/model-context" in text
assert "./pmai-model-vision-language:/opt/action-model" in text
assert "MILVUS_DB_PATH: /data/milvus/androide_milvus.db" in text
env = Path(".env.template").read_text()
assert "PMAI_CORE_PYTHONPATH=/opt/model-context:/opt/action-model:/app/src" in env
print("compose contract ok")
PY
```

Expected before the edit: FAIL, assertions miss those strings.

- [ ] **Step 2: Change the image build context and the service**

`pmai-core.build.context` becomes `.` and `dockerfile` becomes `pmai-mai-core/Dockerfile.dev`.

Dockerfile copies `pmai-mai-core/` to `/app` as it does now (paths gain the `pmai-mai-core/` prefix), then copies the two sibling repos to `/tmp/model-context` and `/tmp/action-model` and runs `pip install /tmp/model-context /tmp/action-model` so dependencies land in site-packages. Add `build-essential` and `cmake` to the apt packages so `llama-cpp-python` can build if no wheel matches. Do not `pip install -e` those two repos: the runtime source comes from the bind mount, ahead of site-packages, via `PYTHONPATH`.

Compose volumes for `pmai-core` add:

```yaml
- ./pmai-model-context:/opt/model-context
- ./pmai-model-vision-language:/opt/action-model
- ./data/milvus:/data/milvus
```

Keep `./data:/data:ro`. List `./data/milvus:/data/milvus` after that parent mount so the Milvus directory stays read-write. Environment adds `MILVUS_DB_PATH: /data/milvus/androide_milvus.db`.

`.env.template`: `PMAI_CORE_PYTHONPATH=/opt/model-context:/opt/action-model:/app/src`.

- [ ] **Step 3: Re-run the check**

Run the Python snippet from Step 1.  
Expected: prints `compose contract ok`.

- [ ] **Step 4: Commit**

```bash
git add pmai-mai-core/Dockerfile.dev docker-compose.yml .env.template
git commit -m "$(cat <<'EOF'
Mount the AI libraries and a writable Milvus Lite directory on mai-core.

EOF
)"
```

`Dockerfile.dev` lives in the mai-core submodule. If `git add pmai-mai-core/Dockerfile.dev` from the launcher only stages a submodule pointer, commit the Dockerfile inside `pmai-mai-core` first, then stage the pointer in the launcher together with `docker-compose.yml` and `.env.template`.

---

### Task 10: Web chat asks mai-core and does not speak

**Files:**
- Modify: `pba-ms-management/src/core/constants/ms-names.constant.ts`
- Modify: `pba-ms-management/src/transports/nats.module.ts`
- Create: `pba-ms-management/src/ms-mai-core-integration/ms-mai-core.service.ts`
- Create: `pba-ms-management/src/ms-mai-core-integration/ms-mai-core.module.ts`
- Modify: `pba-ms-management/src/chat/chat.service.ts`
- Modify: `pba-ms-management/src/chat/chat.module.ts`
- Create: `pba-ms-management/src/chat/chat.service.spec.ts`

**Interfaces:**
- Consumes: `MAI_CORE_MS.interactionService.ask` from Task 8. Response `{ reply: string }`.
- Produces: `MsMaiCoreService.ask(message: string): Promise<{ reply: string }>`. `ChatService.chat` returns that reply and does not call `speak` or `chatStructured`. `declarePoema` is unchanged.

- [ ] **Step 1: Write the failing test**

```typescript
import { ChatService } from './chat.service';

describe('ChatService.chat', () => {
  it('asks mai-core and does not speak or call OpenAI', async () => {
    const openai = { chatStructured: jest.fn() };
    const robotics = { speak: jest.fn() };
    const maiCore = { ask: jest.fn().mockResolvedValue({ reply: 'desde mai-core' }) };
    const service = new ChatService(openai as never, robotics as never, maiCore as never);

    await expect(service.chat({ message: 'Hola R-One' })).resolves.toEqual({
      reply: 'desde mai-core',
    });
    expect(maiCore.ask).toHaveBeenCalledWith('Hola R-One');
    expect(openai.chatStructured).not.toHaveBeenCalled();
    expect(robotics.speak).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run from `pba-ms-management`: `npx jest src/chat/chat.service.spec.ts`  
Expected: FAIL, `ChatService` constructor does not take a third argument.

- [ ] **Step 3: Forward chat to mai-core**

`ms-names.constant.ts`:

```typescript
export const MAI_CORE_NATS = 'MAI_CORE_NATS';
export const MAI_CORE_MS = 'MAI_CORE_MS';
```

In both `ClientsModule.registerAsync` factories inside `nats.module.ts`, add a second client copied from `NATS_SERVICE` with `name: MAI_CORE_NATS` and `timeout: 120000`. Leave the first client's `timeout: 20000`.

`MsMaiCoreService`:

```typescript
@Injectable()
export class MsMaiCoreService {
  constructor(@Inject(MAI_CORE_NATS) private readonly client: ClientProxy) {}

  ask(message: string): Promise<{ reply: string }> {
    return firstValueFrom(
      this.client
        .send<{ reply: string }>(`${MAI_CORE_MS}.interactionService.ask`, { message })
        .pipe(catchError((error) => { throw new RpcException(error); })),
    );
  }
}
```

Its module imports `NatsModule`, provides and exports the service. `ChatModule` imports that module. `ChatService` injects `MsMaiCoreService` as a third constructor dependency. `chat()` logs that it is asking mai-core, returns `this.maiCore.ask(chatStructuredRequestDto.message)`, and does not call OpenAI or `speak`. `declarePoema()` stays as it is.

- [ ] **Step 4: Run test to verify it passes**

Run: `npx jest src/chat/chat.service.spec.ts`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd pba-ms-management
git add src/core/constants/ms-names.constant.ts src/transports/nats.module.ts src/ms-mai-core-integration src/chat/chat.service.ts src/chat/chat.module.ts src/chat/chat.service.spec.ts
git commit -m "$(cat <<'EOF'
Send web chat through the mai-core interaction turn.

EOF
)"
```

---

## Spec coverage

- Turn steps, single-flight, voice vs chat, parallel speak and ordered execute: Task 7 and Task 8.
- Canonical `question` field and JPEG crop: Task 7. Context package already has `question`; Task 2 keeps it importable.
- Vision-language `GlobalObjectForContext` already has `question`, `contexto`, and `image_base64`. No schema edit.
- Description join and empty description: Task 1. Markdown table and removal of ids 1–34: Task 3.
- `responder()` list, catalog filter, Milvus miss skips indexing: Task 4.
- One Gemma instance: Task 5. Collections at startup, temp db test: Task 6. Process startup calls them: Task 8.
- NATS subject, robotics speak and execute, microphone does not block: Task 8.
- Mounts, dependencies, Milvus volume: Task 9.
- Management stops OpenAI and speak on `chat` only: Task 10.
- `declarePoema`, the description screen, Gemma vision, and the chat page: no task.

## Self-review

- Placeholder scan: no TBD, TODO, or "write tests for the above".
- `InteractionTurn.ask(message, source) -> str` is the same in Tasks 7, 8, and 10.
- `responder(obj, secuencias) -> {"respuesta", "movimientos", "fuente", "etiqueta", "backend?"}` matches the spec. Gradio reads `movimientos[0]`.
- Busy and apology strings are copied from the spec in the constraints and in the tests.
