# Cajón de cola en hardware Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show the robot queue live in every admin page: auto-open a drawer on a turn streak, list Normal / wait / Neutro with remaining time and current servo blocks, and Stop from one place.

**Architecture:** `PlaybackQueue.snapshot()` already feeds `GET /sequence/runtime`. Add `duration_ms`, `remaining_ms`, and current `blocks`/`fired` there. Angular `HardwareRuntimeService` polls from `admin-shell`, applies auto-open rules, and owns the overlay drawer. Control panel drops **En hardware** and reads `busy` from the same service. Gateway stays a transparent proxy. The turn does not change.

**Tech Stack:** Python 3.13 + pydantic + pytest (`pba-ms-robotics`); Angular 21 + Vitest (`pmas-web-main`). Gateway unchanged.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-27-turn-runtime-drawer-design.md`.
- Do not change `executeAction`, `getActions`, `_fire_blocks`, `declarePoema`, or `{ reply, fuente, movimientos }`.
- `espera` duration is `round(wait_seconds * 1000)` (production `WAIT_SECONDS` is `1.0` → 1000 ms).
- Gesture `duration_ms` is `round(max(inicio) * 1000)`; empty blocks → 0. Do not use `dur` for the step clock.
- `fired` is `elapsed_s >= inicio` from the start of that step.
- Auto-open only when a **turno streak** starts (`busy && source === 'turno'` and the previous snapshot was not). Manual close during a streak suppresses auto-open until the streak ends.
- Overlay only. Do not reflow the studio iframe. z-index above nav (`z-50` / `z-[55]`), below LAN modal (`z-[60]`).
- Edit only the owning repo. No worktree: Compose bind-mounts `./pba-ms-robotics` and `./pmas-web-main`.
- Do not add a gateway DTO.

---

## File structure

| File | Responsibility |
|---|---|
| `pba-ms-robotics/src/sequence/interfaces/sequence_interface.py` | `RuntimeBlockPublic`; extra fields on `QueueStepPublic` |
| `pba-ms-robotics/src/sequence/playback_queue.py` | Step clock, `step_duration_ms`, public snapshot |
| `pba-ms-robotics/tests/test_playback_queue.py` | Duration, remaining, blocks, fired, Stop idle |
| `pmas-web-main/src/app/core/services/hardware-runtime.ts` | Types, `applyRuntimeTick` / `applyManualClose`, poll + Stop |
| `pmas-web-main/src/app/core/services/hardware-runtime.spec.ts` | Auto-open and normalize tests |
| `pmas-web-main/src/app/components/hardware-runtime-drawer/hardware-runtime-drawer.ts` | FAB + overlay |
| `pmas-web-main/src/app/components/hardware-runtime-drawer/hardware-runtime-drawer.html` | List, servos, Detener |
| `pmas-web-main/src/app/components/hardware-runtime-drawer/hardware-runtime-drawer.copy.spec.ts` | Spanish copy |
| `pmas-web-main/src/app/layouts/admin-shell/admin-shell.ts` | Start/stop poll |
| `pmas-web-main/src/app/layouts/admin-shell/admin-shell.html` | Mount drawer |
| `pmas-web-main/src/app/pages/control-panel/control-panel.ts` | Shared service; no own poll |
| `pmas-web-main/src/app/pages/control-panel/control-panel.html` | Remove En hardware section |
| `pmas-web-main/src/app/pages/control-panel/control-panel.copy.spec.ts` | En hardware / Detener moved off this page |

---

### Task 1: Snapshot duration, remaining, and current blocks

**Files:**
- Modify: `pba-ms-robotics/src/sequence/interfaces/sequence_interface.py`
- Modify: `pba-ms-robotics/src/sequence/playback_queue.py`
- Modify: `pba-ms-robotics/tests/test_playback_queue.py`

**Interfaces:**
- Consumes: existing `QueueStep(id, name, mode, source, blocks)`, `WAIT_SECONDS`, `PlaybackQueue.snapshot() -> RuntimeSnapshot`.
- Produces: `step_duration_ms(step: QueueStep, wait_seconds: float = WAIT_SECONDS) -> int`. `RuntimeBlockPublic(nombre, pca, servo, inicio, dur, pos, vel, fired: bool)`. `QueueStepPublic` gains `duration_ms: int = 0`, `remaining_ms: int | None = None`, `blocks: list[RuntimeBlockPublic] | None = None`. Current step always has `remaining_ms: int` and `blocks: list` (empty on espera). Queue items leave `remaining_ms` and `blocks` as `None`.

- [ ] **Step 1: Write the failing snapshot tests**

Append to `pba-ms-robotics/tests/test_playback_queue.py` (keep existing tests). Extend the existing imports:

```python
from src.sequence.interfaces.sequence_interface import MotionBlock, SequencePlaybackPayload
from src.sequence.playback_queue import WAIT_SECONDS, PlaybackQueue, QueueStep, step_duration_ms
```

Keep the current `SequencePlaybackPayload` import line; add `MotionBlock` to that import. Replace the `WAIT_SECONDS`-only import with the line above.

```python
def _block(inicio: float, nombre: str = "P0_S0") -> MotionBlock:
    return MotionBlock(
        arduino_id=0,
        pca=0,
        servo=0,
        inicio=inicio,
        dur=2.0,
        pos=100,
        vel=5,
        nombre=nombre,
    )


def test_espera_duration_is_wait_seconds_in_ms():
    step = QueueStep(id=1, name="saludo", mode="espera", source="turno")
    assert step_duration_ms(step, 1.0) == 1000
    assert step_duration_ms(step, WAIT_SECONDS) == 1000


def test_gesture_duration_is_max_inicio_ms():
    step = QueueStep(
        id=1,
        name="saludo",
        mode="normal",
        source="turno",
        blocks=[_block(0.0, "a"), _block(1.5, "b")],
    )
    assert step_duration_ms(step) == 1500
    empty = QueueStep(id=1, name="x", mode="neutro", source="turno", blocks=[])
    assert step_duration_ms(empty) == 0


def test_current_has_blocks_and_queue_does_not(tmp_path: Path):
    service = ready_service(tmp_path, wait=0.3)

    def slow_fire(blocks, stop_event):
        stop_event.wait(0.4)

    service._fire_blocks = slow_fire
    ActionService(sequence_service=service).execute_action(1, 0)
    snap = service.get_runtime()
    assert snap.current is not None
    assert snap.current.mode == "normal"
    assert snap.current.duration_ms == 0
    assert snap.current.remaining_ms is not None
    assert snap.current.blocks is not None
    assert [item.nombre for item in snap.current.blocks] == ["P0_S0"]
    espera = snap.queue[0]
    assert espera.mode == "espera"
    assert espera.duration_ms == 300
    assert espera.blocks is None
    assert espera.remaining_ms is None
    service.stop_playback()
    wait_idle(service)


def test_espera_current_has_empty_blocks(tmp_path: Path):
    service = ready_service(tmp_path, wait=0.4)
    service._fire_blocks = lambda blocks, stop_event: None
    ActionService(sequence_service=service).execute_action(1, 0)
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        snap = service.get_runtime()
        if snap.current is not None and snap.current.mode == "espera":
            assert snap.current.blocks == []
            assert snap.current.duration_ms == 400
            service.stop_playback()
            wait_idle(service)
            return
        time.sleep(0.02)
    raise AssertionError(service.get_runtime().model_dump())


def test_remaining_drops_during_slow_step():
    def slow_fire(blocks, stop_event):
        stop_event.wait(0.3)

    queue = PlaybackQueue(slow_fire, wait_seconds=1.0)
    queue.enqueue(
        [
            QueueStep(
                id=1,
                name="saludo",
                mode="normal",
                source="turno",
                blocks=[_block(0.5, "late")],
            )
        ],
        reject_if_busy=False,
    )
    time.sleep(0.12)
    snap = queue.snapshot()
    assert snap.current is not None
    assert snap.current.duration_ms == 500
    assert 0 < snap.current.remaining_ms < 500
    queue.stop()


def test_fired_follows_elapsed_vs_inicio():
    def slow_fire(blocks, stop_event):
        stop_event.wait(0.35)

    queue = PlaybackQueue(slow_fire, wait_seconds=1.0)
    queue.enqueue(
        [
            QueueStep(
                id=1,
                name="saludo",
                mode="normal",
                source="turno",
                blocks=[_block(0.0, "early"), _block(0.2, "late")],
            )
        ],
        reject_if_busy=False,
    )
    time.sleep(0.08)
    first = queue.snapshot()
    names = {item.nombre: item.fired for item in first.current.blocks}
    assert names["early"] is True
    assert names["late"] is False
    time.sleep(0.2)
    second = queue.snapshot()
    later = {item.nombre: item.fired for item in second.current.blocks}
    assert later["early"] is True
    assert later["late"] is True
    queue.stop()


# Stop → idle is already `test_stop_clears_queue_and_wait`. Do not duplicate it.
```

- [ ] **Step 2: Run tests to verify they fail**

From the launcher:

```bash
docker compose exec pba-ms-robotics pytest tests/test_playback_queue.py::test_espera_duration_is_wait_seconds_in_ms tests/test_playback_queue.py::test_gesture_duration_is_max_inicio_ms -v
```

Expected: FAIL with `ImportError` or `AttributeError` for `step_duration_ms`.

- [ ] **Step 3: Add models**

In `pba-ms-robotics/src/sequence/interfaces/sequence_interface.py`, above `QueueStepPublic`:

```python
class RuntimeBlockPublic(BaseModel):
    nombre: str
    pca: int
    servo: int
    inicio: float
    dur: float
    pos: int
    vel: int
    fired: bool
```

Replace `QueueStepPublic` with:

```python
class QueueStepPublic(BaseModel):
    id: int | None = None
    name: str
    mode: Literal["normal", "neutro", "espera"]
    source: Literal["turno", "panel", "estudio"]
    duration_ms: int = 0
    remaining_ms: int | None = None
    blocks: list[RuntimeBlockPublic] | None = None
```

- [ ] **Step 4: Implement duration and snapshot clock**

In `pba-ms-robotics/src/sequence/playback_queue.py`, import `RuntimeBlockPublic`. Add:

```python
def step_duration_ms(step: QueueStep, wait_seconds: float = WAIT_SECONDS) -> int:
    if step.mode == "espera":
        return int(round(wait_seconds * 1000))
    blocks = step.blocks or []
    if not blocks:
        return 0
    return int(round(max(block.inicio for block in blocks) * 1000))
```

On `PlaybackQueue.__init__`, set `self._step_started: float | None = None`.

In `_pop`, after `self._current = step`, set `self._step_started = time.monotonic()`.

In `stop`, also set `self._step_started = None` in both lock blocks where `_current` is cleared.

In `_run` `finally`, when clearing `_current`, set `self._step_started = None`.

Replace `_public` and use it from `snapshot` with elapsed:

```python
    def snapshot(self) -> RuntimeSnapshot:
        with self._lock:
            current_step = self._current
            pending = list(self._queue)
            started = self._step_started
            peeked = False
            if current_step is None and pending:
                current_step = pending[0]
                pending = pending[1:]
                peeked = True
            elapsed = 0.0 if peeked or started is None or current_step is None else time.monotonic() - started
            current = self._public(current_step, for_current=True, elapsed_s=elapsed)
            queue = [
                item
                for item in (self._public(step, for_current=False, elapsed_s=0.0) for step in pending)
                if item is not None
            ]
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

    def _public(
        self,
        step: QueueStep | None,
        *,
        for_current: bool,
        elapsed_s: float,
    ) -> QueueStepPublic | None:
        if step is None:
            return None
        duration = step_duration_ms(step, self.wait_seconds)
        remaining: int | None = None
        blocks = None
        if for_current:
            remaining = max(0, min(duration, duration - int(round(elapsed_s * 1000))))
            if step.mode == "espera" or not step.blocks:
                blocks = []
            else:
                blocks = [
                    RuntimeBlockPublic(
                        nombre=block.nombre,
                        pca=block.pca,
                        servo=block.servo,
                        inicio=block.inicio,
                        dur=block.dur,
                        pos=block.pos,
                        vel=block.vel,
                        fired=elapsed_s >= block.inicio,
                    )
                    for block in step.blocks
                ]
        return QueueStepPublic(
            id=step.id,
            name=step.name,
            mode=step.mode,  # type: ignore[arg-type]
            source=step.source,  # type: ignore[arg-type]
            duration_ms=duration,
            remaining_ms=remaining,
            blocks=blocks,
        )
```

Do not change `_fire_blocks` or `enqueue_turn_pair`.

- [ ] **Step 5: Run the playback tests**

```bash
docker compose exec pba-ms-robotics pytest tests/test_playback_queue.py -v
```

Expected: PASS (existing tests plus the new ones). If `test_user_play_while_busy_leaves_queue` fails because `model_dump()` now includes `duration_ms`, that is fine as long as before/after still match. Do not weaken that assertion.

- [ ] **Step 6: Commit in `pba-ms-robotics`**

```bash
git add src/sequence/interfaces/sequence_interface.py src/sequence/playback_queue.py tests/test_playback_queue.py
git commit -m "$(cat <<'EOF'
Expose step duration and current blocks on the runtime snapshot.

The admin drawer needs remaining time and servo fired flags without changing how the queue plays.
EOF
)"
```

---

### Task 2: Hardware runtime helpers and poll service

**Files:**
- Create: `pmas-web-main/src/app/core/services/hardware-runtime.ts`
- Create: `pmas-web-main/src/app/core/services/hardware-runtime.spec.ts`

**Interfaces:**
- Consumes: `GET ${GATEWAY_URL}/sequence/runtime`, `POST ${GATEWAY_URL}/sequence/stop`. Snapshot JSON from Task 1.
- Produces: types `RuntimeBlock`, `RuntimeStep`, `RuntimeSnapshot`, `RuntimeViewState`. `IDLE_RUNTIME`. `isTurnoStreak(snap)`. `normalizeSnapshot(raw)`. `applyRuntimeTick(state, incoming)`. `applyManualClose(state)`. `formatDurationMs(ms)`. `HardwareRuntimeService` with `runtime`, `drawerOpen`, `unreachable`, `stopError`, `playLocked`, `startPolling()`, `stopPolling()`, `toggleDrawer()`, `closeDrawer()`, `openDrawer()`, `stopHardware()`.

- [ ] **Step 1: Write the failing helper tests**

Create `pmas-web-main/src/app/core/services/hardware-runtime.spec.ts`:

```ts
import { describe, expect, it } from 'vitest';
import {
  IDLE_RUNTIME,
  applyManualClose,
  applyRuntimeTick,
  formatDurationMs,
  isTurnoStreak,
  normalizeSnapshot,
  RuntimeSnapshot,
  RuntimeViewState,
} from './hardware-runtime';

const turnoBusy: RuntimeSnapshot = {
  busy: true,
  source: 'turno',
  current: {
    id: 1,
    name: 'asentir',
    mode: 'normal',
    source: 'turno',
    duration_ms: 0,
    remaining_ms: 0,
    blocks: [],
  },
  queue: [],
};

const panelBusy: RuntimeSnapshot = {
  ...turnoBusy,
  source: 'panel',
  current: { ...turnoBusy.current!, source: 'panel' },
};

const idleState: RuntimeViewState = {
  runtime: IDLE_RUNTIME,
  drawerOpen: false,
  dismissedThisStreak: false,
};

describe('isTurnoStreak', () => {
  it('is true only when busy and source is turno', () => {
    expect(isTurnoStreak(turnoBusy)).toBe(true);
    expect(isTurnoStreak(panelBusy)).toBe(false);
    expect(isTurnoStreak(IDLE_RUNTIME)).toBe(false);
  });
});

describe('applyRuntimeTick', () => {
  it('opens on idle to turno', () => {
    const next = applyRuntimeTick(idleState, turnoBusy);
    expect(next.drawerOpen).toBe(true);
    expect(next.dismissedThisStreak).toBe(false);
  });

  it('does not open on panel or estudio', () => {
    expect(applyRuntimeTick(idleState, panelBusy).drawerOpen).toBe(false);
    expect(
      applyRuntimeTick(idleState, { ...panelBusy, source: 'estudio' }).drawerOpen,
    ).toBe(false);
  });

  it('opens when source becomes turno while already busy', () => {
    const fromPanel: RuntimeViewState = {
      runtime: panelBusy,
      drawerOpen: false,
      dismissedThisStreak: false,
    };
    expect(applyRuntimeTick(fromPanel, turnoBusy).drawerOpen).toBe(true);
  });

  it('does not reopen during the same turno streak after a manual close', () => {
    const open = applyRuntimeTick(idleState, turnoBusy);
    const closed = applyManualClose(open);
    expect(closed.drawerOpen).toBe(false);
    expect(closed.dismissedThisStreak).toBe(true);
    const still = applyRuntimeTick(closed, turnoBusy);
    expect(still.drawerOpen).toBe(false);
  });

  it('opens on the next turno streak after idle', () => {
    const closed = applyManualClose(applyRuntimeTick(idleState, turnoBusy));
    const afterIdle = applyRuntimeTick(closed, IDLE_RUNTIME);
    expect(afterIdle.dismissedThisStreak).toBe(false);
    expect(applyRuntimeTick(afterIdle, turnoBusy).drawerOpen).toBe(true);
  });
});

describe('normalizeSnapshot', () => {
  it('fills missing blocks as an empty list on current', () => {
    const raw = {
      busy: true,
      source: 'turno',
      current: { id: 1, name: 'x', mode: 'espera', source: 'turno', duration_ms: 1000 },
      queue: [{ id: 1, name: 'x', mode: 'neutro', source: 'turno', duration_ms: 0 }],
    };
    const snap = normalizeSnapshot(raw);
    expect(snap.current?.blocks).toEqual([]);
    expect(snap.current?.remaining_ms).toBe(0);
    expect(snap.queue[0].blocks).toEqual([]);
  });
});

describe('formatDurationMs', () => {
  it('shows one decimal under ten seconds', () => {
    expect(formatDurationMs(1500)).toBe('1.5 s');
    expect(formatDurationMs(10000)).toBe('10 s');
  });
});
```

- [ ] **Step 2: Run the spec to verify it fails**

```bash
cd pmas-web-main && npx vitest run src/app/core/services/hardware-runtime.spec.ts
```

Expected: FAIL resolving `./hardware-runtime`.

- [ ] **Step 3: Implement helpers and the service**

Create `pmas-web-main/src/app/core/services/hardware-runtime.ts`:

```ts
import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { GATEWAY_URL } from '../constants/gateway';

export interface RuntimeBlock {
  nombre: string;
  pca: number;
  servo: number;
  inicio: number;
  dur: number;
  pos: number;
  vel: number;
  fired: boolean;
}

export interface RuntimeStep {
  id: number | null;
  name: string;
  mode: 'normal' | 'neutro' | 'espera';
  source: 'turno' | 'panel' | 'estudio';
  duration_ms: number;
  remaining_ms: number;
  blocks: RuntimeBlock[];
}

export interface RuntimeSnapshot {
  busy: boolean;
  source: 'turno' | 'panel' | 'estudio' | null;
  current: RuntimeStep | null;
  queue: RuntimeStep[];
}

export interface RuntimeViewState {
  runtime: RuntimeSnapshot;
  drawerOpen: boolean;
  dismissedThisStreak: boolean;
}

export const IDLE_RUNTIME: RuntimeSnapshot = {
  busy: false,
  source: null,
  current: null,
  queue: [],
};

function asStep(raw: Partial<RuntimeStep> | null | undefined): RuntimeStep | null {
  if (!raw || typeof raw.name !== 'string') return null;
  const mode = raw.mode === 'neutro' || raw.mode === 'espera' ? raw.mode : 'normal';
  const source = raw.source === 'panel' || raw.source === 'estudio' ? raw.source : 'turno';
  return {
    id: raw.id ?? null,
    name: raw.name,
    mode,
    source,
    duration_ms: Number(raw.duration_ms ?? 0),
    remaining_ms: Number(raw.remaining_ms ?? 0),
    blocks: Array.isArray(raw.blocks) ? raw.blocks : [],
  };
}

export function normalizeSnapshot(raw: Partial<RuntimeSnapshot> | null | undefined): RuntimeSnapshot {
  if (!raw) return IDLE_RUNTIME;
  return {
    busy: Boolean(raw.busy),
    source: raw.source === 'turno' || raw.source === 'panel' || raw.source === 'estudio' ? raw.source : null,
    current: asStep(raw.current),
    queue: Array.isArray(raw.queue) ? raw.queue.map((item) => asStep(item)).filter((item): item is RuntimeStep => item !== null) : [],
  };
}

export function isTurnoStreak(snap: Pick<RuntimeSnapshot, 'busy' | 'source'>): boolean {
  return snap.busy === true && snap.source === 'turno';
}

export function applyRuntimeTick(state: RuntimeViewState, incoming: RuntimeSnapshot): RuntimeViewState {
  const next = normalizeSnapshot(incoming);
  const dismissed = isTurnoStreak(next) ? state.dismissedThisStreak : false;
  const autoOpen = isTurnoStreak(next) && !isTurnoStreak(state.runtime) && !dismissed;
  return {
    runtime: next,
    drawerOpen: autoOpen ? true : state.drawerOpen,
    dismissedThisStreak: dismissed,
  };
}

export function applyManualClose(state: RuntimeViewState): RuntimeViewState {
  return {
    ...state,
    drawerOpen: false,
    dismissedThisStreak: isTurnoStreak(state.runtime) ? true : state.dismissedThisStreak,
  };
}

export function formatDurationMs(ms: number): string {
  const value = Math.max(0, ms);
  const seconds = value / 1000;
  if (seconds < 10) return `${seconds.toFixed(1)} s`;
  return `${Math.round(seconds)} s`;
}

@Injectable({ providedIn: 'root' })
export class HardwareRuntimeService {
  private readonly http = inject(HttpClient);
  private timer: ReturnType<typeof setTimeout> | null = null;
  private polling = false;

  readonly runtime = signal<RuntimeSnapshot>(IDLE_RUNTIME);
  readonly drawerOpen = signal(false);
  readonly unreachable = signal(false);
  readonly stopError = signal<string | null>(null);
  private dismissedThisStreak = false;

  readonly playLocked = computed(() => this.unreachable() || this.runtime().busy);

  startPolling(): void {
    if (this.polling) return;
    this.polling = true;
    this.poll();
  }

  stopPolling(): void {
    this.polling = false;
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
  }

  openDrawer(): void {
    this.drawerOpen.set(true);
  }

  closeDrawer(): void {
    const next = applyManualClose({
      runtime: this.runtime(),
      drawerOpen: this.drawerOpen(),
      dismissedThisStreak: this.dismissedThisStreak,
    });
    this.drawerOpen.set(false);
    this.dismissedThisStreak = next.dismissedThisStreak;
  }

  toggleDrawer(): void {
    if (this.drawerOpen()) this.closeDrawer();
    else this.openDrawer();
  }

  stopHardware(): void {
    this.stopError.set(null);
    this.http.post(`${GATEWAY_URL}/sequence/stop`, {}).subscribe({
      next: () => {
        this.stopError.set(null);
        this.poll();
      },
      error: () => this.stopError.set('No se pudo detener'),
    });
  }

  private poll(): void {
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    this.http.get<Partial<RuntimeSnapshot>>(`${GATEWAY_URL}/sequence/runtime`).subscribe({
      next: (res) => {
        this.unreachable.set(false);
        const next = applyRuntimeTick(
          {
            runtime: this.runtime(),
            drawerOpen: this.drawerOpen(),
            dismissedThisStreak: this.dismissedThisStreak,
          },
          normalizeSnapshot(res),
        );
        this.runtime.set(next.runtime);
        this.drawerOpen.set(next.drawerOpen);
        this.dismissedThisStreak = next.dismissedThisStreak;
        this.timer = setTimeout(() => this.poll(), next.runtime.busy || next.drawerOpen ? 500 : 3000);
      },
      error: () => {
        this.unreachable.set(true);
        this.timer = setTimeout(() => this.poll(), 500);
      },
    });
  }
}
```

- [ ] **Step 4: Run the helper tests**

```bash
cd pmas-web-main && npx vitest run src/app/core/services/hardware-runtime.spec.ts
```

Expected: PASS.

- [ ] **Step 5: Commit in `pmas-web-main`**

```bash
git add src/app/core/services/hardware-runtime.ts src/app/core/services/hardware-runtime.spec.ts
git commit -m "$(cat <<'EOF'
Add a shared hardware runtime poll and auto-open rules.

The shell drawer and control panel must see the same queue without reconstructing it from chat.
EOF
)"
```

---

### Task 3: Overlay drawer and fixed button in admin-shell

**Files:**
- Create: `pmas-web-main/src/app/components/hardware-runtime-drawer/hardware-runtime-drawer.ts`
- Create: `pmas-web-main/src/app/components/hardware-runtime-drawer/hardware-runtime-drawer.html`
- Create: `pmas-web-main/src/app/components/hardware-runtime-drawer/hardware-runtime-drawer.copy.spec.ts`
- Modify: `pmas-web-main/src/app/layouts/admin-shell/admin-shell.ts`
- Modify: `pmas-web-main/src/app/layouts/admin-shell/admin-shell.html`

**Interfaces:**
- Consumes: `HardwareRuntimeService` from Task 2. `phaseLabel` and `sourceHint` from `pmas-web-main/src/app/pages/control-panel/panel-kpis.ts`. `environment.compactMode`.
- Produces: selector `app-hardware-runtime-drawer`. Visible copy: `En hardware`, `Detener`, `Nada pendiente.`, `No hay estado del robot. Detener sigue disponible.` Overlay `z-[58]`, FAB `z-[57]`.

- [ ] **Step 1: Write the failing copy spec**

Create `pmas-web-main/src/app/components/hardware-runtime-drawer/hardware-runtime-drawer.copy.spec.ts`:

```ts
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const html = readFileSync(resolve(import.meta.dirname, 'hardware-runtime-drawer.html'), 'utf8');
const ts = readFileSync(resolve(import.meta.dirname, 'hardware-runtime-drawer.ts'), 'utf8');

describe('hardware runtime drawer copy', () => {
  it('is the Spanish hardware queue', () => {
    expect(html).toContain('En hardware');
    expect(html).toContain('Detener');
    expect(html).toContain('Nada pendiente.');
    expect(html).toContain('No hay estado del robot. Detener sigue disponible.');
    expect(html).not.toContain('System Override');
    expect(html).not.toContain('Execution Log');
  });

  it('always offers Detener and never uses arbitrary px text', () => {
    expect(html).toContain('stopHardware()');
    expect(html).not.toMatch(/stopHardware\(\)"[\s\S]*disabled/);
    expect(html).not.toMatch(/text-\[\d+px\]/);
    expect(ts).toContain('HardwareRuntimeService');
  });
});
```

- [ ] **Step 2: Run copy spec to verify it fails**

```bash
cd pmas-web-main && npx vitest run src/app/components/hardware-runtime-drawer/hardware-runtime-drawer.copy.spec.ts
```

Expected: FAIL (file not found).

- [ ] **Step 3: Implement the drawer**

Create `pmas-web-main/src/app/components/hardware-runtime-drawer/hardware-runtime-drawer.ts`:

```ts
import { Component, inject } from '@angular/core';
import { environment } from '../../../environments/environment';
import { phaseLabel, sourceHint } from '../../pages/control-panel/panel-kpis';
import { formatDurationMs, HardwareRuntimeService } from '../../core/services/hardware-runtime';

@Component({
  selector: 'app-hardware-runtime-drawer',
  templateUrl: './hardware-runtime-drawer.html',
})
export class HardwareRuntimeDrawer {
  readonly runtime = inject(HardwareRuntimeService);
  readonly compact = environment.compactMode;
  readonly phaseLabel = phaseLabel;
  readonly sourceHint = sourceHint;
  readonly formatDurationMs = formatDurationMs;
}
```

Create `pmas-web-main/src/app/components/hardware-runtime-drawer/hardware-runtime-drawer.html`:

```html
<button
  type="button"
  (click)="runtime.toggleDrawer()"
  class="fixed z-[57] right-4 flex size-12 items-center justify-center rounded-full border border-outline shadow-lg cursor-pointer"
  [class]="runtime.runtime().busy
    ? 'bg-secondary text-on-secondary'
    : 'bg-surface text-on-surface'"
  [class.bottom-20]="compact"
  [class.md:bottom-6]="compact"
  [class.bottom-6]="!compact"
  aria-label="En hardware">
  <span class="material-symbols-outlined" style="font-size: 1.5rem;">memory</span>
</button>

@if (runtime.drawerOpen()) {
  <div class="fixed inset-0 z-[58] flex justify-end items-end md:items-stretch" role="dialog" aria-modal="true" aria-label="En hardware">
    <div class="absolute inset-0 bg-rail/50" (click)="runtime.closeDrawer()"></div>
    <div
      class="relative z-10 flex flex-col w-full md:w-[22rem] max-h-[70dvh] md:max-h-none md:h-full
             bg-surface text-on-surface border-t md:border-t-0 md:border-l border-outline
             rounded-t-2xl md:rounded-none"
      [class.mb-[4.5rem]]="compact"
      [class.md:mb-0]="compact">
      <header class="flex items-center gap-2 px-4 py-3 border-b border-outline bg-surface-container-high shrink-0">
        <span class="material-symbols-outlined text-secondary" style="font-size: 1.25rem;">memory</span>
        <div class="min-w-0 flex-1">
          <h2 class="font-headline text-base font-bold tracking-tight">En hardware</h2>
          <p class="text-xs text-on-surface-variant truncate">{{ sourceHint(runtime.runtime().source) }}</p>
        </div>
        <button
          type="button"
          (click)="runtime.stopHardware()"
          class="flex min-h-10 items-center gap-1.5 py-2 px-3 rounded-lg bg-error text-on-error text-sm font-semibold cursor-pointer">
          <span class="material-symbols-outlined" style="font-size: 1.1rem;">stop</span>
          Detener
        </button>
        <button type="button" (click)="runtime.closeDrawer()" class="p-2 rounded-lg hover:bg-surface-container cursor-pointer" aria-label="Cerrar">
          <span class="material-symbols-outlined" style="font-size: 1.25rem;">close</span>
        </button>
      </header>

      <div class="flex-1 min-h-0 overflow-y-auto p-4 space-y-3 text-sm">
        @if (runtime.stopError(); as err) {
          <p class="rounded-lg bg-error-container px-3 py-2 text-on-error-container">{{ err }}</p>
        }
        @if (runtime.unreachable()) {
          <p class="rounded-lg bg-error-container px-3 py-2 text-on-error-container">No hay estado del robot. Detener sigue disponible.</p>
        } @else {
          @if (!runtime.runtime().current && runtime.runtime().queue.length === 0) {
            <p class="text-on-surface-variant">Nada pendiente.</p>
          }
          @if (runtime.runtime().current; as current) {
            <article class="rounded-xl border border-secondary/40 bg-secondary/10 p-3 space-y-2">
              <p class="font-semibold">{{ current.name }} · {{ phaseLabel(current.mode) }}</p>
              <p class="text-xs text-on-surface-variant">{{ formatDurationMs(current.remaining_ms) }} / {{ formatDurationMs(current.duration_ms) }}</p>
              @if (current.mode !== 'espera' && current.blocks.length > 0) {
                <ul class="space-y-1 text-xs">
                  @for (block of current.blocks; track $index) {
                    <li [class]="block.fired ? 'text-on-surface' : 'text-on-surface-variant'">
                      {{ block.nombre }} · pca {{ block.pca }} · servo {{ block.servo }} · pos {{ block.pos }} · {{ formatDurationMs(block.dur * 1000) }}
                    </li>
                  }
                </ul>
              }
            </article>
          }
          @for (step of runtime.runtime().queue; track $index) {
            <article class="rounded-xl border border-outline p-3">
              <p>{{ step.name }} · {{ phaseLabel(step.mode) }}</p>
              <p class="text-xs text-on-surface-variant">{{ formatDurationMs(step.duration_ms) }}</p>
            </article>
          }
        }
      </div>
    </div>
  </div>
}
```

FAB compact classes: keep the button above the bottom nav on small screens (`bottom-20`) and `md:bottom-6` once the nav is the left rail.

- [ ] **Step 4: Mount it on the admin shell**

In `admin-shell.ts`:

- Import `HardwareRuntimeDrawer` and `HardwareRuntimeService`.
- Add `HardwareRuntimeDrawer` to `imports`.
- `private readonly hardwareRuntime = inject(HardwareRuntimeService);`
- In `ngOnInit`, after the existing setup: `this.hardwareRuntime.startPolling();`
- Implement `ngOnDestroy` (add `OnDestroy` to the class): `this.hardwareRuntime.stopPolling();`

In `admin-shell.html`, after `<app-lan-share-modal />`:

```html
<app-hardware-runtime-drawer />
```

- [ ] **Step 5: Run copy spec**

```bash
cd pmas-web-main && npx vitest run src/app/components/hardware-runtime-drawer/hardware-runtime-drawer.copy.spec.ts src/app/core/services/hardware-runtime.spec.ts
```

Expected: PASS.

- [ ] **Step 6: Commit in `pmas-web-main`**

```bash
git add src/app/components/hardware-runtime-drawer src/app/layouts/admin-shell/admin-shell.ts src/app/layouts/admin-shell/admin-shell.html
git commit -m "$(cat <<'EOF'
Show the hardware queue as a shell overlay with Stop.

Operators need the turn timeline on chat, vision, and sequences, not only on the control panel.
EOF
)"
```

---

### Task 4: Control panel uses the shared service

**Files:**
- Modify: `pmas-web-main/src/app/pages/control-panel/control-panel.ts`
- Modify: `pmas-web-main/src/app/pages/control-panel/control-panel.html`
- Modify: `pmas-web-main/src/app/pages/control-panel/control-panel.copy.spec.ts`

**Interfaces:**
- Consumes: `HardwareRuntimeService.runtime`, `unreachable`, `playLocked` from Task 2.
- Produces: no `pollRuntime`, no `stopHardware`, no local `runtime` / `runtimeTimer`. KPI cards still use `panelKpis`. Play/Neutro still call `POST /sequence/play`.

- [ ] **Step 1: Update the copy spec to fail**

In `control-panel.copy.spec.ts` replace the two tests that mention En hardware / Detener with:

```ts
  it('is a Spanish operator dashboard', () => {
    expect(html).toContain('Panel de control');
    expect(html).toContain('Registro');
    expect(html).not.toContain('En hardware');
    expect(html).toContain('kpis().estado');
    expect(html).toContain('kpis().origen');
    expect(html).toContain('kpis().secuencias');
    expect(html).toContain('kpis().ultimoEvento');
    expect(html).not.toContain('System Override');
    expect(html).not.toContain('0x4F22-ALPHA');
    expect(html).not.toContain('Robotic Control');
    expect(html).not.toContain('Execution Log');
    expect(html).not.toContain('Uptime');
    expect(html).not.toContain('Signal');
  });

  it('keeps the busy lock and leaves Detener to the shell drawer', () => {
    expect(html).toMatch(/executePhase\(sequence\.name, 'normal'\)[\s\S]*\[disabled\]="playLocked\(\)"/);
    expect(html).toMatch(/executePhase\(sequence\.name, 'neutro'\)[\s\S]*\[disabled\]="playLocked\(\)"/);
    expect(html).not.toContain('stopHardware()');
    expect(html).not.toContain('En hardware');
  });
```

- [ ] **Step 2: Run copy spec to verify it fails**

```bash
cd pmas-web-main && npx vitest run src/app/pages/control-panel/control-panel.copy.spec.ts
```

Expected: FAIL on `not.toContain('En hardware')` and/or `stopHardware()`.

- [ ] **Step 3: Wire the panel to the service and delete the recuadro**

In `control-panel.ts`:

- Import `HardwareRuntimeService`.
- Remove `RuntimeStep`, `RuntimeSnapshot`, `IDLE_RUNTIME`.
- `hardware = inject(HardwareRuntimeService);`
- Replace local `runtime` / `runtimeUnreachable` / `playLocked` with:

```ts
  playLocked = computed(() => this.hardware.playLocked());
```

- In `kpis`:

```ts
      runtimeUnreachable: this.hardware.unreachable(),
      busy: this.hardware.runtime().busy,
      source: this.hardware.runtime().source,
```

- Remove `runtimeTimer`, `pollRuntime`, `stopHardware`.
- `ngOnInit`: delete `this.pollRuntime();`
- `ngOnDestroy`: delete the `runtimeTimer` cleanup.
- In `executePhase` `next:` delete `this.pollRuntime();` (the shell already polls). Keep the ack log.

In `control-panel.html`, delete the entire first `<section>` inside `xl:col-span-1` whose header is **En hardware** (the Detener button and the current/queue copy). Leave **Registro** as the only section in that column.

Keep `sourceHint` / `phaseLabel` imports only if the remaining template still uses them. If not, drop those imports.

- [ ] **Step 4: Run panel and drawer copy tests**

```bash
cd pmas-web-main && npx vitest run src/app/pages/control-panel/control-panel.copy.spec.ts src/app/pages/control-panel/panel-kpis.spec.ts src/app/components/hardware-runtime-drawer/hardware-runtime-drawer.copy.spec.ts src/app/core/services/hardware-runtime.spec.ts
```

Expected: PASS.

- [ ] **Step 5: Commit in `pmas-web-main`**

```bash
git add src/app/pages/control-panel/control-panel.ts src/app/pages/control-panel/control-panel.html src/app/pages/control-panel/control-panel.copy.spec.ts
git commit -m "$(cat <<'EOF'
Drop the control-panel hardware card in favor of the shell drawer.

Play still locks on busy; Stop lives in one overlay so sequences and chat see the same queue.
EOF
)"
```

---

### Task 5: Launcher submodule pointers

**Files:**
- Modify: launcher gitlinks for `pba-ms-robotics` and `pmas-web-main`

**Interfaces:**
- Consumes: Task 1 commit SHA in robotics, Task 2–4 SHAs in web-main.
- Produces: launcher `main` commit that records those SHAs. Do not add `ASENTIR NEUTRO 9.0.json`.

- [ ] **Step 1: Record submodule SHAs**

From the launcher, after Tasks 1–4 are committed in their repos:

```bash
git add pba-ms-robotics pmas-web-main
git status
git commit -m "$(cat <<'EOF'
Point robotics and web-main at the hardware queue drawer.

The snapshot now carries duration and current blocks; the admin shell shows them live.
EOF
)"
```

---

## Self-review

| Spec item | Task |
|---|---|
| Snapshot `duration_ms` / `remaining_ms` / current `blocks`+`fired` | 1 |
| Espera = wait_seconds ms; gesto = max(inicio) | 1 |
| `_fire_blocks` unchanged | 1 (explicit) |
| Gateway no DTO | none |
| Poll 500/3000, error 500 | 2 |
| Auto-open turno streak; dismiss; panel play no auto-open | 2 |
| Manual open shows panel/estudio | 2+3 (same snapshot) |
| Overlay, FAB, Detener, copy | 3 |
| Remove En hardware; playLocked from service | 4 |
| Stop = `POST /sequence/stop` | 2+3 |
| Tests listed in spec §6 | 1 and 2 |
| Import JSON / delete sequences | out of scope |
