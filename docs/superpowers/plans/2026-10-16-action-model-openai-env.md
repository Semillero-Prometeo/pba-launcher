# Action-model OpenAI env Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `responder()` uses OpenAI when a usable `OPENAI_API_KEY` reaches `pmai-core`, and Gemma when the key is missing or the API call fails.

**Architecture:** Compose injects `OPENAI_API_KEY` into `pmai-core` from `PMAI_OPENAI_API_KEY` (fallback `MS_MANAGEMENT_OPENAI_API_KEY`). `load_dotenv` on `pmai-model-vision-language/.env` fills the key only if Compose left it empty. `generar_respuesta` tries OpenAI whenever the key is set; it does not gate on a TCP ping to `8.8.8.8`.

**Tech Stack:** Docker Compose, python-dotenv, OpenAI Python SDK, llama-cpp GGUF fallback, pytest.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-16-action-model-openai-env-design.md`. Turn spec `2026-10-09-rone-interaction-turn-design.md` still applies.
- Compose interpolation, exact: `OPENAI_API_KEY=${PMAI_OPENAI_API_KEY:-${MS_MANAGEMENT_OPENAI_API_KEY}}`
- `PMAI_CORE_PYTHONPATH=/opt/model-context:/opt/action-model:/app/src`
- `load_dotenv` must not use `override=True`. Compose wins over the model `.env`.
- Without `OPENAI_API_KEY` → Gemma, no OpenAI client. With key → always `llamar_openai`. API failure → Gemma and a warning. `_backend` is `openai` or `gguf`.
- Remove the `8.8.8.8:53` pre-check. It must not skip OpenAI when a key is present.
- Model stays `gpt-4o-mini` (`OPENAI_MODEL` in `utils/config.py`).
- Do not edit `pmai-mai-core` (`_fuente_visible`, the turn, `chatService.chat`).
- Do not change `declarePoema`, robotics TTS, Milvus, the prompt, gesture catalog, or `{ reply, fuente, movimientos }`.
- Do not commit secrets. Do not git-add `.env` files that hold keys.
- Action-model commits go in `pmai-model-vision-language`. Compose, `.env.template`, README, `AGENTS.md`, and this plan commit in the launcher.

---

## File structure

| File | Responsibility |
|---|---|
| `pmai-model-vision-language/tests/test_openai_router.py` | Router + dotenv contract |
| `pmai-model-vision-language/utils/gpt/gptapi.py` | OpenAI then Gemma; no DNS gate |
| `pmai-model-vision-language/utils/config.py` | `load_dotenv(..., override=False)` |
| `docker-compose.yml` | Inject `OPENAI_API_KEY` into `pmai-core` |
| `.env.template` | `PMAI_OPENAI_API_KEY` |
| `README.md`, `AGENTS.md` | Compose → model `.env` → Gemma |

---

### Task 1: OpenAI / Gemma router without DNS gate

**Files:**
- Create: `pmai-model-vision-language/tests/test_openai_router.py`
- Modify: `pmai-model-vision-language/utils/gpt/gptapi.py`
- Modify: `pmai-model-vision-language/utils/config.py`

**Interfaces:**
- Consumes: `os.environ["OPENAI_API_KEY"]`, `llamar_openai(prompt: str) -> dict`, `_generar_respuesta_gguf(prompt: str) -> dict`.
- Produces: `generar_respuesta(prompt: str) -> dict` with `_backend` `"openai"` or `"gguf"`. `hay_internet` may remain exported but must not decide the backend. `load_dotenv(PROJECT_ROOT / ".env", override=False)`.

- [ ] **Step 1: Write the failing tests**

Create `pmai-model-vision-language/tests/test_openai_router.py`:

```python
from pathlib import Path

import utils.gpt.gptapi as gpt


def test_key_uses_openai_even_if_dns_probe_would_fail(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(gpt, "hay_internet", lambda *args, **kwargs: False)
    monkeypatch.setattr(
        gpt,
        "llamar_openai",
        lambda prompt: {"respuesta": "hola", "movimientos": []},
    )
    monkeypatch.setattr(
        gpt,
        "_generar_respuesta_gguf",
        lambda prompt: (_ for _ in ()).throw(AssertionError("gguf must not run")),
    )
    out = gpt.generar_respuesta("pregunta")
    assert out["_backend"] == "openai"
    assert out["respuesta"] == "hola"


def test_openai_failure_falls_back_to_gguf(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    def boom(prompt):
        raise RuntimeError("401")

    monkeypatch.setattr(gpt, "llamar_openai", boom)
    monkeypatch.setattr(
        gpt,
        "_generar_respuesta_gguf",
        lambda prompt: {"respuesta": "local", "movimientos": []},
    )
    out = gpt.generar_respuesta("pregunta")
    assert out["_backend"] == "gguf"
    assert out["respuesta"] == "local"


def test_missing_key_does_not_call_openai(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    called = []
    monkeypatch.setattr(gpt, "llamar_openai", lambda prompt: called.append(prompt) or {})
    monkeypatch.setattr(
        gpt,
        "_generar_respuesta_gguf",
        lambda prompt: {"respuesta": "local", "movimientos": []},
    )
    out = gpt.generar_respuesta("pregunta")
    assert called == []
    assert out["_backend"] == "gguf"


def test_empty_key_does_not_call_openai(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    called = []
    monkeypatch.setattr(gpt, "llamar_openai", lambda prompt: called.append(prompt) or {})
    monkeypatch.setattr(
        gpt,
        "_generar_respuesta_gguf",
        lambda prompt: {"respuesta": "local", "movimientos": []},
    )
    out = gpt.generar_respuesta("pregunta")
    assert called == []
    assert out["_backend"] == "gguf"


def test_generar_respuesta_source_does_not_gate_on_hay_internet():
    text = Path("utils/gpt/gptapi.py").read_text(encoding="utf-8")
    router = text.split("def generar_respuesta")[1].split("def ")[0]
    assert "hay_internet" not in router
    assert "8.8.8.8" not in text


def test_load_dotenv_does_not_override_existing_env():
    text = Path("utils/config.py").read_text(encoding="utf-8")
    assert "load_dotenv" in text
    assert "override=True" not in text
    assert "override=False" in text
```

- [ ] **Step 2: Run tests to verify they fail**

From `pmai-model-vision-language`:

```bash
python -m pytest tests/test_openai_router.py -v
```

Expected: FAIL. `test_key_uses_openai_even_if_dns_probe_would_fail` hits Gemma because `usar_openai = bool(api_key) and hay_internet()`. `test_generar_respuesta_source_does_not_gate_on_hay_internet` finds `hay_internet` in the router. `test_load_dotenv_does_not_override_existing_env` misses `override=False`.

- [ ] **Step 3: Implement the router and dotenv call**

In `pmai-model-vision-language/utils/config.py`, replace the `load_dotenv` line with:

```python
load_dotenv(PROJECT_ROOT / ".env", override=False)
```

In `pmai-model-vision-language/utils/gpt/gptapi.py`, replace the module docstring, `hay_internet` defaults, and `generar_respuesta` so the file matches this:

```python
"""
utils/gpt/gptapi.py — Router de LLM con fallback automático.

Estrategia:
  1. Si hay OPENAI_API_KEY en el entorno → intenta OpenAI (gpt-4o-mini).
  2. Si no hay clave, o la llamada falla → modelo GGUF local
     (gemma-4-E2B-it-Q4_K_M.gguf) via llama-cpp-python.

La interfaz pública (generar_respuesta, _validar_movimientos) se mantiene
idéntica para no romper los módulos que la importan.
"""

import json
import logging
import os
import socket

from openai import OpenAI

from utils.config import OPENAI_MODEL
from utils.gguf.ggufapi import (
    _validar_movimientos,
    generar_respuesta as _generar_respuesta_gguf,
)

logger = logging.getLogger(__name__)

__all__ = ["_validar_movimientos", "generar_respuesta", "hay_internet"]


def hay_internet(host: str = "api.openai.com", puerto: int = 443, timeout: float = 2.0) -> bool:
    """Sonda opcional para logs. No decide el backend de generar_respuesta."""
    try:
        socket.setdefaulttimeout(timeout)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, puerto))
        return True
    except OSError:
        return False


def llamar_openai(prompt: str) -> dict:
    """Llama a la API de OpenAI y devuelve respuesta + movimientos."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY no está definida en el entorno.")

    client = OpenAI(api_key=api_key)

    try:
        completion = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        contenido: str = completion.choices[0].message.content or ""
    except Exception as exc:
        logger.error("Error llamando a OpenAI: %s", exc)
        raise

    try:
        data = json.loads(contenido)
        return {
            "respuesta": str(data.get("respuesta", contenido)),
            "movimientos": _validar_movimientos(data.get("movimientos", [])),
        }
    except json.JSONDecodeError:
        return {"respuesta": contenido, "movimientos": []}


def generar_respuesta(prompt: str) -> dict:
    """
    Genera una respuesta con OpenAI si hay API key, o Gemma 4 E2B si no.

    El campo extra ``_backend`` indica qué motor se usó:
      "openai" | "gguf"
    """
    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()

    if api_key:
        try:
            resultado = llamar_openai(prompt)
            resultado["_backend"] = "openai"
            logger.info("Respuesta generada con OpenAI (%s)", OPENAI_MODEL)
            return resultado
        except Exception as exc:
            logger.warning(
                "OpenAI falló (%s) — usando modelo GGUF local como fallback.", exc
            )

    resultado = _generar_respuesta_gguf(prompt)
    resultado["_backend"] = "gguf"
    logger.info("Respuesta generada con modelo GGUF local (Gemma 4 E2B)")
    return resultado
```

Leave `llamar_openai` behavior unchanged aside from living in this file. Do not call `hay_internet` from `generar_respuesta`.

- [ ] **Step 4: Run tests to verify they pass**

From `pmai-model-vision-language`:

```bash
python -m pytest tests/test_openai_router.py tests/test_gguf_singleton.py tests/test_responder_movimientos.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit in `pmai-model-vision-language`**

```bash
cd pmai-model-vision-language
git add tests/test_openai_router.py utils/gpt/gptapi.py utils/config.py
git commit -m "$(cat <<'EOF'
Try OpenAI whenever a key is set, then fall back to Gemma.

EOF
)"
```

Do not stage `.env`.

---

### Task 2: Compose injection and operator docs

**Files:**
- Modify: `docker-compose.yml`
- Modify: `.env.template`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify (local only, never commit): `.env` — restore `PMAI_CORE_PYTHONPATH`

**Interfaces:**
- Consumes: Task 1 router reads `os.environ["OPENAI_API_KEY"]`.
- Produces: `pmai-core` container env `OPENAI_API_KEY` from `PMAI_OPENAI_API_KEY` or `MS_MANAGEMENT_OPENAI_API_KEY`. Operator docs describe Compose → model `.env` → Gemma.

- [ ] **Step 1: Write the failing contract check**

From the launcher root:

```bash
python - <<'PY'
from pathlib import Path
text = Path("docker-compose.yml").read_text()
assert "OPENAI_API_KEY: ${PMAI_OPENAI_API_KEY:-${MS_MANAGEMENT_OPENAI_API_KEY}}" in text, text
tmpl = Path(".env.template").read_text()
assert "PMAI_OPENAI_API_KEY=" in tmpl
readme = Path("README.md").read_text()
assert "PMAI_OPENAI_API_KEY" in readme
agents = Path("AGENTS.md").read_text()
assert "Compose" in agents and "OPENAI" in agents
print("contract_ok")
PY
```

Expected: FAIL on the compose assertion (`OPENAI_API_KEY` is not on `pmai-core` yet).

- [ ] **Step 2: Inject the key in Compose**

In `docker-compose.yml`, under `pmai-core.environment`, add this line immediately after `PYTHONPATH: ${PMAI_CORE_PYTHONPATH}`:

```yaml
      OPENAI_API_KEY: ${PMAI_OPENAI_API_KEY:-${MS_MANAGEMENT_OPENAI_API_KEY}}
```

Do not pass `MS_ROBOTICS_OPENAI_API_KEY` here. Do not add `env_file` for the action-model `.env`; `load_dotenv` remains the fallback.

- [ ] **Step 3: Document the variable in `.env.template`**

After `MS_MANAGEMENT_OPENAI_MODEL=` add:

```
# PMAI CORE — action model LLM (empty = reuse MS_MANAGEMENT_OPENAI_API_KEY)
PMAI_OPENAI_API_KEY=
```

Keep `PMAI_CORE_PYTHONPATH=/opt/model-context:/opt/action-model:/app/src` as it already is.

- [ ] **Step 4: Update README and AGENTS.md**

In `README.md`, replace:

```
- Opcional: `OPENAI_API_KEY` en `pmai-model-vision-language/.env`. Con red y clave se usa `gpt-4o-mini`; si no, Gemma.
```

with:

```
- Clave OpenAI del turno: `PMAI_OPENAI_API_KEY` en el `.env` del lanzador (si va vacía, se reusa `MS_MANAGEMENT_OPENAI_API_KEY`). Compose la inyecta en `pmai-core` como `OPENAI_API_KEY`. Si sigue vacía, `pmai-model-vision-language/.env` es el respaldo. Con clave se usa `gpt-4o-mini`; si no hay clave o la API falla, Gemma.
```

In `AGENTS.md`, replace:

```
- La clave de OpenAI del modelo de acción está en el `.env` de `pmai-model-vision-language`.
```

with:

```
- La clave OpenAI del modelo de acción llega a `pmai-core` por Compose (`PMAI_OPENAI_API_KEY`, o `MS_MANAGEMENT_OPENAI_API_KEY` si aquella va vacía). `pmai-model-vision-language/.env` es respaldo y no pisa la variable del contenedor. `PMAI_CORE_PYTHONPATH` no se recorta a `/app/src`.
```

- [ ] **Step 5: Restore the operator PYTHONPATH locally**

If the launcher `.env` has `PMAI_CORE_PYTHONPATH=/app/src`, set it to:

```
PMAI_CORE_PYTHONPATH=/opt/model-context:/opt/action-model:/app/src
```

Do not add a real API key to git. Do not `git add .env`. Recreate or restart `pmai-core` after this so Compose picks up the env (`docker compose up -d pmai-core` is enough; a full rebuild is not required for env-only changes).

- [ ] **Step 6: Re-run the contract check and Compose config**

```bash
python - <<'PY'
from pathlib import Path
text = Path("docker-compose.yml").read_text()
assert "OPENAI_API_KEY: ${PMAI_OPENAI_API_KEY:-${MS_MANAGEMENT_OPENAI_API_KEY}}" in text
tmpl = Path(".env.template").read_text()
assert "PMAI_OPENAI_API_KEY=" in tmpl
readme = Path("README.md").read_text()
assert "PMAI_OPENAI_API_KEY" in readme
agents = Path("AGENTS.md").read_text()
assert "Compose" in agents and "OPENAI" in agents
print("contract_ok")
PY
docker compose config --quiet
```

Expected: `contract_ok`. `docker compose config --quiet` exits 0.

If `docker compose config` is available without `--quiet` in this Compose version, run `docker compose config` and confirm the `pmai-core` service lists `OPENAI_API_KEY` (value may be interpolated from the local `.env`; do not paste the secret into logs or commits).

- [ ] **Step 7: Commit in the launcher**

```bash
git add docker-compose.yml .env.template README.md AGENTS.md pmai-model-vision-language
git commit -m "$(cat <<'EOF'
Inject the action-model OpenAI key into pmai-core.

EOF
)"
```

Do not stage `.env`. Include the `pmai-model-vision-language` submodule pointer from Task 1.

---

## Self-review vs spec

| Spec requirement | Task |
|---|---|
| Compose injects `OPENAI_API_KEY` with PMAI then management fallback | 2 |
| Model `.env` fills only if empty; `override=False` | 1 |
| No key → Gemma, no client | 1 |
| Key → always try OpenAI; failure → Gemma | 1 |
| Remove `8.8.8.8` gate | 1 |
| `PMAI_CORE_PYTHONPATH` canonical | 2 (template already; operator `.env` + AGENTS) |
| README / AGENTS order Compose → model `.env` → Gemma | 2 |
| Tests for openai / fail / no key / dotenv | 1 |
| `docker compose config` | 2 |
| No mai-core / declarePoema / TTS / secrets in git | constraints |
