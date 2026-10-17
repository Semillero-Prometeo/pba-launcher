# Legacy sequence import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Import Qt-era JSON lists (`interfaz_record9_5_1.py`) as a gesture, generate the studio rewind neutro, let the operator pick a category, and persist with an empty description until the studio completes the pair.

**Architecture:** `parseOriginText` accepts a 7-tuple array or an origin object. Missing `blocks_neutro` is filled by `generateNeutroFrom` (same rewind as `editor.js`). The modal requires category per row and skips filenames containing `NEUTRO`. `ingest_save` accepts `description=""`. `is_complete_pair` still needs a phrase of 10+ characters.

**Tech Stack:** Angular 21 + Vitest (`npx vitest run`); FastAPI/Pydantic ingest + pytest in `pba-ms-robotics`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-16-legacy-sequence-import-design.md`. Neutro/runtime and studio-integration specs still apply.
- Rewind lives in Angular (`origin-sequence.ts`). Do not copy `generate_neutro` into robotics.
- Filename containing `NEUTRO` (any case) is omitted. Do not pair companion files.
- Category is operator-chosen. Do not infer it from the filename.
- `ingest_save`: `""` is valid; 1–9 characters after trim is `Descripción inválida`; ≥ 10 is a complete phrase.
- `is_complete_pair` unchanged: category + both tracks + description ≥ 10.
- Do not edit `interfaz_record9_5_1.py`, mai-core, `declarePoema`, or `{ reply, fuente, movimientos }`.
- Studio save dialog still requires description ≥ 10.
- Angular commits in `pmas-web-main`. Ingest commits in `pba-ms-robotics`. This plan commits in the launcher.

---

## File structure

| File | Responsibility |
|---|---|
| `pba-ms-robotics/src/sequence/ingest.py` | Allow empty description |
| `pba-ms-robotics/tests/test_sequence_ingest.py` | Empty vs 1–9 vs 10+ |
| `pmas-web-main/src/app/pages/sequences/origin-sequence.ts` | Parse list, rewind, skip `NEUTRO` |
| `pmas-web-main/src/app/pages/sequences/origin-sequence.spec.ts` | Parser + rewind + skip |
| `pmas-web-main/src/app/pages/sequences/sequences.ts` | Category field, omit `NEUTRO` files |
| `pmas-web-main/src/app/pages/sequences/sequences.html` | Category select |

---

### Task 1: Ingest accepts empty description

**Files:**
- Modify: `pba-ms-robotics/tests/test_sequence_ingest.py`
- Modify: `pba-ms-robotics/src/sequence/ingest.py`

**Interfaces:**
- Consumes: `ingest_save(payload: dict, existing: MotionSequenceFile | None, next_id: int) -> MotionSequenceFile`. `is_complete_pair(sequence: MotionSequenceFile) -> bool`.
- Produces: `description=""` persists with `id`. `is_complete_pair` is false until the phrase is ≥ 10.

- [ ] **Step 1: Write the failing tests**

Append to `pba-ms-robotics/tests/test_sequence_ingest.py` (keep `test_ingest_rejects_short_description` as-is; it still covers 9 characters):

```python
from src.sequence.ingest import ingest_save, is_complete_pair


def test_ingest_accepts_empty_description():
    raw = dict(ORIGIN)
    raw["description"] = ""
    result = ingest_save({"sequence": raw, "overwrite": False}, existing=None, next_id=11)
    assert result.id == 11
    assert result.description == ""
    assert is_complete_pair(result) is False


def test_ingest_five_char_description_rejected():
    raw = dict(ORIGIN)
    raw["description"] = "corta"
    with pytest.raises(ValueError, match="Descripción inválida"):
        ingest_save({"sequence": raw, "overwrite": False}, existing=None, next_id=12)
```

If `is_complete_pair` is not already imported at the top, add it to the existing import from `src.sequence.ingest` instead of a second import.

- [ ] **Step 2: Run tests to verify they fail**

From `pba-ms-robotics`:

```bash
python -m pytest tests/test_sequence_ingest.py::test_ingest_accepts_empty_description tests/test_sequence_ingest.py::test_ingest_five_char_description_rejected -v
```

Expected: FAIL. `test_ingest_accepts_empty_description` raises `Descripción inválida` because `len(description) < 10`.

- [ ] **Step 3: Allow empty description**

In `pba-ms-robotics/src/sequence/ingest.py`, replace:

```python
    description = description.replace("\n", " ").strip()[:280]
    if len(description) < 10:
        raise ValueError("Descripción inválida")
```

with:

```python
    description = description.replace("\n", " ").strip()[:280]
    if description and len(description) < 10:
        raise ValueError("Descripción inválida")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_sequence_ingest.py -v
```

Expected: PASS (including the existing 9-char reject and 10-char accept).

- [ ] **Step 5: Commit in `pba-ms-robotics`**

```bash
cd pba-ms-robotics
git add src/sequence/ingest.py tests/test_sequence_ingest.py
git commit -m "$(cat <<'EOF'
Allow empty descriptions on sequence ingest.

EOF
)"
```

---

### Task 2: Parse Qt lists and generate neutro

**Files:**
- Modify: `pmas-web-main/src/app/pages/sequences/origin-sequence.spec.ts`
- Modify: `pmas-web-main/src/app/pages/sequences/origin-sequence.ts`

**Interfaces:**
- Consumes: JSON-array of 7-tuples or origin object `{ name?, description?, category?, blocks, blocks_neutro? }`.
- Produces: `generateNeutroFrom(tuples: OriginTuple[]): OriginTuple[]`. `shouldSkipLegacyNeutroFile(fileBaseName: string): boolean`. `parseOriginText(raw, fileBaseName, defaultArduinoId): OriginParseResult` with `error` null for a valid list; generated `blocksNeutro` when the list or origin lacks a neutro track.

- [ ] **Step 1: Replace the spec with the new contract**

Overwrite `pmas-web-main/src/app/pages/sequences/origin-sequence.spec.ts`:

```typescript
import { describe, expect, it } from 'vitest';
import { generateNeutroFrom, parseOriginText, shouldSkipLegacyNeutroFile } from './origin-sequence';

const ABRAZOIZQ: [number, number, number, number, number, number, string][] = [
  [1, 14, 0.0, 2, 650, 3, 'P0_S1'],
  [1, 13, 1.99, 2, 900, 3, 'P0_S2'],
  [1, 12, 4.0, 2, 500, 3, 'P0_S3'],
];

describe('parseOriginText', () => {
  it('reads a Qt 7-tuple list and generates neutro', () => {
    const parsed = parseOriginText(JSON.stringify(ABRAZOIZQ), 'ABRAZOIZQ 7.1', 0);
    expect(parsed.error).toBeNull();
    expect(parsed.name).toBe('ABRAZOIZQ 7.1');
    expect(parsed.description).toBe('');
    expect(parsed.category).toBeNull();
    expect(parsed.blocks).toEqual(ABRAZOIZQ);
    expect(parsed.blocksNeutro.length).toBeGreaterThan(0);
    expect(parsed.blocksNeutro).not.toEqual(parsed.blocks);
  });

  it('keeps an origin pair without regenerating neutro', () => {
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
    expect(parsed.blocksNeutro).toEqual([[0, 0, 0.0, 2, 500, 5, 'P0_S0']]);
  });

  it('generates neutro when origin has blocks but no neutro track', () => {
    const parsed = parseOriginText(
      JSON.stringify({
        name: 'saludo',
        blocks: [[0, 0, 0.0, 2, 850, 5, 'P0_S0']],
      }),
      'archivo',
      1,
    );
    expect(parsed.error).toBeNull();
    expect(parsed.blocksNeutro.length).toBeGreaterThan(0);
  });

  it('rejects neither-list-nor-origin', () => {
    const parsed = parseOriginText('{"foo": 1}', 'x', 0);
    expect(parsed.error).toBeTruthy();
  });
});

describe('shouldSkipLegacyNeutroFile', () => {
  it('skips companion NEUTRO names', () => {
    expect(shouldSkipLegacyNeutroFile('ABRAZOIZQ NEUTRO 7.1')).toBe(true);
    expect(shouldSkipLegacyNeutroFile('brazoizq con guino neutro 7.0')).toBe(true);
    expect(shouldSkipLegacyNeutroFile('ABRAZOIZQ 7.1')).toBe(false);
  });
});

describe('generateNeutroFrom', () => {
  it('rewinds the first pose of each servo', () => {
    const neutro = generateNeutroFrom([
      [0, 0, 0.0, 2, 850, 5, 'P0_S0'],
    ]);
    expect(neutro[0][4]).toBe(0);
    expect(neutro[0][2]).toBe(0);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

From `pmas-web-main`:

```bash
npx vitest run src/app/pages/sequences/origin-sequence.spec.ts
```

Expected: FAIL (`generateNeutroFrom` / `shouldSkipLegacyNeutroFile` not exported; list parse still returns «Falta categoría o neutro»).

- [ ] **Step 3: Implement parser, rewind, and skip helper**

Overwrite `pmas-web-main/src/app/pages/sequences/origin-sequence.ts` with:

```typescript
export type OriginTuple = [number, number, number, number, number, number, string];

export const CATEGORIES = [
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

function toTuple(entry: unknown, index: number): OriginTuple {
  if (!Array.isArray(entry) || entry.length < 7) {
    throw new Error(`Movimiento inválido en índice ${index}`);
  }
  return [
    Number(entry[0]),
    Number(entry[1]),
    Number(entry[2]),
    Number(entry[3]),
    Number(entry[4]),
    Number(entry[5]),
    String(entry[6]),
  ];
}

function failed(fileBaseName: string, error: string): OriginParseResult {
  return {
    name: fileBaseName,
    description: '',
    category: null,
    blocks: [],
    blocksNeutro: [],
    error,
  };
}

export function generateNeutroFrom(tuples: OriginTuple[]): OriginTuple[] {
  if (!tuples.length) return [];
  const ordered = tuples.map((item, index) => ({ item, index }));
  ordered.sort((a, b) => {
    const start = Number(a.item[2]) - Number(b.item[2]);
    return start !== 0 ? start : a.index - b.index;
  });
  const prev = new Map<string, number>();
  const undos: { index: number; row: OriginTuple }[] = [];
  for (const { item, index } of ordered) {
    const key = `${item[0]}:${item[1]}`;
    const inicio = Number(item[2]);
    const dur = Number(item[3]);
    undos.push({
      index,
      row: [item[0], item[1], inicio, dur, prev.has(key) ? prev.get(key)! : 0, item[5], item[6]],
    });
    prev.set(key, item[4]);
  }
  const tEnd = Math.max(...tuples.map((item) => Number(item[2]) + Number(item[3])));
  return undos
    .map(({ index, row }) => {
      const inicio = Number(row[2]);
      const dur = Number(row[3]);
      const next: OriginTuple = [row[0], row[1], tEnd - (inicio + dur), row[3], row[4], row[5], row[6]];
      return { index, row: next };
    })
    .sort((a, b) => {
      const start = Number(a.row[2]) - Number(b.row[2]);
      return start !== 0 ? start : b.index - a.index;
    })
    .map(({ row }) => row);
}

export function shouldSkipLegacyNeutroFile(fileBaseName: string): boolean {
  return /\bneutro\b/i.test(fileBaseName);
}

export function parseOriginText(
  raw: string,
  fileBaseName: string,
  _defaultArduinoId: number | null,
): OriginParseResult {
  try {
    const parsed: unknown = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      const blocks = parsed.map((entry, index) => toTuple(entry, index));
      return {
        name: fileBaseName,
        description: '',
        category: null,
        blocks,
        blocksNeutro: generateNeutroFrom(blocks),
        error: null,
      };
    }
    if (parsed && typeof parsed === 'object' && Array.isArray((parsed as { blocks?: unknown }).blocks)) {
      const body = parsed as {
        name?: unknown;
        description?: unknown;
        category?: unknown;
        blocks: unknown[];
        blocks_neutro?: unknown;
      };
      const name = typeof body.name === 'string' && body.name.trim() ? body.name.trim() : fileBaseName;
      const description = typeof body.description === 'string' ? body.description : '';
      const category = typeof body.category === 'string' ? body.category : null;
      const blocks = body.blocks.map((entry, index) => toTuple(entry, index));
      const neutroRaw = Array.isArray(body.blocks_neutro) ? body.blocks_neutro : [];
      const blocksNeutro =
        neutroRaw.length > 0
          ? neutroRaw.map((entry, index) => toTuple(entry, index))
          : generateNeutroFrom(blocks);
      return {
        name,
        description,
        category,
        blocks,
        blocksNeutro,
        error: null,
      };
    }
    return failed(fileBaseName, 'El archivo no contiene una lista de movimientos');
  } catch (error) {
    return failed(fileBaseName, error instanceof Error ? error.message : 'Error de parseo');
  }
}
```

`shouldSkipLegacyNeutroFile` uses a word-boundary so `ABRAZOIZQ` does not match. `ABRAZOIZQ NEUTRO 7.1` matches.

- [ ] **Step 4: Run tests to verify they pass**

```bash
npx vitest run src/app/pages/sequences/origin-sequence.spec.ts
```

Expected: PASS.

- [ ] **Step 5: Commit in `pmas-web-main`**

```bash
cd pmas-web-main
git add src/app/pages/sequences/origin-sequence.ts src/app/pages/sequences/origin-sequence.spec.ts
git commit -m "$(cat <<'EOF'
Accept Qt sequence lists and generate rewind neutro.

EOF
)"
```

---

### Task 3: Modal category and skip NEUTRO files

**Files:**
- Modify: `pmas-web-main/src/app/pages/sequences/sequences.ts`
- Modify: `pmas-web-main/src/app/pages/sequences/sequences.html`
- Create: `pmas-web-main/src/app/pages/sequences/sequences.spec.ts`

**Interfaces:**
- Consumes: Task 2 `parseOriginText`, `shouldSkipLegacyNeutroFile`, `CATEGORIES`.
- Produces: `OriginImportItem.omitted`. `importLegacyItems` sends only rows with `error === null`, `omitted === false`, a category, Arduino, and name. Description in the POST is `''` unless the origin file already had one.

- [ ] **Step 1: Write the failing file-read test**

Create `pmas-web-main/src/app/pages/sequences/sequences.spec.ts`:

```typescript
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const ts = readFileSync(resolve(__dirname, 'sequences.ts'), 'utf8');
const html = readFileSync(resolve(__dirname, 'sequences.html'), 'utf8');

describe('legacy import modal', () => {
  it('requires a category and skips NEUTRO files', () => {
    expect(ts).toContain('shouldSkipLegacyNeutroFile');
    expect(ts).toContain('updateLegacyItemCategory');
    expect(ts).toMatch(/item\.category/);
    expect(html).toContain('updateLegacyItemCategory');
    expect(html).toMatch(/Categor[ií]a/);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
npx vitest run src/app/pages/sequences/sequences.spec.ts
```

Expected: FAIL (`shouldSkipLegacyNeutroFile` / category select missing).

- [ ] **Step 3: Wire the modal**

In `sequences.ts`, change the `origin-sequence` import to:

```typescript
import { CATEGORIES, OriginTuple, parseOriginText, shouldSkipLegacyNeutroFile } from './origin-sequence';
```

Add `omitted` to `OriginImportItem`:

```typescript
interface OriginImportItem {
  sourceFileName: string;
  sourceRelativePath: string;
  targetName: string;
  description: string;
  category: string | null;
  arduino_id: number | null;
  tupleBlocks: OriginTuple[];
  tupleBlocksNeutro: OriginTuple[];
  omitted: boolean;
  error: string | null;
}
```

Expose categories on the class:

```typescript
  readonly categories = CATEGORIES;
```

Add:

```typescript
  updateLegacyItemCategory(index: number, category: string) {
    this.legacyItems.update((items) =>
      items.map((item, idx) => (idx === index ? { ...item, category } : item)),
    );
  }
```

In `importLegacyItems`, replace the `validItems` filter with:

```typescript
    const validItems = items.filter(
      (item) =>
        item.error === null &&
        item.omitted === false &&
        item.category !== null &&
        item.arduino_id !== null &&
        item.targetName.trim().length > 0,
    );
```

In `parseOriginFile` `onload`, after computing `fileBaseName`:

```typescript
        if (shouldSkipLegacyNeutroFile(fileBaseName)) {
          resolve({
            sourceFileName: file.name,
            sourceRelativePath: relativePath,
            targetName: fileBaseName,
            description: '',
            category: null,
            arduino_id: defaultArduinoId,
            tupleBlocks: [],
            tupleBlocksNeutro: [],
            omitted: true,
            error: null,
          });
          return;
        }
        const parsed = parseOriginText(String(reader.result ?? ''), fileBaseName, defaultArduinoId);
        resolve({
          sourceFileName: file.name,
          sourceRelativePath: relativePath,
          targetName: parsed.name,
          description: parsed.description,
          category: parsed.category,
          arduino_id: defaultArduinoId,
          tupleBlocks: parsed.blocks,
          tupleBlocksNeutro: parsed.blocksNeutro,
          omitted: false,
          error: parsed.error,
        });
```

Add `omitted: false` to the `onerror` resolve object.

In `sequences.html`, replace the help paragraph with:

```html
      <p class="text-xs text-slate-400 mb-4">
        Listas del software original (7-tuplas) o origen nuevo. Elige categoría y Arduino por fila. Los archivos NEUTRO se omiten.
      </p>
```

Inside the `@for` row, after the `sourceRelativePath` line, add an omitted branch **before** the existing `@if (item.error)`:

```html
            @if (item.omitted) {
              <div class="text-xs text-outline">Archivo NEUTRO omitido</div>
            } @else if (item.error) {
              <div class="text-xs text-red-400">{{ item.error }}</div>
            } @else {
```

Close with the same `}` as today. In the else grid, add a category label after Nombre (grid can stay 3 columns; category replaces the movements-only third cell or sits with Arduino). Replace the «Movimientos detectados» cell with:

```html
                <label class="text-[11px] text-slate-400">
                  Categoría
                  <select
                    [ngModel]="item.category"
                    (ngModelChange)="updateLegacyItemCategory(i, $event)"
                    class="w-full mt-1 rounded bg-surface-container-high border border-white/10 px-2 py-1 text-sm">
                    <option [ngValue]="null">Elegir…</option>
                    @for (category of categories; track category) {
                      <option [ngValue]="category">{{ category }}</option>
                    }
                  </select>
                </label>
```

Keep the movements count as a fourth line under the grid if it still fits; otherwise drop it. Category is required.

- [ ] **Step 4: Run tests**

```bash
npx vitest run src/app/pages/sequences/origin-sequence.spec.ts src/app/pages/sequences/sequences.spec.ts
```

Expected: PASS.

- [ ] **Step 5: Commit in `pmas-web-main` and point the launcher**

```bash
cd pmas-web-main
git add src/app/pages/sequences/sequences.ts src/app/pages/sequences/sequences.html src/app/pages/sequences/sequences.spec.ts
git commit -m "$(cat <<'EOF'
Require a category when importing Qt sequence lists.

EOF
)"
```

From the launcher root:

```bash
git add pmas-web-main pba-ms-robotics
git commit -m "$(cat <<'EOF'
Point web and robotics at legacy sequence import.

EOF
)"
```

Do not stage `ABRAZOIZQ*.json`, `error.md`, or `.env`.

---

## Self-review vs spec

| Spec requirement | Task |
|---|---|
| Qt 7-tuple list is a gesture + generated neutro | 2 |
| Origin pair kept as-is | 2 |
| Origin without neutro generates rewind | 2 |
| Operator picks category; no send without it | 3 |
| Empty description on ingest; pair incomplete | 1 |
| Skip filename containing `NEUTRO` | 2, 3 |
| Neither-list-nor-origin rejected | 2 |
| Description 1–9 rejected; ≥ 10 complete | 1 (existing + new) |
| No robotics rewind copy; no Qt editor edit | constraints |
