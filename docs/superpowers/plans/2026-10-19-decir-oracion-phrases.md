# Decir oración parametrizable Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hardcoded Decir oración quick phrases with a single robotics JSON catalog that the chat UI can list, create, edit, and deactivate.

**Architecture:** `PhraseStore` in `pba-ms-robotics` owns `data/phrases.json`. NATS `phraseService.list|create|update|setActive` feed gateway `GET/POST/PATCH /voice/phrases`. Angular drops `decirQuickOptions`, loads the catalog, speaks `phrase.text` on card click, and manages the catalog in a dialog. `POST /voice/speak` is unchanged.

**Tech Stack:** Python 3.13 + pydantic + pytest (`pba-ms-robotics`); NestJS 11 + class-validator (`pba-ms-gateway`); Angular 21 + Vitest (`pmas-web-main`).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-19-decir-oracion-phrases-design.md`.
- One file: `PHRASES_PATH` default `/usr/src/app/data/phrases.json`.
- Fields: `id` int, `title` 1–80, `text` 1–2000, `icon` empty or `[a-z0-9_]+`, `active` bool.
- Soft deactivate only. No DELETE. No reorder. No Prisma.
- Anyone with JWT may CRUD. No ADMIN gate.
- Seed once when the file is missing or `items` is `[]`. Corrupt JSON → 500, do not overwrite.
- Card click speaks `phrase.text` in full. Do not send it through the 400-char textarea.
- Do not change TTS, `declarePoema`, or the turn.
- Edit only the owning repo. No worktree: Compose bind-mounts `./pba-ms-robotics`.
- Do not commit runtime `data/phrases.json`.

---

## File structure

| File | Responsibility |
|---|---|
| `pba-ms-robotics/src/voice/phrases/errors.py` | `PhraseError` with `status_code` |
| `pba-ms-robotics/src/voice/phrases/models.py` | `Phrase`, create/update/active payloads |
| `pba-ms-robotics/src/voice/phrases/seed.py` | The 25 current labels + titles |
| `pba-ms-robotics/src/voice/phrases/store.py` | Read/validate/seed/write `phrases.json` |
| `pba-ms-robotics/src/voice/phrases/phrase_controller.py` | NATS handlers |
| `pba-ms-robotics/src/core/nats/nats_subscribers.py` | Wire `phraseService.*` |
| `pba-ms-robotics/src/core/settings/env.py` | `PHRASES_PATH` |
| `pba-ms-robotics/tests/test_phrase_store.py` | Store tests (temp file, no NATS/TTS) |
| `pba-ms-gateway/src/robotics-ms/voice/dto/phrase.dto.ts` | HTTP DTOs |
| `pba-ms-gateway/src/robotics-ms/voice/voice.controller.ts` | `/voice/phrases*` |
| `pmas-web-main/src/app/pages/robotics-chat/decir-phrases.ts` | `Phrase` type + `filterSpeakPhrases` |
| `pmas-web-main/src/app/pages/robotics-chat/decir-phrases.spec.ts` | Filter tests |
| `pmas-web-main/src/app/pages/robotics-chat/robotics-chat.ts` | Load, speak, dialog |
| `pmas-web-main/src/app/pages/robotics-chat/robotics-chat.html` | Grid + manage dialog |

---

### Task 1: Phrase JSON store and seed

**Files:**
- Create: `pba-ms-robotics/src/voice/phrases/__init__.py` (empty)
- Create: `pba-ms-robotics/src/voice/phrases/errors.py`
- Create: `pba-ms-robotics/src/voice/phrases/models.py`
- Create: `pba-ms-robotics/src/voice/phrases/seed.py`
- Create: `pba-ms-robotics/src/voice/phrases/store.py`
- Create: `pba-ms-robotics/tests/test_phrase_store.py`
- Modify: `pba-ms-robotics/src/core/settings/env.py` (add `PHRASES_PATH`)
- Modify: `pba-ms-robotics/.env.template` (comment `PHRASES_PATH=`)
- Modify: `pba-ms-robotics/.gitignore` (add `/data/phrases.json`)

**Interfaces:**
- Consumes: `path: Path` to the JSON file. Does **not** import `src.core.settings.env` (that module requires `NATS_SERVER` and would break pytest).
- Produces: `PhraseError(message, *, status_code: int)`. `Phrase(id: int, title: str, text: str, icon: str = "", active: bool = True)`. `PhraseStore(path: Path)`. `list_phrases() -> list[Phrase]`. `create(title: str, text: str, icon: str = "") -> Phrase`. `update(phrase_id: int, patch: dict[str, str | None]) -> Phrase`. `set_active(phrase_id: int, active: bool) -> Phrase`. `SEED_ROWS: list[tuple[str, str, str]]` as `(title, text, icon)`.

- [ ] **Step 1: Write the failing store tests**

Create `pba-ms-robotics/tests/test_phrase_store.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.voice.phrases.errors import PhraseError
from src.voice.phrases.seed import SEED_ROWS
from src.voice.phrases.store import PhraseStore


def store_at(tmp_path: Path) -> PhraseStore:
    return PhraseStore(tmp_path / "phrases.json")


def test_missing_file_seeds_current_phrases(tmp_path: Path) -> None:
    store = store_at(tmp_path)
    items = store.list_phrases()
    assert len(items) == len(SEED_ROWS)
    assert all(item.active for item in items)
    assert [item.title for item in items] == [row[0] for row in SEED_ROWS]
    assert items[0].id == 1
    assert items[-1].id == len(SEED_ROWS)
    assert items[0].icon == ""
    assert items[1].icon == "menu_book"


def test_empty_items_seeds(tmp_path: Path) -> None:
    path = tmp_path / "phrases.json"
    path.write_text('{"items": []}\n', encoding="utf-8")
    items = PhraseStore(path).list_phrases()
    assert len(items) == len(SEED_ROWS)


def test_second_list_does_not_duplicate(tmp_path: Path) -> None:
    store = store_at(tmp_path)
    first = store.list_phrases()
    second = store.list_phrases()
    assert [item.id for item in first] == [item.id for item in second]
    assert len(second) == len(SEED_ROWS)


def test_create_update_and_set_active_persist(tmp_path: Path) -> None:
    store = store_at(tmp_path)
    store.list_phrases()
    created = store.create("Nueva", "Texto hablado", "star")
    assert created.id == len(SEED_ROWS) + 1
    assert created.active is True
    updated = store.update(created.id, {"title": "Editada", "icon": ""})
    assert updated.title == "Editada"
    assert updated.text == "Texto hablado"
    assert updated.icon == ""
    inactive = store.set_active(created.id, False)
    assert inactive.active is False
    again = PhraseStore(tmp_path / "phrases.json").list_phrases()
    found = next(item for item in again if item.id == created.id)
    assert found.title == "Editada"
    assert found.active is False


def test_invalid_title_and_missing_id(tmp_path: Path) -> None:
    store = store_at(tmp_path)
    store.list_phrases()
    with pytest.raises(PhraseError) as empty:
        store.create("  ", "hola")
    assert empty.value.status_code == 400
    with pytest.raises(PhraseError) as missing:
        store.set_active(9999, False)
    assert missing.value.status_code == 404


def test_corrupt_json_does_not_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "phrases.json"
    path.write_text("{nope", encoding="utf-8")
    with pytest.raises(PhraseError) as exc:
        PhraseStore(path).list_phrases()
    assert exc.value.status_code == 500
    assert path.read_text(encoding="utf-8") == "{nope"
```

- [ ] **Step 2: Run tests to verify they fail**

Run from the launcher (robotics is bind-mounted):

```bash
docker compose exec pba-ms-robotics python -m pytest tests/test_phrase_store.py -v
```

If Compose is down, from `pba-ms-robotics` with pydantic on `PYTHONPATH=src`:

```bash
PYTHONPATH=. python3 -m pytest tests/test_phrase_store.py -v
```

Expected: FAIL with `ModuleNotFoundError: src.voice.phrases` or `PhraseStore` missing.

- [ ] **Step 3: Implement store, models, seed, and env**

`pba-ms-robotics/src/voice/phrases/__init__.py` — empty file.

`pba-ms-robotics/src/voice/phrases/errors.py`:

```python
"""HTTP-style codes for NATS error payloads consumed by the gateway."""


class PhraseError(Exception):
    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code
```

`pba-ms-robotics/src/voice/phrases/models.py`:

```python
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Phrase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    title: str
    text: str
    icon: str = ""
    active: bool = True


class PhraseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    text: str
    icon: str | None = None


class PhraseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    title: str | None = None
    text: str | None = None
    icon: str | None = None


class PhraseSetActive(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    active: bool
```

`pba-ms-robotics/src/voice/phrases/seed.py` — copy each `label` from `pmas-web-main/src/app/pages/robotics-chat/robotics-chat.ts` `decirQuickOptions` (same order) into `text`. Titles and icons from the spec table:

```python
SEED_ROWS: list[tuple[str, str, str]] = [
    (
        "Saludo Patria",
        "Saludos, Colegio Militar Patria. Aquí R-One reportándose. Sí, soy un androide, y no vengo de una película de ciencia ficción; fui creado en los laboratorios de la Universidad Libre por el increíble equipo de Ingeniería de Sistemas y Ciencia de Datos. Ellos me entrenaron con datos y me enseñaron a interactuar con el mundo. Quería pasar por aquí para enviarles un fuerte saludo a todos los estudiantes de bachillerato. Sigan preparándose con fuerza y honor, porque el mundo digital los necesita. ¡Procesando despedida... Cambio y fuera!",
        "",
    ),
    (
        "Patria en vivo",
        "Atención, Colegio Militar Patria! Aquí R-One transmitiendo en vivo y en directo. Sé lo que están pensando: ¿Un robot real hablando con nosotros?. ¡Afirmativo! Soy un androide programado y ensamblado por el dream team de Ingeniería de Sistemas y Ciencia de Datos de la Universidad Libre. Ellos me dieron los algoritmos y yo pongo la actitud. Un saludo gigante a todo el bachillerato. Sigan marchando hacia adelante y recuerden que los datos no mienten: ¡ustedes tienen un futuro brillante! Fin de la transmisión. ¡Boom!",
        "menu_book",
    ),
    (
        "Carreras Unilibre",
        "Atención, bachillerato del Colegio Militar Patria! Aquí R-One reportándose una vez más. Como ya saben, soy un androide y fui creado por las mentes brillantes de esta institución. Hoy vengo a desplegar en sus pantallas mi base de datos con los programas de ingeniería que la Universidad Libre tiene para ustedes. Abriendo archivo en 3, 2, 1... Primero: Ingeniería Ambiental, para proteger el planeta. Segundo: Ingeniería de Sistemas, mis creadores de código. Tercero: Ciencia de Datos, los cerebros de mi analítica. Cuarto: Ingeniería Industrial, para optimizar el mundo.Y quinto: Ingeniería Mecánica, los que me dieron mis piezas y movimiento. Un saludo gigante a todos. Si quieren construir el futuro como lo hicieron conmigo, ¡la Unilibre los espera! ¡Cerrando sistema... ¡Chao!",
        "menu_book",
    ),
    (
        "Invitación Facultad",
        "Atención, bachillerato del Colegio Militar Patria! Aquí R-One con un mensaje de alta prioridad. Ya conocen mi procedencia y las increíbles carreras que tenemos en la Universidad Libre: Ingeniería Ambiental, de Sistemas, Ciencia de Datos, Industrial y Mecánica. Ahora, mi sistema me indica que es momento de hacerles una invitación oficial. ¡Queremos que ustedes sean los próximos en crear tecnología! Los invito a estudiar en nuestra Facultad de Ingeniería. Si quieren aprender a diseñar robots como yo, a proteger el planeta o a dominar los datos del mundo, la Unilibre es su lugar. ¡Únanse al equipo del futuro! Procesando desconexión... ¡Chao!",
        "menu_book",
    ),
    (
        "Soy R-One",
        "Soy R-One, también llamado Federico, el asistente del semillero Prometeo.",
        "menu_book",
    ),
    (
        "Interactúe conmigo",
        "¡Puede interactuar conmigo en cualquier momento! Estoy aquí para orientarle, explicarle y acompañarle en lo que necesite. ¡Adelante, pregunte con total confianza!",
        "menu_book",
    ),
    (
        "Saludo corto",
        "Hola, es un gusto saludarle. Puedo ayudarle con información académica, tecnológica o administrativa.",
        "waving_hand",
    ),
    (
        "Sobre mí",
        "¡Le cuento un poco sobre mí! Soy R-One, también llamado Federico, un androide desarrollado por estudiantes de diferentes semestres de la Universidad Libre. Fui construido desde cero tomando como base la plataforma InMoov, y todas mis piezas fueron impresas en la universidad. Además, el software que me permite interactuar con usted también fue diseñado y desarrollado allí. ¡Soy el resultado del trabajo colaborativo, la innovación y el aprendizaje continuo!",
        "waving_hand",
    ),
    (
        "Robot pasando",
        "¡Permiso! ¡Robot pasando en mi nuevo carrito! Por favor, déjeme espacio para desplazarme con seguridad.",
        "directions_car",
    ),
    (
        "Mis creadores",
        "¡Ohh! ¡Aquí están mis creadores! Qué gusto ver al equipo que hizo posible mi desarrollo.",
        "groups",
    ),
    (
        "Miren, padres",
        "¡Miren, padres! ¡Soy famoso! Estoy representando con orgullo a la Universidad Libre en este evento.",
        "star",
    ),
    (
        "Hola Yohel",
        "¡Hola, Yohel! Te veo desde aquí. ¿Va a hacerle mantenimiento a mi código? ¡Espero que todo esté funcionando perfectamente!",
        "code",
    ),
    (
        "Hola Mauricio",
        "¡Hola, ingeniero Mauricio! Tengo entendido que usted es el director de Ingeniería de Sistemas. ¡Aquí estoy representando a la Universidad Libre con mucho orgullo! Si tienen preguntas, pueden acercarse a él o interactuar conmigo.",
        "school",
    ),
    (
        "Hola Marce",
        "¡Marce! Le cuento que ya he avanzado hasta sexto semestre de Ingeniería de Sistemas en la Universidad Libre. ¡El aprendizaje ha sido increíble!",
        "psychology",
    ),
    (
        "Hola Pablo",
        "¡Pablo! Por favor, no me saque del semillero Prometeo. ¡Aún tengo mucho por aprender y aportar!",
        "science",
    ),
    (
        "Hola Juan Manuel",
        "¡Juan Manuel! Necesito su ayuda, no estoy moviendo mis deditos correctamente. ¿Podría revisar mis servitos? Creo que requieren mantenimiento.",
        "build",
    ),
    (
        "Foto, sonrían",
        "¡Foooootoo! ¡Sonrían, por favor! Este es un gran momento para recordar.",
        "photo_camera",
    ),
    ("Hasta la vista", "¡Hasta la vista beibi!", "waving_hand"),
    (
        "La familia",
        "¡La familia es lo primero! Siempre es importante apoyarnos y crecer juntos.",
        "favorite",
    ),
    (
        "Stand Unilibre",
        "¡Atención, por favor! El stand de la Universidad Libre se encuentra en el pabellón 3, piso 2, stand 526. ¡Le invito a visitarnos y conocer más sobre nuestros proyectos!",
        "location_on",
    ),
    ("Acérquense", "¡Acerquence por favor! No muerdo ha ha ha", "location_on"),
    ("¿Quieren una foto?", "¡Quieren una foto? ¡Aquí estoy!", "location_on"),
    ("Qué bonita", "¡Que bonita! ¿Quieres que te saque una foto?", "location_on"),
    ("Hola guapos", "¡Hola guapos, como estan el dia de hoy!", "location_on"),
    (
        "Si puedo moverme",
        "Si puedo moverme, en estos dias sufri un problema pero en unas horas podre moverme con normalidad.",
        "location_on",
    ),
]
```

`pba-ms-robotics/src/voice/phrases/store.py`:

```python
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from src.voice.phrases.errors import PhraseError
from src.voice.phrases.models import Phrase
from src.voice.phrases.seed import SEED_ROWS

_ICON_RE = re.compile(r"^[a-z0-9_]+$")
_TITLE_MAX = 80
_TEXT_MAX = 2000


class PhraseStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(os.getenv("PHRASES_PATH", "/usr/src/app/data/phrases.json"))

    def list_phrases(self) -> list[Phrase]:
        return self._load()

    def create(self, title: str, text: str, icon: str = "") -> Phrase:
        items = self._load()
        next_id = max((item.id for item in items), default=0) + 1
        phrase = Phrase(
            id=next_id,
            title=self._clean_title(title),
            text=self._clean_text(text),
            icon=self._clean_icon(icon),
            active=True,
        )
        items.append(phrase)
        self._write(items)
        return phrase

    def update(self, phrase_id: int, patch: dict[str, str | None]) -> Phrase:
        items = self._load()
        phrase = self._find(items, phrase_id)
        if "title" in patch and patch["title"] is not None:
            phrase.title = self._clean_title(patch["title"])
        if "text" in patch and patch["text"] is not None:
            phrase.text = self._clean_text(patch["text"])
        if "icon" in patch:
            phrase.icon = self._clean_icon(patch["icon"] or "")
        self._write(items)
        return phrase

    def set_active(self, phrase_id: int, active: bool) -> Phrase:
        items = self._load()
        phrase = self._find(items, phrase_id)
        phrase.active = active
        self._write(items)
        return phrase

    def _load(self) -> list[Phrase]:
        if not self.path.exists():
            return self._seed()
        raw = self.path.read_text(encoding="utf-8")
        try:
            parsed: Any = json.loads(raw)
            items_raw = parsed["items"]
            items = [Phrase.model_validate(item) for item in items_raw]
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise PhraseError("Catálogo de frases corrupto", status_code=500) from exc
        if not items:
            return self._seed()
        return items

    def _seed(self) -> list[Phrase]:
        items = [
            Phrase(id=index, title=title, text=text, icon=icon, active=True)
            for index, (title, text, icon) in enumerate(SEED_ROWS, start=1)
        ]
        self._write(items)
        return items

    def _write(self, items: list[Phrase]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({"items": [item.model_dump() for item in items]}, ensure_ascii=False, indent=2)
        fd, tmp_name = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.write("\n")
            os.replace(tmp_name, self.path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    def _find(self, items: list[Phrase], phrase_id: int) -> Phrase:
        for item in items:
            if item.id == phrase_id:
                return item
        raise PhraseError(f"Frase {phrase_id} no encontrada", status_code=404)

    def _clean_title(self, value: str) -> str:
        title = value.strip()
        if not title or len(title) > _TITLE_MAX:
            raise PhraseError("Título inválido", status_code=400)
        return title

    def _clean_text(self, value: str) -> str:
        text = value.strip()
        if not text or len(text) > _TEXT_MAX:
            raise PhraseError("Texto inválido", status_code=400)
        return text

    def _clean_icon(self, value: str) -> str:
        icon = value.strip()
        if icon and _ICON_RE.fullmatch(icon) is None:
            raise PhraseError("Ícono inválido", status_code=400)
        return icon
```

In `pba-ms-robotics/src/core/settings/env.py`, after `ACTION_DESCRIPTIONS_PATH`:

```python
PHRASES_PATH: str = os.getenv("PHRASES_PATH", "/usr/src/app/data/phrases.json")
```

In `pba-ms-robotics/.env.template`, append:

```
# PHRASES_PATH=/usr/src/app/data/phrases.json
```

In `pba-ms-robotics/.gitignore`, append:

```
/data/phrases.json
```

Do not import `env.py` from `store.py`.

- [ ] **Step 4: Run tests to verify they pass**

```bash
docker compose exec pba-ms-robotics python -m pytest tests/test_phrase_store.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit in `pba-ms-robotics`**

```bash
git add src/voice/phrases tests/test_phrase_store.py src/core/settings/env.py .env.template .gitignore
git commit -m "Store Decir oración phrases in one robotics JSON catalog."
```

---

### Task 2: NATS phraseService

**Files:**
- Create: `pba-ms-robotics/src/voice/phrases/phrase_controller.py`
- Modify: `pba-ms-robotics/src/core/nats/nats_subscribers.py`

**Interfaces:**
- Consumes: `PhraseStore` from Task 1. `PhraseCreate`, `PhraseUpdate`, `PhraseSetActive` from `models.py`.
- Produces: NATS subjects `ROBOTICS_MS.phraseService.list|create|update|setActive`. `list` returns `{ "items": Phrase[] }`. create/update/setActive return one `Phrase` dict.

- [ ] **Step 1: Write the controller**

`pba-ms-robotics/src/voice/phrases/phrase_controller.py`:

```python
from __future__ import annotations

from typing import Any

from src.voice.phrases.models import PhraseCreate, PhraseSetActive, PhraseUpdate
from src.voice.phrases.store import PhraseStore


class PhraseController:
    def __init__(self, store: PhraseStore | None = None) -> None:
        self._store = store or PhraseStore()

    async def list_phrases(self, _: dict[str, Any]) -> dict[str, Any]:
        return {"items": [item.model_dump() for item in self._store.list_phrases()]}

    async def create_phrase(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = PhraseCreate.model_validate(data)
        return self._store.create(payload.title, payload.text, payload.icon or "").model_dump()

    async def update_phrase(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = PhraseUpdate.model_validate(data)
        patch: dict[str, str | None] = {}
        if "title" in payload.model_fields_set:
            patch["title"] = payload.title
        if "text" in payload.model_fields_set:
            patch["text"] = payload.text
        if "icon" in payload.model_fields_set:
            patch["icon"] = payload.icon
        return self._store.update(payload.id, patch).model_dump()

    async def set_active(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = PhraseSetActive.model_validate(data)
        return self._store.set_active(payload.id, payload.active).model_dump()
```

- [ ] **Step 2: Subscribe**

In `pba-ms-robotics/src/core/nats/nats_subscribers.py`, import and construct `PhraseController` next to `VoiceService`. Append these subscribers (keep `voiceService.speak` as it is):

```python
from src.voice.phrases.phrase_controller import PhraseController

# inside create_subscribers, after voice_service = ...
phrase_controller = PhraseController()

# append before return:
        NatsSubscriber(
            controller=phrase_controller.list_phrases,
            subject=f"{ROBOTICS_MS}.phraseService.list",
        ),
        NatsSubscriber(
            controller=phrase_controller.create_phrase,
            subject=f"{ROBOTICS_MS}.phraseService.create",
        ),
        NatsSubscriber(
            controller=phrase_controller.update_phrase,
            subject=f"{ROBOTICS_MS}.phraseService.update",
        ),
        NatsSubscriber(
            controller=phrase_controller.set_active,
            subject=f"{ROBOTICS_MS}.phraseService.setActive",
        ),
```

`PhraseError.status_code` is already mapped by `_rpc_error_payload` in `nats_client.py`. Do not change TTS.

- [ ] **Step 3: Re-run store tests**

```bash
docker compose exec pba-ms-robotics python -m pytest tests/test_phrase_store.py -v
```

Expected: 6 passed.

- [ ] **Step 4: Commit in `pba-ms-robotics`**

```bash
git add src/voice/phrases/phrase_controller.py src/core/nats/nats_subscribers.py
git commit -m "Expose phrase catalog over NATS phraseService."
```

---

### Task 3: Gateway HTTP `/voice/phrases`

**Files:**
- Create: `pba-ms-gateway/src/robotics-ms/voice/dto/phrase.dto.ts`
- Modify: `pba-ms-gateway/src/robotics-ms/voice/voice.controller.ts`

**Interfaces:**
- Consumes: NATS subjects from Task 2. JWT via existing `@UseGuards(JwtAuthGuard)` on `VoiceController`. No `RolesGuard`.
- Produces: `GET /voice/phrases` → `{ items }`. `POST /voice/phrases` `{ title, text, icon? }`. `PATCH /voice/phrases/:id` `{ title?, text?, icon? }` sent as `{ id, ...body }`. `PATCH /voice/phrases/:id/active` `{ active }` sent as `{ id, active }`.

- [ ] **Step 1: Add DTOs**

`pba-ms-gateway/src/robotics-ms/voice/dto/phrase.dto.ts`:

```typescript
import { IsBoolean, IsOptional, IsString, Matches, MaxLength, MinLength } from 'class-validator';

export class CreatePhraseDto {
  @IsString()
  @MinLength(1)
  @MaxLength(80)
  title: string;

  @IsString()
  @MinLength(1)
  @MaxLength(2000)
  text: string;

  @IsOptional()
  @IsString()
  @Matches(/^[a-z0-9_]*$/)
  icon?: string;
}

export class UpdatePhraseDto {
  @IsOptional()
  @IsString()
  @MinLength(1)
  @MaxLength(80)
  title?: string;

  @IsOptional()
  @IsString()
  @MinLength(1)
  @MaxLength(2000)
  text?: string;

  @IsOptional()
  @IsString()
  @Matches(/^[a-z0-9_]*$/)
  icon?: string;
}

export class SetPhraseActiveDto {
  @IsBoolean()
  active: boolean;
}
```

- [ ] **Step 2: Add routes on `VoiceController`**

Replace the imports and class body of `pba-ms-gateway/src/robotics-ms/voice/voice.controller.ts` with:

```typescript
import { Body, Controller, Get, Inject, Param, ParseIntPipe, Patch, Post, UseGuards } from '@nestjs/common';
import { ClientProxy, RpcException } from '@nestjs/microservices';
import { catchError } from 'rxjs';
import { NATS_SERVICE, ROBOTICS_MS } from 'src/core/constants/ms-names.constant';
import { SpeakPayload } from './dto/voice.dto';
import { CreatePhraseDto, SetPhraseActiveDto, UpdatePhraseDto } from './dto/phrase.dto';
import { JwtAuthGuard } from 'src/auth/guards';

@UseGuards(JwtAuthGuard)
@Controller('voice')
export class VoiceController {
  constructor(@Inject(NATS_SERVICE) private readonly client: ClientProxy) {}

  @Post('speak')
  async speak(@Body() body: SpeakPayload) {
    return this.client.send(`${ROBOTICS_MS}.voiceService.speak`, body).pipe(
      catchError((error) => {
        throw new RpcException(error);
      }),
    );
  }

  @Get('phrases')
  listPhrases() {
    return this.client.send(`${ROBOTICS_MS}.phraseService.list`, {}).pipe(
      catchError((error) => {
        throw new RpcException(error);
      }),
    );
  }

  @Post('phrases')
  createPhrase(@Body() body: CreatePhraseDto) {
    return this.client.send(`${ROBOTICS_MS}.phraseService.create`, body).pipe(
      catchError((error) => {
        throw new RpcException(error);
      }),
    );
  }

  @Patch('phrases/:id/active')
  setPhraseActive(@Param('id', ParseIntPipe) id: number, @Body() body: SetPhraseActiveDto) {
    return this.client.send(`${ROBOTICS_MS}.phraseService.setActive`, { id, active: body.active }).pipe(
      catchError((error) => {
        throw new RpcException(error);
      }),
    );
  }

  @Patch('phrases/:id')
  updatePhrase(@Param('id', ParseIntPipe) id: number, @Body() body: UpdatePhraseDto) {
    return this.client.send(`${ROBOTICS_MS}.phraseService.update`, { id, ...body }).pipe(
      catchError((error) => {
        throw new RpcException(error);
      }),
    );
  }
}
```

Keep `@Patch('phrases/:id/active')` above `@Patch('phrases/:id')`. Do not add `RolesGuard`. Leave `speak` as the first method.

- [ ] **Step 3: Typecheck**

```bash
cd pba-ms-gateway && npx tsc --noEmit -p tsconfig.build.json
```

Expected: exit 0.

- [ ] **Step 4: Commit in `pba-ms-gateway`**

```bash
git add src/robotics-ms/voice/dto/phrase.dto.ts src/robotics-ms/voice/voice.controller.ts
git commit -m "Add HTTP CRUD for Decir oración phrases."
```

---

### Task 4: Angular catalog and manage dialog

**Files:**
- Create: `pmas-web-main/src/app/pages/robotics-chat/decir-phrases.ts`
- Create: `pmas-web-main/src/app/pages/robotics-chat/decir-phrases.spec.ts`
- Modify: `pmas-web-main/src/app/pages/robotics-chat/robotics-chat.ts`
- Modify: `pmas-web-main/src/app/pages/robotics-chat/robotics-chat.html`

**Interfaces:**
- Consumes: `GET/POST/PATCH ${GATEWAY_URL}/voice/phrases` from Task 3. `Phrase { id, title, text, icon, active }`.
- Produces: `filterSpeakPhrases(items, query)` returns active items matching title or text. Card click calls `speakDecir(phrase.text)` without using the textarea as the source.

- [ ] **Step 1: Write the failing filter test**

`pmas-web-main/src/app/pages/robotics-chat/decir-phrases.spec.ts`:

```typescript
import { describe, expect, it } from 'vitest';
import { filterSpeakPhrases, type Phrase } from './decir-phrases';

const items: Phrase[] = [
  { id: 1, title: 'Saludo Patria', text: 'Saludos colegio', icon: '', active: true },
  { id: 2, title: 'Hasta la vista', text: 'beibi', icon: 'waving_hand', active: false },
  { id: 3, title: 'Stand', text: 'pabellón 3', icon: 'location_on', active: true },
];

describe('filterSpeakPhrases', () => {
  it('hides inactive phrases', () => {
    expect(filterSpeakPhrases(items, '').map((item) => item.id)).toEqual([1, 3]);
  });

  it('matches title or text', () => {
    expect(filterSpeakPhrases(items, 'pabellón').map((item) => item.id)).toEqual([3]);
    expect(filterSpeakPhrases(items, 'patria').map((item) => item.id)).toEqual([1]);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd pmas-web-main && npx ng test --watch=false --include=src/app/pages/robotics-chat/decir-phrases.spec.ts
```

Expected: FAIL — `decir-phrases` missing or `filterSpeakPhrases` not exported.

- [ ] **Step 3: Implement helper and wire the chat page**

`pmas-web-main/src/app/pages/robotics-chat/decir-phrases.ts`:

```typescript
export interface Phrase {
  id: number;
  title: string;
  text: string;
  icon: string;
  active: boolean;
}

export interface PhraseCatalog {
  items: Phrase[];
}

export function filterSpeakPhrases(items: Phrase[], query: string): Phrase[] {
  const needle = query.trim().toLowerCase();
  const active = items.filter((item) => item.active);
  if (!needle) return active;
  return active.filter(
    (item) => item.title.toLowerCase().includes(needle) || item.text.toLowerCase().includes(needle),
  );
}
```

In `robotics-chat.ts`:

1. Import `Phrase`, `PhraseCatalog`, `filterSpeakPhrases` from `./decir-phrases`.
2. **Delete** the entire `decirQuickOptions` array.
3. Replace phrase state and the computed with:

```typescript
  phrases = signal<Phrase[]>([]);
  phrasesLoadError = signal(false);
  manageOpen = signal(false);
  manageBusy = signal(false);
  manageError = signal<string | null>(null);
  editingId = signal<number | null>(null);
  formTitle = signal('');
  formText = signal('');
  formIcon = signal('');

  readonly filteredDecirQuickOptions = computed(() =>
    filterSpeakPhrases(this.phrases(), this.quickPhraseSearch()),
  );
```

4. Replace `sendDecir` / `applyDecirQuick` so the catalog never goes through the 400-char box:

```typescript
  sendDecir() {
    const text = this.decirInput().trim();
    if (!text || this.decirBusy()) return;
    this.decirInput.set('');
    this.speakDecir(text);
  }

  applyDecirQuick(phrase: Phrase) {
    this.speakDecir(phrase.text);
  }

  private speakDecir(text: string) {
    const spoken = text.trim();
    if (!spoken || this.decirBusy()) return;
    const entry: SentenceEntry = { text: spoken, timestamp: this.now(), status: 'sending' };
    this.decirHistory.update((history) => [entry, ...history]);
    this.decirBusy.set(true);
    this.shouldScrollDecir = true;
    this.http.post<{ status: string }>(`${GATEWAY_URL}/voice/speak`, { message: spoken }).subscribe({
      next: () => {
        this.decirHistory.update((history) =>
          history.map((item, index) => (index === 0 ? { ...item, status: 'done' } : item)),
        );
        this.decirBusy.set(false);
      },
      error: () => {
        this.decirHistory.update((history) =>
          history.map((item, index) => (index === 0 ? { ...item, status: 'error' } : item)),
        );
        this.decirBusy.set(false);
      },
    });
  }

  loadPhrases() {
    this.http.get<PhraseCatalog>(`${GATEWAY_URL}/voice/phrases`).subscribe({
      next: (body) => {
        this.phrases.set(body.items ?? []);
        this.phrasesLoadError.set(false);
      },
      error: () => {
        this.phrases.set([]);
        this.phrasesLoadError.set(true);
      },
    });
  }

  openManage() {
    this.manageError.set(null);
    this.editingId.set(null);
    this.formTitle.set('');
    this.formText.set('');
    this.formIcon.set('');
    this.manageOpen.set(true);
  }

  closeManage() {
    this.manageOpen.set(false);
  }

  startEdit(phrase: Phrase) {
    this.editingId.set(phrase.id);
    this.formTitle.set(phrase.title);
    this.formText.set(phrase.text);
    this.formIcon.set(phrase.icon);
    this.manageError.set(null);
  }

  savePhrase() {
    if (this.manageBusy()) return;
    const title = this.formTitle().trim();
    const text = this.formText().trim();
    const icon = this.formIcon().trim();
    if (!title || !text) {
      this.manageError.set('Título y texto son obligatorios.');
      return;
    }
    this.manageBusy.set(true);
    const body = { title, text, icon };
    const id = this.editingId();
    const request =
      id === null
        ? this.http.post<Phrase>(`${GATEWAY_URL}/voice/phrases`, body)
        : this.http.patch<Phrase>(`${GATEWAY_URL}/voice/phrases/${id}`, body);
    request.subscribe({
      next: () => {
        this.manageBusy.set(false);
        this.editingId.set(null);
        this.formTitle.set('');
        this.formText.set('');
        this.formIcon.set('');
        this.manageError.set(null);
        this.loadPhrases();
      },
      error: () => {
        this.manageBusy.set(false);
        this.manageError.set('No se pudo guardar la frase.');
      },
    });
  }

  setPhraseActive(phrase: Phrase, active: boolean) {
    if (this.manageBusy()) return;
    this.manageBusy.set(true);
    this.http.patch<Phrase>(`${GATEWAY_URL}/voice/phrases/${phrase.id}/active`, { active }).subscribe({
      next: () => {
        this.manageBusy.set(false);
        this.loadPhrases();
      },
      error: () => {
        this.manageBusy.set(false);
        this.manageError.set('No se pudo cambiar el estado.');
      },
    });
  }
```

5. In `ngOnInit`, after `loadChatRoute()`, call `this.loadPhrases();`.

There must be no remaining reference to `decirQuickOptions`.

- [ ] **Step 4: Update the template**

In `robotics-chat.html`, replace the “Frases rápidas” header + grid (the block that starts with `<p class="text-sm font-semibold text-on-surface">Frases rápidas</p>` through the empty-search `@if`) with:

```html
          <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-3">
            <p class="text-sm font-semibold text-on-surface">Frases rápidas</p>
            <div class="flex flex-col sm:flex-row gap-2 sm:items-center">
              <input
                [ngModel]="quickPhraseSearch()"
                (ngModelChange)="quickPhraseSearch.set($event)"
                placeholder="Buscar frase..."
                class="w-full sm:w-64 bg-surface-container-low border border-outline rounded-lg px-3 py-2 text-xs text-on-surface placeholder:text-on-surface-variant"/>
              <button
                type="button"
                (click)="openManage()"
                class="text-xs font-semibold px-3 py-2 rounded-lg border border-outline bg-surface-container hover:border-primary/40 hover:bg-primary/8 cursor-pointer">
                Gestionar frases
              </button>
            </div>
          </div>
          @if (phrasesLoadError()) {
            <p class="text-xs text-error mb-3">No se pudieron cargar las frases. Puedes escribir y decir igual.</p>
          }
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 mb-4">
            @for (opt of filteredDecirQuickOptions(); track opt.id) {
              <button
                (click)="applyDecirQuick(opt)"
                [disabled]="decirBusy()"
                class="flex flex-col items-start gap-2 p-3 rounded-xl border
                       border-outline bg-surface-container
                       hover:border-primary/40 hover:bg-primary/8
                       transition-all cursor-pointer text-left
                       disabled:opacity-40 disabled:cursor-not-allowed
                       active:scale-[0.97]">
                <span class="text-xs font-label text-on-surface leading-snug">
                  @if (opt.icon) {
                    <span class="material-symbols-outlined text-primary/70"
                          style="font-size: 0.8rem; font-variation-settings: 'FILL' 1;">{{ opt.icon }}</span>
                  }
                  {{ opt.title }}
                </span>
              </button>
            }
            @if (filteredDecirQuickOptions().length === 0 && !phrasesLoadError()) {
              <div class="col-span-full text-xs text-on-surface-variant border border-dashed border-outline rounded-lg px-3 py-4 text-center">
                No hay frases que coincidan con la búsqueda.
              </div>
            }
          </div>
```

Append this dialog as the last child of the Decir oración `@if (activeTab() === 'decir')` block (sibling of the column, still inside that `@if`):

```html
    @if (manageOpen()) {
      <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-rail/80"
           role="dialog" aria-labelledby="manage-phrases-title">
        <div class="w-full max-w-3xl max-h-[90vh] overflow-y-auto bg-surface rounded-xl border border-outline">
          <div class="flex items-center justify-between px-5 py-4 border-b border-outline bg-surface-container">
            <h3 id="manage-phrases-title" class="font-headline font-bold text-base text-on-surface">Gestionar frases</h3>
            <button type="button" (click)="closeManage()" class="p-2 rounded-lg text-on-surface-variant hover:bg-surface-container-high cursor-pointer">
              <span class="material-symbols-outlined" style="font-size: 1.125rem;">close</span>
            </button>
          </div>
          <div class="px-5 py-4 space-y-4">
            @if (manageError()) {
              <p class="text-sm text-error">{{ manageError() }}</p>
            }
            <div class="grid grid-cols-1 gap-3">
              <label class="text-xs font-semibold text-on-surface-variant">Título
                <input [ngModel]="formTitle()" (ngModelChange)="formTitle.set($event)" maxlength="80"
                       class="mt-1 w-full bg-background border border-outline rounded-lg px-3 py-2 text-sm text-on-surface outline-none"/>
              </label>
              <label class="text-xs font-semibold text-on-surface-variant">Texto hablado
                <textarea [ngModel]="formText()" (ngModelChange)="formText.set($event)" maxlength="2000" rows="4"
                          class="mt-1 w-full bg-background border border-outline rounded-lg px-3 py-2 text-sm text-on-surface outline-none resize-y"></textarea>
              </label>
              <label class="text-xs font-semibold text-on-surface-variant">Ícono Material (opcional)
                <input [ngModel]="formIcon()" (ngModelChange)="formIcon.set($event)" placeholder="waving_hand"
                       class="mt-1 w-full bg-background border border-outline rounded-lg px-3 py-2 text-sm text-on-surface outline-none"/>
              </label>
              <button type="button" (click)="savePhrase()" [disabled]="manageBusy()"
                      class="rounded-lg px-3 py-2 text-sm font-semibold bg-primary text-on-primary disabled:opacity-40 cursor-pointer">
                {{ editingId() === null ? 'Crear frase' : 'Guardar cambios' }}
              </button>
            </div>
            <ul class="divide-y divide-outline-variant border border-outline rounded-lg">
              @for (phrase of phrases(); track phrase.id) {
                <li class="flex flex-col sm:flex-row sm:items-center gap-2 px-3 py-3">
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-semibold text-on-surface">
                      @if (phrase.icon) {
                        <span class="material-symbols-outlined text-primary/70 align-middle"
                              style="font-size: 0.9rem;">{{ phrase.icon }}</span>
                      }
                      {{ phrase.title }}
                    </p>
                    <p class="text-xs text-on-surface-variant">{{ phrase.active ? 'Activa' : 'Inactiva' }}</p>
                  </div>
                  <div class="flex gap-2">
                    <button type="button" (click)="startEdit(phrase)" class="text-xs px-2 py-1 rounded-lg border border-outline cursor-pointer">Editar</button>
                    <button type="button" (click)="setPhraseActive(phrase, !phrase.active)" [disabled]="manageBusy()"
                            class="text-xs px-2 py-1 rounded-lg border border-outline cursor-pointer">
                      {{ phrase.active ? 'Desactivar' : 'Activar' }}
                    </button>
                  </div>
                </li>
              }
            </ul>
          </div>
        </div>
      </div>
    }
```

Do not add an Eliminar button. Leave the free-text textarea `maxlength="400"` as it is.

- [ ] **Step 5: Run tests**

```bash
cd pmas-web-main && npx ng test --watch=false --include=src/app/pages/robotics-chat/decir-phrases.spec.ts
```

Expected: 2 passed.

Then:

```bash
cd pmas-web-main && npx ng test --watch=false
```

Expected: existing suite still passes (including the 2 new tests).

- [ ] **Step 6: Commit in `pmas-web-main`**

```bash
git add src/app/pages/robotics-chat/decir-phrases.ts src/app/pages/robotics-chat/decir-phrases.spec.ts src/app/pages/robotics-chat/robotics-chat.ts src/app/pages/robotics-chat/robotics-chat.html
git commit -m "Load Decir oración phrases from robotics instead of a hardcoded list."
```

---

### Task 5: Launcher pointer

**Files:**
- Modify: launcher submodule SHAs after the three repo commits (only if this checkout tracks them).

**Interfaces:**
- Consumes: commits from Tasks 1–4.
- Produces: launcher `main` points at the new robotics, gateway, and web-main commits. Do not commit `pba-ms-robotics/data/phrases.json`.

- [ ] **Step 1: Point submodules and commit on the launcher**

```bash
git add pba-ms-robotics pba-ms-gateway pmas-web-main docs/superpowers/plans/2026-10-19-decir-oracion-phrases.md
git commit -m "Point submodules at the parametrized Decir oración catalog."
```

If a submodule has no new commit yet, do not stage it.

---

## Self-review

1. **Spec coverage:** JSON + seed (T1), NATS (T2), HTTP (T3), grid/dialog/speak-full-text (T4), anyone-with-JWT (T3), no delete (T4), corrupt 500 (T1), `speak` unchanged (T2/T3).
2. **Placeholders:** none. Seed texts are the current `decirQuickOptions` labels.
3. **Types:** `Phrase`, `PhraseStore.update(id, patch)`, NATS `phraseService.*`, HTTP `/voice/phrases` match across tasks.
