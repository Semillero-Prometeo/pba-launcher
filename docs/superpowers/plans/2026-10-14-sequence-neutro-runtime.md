# Gesture–neutro pair, categories, and hardware queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Each studio sequence is a gesture plus an editable rest track and one body category; robotics queues turn playback as normal → 1 s → neutro → 1 s; the control panel groups by category, offers Normal/Neutro, and shows live hardware state.

**Architecture:** One JSON file, two tracks (`blocks`, `blocks_neutro`). Studio writes origin (no `id`). Robotics ingest assigns `id` and only lists complete pairs in `getActions`. A single `PlaybackQueue` in robotics owns the serial: turn `executeAction` enqueues four steps and returns immediately; panel/studio play enqueues one phase and errors if busy. The panel polls `GET /sequence/runtime`. mai-core is not edited.

**Tech Stack:** Python 3.13 (robotics, studio FastAPI, pytest), NestJS 11 / class-validator / Jest (gateway), Angular 21 / Vitest (web-main).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-14-sequence-neutro-runtime-design.md`. Integration spec `2026-10-14-motion-studio-integration-design.md` still applies for iframe, JWT, `id` assignment, and origin-without-id.
- Categories (exactly one, required on save): `cara` | `cuello` | `brazo_derecho` | `brazo_izquierdo` | `torso` | `cadera`. Panel labels in that order: Cara, Cuello, Brazo derecho, Brazo izquierdo, Torso, Cadera.
- Origin JSON never includes `id` or `version`. Canonical adds `version` and `id`. Overwrite of the same `name` keeps `id`.
- `getActions` / `executeAction(action_id, arduino_id)` signatures do not change. Markdown catalog table, `declarePoema`, chat page, and mai-core are not edited.
- `WAIT_SECONDS = 1.0`. Gap after every turn phase, including after the last neutro of a pair.
- `executeAction` of a complete pair enqueues `normal`, `espera`, `neutro`, `espera` with `source=turno` and **returns as soon as those four steps are queued**. Never reject because busy.
- Panel/studio `POST /sequence/play` with `busy` raises `ValueError("Ya existe una secuencia en ejecución")`. Queue unchanged. One phase, no trailing wait.
- Incomplete sequence (has `id` but missing `category` or empty `blocks_neutro`): `executeAction` omits (`status="ok"`, `response=["omitido"]`), no serial. Unknown id: serial write as today.
- Legacy files without pair stay on disk and in `listSequences`. They do not appear in `getActions` or the control-panel execution list. Do not rewrite them.
- `POST /sequence/stop` cuts the current phase, cancels wait, clears the queue. No extra neutro. Idle stop is ok.
- Arduino missing when **firing** a step: log, discard that step, continue the queue (including a following wait).
- Coupled studio does not open `/dev/ttyACM*` or `/dev/ttyUSB*`. Play-on-disk only moves the playhead.
- Chain API (`chain/start`, `chain/stop`, `chain/status`) stays. The control panel stops using it.
- Commits for service code go inside that submodule. This plan, `AGENTS.md`, and `.cursor/rules` commit in the launcher.
- Do not relaunch PyQt. Do not persist the queue. Do not assign `id` in the studio.

---

## File structure

| File | Responsibility |
|---|---|
| `pba-ms-robotics/src/sequence/ingest.py` | `CATEGORIES`, `blocks_from_raw`, `is_complete_pair`, ingest requires both tracks + category |
| `pba-ms-robotics/src/sequence/interfaces/sequence_interface.py` | `category`, `blocks_neutro` on file; play payload `mode`/`name`/`source`; runtime models |
| `pba-ms-robotics/src/sequence/playback_queue.py` | Step list, 1 s waits, worker thread, snapshot, stop |
| `pba-ms-robotics/src/sequence/sequence_service.py` | Persist pair, filter catalog, enqueue turn, user play, `get_runtime` |
| `pba-ms-robotics/src/action/action_service.py` | `execute_action` enqueues pair or omits or serial |
| `pba-ms-robotics/src/sequence/sequence_controller.py` | Play payload + `get_runtime` |
| `pba-ms-robotics/src/core/nats/nats_subscribers.py` | `getRuntime` subject |
| `pba-ms-gateway/src/robotics-ms/sequence/dto/sequence.dto.ts` | `category`, `blocks_neutro`, play `mode`/`name`/`source` |
| `pba-ms-gateway/src/robotics-ms/sequence/sequence.controller.ts` | `GET /sequence/runtime` |
| `pmas-web-motion-studio/src/neutro.py` | Pure `generate_neutro` |
| `pmas-web-motion-studio/src/local_sequences.py` | Origin on disk includes category + both tracks |
| `pmas-web-motion-studio/src/static/` | Category, track switch, generate neutro, save/play active track |
| `pmas-web-main/src/app/pages/sequences/origin-sequence.ts` | Import rejects rows without pair |
| `pmas-web-main/src/app/pages/control-panel/` | Six sections, Normal/Neutro, En hardware, poll |

---

### Task 1: Robotics ingest of category + both tracks

**Files:**
- Modify: `pba-ms-robotics/src/sequence/ingest.py`
- Modify: `pba-ms-robotics/src/sequence/interfaces/sequence_interface.py`
- Modify: `pba-ms-robotics/src/sequence/sequence_service.py`
- Modify: `pba-ms-robotics/tests/test_sequence_ingest.py`
- Modify: `pba-ms-robotics/tests/test_action_catalog.py`

**Interfaces:**
- Consumes: save envelope `{ "sequence": origin-or-canonical, "overwrite": bool }`. Origin now requires `category` and nonempty `blocks_neutro`.
- Produces: `CATEGORIES: tuple[str, ...]`. `blocks_from_raw(blocks_raw: object, file_arduino: int) -> list[MotionBlock]`. `is_complete_pair(sequence: MotionSequenceFile) -> bool`. `ingest_save(...) -> MotionSequenceFile` with `category: str` and `blocks_neutro: list[MotionBlock]`. `MotionSequenceFile.category: str | None = None`. `MotionSequenceFile.blocks_neutro: list[MotionBlock] = []`. `SequenceFileInfo.category: str | None = None`. `as_commands()` skips unless `id is not None` and `is_complete_pair`. `_parse_sequence_payload` stays lenient (legacy without pair still loads).

- [ ] **Step 1: Write the failing tests**

Replace `ORIGIN` in `pba-ms-robotics/tests/test_sequence_ingest.py` with a complete pair and add these tests (keep the existing id / overwrite / invalid-payload tests, updating them to use the pair):

```python
CATEGORIES = (
    "cara",
    "cuello",
    "brazo_derecho",
    "brazo_izquierdo",
    "torso",
    "cadera",
)

ORIGIN = {
    "name": "saludo",
    "description": "Saludo con el brazo derecho",
    "category": "brazo_derecho",
    "arduino_id": 2,
    "blocks": [[0, 0, 0.0, 2, 850, 5, "P0_S0"]],
    "blocks_neutro": [[0, 0, 0.0, 2, 500, 5, "P0_S0"]],
}


def test_origin_pair_becomes_canonical():
    from src.sequence.ingest import ingest_save

    result = ingest_save({"sequence": ORIGIN, "overwrite": False}, existing=None, next_id=1)
    assert result.id == 1
    assert result.category == "brazo_derecho"
    assert result.blocks[0].pos == 850
    assert result.blocks_neutro[0].pos == 500
    assert result.blocks_neutro[0].arduino_id == 2


def test_ingest_rejects_missing_category():
    from src.sequence.ingest import ingest_save

    raw = dict(ORIGIN)
    raw.pop("category")
    with pytest.raises(ValueError, match="Categoría inválida"):
        ingest_save({"sequence": raw, "overwrite": False}, None, 1)


def test_ingest_rejects_empty_neutro():
    from src.sequence.ingest import ingest_save

    raw = dict(ORIGIN)
    raw["blocks_neutro"] = []
    with pytest.raises(ValueError, match="Falta la pista neutra"):
        ingest_save({"sequence": raw, "overwrite": False}, None, 1)


def test_legacy_file_lists_but_not_in_catalog(tmp_path: Path):
    path = tmp_path / "legado.json"
    path.write_text(
        '{"version": 1, "id": 7, "name": "legado", "blocks": ['
        '{"arduino_id": 0, "pca": 0, "servo": 0, "inicio": 0, "dur": 2, "pos": 0, "vel": 1, "nombre": "P0_S0"}'
        "]}",
        encoding="utf-8",
    )
    service = SequenceService(data_dir=tmp_path)
    listed = service.list_sequences()
    assert listed.data[0].id == 7
    assert listed.data[0].category is None
    assert '"category"' not in path.read_text(encoding="utf-8")
    from src.action.action_service import ActionService

    assert ActionService(sequence_service=service).get_actions() == []
```

In `pba-ms-robotics/tests/test_action_catalog.py`, use the same `ORIGIN` pair. `test_get_actions_from_sequences_not_firmware` must still return one `Command` for `saludo` and ignore `legado.json`. `test_execute_action_plays_sequence` will be rewritten in Task 2; for this task keep it compiling by leaving the `start_playback` mock (it will change next).

Also assert `listed.data[0].category == "brazo_derecho"` in `test_save_and_list_roundtrip`.

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd pba-ms-robotics && python -m pytest tests/test_sequence_ingest.py tests/test_action_catalog.py -v
```

Expected: FAIL — `MotionSequenceFile` has no `category` / `blocks_neutro`; ingest does not raise `Categoría inválida`.

- [ ] **Step 3: Implement ingest and models**

In `sequence_interface.py`, extend `MotionSequenceFile` and `SequenceFileInfo`:

```python
category: str | None = Field(default=None)
blocks_neutro: list[MotionBlock] = Field(default_factory=list)
```

```python
class SequenceFileInfo(BaseModel):
    name: str
    file_name: str
    id: int | None = None
    description: str = ""
    category: str | None = None
```

Replace `pba-ms-robotics/src/sequence/ingest.py` with:

```python
from typing import Any

from src.sequence.interfaces.sequence_interface import MotionBlock, MotionSequenceFile

CATEGORIES = (
    "cara",
    "cuello",
    "brazo_derecho",
    "brazo_izquierdo",
    "torso",
    "cadera",
)


def next_sequence_id(existing: list[MotionSequenceFile]) -> int:
    ids = [item.id for item in existing if item.id is not None]
    return (max(ids) if ids else 0) + 1


def blocks_from_raw(blocks_raw: object, file_arduino: int) -> list[MotionBlock]:
    if not isinstance(blocks_raw, list) or not blocks_raw:
        raise ValueError("Formato de secuencia inválido")
    blocks: list[MotionBlock] = []
    for item in blocks_raw:
        if isinstance(item, list) and len(item) == 7:
            pca, servo, inicio, dur, pos, vel, nombre = item
            blocks.append(
                MotionBlock(
                    arduino_id=int(file_arduino),
                    pca=int(pca),
                    servo=int(servo),
                    inicio=float(inicio),
                    dur=float(dur),
                    pos=int(pos),
                    vel=int(vel),
                    nombre=str(nombre),
                )
            )
            continue
        if isinstance(item, dict):
            block = dict(item)
            block.setdefault("arduino_id", file_arduino)
            blocks.append(MotionBlock.model_validate(block))
            continue
        raise ValueError("Formato de secuencia inválido")
    return blocks


def is_complete_pair(sequence: MotionSequenceFile) -> bool:
    return (
        sequence.category in CATEGORIES
        and bool(sequence.blocks)
        and bool(sequence.blocks_neutro)
    )


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
    if not isinstance(description, str) or "\n" in description:
        raise ValueError("Descripción inválida")
    category = raw.get("category")
    if category not in CATEGORIES:
        raise ValueError("Categoría inválida")
    file_arduino = raw.get("arduino_id", 0)
    if file_arduino is None:
        file_arduino = 0
    blocks = blocks_from_raw(raw.get("blocks"), int(file_arduino))
    try:
        blocks_neutro = blocks_from_raw(raw.get("blocks_neutro"), int(file_arduino))
    except ValueError as exc:
        raise ValueError("Falta la pista neutra") from exc
    assigned_id = existing.id if existing is not None and existing.id is not None else next_id
    return MotionSequenceFile(
        version=int(raw.get("version") or 1),
        id=assigned_id,
        name=name,
        description=description,
        category=category,
        blocks=blocks,
        blocks_neutro=blocks_neutro,
    )
```

In `sequence_service.py`:

- `list_sequences` copies `category=parsed.category`.
- `as_commands` uses `if sequence.id is None or not is_complete_pair(sequence): continue`.
- `_parse_sequence_payload` for a raw list uses `blocks_from_raw` and returns `MotionSequenceFile(name=name, blocks=..., id=None)` — **do not** call `ingest_save` (that would demand a pair). For a dict whose `blocks[0]` is a list, convert both tracks with `blocks_from_raw` if present, set `id=None` unless the dict already has `id`, and leave `category` as `raw.get("category")` if it is in `CATEGORIES` else `None`. For object-block dicts, `MotionSequenceFile.model_validate` as today (missing category/neutro is valid for reads).

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd pba-ms-robotics && python -m pytest tests/test_sequence_ingest.py tests/test_action_catalog.py -v
```

Expected: PASS (except leave `test_execute_action_plays_sequence` passing with the existing `start_playback` mock).

- [ ] **Step 5: Commit**

```bash
cd pba-ms-robotics
git add src/sequence/ingest.py src/sequence/interfaces/sequence_interface.py src/sequence/sequence_service.py tests/test_sequence_ingest.py tests/test_action_catalog.py
git commit -m "Require a category and rest track when ingesting a sequence."
```

---

### Task 2: Robotics playback queue, runtime, and executeAction

**Files:**
- Create: `pba-ms-robotics/src/sequence/playback_queue.py`
- Create: `pba-ms-robotics/tests/test_playback_queue.py`
- Modify: `pba-ms-robotics/src/sequence/interfaces/sequence_interface.py`
- Modify: `pba-ms-robotics/src/sequence/sequence_service.py`
- Modify: `pba-ms-robotics/src/sequence/sequence_controller.py`
- Modify: `pba-ms-robotics/src/core/nats/nats_subscribers.py`
- Modify: `pba-ms-robotics/src/action/action_service.py`
- Modify: `pba-ms-robotics/tests/test_action_catalog.py`

**Interfaces:**
- Consumes: `MotionSequenceFile` complete pairs; `SequencePlaybackPayload(mode, source, name, blocks)`.
- Produces: `WAIT_SECONDS = 1.0`. `QueueStep(id: int | None, name: str, mode: Literal["normal","neutro","espera"], source: Literal["turno","panel","estudio"], blocks: list[MotionBlock] | None = None)`. `RuntimeSnapshot(busy: bool, source: str | None, current: QueueStepPublic | None, queue: list[QueueStepPublic])` where public steps omit `blocks`. `PlaybackQueue.enqueue(steps, reject_if_busy: bool) -> None`. `SequenceService.enqueue_turn_pair(sequence) -> SequenceStatusResponse`. `SequenceService.start_user_playback(payload) -> SequenceStatusResponse`. `SequenceService.get_runtime() -> RuntimeSnapshot`. `SequenceService.stop_playback()` also stops the queue. `ActionService.execute_action` calls `enqueue_turn_pair` or returns omit or serial.

- [ ] **Step 1: Write the failing tests**

Create `pba-ms-robotics/tests/test_playback_queue.py`:

```python
import os
import time
from pathlib import Path
from unittest.mock import MagicMock

os.environ.setdefault("NATS_SERVER", "nats://localhost:4222")

import pytest

from src.action.action_service import ActionService
from src.sequence.interfaces.sequence_interface import SequencePlaybackPayload, SequenceStatusResponse
from src.sequence.playback_queue import WAIT_SECONDS
from src.sequence.sequence_service import SequenceService

ORIGIN = {
    "name": "saludo",
    "description": "Saludo con el brazo derecho",
    "category": "brazo_derecho",
    "arduino_id": 0,
    "blocks": [[0, 0, 0.0, 2, 850, 5, "P0_S0"]],
    "blocks_neutro": [[0, 0, 0.0, 2, 500, 5, "P0_S0"]],
}

ORIGIN_TWO = {
    **ORIGIN,
    "name": "adios",
    "description": "Despedida",
    "blocks": [[0, 1, 0.0, 2, 200, 5, "P0_S1"]],
    "blocks_neutro": [[0, 1, 0.0, 2, 200, 5, "P0_S1"]],
}


def ready_service(tmp_path: Path, wait: float = 0.05) -> SequenceService:
    service = SequenceService(data_dir=tmp_path)
    service.playback_queue.wait_seconds = wait
    service._ensure_connections = lambda blocks: None  # noqa: ARG005
    service._send_block_command = lambda block: None  # noqa: ARG005
    service.save_sequence({"sequence": ORIGIN, "overwrite": False})
    service.save_sequence({"sequence": ORIGIN_TWO, "overwrite": False})
    return service


def wait_idle(service: SequenceService, timeout: float = 3.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not service.get_runtime().busy:
            return
        time.sleep(0.02)
    raise AssertionError(service.get_runtime().model_dump())


def test_wait_seconds_is_one():
    assert WAIT_SECONDS == 1.0


def test_execute_action_enqueues_pair_and_returns_before_it_finishes(tmp_path: Path):
    service = ready_service(tmp_path, wait=0.3)
    hold = service.playback_queue._stop

    def slow_fire(blocks, stop_event):
        stop_event.wait(0.4)

    service._fire_blocks = slow_fire
    actions = ActionService(sequence_service=service)
    started = time.monotonic()
    result = actions.execute_action(1, 0)
    elapsed = time.monotonic() - started
    assert result.status == "ok"
    assert elapsed < 0.2
    snap = service.get_runtime()
    assert snap.busy is True
    assert snap.source == "turno"
    assert snap.current is not None
    assert snap.current.mode == "normal"
    assert snap.current.name == "saludo"
    modes = [snap.current.mode, *[item.mode for item in snap.queue]]
    assert modes == ["normal", "espera", "neutro", "espera"]
    service.stop_playback()
    wait_idle(service)


def test_second_execute_appends_second_pair(tmp_path: Path):
    service = ready_service(tmp_path, wait=0.3)

    def slow_fire(blocks, stop_event):
        stop_event.wait(0.4)

    service._fire_blocks = slow_fire
    actions = ActionService(sequence_service=service)
    actions.execute_action(1, 0)
    actions.execute_action(2, 0)
    snap = service.get_runtime()
    names_modes = [(snap.current.name, snap.current.mode)] + [
        (item.name, item.mode) for item in snap.queue
    ]
    assert names_modes == [
        ("saludo", "normal"),
        ("saludo", "espera"),
        ("saludo", "neutro"),
        ("saludo", "espera"),
        ("adios", "normal"),
        ("adios", "espera"),
        ("adios", "neutro"),
        ("adios", "espera"),
    ]
    service.stop_playback()
    wait_idle(service)


def test_user_play_while_busy_leaves_queue(tmp_path: Path):
    service = ready_service(tmp_path, wait=0.3)
    service._fire_blocks = lambda blocks, stop_event: stop_event.wait(0.4)
    ActionService(sequence_service=service).execute_action(1, 0)
    before = service.get_runtime().model_dump()
    with pytest.raises(ValueError, match="Ya existe una secuencia en ejecución"):
        service.start_user_playback(
            SequencePlaybackPayload(mode="neutro", source="panel", name="saludo")
        )
    after = service.get_runtime().model_dump()
    assert after["queue"] == before["queue"]
    assert after["current"] == before["current"]
    service.stop_playback()
    wait_idle(service)


def test_stop_clears_queue_and_wait(tmp_path: Path):
    service = ready_service(tmp_path, wait=2.0)
    service._fire_blocks = lambda blocks, stop_event: stop_event.wait(0.05)
    ActionService(sequence_service=service).execute_action(1, 0)
    time.sleep(0.08)
    status = service.stop_playback()
    assert status.status == "ok"
    wait_idle(service, timeout=1.0)
    snap = service.get_runtime()
    assert snap.busy is False
    assert snap.current is None
    assert snap.queue == []
    assert snap.source is None


def test_missing_arduino_skips_step_and_continues(tmp_path: Path):
    service = ready_service(tmp_path, wait=0.05)
    calls: list[str] = []

    def fire(blocks, stop_event):
        if blocks[0].pos == 850:
            raise ValueError("Arduinos no conectados para la secuencia: [0]")
        calls.append(blocks[0].nombre)
        return None

    service._fire_blocks = fire
    ActionService(sequence_service=service).execute_action(1, 0)
    wait_idle(service)
    assert calls == ["P0_S0"]


def test_incomplete_sequence_omits(tmp_path: Path):
    service = SequenceService(data_dir=tmp_path)
    (tmp_path / "incompleto.json").write_text(
        '{"version": 1, "id": 3, "name": "incompleto", "blocks": ['
        '{"arduino_id": 0, "pca": 0, "servo": 0, "inicio": 0, "dur": 2, "pos": 0, "vel": 1, "nombre": "P0_S0"}'
        "]}",
        encoding="utf-8",
    )
    service.start_user_playback = MagicMock()
    result = ActionService(sequence_service=service).execute_action(3, 0)
    assert result.status == "ok"
    assert result.response == ["omitido"]
    service.start_user_playback.assert_not_called()


def test_unknown_id_writes_serial(tmp_path: Path):
    service = SequenceService(data_dir=tmp_path)
    actions = ActionService(sequence_service=service)
    actions.arduino_utils = MagicMock()
    connection = MagicMock()
    actions.arduino_utils.connections = {0: connection}
    actions.arduino_utils.json_reader.read_first_meaningful_line.return_value = ["ok"]
    result = actions.execute_action(99, 0)
    connection.serial.write.assert_called_once_with(b"99\n")
    assert result.status == "ok"


def test_get_actions_one_row_per_gesture(tmp_path: Path):
    service = ready_service(tmp_path)
    commands = ActionService(sequence_service=service).get_actions()
    assert [item.name for item in commands] == ["adios", "saludo"] or [
        item.name for item in commands
    ] == ["saludo", "adios"]
    assert all(item.id in {1, 2} for item in commands)
```

Rewrite `test_execute_action_plays_sequence` in `test_action_catalog.py` to mock `enqueue_turn_pair` instead of `start_playback`:

```python
def test_execute_action_enqueues_complete_pair(tmp_path: Path):
    sequences = SequenceService(data_dir=tmp_path)
    sequences.save_sequence({"sequence": ORIGIN, "overwrite": False})
    sequences.enqueue_turn_pair = MagicMock(
        return_value=SequenceStatusResponse(status="ok", message="Encolado")
    )
    service = ActionService(sequence_service=sequences)
    result = service.execute_action(action_id=1, arduino_id=9)
    sequences.enqueue_turn_pair.assert_called_once()
    assert result.status == "ok"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd pba-ms-robotics && python -m pytest tests/test_playback_queue.py tests/test_action_catalog.py -v
```

Expected: FAIL — `playback_queue` / `enqueue_turn_pair` / `get_runtime` missing.

- [ ] **Step 3: Implement the queue**

Add to `sequence_interface.py`:

```python
from typing import Literal

class SequencePlaybackPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    mode: Literal["normal", "neutro"] = "normal"
    source: Literal["panel", "estudio"] = "panel"
    name: str | None = None
    blocks: list[MotionBlock] | None = None

    @model_validator(mode="after")
    def name_or_blocks(self) -> "SequencePlaybackPayload":
        if not self.name and not self.blocks:
            raise ValueError("Indique name o blocks")
        return self


class QueueStepPublic(BaseModel):
    id: int | None = None
    name: str
    mode: Literal["normal", "neutro", "espera"]
    source: Literal["turno", "panel", "estudio"]


class RuntimeSnapshot(BaseModel):
    busy: bool
    source: Literal["turno", "panel", "estudio"] | None = None
    current: QueueStepPublic | None = None
    queue: list[QueueStepPublic]
```

Create `pba-ms-robotics/src/sequence/playback_queue.py`:

```python
from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from src.sequence.interfaces.sequence_interface import (
    MotionBlock,
    QueueStepPublic,
    RuntimeSnapshot,
)

logger = logging.getLogger(__name__)

WAIT_SECONDS = 1.0


@dataclass
class QueueStep:
    id: int | None
    name: str
    mode: str
    source: str
    blocks: list[MotionBlock] | None = None


class PlaybackQueue:
    def __init__(
        self,
        fire_blocks: Callable[[list[MotionBlock], threading.Event], None],
        wait_seconds: float = WAIT_SECONDS,
    ) -> None:
        self._fire_blocks = fire_blocks
        self.wait_seconds = wait_seconds
        self._lock = threading.Lock()
        self._queue: list[QueueStep] = []
        self._current: QueueStep | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def enqueue(self, steps: list[QueueStep], *, reject_if_busy: bool) -> None:
        with self._lock:
            if reject_if_busy and self._busy_unlocked():
                raise ValueError("Ya existe una secuencia en ejecución")
            self._queue.extend(steps)
            if self._thread is None or not self._thread.is_alive():
                self._stop.clear()
                self._thread = threading.Thread(
                    target=self._run, name="sequence-queue", daemon=True
                )
                self._thread.start()

    def stop(self) -> None:
        with self._lock:
            self._queue.clear()
            thread = self._thread
            self._stop.set()
        if thread is not None:
            thread.join(timeout=2.0)
        with self._lock:
            self._current = None
            self._thread = None
            self._stop = threading.Event()

    def snapshot(self) -> RuntimeSnapshot:
        with self._lock:
            current = self._public(self._current)
            queue = [self._public(item) for item in self._queue]
            source = None
            if current is not None:
                source = current.source
            elif queue:
                source = queue[0].source
            return RuntimeSnapshot(
                busy=self._busy_unlocked(),
                source=source,
                current=current,
                queue=queue,
            )

    def _busy_unlocked(self) -> bool:
        thread_live = self._thread is not None and self._thread.is_alive()
        return thread_live or self._current is not None or bool(self._queue)

    def _public(self, step: QueueStep | None) -> QueueStepPublic | None:
        if step is None:
            return None
        return QueueStepPublic(id=step.id, name=step.name, mode=step.mode, source=step.source)  # type: ignore[arg-type]

    def _pop(self) -> QueueStep | None:
        with self._lock:
            if not self._queue:
                self._current = None
                return None
            step = self._queue.pop(0)
            self._current = step
            return step

    def _run(self) -> None:
        try:
            while not self._stop.is_set():
                step = self._pop()
                if step is None:
                    return
                if step.mode == "espera":
                    self._sleep(self.wait_seconds)
                    continue
                if step.blocks is None:
                    logger.warning("Paso %s sin bloques; se descarta", step.name)
                    continue
                try:
                    self._fire_blocks(step.blocks, self._stop)
                except ValueError:
                    logger.warning("Paso descartado por hardware ausente: %s %s", step.name, step.mode)
                    continue
        finally:
            with self._lock:
                if self._thread is threading.current_thread():
                    self._thread = None
                    self._current = None

    def _sleep(self, seconds: float) -> None:
        deadline = time.monotonic() + seconds
        while not self._stop.is_set() and time.monotonic() < deadline:
            time.sleep(0.02)
```

In `SequenceService.__init__` create the queue with a lookup lambda so tests can replace `_fire_blocks` on the instance after construction:

```python
self.playback_queue = PlaybackQueue(lambda blocks, stop: self._fire_blocks(blocks, stop))
```

Extract `_fire_blocks` from the body of `_run_playback` (the sorted-block loop). `_run_playback` should call `_fire_blocks` then clear `_playback_thread` as it does today (chain still uses `start_playback`).

Add:

```python
def enqueue_turn_pair(self, sequence: MotionSequenceFile) -> SequenceStatusResponse:
    source = "turno"
    steps = [
        QueueStep(id=sequence.id, name=sequence.name, mode="normal", source=source, blocks=list(sequence.blocks)),
        QueueStep(id=sequence.id, name=sequence.name, mode="espera", source=source),
        QueueStep(id=sequence.id, name=sequence.name, mode="neutro", source=source, blocks=list(sequence.blocks_neutro)),
        QueueStep(id=sequence.id, name=sequence.name, mode="espera", source=source),
    ]
    self.playback_queue.enqueue(steps, reject_if_busy=False)
    return SequenceStatusResponse(status="ok", message="Encolado")


def start_user_playback(self, payload: SequencePlaybackPayload) -> SequenceStatusResponse:
    if payload.blocks is not None:
        name = payload.name or ""
        step = QueueStep(id=None, name=name, mode=payload.mode, source=payload.source, blocks=list(payload.blocks))
    else:
        sequence = self.get_sequence(payload.name or "")
        blocks = sequence.blocks_neutro if payload.mode == "neutro" else sequence.blocks
        step = QueueStep(
            id=sequence.id,
            name=sequence.name,
            mode=payload.mode,
            source=payload.source,
            blocks=list(blocks),
        )
    self.playback_queue.enqueue([step], reject_if_busy=True)
    return SequenceStatusResponse(status="ok", message="Secuencia iniciada")


def get_runtime(self) -> RuntimeSnapshot:
    return self.playback_queue.snapshot()
```

`start_playback` (chain / old callers) stays. `stop_playback` calls `self.playback_queue.stop()` first, then joins the legacy playback thread as today. Idle message stays `No había secuencia en ejecución` when both were idle.

`sequence_controller.start_playback` validates `SequencePlaybackPayload` and calls `start_user_playback`. Add:

```python
async def get_runtime(self, _: dict[str, Any]) -> dict[str, Any]:
    return self.sequence_service.get_runtime().model_dump()
```

In `nats_subscribers.py` add subject `{ROBOTICS_MS}.sequenceService.getRuntime` → `sequence_controller.get_runtime`. Keep `startPlayback` validating the new payload (name-or-blocks).

`action_service.execute_action`:

```python
def execute_action(self, action_id: int, arduino_id: int) -> ExecuteActionResponse:
    sequence = self.sequence_service.find_by_id(action_id)
    if sequence is not None:
        if not is_complete_pair(sequence):
            logger.warning("Secuencia %s incompleta; se omite", action_id)
            return ExecuteActionResponse(status="ok", response=["omitido"])
        status = self.sequence_service.enqueue_turn_pair(sequence)
        return ExecuteActionResponse(
            status=status.status,
            response=[status.message] if status.message else ["secuencia"],
        )
    # existing serial write
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd pba-ms-robotics && python -m pytest tests/test_playback_queue.py tests/test_action_catalog.py tests/test_sequence_ingest.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd pba-ms-robotics
git add src/sequence/playback_queue.py src/sequence/interfaces/sequence_interface.py src/sequence/sequence_service.py src/sequence/sequence_controller.py src/core/nats/nats_subscribers.py src/action/action_service.py tests/test_playback_queue.py tests/test_action_catalog.py
git commit -m "Queue turn pairs on one player and expose live runtime."
```

---

### Task 3: Gateway DTO, play mode, and GET /sequence/runtime

**Files:**
- Modify: `pba-ms-gateway/src/robotics-ms/sequence/dto/sequence.dto.ts`
- Modify: `pba-ms-gateway/src/robotics-ms/sequence/dto/sequence.dto.spec.ts`
- Modify: `pba-ms-gateway/src/robotics-ms/sequence/sequence.controller.ts`

**Interfaces:**
- Consumes: JSON bodies already used by studio/panel.
- Produces: `MotionSequenceDto.category` required, `blocks_neutro` required nonempty array. `StartPlaybackDto.mode` default inferred by omitting (`normal` in robotics), optional `name`, optional `blocks`, optional `source`. `GET /sequence/runtime` → NATS `ROBOTICS_MS.sequenceService.getRuntime`. Chain routes unchanged.

- [ ] **Step 1: Write the failing tests**

Extend `sequence.dto.spec.ts`:

```typescript
import { SaveSequenceDto, StartPlaybackDto } from './sequence.dto';

function validatePlay(body: object) {
  const instance = plainToInstance(StartPlaybackDto, body);
  return validateSync(instance, { whitelist: true, forbidNonWhitelisted: true });
}

it('accepts origin with category and blocks_neutro', () => {
  const errors = validateBody({
    sequence: {
      name: 'saludo',
      description: 'Saludo con el brazo derecho',
      category: 'brazo_derecho',
      arduino_id: 0,
      blocks: [[0, 0, 0.0, 2, 850, 5, 'P0_S0']],
      blocks_neutro: [[0, 0, 0.0, 2, 500, 5, 'P0_S0']],
    },
    overwrite: false,
  });
  expect(errors).toEqual([]);
});

it('rejects origin without category', () => {
  const errors = validateBody({
    sequence: {
      name: 'saludo',
      blocks: [[0, 0, 0.0, 2, 0, 1, 'P0_S0']],
      blocks_neutro: [[0, 0, 0.0, 2, 0, 1, 'P0_S0']],
    },
  });
  expect(errors.length).toBeGreaterThan(0);
});

it('accepts play by name and mode', () => {
  expect(validatePlay({ name: 'saludo', mode: 'neutro', source: 'panel' })).toEqual([]);
});

it('rejects play without name or blocks', () => {
  expect(validatePlay({ mode: 'normal' }).length).toBeGreaterThan(0);
});
```

Update the existing origin fixture to include `category` and `blocks_neutro` so it still passes.

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd pba-ms-gateway && npx jest src/robotics-ms/sequence/dto/sequence.dto.spec.ts
```

Expected: FAIL — `category` / `StartPlaybackDto.name` not on the DTO.

- [ ] **Step 3: Implement DTOs and runtime route**

On `MotionSequenceDto`:

```typescript
import { IsIn, Validate, ValidatorConstraint, ValidatorConstraintInterface, ValidationArguments } from 'class-validator';

@IsString()
@IsIn(['cara', 'cuello', 'brazo_derecho', 'brazo_izquierdo', 'torso', 'cadera'])
category: string;

@IsArray()
@ArrayMinSize(1)
blocks_neutro: unknown[];
```

Replace `StartPlaybackDto`:

```typescript
@ValidatorConstraint({ name: 'nameOrBlocks', async: false })
class NameOrBlocksConstraint implements ValidatorConstraintInterface {
  validate(_: unknown, args: ValidationArguments) {
    const obj = args.object as StartPlaybackDto;
    return Boolean(obj.name) || (Array.isArray(obj.blocks) && obj.blocks.length > 0);
  }

  defaultMessage() {
    return 'Indique name o blocks';
  }
}

export class StartPlaybackDto {
  @Validate(NameOrBlocksConstraint)
  @IsOptional()
  @IsIn(['normal', 'neutro'])
  mode?: 'normal' | 'neutro';

  @IsOptional()
  @IsIn(['panel', 'estudio'])
  source?: 'panel' | 'estudio';

  @IsOptional()
  @IsString()
  @IsNotEmpty()
  name?: string;

  @IsOptional()
  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => MotionBlockDto)
  blocks?: MotionBlockDto[];
}
```

In `sequence.controller.ts` add:

```typescript
@Get('runtime')
async getRuntime() {
  return this.client.send(`${ROBOTICS_MS}.sequenceService.getRuntime`, {}).pipe(
    catchError((error) => {
      throw new RpcException(error);
    }),
  );
}
```

Keep `chain/start`, `chain/stop`, `chain/status`.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd pba-ms-gateway && npx jest src/robotics-ms/sequence/dto/sequence.dto.spec.ts
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd pba-ms-gateway
git add src/robotics-ms/sequence/dto/sequence.dto.ts src/robotics-ms/sequence/dto/sequence.dto.spec.ts src/robotics-ms/sequence/sequence.controller.ts
git commit -m "Accept pair fields on save and expose sequence runtime."
```

---

### Task 4: Studio generate-neutro and local origin store

**Files:**
- Create: `pmas-web-motion-studio/src/neutro.py`
- Create: `pmas-web-motion-studio/tests/test_neutro.py`
- Modify: `pmas-web-motion-studio/src/local_sequences.py`
- Modify: `pmas-web-motion-studio/tests/test_local_sequences.py`

**Interfaces:**
- Consumes: 7-tuples `[pca, servo, inicio, dur, pos, vel, nombre]`.
- Produces: `generate_neutro(blocks: list[list], existing: list[list] | None = None, replace: bool = False) -> list[list]`. For each `(pca, servo)` take the `pos` of the block with smallest `inicio` (tie: first in the array). Emit `[pca, servo, 0, 2, pos, vel, nombre]` using `vel` and `nombre` of that seed. If `existing` is nonempty and `replace` is false: `ValueError("La pista neutra ya existe")`. `LocalSequenceStore._normalize` requires `category in CATEGORIES` and nonempty `blocks_neutro`; origin JSON still has no `id`.

- [ ] **Step 1: Write the failing tests**

Create `pmas-web-motion-studio/tests/test_neutro.py`:

```python
import pytest
from src.neutro import generate_neutro


def test_first_pos_per_servo():
    blocks = [
        [0, 0, 1.0, 2, 900, 4, "tarde"],
        [0, 0, 0.0, 2, 100, 5, "temprano"],
        [0, 1, 0.5, 1, 300, 2, "otro"],
    ]
    assert generate_neutro(blocks) == [
        [0, 0, 0, 2, 100, 5, "temprano"],
        [0, 1, 0, 2, 300, 2, "otro"],
    ]


def test_tie_keeps_first_in_array():
    blocks = [
        [0, 0, 0.0, 2, 10, 1, "a"],
        [0, 0, 0.0, 2, 99, 9, "b"],
    ]
    assert generate_neutro(blocks) == [[0, 0, 0, 2, 10, 1, "a"]]


def test_replace_flag_required_when_existing():
    existing = [[0, 0, 0, 2, 1, 1, "x"]]
    with pytest.raises(ValueError, match="ya existe"):
        generate_neutro([[0, 0, 0, 2, 2, 2, "y"]], existing=existing, replace=False)
    assert generate_neutro([[0, 0, 0, 2, 2, 2, "y"]], existing=existing, replace=True) == [
        [0, 0, 0, 2, 2, 2, "y"]
    ]
```

Update `ORIGIN` in `tests/test_local_sequences.py`:

```python
ORIGIN = {
    "name": "saludo",
    "description": "Saludo con el brazo derecho",
    "category": "brazo_derecho",
    "arduino_id": 0,
    "blocks": [[0, 0, 0.0, 2, 500, 5, "P0_S0"]],
    "blocks_neutro": [[0, 0, 0.0, 2, 500, 5, "P0_S0"]],
}
```

Add:

```python
def test_save_rejects_missing_category(tmp_path):
    client = client_with_store(tmp_path)
    raw = dict(ORIGIN)
    raw.pop("category")
    response = client.post("/local/sequences", json={"sequence": raw, "overwrite": False})
    assert response.status_code == 400
    assert "categoría" in response.json()["detail"].lower() or "categoria" in response.json()["detail"].lower()


def test_save_roundtrip_keeps_neutro(tmp_path):
    client = client_with_store(tmp_path)
    saved = client.post("/local/sequences", json={"sequence": ORIGIN, "overwrite": False})
    assert saved.status_code == 200
    assert saved.json()["category"] == "brazo_derecho"
    assert saved.json()["blocks_neutro"][0] == [0, 0, 0.0, 2, 500, 5, "P0_S0"]
    assert "id" not in saved.json()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd pmas-web-motion-studio && python -m pytest tests/test_neutro.py tests/test_local_sequences.py -v
```

Expected: FAIL — `src.neutro` missing; local save does not require category.

- [ ] **Step 3: Implement**

Create `pmas-web-motion-studio/src/neutro.py`:

```python
from typing import Any

CATEGORIES = (
    "cara",
    "cuello",
    "brazo_derecho",
    "brazo_izquierdo",
    "torso",
    "cadera",
)


def generate_neutro(
    blocks: list[list[Any]],
    existing: list[list[Any]] | None = None,
    replace: bool = False,
) -> list[list[Any]]:
    if existing and not replace:
        raise ValueError("La pista neutra ya existe")
    seeds: dict[tuple[int, int], list[Any]] = {}
    order: list[tuple[int, int]] = []
    for item in blocks:
        pca, servo = int(item[0]), int(item[1])
        key = (pca, servo)
        if key not in seeds:
            seeds[key] = item
            order.append(key)
            continue
        if float(item[2]) < float(seeds[key][2]):
            seeds[key] = item
    return [
        [pca, servo, 0, 2, int(seeds[(pca, servo)][4]), int(seeds[(pca, servo)][5]), str(seeds[(pca, servo)][6])]
        for pca, servo in order
    ]
```

In `_normalize`, reuse `blocks_from_raw` logic already there as a local helper `_tuples(raw)` used for both `blocks` and `blocks_neutro`. Require `category` in `CATEGORIES` (`ValueError("Categoría inválida")`) and nonempty neutro (`ValueError("Falta la pista neutra")`). Return dict:

```python
return {
    "name": name,
    "description": description,
    "category": category,
    "arduino_id": arduino_id,
    "blocks": tuples,
    "blocks_neutro": neutro,
}
```

`app.py` already maps `ValueError` to 400; keep that.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd pmas-web-motion-studio && python -m pytest tests/test_neutro.py tests/test_local_sequences.py tests/test_app.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd pmas-web-motion-studio
git add src/neutro.py src/local_sequences.py tests/test_neutro.py tests/test_local_sequences.py
git commit -m "Generate a rest track and require it in studio origin files."
```

---

### Task 5: Studio editor — category, two tracks, generate, busy play

**Files:**
- Modify: `pmas-web-motion-studio/src/static/index.html`
- Modify: `pmas-web-motion-studio/src/static/editor.js`
- Modify: `pmas-web-motion-studio/src/static/editor.css`
- Modify: `pmas-web-motion-studio/tests/test_app.py`

**Interfaces:**
- Consumes: `generate_neutro` algorithm duplicated in JS (same rules as `src/neutro.py`). Coupled play `POST /sequence/play` with `{ mode, source: "estudio", blocks }` of the **active** track.
- Produces: `buildOrigin()` includes `category`, `blocks`, `blocks_neutro`. Library still one row per gesture. 401 still requests auth; 409/400 on play show the error and do not call `requestAuth`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_app.py` add:

```python
def test_index_has_category_and_neutro_controls():
    text = TestClient(app).get("/").text
    assert 'id="category"' in text
    assert 'id="track-gesto"' in text
    assert 'id="track-neutro"' in text
    assert 'id="generate-neutro"' in text
    assert "brazo_derecho" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd pmas-web-motion-studio && python -m pytest tests/test_app.py::test_index_has_category_and_neutro_controls -v
```

Expected: FAIL — ids missing.

- [ ] **Step 3: Implement the editor**

In `index.html` chrome, after Arduino, add:

```html
<label class="field">
  <span>Categoría</span>
  <select id="category">
    <option value="">Elegir</option>
    <option value="cara">Cara</option>
    <option value="cuello">Cuello</option>
    <option value="brazo_derecho">Brazo derecho</option>
    <option value="brazo_izquierdo">Brazo izquierdo</option>
    <option value="torso">Torso</option>
    <option value="cadera">Cadera</option>
  </select>
</label>
```

In `.actions`, after Play:

```html
<button type="button" id="track-gesto" class="btn active">Gesto</button>
<button type="button" id="track-neutro" class="btn">Neutro</button>
<button type="button" id="generate-neutro" class="btn">Generar neutro</button>
```

In `editor.js`:

- Keep `blocks` as the active track's array. Add `gestureBlocks = []`, `neutroBlocks = []`, `activeTrack = "normal"`.
- `setActiveTrack(next)` copies `blocks` into `gestureBlocks` or `neutroBlocks` depending on `activeTrack`, then loads the other array into `blocks`, updates button `.active`, toggles `document.documentElement.classList.toggle("track-neutro", next === "neutro")`, `render()`.
- `flushActive()` copies `blocks` into `gestureBlocks` or `neutroBlocks` according to `activeTrack`. `setActiveTrack(next)` flushes, then sets `blocks` to the other array (same object reference as `gestureBlocks` / `neutroBlocks`).
- `buildOrigin()` first calls `flushActive()`, then:

```javascript
function buildOrigin() {
  flushActive();
  return {
    name: els.name.value.trim(),
    description: els.description.value.replace(/\n/g, " ").slice(0, 280),
    category: els.category.value,
    arduino_id: Number(els.arduino.value || 0),
    blocks: tuplesOf(gestureBlocks),
    blocks_neutro: tuplesOf(neutroBlocks),
  };
}
```

- Save: if `!sequence.category || !sequence.blocks.length || !sequence.blocks_neutro.length` → `setStatus("Categoría, gesto y neutro son obligatorios", true)` and return.
- `generateNeutro()`:

```javascript
function generateNeutro() {
  flushActive();
  if (!gestureBlocks.length) {
    setStatus("Agrega bloques al gesto", true);
    return;
  }
  if (neutroBlocks.length && !confirm("¿Reemplazar la pista neutra?")) return;
  neutroBlocks = generateNeutroFrom(tuplesOf(gestureBlocks)).map((item) => createBlock({
    pca: item[0], servo: item[1], inicio: item[2], dur: item[3], pos: item[4], vel: item[5], nombre: item[6],
  }));
  if (activeTrack === "neutro") blocks = neutroBlocks;
  render();
  setStatus("Pista neutra generada");
}

function generateNeutroFrom(tuples) {
  const seeds = new Map();
  const order = [];
  for (const item of tuples) {
    const key = `${item[0]}:${item[1]}`;
    if (!seeds.has(key)) {
      seeds.set(key, item);
      order.push(key);
      continue;
    }
    if (Number(item[2]) < Number(seeds.get(key)[2])) seeds.set(key, item);
  }
  return order.map((key) => {
    const item = seeds.get(key);
    return [item[0], item[1], 0, 2, item[4], item[5], item[6]];
  });
}
```

- `parseLoadedSequence`: fill `els.category`, map `blocks` → `gestureBlocks`, `blocks_neutro` → `neutroBlocks` (empty if missing), `activeTrack = "normal"`, `blocks = gestureBlocks`.
- `playCurrent`: flush; play **active** track tuples. Coupled body:

```javascript
body: JSON.stringify({
  mode: activeTrack === "neutro" ? "neutro" : "normal",
  source: "estudio",
  blocks: playBlocks,
})
```

On `!response.ok`: `stopPlayhead()`; `setStatus(await readError(response) || "No se pudo previsualizar", true)`; **do not** call `requestAuth` unless `response.status === 401` (already handled in `authorizedFetch`).

- CSS: `.track-neutro .block { filter: hue-rotate(40deg); }` and `.btn.active { outline: 1px solid var(--cyan); }`.

Bump cache query on `editor.js` / `editor.css` (`?v=neutro`).

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd pmas-web-motion-studio && python -m pytest tests/test_app.py tests/test_local_sequences.py tests/test_neutro.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd pmas-web-motion-studio
git add src/static/index.html src/static/editor.js src/static/editor.css tests/test_app.py
git commit -m "Edit gesture and rest tracks in one studio sequence."
```

---

### Task 6: Angular origin importer rejects incomplete rows

**Files:**
- Modify: `pmas-web-main/src/app/pages/sequences/origin-sequence.ts`
- Modify: `pmas-web-main/src/app/pages/sequences/origin-sequence.spec.ts`
- Modify: `pmas-web-main/src/app/pages/sequences/sequences.ts`

**Interfaces:**
- Consumes: file text.
- Produces: `OriginParseResult` with `category: string | null` and `blocksNeutro: OriginTuple[]`. `error` set when category missing or `blocks_neutro` empty. `importSingleOrigin` POSTs `category` and `blocks_neutro`. Raw 7-tuple lists (no wrapper) are rejected with that error. Other valid files in the same batch still import.

- [ ] **Step 1: Write the failing tests**

Replace/extend `origin-sequence.spec.ts`:

```typescript
it('reads origin pair', () => {
  const parsed = parseOriginText(
    JSON.stringify({
      name: 'saludo',
      description: 'Saludo con el brazo derecho',
      category: 'brazo_derecho',
      blocks: [[0, 0, 0.0, 2, 850, 5, 'P0_S0']],
      blocks_neutro: [[0, 0, 0.0, 2, 500, 5, 'P0_S0']],
    }),
    'archivo',
    1,
  );
  expect(parsed.error).toBeNull();
  expect(parsed.category).toBe('brazo_derecho');
  expect(parsed.blocksNeutro[0][4]).toBe(500);
});

it('rejects missing category or neutro', () => {
  const parsed = parseOriginText(
    JSON.stringify({
      name: 'saludo',
      blocks: [[0, 0, 0.0, 2, 0, 1, 'P0_S0']],
    }),
    'archivo',
    1,
  );
  expect(parsed.error).toMatch(/categor[ií]a|neutro/i);
});

it('rejects raw 7-tuple list', () => {
  const parsed = parseOriginText(JSON.stringify([[0, 0, 0.0, 2, 0, 1, 'P0_S0']]), 'viejo', 0);
  expect(parsed.error).toBeTruthy();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd pmas-web-main && npx vitest run src/app/pages/sequences/origin-sequence.spec.ts
```

Expected: FAIL — `category` / `blocksNeutro` missing; raw list currently succeeds.

- [ ] **Step 3: Implement**

```typescript
const CATEGORIES = [
  'cara',
  'cuello',
  'brazo_derecho',
  'brazo_izquierdo',
  'torso',
  'cadera',
] as const;

export interface OriginParseResult {
  name: string;
  description: string;
  category: string | null;
  blocks: OriginTuple[];
  blocksNeutro: OriginTuple[];
  error: string | null;
}
```

When the wrapper has `blocks` but `category` is not in `CATEGORIES` or `blocks_neutro` is missing/empty, return `error: 'Falta categoría o neutro'`. Raw arrays return the same error. Success path maps `blocks_neutro` with `toTuple`.

`OriginImportItem` gains `category` and `tupleBlocksNeutro`. `validItems` already requires `error === null`. Payload:

```typescript
sequence: {
  name: item.targetName.trim(),
  description: item.description,
  category: item.category,
  arduino_id: item.arduino_id,
  blocks: item.tupleBlocks,
  blocks_neutro: item.tupleBlocksNeutro,
}
```

A failed POST still `resolve()` so siblings continue.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd pmas-web-main && npx vitest run src/app/pages/sequences/origin-sequence.spec.ts
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd pmas-web-main
git add src/app/pages/sequences/origin-sequence.ts src/app/pages/sequences/origin-sequence.spec.ts src/app/pages/sequences/sequences.ts
git commit -m "Import only origin files that include category and rest track."
```

---

### Task 7: Control panel — categories, Normal/Neutro, En hardware

**Files:**
- Create: `pmas-web-main/src/app/pages/control-panel/sequence-groups.ts`
- Create: `pmas-web-main/src/app/pages/control-panel/sequence-groups.spec.ts`
- Modify: `pmas-web-main/src/app/pages/control-panel/control-panel.ts`
- Modify: `pmas-web-main/src/app/pages/control-panel/control-panel.html`

**Interfaces:**
- Consumes: `GET /sequence/files`, `GET /sequence/file?name=`, `GET /sequence/runtime`, `POST /sequence/play` `{ name, mode, source: "panel" }`, `POST /sequence/stop`.
- Produces: `CATEGORY_ORDER`, `CATEGORY_LABELS`, `isPlayableSequence`, `groupByCategory`. Panel always renders six sections in that order. `playLocked = runtimeUnreachable || runtime.busy`. Poll 500 ms if `busy || unreachable`, else 3 s. Stop always enabled. Chain builder removed from this view (HTTP chain routes remain).

- [ ] **Step 1: Write the failing tests**

Create `sequence-groups.spec.ts`:

```typescript
import { describe, expect, it } from 'vitest';
import { CATEGORY_LABELS, CATEGORY_ORDER, groupByCategory, isPlayableSequence } from './sequence-groups';

const saludo = {
  name: 'saludo',
  description: 'Saludo con el brazo derecho',
  category: 'brazo_derecho' as const,
  blocks: [{ pos: 1 }],
  blocks_neutro: [{ pos: 2 }],
};

describe('sequence groups', () => {
  it('keeps the six body sections in spec order', () => {
    expect(CATEGORY_ORDER).toEqual([
      'cara',
      'cuello',
      'brazo_derecho',
      'brazo_izquierdo',
      'torso',
      'cadera',
    ]);
    expect(CATEGORY_LABELS.brazo_derecho).toBe('Brazo derecho');
  });

  it('hides legacy files without a pair', () => {
    expect(
      isPlayableSequence({
        name: 'legado',
        description: '',
        category: null,
        blocks: [{ pos: 1 }],
        blocks_neutro: [],
      }),
    ).toBe(false);
    expect(isPlayableSequence(saludo)).toBe(true);
  });

  it('puts playable sequences in the six sections', () => {
    const groups = groupByCategory([saludo]);
    expect(groups.map((item) => item.key)).toEqual(CATEGORY_ORDER);
    expect(groups[2].label).toBe('Brazo derecho');
    expect(groups[2].sequences[0].name).toBe('saludo');
    expect(groups[0].sequences).toEqual([]);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd pmas-web-main && npx vitest run src/app/pages/control-panel/sequence-groups.spec.ts
```

Expected: FAIL — module missing.

- [ ] **Step 3: Implement grouping helper and panel**

`sequence-groups.ts`:

```typescript
export const CATEGORY_ORDER = [
  'cara',
  'cuello',
  'brazo_derecho',
  'brazo_izquierdo',
  'torso',
  'cadera',
] as const;

export type SequenceCategory = (typeof CATEGORY_ORDER)[number];

export const CATEGORY_LABELS: Record<SequenceCategory, string> = {
  cara: 'Cara',
  cuello: 'Cuello',
  brazo_derecho: 'Brazo derecho',
  brazo_izquierdo: 'Brazo izquierdo',
  torso: 'Torso',
  cadera: 'Cadera',
};

export interface PlayableSequence {
  name: string;
  description: string;
  category: SequenceCategory | null | undefined;
  blocks: unknown[];
  blocks_neutro: unknown[];
}

export function isPlayableSequence(sequence: PlayableSequence): boolean {
  return (
    CATEGORY_ORDER.includes(sequence.category as SequenceCategory) &&
    Array.isArray(sequence.blocks) &&
    sequence.blocks.length > 0 &&
    Array.isArray(sequence.blocks_neutro) &&
    sequence.blocks_neutro.length > 0
  );
}

export function groupByCategory(sequences: PlayableSequence[]) {
  return CATEGORY_ORDER.map((key) => ({
    key,
    label: CATEGORY_LABELS[key],
    sequences: sequences
      .filter((item) => item.category === key && isPlayableSequence(item))
      .sort((a, b) => a.name.localeCompare(b.name)),
  }));
}
```

In `control-panel.ts`:

- Extend `SequenceDetail` with `id?: number | null`, `category?: string | null`, `blocks_neutro: MotionBlock[]`.
- Replace folder grouping with `sequenceGroups = signal(groupByCategory([]))` after fetch; skip files that fail `isPlayableSequence`.
- Remove `selectedChain`, `addToChain`, `removeFromChain`, `clearChain`, `startChain`, `stopChain`, `refreshChainStatus`, `chainStatusTimer`, chain signals.
- Add:

```typescript
interface RuntimeStep {
  id: number | null;
  name: string;
  mode: 'normal' | 'neutro' | 'espera';
  source: 'turno' | 'panel' | 'estudio';
}

interface RuntimeSnapshot {
  busy: boolean;
  source: 'turno' | 'panel' | 'estudio' | null;
  current: RuntimeStep | null;
  queue: RuntimeStep[];
}

runtime = signal<RuntimeSnapshot>({ busy: false, source: null, current: null, queue: [] });
runtimeUnreachable = signal(false);
playLocked = computed(() => this.runtimeUnreachable() || this.runtime().busy);

executePhase(name: string, mode: 'normal' | 'neutro') {
  if (this.playLocked()) return;
  this.http
    .post<{ status: string; message: string }>(`${GATEWAY_URL}/sequence/play`, {
      name,
      mode,
      source: 'panel',
    })
    .subscribe({
      next: () => {
        this.appendLog({ group: this.groupLabelForSequence(name), sequenceName: `${name} ${mode}`, status: 'ack', message: 'Solicitado' });
        this.pollRuntime();
      },
      error: (err) => {
        this.appendLog({
          group: this.groupLabelForSequence(name),
          sequenceName: name,
          status: 'error',
          message: err?.error?.message || 'No se pudo ejecutar',
        });
      },
    });
}

stopHardware() {
  this.http.post(`${GATEWAY_URL}/sequence/stop`, {}).subscribe({
    next: () => this.pollRuntime(),
    error: () => this.appendLog({ group: 'HARDWARE', sequenceName: 'stop', status: 'error', message: 'No se pudo detener' }),
  });
}

private pollRuntime() {
  if (this.runtimeTimer) clearTimeout(this.runtimeTimer);
  this.http.get<RuntimeSnapshot>(`${GATEWAY_URL}/sequence/runtime`).subscribe({
    next: (res) => {
      this.runtimeUnreachable.set(false);
      this.runtime.set(res);
      this.runtimeTimer = setTimeout(() => this.pollRuntime(), res.busy ? 500 : 3000);
    },
    error: () => {
      this.runtimeUnreachable.set(true);
      this.runtimeTimer = setTimeout(() => this.pollRuntime(), 500);
    },
  });
}
```

`ngOnInit` calls `loadSequences()` and `pollRuntime()`. `ngOnDestroy` clears `runtimeTimer`.

Filter search uses `group.sequences` (not `sequenceNames`). `groupFilterOptions` is `Todas` plus the six labels (`ALL` + `CATEGORY_ORDER`). Empty section with no search query still shows the six headers (empty state inside each). When a search is active, hide sections with zero matches.

In `control-panel.html`:

- Each sequence card: name, description, two buttons `Normal` and `Neutro` calling `executePhase(name, 'normal'|'neutro')`, `[disabled]="playLocked()"`.
- Replace the chain card with:

```html
<div class="bg-surface-container rounded-xl border border-white/5 shadow-xl overflow-hidden">
  <div class="px-5 py-3 bg-surface-container-high border-b border-white/5 flex items-center justify-between">
    <h3 class="font-headline text-sm font-bold tracking-tight text-on-surface">En hardware</h3>
    <button (click)="stopHardware()" class="py-2 px-3 rounded bg-red-600 text-white text-[10px] font-semibold cursor-pointer">
      Detener
    </button>
  </div>
  <div class="p-4 space-y-2 text-[10px] font-mono text-slate-400">
    @if (runtimeUnreachable()) {
      <p class="text-error">sin estado</p>
    } @else {
      <p>Origen: {{ runtime().source || '—' }}</p>
      <p>Fase: {{ runtime().current ? (runtime().current!.name + ' · ' + runtime().current!.mode) : 'idle' }}</p>
      <p>Cola:</p>
      @if (runtime().queue.length === 0) {
        <p>—</p>
      } @else {
        @for (step of runtime().queue; track $index) {
          <p>{{ step.name }} · {{ step.mode }}</p>
        }
      }
    }
  </div>
</div>
```

Keep Execution Log. Change the empty-filter copy only if all six sections are empty of playable sequences after load (`sequenceGroups().every(g => g.sequences.length === 0)` and no search).

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd pmas-web-main && npx vitest run src/app/pages/control-panel/sequence-groups.spec.ts src/app/pages/sequences/origin-sequence.spec.ts
```

Expected: PASS.

Browser check when Compose is up: open `/control-panel`, confirm six headers, Normal/Neutro disabled while a turn-like play is busy, En hardware lists current + queue, Detener clears it. If Compose is not running, say so; the Vitest helpers are the automated gate.

- [ ] **Step 5: Commit**

```bash
cd pmas-web-main
git add src/app/pages/control-panel/sequence-groups.ts src/app/pages/control-panel/sequence-groups.spec.ts src/app/pages/control-panel/control-panel.ts src/app/pages/control-panel/control-panel.html
git commit -m "Show category playback and live hardware state on the control panel."
```

---

### Task 8: Agent docs

**Files:**
- Modify: `AGENTS.md`
- Modify: `.cursor/rules/robotics-actions.mdc`

**Interfaces:**
- Consumes: behavior shipped in Tasks 1–7.
- Produces: agents read that `getActions` is complete pairs only; `executeAction` enqueues normal→wait→neutro→wait; panel is the visor.

- [ ] **Step 1: Write the doc edits**

In `AGENTS.md` turn step 3, after “lista secuencias ingestadas con `id`”, add that only pairs with `category` and `blocks_neutro` enter the catalog. Step 5: mai-core still calls `executeAction` per id without waiting; robotics expands each id to normal, 1 s, neutro, 1 s.

In `.cursor/rules/robotics-actions.mdc` replace the `execute_action` paragraph with:

```
`get_actions` lista solo pares completos (`category` + `blocks` + `blocks_neutro`) que ya tienen `id`.

`execute_action` recibe `action_id` y `arduino_id`. Par completo: encola normal, espera 1 s, neutro, espera 1 s y regresa. Par incompleto: omite (`omitido`). Sin secuencia: escribe el número al serial. Play de panel/estudio con `busy` se rechaza; el turno nunca se rechaza por ocupado. `GET runtime` es el estado del reproductor.
```

- [ ] **Step 2: Self-check the wording against the spec**

Confirm no claim that mai-core inserts neutros or that Stop sends a rest pose.

- [ ] **Step 3: Commit**

```bash
git add AGENTS.md .cursor/rules/robotics-actions.mdc docs/superpowers/plans/2026-10-14-sequence-neutro-runtime.md
git commit -m "Document pair playback and the robotics hardware queue."
```

Do not commit submodule pointer bumps unless the user asks.

---

## Self-review

Spec coverage:

| Spec item | Task |
|---|---|
| Category enum + labels | 1, 4, 5, 7 |
| Origin `blocks` + `blocks_neutro` | 1, 4, 5, 6 |
| Generate neutro algorithm + confirm replace | 4, 5 |
| Canonical `id`, overwrite keeps `id` | 1 (existing ingest) |
| Legacy list / not catalog / not panel | 1, 7 |
| Turn queue 1n, wait, 1neutro, wait, 2n… | 2 |
| `executeAction` returns after enqueue | 2 |
| Incomplete omit / unknown serial | 2 |
| Panel play one phase, busy error | 2, 3, 7 |
| Studio coupled play respects busy | 5 |
| Stop clears phase + wait + queue | 2, 7 |
| `GET /sequence/runtime` | 2, 3, 7 |
| Poll 500 ms / 3 s, sin estado | 7 |
| Importer rejects incomplete row | 6 |
| mai-core unchanged | constraints + Task 2 double-call |
| Chain API kept | 3, 7 (UI only) |
| No extra neutro on Stop | 2 |
| Arduino missing skips step | 2 |

Placeholder scan: none. Types: `enqueue_turn_pair`, `start_user_playback`, `get_runtime`, `WAIT_SECONDS`, `is_complete_pair`, `generate_neutro`, `blocksNeutro` (TS importer) vs `blocks_neutro` (JSON).
