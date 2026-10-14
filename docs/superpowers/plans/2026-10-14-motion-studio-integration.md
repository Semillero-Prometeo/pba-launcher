# Motion Studio Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The motion studio becomes a Compose web service that creates sequences with a description; robotics assigns `id`, stores the canonical file, and exposes those rows through the existing `getActions` / `executeAction` turn contract.

**Architecture:** Studio never talks NATS. Coupled mode POSTs origin JSON (`name`, `description`, 7-tuples) to the gateway. Robotics ingests that payload into `MotionSequenceFile` with a stable integer `id`. `getActions` lists ingested sequences as `Command`s. `executeAction` plays the matching sequence blocks, otherwise writes the number to serial. Angular `/sequences` is an iframe plus the JSON importer.

**Tech Stack:** Python 3.13 (robotics, studio FastAPI), NestJS 11 / class-validator (gateway), Angular 21 / Vitest (web-main), Docker Compose, pytest, Jest.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-14-motion-studio-integration-design.md`.
- Studio origin JSON never includes `id` or `version`. Blocks are 7-tuples `[pca, servo, inicio, dur, pos, vel, nombre]`.
- Canonical file: `{ version, id, name, description, blocks: MotionBlock[] }`. `name` 1–80. `description` 0–280, one line, no Markdown.
- `id` assigned by robotics: empty store → `1`; new name → `max(existing ids) + 1`; deleted ids are not reused; overwrite of the same name keeps `id`.
- Canonical files on disk without `id` stay as-is. They appear in `listSequences`. They do **not** appear in `getActions` until a save/overwrite assigns `id`.
- `getActions` catalog is ingested sequences only, not Arduino firmware commands. Empty store → `[]`.
- `executeAction(action_id, arduino_id)` signature does not change. Sequence `id` match → `start_playback(blocks)`. Else serial write as today.
- `ACTION_DESCRIPTIONS_PATH` is not written. Do not delete it.
- mai-core, the Markdown table, `declarePoema`, and the chat page are not edited.
- Coupled studio does not open `/dev/ttyACM*` or `/dev/ttyUSB*`.
- Commits for service code go inside that submodule. Compose, `.env.template`, `AGENTS.md`, `.cursor/rules`, and this plan commit in the launcher.
- PostMessage auth type: `prometeo-auth` (parent → iframe) and `prometeo-auth-request` (iframe → parent). Token key in Angular stays `prometeo_token`.
- Motion studio HTTP port: `4210` (`MOTION_STUDIO_PORT`).
- Duplicate name without overwrite: robotics error `La secuencia '{name}' ya existe. Use overwrite=true para reemplazar.` (already used). Studio/UI asks, then retries with `overwrite=true`.
- Do not rewrite PyQt files. Compose does not launch PyQt.

---

## File structure

| File | Responsibility |
|---|---|
| `pba-ms-robotics/src/sequence/ingest.py` | Origin vs canonical discrimination, `id` assignment, 7-tuple → `MotionBlock` |
| `pba-ms-robotics/src/sequence/interfaces/sequence_interface.py` | `id`, `description` on file and list row; looser save envelope |
| `pba-ms-robotics/src/sequence/sequence_service.py` | Persist ingest, list with `id`/`description`, `as_commands()`, `find_by_id()` |
| `pba-ms-robotics/src/sequence/sequence_controller.py` | `save_sequence` accepts origin or canonical dict |
| `pba-ms-robotics/src/core/nats/nats_subscribers.py` | Stop validating save with `SaveSequencePayload` that forbids origin |
| `pba-ms-robotics/src/action/action_service.py` | `get_actions` from sequences; `execute_action` plays sequence if `id` matches |
| `pba-ms-gateway/src/robotics-ms/sequence/dto/sequence.dto.ts` | Optional `id`/`description`/`arduino_id`; blocks as origin or objects |
| `pmas-web-motion-studio/src/app.py` | FastAPI static editor |
| `pmas-web-motion-studio/src/static/` | Name, description, blocks, coupled save/play, standalone download |
| `pmas-web-main/src/app/pages/sequences/` | Iframe shell + origin importer |
| `pmas-web-main/src/app/core/constants/motion-studio.ts` | `resolveMotionStudioUrl` |
| `docker-compose.yml`, `.env.template`, `README.md` | Studio service and port 4210 |

---

### Task 1: Robotics ingest (origin → canonical with `id`)

**Files:**
- Create: `pba-ms-robotics/src/sequence/ingest.py`
- Create: `pba-ms-robotics/tests/test_sequence_ingest.py`
- Modify: `pba-ms-robotics/src/sequence/interfaces/sequence_interface.py`
- Modify: `pba-ms-robotics/src/sequence/sequence_service.py`
- Modify: `pba-ms-robotics/src/sequence/sequence_controller.py`
- Modify: `pba-ms-robotics/src/core/nats/nats_subscribers.py`

**Interfaces:**
- Consumes: save envelope `{ "sequence": <origin-or-canonical>, "overwrite": bool }`. Origin sequence: `{ "name": str, "description"?: str, "arduino_id"?: int, "blocks": list[list] }`. Canonical sequence: `{ "version"?: int, "id"?: int, "name": str, "description"?: str, "blocks": list[dict] }`.
- Produces: `ingest_save(payload: dict[str, Any], existing: MotionSequenceFile | None, next_id: int) -> MotionSequenceFile`. `MotionSequenceFile.id: int | None = None`. `MotionSequenceFile.description: str = ""` max 280. `SequenceFileInfo` gains `id: int | None = None` and `description: str = ""`. `SequenceService.__init__(self, data_dir: Path | None = None)`. `save_sequence` writes canonical JSON always with an assigned `id`.

- [ ] **Step 1: Write the failing tests**

Create `pba-ms-robotics/tests/test_sequence_ingest.py`:

```python
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.sequence.ingest import ingest_save, next_sequence_id
from src.sequence.interfaces.sequence_interface import MotionSequenceFile
from src.sequence.sequence_service import SequenceService


ORIGIN = {
    "name": "saludo",
    "description": "Saludo con el brazo derecho",
    "arduino_id": 2,
    "blocks": [[0, 0, 0.0, 2, 0, 1, "P0_S0"]],
}


def test_origin_becomes_canonical_with_id():
    result = ingest_save({"sequence": ORIGIN, "overwrite": False}, existing=None, next_id=1)
    assert result.id == 1
    assert result.version == 1
    assert result.name == "saludo"
    assert result.description == "Saludo con el brazo derecho"
    assert result.blocks[0].arduino_id == 2
    assert result.blocks[0].pca == 0
    assert result.blocks[0].nombre == "P0_S0"


def test_raw_seven_tuple_list_description_empty():
    result = ingest_save(
        {"sequence": {"name": "viejo", "blocks": [[0, 0, 0.0, 2, 0, 1, "P0_S0"]]}, "overwrite": False},
        existing=None,
        next_id=3,
    )
    assert result.id == 3
    assert result.description == ""


def test_overwrite_keeps_id_updates_description():
    existing = ingest_save({"sequence": ORIGIN, "overwrite": False}, existing=None, next_id=4)
    updated = dict(ORIGIN)
    updated["description"] = "Otra frase"
    result = ingest_save(
        {"sequence": updated, "overwrite": True},
        existing=existing,
        next_id=99,
    )
    assert result.id == 4
    assert result.description == "Otra frase"


def test_invalid_payload_rejected():
    with pytest.raises((ValueError, ValidationError)):
        ingest_save({"sequence": {"name": "x", "blocks": "no"}, "overwrite": False}, None, 1)


def test_next_id_skips_deleted_and_starts_at_one():
    assert next_sequence_id([]) == 1
    kept = MotionSequenceFile(
        version=1,
        id=4,
        name="saludo",
        description="",
        blocks=[{"arduino_id": 0, "pca": 0, "servo": 0, "inicio": 0, "dur": 2, "pos": 0, "vel": 1, "nombre": "P0_S0"}],
    )
    assert next_sequence_id([kept]) == 5


def test_save_and_list_roundtrip(tmp_path: Path):
    service = SequenceService(data_dir=tmp_path)
    service.save_sequence({"sequence": ORIGIN, "overwrite": False})
    listed = service.list_sequences()
    assert listed.total == 1
    assert listed.data[0].name == "saludo"
    assert listed.data[0].id == 1
    assert listed.data[0].description == "Saludo con el brazo derecho"
    loaded = service.get_sequence("saludo")
    assert loaded.id == 1
    assert loaded.blocks[0].arduino_id == 2


def test_canonical_without_id_lists_but_file_untouched(tmp_path: Path):
    path = tmp_path / "legado.json"
    path.write_text(
        '{"version": 1, "name": "legado", "blocks": ['
        '{"arduino_id": 0, "pca": 0, "servo": 0, "inicio": 0, "dur": 2, "pos": 0, "vel": 1, "nombre": "P0_S0"}'
        "]}",
        encoding="utf-8",
    )
    service = SequenceService(data_dir=tmp_path)
    listed = service.list_sequences()
    assert listed.data[0].name == "legado"
    assert listed.data[0].id is None
    assert listed.data[0].description == ""
    assert "\"id\"" not in path.read_text(encoding="utf-8")


def test_duplicate_without_overwrite_raises(tmp_path: Path):
    service = SequenceService(data_dir=tmp_path)
    service.save_sequence({"sequence": ORIGIN, "overwrite": False})
    with pytest.raises(ValueError, match="ya existe"):
        service.save_sequence({"sequence": ORIGIN, "overwrite": False})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd pba-ms-robotics && python -m pytest tests/test_sequence_ingest.py -v`

Expected: FAIL with `ModuleNotFoundError: src.sequence.ingest` (or `SequenceService.__init__() got an unexpected keyword argument 'data_dir'`).

- [ ] **Step 3: Implement ingest and persist**

`MotionSequenceFile` and `SequenceFileInfo` in `sequence_interface.py`:

```python
class MotionSequenceFile(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    version: int = Field(default=1, ge=1)
    id: int | None = Field(default=None, ge=1)
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=280)
    blocks: list[MotionBlock]


class SequenceFileInfo(BaseModel):
    name: str
    file_name: str
    id: int | None = None
    description: str = ""


class SaveSequencePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence: dict[str, Any]
    overwrite: bool = False
```

Keep `MotionBlock.legacy_block_compat` as it is. `ingest.py`:

```python
from typing import Any

from src.sequence.interfaces.sequence_interface import MotionBlock, MotionSequenceFile


def next_sequence_id(existing: list[MotionSequenceFile]) -> int:
    ids = [item.id for item in existing if item.id is not None]
    return (max(ids) if ids else 0) + 1


def ingest_save(
    payload: dict[str, Any],
    existing: MotionSequenceFile | None,
    next_id: int,
) -> MotionSequenceFile:
    raw = payload.get("sequence")
    if not isinstance(raw, dict):
        raise ValueError("Formato de secuencia inválido")
    name = str(raw.get("name") or "").strip()
    if not name:
        raise ValueError("Nombre de secuencia inválido")
    description = raw.get("description", "")
    if description is None:
        description = ""
    if not isinstance(description, str):
        raise ValueError("Descripción inválida")
    if "\n" in description:
        raise ValueError("Descripción inválida")
    blocks_raw = raw.get("blocks")
    if not isinstance(blocks_raw, list) or not blocks_raw:
        raise ValueError("Formato de secuencia inválido")
    file_arduino = raw.get("arduino_id", 0)
    if file_arduino is None:
        file_arduino = 0
    blocks: list[MotionBlock] = []
    for item in blocks_raw:
        if isinstance(item, list) and len(item) == 7:
            pca, servo, inicio, dur, pos, vel, nombre = item
            blocks.append(
                MotionBlock(
                    arduino_id=int(file_arduino),
                    pca=pca,
                    servo=servo,
                    inicio=inicio,
                    dur=dur,
                    pos=pos,
                    vel=vel,
                    nombre=nombre,
                )
            )
            continue
        if isinstance(item, dict):
            block = dict(item)
            block.setdefault("arduino_id", file_arduino)
            blocks.append(MotionBlock.model_validate(block))
            continue
        raise ValueError("Formato de secuencia inválido")
    assigned_id = existing.id if existing is not None and existing.id is not None else next_id
    return MotionSequenceFile(
        version=int(raw.get("version") or 1),
        id=assigned_id,
        name=name,
        description=description,
        blocks=blocks,
    )
```

`SequenceService.__init__` takes `data_dir: Path | None = None` and uses `Path(SEQUENCES_DATA_DIR)` when omitted.

`list_sequences` reads each JSON with `_parse_sequence_payload`, fills `SequenceFileInfo(name, file_name, id=parsed.id, description=parsed.description)`. Missing `description` → `""`. Do not write the file back.

`save_sequence(self, payload: dict[str, Any] | MotionSequenceFile, overwrite: bool | None = None)`:
- If the caller still passes a `MotionSequenceFile` (internal), wrap it as `{"sequence": sequence.model_dump(), "overwrite": overwrite or False}`.
- `file_path = self._resolve_sequence_path(name)` from the payload name.
- `existing = self.get_sequence(name)` if the file exists, else `None`.
- If exists and not overwrite: raise the existing Spanish error.
- `all_files = [self.get_sequence(info.name) for info in self.list_sequences().data]` before writing, excluding the name being overwritten when computing `next_id`.
- `next_id = next_sequence_id(all_files)`.
- `canonical = ingest_save(envelope, existing, next_id)`.
- Write `canonical.model_dump_json(indent=2)`. Saved files always include `id`.

`sequence_controller.save_sequence` accepts `dict[str, Any]`, validates only that `sequence` is a dict and `overwrite` is bool (use `SaveSequencePayload` with `sequence: dict[str, Any]`), then `return self.sequence_service.save_sequence(payload.model_dump())`.

`nats_subscribers.py` save handler:

```python
controller=lambda data: sequence_controller.save_sequence(data),
```

Do not `SaveSequencePayload.model_validate` with the old `MotionSequenceFile` strict envelope.

`_parse_sequence_payload` for a dict: `setdefault("name", name)` then `MotionSequenceFile.model_validate`. If an origin file (7-tuple `blocks`) is already in the data dir, parse it without assigning a durable `id` and do not write:

```python
if isinstance(payload, dict) and payload.get("blocks") and isinstance(payload["blocks"][0], list):
    parsed = ingest_save({"sequence": payload, "overwrite": True}, existing=None, next_id=1)
    return parsed.model_copy(update={"id": None})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd pba-ms-robotics && python -m pytest tests/test_sequence_ingest.py -v`

Expected: PASS (8 tests).

- [ ] **Step 5: Commit in `pba-ms-robotics`**

```bash
cd pba-ms-robotics
git add src/sequence/ingest.py src/sequence/interfaces/sequence_interface.py src/sequence/sequence_service.py src/sequence/sequence_controller.py src/core/nats/nats_subscribers.py tests/test_sequence_ingest.py
git commit -m "Ingest studio origin sequences and assign a stable id."
```

---

### Task 2: `getActions` and `executeAction` use ingested sequences

**Files:**
- Create: `pba-ms-robotics/tests/test_action_catalog.py`
- Modify: `pba-ms-robotics/src/sequence/sequence_service.py`
- Modify: `pba-ms-robotics/src/action/action_service.py`

**Interfaces:**
- Consumes: `SequenceService` from Task 1. Canonical files with `id`.
- Produces: `SequenceService.as_commands() -> list[Command]`. `SequenceService.find_by_id(action_id: int) -> MotionSequenceFile | None`. `ActionService.get_actions()` returns only those commands (empty list if none have `id`). `ActionService.execute_action(action_id: int, arduino_id: int)`: if `find_by_id` hits, call `start_playback(sequence.blocks)` and return `ExecuteActionResponse`; else existing serial write.

- [ ] **Step 1: Write the failing tests**

```python
from pathlib import Path
from unittest.mock import MagicMock

from src.action.action_service import ActionService
from src.action.interfaces.command_interface import Command
from src.sequence.interfaces.sequence_interface import SequenceStatusResponse
from src.sequence.sequence_service import SequenceService


ORIGIN = {
    "name": "saludo",
    "description": "Saludo con el brazo derecho",
    "arduino_id": 2,
    "blocks": [[0, 0, 0.0, 2, 0, 1, "P0_S0"]],
}


def test_get_actions_from_sequences_not_firmware(tmp_path: Path):
    sequences = SequenceService(data_dir=tmp_path)
    sequences.save_sequence({"sequence": ORIGIN, "overwrite": False})
    (tmp_path / "legado.json").write_text(
        '{"version": 1, "name": "legado", "blocks": ['
        '{"arduino_id": 0, "pca": 0, "servo": 0, "inicio": 0, "dur": 2, "pos": 0, "vel": 1, "nombre": "P0_S0"}'
        "]}",
        encoding="utf-8",
    )
    service = ActionService(sequence_service=sequences)
    commands = service.get_actions()
    assert commands == [
        Command(id=1, name="saludo", arduino_id=2, description="Saludo con el brazo derecho")
    ]


def test_empty_store_get_actions_empty(tmp_path: Path):
    service = ActionService(sequence_service=SequenceService(data_dir=tmp_path))
    assert service.get_actions() == []


def test_execute_action_plays_sequence(tmp_path: Path):
    sequences = SequenceService(data_dir=tmp_path)
    sequences.save_sequence({"sequence": ORIGIN, "overwrite": False})
    sequences.start_playback = MagicMock(
        return_value=SequenceStatusResponse(status="ok", message="Secuencia en ejecución")
    )
    service = ActionService(sequence_service=sequences)
    result = service.execute_action(action_id=1, arduino_id=9)
    sequences.start_playback.assert_called_once()
    blocks = sequences.start_playback.call_args.args[0]
    assert blocks[0].arduino_id == 2
    assert result.status == "ok"


def test_execute_action_unknown_id_writes_serial(tmp_path: Path):
    sequences = SequenceService(data_dir=tmp_path)
    service = ActionService(sequence_service=sequences)
    service.arduino_utils = MagicMock()
    connection = MagicMock()
    service.arduino_utils.connections = {0: connection}
    service.arduino_utils.json_reader.read_first_meaningful_line.return_value = ["ok"]
    result = service.execute_action(action_id=99, arduino_id=0)
    connection.serial.write.assert_called_once_with(b"99\n")
    assert result.status == "ok"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd pba-ms-robotics && python -m pytest tests/test_action_catalog.py -v`

Expected: FAIL (`ActionService.__init__() got an unexpected keyword argument 'sequence_service'` or `get_actions` still talks to serial / returns `[]` for other reasons).

- [ ] **Step 3: Implement catalog and dual execute**

On `SequenceService`:

```python
def as_commands(self) -> list[Command]:
    from src.action.interfaces.command_interface import Command

    commands: list[Command] = []
    for info in self.list_sequences().data:
        sequence = self.get_sequence(info.name)
        if sequence.id is None or not sequence.blocks:
            continue
        commands.append(
            Command(
                id=sequence.id,
                name=sequence.name,
                arduino_id=sequence.blocks[0].arduino_id,
                description=sequence.description,
            )
        )
    return commands


def find_by_id(self, action_id: int) -> MotionSequenceFile | None:
    for info in self.list_sequences().data:
        sequence = self.get_sequence(info.name)
        if sequence.id == action_id:
            return sequence
    return None
```

`ActionService.__init__(self, sequence_service: SequenceService | None = None)` stores `self.sequence_service = sequence_service or SequenceService()`.

`get_actions`:

```python
def get_actions(self) -> list[Command]:
    commands = self.sequence_service.as_commands()
    if not commands:
        logger.info("Catálogo de movimientos vacío: no hay secuencias con id.")
    return commands
```

Do not call `get_actions_from_arduino` here. Do not apply `ACTION_DESCRIPTIONS_PATH` here.

`execute_action`:

```python
def execute_action(self, action_id: int, arduino_id: int) -> ExecuteActionResponse:
    sequence = self.sequence_service.find_by_id(action_id)
    if sequence is not None:
        status = self.sequence_service.start_playback(sequence.blocks)
        return ExecuteActionResponse(
            status=status.status,
            response=[status.message] if status.message else ["secuencia"],
        )
    # existing serial write using arduino_id, unchanged
```

If `start_playback` raises (no Arduino), let it raise. mai-core already continues after a failed `executeAction`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd pba-ms-robotics && python -m pytest tests/test_action_catalog.py tests/test_sequence_ingest.py -v`

Expected: PASS.

- [ ] **Step 5: Commit in `pba-ms-robotics`**

```bash
cd pba-ms-robotics
git add src/action/action_service.py src/sequence/sequence_service.py tests/test_action_catalog.py
git commit -m "Serve ingested sequences through getActions and executeAction."
```

---

### Task 3: Gateway accepts origin or canonical save bodies

**Files:**
- Create: `pba-ms-gateway/src/robotics-ms/sequence/dto/sequence.dto.spec.ts`
- Modify: `pba-ms-gateway/src/robotics-ms/sequence/dto/sequence.dto.ts`

**Interfaces:**
- Consumes: HTTP `POST /sequence/file` body `{ sequence, overwrite? }` from studio (origin) and from the Angular importer.
- Produces: `MotionSequenceDto` with optional `version`, `id`, `description`, `arduino_id`; required `name`; `blocks: unknown[]` with at least one item. `forbidNonWhitelisted` still passes because those keys are declared. Robotics still validates tuples vs objects.

- [ ] **Step 1: Write the failing tests**

```typescript
import { validateSync } from 'class-validator';
import { plainToInstance } from 'class-transformer';
import { SaveSequenceDto } from './sequence.dto';

function validateBody(body: object) {
  const instance = plainToInstance(SaveSequenceDto, body);
  return validateSync(instance, { whitelist: true, forbidNonWhitelisted: true });
}

describe('SaveSequenceDto', () => {
  it('accepts origin 7-tuples with description', () => {
    const errors = validateBody({
      sequence: {
        name: 'saludo',
        description: 'Saludo con el brazo derecho',
        arduino_id: 0,
        blocks: [[0, 0, 0.0, 2, 0, 1, 'P0_S0']],
      },
      overwrite: false,
    });
    expect(errors).toEqual([]);
  });

  it('accepts canonical blocks with id', () => {
    const errors = validateBody({
      sequence: {
        version: 1,
        id: 4,
        name: 'saludo',
        description: '',
        blocks: [
          {
            arduino_id: 0,
            pca: 0,
            servo: 0,
            inicio: 0,
            dur: 2,
            pos: 0,
            vel: 1,
            nombre: 'P0_S0',
          },
        ],
      },
      overwrite: true,
    });
    expect(errors).toEqual([]);
  });

  it('rejects empty blocks', () => {
    const errors = validateBody({
      sequence: { name: 'x', blocks: [] },
    });
    expect(errors.length).toBeGreaterThan(0);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd pba-ms-gateway && npx jest src/robotics-ms/sequence/dto/sequence.dto.spec.ts --rootDir=.`

Expected: FAIL (`property arduino_id should not exist` and/or nested block validation errors on arrays).

- [ ] **Step 3: Relax `MotionSequenceDto`**

```typescript
import {
  ArrayMinSize,
  IsArray,
  IsBoolean,
  IsInt,
  IsNotEmpty,
  IsNumber,
  IsOptional,
  IsString,
  Max,
  MaxLength,
  Min,
  MinLength,
  ValidateNested,
} from 'class-validator';
import { Type } from 'class-transformer';

export class MotionSequenceDto {
  @IsOptional()
  @IsInt()
  @Min(1)
  version?: number;

  @IsOptional()
  @IsInt()
  @Min(1)
  id?: number;

  @IsString()
  @MinLength(1)
  @MaxLength(80)
  name: string;

  @IsOptional()
  @IsString()
  @MaxLength(280)
  description?: string;

  @IsOptional()
  @IsInt()
  @Min(0)
  arduino_id?: number;

  @IsArray()
  @ArrayMinSize(1)
  blocks: unknown[];
}
```

Keep `MotionBlockDto` for `StartPlaybackDto` (play still sends objects). Do not put `@ValidateNested` / `@Type(() => MotionBlockDto)` on save `blocks`.

`SaveSequenceDto` stays `{ sequence: MotionSequenceDto, overwrite?: boolean }`.

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd pba-ms-gateway && npx jest src/robotics-ms/sequence/dto/sequence.dto.spec.ts --rootDir=.`

Expected: PASS.

- [ ] **Step 5: Commit in `pba-ms-gateway`**

```bash
cd pba-ms-gateway
git add src/robotics-ms/sequence/dto/sequence.dto.ts src/robotics-ms/sequence/dto/sequence.dto.spec.ts
git commit -m "Accept studio origin sequence payloads on POST /sequence/file."
```

---

### Task 4: Motion studio web service (origin editor, coupled or loose)

**Files:**
- Create: `pmas-web-motion-studio/pyproject.toml`
- Create: `pmas-web-motion-studio/src/app.py`
- Create: `pmas-web-motion-studio/src/static/index.html`
- Create: `pmas-web-motion-studio/src/static/editor.js`
- Create: `pmas-web-motion-studio/src/static/editor.css`
- Create: `pmas-web-motion-studio/tests/test_app.py`
- Create: `pmas-web-motion-studio/Dockerfile.dev`
- Do not delete or rewrite `interfaz_record9_5_1.py`, `editor_servo3.py`, `motion_control.py`.

**Interfaces:**
- Consumes: `postMessage` `{ type: "prometeo-auth", token: string, gatewayUrl: string }` from the Angular parent. Optional retry via `{ type: "prometeo-auth-request" }` to `window.parent`.
- Produces: HTTP `GET /` editor. Origin object `{ name, description, arduino_id, blocks: number/string 7-tuples }`. Coupled: `POST ${gatewayUrl}/sequence/file` with `Authorization: Bearer ${token}` and `{ sequence: origin, overwrite }`. Coupled play: convert tuples to objects with `arduino_id`, `POST ${gatewayUrl}/sequence/play`. Loose: download origin JSON; no gateway calls. Token kept in a JS variable, never `localStorage`.

- [ ] **Step 1: Write the failing app test**

```python
from fastapi.testclient import TestClient

from src.app import app


def test_index_serves_editor():
    response = TestClient(app).get("/")
    assert response.status_code == 200
    text = response.text.lower()
    assert "description" in text or "descripcion" in text or "descripción" in text
    assert "nombre" in text
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd pmas-web-motion-studio && python -m pytest tests/test_app.py -v`

Expected: FAIL (`No module named src.app`).

- [ ] **Step 3: Implement FastAPI + editor**

`pyproject.toml`: package `pmas-web-motion-studio`, requires-python `>=3.13`, deps `fastapi`, `uvicorn`, `python-multipart`; optional-dev `pytest`, `httpx`. pytest `testpaths = ["tests"]`.

`src/app.py`:

```python
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

STATIC_DIR = Path(__file__).resolve().parent / "static"
app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
```

`index.html` fields: `name` (required), `description` (textarea, maxlength 280), `arduino_id` (number, default 0), a table of blocks with columns pca, servo, inicio, dur, pos, vel, nombre, add-row button. Buttons: Guardar, Descargar JSON, Previsualizar. Status line `#status`. Banner `#mode` (“Acoplado” / “Suelto: no hay sesión”). Script `/static/editor.js`.

`editor.js` (required behavior, keep it in one file):

```javascript
const POST_AUTH = "prometeo-auth";
const POST_AUTH_REQUEST = "prometeo-auth-request";
let token = null;
let gatewayUrl = null;

function isTrustedParent(event) {
  try {
    return new URL(event.origin).hostname === window.location.hostname;
  } catch {
    return false;
  }
}

window.addEventListener("message", (event) => {
  if (!isTrustedParent(event)) return;
  const data = event.data || {};
  if (data.type !== POST_AUTH) return;
  if (typeof data.token !== "string" || !data.token) return;
  if (typeof data.gatewayUrl !== "string" || !data.gatewayUrl) return;
  token = data.token;
  gatewayUrl = data.gatewayUrl.replace(/\/$/, "");
  document.getElementById("mode").textContent = "Acoplado";
});

function buildOrigin() {
  const name = document.getElementById("name").value.trim();
  const description = document.getElementById("description").value.replace(/\n/g, " ").slice(0, 280);
  const arduino_id = Number(document.getElementById("arduino_id").value || 0);
  const blocks = [...document.querySelectorAll("tbody tr")].map((row) => {
    const v = (cls) => row.querySelector(cls).value;
    return [
      Number(v(".pca")),
      Number(v(".servo")),
      Number(v(".inicio")),
      Number(v(".dur")),
      Number(v(".pos")),
      Number(v(".vel")),
      String(v(".nombre")),
    ];
  });
  return { name, description, arduino_id, blocks };
}

async function saveCoupled(overwrite) {
  const sequence = buildOrigin();
  const response = await fetch(`${gatewayUrl}/sequence/file`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ sequence, overwrite: Boolean(overwrite) }),
  });
  if (response.status === 401 || response.status === 403) {
    token = null;
    document.getElementById("mode").textContent = "Suelto: no hay sesión";
    window.parent.postMessage({ type: POST_AUTH_REQUEST }, "*");
    throw new Error("Sesión vencida");
  }
  if (!response.ok) {
    const text = await response.text();
    if (!overwrite && /ya existe/i.test(text)) {
      if (confirm("La secuencia ya existe. ¿Sobrescribir?")) {
        return saveCoupled(true);
      }
      return;
    }
    throw new Error("No se pudo guardar");
  }
}

document.getElementById("save").onclick = async () => {
  const sequence = buildOrigin();
  if (!sequence.name || !sequence.blocks.length) {
    document.getElementById("status").textContent = "Define nombre y bloques";
    return;
  }
  try {
    if (token && gatewayUrl) {
      await saveCoupled(false);
      document.getElementById("status").textContent = "Secuencia guardada";
      return;
    }
    const blob = new Blob([JSON.stringify(sequence, null, 2)], { type: "application/json" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `${sequence.name}.json`;
    link.click();
    document.getElementById("status").textContent = "JSON descargado (suelto)";
  } catch (error) {
    document.getElementById("status").textContent = error.message || "No se pudo guardar";
  }
};
```

Previsualizar: if not coupled, set status `Suelto: no hay sesión` and return. If coupled, `POST ${gatewayUrl}/sequence/play` with `{ blocks: origin.blocks.map(t => ({ arduino_id: origin.arduino_id, pca: t[0], servo: t[1], inicio: t[2], dur: t[3], pos: t[4], vel: t[5], nombre: t[6] })) }`. Do not open serial ports in Python.

`Dockerfile.dev`:

```dockerfile
FROM python:3.13-slim
WORKDIR /usr/src/app
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir -e ".[dev]"
EXPOSE 4210
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "4210", "--reload"]
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd pmas-web-motion-studio && python -m pytest tests/test_app.py -v`

Expected: PASS.

- [ ] **Step 5: Commit in `pmas-web-motion-studio`**

```bash
cd pmas-web-motion-studio
git add pyproject.toml src/app.py src/static tests/test_app.py Dockerfile.dev
git commit -m "Serve a web sequence editor that saves origin JSON or posts to the gateway."
```

---

### Task 5: Angular `/sequences` iframe, JWT, origin import

**Files:**
- Create: `pmas-web-main/src/app/core/constants/motion-studio.ts`
- Create: `pmas-web-main/src/app/core/constants/motion-studio.spec.ts`
- Create: `pmas-web-main/src/app/pages/sequences/origin-sequence.ts`
- Create: `pmas-web-main/src/app/pages/sequences/origin-sequence.spec.ts`
- Modify: `pmas-web-main/src/app/pages/sequences/sequences.ts`
- Modify: `pmas-web-main/src/app/pages/sequences/sequences.html`
- Modify: `pmas-web-main/src/app/pages/control-panel/control-panel.ts`
- Modify: `pmas-web-main/src/app/pages/control-panel/control-panel.html`

**Interfaces:**
- Consumes: `AuthService.token()`, `GATEWAY_URL`, Task 3 save body, Task 4 iframe origin.
- Produces: `MOTION_STUDIO_PORT = 4210`. `resolveMotionStudioUrl(hostname: string, port: number = MOTION_STUDIO_PORT): string` → `http://${hostname}:${port}`. `parseOriginText(raw: string, fileBaseName: string, defaultArduinoId: number | null): { name: string; description: string; blocks: number[][]; error: string | null }`. Parent `postMessage` to iframe `{ type: 'prometeo-auth', token, gatewayUrl: GATEWAY_URL }`. On `prometeo-auth-request` from iframe (same hostname), send again. Import POSTs origin `{ name, description, arduino_id, blocks: 7-tuples }` to `/sequence/file`. Control panel `SequenceFile` includes `description` and `id`; search matches description; label shows description under the name when non-empty.

- [ ] **Step 1: Write the failing tests**

`motion-studio.spec.ts` (copy the `gateway.spec.ts` style):

```typescript
import { describe, expect, it } from 'vitest';
import { resolveMotionStudioUrl, MOTION_STUDIO_PORT } from './motion-studio';

describe('resolveMotionStudioUrl', () => {
  it('builds http URL from hostname and default port', () => {
    expect(resolveMotionStudioUrl('10.211.14.115')).toBe('http://10.211.14.115:4210');
  });

  it('uses MOTION_STUDIO_PORT by default', () => {
    expect(MOTION_STUDIO_PORT).toBe(4210);
  });
});
```

`origin-sequence.spec.ts`:

```typescript
import { describe, expect, it } from 'vitest';
import { parseOriginText } from './origin-sequence';

describe('parseOriginText', () => {
  it('reads origin wrapper', () => {
    const parsed = parseOriginText(
      JSON.stringify({
        name: 'saludo',
        description: 'Saludo con el brazo derecho',
        blocks: [[0, 0, 0.0, 2, 0, 1, 'P0_S0']],
      }),
      'archivo',
      1,
    );
    expect(parsed.error).toBeNull();
    expect(parsed.name).toBe('saludo');
    expect(parsed.description).toBe('Saludo con el brazo derecho');
    expect(parsed.blocks).toEqual([[0, 0, 0.0, 2, 0, 1, 'P0_S0']]);
  });

  it('reads raw 7-tuple list with empty description', () => {
    const parsed = parseOriginText(
      JSON.stringify([[0, 0, 0.0, 2, 0, 1, 'P0_S0']]),
      'viejo',
      0,
    );
    expect(parsed.error).toBeNull();
    expect(parsed.name).toBe('viejo');
    expect(parsed.description).toBe('');
  });

  it('rejects neither-list-nor-origin', () => {
    const parsed = parseOriginText('{"foo": 1}', 'x', 0);
    expect(parsed.error).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd pmas-web-main && npx ng test --include=src/app/core/constants/motion-studio.spec.ts --include=src/app/pages/sequences/origin-sequence.spec.ts --watch=false`

If `ng test --include` is unsupported in this CLI, run `npx ng test --watch=false` and expect FAIL on missing modules. Expected: FAIL (`Cannot find module './motion-studio'`).

- [ ] **Step 3: Implement constants, parser, iframe shell, control-panel description**

`motion-studio.ts`:

```typescript
export const MOTION_STUDIO_PORT = 4210;

export function resolveMotionStudioUrl(hostname: string, port: number = MOTION_STUDIO_PORT): string {
  return `http://${hostname}:${port}`;
}
```

Export `MOTION_STUDIO_URL` the same way `GATEWAY_URL` uses the page hostname.

`parseOriginText`: if parsed is an array, require every row length >= 7, return `{ name: fileBaseName, description: '', blocks }`. If parsed is an object with `blocks` array of 7-tuples, use `name || fileBaseName`, `description || ''`. Otherwise `{ error: 'El archivo no contiene una lista de movimientos', name: fileBaseName, description: '', blocks: [] }`.

Replace `sequences.html` with: title «Creación de Secuencias», short subtitle that the studio is the editor, button «Importar JSON», status line, iframe `#studioFrame` with `[src]="studioSrc"` (bypassSecurityTrustResourceUrl), `(load)="onStudioLoad()"`, `(error)="onStudioError()"`. On error, text exact: `El estudio de movimiento no está disponible.` Do not show the old timeline, Arduino scan, or play/stop (those stay on the control panel). Keep the import modal; wire file input to `parseOriginText`.

`sequences.ts`: inject `AuthService`, `DomSanitizer`. `studioSrc` from `MOTION_STUDIO_URL`. `onStudioLoad`:

```typescript
const frame = this.studioFrame()?.nativeElement as HTMLIFrameElement | undefined;
const token = this.auth.token();
if (!frame?.contentWindow || !token) return;
frame.contentWindow.postMessage(
  { type: 'prometeo-auth', token, gatewayUrl: GATEWAY_URL },
  MOTION_STUDIO_URL,
);
```

`@HostListener('window:message', ['$event'])` if `event.data?.type === 'prometeo-auth-request'` and `new URL(event.origin).hostname === window.location.hostname`, call the same postMessage.

Importer: valid rows still require `arduino_id !== null`. POST:

```typescript
{
  sequence: {
    name: item.targetName.trim(),
    description: item.description,
    arduino_id: item.arduino_id,
    blocks: item.tupleBlocks,
  },
  overwrite: true,
}
```

Do not convert tuples to objects in Angular for this POST.

Control panel: extend `SequenceFile` with `id: number | null` and `description: string`. In `filteredSequenceGroups`, also match `description`. In the sequence button, under `displaySequenceName(name)`, if description is non-empty show it as `text-[10px] text-outline`. Load description from `listSequences` when present so the extra GET-per-file is not required for the text; keep existing GETs if grouping still needs blocks.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd pmas-web-main && npx ng test --watch=false`

Expected: PASS, including the new specs. Existing `gateway.spec.ts` still passes.

- [ ] **Step 5: Commit in `pmas-web-main`**

```bash
cd pmas-web-main
git add src/app/core/constants/motion-studio.ts src/app/core/constants/motion-studio.spec.ts src/app/pages/sequences src/app/pages/control-panel
git commit -m "Embed the motion studio and import origin JSON with descriptions."
```

---

### Task 6: Compose, env, agent docs

**Files:**
- Modify: `docker-compose.yml`
- Modify: `.env.template`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `.cursor/rules/robotics-actions.mdc`

**Interfaces:**
- Consumes: Task 4 `Dockerfile.dev` and uvicorn on 4210.
- Produces: Compose service `pmas-web-motion-studio`. Host port `${MOTION_STUDIO_PORT}`. Angular does not need a Docker env for the iframe URL (it uses the page hostname, like the gateway). Docs state sequences-with-id are the turn catalog.

- [ ] **Step 1: Add the Compose service and port**

In `.env.template` after `WEB_MAIN_PORT=4200`:

```
# PMAS WEB MOTION STUDIO
MOTION_STUDIO_PORT=4210
```

In `docker-compose.yml`, after `pmas-web-main`:

```yaml
  pmas-web-motion-studio:
    build:
      context: ./pmas-web-motion-studio
      dockerfile: Dockerfile.dev
    ports:
      - "${MOTION_STUDIO_PORT}:${MOTION_STUDIO_PORT}"
    volumes:
      - ./pmas-web-motion-studio:/usr/src/app
    command: uvicorn src.app:app --host 0.0.0.0 --port ${MOTION_STUDIO_PORT} --reload --reload-dir /usr/src/app
    environment:
      - PORT=${MOTION_STUDIO_PORT}
```

No NATS. No privileged. No serial devices.

- [ ] **Step 2: Update README, AGENTS.md, robotics rule**

README: document `MOTION_STUDIO_PORT=4210`, `sudo ufw allow 4210/tcp`, and that `/sequences` loads that origin in an iframe. Replace the sentence that says descriptions come only from `ACTION_DESCRIPTIONS_PATH` with: the turn catalog is ingested sequences (`id`, name, description); `ACTION_DESCRIPTIONS_PATH` remains unused for those phrases.

`AGENTS.md` table: `pmas-web-motion-studio` | Editor web de secuencias (origen + descripción); Compose lo levanta; Angular lo incrusta. Remove “`pmas-web-motion-studio` no forman parte del turno” — keep `pba-arduino-codes` out of the turn. Step 3 of the turn: `getActions` lists ingested sequences; empty store → speak and do not move; no Arduino is not the reason the catalog is empty.

`.cursor/rules/robotics-actions.mdc` replace the body with:

```markdown
# Acciones del cuerpo

`get_actions` arma el catálogo con las secuencias canónicas que ya tienen `id`. Cada fila es `Command(id, name, arduino_id, description)` donde `arduino_id` es el del primer bloque. Sin secuencias con `id`, la lista es vacía. No rellenes con gestos de ejemplo ni con el firmware Arduino.

`execute_action` recibe `action_id` y `arduino_id`. Si hay una secuencia con ese `id`, reproduce sus bloques. Si no, escribe ese número al serial de ese Arduino.

La descripción vive en el archivo de la secuencia. No escribas `ACTION_DESCRIPTIONS_PATH` para estas frases.
```

- [ ] **Step 3: Sanity-check Compose config**

Run: `docker compose config`

Expected: YAML valid; service `pmas-web-motion-studio` present; published port 4210.

- [ ] **Step 4: Commit in the launcher**

```bash
git add docker-compose.yml .env.template README.md AGENTS.md .cursor/rules/robotics-actions.mdc
git commit -m "Launch the motion studio web service on port 4210."
```

Do not stage unrelated `.gitmodules` or submodule pointer changes.

---

## Self-review vs spec

| Spec requirement | Task |
|---|---|
| Studio is its own web service, iframe in `/sequences` | 4, 5, 6 |
| Origin = 7-tuples + name + description, no id | 1, 4 |
| Robotics assigns id, overwrite keeps id, no reuse | 1 |
| Canonical files without id list but skip `getActions` | 1, 2 |
| `listSequences` includes id + description | 1 |
| `getActions` from sequences; table unchanged | 2 |
| `executeAction` plays sequence or serial | 2 |
| Gateway origin POST | 3 |
| JWT postMessage, loose download, coupled play via gateway | 4, 5 |
| Import origin + raw 7-tuples | 5 |
| Control panel shows description | 5 |
| No live panel sync, no PyQt delete, no mai-core contract change | constraints |
| Compose + MOTION_STUDIO_URL/port | 6 |
| `ACTION_DESCRIPTIONS_PATH` not used for these phrases | 2, 6 |
