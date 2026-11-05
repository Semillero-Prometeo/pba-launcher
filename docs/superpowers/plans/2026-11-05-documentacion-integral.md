# Documentación integral de R-ONE — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Escribir `docs/project-docs/r-one-documentacion-integral.md`, un único documento que reemplaza a la memoria académica y explica R-ONE de cero a cien a un público mixto.

**Architecture:** Un área de trabajo ignorada por git (`docs/project-docs/.work/`) guarda el Word descomprimido, el clon de `pba-arduino-codes`, las notas de investigación por repositorio y tres scripts de verificación (`check_doc.py`, `ids.py`, `toc.py`) más el curador de imágenes (`figuras.py`). Primero se investiga y se cura; después se escribe un esqueleto con todos los encabezados y marcadores `<!-- pendiente: tarea N -->`; cada tarea de redacción reemplaza solo sus marcadores. Al final se genera la tabla de contenido, se archiva la memoria y se reapuntan `AGENTS.md` y `README.md`.

**Tech Stack:** Markdown con Mermaid, Python 3.13 (solo biblioteca estándar), Node 24 con `@mermaid-js/mermaid-cli`, `rg`, git.

**Spec:** `docs/superpowers/specs/2026-11-05-documentacion-integral-design.md`

## Global Constraints

- Entregable único: `docs/project-docs/r-one-documentacion-integral.md`. Imágenes en `docs/project-docs/assets/`.
- Solo cambian `docs/`, `.gitignore`, `AGENTS.md` y `README.md` del lanzador. Ningún repositorio hijo cambia.
- Si el código y otra fuente no coinciden, gana el código. Lo no verificable se escribe "pendiente de confirmar: <motivo>". Nunca se inventa un dato.
- Español natural, tercera persona, párrafos encadenados con conectores ("por eso", "en cambio", "a continuación", "dicho de otro modo", "de ahí que"). Listas solo para lo enumerable; tablas solo para datos cortos; la prosa explica el porqué.
- Patrón para lo complejo: (1) la idea en una frase, (2) una analogía o un ejemplo del propio R-ONE, (3) la referencia exacta en el código (ruta y función) y, si aplica, una fuente externa enlazada (documentación oficial de NATS, NestJS, Prisma, Angular, FastAPI, Ultralytics, BLIP en Hugging Face, Milvus, llama.cpp, Vosk, Piper).
- Las rutas de archivo se citan siempre relativas a la raíz del lanzador y entre comillas invertidas, por ejemplo `pmai-mai-core/src/pmai_core/api/interaction`. Así `check_doc.py` las verifica.
- Los identificadores de código (funciones, patrones NATS, variables de entorno) van entre comillas invertidas y escritos exactamente como en el código.
- Encabezados sin énfasis (`*`, `_`) para que las anclas sean estables.
- Diagramas en Mermaid: `flowchart` para bloques y decisiones, `sequenceDiagram` entre servicios, `stateDiagram-v2` para estados, `erDiagram` para Postgres. Etiquetas de nodos entre comillas dobles cuando tengan espacios, acentos o signos.
- Imágenes con pie numerado global debajo, en cursiva: `*Figura N. Descripción. Fuente: memoria académica 2026.*` La numeración de figuras es correlativa en todo el documento.
- Cada parte abre con un párrafo en blockquote que dice a quién va dirigida y qué puede saltarse.
- Invariantes del sistema que el texto nunca contradice (de `AGENTS.md`):
  - El chat HTTP y el micrófono entran por `MANAGEMENT_MS.chatService.chat`.
  - Turnos apagados o modelo `basico`: management usa OpenAI `chatStructured`, llama a `voiceService.speak` y responde `{ reply, fuente: "OpenAI", movimientos: [] }`.
  - Turnos encendidos y modelo `complejo`: reenvía a `MAI_CORE_MS.interactionService.ask`.
  - Persona de mayor confianza; empate por `id_global` menor; sin persona: `Persona no identificada` y sin imagen.
  - Recorte JPEG calidad 85 y BLIP; si BLIP falla, contexto vacío y se sigue.
  - `ROBOTICS_MS.actionService.getActions` lista pares completos (`category` + `blocks` + `blocks_neutro`) con `id`. Lista vacía: se habla y no se mueve; no es un fallo.
  - `responder()` en `pmai-model-vision-language/utils/main.py`: Milvus `conocimiento`, luego `interacciones` con coincidencia estricta; sin acierto, OpenAI si hay clave y red; si no, Gemma 4 E2B. Máximo 3 ids, solo del catálogo de esa llamada.
  - Robótica encola normal → 1 s → neutro → 1 s por id; la llamada regresa al encolar.
  - `fuente` ∈ `caché`, `OpenAI`, `Gemma (local)`, `ocupado`, `voz corta`, `disculpa`.
  - `chatService.declarePoema` no usa el turno, sigue en OpenAI y habla.
  - `PMAI_CORE_PYTHONPATH=/opt/model-context:/opt/action-model:/app/src`; la imagen de `pmai-core` se construye con contexto en la raíz del lanzador.
  - GGUF en `pmai-model-vision-language/models/gguf/gemma-4-E2B-it-Q4_K_M.gguf`, descargable de `unsloth/gemma-4-E2B-it-GGUF`.
  - Milvus Lite en `pmai-model-vision-language/utils/milvus/androide_milvus.db` (en el contenedor `MILVUS_DB_PATH=/data/milvus/androide_milvus.db`; verificar cuál manda y explicarlo).
  - `pmai-model-context` se importa como `model_context`; `pmai-model-vision-language` como `utils`.
- Commits en el lanzador, en español, en imperativo y con punto final, por ejemplo `git commit -m "Escribe la Parte I de la documentación integral."`.
- Tamaño objetivo total: 4.000–6.000 líneas.

## Plantillas compartidas

### Plantilla de notas de investigación

Cada archivo `docs/project-docs/.work/notes/<repositorio>.md` sigue exactamente esta forma. Cada hecho termina con su fuente `(ruta:línea)`.

```markdown
# <repositorio>

## Versión
Rama `<rama>`, commit `<hash corto>` (`git -C <repositorio> log -1 --format='%h %ad %s' --date=short`).

## Propósito
Qué resuelve y qué no le toca (2–4 frases).

## Tecnología
Lenguaje, framework y versiones relevantes, tomadas de `package.json` o `pyproject.toml`.

## Árbol
Carpetas hasta el nivel de módulo, una línea por carpeta con su función.

## Archivos clave
Punto de entrada primero. Ruta y propósito en una línea.

## Contratos expuestos
Patrón NATS, endpoint HTTP o WebSocket; carga de entrada; respuesta; archivo que lo implementa.

## Contratos consumidos
Patrón o endpoint que llama, a qué servicio y desde qué archivo.

## Configuración
Variable o clave de ajustes, valor por defecto, quién la lee.

## Datos
Esquemas, archivos JSON, colecciones o modelos en disco que posee.

## Pruebas
Comando exacto (tomado de `package.json`/`pyproject.toml`), qué cubren los archivos de prueba y, si se ejecutaron, el resultado.

## Trampas
Invariantes, errores conocidos y cosas que no se deben romper.

## Hechos para los flujos
Pasos que este repositorio aporta a los flujos de la Parte II (login, ruta Básico, turno, micrófono, gesto, visión, estudio, poema).

## Pendiente de confirmar
Lo que no se pudo verificar y por qué.
```

### Comandos de investigación por tecnología

NestJS (`pba-ms-gateway`, `pba-ms-auth`, `pba-ms-management`):

```bash
R=pba-ms-management
rg -n "@(MessagePattern|EventPattern)\(" $R/src
rg -n "\.send\(|\.emit\(" $R/src --glob '*.ts'
rg -n "@(Controller|Get|Post|Put|Patch|Delete)\(" $R/src
rg -n "process\.env\." $R/src
ls $R/prisma && cat $R/prisma/schema.prisma 2>/dev/null
jq .scripts,.dependencies $R/package.json
```

Python con NATS (`pba-ms-robotics`, `pmai-mai-core`):

```bash
R=pba-ms-robotics
rg -ln "NatsSubscriber\(" $R/src
rg -n "subject\s*=|subject=" $R/src
rg -n "nest_request|\.request\(" $R/src
rg -n "os\.environ|getenv|settings\." $R/src | head -80
sed -n '/\[project\]/,/^\[/p' $R/pyproject.toml
```

Angular (`pmas-web-main`):

```bash
rg -n "path:" pmas-web-main/src/app/app.routes.ts
rg -n "http\.(get|post|put|patch|delete)|WebSocket|webSocket\(" pmas-web-main/src/app
rg -n "apiUrl|baseUrl|environment" pmas-web-main/src/app/config pmas-web-main/src/app/core
```

FastAPI (`pmas-web-motion-studio`, `pba-ms-robotics/src/app.py`):

```bash
rg -n "@(app|router)\.(get|post|put|patch|delete|websocket)\(" pmas-web-motion-studio/src pba-ms-robotics/src
```

### Verificación estándar de una tarea de redacción

```bash
cd /home/personal/Projects/ulibre-prometeo/pba-launcher
python3 docs/project-docs/.work/check_doc.py --mermaid docs/project-docs/r-one-documentacion-integral.md
```

Expected: la última línea es `check_doc: 0 errores, <P> pendientes, <C> por confirmar, <M> bloques mermaid`, y `<P>` bajó respecto a la tarea anterior.

```bash
rg -c "<!-- pendiente: tarea <N> -->" docs/project-docs/r-one-documentacion-integral.md
```

Expected: sin salida (cero coincidencias) para el número de la tarea en curso.

```bash
python3 docs/project-docs/.work/ids.py docs/project-docs/r-one-documentacion-integral.md --desde "<encabezado inicial>" --hasta "<encabezado siguiente>"
```

Expected: `ids: <n> citados, <m> sin encontrar`. Cada identificador sin encontrar se corrige o se justifica en el mensaje de cierre de la tarea (por ejemplo, es un concepto y no un símbolo de código).

---

### Task 1: Área de trabajo y verificador del documento

**Files:**
- Modify: `.gitignore`
- Create: `docs/project-docs/.work/check_doc.py`
- Create: `docs/project-docs/.work/test_check_doc.py`
- Create: `docs/project-docs/.work/ids.py`
- Create: `docs/project-docs/.work/toc.py`

**Interfaces:**
- Produces: `check_doc.slug(text: str) -> str` (ancla estilo GitHub); `check_doc.check(text: str, doc_dir: Path, final: bool = False) -> dict` con claves `errors: list[str]`, `pending: int`, `confirm: int`, `mermaid: list[tuple[int, str]]`, `anchors: set[str]`; CLI `check_doc.py [--final] [--mermaid] <doc>`; CLI `ids.py <doc> --desde <texto> [--hasta <texto>]`; CLI `toc.py <doc>`.

- [ ] **Step 1: Ignorar el área de trabajo y el Word archivado**

Añadir al final de `.gitignore`:

```gitignore

# documentación integral: área de trabajo y Word archivado
docs/project-docs/.work/
docs/project-docs/archivo/*.docx
```

Run: `mkdir -p docs/project-docs/.work/notes && git status --short docs/project-docs`
Expected: `.work/` no aparece como sin seguimiento.

- [ ] **Step 2: Escribir las pruebas del verificador**

Crear `docs/project-docs/.work/test_check_doc.py`:

```python
import tempfile
from pathlib import Path

import check_doc as cd


def run(text, final=False, files=()):
    with tempfile.TemporaryDirectory() as d:
        for f in files:
            p = Path(d) / f
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"x")
        return cd.check(text, Path(d), final=final)


def kinds(res):
    return sorted({e.split(" ", 1)[0] for e in res["errors"]})


def test_slug_accents():
    assert cd.slug("1. Qué es R-ONE y por qué existe") == "1-qué-es-r-one-y-por-qué-existe"
    assert cd.slug("Anexo C. Patrones `NATS`") == "anexo-c-patrones-nats"
    assert cd.slug("Parte I. Entender R-ONE") == "parte-i-entender-r-one"


def test_clean_doc():
    text = (
        "# T\n\n## Parte I. Entender R-ONE\n\n"
        "Ver [arriba](#parte-i-entender-r-one).\n\n"
        "![f](assets/a.png)\n\n"
        "Archivo `pmai-mai-core/settings.toml`.\n\n"
        "```mermaid\nflowchart LR\n  A --> B\n```\n"
    )
    res = run(text, files=["assets/a.png"])
    assert res["errors"] == [], res["errors"]
    assert len(res["mermaid"]) == 1


def test_duplicate_headings():
    assert run("## Propósito\n\n## Propósito\n\n[x](#propósito-1)\n")["errors"] == []


def test_broken_anchor():
    assert kinds(run("## A\n\n[x](#b)\n")) == ["ancla"]


def test_missing_image():
    assert kinds(run("![f](assets/no.png)\n")) == ["imagen"]


def test_bad_launcher_path():
    assert kinds(run("`pmai-mai-core/no-existe.py`\n")) == ["ruta"]


def test_path_with_line_suffix():
    assert run("`pmai-mai-core/settings.toml:1`\n")["errors"] == []


def test_non_launcher_path_ignored():
    assert run("`src/app.ts` y `utils/main.py`\n")["errors"] == []


def test_markers_are_case_sensitive():
    assert kinds(run("Falta TBD aquí.\n")) == ["marcador"]
    assert run("Todo el sistema y todo lo demás.\n")["errors"] == []


def test_unclosed_fence():
    assert kinds(run("```python\nx = 1\n")) == ["bloque"]


def test_pending_markers():
    text = "<!-- pendiente: tarea 8 -->\n"
    res = run(text)
    assert res["errors"] == [] and res["pending"] == 1
    assert kinds(run(text, final=True)) == ["pendiente"]


def test_fenced_content_ignored():
    assert run("```\n[x](#nope) TBD `pmai-mai-core/nada`\n```\n")["errors"] == []


def test_confirm_count():
    assert run("Esto es pendiente de confirmar: falta el firmware.\n")["confirm"] == 1


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
    print("todas las pruebas pasan")
```

- [ ] **Step 3: Ejecutar las pruebas y ver que fallan**

Run: `cd docs/project-docs/.work && python3 test_check_doc.py`
Expected: `ModuleNotFoundError: No module named 'check_doc'`.

- [ ] **Step 4: Implementar `check_doc.py`**

Crear `docs/project-docs/.work/check_doc.py`:

```python
#!/usr/bin/env python3
"""Verificador del documento integral de R-ONE.

  python3 docs/project-docs/.work/check_doc.py docs/project-docs/r-one-documentacion-integral.md
  python3 docs/project-docs/.work/check_doc.py --final --mermaid docs/project-docs/r-one-documentacion-integral.md
"""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
ALIASES = {"pba-arduino-codes": WORK / "pba-arduino-codes"}
TOP = {p.name for p in ROOT.iterdir()} | set(ALIASES)

FENCE = re.compile(r"^\s*(```|~~~)")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
LINK = re.compile(r"(!?)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
INLINE_CODE = re.compile(r"`([^`\n]+)`")
MARKER = re.compile(r"\b(TBD|TODO|FIXME|XXX)\b")
LOREM = re.compile(r"lorem ipsum", re.IGNORECASE)
PENDING = re.compile(r"<!--\s*pendiente:[^>]*-->")
CONFIRM = re.compile(r"pendiente de confirmar", re.IGNORECASE)
LINE_SUFFIX = re.compile(r":\d+(-\d+)?$")


def slug(text: str) -> str:
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = text.replace("`", "").strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def check_path(token: str) -> bool | None:
    if "/" not in token or "://" in token or any(c in token for c in "*<>{}$|"):
        return None
    token = LINE_SUFFIX.sub("", token).rstrip("/")
    first, _, rest = token.partition("/")
    if first not in TOP:
        return None
    base = ALIASES.get(first)
    target = base / rest if base else ROOT / token
    return target.exists()


def check(text: str, doc_dir: Path, final: bool = False) -> dict:
    errors: list[str] = []
    counts: dict[str, int] = {}
    anchors: set[str] = set()
    links: list[tuple[int, str, str]] = []
    codes: list[tuple[int, str]] = []
    mermaid: list[tuple[int, str]] = []
    pending = confirm = 0
    in_fence, lang, start, buf = False, "", 0, []

    for n, line in enumerate(text.splitlines(), 1):
        if FENCE.match(line):
            if not in_fence:
                in_fence, lang, start, buf = True, line.strip()[3:].strip().lower(), n, []
            else:
                in_fence = False
                if lang == "mermaid":
                    mermaid.append((start, "\n".join(buf)))
            continue
        if in_fence:
            buf.append(line)
            continue
        h = HEADING.match(line)
        if h:
            base = slug(h.group(2))
            seen = counts.get(base, 0)
            anchors.add(base if seen == 0 else f"{base}-{seen}")
            counts[base] = seen + 1
        links += [(n, m.group(1), m.group(2)) for m in LINK.finditer(line)]
        codes += [(n, m.group(1)) for m in INLINE_CODE.finditer(line)]
        if MARKER.search(line) or LOREM.search(line):
            errors.append(f"marcador línea {n}: {line.strip()[:80]}")
        if PENDING.search(line):
            pending += 1
            if final:
                errors.append(f"pendiente línea {n}: {line.strip()[:80]}")
        confirm += len(CONFIRM.findall(line))

    if in_fence:
        errors.append(f"bloque línea {start}: bloque de código sin cerrar")
    for n, bang, target in links:
        if target.startswith("#"):
            if unquote(target[1:]) not in anchors:
                errors.append(f"ancla línea {n}: {target}")
        elif re.match(r"^[a-z]+:", target):
            continue
        elif not (doc_dir / unquote(target.split("#", 1)[0])).exists():
            errors.append(f"{'imagen' if bang else 'enlace'} línea {n}: {target}")
    for n, token in codes:
        if check_path(token) is False:
            errors.append(f"ruta línea {n}: {token}")
    return {"errors": errors, "pending": pending, "confirm": confirm,
            "mermaid": mermaid, "anchors": anchors}


def run_mermaid(blocks: list[tuple[int, str]]) -> list[str]:
    mmdc = WORK / "node" / "node_modules" / ".bin" / "mmdc"
    if not mmdc.exists():
        return ["mermaid: falta mmdc; npm --prefix docs/project-docs/.work/node install @mermaid-js/mermaid-cli"]
    out = WORK / "mermaid"
    out.mkdir(exist_ok=True)
    cfg = WORK / "puppeteer.json"
    cfg.write_text('{"args": ["--no-sandbox"]}', encoding="utf-8")
    errors = []
    for i, (line, block) in enumerate(blocks, 1):
        src = out / f"{i:03d}.mmd"
        src.write_text(block, encoding="utf-8")
        r = subprocess.run([str(mmdc), "-q", "-p", str(cfg), "-i", str(src),
                            "-o", str(out / f"{i:03d}.svg")], capture_output=True, text=True)
        if r.returncode != 0:
            msg = (r.stderr or r.stdout).strip().splitlines()
            errors.append(f"mermaid línea {line}: {msg[0] if msg else 'error'}")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("doc")
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--mermaid", action="store_true")
    a = ap.parse_args()
    doc = Path(a.doc).resolve()
    res = check(doc.read_text(encoding="utf-8"), doc.parent, final=a.final)
    errors = res["errors"] + (run_mermaid(res["mermaid"]) if a.mermaid else [])
    for e in errors:
        print(f"ERROR {e}")
    print(f"check_doc: {len(errors)} errores, {res['pending']} pendientes, "
          f"{res['confirm']} por confirmar, {len(res['mermaid'])} bloques mermaid")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Ejecutar las pruebas y ver que pasan**

Run: `cd docs/project-docs/.work && python3 test_check_doc.py`
Expected: una línea `ok test_...` por prueba y al final `todas las pruebas pasan`.

- [ ] **Step 6: Implementar `ids.py`**

Crear `docs/project-docs/.work/ids.py`:

```python
#!/usr/bin/env python3
"""Busca en el código cada identificador citado entre comillas invertidas en una parte del documento."""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
IDENT = re.compile(r"^[A-Za-z_][\w.]*(\(\))?$")


def found(token: str) -> bool:
    base = ["rg", "-F", "-q", "--glob", "!docs/**", "--glob", "!**/node_modules/**",
            "--glob", "!**/dist/**", "--", token]
    if subprocess.run(base + [str(ROOT)]).returncode == 0:
        return True
    arduino = WORK / "pba-arduino-codes"
    return arduino.exists() and subprocess.run(
        ["rg", "-F", "-q", "--no-ignore", "--", token, str(arduino)]).returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("doc")
    ap.add_argument("--desde", required=True)
    ap.add_argument("--hasta")
    a = ap.parse_args()
    text = Path(a.doc).read_text(encoding="utf-8")
    start = text.index(a.desde)
    end = text.index(a.hasta, start + 1) if a.hasta else len(text)
    part = re.sub(r"```.*?```", "", text[start:end], flags=re.S)
    tokens = sorted({t.removesuffix("()") for t in re.findall(r"`([^`\n]+)`", part) if IDENT.match(t)})
    tokens = [t for t in tokens if len(t) >= 4 and ("_" in t or "." in t or any(c.isupper() for c in t[1:]))]
    missing = [t for t in tokens if not found(t) and not ("." in t and found(t.split(".")[-1]))]
    for t in missing:
        print(f"SIN ENCONTRAR {t}")
    print(f"ids: {len(tokens)} citados, {len(missing)} sin encontrar")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Run: `printf '# x\n\n`responder` `MILVUS_DB_PATH` `noExisteNada_123`\n' > /tmp/ids.md && python3 docs/project-docs/.work/ids.py /tmp/ids.md --desde "# x"`
Expected: `SIN ENCONTRAR noExisteNada_123` y `ids: 2 citados, 1 sin encontrar` (`responder` queda fuera por no tener mayúscula interna, guion bajo ni punto).

- [ ] **Step 7: Implementar `toc.py`**

Crear `docs/project-docs/.work/toc.py`:

```python
#!/usr/bin/env python3
"""Regenera la tabla de contenido entre <!-- toc:inicio --> y <!-- toc:fin -->."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_doc import FENCE, HEADING, slug  # noqa: E402

START, END = "<!-- toc:inicio -->", "<!-- toc:fin -->"


def build(text: str) -> str:
    counts: dict[str, int] = {}
    items, in_fence = [], False
    for line in text.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        h = None if in_fence else HEADING.match(line)
        if not h:
            continue
        level, title = len(h.group(1)), h.group(2)
        base = slug(title)
        seen = counts.get(base, 0)
        anchor = base if seen == 0 else f"{base}-{seen}"
        counts[base] = seen + 1
        if level in (2, 3) and title != "Tabla de contenido":
            items.append(f"{'  ' * (level - 2)}- [{title.replace('`', '')}](#{anchor})")
    return "\n".join(items)


def main() -> int:
    doc = Path(sys.argv[1])
    text = doc.read_text(encoding="utf-8")
    head, _, rest = text.partition(START)
    _, _, tail = rest.partition(END)
    doc.write_text(f"{head}{START}\n{build(text)}\n{END}{tail}", encoding="utf-8")
    print("toc regenerada")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Run: `printf '# D\n\n## Tabla de contenido\n\n<!-- toc:inicio -->\n<!-- toc:fin -->\n\n## Parte I. Uno\n\n### 1. Qué\n' > /tmp/toc.md && python3 docs/project-docs/.work/toc.py /tmp/toc.md && cat /tmp/toc.md`
Expected: entre los marcadores aparecen `- [Parte I. Uno](#parte-i-uno)` y `  - [1. Qué](#1-qué)`.

- [ ] **Step 8: Instalar el validador de Mermaid**

Run: `npm --prefix docs/project-docs/.work/node install @mermaid-js/mermaid-cli && printf '```mermaid\nflowchart LR\n  A --> B\n```\n' > /tmp/m.md && python3 docs/project-docs/.work/check_doc.py --mermaid /tmp/m.md`
Expected: `check_doc: 0 errores, 0 pendientes, 0 por confirmar, 1 bloques mermaid`.
Si la descarga de Chromium falla por red, repetir el comando con `full_network`. Si sigue fallando, dejarlo anotado en el cierre de la tarea; las tareas siguientes usarán `check_doc.py` sin `--mermaid` y revisarán cada bloque a mano contra la sintaxis de [mermaid.js.org](https://mermaid.js.org/intro/syntax-reference.html).

- [ ] **Step 9: Commit**

```bash
git add .gitignore
git commit -m "Ignora el área de trabajo de la documentación integral."
```

---

### Task 2: Catálogo y curaduría de las imágenes del Word

**Files:**
- Create: `docs/project-docs/.work/figuras.py`
- Create: `docs/project-docs/.work/figuras.tsv` (generado y luego editado)
- Create: `docs/project-docs/assets/fig-*.{png,jpeg,jpg}`

**Interfaces:**
- Consumes: el `.docx` en `docs/project-docs/` o en `docs/project-docs/archivo/`.
- Produces: `docs/project-docs/.work/figuras.tsv` con columnas `ilustracion	medio	pie	decision	destino`; imágenes `docs/project-docs/assets/fig-<parte>-<tema>[-n].<ext>` que las tareas 8–14 incrustan. La tabla con `decision=conservar` es la lista autorizada de figuras.

- [ ] **Step 1: Escribir `figuras.py`**

```python
#!/usr/bin/env python3
"""Catálogo de ilustraciones del Word original y copia de las curadas a assets/.

  python3 docs/project-docs/.work/figuras.py catalogar
  python3 docs/project-docs/.work/figuras.py copiar
"""
from __future__ import annotations

import csv
import re
import shutil
import sys
import zipfile
from pathlib import Path

WORK = Path(__file__).resolve().parent
PROJECT_DOCS = WORK.parent
ASSETS = PROJECT_DOCS / "assets"
TSV = WORK / "figuras.tsv"
DOCX = "1. Documentación del Proyecto - Inteligencia Artificial Multimodal y Robótica Autonoma (1).docx"
NAME = re.compile(r"fig-[a-z0-9-]+\.(png|jpe?g)")


def docx_path() -> Path:
    for p in (PROJECT_DOCS / DOCX, PROJECT_DOCS / "archivo" / DOCX):
        if p.exists():
            return p
    sys.exit("No encuentro el .docx")


def catalogar() -> None:
    out = WORK / "docx"
    with zipfile.ZipFile(docx_path()) as z:
        z.extractall(out)
    rels_xml = (out / "word/_rels/document.xml.rels").read_text(encoding="utf-8")
    rels = {}
    for tag in re.findall(r"<Relationship [^>]*>", rels_xml):
        rid = re.search(r'Id="([^"]+)"', tag).group(1)
        target = re.search(r'Target="([^"]+)"', tag).group(1)
        if target.startswith("media/"):
            rels[rid] = target
    doc = (out / "word/document.xml").read_text(encoding="utf-8")
    rows, pending, last = [], [], "inicio"
    for para in re.findall(r"<w:p[ >].*?</w:p>", doc, re.S):
        pending += [rels[r] for r in re.findall(r'r:embed="([^"]+)"', para) if r in rels]
        text = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", para)).strip()
        m = re.match(r"Ilustraci[oó]n\s*(\d+)", text)
        if m and pending:
            rows += [[m.group(1), media, text, "", ""] for media in pending]
            pending, last = [], m.group(1)
    rows += [[f"sin-pie-tras-{last}", media, "", "", ""] for media in pending]
    with TSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["ilustracion", "medio", "pie", "decision", "destino"])
        w.writerows(rows)
    print(f"{len(rows)} imágenes catalogadas en {TSV}")


def copiar() -> None:
    ASSETS.mkdir(exist_ok=True)
    copied = 0
    with TSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if row["decision"] not in ("conservar", "descartar"):
                sys.exit(f"decisión vacía o inválida para {row['medio']}")
            if row["decision"] == "descartar":
                continue
            if not NAME.fullmatch(row["destino"]):
                sys.exit(f"destino inválido para {row['medio']}: {row['destino']!r}")
            if Path(row["destino"]).suffix.lstrip(".") != Path(row["medio"]).suffix.lstrip("."):
                sys.exit(f"la extensión de {row['destino']} no coincide con {row['medio']}")
            shutil.copyfile(WORK / "docx" / "word" / row["medio"], ASSETS / row["destino"])
            copied += 1
    print(f"{copied} imágenes copiadas a {ASSETS}")


if __name__ == "__main__":
    {"catalogar": catalogar, "copiar": copiar}[sys.argv[1]]()
```

- [ ] **Step 2: Catalogar**

Run: `python3 docs/project-docs/.work/figuras.py catalogar`
Expected: `191 imágenes catalogadas en …/figuras.tsv` (176 con pie y unas 15 `sin-pie-tras-123`; el número exacto puede variar en ±2 por imágenes reutilizadas como `image130.png`).

- [ ] **Step 3: Curar abriendo cada candidata**

Abrir cada imagen candidata con la herramienta de lectura de imágenes (`docs/project-docs/.work/docx/word/media/imageN.png`) y llenar `decision` y `destino` en `figuras.tsv`. Criterio: se conserva solo si es legible y explica algo que sigue siendo cierto hoy.

Punto de partida por número de ilustración (confirmar viendo la imagen):

| Ilustraciones | Decisión inicial | Motivo |
|---|---|---|
| 2–4, 6–20, 22, 23 | descartar | Pantallas y código de la interfaz anterior al rediseño navy del 2026-10-14 |
| 5, 21, 24, 25 | revisar | Diagramas de topología, CMS, petición HTTP y visión; conservar solo si coinciden con el código actual |
| 26–42, 44–51 | descartar | Instalación de ffmpeg y Label Studio paso a paso; la Parte VI lo resume en prosa |
| 43, 52, 53, 54, 55, 56, 57, 61 | conservar | Ejemplos de extracción y etiquetado, estructura y tamaño del dataset |
| 58–60, 62–76 | descartar | Capturas de git y de código |
| 77 | revisar una por una (image89–image121) | Conservar curvas y matrices de resultados del entrenamiento (`results`, matriz de confusión, curvas PR/F1, lotes de validación) |
| 78–82, 84–92, 95–98, 100–102, 104, 106, 107, 109 | descartar | Capturas de código y de notebooks |
| 83 | conservar | Visión integrada en R-ONE |
| 93, 94, 99, 103, 105, 108, 110–113 | conservar | Métricas y resultados de BLIP, alucinaciones y palabras protegidas |
| 114–123 | conservar | Diagramas del modelo de acción; si alguno contradice el turno actual, va a la Parte VI con nota |
| sin-pie-tras-123 | revisar | Probablemente métricas del modelo de acción |

Nombres de destino: `fig-<parte>-<tema>[-n].<ext>` en minúsculas sin acentos, con la extensión del medio original. Ejemplos: `fig-vi-etiquetado-ejemplo-1.jpeg`, `fig-vi-yolo-matriz-confusion.png`, `fig-vi-blip-alucinaciones.png`, `fig-ii-vision-tiempo-real.png`.

- [ ] **Step 4: Copiar las conservadas**

Run: `python3 docs/project-docs/.work/figuras.py copiar && ls docs/project-docs/assets | wc -l && du -sh docs/project-docs/assets`
Expected: `<n> imágenes copiadas` con `<n>` entre 30 y 80, y un tamaño razonable (menos de 15 MB). Si supera 15 MB, revisar si hay curvas repetidas y descartar duplicados.

- [ ] **Step 5: Commit**

```bash
git add docs/project-docs/assets
git commit -m "Añade las ilustraciones curadas de la memoria académica."
```

---

### Task 3: Clonar `pba-arduino-codes` en el área de trabajo

**Files:**
- Create: `docs/project-docs/.work/pba-arduino-codes/` (clon, ignorado por git)

**Interfaces:**
- Produces: el árbol del firmware en `docs/project-docs/.work/pba-arduino-codes`, que `check_doc.py` y `ids.py` resuelven para rutas que empiezan con `pba-arduino-codes/`.

- [ ] **Step 1: Clonar la rama `dev`**

Run: `git clone --branch dev https://github.com/Semillero-Prometeo/pba-arduino-codes.git docs/project-docs/.work/pba-arduino-codes || git clone https://github.com/Semillero-Prometeo/pba-arduino-codes.git docs/project-docs/.work/pba-arduino-codes`
Expected: `Cloning into …` sin errores. Si GitHub pide credenciales o responde 404, detener la tarea, anotarlo y seguir: la ficha 20 se escribirá desde lo que `pba-ms-robotics` espera del firmware y quedará marcada "pendiente de confirmar: repositorio no accesible".

- [ ] **Step 2: Comprobar**

Run: `git -C docs/project-docs/.work/pba-arduino-codes log -1 --format='%h %ad %s' --date=short && find docs/project-docs/.work/pba-arduino-codes -name '*.ino' | head`
Expected: un commit y al menos un `.ino`.

No hay commit: el clon está ignorado.

---

### Task 4: Notas de investigación — lanzador, web, gateway y auth

**Files:**
- Create: `docs/project-docs/.work/notes/pba-launcher.md`
- Create: `docs/project-docs/.work/notes/pmas-web-main.md`
- Create: `docs/project-docs/.work/notes/pba-ms-gateway.md`
- Create: `docs/project-docs/.work/notes/pba-ms-auth.md`

**Interfaces:**
- Produces: cuatro notas con la "Plantilla de notas de investigación" completa. Las tareas 8–14 citan solo hechos que estén en estas notas o que verifiquen en el código.

Esta tarea es independiente de las tareas 5 y 6 y puede ejecutarse en paralelo con ellas.

- [ ] **Step 1: `pba-launcher.md`**

Fuentes obligatorias: `docker-compose.yml` (9 servicios, puertos, volúmenes, variables, `depends_on`, `privileged`), `.env.template` (todas las variables, sin copiar valores secretos de `.env`), `nats.conf`, `.dockerignore`, `.gitmodules` (url y rama de cada submódulo), cada script en `scripts/` (leerlo entero: qué hace, argumentos, efectos), `README.md`, `AGENTS.md`, `.cursor/rules/*.mdc`, `PRODUCT.md`, `DESIGN.md`, `docs/project-docs/jetson-orin-nano-r-one.md`, `data/` (qué contiene y quién lo monta). En "Árbol" describir cada carpeta de primer nivel.

- [ ] **Step 2: `pmas-web-main.md`**

Fuentes: `pmas-web-main/package.json`, `angular.json`, `src/main.ts`, `src/app/app.config.ts`, `src/app/app.routes.ts`, `src/app/config/`, `src/app/core/{services,guards,interceptors,models,constants}`, cada carpeta de `src/app/pages/` y `src/app/components/`, `src/app/layouts/admin-shell`, `src/styles.css`. Registrar: cada ruta con su guard y página; cada servicio con los endpoints o WebSocket que llama; cómo se guarda el token; cómo el chat elige ruta (picker Básico/Complejo); cómo se incrusta el estudio en `/sequences` (iframe al puerto `MOTION_STUDIO_PORT`); el cajón de runtime del hardware (`hardware-runtime-drawer`); el QR de red (`lan-share-modal`).

- [ ] **Step 3: `pba-ms-gateway.md`**

Fuentes: `pba-ms-gateway/src/main.ts`, `src/app.module.ts`, `src/transports/`, `src/auth/{strategies,guards}`, `src/core/`, y cada controlador en `src/auth-ms`, `src/robotics-ms`, `src/mai-core-ms` y los de management (buscar con `rg -n "@Controller\(" pba-ms-gateway/src`). Registrar para cada endpoint HTTP: método, ruta completa con prefijo global, guard/rol, patrón NATS al que reenvía y servicio destino. Revisar si el gateway usa su propia `DATABASE_URL`/Prisma y para qué.

- [ ] **Step 4: `pba-ms-auth.md`**

Fuentes: `pba-ms-auth/prisma/schema.prisma` (modelos, relaciones, enums completos), `prisma/migrations` (lista), seed (buscar con `rg -ln "seed" pba-ms-auth` y `scripts/seed-auth.sh`), `src/main.ts`, cada módulo (`auth`, `users`, `person`, `roles`, `app-settings`, `document-types`) con sus `@MessagePattern`. Registrar: cómo se firma y valida el JWT (`SECRET`, expiración), restauración de contraseña (`RESTORE_PASSWORD_SECRET`), roles ADMIN y USER, tipos de documento (cédula, tarjeta de identidad, otro), usuarios sembrados.

- [ ] **Step 5: Verificar las rutas citadas**

Run: `for f in docs/project-docs/.work/notes/{pba-launcher,pmas-web-main,pba-ms-gateway,pba-ms-auth}.md; do python3 docs/project-docs/.work/check_doc.py "$f"; done`
Expected: cuatro líneas `check_doc: 0 errores, …`.

Run: `rg -L "^## Pendiente de confirmar" docs/project-docs/.work/notes/{pba-launcher,pmas-web-main,pba-ms-gateway,pba-ms-auth}.md`
Expected: sin salida (todas las notas tienen la plantilla completa).

No hay commit: las notas están ignoradas.

---

### Task 5: Notas de investigación — management, robótica, firmware y estudio

**Files:**
- Create: `docs/project-docs/.work/notes/pba-ms-management.md`
- Create: `docs/project-docs/.work/notes/pba-ms-robotics.md`
- Create: `docs/project-docs/.work/notes/pba-arduino-codes.md`
- Create: `docs/project-docs/.work/notes/pmas-web-motion-studio.md`

**Interfaces:**
- Consumes: el clon de la Task 3.
- Produces: cuatro notas con la "Plantilla de notas de investigación" completa.

Esta tarea es independiente de las tareas 4 y 6 y puede ejecutarse en paralelo con ellas.

- [ ] **Step 1: `pba-ms-management.md`**

Fuentes: `pba-ms-management/src/chat/` entero (`chat.controller.ts`, servicio, DTOs), `src/openai-integration/` (incluidos `schema` y `constants`), `src/ms-mai-core-integration/`, `src/ms-robotics-integration/`, `src/ms-auth-integration/`, `src/core/settings`, `prisma/schema.prisma`, `data/` (almacén JSON de la ruta del chat). Registrar: la lógica exacta que decide entre `basico` y `complejo` y dónde se guarda; `chatStructured` y su esquema; `declarePoema`; los patrones `chatService.*` expuestos y los que consume (`interactionService.ask`, `voiceService.speak`); `OPENAI_SYSTEM_PROMPT` y `OPENAI_MODEL`; los CRUD de frases "Decir oración" (buscar `rg -n "oraci|phrase" pba-ms-management/src pba-ms-robotics/src`).

- [ ] **Step 2: `pba-ms-robotics.md`**

Fuentes: `pba-ms-robotics/src/app.py`, `src/core/nats/{nats_client.py,nats_subscribers.py,nest_request.py}`, `src/core/settings`, `src/action/`, `src/sequence/`, `src/voice/{tts,output,phrases,utils}`, `data/` (JSON canónico de secuencias y su forma: `id`, `category`, `blocks`, `blocks_neutro`, descripción), `tests/`. Registrar: cada sujeto NATS suscrito con su controlador; `getActions` y qué filtra (pares completos con `id`, qué pasa con JSON legado); `executeAction` y la cola normal → 1 s → neutro → 1 s (`tests/test_playback_queue.py`); Detener; el snapshot de runtime (duración de paso, bloques actuales); cómo habla con el Arduino (puerto serie, baudios, detección del puerto, formato de comando, PCA9685); los modos de TTS (`VOICE_TTS_MODE`, OpenAI TTS, Piper `PIPER_MODEL_PATH`, eSpeak `ESPEAK_VOICE`) y la salida por PulseAudio/Bluetooth (`PULSE_SERVER`); `VOICE_SKIP_PLAYBACK`; `ACTION_DESCRIPTIONS_PATH` y por qué el turno no lo usa.

- [ ] **Step 3: `pba-arduino-codes.md`**

Fuentes: el clon en `docs/project-docs/.work/pba-arduino-codes` (cada `.ino`/`.h`, README). Registrar: placa, bibliotecas, mapa de canales del PCA9685 por servo, límites de ángulo, protocolo serie (formato exacto de un comando y de su respuesta), baudios, y cómo se corresponde con lo que envía `pba-ms-robotics`. Citar rutas como `pba-arduino-codes/<ruta>`. Si la Task 3 no pudo clonar, llenar la nota desde el lado de robótica y marcar todo el firmware como "pendiente de confirmar: repositorio no accesible".

- [ ] **Step 4: `pmas-web-motion-studio.md`**

Fuentes: `pmas-web-motion-studio/src/app.py`, `src/static/` (HTML, JS como `library-view.js`, `editor.css`), `data/`, `interfaz_record9_5_1.py`, `start-studio.bat`, `tests/`, README. Registrar: endpoints FastAPI; cómo se graba una secuencia (origen + descripción), cómo guarda el par normal/neutro y la "rebobinada" al neutro; cómo llega la secuencia a robótica (ingesta con `id`) y qué JSON escribe; cómo se incrusta en Angular; qué es `interfaz_record9_5_1.py` (herramienta de escritorio histórica o vigente).

- [ ] **Step 5: Verificar las rutas citadas**

Run: `for f in docs/project-docs/.work/notes/{pba-ms-management,pba-ms-robotics,pba-arduino-codes,pmas-web-motion-studio}.md; do python3 docs/project-docs/.work/check_doc.py "$f"; done`
Expected: cuatro líneas `check_doc: 0 errores, …`.

Run: `rg -L "^## Pendiente de confirmar" docs/project-docs/.work/notes/{pba-ms-management,pba-ms-robotics,pba-arduino-codes,pmas-web-motion-studio}.md`
Expected: sin salida.

---

### Task 6: Notas de investigación — núcleo e inteligencia artificial

**Files:**
- Create: `docs/project-docs/.work/notes/pmai-mai-core.md`
- Create: `docs/project-docs/.work/notes/pmai-model-context.md`
- Create: `docs/project-docs/.work/notes/pmai-model-vision-language.md`
- Create: `docs/project-docs/.work/notes/pmai-model-vision.md`

**Interfaces:**
- Produces: cuatro notas con la "Plantilla de notas de investigación" completa.

Esta tarea es independiente de las tareas 4 y 5 y puede ejecutarse en paralelo con ellas.

- [ ] **Step 1: `pmai-mai-core.md`**

Fuentes: `pmai-mai-core/settings.toml` (todas las claves con su significado), `pyproject.toml`, `Dockerfile.dev` (por qué el contexto es la raíz del lanzador; qué copia de `pmai-model-context` y `pmai-model-vision-language`), `src/pmai_core/__main__.py` o punto de entrada, `src/pmai_core/{api,resources,pipeline,domain,core,messaging,models}`. Registrar: cada carpeta de `api/` (health, monitoring, vision, camera, management_ms, robotics_ms, audio, interaction) con sus sujetos NATS; `interaction_turn.py` paso a paso (elección de persona, recorte JPEG 85, BLIP, `getActions`, `responder()`, `speak`, `executeAction`, valores de `fuente`, umbral de voz corta de 14 caracteres, turno ocupado, frases de "pensando" del último commit); el pipeline de visión (fuentes de cámara, YOLO, seguimiento, ReID, `id_global`, confianza); el micrófono (Vosk `vosk-model-small-es-0.42`, cómo detecta fin de frase, cómo despacha a `chatService.chat`); cómo llega el video a la pantalla (WebSocket o NATS, puerto `PMAI_CORE_PORT`); `watchfiles`; variables `OMP/MKL/OPENBLAS_NUM_THREADS`.

- [ ] **Step 2: `pmai-model-context.md`**

Fuentes: `pmai-model-context/model_context/`, `pyproject.toml`, `tests/`, `objetos/`, `main.ipynb` (solo para la historia), README. Registrar: modelo BLIP exacto (id de Hugging Face), cuantización, parámetros de generación, palabras protegidas y filtros de alucinación, API pública que llama mai-core, y por qué el paquete se llama `model_context` (choque con `utils`).

- [ ] **Step 3: `pmai-model-vision-language.md`**

Fuentes: `pmai-model-vision-language/utils/main.py` (`responder()` completo), `utils/{encoder,milvus,gpt,gguf,ollama,context_builder,webscraping}`, `utils/personalizacion.py`, `prompt/`, `models/`, `data/` (`aperturas.json`), `app.py`, `pyproject.toml`, `tests/`, `docs/`, README, `advice.txt`. Registrar: modelo de embeddings y dimensión; esquema y umbrales de `conocimiento` e `interacciones`; coincidencia estricta; qué se guarda y qué no (el nombre no se indexa); `milvus_caido`; `backend` openai/gguf; modelo OpenAI (`gpt-4o-mini`); carga singleton del GGUF y descarga desde Hugging Face (`GGUF_HF_REPO`, `GGUF_HF_FILENAME`); construcción del prompt con `{catalogo_movimientos}`; personalización (`_etiqueta_real`, `_anteponer_nombre`, `UMBRAL_APERTURA`); `load_dotenv(..., override=False)`; las dos fases de web scraping y `preguntas_respuestas.json`; `scripts/seed-conocimiento.sh` y `cargar_preguntas.py`; qué es `utils/ollama` y `utils/stt-tts_to_test` (vigente o histórico); las dos rutas de Milvus (`androide_milvus.db` en la raíz y en `utils/milvus/`) y cuál usa el contenedor.

- [ ] **Step 4: `pmai-model-vision.md`**

Fuentes: `pmai-model-vision/README.md`, `data.yaml` (25 clases con sus nombres), `utils/`, `requirements.txt`, `main.ipynb`, `my_model/`, `runs/` (métricas finales: buscar `results.csv` y leer la última fila), `docs/project-docs/model-vision-project.md`. Registrar: fases del detector, 802 imágenes, partición train/val, hiperparámetros de entrenamiento, métricas (mAP50, mAP50-95, precisión, recall), qué peso usa mai-core y dónde vive.

- [ ] **Step 5: Verificar las rutas citadas**

Run: `for f in docs/project-docs/.work/notes/{pmai-mai-core,pmai-model-context,pmai-model-vision-language,pmai-model-vision}.md; do python3 docs/project-docs/.work/check_doc.py "$f"; done`
Expected: cuatro líneas `check_doc: 0 errores, …`.

Run: `rg -L "^## Pendiente de confirmar" docs/project-docs/.work/notes/{pmai-mai-core,pmai-model-context,pmai-model-vision-language,pmai-model-vision}.md`
Expected: sin salida.

---

### Task 7: Esqueleto del documento

**Files:**
- Create: `docs/project-docs/r-one-documentacion-integral.md`

**Interfaces:**
- Consumes: la sección "Versión" de las 12 notas.
- Produces: todos los encabezados definitivos (las anclas que el resto de tareas enlaza) y un marcador `<!-- pendiente: tarea N -->` bajo cada encabezado que redacta la tarea N.

- [ ] **Step 1: Escribir el esqueleto**

Crear el archivo con exactamente este contenido, reemplazando solo la tabla de versiones con los datos reales de las notas (rama, commit corto, fecha):

````markdown
# R-ONE: documentación integral

Semillero de investigación Prometeo · Facultad de Ingeniería · Universidad Libre, seccional Bogotá

<!-- pendiente: tarea 8 -->

## Cómo leer este documento

<!-- pendiente: tarea 8 -->

## Versión documentada

| Repositorio | Rama | Commit | Fecha |
|---|---|---|---|
| `pba-launcher` | main | … | … |
| `pmas-web-main` | dev | … | … |
| `pba-ms-gateway` | dev | … | … |
| `pba-ms-auth` | dev | … | … |
| `pba-ms-management` | dev | … | … |
| `pba-ms-robotics` | dev | … | … |
| `pmai-mai-core` | dev | … | … |
| `pmai-model-context` | dev | … | … |
| `pmai-model-vision-language` | dev | … | … |
| `pmai-model-vision` | dev | … | … |
| `pmas-web-motion-studio` | dev | … | … |
| `pba-arduino-codes` | dev | … | … |

## Tabla de contenido

<!-- toc:inicio -->
<!-- toc:fin -->

## Parte I. Entender R-ONE

<!-- pendiente: tarea 8 -->

### 1. Qué es R-ONE y por qué existe

#### 1.1 El semillero Prometeo

<!-- pendiente: tarea 8 -->

#### 1.2 Objetivos del proyecto

<!-- pendiente: tarea 8 -->

#### 1.3 Qué puede hacer R-ONE hoy

<!-- pendiente: tarea 8 -->

### 2. El sistema en una página

<!-- pendiente: tarea 8 -->

### 3. Recorrido de una pregunta

<!-- pendiente: tarea 8 -->

### 4. Conceptos clave

#### 4.1 Microservicios y gateway

<!-- pendiente: tarea 8 -->

#### 4.2 NATS y los patrones de mensaje

<!-- pendiente: tarea 8 -->

#### 4.3 Sesión y JWT

<!-- pendiente: tarea 8 -->

#### 4.4 Detección, seguimiento y reidentificación

<!-- pendiente: tarea 8 -->

#### 4.5 Descripción de escena

<!-- pendiente: tarea 8 -->

#### 4.6 Embeddings y búsqueda vectorial

<!-- pendiente: tarea 8 -->

#### 4.7 Caché semántico

<!-- pendiente: tarea 8 -->

#### 4.8 Modelo local frente a modelo en la nube

<!-- pendiente: tarea 8 -->

#### 4.9 Secuencias, bloques y el par normal y neutro

<!-- pendiente: tarea 8 -->

## Parte II. Arquitectura y flujos

<!-- pendiente: tarea 9 -->

### 5. Mapa de servicios

#### 5.1 Servicios y puertos

<!-- pendiente: tarea 9 -->

#### 5.2 Canales de comunicación

<!-- pendiente: tarea 9 -->

### 6. Flujos

#### 6.1 Inicio de sesión

<!-- pendiente: tarea 9 -->

#### 6.2 Chat por la ruta Básico

<!-- pendiente: tarea 9 -->

#### 6.3 Chat por la ruta Complejo: el turno

<!-- pendiente: tarea 9 -->

#### 6.4 El micrófono

<!-- pendiente: tarea 9 -->

#### 6.5 Ciclo de un gesto

<!-- pendiente: tarea 9 -->

#### 6.6 Visión en tiempo real

<!-- pendiente: tarea 9 -->

#### 6.7 Creación e ingesta de una secuencia

<!-- pendiente: tarea 9 -->

#### 6.8 Declarar un poema

<!-- pendiente: tarea 9 -->

### 7. Datos y persistencia

#### 7.1 Postgres y Prisma

<!-- pendiente: tarea 9 -->

#### 7.2 Milvus Lite

<!-- pendiente: tarea 9 -->

#### 7.3 Secuencias en JSON

<!-- pendiente: tarea 9 -->

#### 7.4 Ruta del chat

<!-- pendiente: tarea 9 -->

#### 7.5 Modelos de IA en disco

<!-- pendiente: tarea 9 -->

## Parte III. Repositorios

<!-- pendiente: tarea 10 -->

### 8. Cómo leer una ficha

<!-- pendiente: tarea 10 -->

### 9. pba-launcher

<!-- pendiente: tarea 10 -->

### 10. pmas-web-main

<!-- pendiente: tarea 10 -->

### 11. pba-ms-gateway

<!-- pendiente: tarea 10 -->

### 12. pba-ms-auth

<!-- pendiente: tarea 10 -->

### 13. pba-ms-management

<!-- pendiente: tarea 10 -->

### 14. pba-ms-robotics

<!-- pendiente: tarea 10 -->

### 15. pmai-mai-core

<!-- pendiente: tarea 11 -->

### 16. pmai-model-context

<!-- pendiente: tarea 11 -->

### 17. pmai-model-vision-language

<!-- pendiente: tarea 11 -->

### 18. pmai-model-vision

<!-- pendiente: tarea 11 -->

### 19. pmas-web-motion-studio

<!-- pendiente: tarea 11 -->

### 20. pba-arduino-codes

<!-- pendiente: tarea 11 -->

## Parte IV. Despliegue y operación

<!-- pendiente: tarea 12 -->

### 21. Requisitos y configuración

<!-- pendiente: tarea 12 -->

### 22. Arranque local y en red local

<!-- pendiente: tarea 12 -->

### 23. La Jetson Orin Nano

<!-- pendiente: tarea 12 -->

### 24. Solución de problemas

<!-- pendiente: tarea 12 -->

## Parte V. Producto e identidad visual

<!-- pendiente: tarea 13 -->

### 25. Para quién es la interfaz

<!-- pendiente: tarea 13 -->

### 26. Principios y voz

<!-- pendiente: tarea 13 -->

### 27. Paleta, tipografía y accesibilidad

<!-- pendiente: tarea 13 -->

## Parte VI. Evolución e investigación

<!-- pendiente: tarea 13 -->

### 28. Stakeholders e hitos

<!-- pendiente: tarea 13 -->

### 29. El detector de objetos

#### 29.1 Captura y extracción de imágenes

<!-- pendiente: tarea 13 -->

#### 29.2 Etiquetado en Label Studio

<!-- pendiente: tarea 13 -->

#### 29.3 Análisis del dataset

<!-- pendiente: tarea 13 -->

#### 29.4 Limpieza y preprocesamiento

<!-- pendiente: tarea 13 -->

#### 29.5 Entrenamiento y aumento de datos

<!-- pendiente: tarea 13 -->

#### 29.6 Resultados

<!-- pendiente: tarea 13 -->

#### 29.7 Despliegue en mai-core

<!-- pendiente: tarea 13 -->

### 30. El modelo contextual

#### 30.1 Elección del modelo

<!-- pendiente: tarea 13 -->

#### 30.2 Pruebas de BLIP-base y Geospace

<!-- pendiente: tarea 13 -->

#### 30.3 Optimización e inferencia

<!-- pendiente: tarea 13 -->

#### 30.4 Alucinaciones y palabras protegidas

<!-- pendiente: tarea 13 -->

### 31. El modelo de acción

#### 31.1 Fase de análisis

<!-- pendiente: tarea 13 -->

#### 31.2 Ingesta por web scraping

<!-- pendiente: tarea 13 -->

#### 31.3 Búsqueda semántica y caché

<!-- pendiente: tarea 13 -->

#### 31.4 Ingeniería del prompt

<!-- pendiente: tarea 13 -->

#### 31.5 Métricas

<!-- pendiente: tarea 13 -->

### 32. La primera interfaz y las decisiones descartadas

<!-- pendiente: tarea 13 -->

## Anexos

### Anexo A. Glosario

<!-- pendiente: tarea 14 -->

### Anexo B. Variables de entorno

<!-- pendiente: tarea 14 -->

### Anexo C. Patrones NATS

<!-- pendiente: tarea 14 -->

### Anexo D. Endpoints HTTP del gateway

<!-- pendiente: tarea 14 -->

### Anexo E. Índice de figuras y diagramas

<!-- pendiente: tarea 14 -->
````

Dentro de cada ficha de la Parte III, la tarea que la redacta crea estos subencabezados de nivel 4, numerados con el número de la ficha: `Propósito`, `Versión`, `Tecnología`, `Árbol`, `Archivos clave`, `Contratos`, `Configuración`, `Pruebas`, `Trampas` (por ejemplo `#### 15.6 Contratos`).

- [ ] **Step 2: Verificar y generar la tabla de contenido provisional**

Run: `python3 docs/project-docs/.work/toc.py docs/project-docs/r-one-documentacion-integral.md && python3 docs/project-docs/.work/check_doc.py docs/project-docs/r-one-documentacion-integral.md`
Expected: `toc regenerada` y `check_doc: 0 errores, 80 pendientes, 0 por confirmar, 0 bloques mermaid` (17 de la tarea 8, 16 de la 9, 8 de la 10, 6 de la 11, 5 de la 12, 23 de la 13 y 5 de la 14).

- [ ] **Step 3: Commit**

```bash
git add docs/project-docs/r-one-documentacion-integral.md
git commit -m "Crea el esqueleto de la documentación integral de R-ONE."
```

---

### Task 8: Parte I — Entender R-ONE

**Files:**
- Modify: `docs/project-docs/r-one-documentacion-integral.md` (introducción, "Cómo leer este documento" y Parte I; solo los marcadores `tarea 8`)

**Interfaces:**
- Consumes: las 12 notas; capítulo 1 de la memoria (`docs/project-docs/1. Documentación del Proyecto - Inteligencia Artificial Multimodal y Robótica Autonoma.md`, líneas 401–455); `docs/project-docs/high-level-architecture.png`; `docs/project-docs/project-start-plan.png`.
- Produces: las anclas de conceptos de la sección 4 (por ejemplo `#46-embeddings-y-búsqueda-vectorial`), que las Partes II y III enlazan en lugar de reexplicar.

- [ ] **Step 1: Introducción y "Cómo leer este documento"**

Introducción (1–2 párrafos): qué es este documento, que reemplaza a la memoria académica (archivada en `docs/project-docs/archivo/`) y que refleja la versión de la tabla "Versión documentada". "Cómo leer": una tabla de rutas de lectura por perfil (visitante o evaluador: Partes I y V; operador: Partes I y IV; desarrollador nuevo: I, II, III y anexos; investigador: I y VI), y una nota sobre convenciones (rutas relativas al lanzador, "pendiente de confirmar").

- [ ] **Step 2: Sección 1**

1.1: el semillero, la universidad, el equipo de la memoria (Johel Arias, Andrea López, Anyi Becerra, Daniela Fierro, Evelin Sánchez) y el contexto. 1.2: objetivo general y específicos de la memoria, reescritos en prosa y con una frase de estado actual por objetivo (cumplido, parcial, pendiente) sustentada en el código. 1.3: capacidades actuales en prosa: ver con varias cámaras, reconocer a las personas entre cámaras, describir la escena, responder por voz y chat, gesticular con secuencias, administrar usuarios y un estudio para crear movimientos.

- [ ] **Step 3: Sección 2 con diagrama**

Un `flowchart LR` con cuatro grupos (`subgraph`): Percepción (cámaras, micrófono), Núcleo (`pmai-core`), Servicios (gateway, auth, management, robotics, Postgres, NATS) y Cuerpo e interfaz (Arduino y servos, parlante, `pmas-web-main`, `pmas-web-motion-studio`). Incrustar `high-level-architecture.png` como Figura 1 si coincide con el código actual; si no, citarla en la Parte VI y explicarlo aquí en una frase. Dos o tres párrafos que recorran el diagrama de izquierda a derecha.

- [ ] **Step 4: Sección 3, recorrido narrado**

Relato en presente, de 600–900 palabras: Laura (persona de ejemplo) se para frente a R-ONE y pregunta "¿qué es la Universidad Libre?". Cubrir en orden los pasos 1–6 del turno de `AGENTS.md` con el detalle real de las notas: la cámara la detecta y le asigna `id_global`, el micrófono transcribe con Vosk, management decide la ruta, mai-core elige a la persona y recorta la imagen, BLIP la describe ("una mujer con chaqueta azul frente a una pared"), robótica entrega el catálogo, Milvus encuentra la pregunta en `conocimiento`, se antepone el nombre, robótica habla y ejecuta el gesto con su neutro, y la pantalla muestra `fuente: caché`. Cerrar con dos variaciones cortas: qué cambia si la pregunta es nueva (OpenAI o Gemma) y qué pasa si la ruta es Básico. Incluir un `flowchart TD` simplificado de 8–10 nodos que enlace con la sección 6.3.

- [ ] **Step 5: Sección 4, conceptos**

Para cada subsección 4.1–4.9, 2–4 párrafos con el patrón de tres pasos de las restricciones globales y al menos una fuente externa enlazada. Analogías sugeridas: gateway como recepción de un edificio; NATS como un conmutador telefónico con extensiones (`request`/`reply` frente a `emit`); JWT como manilla de un evento; ReID como reconocer a alguien que cambia de sala por la ropa; embeddings como coordenadas de significado; caché semántico como el ejemplo de Milvus del spec; local frente a nube como una calculadora de bolsillo frente a una llamada a un experto; par normal y neutro como hacer un gesto y volver a la postura de descanso. Cada subsección termina con "En R-ONE:" y la ruta del código.

- [ ] **Step 6: Verificar**

Run: `python3 docs/project-docs/.work/check_doc.py --mermaid docs/project-docs/r-one-documentacion-integral.md && rg -c "<!-- pendiente: tarea 8 -->" docs/project-docs/r-one-documentacion-integral.md; python3 docs/project-docs/.work/ids.py docs/project-docs/r-one-documentacion-integral.md --desde "## Parte I. Entender R-ONE" --hasta "## Parte II. Arquitectura y flujos"`
Expected: `check_doc: 0 errores, …`; `rg` sin salida; `ids:` con cada "sin encontrar" corregido o justificado.

Leer de nuevo la Parte I completa como lo haría un evaluador que no programa: ninguna sigla sin explicar en su primera aparición y ningún párrafo que sea solo una lista disfrazada.

- [ ] **Step 7: Commit**

```bash
git add docs/project-docs/r-one-documentacion-integral.md
git commit -m "Escribe la Parte I de la documentación integral."
```

---

### Task 9: Parte II — Arquitectura y flujos

**Files:**
- Modify: `docs/project-docs/r-one-documentacion-integral.md` (solo los marcadores `tarea 9`)

**Interfaces:**
- Consumes: las 12 notas (secciones "Contratos" y "Hechos para los flujos"); `docker-compose.yml`; anclas de la sección 4.
- Produces: anclas `#61-inicio-de-sesión` … `#75-modelos-de-ia-en-disco`, que la Parte III y la Parte IV enlazan.

- [ ] **Step 1: Apertura y sección 5**

Blockquote de audiencia (desarrolladores y operadores curiosos). 5.1: tabla de los 9 servicios de Compose (servicio, repositorio, tecnología, puerto(s) con su variable, puerto de depuración 9230–9233, dependencias) y un párrafo por grupo explicando el porqué de cada uno. 5.2: un `flowchart LR` con todos los servicios y una arista por canal real, rotulada `HTTP`, `NATS`, `WebSocket`, `iframe`, `serie` o `PulseAudio`; después, un párrafo sobre cómo Nest y Python comparten NATS (el formato `{ pattern, data }` de `pba-ms-robotics/src/core/nats/nest_request.py`).

- [ ] **Step 2: Flujos 6.1–6.4**

Cada flujo: un párrafo que lo sitúa, un `sequenceDiagram` con nombres reales de patrones y endpoints, y 2–4 párrafos con los casos de error. 6.1: navegador → gateway → `pba-ms-auth` → Postgres; token, guards, "Tu sesión venció. Entra de nuevo.". 6.2: ruta Básico con `chatStructured`, `voiceService.speak` y la respuesta exacta. 6.3: ruta Complejo con los pasos 1–6, más un `stateDiagram-v2` del turno cuyos estados finales son las seis `fuente`, y una tabla `fuente` → cuándo ocurre. 6.4: Vosk, umbral de 14 caracteres, turno ocupado, frases de "pensando" y entrada por el mismo `chatService.chat`.

- [ ] **Step 3: Flujos 6.5–6.8**

6.5: `stateDiagram-v2` de un gesto (encolado → normal → espera 1 s → neutro → espera 1 s → libre; Detener desde cualquier estado) y el diagrama de secuencia de `executeAction` con varios ids. Explicar por qué mai-core no espera y por qué la interfaz no inicia otro movimiento mientras el hardware está ocupado. 6.6: de la cámara a la pantalla (captura, YOLO, seguimiento, ReID, transporte a Angular). Incrustar una figura curada de visión si `figuras.tsv` la conserva. 6.7: el estudio graba origen y descripción, guarda el par, robótica lo ingesta con `id` y desde ese momento aparece en `getActions`. 6.8: `declarePoema` en OpenAI, que sí habla y por qué no pasa por el turno.

- [ ] **Step 4: Sección 7**

7.1: `erDiagram` con todos los modelos Prisma de auth (y de gateway o management si tienen esquema propio), más un párrafo por entidad. 7.2: las colecciones `conocimiento` e `interacciones` (campos, dimensión, métrica, umbrales), un `flowchart TD` de la consulta y la explicación de la ruta del archivo `.db` dentro y fuera del contenedor. 7.3: un ejemplo real recortado del JSON canónico de una secuencia (de `pba-ms-robotics/data/`) en un bloque `json`, explicado campo por campo. 7.4: dónde y cómo se guarda la elección Básico/Complejo y quién la cambia. 7.5: tabla de modelos (archivo o id, tamaño aproximado, quién lo carga, de dónde se descarga y cuándo).

- [ ] **Step 5: Verificar**

Run: `python3 docs/project-docs/.work/check_doc.py --mermaid docs/project-docs/r-one-documentacion-integral.md && rg -c "<!-- pendiente: tarea 9 -->" docs/project-docs/r-one-documentacion-integral.md; python3 docs/project-docs/.work/ids.py docs/project-docs/r-one-documentacion-integral.md --desde "## Parte II. Arquitectura y flujos" --hasta "## Parte III. Repositorios"`
Expected: `check_doc: 0 errores, …` con al menos 12 bloques Mermaid nuevos; `rg` sin salida; cada identificador sin encontrar corregido o justificado.

Contrastar los invariantes de las restricciones globales uno por uno con la Parte II: ninguno contradicho.

- [ ] **Step 6: Commit**

```bash
git add docs/project-docs/r-one-documentacion-integral.md
git commit -m "Escribe la Parte II de la documentación integral."
```

---

### Task 10: Parte III — fichas 8 a 14

**Files:**
- Modify: `docs/project-docs/r-one-documentacion-integral.md` (solo los marcadores `tarea 10`)

**Interfaces:**
- Consumes: notas de `pba-launcher`, `pmas-web-main`, `pba-ms-gateway`, `pba-ms-auth`, `pba-ms-management`, `pba-ms-robotics`; anclas de las Partes I y II.
- Produces: anclas de las fichas 9–14 con subencabezados `#### <n>.1 Propósito` … `#### <n>.9 Trampas`.

- [ ] **Step 1: Apertura de la Parte III y sección 8**

Blockquote de audiencia (desarrolladores). Sección 8: explica la plantilla de nueve apartados, que las rutas son relativas al lanzador y que los flujos se explican en la Parte II (con enlaces).

- [ ] **Step 2: Fichas 9 a 14**

Cada ficha con sus nueve subencabezados de nivel 4, en este orden: Propósito, Versión, Tecnología, Árbol, Archivos clave, Contratos, Configuración, Pruebas, Trampas.
- Árbol: bloque de código `text` con el árbol hasta nivel de módulo y un comentario breve por carpeta, seguido de 1–2 párrafos que expliquen la lógica de la organización.
- Contratos: tabla de expuestos y tabla de consumidos (patrón o endpoint, entrada, salida, archivo).
- Configuración: tabla (variable, defecto, efecto), enlazando al Anexo B para la lista global.
- Pruebas: comando exacto y qué cubren.
- Trampas: prosa con los invariantes de las notas.
- En lugar de reexplicar un flujo, enlazarlo (por ejemplo, "ver [6.3](#63-chat-por-la-ruta-complejo-el-turno)").

Requisitos por ficha:
- 9 (lanzador): las carpetas de primer nivel, cada script de `scripts/` y por qué la imagen de `pmai-core` se construye desde la raíz.
- 10 (web): rutas y guards, servicios y endpoints, cajón de runtime, iframe del estudio.
- 11 (gateway): resumen y enlace al Anexo D para la lista completa.
- 12 (auth): modelos, JWT, roles y siembra.
- 13 (management): lógica de ruta, OpenAI y poema.
- 14 (robotics): cola, TTS y serie. Añadir un `flowchart` interno de la cola de reproducción.

Longitud orientativa: 120–250 líneas por ficha.

- [ ] **Step 3: Verificar**

Run: `python3 docs/project-docs/.work/check_doc.py --mermaid docs/project-docs/r-one-documentacion-integral.md && rg -c "<!-- pendiente: tarea 10 -->" docs/project-docs/r-one-documentacion-integral.md; python3 docs/project-docs/.work/ids.py docs/project-docs/r-one-documentacion-integral.md --desde "## Parte III. Repositorios" --hasta "### 15. pmai-mai-core"`
Expected: `check_doc: 0 errores, …`; `rg` sin salida; cada identificador sin encontrar corregido o justificado.

Run: `rg -n "^#### (9|1[0-4])\.[1-9] " docs/project-docs/r-one-documentacion-integral.md | wc -l`
Expected: `54` (6 fichas × 9 apartados).

- [ ] **Step 4: Commit**

```bash
git add docs/project-docs/r-one-documentacion-integral.md
git commit -m "Escribe las fichas del lanzador, la web y los servicios Nest y de robótica."
```

---

### Task 11: Parte III — fichas 15 a 20

**Files:**
- Modify: `docs/project-docs/r-one-documentacion-integral.md` (solo los marcadores `tarea 11`)

**Interfaces:**
- Consumes: notas de `pmai-mai-core`, `pmai-model-context`, `pmai-model-vision-language`, `pmai-model-vision`, `pmas-web-motion-studio`, `pba-arduino-codes`; anclas de las Partes I y II.
- Produces: anclas de las fichas 15–20 con subencabezados `#### <n>.1 Propósito` … `#### <n>.9 Trampas`.

- [ ] **Step 1: Fichas 15 a 20**

Misma plantilla de nueve subencabezados de nivel 4 (Propósito, Versión, Tecnología, Árbol, Archivos clave, Contratos, Configuración, Pruebas, Trampas), con árbol en bloque `text`, contratos en tablas, configuración enlazada al Anexo B y flujos enlazados a la Parte II en vez de repetidos.

Requisitos por ficha:
- 15 (mai-core): un `flowchart` interno del pipeline (cámaras → detección → seguimiento → ReID → publicación) y otro del turno dentro del código (`api/interaction`), las claves de `settings.toml` en tabla, `PMAI_CORE_PYTHONPATH` y por qué no se recorta.
- 16 (contexto): modelo y parámetros, API que usa mai-core y por qué el paquete se llama `model_context`.
- 17 (vision-language): `responder()` paso a paso con un ejemplo de entrada y salida JSON (`reply`, `fuente`, `movimientos`, `backend`, `milvus_caido`), el prompt con `{catalogo_movimientos}`, la personalización y la siembra de `conocimiento`.
- 18 (vision): clases, pesos y métricas finales, enlazando a la sección 29 para la historia.
- 19 (estudio): endpoints, grabación, par normal/neutro y la integración por iframe.
- 20 (firmware): protocolo serie con un ejemplo de comando, mapa de canales y límites. Si no hubo clon, la ficha lo dice al inicio y marca cada dato como "pendiente de confirmar: repositorio no accesible".

Longitud orientativa: 120–300 líneas por ficha; mai-core y vision-language serán las más largas.

- [ ] **Step 2: Verificar**

Run: `python3 docs/project-docs/.work/check_doc.py --mermaid docs/project-docs/r-one-documentacion-integral.md && rg -c "<!-- pendiente: tarea 11 -->" docs/project-docs/r-one-documentacion-integral.md; python3 docs/project-docs/.work/ids.py docs/project-docs/r-one-documentacion-integral.md --desde "### 15. pmai-mai-core" --hasta "## Parte IV. Despliegue y operación"`
Expected: `check_doc: 0 errores, …`; `rg` sin salida; cada identificador sin encontrar corregido o justificado.

Run: `rg -n "^#### (1[5-9]|20)\.[1-9] " docs/project-docs/r-one-documentacion-integral.md | wc -l`
Expected: `54`.

- [ ] **Step 3: Commit**

```bash
git add docs/project-docs/r-one-documentacion-integral.md
git commit -m "Escribe las fichas del núcleo, los modelos, el estudio y el firmware."
```

---

### Task 12: Parte IV — Despliegue y operación

**Files:**
- Modify: `docs/project-docs/r-one-documentacion-integral.md` (solo los marcadores `tarea 12`)

**Interfaces:**
- Consumes: nota `pba-launcher` (scripts, Compose, `.env.template`), `README.md`, `docs/project-docs/jetson-orin-nano-r-one.md`, notas de robótica (Bluetooth y PulseAudio) y de mai-core (cámaras y micrófono).
- Produces: ancla `#24-solución-de-problemas`, que el README enlazará.

- [ ] **Step 1: Secciones 21 y 22**

21: requisitos de hardware y software (Docker, Compose, red, clave OpenAI opcional, cámaras, micrófono, parlante); `.env` desde `.env.template` explicado por bloques; qué se descarga en el primer arranque y por qué tarda. 22: arranque paso a paso con bloques `bash` exactos (`git submodule update --init --recursive`, `cp .env.template .env`, `mkdir -p data/milvus`, `docker compose build pmai-core`, `./scripts/lan-up.sh`, `LAN_IFACE=…`), qué imprime cada paso, la tabla de comandos `rone-*` del README, la reconstrucción de `pmas-web-main` y el QR de red. Las diferencias en WSL2 (cámaras V4L2 comentadas en Compose; `camera.sources` en `settings.toml`).

- [ ] **Step 2: Sección 23**

Ficha de la placa (tabla resumida), qué se instaló y configuró, alias `rone-*` en `~/.bashrc`, Wi-Fi de campo (`rone-wifi scan|join|hotspot`), Bluetooth (`rone-bt`, Thinkplus-K3-pro), SSH y `jetson-w4.local`. Cerrar remitiendo a `docs/project-docs/jetson-orin-nano-r-one.md` como bitácora viva.

- [ ] **Step 3: Sección 24**

Una subsección en negrita por síntoma (no encabezados, para no inflar la tabla de contenido): no habla, no se mueve, no ve, no escucha, Gemma no carga, Milvus vacío o caído, sin clave OpenAI, catálogo de gestos vacío, la sesión venció, el teléfono no abre la interfaz. Cada síntoma en prosa: causa probable, qué revisar, comando exacto (por ejemplo `docker compose logs -f pba-ms-robotics`, `rone-bt status`, `./scripts/seed-conocimiento.sh`, `docker compose restart pmai-core`) y qué salida indica que se resolvió. Recordar que un catálogo vacío no es un fallo del turno y que la falta del Arduino no explica un catálogo vacío.

- [ ] **Step 4: Verificar**

Run: `python3 docs/project-docs/.work/check_doc.py --mermaid docs/project-docs/r-one-documentacion-integral.md && rg -c "<!-- pendiente: tarea 12 -->" docs/project-docs/r-one-documentacion-integral.md; python3 docs/project-docs/.work/ids.py docs/project-docs/r-one-documentacion-integral.md --desde "## Parte IV. Despliegue y operación" --hasta "## Parte V. Producto e identidad visual"`
Expected: `check_doc: 0 errores, …`; `rg` sin salida; cada identificador sin encontrar corregido o justificado.

Run: `for s in lan-up lan-down lan-restart wifi-up bt-up seed-auth seed-conocimiento; do rg -q "scripts/$s.sh" docs/project-docs/r-one-documentacion-integral.md || echo "falta $s"; done`
Expected: sin salida.

- [ ] **Step 5: Commit**

```bash
git add docs/project-docs/r-one-documentacion-integral.md
git commit -m "Escribe la Parte IV de la documentación integral."
```

---

### Task 13: Partes V y VI — Producto e historia

**Files:**
- Modify: `docs/project-docs/r-one-documentacion-integral.md` (solo los marcadores `tarea 13`)

**Interfaces:**
- Consumes: `PRODUCT.md`, `DESIGN.md`, `pmas-web-main/src/styles.css`; la memoria (capítulo 3, líneas 573–603; capítulo 4, líneas 603–1257; capítulo 6, líneas 1267–2684); `docs/project-docs/model-vision-project.md`; `docs/project-docs/project-start-plan.png`; `docs/project-docs/high-level-action-model.jpeg`; `figuras.tsv` con las figuras conservadas; notas de los repositorios `pmai-*`.
- Produces: las anclas 25–32.

- [ ] **Step 1: Parte V**

25: usuarios y propósito del producto (de `PRODUCT.md`). 26: los siete principios y la voz de operador, con ejemplos de textos reales de la interfaz. 27: una tabla de tokens (navy `#0B2540`, cian `#38bdf8`, esmeralda `#059669`, campo `#eef2f6`, tarjeta `#f7fafc` y los de `DESIGN.md`), la tipografía y las reglas de accesibilidad (cuerpo ≥ 14 px, AA, foco visible, el color nunca como único medio).

- [ ] **Step 2: Sección 28**

Stakeholders de la memoria en una tabla con su interés. Los nueve hitos de `project-start-plan.png` (incrustada como figura), cada uno con su estado actual en una frase.

- [ ] **Step 3: Sección 29**

Reescribir en prosa la sección 6.1 de la memoria, actualizada con la nota de `pmai-model-vision`: extracción con ffmpeg (el comando real, sin las capturas de instalación), Label Studio, 802 imágenes y 25 clases con su distribución por integrante, limpieza (`data_cleaning`, `clean_missing_labels`, `clean_corrupt_labels`, `clean_corrupt_images`, `remove_duplicates`), preprocesamiento (`preprocess_image`, balance de blancos, CLAHE, gamma, letterbox, cada uno explicado con una frase de qué corrige), entrenamiento y aumento de datos, resultados con las figuras conservadas de la ilustración 77 y su lectura (qué significa mAP50 con un ejemplo), despliegue en mai-core enlazando la ficha 15. Un `flowchart LR` del pipeline del dataset.

- [ ] **Step 4: Sección 30**

Reescribir la sección 6.2 de la memoria: por qué BLIP-base, la comparación con Geospace, los casos de prueba y sus métricas (figuras 93, 94 y 99 si se conservaron), la cuantización y los parámetros de inferencia, las palabras omitidas, los patrones de alucinación y las palabras protegidas (figuras 110–112), y la inferencia con imágenes reales (figura 113). Cerrar con lo que hoy usa `pmai-model-context`.

- [ ] **Step 5: Sección 31**

Reescribir la sección 6.3 de la memoria y las secciones finales sin desarrollar ("Stack tecnologico", "Proceso de Ingesta", "Base vectorial Milvus", "Prompt Engineering", "Resultados", "Metricas"): la fase de análisis con `high-level-action-model.jpeg` y las figuras 114–123 conservadas, la ingesta en dos fases de web scraping, la búsqueda semántica y el caché, la evolución del prompt (catálogo fijo 1–34 frente a catálogo vivo; `"movimiento"` frente a `"movimientos"`) y las métricas disponibles o "pendiente de confirmar: la memoria deja la sección vacía".

- [ ] **Step 6: Sección 32**

La interfaz que describe el capítulo 4 de la memoria frente a la actual: CMS, páginas públicas, editor de secuencias de línea de tiempo, telemetría y el paso al estudio integrado y al rediseño navy. Más una lista en prosa de decisiones descartadas con su motivo (por ejemplo: catálogo fijo de gestos, `utils` como nombre del paquete de contexto, Ollama, Geospace, o lo que las notas marquen como histórico).

- [ ] **Step 7: Verificar**

Run: `python3 docs/project-docs/.work/check_doc.py --mermaid docs/project-docs/r-one-documentacion-integral.md && rg -c "<!-- pendiente: tarea 13 -->" docs/project-docs/r-one-documentacion-integral.md; python3 docs/project-docs/.work/ids.py docs/project-docs/r-one-documentacion-integral.md --desde "## Parte V. Producto e identidad visual" --hasta "## Anexos"`
Expected: `check_doc: 0 errores, …`; `rg` sin salida; cada identificador sin encontrar corregido o justificado.

Run: `awk -F'\t' '$4=="conservar"{print $5}' docs/project-docs/.work/figuras.tsv | while read f; do rg -q "assets/$f" docs/project-docs/r-one-documentacion-integral.md || echo "sin usar $f"; done`
Expected: sin salida (toda figura conservada está incrustada en algún lugar del documento). Si alguna sobra, incrustarla donde aporte o cambiarla a `descartar` y borrarla de `assets/`.

- [ ] **Step 8: Commit**

```bash
git add docs/project-docs/r-one-documentacion-integral.md docs/project-docs/assets
git commit -m "Escribe las Partes V y VI de la documentación integral."
```

---

### Task 14: Anexos

**Files:**
- Modify: `docs/project-docs/r-one-documentacion-integral.md` (solo los marcadores `tarea 14`)

**Interfaces:**
- Consumes: el capítulo 2 de la memoria (glosario, líneas 455–573); todas las notas (secciones "Configuración" y "Contratos"); `docker-compose.yml`; `.env.template`; el documento ya escrito (figuras y bloques Mermaid).
- Produces: anclas `#anexo-a-glosario` … `#anexo-e-índice-de-figuras-y-diagramas`, que las Partes II y III ya enlazan.

- [ ] **Step 1: Anexo A**

Los 24 términos de la memoria (Angular … XSS), reescritos y actualizados, más los nuevos (al menos: BLIP, Compose, embedding, GGUF, Gemma, Jetson, Label Studio, llama.cpp, mAP, Milvus, NATS, NestJS, neutro, Piper, Prisma, PulseAudio, ReID, secuencia, turno, Vosk, YOLO). Orden alfabético; cada entrada en 1–3 frases y, si aplica, un enlace a la sección donde se explica a fondo.

- [ ] **Step 2: Anexo B**

Una tabla por servicio con todas las variables de `docker-compose.yml` y `.env.template`: variable, variable del contenedor que alimenta, valor por defecto o de plantilla (sin secretos), efecto, y en qué ficha se explica. Incluir las claves relevantes de `pmai-mai-core/settings.toml` y del `.env` de `pmai-model-vision-language`, con la regla de precedencia (`load_dotenv(..., override=False)`).

- [ ] **Step 3: Anexos C y D**

C: una tabla con todos los patrones NATS (patrón, servicio que responde, quién lo llama, entrada, salida, archivo). Contrastar que cada `@MessagePattern` y cada `NatsSubscriber` de las notas aparezcan. D: una tabla con todos los endpoints del gateway (método, ruta, guard o rol, patrón NATS destino, uso desde la interfaz).

Run: `rg -o "@MessagePattern\(['\"][^'\"]+" pba-ms-*/src -r '' | wc -l`
Expected: el número de filas de NestJS en la tabla C es igual o mayor (algunos patrones se definen con constantes; resolverlas en la nota y contarlas).

- [ ] **Step 4: Anexo E**

Dos listas generadas a mano a partir del documento final: figuras (número, pie, enlace a la sección) y diagramas Mermaid (tipo, tema, enlace a la sección).

Run: `rg -c "^\*Figura [0-9]+\." docs/project-docs/r-one-documentacion-integral.md; python3 docs/project-docs/.work/check_doc.py docs/project-docs/r-one-documentacion-integral.md | tail -1`
Expected: el número de figuras y de bloques Mermaid coincide con las entradas del Anexo E.

- [ ] **Step 5: Verificar**

Run: `python3 docs/project-docs/.work/check_doc.py --mermaid docs/project-docs/r-one-documentacion-integral.md && rg -c "<!-- pendiente: tarea 14 -->" docs/project-docs/r-one-documentacion-integral.md; python3 docs/project-docs/.work/ids.py docs/project-docs/r-one-documentacion-integral.md --desde "## Anexos"`
Expected: `check_doc: 0 errores, …`; `rg` sin salida; cada identificador sin encontrar corregido o justificado.

- [ ] **Step 6: Commit**

```bash
git add docs/project-docs/r-one-documentacion-integral.md
git commit -m "Escribe los anexos de la documentación integral."
```

---

### Task 15: Tabla de contenido, archivo, referencias y verificación final

**Files:**
- Modify: `docs/project-docs/r-one-documentacion-integral.md`
- Move: `docs/project-docs/1. Documentación del Proyecto - Inteligencia Artificial Multimodal y Robótica Autonoma.md` → `docs/project-docs/archivo/`
- Move (sin git): `docs/project-docs/1. Documentación del Proyecto - Inteligencia Artificial Multimodal y Robótica Autonoma (1).docx` → `docs/project-docs/archivo/`
- Modify: `AGENTS.md`
- Modify: `README.md`
- Create: `docs/project-docs/.work/cobertura.tsv`

**Interfaces:**
- Consumes: todo lo anterior.

- [ ] **Step 1: Cobertura de la memoria**

Crear `docs/project-docs/.work/cobertura.tsv` con columnas `encabezado_memoria	ancla_nueva`, una fila por cada capítulo y sección numerada de la memoria. Obtener la lista con:

Run: `grep -nE '^# \*\*(Capitulo [0-9]+|[0-9]+\.[0-9]+\.)' "docs/project-docs/1. Documentación del Proyecto - Inteligencia Artificial Multimodal y Robótica Autonoma.md"`

Después comprobar que cada ancla existe:

```bash
python3 - <<'EOF'
import csv, sys
from pathlib import Path
sys.path.insert(0, "docs/project-docs/.work")
import check_doc as cd
doc = Path("docs/project-docs/r-one-documentacion-integral.md")
anchors = cd.check(doc.read_text(encoding="utf-8"), doc.parent)["anchors"]
rows = list(csv.DictReader(open("docs/project-docs/.work/cobertura.tsv", encoding="utf-8"), delimiter="\t"))
bad = [r for r in rows if r["ancla_nueva"].lstrip("#") not in anchors]
for r in bad:
    print("SIN DESTINO", r["encabezado_memoria"], r["ancla_nueva"])
print(f"cobertura: {len(rows)} encabezados, {len(bad)} sin destino")
EOF
```

Expected: `cobertura: <n> encabezados, 0 sin destino`, con `<n>` igual al número de líneas del `grep`.

- [ ] **Step 2: Tabla de contenido definitiva**

Run: `python3 docs/project-docs/.work/toc.py docs/project-docs/r-one-documentacion-integral.md`
Expected: `toc regenerada`.

- [ ] **Step 3: Archivar la memoria**

```bash
mkdir -p docs/project-docs/archivo
git mv "docs/project-docs/1. Documentación del Proyecto - Inteligencia Artificial Multimodal y Robótica Autonoma.md" docs/project-docs/archivo/
mv "docs/project-docs/1. Documentación del Proyecto - Inteligencia Artificial Multimodal y Robótica Autonoma (1).docx" docs/project-docs/archivo/
git status --short docs/project-docs
```

Expected: el `.md` aparece como renombrado (`R`) y el `.docx` no aparece (está ignorado).

- [ ] **Step 4: Reapuntar referencias**

Run: `rg -n "Documentación del Proyecto" --glob '!docs/project-docs/archivo/**' --glob '!docs/superpowers/**' --glob '!**/node_modules/**' .`
Expected: solo `AGENTS.md` y, si aparece, `docs/project-docs/r-one-documentacion-integral.md` (la mención del archivo en la introducción).

En `AGENTS.md`, reemplazar la fila:

```markdown
| `docs/project-docs/1. Documentación del Proyecto - Inteligencia Artificial Multimodal y Robótica Autonoma.md` | Memoria académica del sistema |
```

por:

```markdown
| `docs/project-docs/r-one-documentacion-integral.md` | Documentación integral: conceptos, arquitectura, flujos, repositorios, operación e historia |
| `docs/project-docs/archivo/` | Memoria académica anterior. Solo consulta histórica |
```

En `README.md`, insertar antes de `## ⚙️ Configuración Inicial`:

```markdown
> Documentación completa del proyecto: [docs/project-docs/r-one-documentacion-integral.md](docs/project-docs/r-one-documentacion-integral.md). Si algo falla al arrancar, ve a [Solución de problemas](docs/project-docs/r-one-documentacion-integral.md#24-solución-de-problemas).

```

- [ ] **Step 5: Verificación final**

Run: `python3 docs/project-docs/.work/check_doc.py --final --mermaid docs/project-docs/r-one-documentacion-integral.md`
Expected: `check_doc: 0 errores, 0 pendientes, <C> por confirmar, <M> bloques mermaid`.

Run: `rg -n -i "pendiente de confirmar" docs/project-docs/r-one-documentacion-integral.md`
Expected: cada coincidencia va seguida de `:` y un motivo concreto. Listar todas en el mensaje de cierre.

Run: `wc -l docs/project-docs/r-one-documentacion-integral.md`
Expected: entre 4.000 y 6.000 líneas. Si queda por debajo de 4.000, revisar qué ficha o flujo quedó delgado frente a sus notas; si supera 6.000, buscar repeticiones entre la Parte II y la Parte III y sustituirlas por enlaces.

Run: `python3 docs/project-docs/.work/ids.py docs/project-docs/r-one-documentacion-integral.md --desde "## Parte I. Entender R-ONE"`
Expected: `ids: <n> citados, <m> sin encontrar`, con cada "sin encontrar" ya justificado en tareas anteriores.

Leer el documento completo de principio a fin una vez, con dos lentes: (1) tono (conectores, prosa en lugar de listas, ninguna sigla sin explicar en su primera aparición) y (2) coherencia (la Parte I no contradice a la II, ni la II a la III; los invariantes globales se cumplen). Corregir en el acto.

- [ ] **Step 6: Commit**

```bash
git add docs/project-docs/r-one-documentacion-integral.md docs/project-docs/archivo AGENTS.md README.md
git commit -m "Publica la documentación integral y archiva la memoria académica."
```
