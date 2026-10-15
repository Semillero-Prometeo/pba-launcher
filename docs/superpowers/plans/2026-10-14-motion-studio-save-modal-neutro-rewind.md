# Motion Studio save dialog, rewind neutro, and identity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Motion Studio saves through a dialog (name, description ≥ 10, category, Arduino), generates neutro as a rewind that undoes the gesture path, and shares PRODUCT/DESIGN identity with the operator shell.

**Architecture:** Keep the iframe in `pmas-web-motion-studio`. Python `generate_neutro` and JS `generateNeutroFrom` implement the same rewind. `local_sequences._normalize` and robotics `ingest_save` / `is_complete_pair` reject short descriptions. Tokens live in `editor.css`; PRODUCT.md and DESIGN.md at the launcher root are updated, not copied into the studio repo.

**Tech Stack:** Vanilla HTML/CSS/JS in the studio iframe; FastAPI + pytest in `pmas-web-motion-studio`; Python ingest in `pba-ms-robotics`; Markdown at launcher root.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-14-motion-studio-save-modal-neutro-rewind-design.md`.
- Sequence-neutro-runtime spec still governs JSON shape (`blocks` + `blocks_neutro` + `category`), six categories, and the turn queue (normal → 1 s → neutro → 1 s).
- Do not change `executeAction`, `getActions` signature, `declarePoema`, or `{ reply, fuente, movimientos }`.
- Do not edit auth, vision, mai-core, or Angular except if the studio iframe wrapper is broken.
- Do not rewrite `interfaz_record9_5_1.py`. Do not add a DESIGN.md inside `pmas-web-motion-studio`.
- Chrome `#0B2540` + `#eef2f6`. Canvas `#eef2f6`. Card `#f7fafc`. Emerald `#059669` only Neutro/ok. Cyan `#38bdf8` Play, Guardar, Gesto activo. Stop `#dc2626`. Type ≥ 12px labels / ≥ 14px body. No `#000f1d`, no `#10b981`, no `#ffffff`.
- Work on `feat/sequence-neutro-runtime`. Studio commits in `pmas-web-motion-studio`. Robotics commits in `pba-ms-robotics`. Docs in the launcher.

---

## File structure

| File | Responsibility |
|---|---|
| `pmas-web-motion-studio/src/neutro.py` | Pure rewind `generate_neutro`. |
| `pmas-web-motion-studio/tests/test_neutro.py` | Rewind contract. |
| `pmas-web-motion-studio/src/local_sequences.py` | Description ≥ 10 on disk save. |
| `pmas-web-motion-studio/tests/test_local_sequences.py` | Short description rejected. |
| `pmas-web-motion-studio/tests/test_app.py` | Toolbar order, dialog, no chrome fields. |
| `pmas-web-motion-studio/src/static/index.html` | Chrome, toolbar, `<dialog>`, fonts. |
| `pmas-web-motion-studio/src/static/editor.js` | Rewind JS, open/validate dialog, save. |
| `pmas-web-motion-studio/src/static/editor.css` | Identity tokens and chrome. |
| `pmas-web-motion-studio/tests/test_editor_css.py` | Token contract on CSS. |
| `pba-ms-robotics/src/sequence/ingest.py` | `ingest_save` + `is_complete_pair` description ≥ 10. |
| `pba-ms-robotics/tests/test_sequence_ingest.py` | Ingest and catalog rules. |
| `PRODUCT.md` / `DESIGN.md` | Studio is no longer a pending visual cut. |

---

### Task 1: Rewind `generate_neutro`

**Files:**
- Modify: `pmas-web-motion-studio/tests/test_neutro.py`
- Modify: `pmas-web-motion-studio/src/neutro.py`

**Interfaces:**
- Consumes: 7-tuples `[pca, servo, inicio, dur, pos, vel, nombre]`.
- Produces: `generate_neutro(blocks, existing=None, replace=False) -> list[list]`. Rest pos is `0`. `inicio' = T - (inicio + dur)` with `T = max(inicio + dur)`. If `existing` nonempty and `replace` is false: `ValueError("La pista neutra ya existe")`.

- [ ] **Step 1: Replace `tests/test_neutro.py` with rewind cases**

```python
import pytest
from src.neutro import generate_neutro


def test_same_servo_two_steps_rewinds_to_rest():
    blocks = [
        [0, 0, 0.0, 1, 200, 5, "a"],
        [0, 0, 1.0, 0.5, 400, 5, "b"],
    ]
    assert generate_neutro(blocks) == [
        [0, 0, 0.0, 0.5, 200, 5, "b"],
        [0, 0, 0.5, 1, 0, 5, "a"],
    ]


def test_two_servos_each_return_to_zero():
    blocks = [
        [0, 0, 0.0, 1, 200, 5, "a"],
        [0, 1, 0.0, 1, 300, 4, "b"],
    ]
    assert generate_neutro(blocks) == [
        [0, 1, 0.0, 1, 0, 4, "b"],
        [0, 0, 0.0, 1, 0, 5, "a"],
    ]


def test_inicio_tie_uses_array_index_then_inverts():
    blocks = [
        [0, 0, 0.0, 1, 10, 1, "a"],
        [0, 0, 0.0, 1, 99, 9, "b"],
    ]
    assert generate_neutro(blocks) == [
        [0, 0, 0.0, 1, 10, 9, "b"],
        [0, 0, 0.0, 1, 0, 1, "a"],
    ]


def test_gap_is_mirrored():
    blocks = [
        [0, 0, 0.0, 1, 200, 5, "a"],
        [0, 0, 2.0, 1, 400, 5, "b"],
    ]
    assert generate_neutro(blocks) == [
        [0, 0, 0.0, 1, 200, 5, "b"],
        [0, 0, 2.0, 1, 0, 5, "a"],
    ]


def test_replace_flag_required_when_existing():
    existing = [[0, 0, 0, 2, 1, 1, "x"]]
    with pytest.raises(ValueError, match="ya existe"):
        generate_neutro([[0, 0, 0, 1, 2, 2, "y"]], existing=existing, replace=False)
    assert generate_neutro(
        [[0, 0, 0, 1, 2, 2, "y"]], existing=existing, replace=True
    ) == [[0, 0, 0.0, 1, 0, 2, "y"]]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd pmas-web-motion-studio && python -m pytest tests/test_neutro.py -v
```

Expected: FAIL on the first rewind assertion (old function still emits `[pca, servo, 0, 2, first_pos, …]`).

- [ ] **Step 3: Implement rewind in `src/neutro.py`**

Replace `generate_neutro` with:

```python
def generate_neutro(
    blocks: list[list[Any]],
    existing: list[list[Any]] | None = None,
    replace: bool = False,
) -> list[list[Any]]:
    if existing and not replace:
        raise ValueError("La pista neutra ya existe")
    if not blocks:
        return []
    ordered = sorted(enumerate(blocks), key=lambda pair: (float(pair[1][2]), pair[0]))
    prev: dict[tuple[int, int], int] = {}
    undos: list[tuple[int, list[Any]]] = []
    for index, item in ordered:
        pca, servo = int(item[0]), int(item[1])
        key = (pca, servo)
        inicio = float(item[2])
        dur = float(item[3])
        pos = int(item[4])
        vel = int(item[5])
        nombre = str(item[6])
        undos.append(
            (index, [pca, servo, inicio, dur, prev.get(key, 0), vel, nombre])
        )
        prev[key] = pos
    t_end = max(float(item[2]) + float(item[3]) for item in blocks)
    out: list[tuple[float, int, list[Any]]] = []
    for index, row in undos:
        inicio = float(row[2])
        dur = float(row[3])
        row[2] = t_end - (inicio + dur)
        out.append((float(row[2]), -index, row))
    out.sort(key=lambda item: (item[0], item[1]))
    return [
        [row[0], row[1], row[2], row[3], row[4], row[5], row[6]]
        for _, _, row in out
    ]
```

Leave `CATEGORIES` as it is.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd pmas-web-motion-studio && python -m pytest tests/test_neutro.py -v
```

Expected: PASS (5 tests).

- [ ] **Step 5: Commit in `pmas-web-motion-studio`**

```bash
git add src/neutro.py tests/test_neutro.py
git commit -m "$(cat <<'EOF'
Rewind generated neutro along the gesture path.

Each step keeps its duration and returns the servo to the pose it had before that move.
EOF
)"
```

---

### Task 2: Description ≥ 10 on disk and ingest

**Files:**
- Modify: `pmas-web-motion-studio/src/local_sequences.py` (`_normalize`)
- Modify: `pmas-web-motion-studio/tests/test_local_sequences.py`
- Modify: `pba-ms-robotics/src/sequence/ingest.py` (`ingest_save`, `is_complete_pair`)
- Modify: `pba-ms-robotics/tests/test_sequence_ingest.py`

**Interfaces:**
- Consumes: origin JSON `description` string.
- Produces: after newline→space, strip, `[:280]`, `len >= 10` or `ValueError("Descripción inválida")`. `is_complete_pair` is false when `len(description.strip()) < 10`.

- [ ] **Step 1: Add failing local-store tests**

Append to `pmas-web-motion-studio/tests/test_local_sequences.py`:

```python
def test_save_rejects_short_description(tmp_path):
    client = client_with_store(tmp_path)
    raw = dict(ORIGIN)
    raw["description"] = "123456789"
    response = client.post("/local/sequences", json={"sequence": raw, "overwrite": False})
    assert response.status_code == 400
    assert "descripci" in response.json()["detail"].lower()


def test_save_accepts_ten_char_description(tmp_path):
    client = client_with_store(tmp_path)
    raw = dict(ORIGIN)
    raw["description"] = "1234567890"
    response = client.post("/local/sequences", json={"sequence": raw, "overwrite": False})
    assert response.status_code == 200
    assert response.json()["description"] == "1234567890"
```

- [ ] **Step 2: Run local tests to verify they fail**

```bash
cd pmas-web-motion-studio && python -m pytest tests/test_local_sequences.py::test_save_rejects_short_description tests/test_local_sequences.py::test_save_accepts_ten_char_description -v
```

Expected: FAIL (`test_save_rejects_short_description` gets 200).

- [ ] **Step 3: Enforce length in `_normalize`**

In `pmas-web-motion-studio/src/local_sequences.py`, replace the description block with:

```python
        description = (
            str(payload.get("description") or "").replace("\n", " ").strip()[:280]
        )
        if len(description) < 10:
            raise ValueError("Descripción inválida")
```

- [ ] **Step 4: Run local tests**

```bash
cd pmas-web-motion-studio && python -m pytest tests/test_local_sequences.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit in `pmas-web-motion-studio`**

```bash
git add src/local_sequences.py tests/test_local_sequences.py
git commit -m "$(cat <<'EOF'
Reject sequence descriptions shorter than ten characters.

The turn prompt needs a usable phrase, not an empty or two-letter field.
EOF
)"
```

- [ ] **Step 6: Add failing robotics ingest tests**

In `pba-ms-robotics/tests/test_sequence_ingest.py`:

Replace `test_raw_seven_tuple_list_description_empty` with:

```python
def test_ingest_rejects_short_description():
    raw = dict(ORIGIN)
    raw["description"] = "123456789"
    with pytest.raises(ValueError, match="Descripción inválida"):
        ingest_save({"sequence": raw, "overwrite": False}, existing=None, next_id=3)


def test_ingest_accepts_ten_char_description():
    raw = dict(ORIGIN)
    raw["description"] = "1234567890"
    result = ingest_save({"sequence": raw, "overwrite": False}, existing=None, next_id=3)
    assert result.description == "1234567890"
```

Add:

```python
def test_short_description_lists_but_not_in_catalog(tmp_path: Path):
    path = tmp_path / "corto.json"
    path.write_text(
        '{"version": 1, "id": 8, "name": "corto", "description": "corta",'
        '"category": "cara", "blocks": ['
        '{"arduino_id": 0, "pca": 0, "servo": 0, "inicio": 0, "dur": 2, "pos": 0, "vel": 1, "nombre": "P0_S0"}'
        '], "blocks_neutro": ['
        '{"arduino_id": 0, "pca": 0, "servo": 0, "inicio": 0, "dur": 2, "pos": 0, "vel": 1, "nombre": "N0"}'
        "]}",
        encoding="utf-8",
    )
    service = SequenceService(data_dir=tmp_path)
    listed = service.list_sequences()
    assert listed.data[0].name == "corto"
    from src.action.action_service import ActionService

    assert ActionService(sequence_service=service).get_actions() == []
```

Import `is_complete_pair` only if a unit assertion is clearer; the catalog test is enough.

- [ ] **Step 7: Run robotics tests to verify they fail**

```bash
cd pba-ms-robotics && python -m pytest tests/test_sequence_ingest.py::test_ingest_rejects_short_description tests/test_sequence_ingest.py::test_short_description_lists_but_not_in_catalog -v
```

Expected: FAIL (short description still ingests or still catalogs).

- [ ] **Step 8: Update `ingest.py`**

`is_complete_pair`:

```python
def is_complete_pair(sequence: MotionSequenceFile) -> bool:
    return (
        sequence.category in CATEGORIES
        and bool(sequence.blocks)
        and bool(sequence.blocks_neutro)
        and len((sequence.description or "").strip()) >= 10
    )
```

In `ingest_save`, replace the description handling with:

```python
    description = raw.get("description", "")
    if description is None:
        description = ""
    if not isinstance(description, str):
        raise ValueError("Descripción inválida")
    description = description.replace("\n", " ").strip()[:280]
    if len(description) < 10:
        raise ValueError("Descripción inválida")
```

Drop the old `"\n" in description` hard reject; newlines become spaces, then length is measured.

- [ ] **Step 9: Run robotics ingest + catalog tests**

```bash
cd pba-ms-robotics && python -m pytest tests/test_sequence_ingest.py tests/test_action_catalog.py -v
```

Expected: PASS. `ORIGIN` descriptions stay ≥ 10. Legacy files without description still list and stay out of `getActions`.

- [ ] **Step 10: Commit in `pba-ms-robotics`**

```bash
git add src/sequence/ingest.py tests/test_sequence_ingest.py
git commit -m "$(cat <<'EOF'
Keep short descriptions out of the action catalog.

Ingest and getActions now require a phrase of at least ten characters.
EOF
)"
```

---

### Task 3: Toolbar and save `<dialog>` markup

**Files:**
- Modify: `pmas-web-motion-studio/tests/test_app.py`
- Modify: `pmas-web-motion-studio/src/static/index.html`

**Interfaces:**
- Consumes: existing ids `play`, `stop`, `add`, `track-gesto`, `track-neutro`, `generate-neutro`, `save`, `load`, `name`, `description`, `category`, `arduino_id`.
- Produces: those metadata ids live inside `#save-dialog`. Chrome contains only identity + `#mode`. Action order is Play → Stop → Agregar → Gesto → Neutro → Generar neutro → Guardar → Actualizar. Description `minlength="10"` `maxlength="280"` `required`.

- [ ] **Step 1: Rewrite `tests/test_app.py` assertions**

```python
from fastapi.testclient import TestClient
from src.app import app


def test_index_has_category_and_neutro_controls():
    text = TestClient(app).get("/").text
    chrome = text.split('<header class="chrome">', 1)[1].split("</header>", 1)[0]
    assert 'id="name"' not in chrome
    assert 'id="description"' not in chrome
    assert 'id="category"' not in chrome
    assert 'id="arduino_id"' not in chrome
    assert 'id="save-dialog"' in text
    dialog = text.split('id="save-dialog"', 1)[1]
    assert 'id="name"' in dialog
    assert 'id="description"' in dialog
    assert 'minlength="10"' in dialog
    assert 'id="category"' in dialog
    assert 'id="arduino_id"' in dialog
    assert 'id="track-gesto"' in text
    assert 'id="track-neutro"' in text
    assert 'id="generate-neutro"' in text
    assert "brazo_derecho" in text


def test_toolbar_order_is_play_stop_add_tracks_save():
    text = TestClient(app).get("/").text
    actions = text.split('<div class="actions">', 1)[1].split("</div>", 1)[0]
    ids = []
    for token in (
        'id="play"',
        'id="stop"',
        'id="add"',
        'id="track-gesto"',
        'id="track-neutro"',
        'id="generate-neutro"',
        'id="save"',
        'id="load"',
    ):
        ids.append((actions.index(token), token))
    assert [item[1] for item in ids] == [item[1] for item in sorted(ids)]


def test_index_serves_editor():
    response = TestClient(app).get("/")
    assert response.status_code == 200
    text = response.text.lower()
    assert "description" in text or "descripcion" in text or "descripción" in text
    assert "nombre" in text
    assert 'id="tracks"' in response.text
    assert "agregar" in text
    assert "material-symbols-outlined" in text
    assert "space grotesk" in text
```

Keep `test_index_has_library_panel` in `test_local_sequences.py` as it is.

- [ ] **Step 2: Run to verify fail**

```bash
cd pmas-web-motion-studio && python -m pytest tests/test_app.py -v
```

Expected: FAIL (`id="name"` still in chrome / toolbar order / fonts).

- [ ] **Step 3: Replace chrome, actions, and add the dialog in `index.html`**

Head:

```html
    <title>R-ONE Motion Studio</title>
    <link rel="stylesheet" href="/static/editor.css?v=identity" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&family=Inter:wght@400;600;700&display=swap" rel="stylesheet" />
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet" />
```

Update the HTML comment OWN-WORLD line from industrial night to navy chrome / cool paper.

Chrome (identity only):

```html
      <header class="chrome">
        <div class="identity">
          <strong>Motion Studio</strong>
          <span id="mode" class="mode">Suelto</span>
        </div>
      </header>
      <div class="actions">
        <button type="button" id="play" class="btn btn-play"><span class="material-symbols-outlined" aria-hidden="true">play_arrow</span> Play</button>
        <button type="button" id="stop" class="btn btn-stop"><span class="material-symbols-outlined" aria-hidden="true">stop</span> Stop</button>
        <button type="button" id="add" class="btn"><span class="material-symbols-outlined" aria-hidden="true">add</span> Agregar</button>
        <div class="track-switch" role="group" aria-label="Pista">
          <button type="button" id="track-gesto" class="btn active"><span class="material-symbols-outlined" aria-hidden="true">animation</span> Gesto</button>
          <button type="button" id="track-neutro" class="btn"><span class="material-symbols-outlined" aria-hidden="true">restart_alt</span> Neutro</button>
        </div>
        <button type="button" id="generate-neutro" class="btn btn-neutro"><span class="material-symbols-outlined" aria-hidden="true">swap_vert</span> Generar neutro</button>
        <button type="button" id="save" class="btn btn-save"><span class="material-symbols-outlined" aria-hidden="true">save</span> Guardar</button>
        <button type="button" id="load" class="btn"><span class="material-symbols-outlined" aria-hidden="true">refresh</span> Actualizar</button>
      </div>
```

Before `</div>` of `.app` (after inspector is fine):

```html
      <dialog id="save-dialog" class="save-dialog">
        <form id="save-form">
          <h2>Guardar secuencia</h2>
          <label class="field">
            <span>Nombre</span>
            <input id="name" name="name" maxlength="80" required placeholder="saludo" />
          </label>
          <label class="field">
            <span>Descripción</span>
            <input id="description" name="description" minlength="10" maxlength="280" required placeholder="Para el prompt del turno" />
          </label>
          <p id="save-error" class="save-error" hidden></p>
          <label class="field">
            <span>Categoría</span>
            <select id="category" name="category" required>
              <option value="">Elegir</option>
              <option value="cara">Cara</option>
              <option value="cuello">Cuello</option>
              <option value="brazo_derecho">Brazo derecho</option>
              <option value="brazo_izquierdo">Brazo izquierdo</option>
              <option value="torso">Torso</option>
              <option value="cadera">Cadera</option>
            </select>
          </label>
          <label class="field">
            <span>Arduino</span>
            <input id="arduino_id" name="arduino_id" type="number" min="0" value="0" required />
          </label>
          <div class="save-actions">
            <button type="button" id="save-cancel" class="btn">Cancelar</button>
            <button type="submit" id="save-confirm" class="btn btn-save">Guardar</button>
          </div>
        </form>
      </dialog>
```

Keep workspace, inspector, status, library as they are.

- [ ] **Step 4: Run tests**

```bash
cd pmas-web-motion-studio && python -m pytest tests/test_app.py -v
```

Expected: PASS. `editor.js` still finds the same ids (they moved into the dialog). Do not wire the dialog yet if tests only read HTML.

- [ ] **Step 5: Commit in `pmas-web-motion-studio`**

```bash
git add src/static/index.html tests/test_app.py
git commit -m "$(cat <<'EOF'
Move sequence metadata into a save dialog.

The chrome no longer mixes the timeline task with name and category fields.
EOF
)"
```

---

### Task 4: Dialog behavior and JS rewind

**Files:**
- Modify: `pmas-web-motion-studio/src/static/editor.js`

**Interfaces:**
- Consumes: `generate_neutro` rules from Task 1. `#save-dialog`, `#save-form`, `#save-cancel`, `#save-error`.
- Produces: `generateNeutroFrom(tuples)` matches Python. `#save` opens the dialog; submit validates description length ≥ 10, category, both tracks; then `saveLocal` / `saveCoupled`. Cancel closes without writing. `buildOrigin` still reads `els.name` / `els.description` / `els.category` / `els.arduino`.

- [ ] **Step 1: Replace `generateNeutroFrom`**

```javascript
function generateNeutroFrom(tuples) {
  if (!tuples.length) return [];
  const ordered = tuples.map((item, index) => ({ item, index }));
  ordered.sort((a, b) => {
    const start = Number(a.item[2]) - Number(b.item[2]);
    return start !== 0 ? start : a.index - b.index;
  });
  const prev = new Map();
  const undos = [];
  for (const { item, index } of ordered) {
    const key = `${item[0]}:${item[1]}`;
    const inicio = Number(item[2]);
    const dur = Number(item[3]);
    undos.push({
      index,
      row: [item[0], item[1], inicio, dur, prev.has(key) ? prev.get(key) : 0, item[5], item[6]],
    });
    prev.set(key, item[4]);
  }
  const tEnd = Math.max(...tuples.map((item) => Number(item[2]) + Number(item[3])));
  return undos
    .map(({ index, row }) => {
      const inicio = Number(row[2]);
      const dur = Number(row[3]);
      row[2] = tEnd - (inicio + dur);
      return { index, row };
    })
    .sort((a, b) => {
      const start = Number(a.row[2]) - Number(b.row[2]);
      return start !== 0 ? start : b.index - a.index;
    })
    .map(({ row }) => row);
}
```

Leave `generateNeutro()` as it is (empty-gesture message + confirm replace).

- [ ] **Step 2: Open the dialog from Guardar**

Add after `buildOrigin`:

```javascript
function setSaveError(message) {
  const node = document.getElementById("save-error");
  if (!message) {
    node.hidden = true;
    node.textContent = "";
    return;
  }
  node.hidden = false;
  node.textContent = message;
}

function openSaveDialog() {
  setSaveError("");
  document.getElementById("save-dialog").showModal();
}

async function confirmSave(event) {
  event.preventDefault();
  const sequence = buildOrigin();
  const description = sequence.description.trim();
  if (!sequence.name) {
    setSaveError("Escribe un nombre.");
    return;
  }
  if (description.length < 10) {
    setSaveError("La descripción debe tener al menos 10 caracteres.");
    return;
  }
  if (!sequence.category) {
    setSaveError("Elige una categoría.");
    return;
  }
  if (!sequence.blocks.length || !sequence.blocks_neutro.length) {
    setSaveError("Categoría, gesto y neutro son obligatorios");
    return;
  }
  try {
    const saved = isCoupled() ? await saveCoupled(false) : await saveLocal(false);
    if (!saved) return;
    selectedLibraryName = sequence.name;
    document.getElementById("save-dialog").close();
    await refreshLibrary();
    setStatus(isCoupled() ? "Secuencia guardada en robótica" : "Secuencia guardada en disco");
  } catch (error) {
    setSaveError(error.message || "No se pudo guardar");
    setStatus(error.message || "No se pudo guardar", true);
  }
}
```

Replace the save click handler:

```javascript
document.getElementById("save").onclick = () => openSaveDialog();
document.getElementById("save-form").addEventListener("submit", (event) => {
  void confirmSave(event);
});
document.getElementById("save-cancel").onclick = () => {
  document.getElementById("save-dialog").close();
};
document.getElementById("save-dialog").addEventListener("cancel", () => setSaveError(""));
```

`parseLoadedSequence` already fills the same ids; opening Guardar after load prefills.

- [ ] **Step 3: Sanity-check JS syntax**

```bash
node --check pmas-web-motion-studio/src/static/editor.js
```

Expected: empty stdout, exit 0.

- [ ] **Step 4: Re-run studio pytest**

```bash
cd pmas-web-motion-studio && python -m pytest tests -v
```

Expected: PASS.

- [ ] **Step 5: Commit in `pmas-web-motion-studio`**

```bash
git add src/static/editor.js
git commit -m "$(cat <<'EOF'
Wire the save dialog and match JS neutro to the rewind.

Guardar no longer writes until the operator confirms name, phrase, category, and Arduino.
EOF
)"
```

---

### Task 5: Identity CSS + PRODUCT/DESIGN

**Files:**
- Create: `pmas-web-motion-studio/tests/test_editor_css.py`
- Modify: `pmas-web-motion-studio/src/static/editor.css`
- Modify: `PRODUCT.md`
- Modify: `DESIGN.md`

**Interfaces:**
- Consumes: DESIGN hexes from the spec One Skin table.
- Produces: `editor.css` `:root` on cool paper; `.chrome` navy; Play/Guardar cyan; Neutro emerald `#059669`; Stop `#dc2626`. PRODUCT evidence lists this CSS. DESIGN layout mentions the iframe.

- [ ] **Step 1: Write the failing CSS spec**

```python
from pathlib import Path

CSS = Path("src/static/editor.css").read_text(encoding="utf-8")


def test_canvas_is_cool_paper_not_industrial_night():
    assert "--bg: #eef2f6" in CSS
    assert "#000f1d" not in CSS
    assert "#10b981" not in CSS
    assert "#ffffff" not in CSS


def test_chrome_is_navy_and_neutro_is_reserved_emerald():
    assert "#0B2540" in CSS
    assert "#059669" in CSS
    assert "#38bdf8" in CSS
    assert "#dc2626" in CSS
```

- [ ] **Step 2: Run to verify fail**

```bash
cd pmas-web-motion-studio && python -m pytest tests/test_editor_css.py -v
```

Expected: FAIL (`#000f1d` still present).

- [ ] **Step 3: Retoken `editor.css`**

Replace `:root` with:

```css
:root {
  --bg: #eef2f6;
  --surface: #f7fafc;
  --panel: #f7fafc;
  --line: #c5d4e0;
  --text: #0B2540;
  --muted: #3d5a73;
  --cyan: #38bdf8;
  --on-cyan: #0c4a6e;
  --emerald: #059669;
  --rose: #dc2626;
  --rail: #0B2540;
  --on-rail: #eef2f6;
  --px-per-s: 100;
  --row-h: 44px;
  --block-h: 30px;
  --lane-w: 118px;
  --lib-w: 16.5rem;
  --ruler-h: 28px;
}
```

`.chrome`:

```css
.chrome {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 0.75rem;
  padding: 0.5rem 0.75rem;
  background: var(--rail);
  color: var(--on-rail);
  border-bottom: 1px solid var(--line);
  flex-shrink: 0;
}

.identity strong {
  font-family: "Space Grotesk", Inter, sans-serif;
  font-size: 1.125rem;
  font-weight: 700;
}

.mode {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--on-rail);
  border: 1px solid color-mix(in srgb, var(--on-rail) 35%, transparent);
  border-radius: 999px;
  padding: 0.15rem 0.5rem;
}
```

Inputs (no `#041018`):

```css
input,
select {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 0.75rem;
  padding: 0.5rem 0.65rem;
  outline: none;
  font-size: 0.875rem;
}

.field span {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--muted);
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  min-height: 2.75rem;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 0.75rem;
  padding: 0.4rem 0.75rem;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 600;
}

.btn .material-symbols-outlined {
  font-size: 1.1rem;
}

.btn-play,
.btn-save {
  background: var(--cyan);
  color: var(--on-cyan);
  border-color: var(--cyan);
}

.btn-stop {
  color: var(--rose);
  border-color: var(--rose);
}

.btn-neutro,
#track-neutro.active {
  background: var(--emerald);
  color: #ecfdf5;
  border-color: var(--emerald);
}

#track-gesto.active {
  background: var(--cyan);
  color: var(--on-cyan);
  border-color: var(--cyan);
}

.track-neutro .block {
  background: var(--emerald);
}

.save-dialog {
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--line);
  border-radius: 0.75rem;
  padding: 1.25rem;
  max-width: 28rem;
  width: calc(100% - 2rem);
}

.save-dialog::backdrop {
  background: color-mix(in srgb, var(--rail) 55%, transparent);
}

.save-error {
  color: var(--rose);
  font-size: 0.875rem;
  margin: 0;
}

.save-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1rem;
}
```

Bump `.btn` / `.status` / `.field span` off sub-12px sizes (`0.58rem`, `0.62rem`, `0.72rem`, `0.78rem`). Status `0.875rem`. Remove `input` dark fill `#041018` if any leftover. Keep timeline drag geometry (`--px-per-s`, row heights).

- [ ] **Step 4: Run CSS + app tests**

```bash
cd pmas-web-motion-studio && python -m pytest tests/test_editor_css.py tests/test_app.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit CSS in `pmas-web-motion-studio`**

```bash
git add src/static/editor.css tests/test_editor_css.py
git commit -m "$(cat <<'EOF'
Paint Motion Studio with the operator navy and cool paper.

The iframe stops using industrial night so it matches PRODUCT and DESIGN.
EOF
)"
```

- [ ] **Step 6: Update launcher PRODUCT.md and DESIGN.md**

In `PRODUCT.md` Evidence, add:

```markdown
- Spec: `docs/superpowers/specs/2026-10-14-motion-studio-save-modal-neutro-rewind-design.md`
- Tokens: `pmas-web-main/src/styles.css`
- Studio: `pmas-web-motion-studio/src/static/editor.css`
```

Replace principle 5 with:

```markdown
5. **Cortes siguientes** — auth y visión son otros ciclos. El estudio ya comparte esta identidad.
```

In `DESIGN.md` Layout, add:

```markdown
- Motion Studio (iframe): cabecera navy; barra Play / Stop / Agregar / Gesto|Neutro / Generar neutro / Guardar / Actualizar; Guardar abre diálogo (nombre, descripción ≥ 10, categoría, Arduino); escenario en papel frío; barras de gesto cian y de neutro esmeralda. No reabrir la gramática de la regla.
```

Add to Accent Chip Rule uses: Play, Guardar, pista Gesto activa.

- [ ] **Step 7: Commit docs in the launcher**

```bash
git add PRODUCT.md DESIGN.md
git commit -m "$(cat <<'EOF'
Record Motion Studio on the shared PRODUCT and DESIGN identity.

The studio iframe is no longer a pending visual cut.
EOF
)"
```

---

### Task 6: Browser check in Compose

**Files:** none unless a leftover class breaks the iframe.

**Interfaces:**
- Consumes: running `sudo docker compose up` (already used for the operator UI). Studio is the Seq. iframe.
- Produces: visual confirmation; fix only if chrome is still night, dialog missing, or Generate neutro still emits duration-2 rest blocks.

- [ ] **Step 1: Rebuild the studio container if Compose does not bind-mount `src/static`**

If the running studio image is stale, restart that service so `index.html` / `editor.css` / `editor.js` load. Do not restart mai-core unless needed.

- [ ] **Step 2: Log in as `admin-prometeo@unilibre.edu.co` / `Prometeo2026*` and open Seq.**

Confirm:

1. Iframe header is navy; canvas is cool paper, not `#000f1d`.
2. Toolbar order matches Goal 2; both Gesto and Neutro are readable.
3. Nombre/descripción/categoría are not in the header.
4. Guardar opens the dialog; a 9-character description cannot confirm; 10 can (do not have to persist if Arduino/catalog empty — cancel after the error/success path is clear).
5. Agregar two sequential blocks on one servo, Generar neutro, switch to Neutro: two blocks, reversed times, last move returns toward 0.

Do not send a chat turn. Do not change robotics queue behavior.

- [ ] **Step 3: If something fails, fix in the owning file and re-run the matching pytest from Tasks 1–5. Commit the fix in that repo.**

- [ ] **Step 4: No extra commit if the browser matches the spec.**

---

## Self-review

**Spec coverage:**
- Task strip / chrome without metadata → Task 3
- Save dialog + prefill via existing fields → Tasks 3–4
- Description ≥ 10 local + ingest + `is_complete_pair` → Task 2
- Rewind algorithm JS+Python → Tasks 1 and 4
- One Skin / PRODUCT / DESIGN → Task 5
- Browser → Task 6
- Auth, vision, turn contract, Qt editor → Global Constraints / non-goals (no task)

**Placeholders:** none.

**Types:** `generate_neutro` / `generateNeutroFrom` keep 7-tuples. `ingest_save` still returns `MotionSequenceFile`. Dialog reuses `#name` `#description` `#category` `#arduino_id`.
