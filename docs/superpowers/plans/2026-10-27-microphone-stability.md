# USB microphone stability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop the USB microphone from waking on silence or on a substring, keep the same device across USB re-enumeration, feed Vosk and VAD 16 kHz frames, and show connection, level, and the last phrase in the R-ONE chat.

**Architecture:** Pure helpers in `pmai-mai-core` (`energy`, `wake_match`, `resample`, `listen_rules`, discovery fingerprint) decide gating, matching, frames, phase, and level. `AudioService` wires them into the existing Vosk loop and remembers the microphone by fingerprint. `GET /audio/listening-status` grows four fields. The gateway route stays a pass-through. `pmas-web-main` polls that JSON every 500 ms and renders a strip, a meter, and a read-only detail. One plan: the strip is the client of this status contract.

**Tech Stack:** Python 3.12, pydantic, numpy, pytest (`pmai-mai-core`); Angular 21, Vitest (`pmas-web-main`). Vosk and webrtcvad stay; tests do not load the model or open a sound card.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-27-microphone-stability-design.md`.
- Owners: `pmai-mai-core` (listen, fingerprint, resample, status) and `pmas-web-main` (chat strip). Do not edit `pba-ms-gateway`. Do not edit the Jetson. Do not change the turn, `POST /chat/question`, or the browser dictation button.
- Wake phrases stay `hey fede`, `fede`, `federico`. Do not add openWakeWord, Porcupine, or another Vosk model.
- New `[audio]` keys: `wake_energy_rms = 500`, `wake_energy_hangover_ms = 300`, `wake_confirm_chunks = 2`, `level_rms_full_scale = 4000`, `level_hold_ms = 500`. Existing `chunk_ms = 30`, `long_silence_ms = 1600`, `post_wake_grace_ms = 2200`, `max_recording_seconds = 20`, `min_recording_seconds = 1`, `preroll_seconds = 0.4`, `wake_partial_match = true` stay.
- RMS is the square root of the mean of squared int16 samples. Below 500 the wake recognizer does not see the frame. The next 300 ms after a drop still enter the recognizer. Phase may already be `silent` during that hangover.
- Match is whole words. Lowercase, keep letters (including accents), digits, and spaces. `wake_partial_match = true` allows the phrase as a full-word suffix. `false` requires an exact word list. `fede` does not match `federico` or `confederación`. Prefer the longest configured phrase. Two consecutive partials, or one final result, open capture. One partial does not.
- Device audio is resampled to mono 16 kHz, 30 ms, 480-sample frames before Vosk and webrtcvad. 16 kHz is copied. Any other rate uses linear resampling.
- `microphone_id` is `sha1` of `name|hostapi|channels`. Sample rate is not part of the id. `device_index` is only how the stream is opened. A missing selected fingerprint is not replaced by another input. PortAudio failure retries after 2 s. A missing model, missing library, or no openable rate sets `phase` `error` and retries after 1 s. An unusable VAD frame counts as speech and is logged once per open stream.
- Status adds `selected_microphone_name`, `stream_open`, `phase` (`disconnected|silent|hearing|capturing|error`), and `input_level` (0–100). Level is the max RMS of the last 500 ms scaled by `min(100, round(rms * 100 / 4000))`, with no extra decay while 30 ms frames are arriving. After frames stop, that value falls linearly to 0 over 500 ms.
- Chat strip copy, first match wins: HTTP failure `No se pudo consultar el micrófono`; `running` false `Micrófono apagado`; `listening_enabled` false `Escucha en pausa`; `error` `Error de audio`; `disconnected` `Desconectado`; `capturing` `Frase reconocida`; `hearing` `Oyendo`; `silent` `Conectado, en silencio`. HTTP failure shows level 0 and keeps the last payload with `Sin lectura en vivo`. Detail is read-only: microphone `Ninguno`, phrase `Ninguna`, error `Ninguno`.
- Commit only inside the owning repo (`pmai-mai-core` or `pmas-web-main`). Do not commit a launcher submodule pointer.
- No real USB or Jetson check in this work.

## File structure

| File | Responsibility |
|---|---|
| `pmai-mai-core/src/pmai_core/resources/audio/energy.py` | RMS and the wake energy gate |
| `pmai-mai-core/src/pmai_core/resources/audio/wake_match.py` | Whole-word wake match and the two-partial confirm |
| `pmai-mai-core/src/pmai_core/resources/audio/resample.py` | Linear resample to 16 kHz and 480-sample frames |
| `pmai-mai-core/src/pmai_core/resources/audio/listen_rules.py` | VAD failure counts as speech, silence advance, end of capture, retry delay |
| `pmai-mai-core/src/pmai_core/resources/audio/level.py` | Held meter and `listening_phase` |
| `pmai-mai-core/src/pmai_core/resources/audio/discovery.py` | Fingerprint id, USB-first ordering |
| `pmai-mai-core/src/pmai_core/resources/audio/models.py` | Status fields |
| `pmai-mai-core/src/pmai_core/resources/audio/service.py` | Loop, sticky selection, failures |
| `pmai-mai-core/src/pmai_core/api/audio/audio_controller.py` | Status JSON |
| `pmai-mai-core/src/pmai_core/settings.py` | New audio keys |
| `pmai-mai-core/settings.toml` | The same keys for the running process |
| `pmai-mai-core/tests/audio/test_*.py` | No sound card, no Vosk model |
| `pmas-web-main/src/app/pages/robotics-chat/microphone-status.ts` | Strip label, level, detail |
| `pmas-web-main/src/app/pages/robotics-chat/microphone-status.spec.ts` | The eight labels |
| `pmas-web-main/src/app/pages/robotics-chat/robotics-chat.ts` | 500 ms poll |
| `pmas-web-main/src/app/pages/robotics-chat/robotics-chat.html` | Strip, meter, detail |

---

### Task 1: Energy gate and audio settings

**Files:**
- Create: `pmai-mai-core/src/pmai_core/resources/audio/energy.py`
- Create: `pmai-mai-core/tests/audio/test_energy.py`
- Modify: `pmai-mai-core/pyproject.toml` (`[tool.pytest.ini_options]`)
- Modify: `pmai-mai-core/src/pmai_core/settings.py` (`AudioSettings`)
- Modify: `pmai-mai-core/settings.toml` (`[audio]`)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `chunk_rms(pcm: bytes) -> float`. `WakeEnergyGate(threshold: int, hangover_ms: int)` with `feed(rms: float, chunk_ms: int) -> bool`. `AudioSettings.wake_energy_rms: int = 500`, `wake_energy_hangover_ms: int = 300`, `wake_confirm_chunks: int = 2`, `level_rms_full_scale: int = 4000`, `level_hold_ms: int = 500`.

- [ ] **Step 1: Write the failing test**

Add `pythonpath = ["src"]` under `[tool.pytest.ini_options]` in `pmai-mai-core/pyproject.toml`, next to `testpaths`.

Create `pmai-mai-core/tests/audio/test_energy.py`:

```python
from __future__ import annotations

import struct

from pmai_core.resources.audio.energy import WakeEnergyGate, chunk_rms
from pmai_core.settings import AudioSettings


def _pcm(value: int, count: int = 480) -> bytes:
    return struct.pack(f"<{count}h", *([value] * count))


def test_audio_settings_defaults() -> None:
    audio = AudioSettings()
    assert audio.wake_energy_rms == 500
    assert audio.wake_energy_hangover_ms == 300
    assert audio.wake_confirm_chunks == 2
    assert audio.level_rms_full_scale == 4000
    assert audio.level_hold_ms == 500


def test_silence_rms_is_zero() -> None:
    assert chunk_rms(_pcm(0)) == 0


def test_constant_sample_rms_is_abs_value() -> None:
    assert chunk_rms(_pcm(500)) == 500


def test_below_threshold_does_not_open_gate() -> None:
    gate = WakeEnergyGate(500, 300)
    assert gate.feed(100, 30) is False


def test_above_threshold_opens_gate_and_arms_hangover() -> None:
    gate = WakeEnergyGate(500, 300)
    assert gate.feed(800, 30) is True
    assert gate.feed(100, 30) is True


def test_hangover_lasts_300_ms_then_closes() -> None:
    gate = WakeEnergyGate(500, 300)
    assert gate.feed(800, 30) is True
    for _ in range(10):
        assert gate.feed(100, 30) is True
    assert gate.feed(100, 30) is False
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `pmai-mai-core`:

```bash
python -m pytest tests/audio/test_energy.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'pmai_core.resources.audio.energy'`.

- [ ] **Step 3: Write the minimal implementation**

Create `pmai-mai-core/src/pmai_core/resources/audio/energy.py`:

```python
from __future__ import annotations

import struct


def chunk_rms(pcm: bytes) -> float:
    count = len(pcm) // 2
    if count <= 0:
        return 0.0
    samples = struct.unpack(f"<{count}h", pcm[: count * 2])
    total = sum(sample * sample for sample in samples)
    return (total / count) ** 0.5


class WakeEnergyGate:
    def __init__(self, threshold: int, hangover_ms: int) -> None:
        self._threshold = threshold
        self._left_ms = 0
        self._hangover_ms = hangover_ms

    def feed(self, rms: float, chunk_ms: int) -> bool:
        if rms >= self._threshold:
            self._left_ms = self._hangover_ms
            return True
        if self._left_ms <= 0:
            return False
        self._left_ms = max(0, self._left_ms - chunk_ms)
        return True
```

In `AudioSettings`, after `wake_partial_match`, add:

```python
    wake_energy_rms: int = 500
    wake_energy_hangover_ms: int = 300
    wake_confirm_chunks: int = 2
    level_rms_full_scale: int = 4000
    level_hold_ms: int = 500
```

Inside `_normalize_audio_settings`, before `return self`:

```python
        self.wake_energy_rms = max(1, self.wake_energy_rms)
        self.wake_energy_hangover_ms = max(0, self.wake_energy_hangover_ms)
        self.wake_confirm_chunks = max(1, self.wake_confirm_chunks)
        self.level_rms_full_scale = max(1, self.level_rms_full_scale)
        self.level_hold_ms = max(1, self.level_hold_ms)
```

In `settings.toml`, after `wake_partial_match = true`, add:

```toml
wake_energy_rms = 500
wake_energy_hangover_ms = 300
wake_confirm_chunks = 2
level_rms_full_scale = 4000
level_hold_ms = 500
```

- [ ] **Step 4: Run the test to verify it passes**

Run from `pmai-mai-core`:

```bash
python -m pytest tests/audio/test_energy.py -v
```

Expected: PASS, 6 tests.

- [ ] **Step 5: Commit**

```bash
git -C pmai-mai-core add pyproject.toml settings.toml src/pmai_core/settings.py src/pmai_core/resources/audio/energy.py tests/audio/test_energy.py
git -C pmai-mai-core commit -m "$(cat <<'EOF'
Ignore silence in the wake-word recognizer.

EOF
)"
```

---

### Task 2: Whole-word wake match

**Files:**
- Create: `pmai-mai-core/src/pmai_core/resources/audio/wake_match.py`
- Create: `pmai-mai-core/tests/audio/test_wake_match.py`

**Interfaces:**
- Consumes: `wake_confirm_chunks` from Task 1 (the class takes the int directly).
- Produces: `match_wake_phrase(text: str, phrases: list[str], partial_match: bool) -> str | None`. `WakeConfirm(chunks: int)` with `observe(phrase: str | None, is_final: bool) -> bool` and `reset() -> None`.

- [ ] **Step 1: Write the failing test**

Create `pmai-mai-core/tests/audio/test_wake_match.py`:

```python
from __future__ import annotations

from pmai_core.resources.audio.wake_match import WakeConfirm, match_wake_phrase

PHRASES = ["hey fede", "fede", "federico"]


def test_exact_phrase_matches() -> None:
    assert match_wake_phrase("hey fede", PHRASES, True) == "hey fede"
    assert match_wake_phrase("fede", PHRASES, True) == "fede"
    assert match_wake_phrase("federico", PHRASES, True) == "federico"


def test_suffix_matches_longest_phrase() -> None:
    assert match_wake_phrase("oye hey fede", PHRASES, True) == "hey fede"


def test_substring_inside_another_word_does_not_match() -> None:
    assert match_wake_phrase("confederación", PHRASES, True) is None
    assert match_wake_phrase("federico", ["fede"], True) is None


def test_partial_match_false_rejects_suffix() -> None:
    assert match_wake_phrase("oye hey fede", PHRASES, False) is None
    assert match_wake_phrase("hey fede", PHRASES, False) == "hey fede"


def test_punctuation_and_case_are_ignored() -> None:
    assert match_wake_phrase("Hey, Fede!", PHRASES, False) == "hey fede"


def test_one_partial_does_not_open() -> None:
    confirm = WakeConfirm(2)
    assert confirm.observe("hey fede", False) is False


def test_two_partials_open() -> None:
    confirm = WakeConfirm(2)
    assert confirm.observe("hey fede", False) is False
    assert confirm.observe("hey fede", False) is True


def test_different_partial_resets() -> None:
    confirm = WakeConfirm(2)
    assert confirm.observe("hey fede", False) is False
    assert confirm.observe("fede", False) is False
    assert confirm.observe("fede", False) is True


def test_final_opens_once() -> None:
    confirm = WakeConfirm(2)
    assert confirm.observe("hey fede", True) is True


def test_empty_final_does_not_open() -> None:
    confirm = WakeConfirm(2)
    assert confirm.observe(None, True) is False


def test_silence_resets_partial_count() -> None:
    confirm = WakeConfirm(2)
    assert confirm.observe("hey fede", False) is False
    confirm.reset()
    assert confirm.observe("hey fede", False) is False
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `pmai-mai-core`:

```bash
python -m pytest tests/audio/test_wake_match.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'pmai_core.resources.audio.wake_match'`.

- [ ] **Step 3: Write the minimal implementation**

Create `pmai-mai-core/src/pmai_core/resources/audio/wake_match.py`:

```python
from __future__ import annotations

import re

_DROP = re.compile(r"[^\w\s]", re.UNICODE)


def normalize_words(text: str) -> list[str]:
    cleaned = _DROP.sub(" ", text.lower()).replace("_", " ")
    return [word for word in cleaned.split() if word]


def match_wake_phrase(text: str, phrases: list[str], partial_match: bool) -> str | None:
    words = normalize_words(text)
    if not words:
        return None
    ranked = sorted(
        ((normalize_words(phrase), phrase) for phrase in phrases),
        key=lambda item: len(item[0]),
        reverse=True,
    )
    for phrase_words, _original in ranked:
        if not phrase_words:
            continue
        if words == phrase_words:
            return " ".join(phrase_words)
        if (
            partial_match
            and len(words) >= len(phrase_words)
            and words[-len(phrase_words) :] == phrase_words
        ):
            return " ".join(phrase_words)
    return None


class WakeConfirm:
    def __init__(self, chunks: int) -> None:
        self._need = max(1, chunks)
        self._phrase: str | None = None
        self._count = 0

    def reset(self) -> None:
        self._phrase = None
        self._count = 0

    def observe(self, phrase: str | None, is_final: bool) -> bool:
        if is_final:
            self.reset()
            return phrase is not None
        if phrase is None:
            self.reset()
            return False
        if phrase == self._phrase:
            self._count += 1
        else:
            self._phrase = phrase
            self._count = 1
        if self._count >= self._need:
            self.reset()
            return True
        return False
```

- [ ] **Step 4: Run the test to verify it passes**

Run from `pmai-mai-core`:

```bash
python -m pytest tests/audio/test_wake_match.py -v
```

Expected: PASS, 11 tests.

- [ ] **Step 5: Commit**

```bash
git -C pmai-mai-core add src/pmai_core/resources/audio/wake_match.py tests/audio/test_wake_match.py
git -C pmai-mai-core commit -m "$(cat <<'EOF'
Match the wake phrase on whole words.

EOF
)"
```

---

### Task 3: 16 kHz frames

**Files:**
- Create: `pmai-mai-core/src/pmai_core/resources/audio/resample.py`
- Create: `pmai-mai-core/tests/audio/test_resample.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `resample_linear(samples: numpy.ndarray, source_rate: int, target_rate: int = 16000) -> numpy.ndarray`. `FrameSlicer(frame_samples: int = 480)` with `push(samples: numpy.ndarray) -> list[bytes]`.

- [ ] **Step 1: Write the failing test**

Create `pmai-mai-core/tests/audio/test_resample.py`:

```python
from __future__ import annotations

import numpy as np

from pmai_core.resources.audio.resample import FrameSlicer, resample_linear


def test_16k_is_copied() -> None:
    source = np.array([0, 1000, -1000], dtype=np.int16)
    assert np.array_equal(resample_linear(source, 16000), source)


def test_endpoints_are_kept() -> None:
    source = np.linspace(0, 900, 48, dtype=np.float64)
    output = resample_linear(source, 48000)
    assert int(output[0]) == 0
    assert int(output[-1]) == 900


def test_one_second_becomes_16000_samples() -> None:
    for rate in (48000, 44100):
        source = np.zeros(rate, dtype=np.int16)
        output = resample_linear(source, rate)
        assert output.dtype == np.int16
        assert len(output) == 16000


def test_slicer_emits_480_sample_frames() -> None:
    slicer = FrameSlicer(480)
    source = np.zeros(48000, dtype=np.int16)
    frames = slicer.push(resample_linear(source, 48000))
    assert frames
    assert all(len(frame) == 960 for frame in frames)
    assert len(frames) == 33
    assert len(slicer.pending) == 160
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `pmai-mai-core`:

```bash
python -m pytest tests/audio/test_resample.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'pmai_core.resources.audio.resample'`.

- [ ] **Step 3: Write the minimal implementation**

Create `pmai-mai-core/src/pmai_core/resources/audio/resample.py`:

```python
from __future__ import annotations

import numpy as np


def resample_linear(samples: np.ndarray, source_rate: int, target_rate: int = 16000) -> np.ndarray:
    audio = np.asarray(samples, dtype=np.float64).reshape(-1)
    if source_rate == target_rate:
        return np.clip(np.round(audio), -32768, 32767).astype(np.int16)
    if audio.size == 0:
        return np.zeros(0, dtype=np.int16)
    out_len = int(round(audio.size * target_rate / source_rate))
    if out_len <= 1 or audio.size == 1:
        return np.clip(np.round(audio[:1]), -32768, 32767).astype(np.int16)
    positions = np.linspace(0, audio.size - 1, out_len)
    left = np.floor(positions).astype(np.int64)
    right = np.minimum(left + 1, audio.size - 1)
    frac = positions - left
    mixed = audio[left] * (1.0 - frac) + audio[right] * frac
    return np.clip(np.round(mixed), -32768, 32767).astype(np.int16)


class FrameSlicer:
    def __init__(self, frame_samples: int = 480) -> None:
        self._frame_samples = frame_samples
        self._pending = np.zeros(0, dtype=np.int16)

    @property
    def pending(self) -> np.ndarray:
        return self._pending

    def push(self, samples: np.ndarray) -> list[bytes]:
        if samples.size == 0:
            return []
        audio = np.concatenate([self._pending, np.asarray(samples, dtype=np.int16).reshape(-1)])
        frames: list[bytes] = []
        start = 0
        while start + self._frame_samples <= audio.size:
            piece = audio[start : start + self._frame_samples]
            frames.append(piece.astype(np.int16, copy=False).tobytes())
            start += self._frame_samples
        self._pending = audio[start:]
        return frames
```

- [ ] **Step 4: Run the test to verify it passes**

Run from `pmai-mai-core`:

```bash
python -m pytest tests/audio/test_resample.py -v
```

Expected: PASS, 4 tests.

- [ ] **Step 5: Commit**

```bash
git -C pmai-mai-core add src/pmai_core/resources/audio/resample.py tests/audio/test_resample.py
git -C pmai-mai-core commit -m "$(cat <<'EOF'
Feed Vosk and the voice detector 16 kHz frames.

EOF
)"
```

---

### Task 4: Stable microphone id

**Files:**
- Modify: `pmai-mai-core/src/pmai_core/resources/audio/discovery.py`
- Create: `pmai-mai-core/tests/audio/test_discovery.py`

**Interfaces:**
- Consumes: `MicrophoneInfo` in `models.py`.
- Produces: `build_fingerprint(name: str, hostapi_name: str, channels: int) -> str`. `microphones_from_devices(devices: list[dict], hostapis: list[dict], preferred_id: str | None = None) -> list[MicrophoneInfo]`. `discover_usb_microphones` keeps its signature and delegates to `microphones_from_devices`. `microphone_id` and `hardware_fingerprint` are the same hash. `sample_rate` stays on the info object and is not hashed.

- [ ] **Step 1: Write the failing test**

Create `pmai-mai-core/tests/audio/test_discovery.py`:

```python
from __future__ import annotations

from pmai_core.resources.audio.discovery import build_fingerprint, microphones_from_devices

HOSTAPIS = [{"name": "ALSA"}]


def _device(name: str, index_rate: int, channels: int = 1) -> dict:
    return {
        "name": name,
        "max_input_channels": channels,
        "hostapi": 0,
        "default_samplerate": float(index_rate),
    }


def test_fingerprint_ignores_sample_rate() -> None:
    devices = [
        _device("USB PnP", 16000),
        _device("USB PnP", 48000),
    ]
    found = microphones_from_devices(devices, HOSTAPIS)
    assert found[0].microphone_id == found[1].microphone_id
    assert found[0].sample_rate == 16000
    assert found[1].sample_rate == 48000
    assert found[0].microphone_id == build_fingerprint("USB PnP", "ALSA", 1)
    assert found[0].hardware_fingerprint == found[0].microphone_id


def test_usb_device_is_listed_when_an_analog_input_is_also_present() -> None:
    devices = [
        _device("Analog", 16000),
        _device("USB Mic", 16000),
    ]
    found = microphones_from_devices(devices, HOSTAPIS)
    assert [item.name for item in found] == ["USB Mic"]


def test_analog_input_is_listed_when_no_usb_input_exists() -> None:
    found = microphones_from_devices([_device("Analog", 16000)], HOSTAPIS)
    assert found[0].name == "Analog"
    assert found[0].device_index == 0


def test_preferred_id_is_listed_first() -> None:
    devices = [
        _device("USB A", 16000),
        _device("USB B", 16000),
    ]
    preferred = build_fingerprint("USB B", "ALSA", 1)
    found = microphones_from_devices(devices, HOSTAPIS, preferred)
    assert found[0].microphone_id == preferred
    assert found[0].device_index == 1
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `pmai-mai-core`:

```bash
python -m pytest tests/audio/test_discovery.py -v
```

Expected: FAIL with `ImportError: cannot import name 'build_fingerprint'` or `cannot import name 'microphones_from_devices'`.

- [ ] **Step 3: Write the minimal implementation**

Replace `pmai-mai-core/src/pmai_core/resources/audio/discovery.py` with:

```python
"""USB microphone discovery helpers."""

from __future__ import annotations

import hashlib
from typing import Any

import structlog

from pmai_core.resources.audio.models import MicrophoneInfo

logger = structlog.get_logger(__name__)

try:
    import sounddevice as sd
except (ModuleNotFoundError, OSError):  # pragma: no cover - guarded at runtime
    sd = None


def _is_usb_like(name: str, hostapi_name: str) -> bool:
    blob = f"{name} {hostapi_name}".lower()
    return "usb" in blob


def build_fingerprint(name: str, hostapi_name: str, channels: int) -> str:
    raw = f"{name}|{hostapi_name}|{channels}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()  # nosec B324


def microphones_from_devices(
    devices: list[dict[str, Any]],
    hostapis: list[dict[str, Any]],
    preferred_id: str | None = None,
) -> list[MicrophoneInfo]:
    discovered: list[MicrophoneInfo] = []
    fallback: list[MicrophoneInfo] = []
    for idx, dev in enumerate(devices):
        max_input = int(dev.get("max_input_channels", 0) or 0)
        if max_input <= 0:
            continue
        host_idx = int(dev.get("hostapi", -1))
        hostapi_name = (
            str(hostapis[host_idx].get("name", "unknown"))
            if 0 <= host_idx < len(hostapis)
            else "unknown"
        )
        name = str(dev.get("name", f"Audio Device {idx}"))
        sample_rate = int(float(dev.get("default_samplerate", 16000.0)))
        fingerprint = build_fingerprint(name, hostapi_name, max_input)
        info = MicrophoneInfo(
            microphone_id=fingerprint,
            name=name,
            hostapi_name=hostapi_name,
            device_index=idx,
            hardware_fingerprint=fingerprint,
            channels=max_input,
            sample_rate=sample_rate,
        )
        if _is_usb_like(name, hostapi_name):
            discovered.append(info)
        else:
            fallback.append(info)

    ordered = discovered or fallback
    if preferred_id:
        ordered = sorted(ordered, key=lambda item: item.microphone_id != preferred_id)
    return ordered


def discover_usb_microphones(preferred_id: str | None = None) -> list[MicrophoneInfo]:
    """Discover audio input devices; prioritize USB-like devices."""
    if sd is None:
        logger.warning("sounddevice_unavailable_for_microphone_discovery")
        return []
    devices = list(sd.query_devices())
    hostapis = list(sd.query_hostapis())
    return microphones_from_devices(devices, hostapis, preferred_id)
```

- [ ] **Step 4: Run the test to verify it passes**

Run from `pmai-mai-core`:

```bash
python -m pytest tests/audio/test_discovery.py -v
```

Expected: PASS, 4 tests.

- [ ] **Step 5: Commit**

```bash
git -C pmai-mai-core add src/pmai_core/resources/audio/discovery.py tests/audio/test_discovery.py
git -C pmai-mai-core commit -m "$(cat <<'EOF'
Identify microphones by hardware fingerprint instead of device index.

EOF
)"
```

---

### Task 5: Level, phase, and status JSON

**Files:**
- Create: `pmai-mai-core/src/pmai_core/resources/audio/level.py`
- Create: `pmai-mai-core/tests/audio/test_level.py`
- Modify: `pmai-mai-core/src/pmai_core/resources/audio/models.py`
- Modify: `pmai-mai-core/src/pmai_core/resources/audio/service.py` (`get_status` constructor only)
- Modify: `pmai-mai-core/src/pmai_core/api/audio/audio_controller.py`
- Create: `pmai-mai-core/tests/audio/test_status_payload.py`

**Interfaces:**
- Consumes: `level_rms_full_scale`, `level_hold_ms`, `chunk_ms`, `wake_energy_rms` as plain numbers.
- Produces: `LevelHold(full_scale: int, hold_ms: int, chunk_ms: int)` with `update(rms: float, now_ms: int) -> int` and `level_at(now_ms: int) -> int`. `listening_phase(*, fatal: bool, stream_open: bool, capturing: bool, last_rms: float, threshold: float) -> ListenPhase`. `ListenPhase` in `models.py`. `AudioRuntimeStatus` gains `selected_microphone_name: str | None`, `stream_open: bool`, `phase: ListenPhase`, `input_level: int`. `listening_status_payload(status: AudioRuntimeStatus) -> dict[str, Any]`.

- [ ] **Step 1: Write the failing tests**

Create `pmai-mai-core/tests/audio/test_level.py`:

```python
from __future__ import annotations

from pmai_core.resources.audio.level import LevelHold, listening_phase
from pmai_core.resources.audio.models import ListenPhase


def test_full_scale_is_100() -> None:
    hold = LevelHold(4000, 500, 30)
    assert hold.update(4000, 0) == 100


def test_half_scale_is_50() -> None:
    hold = LevelHold(4000, 500, 30)
    assert hold.update(2000, 0) == 50


def test_window_keeps_peak_while_frames_arrive() -> None:
    hold = LevelHold(4000, 500, 30)
    hold.update(4000, 0)
    assert hold.update(0, 30) == 100
    assert hold.level_at(40) == 100


def test_level_decays_after_frames_stop() -> None:
    hold = LevelHold(4000, 500, 30)
    hold.update(4000, 0)
    assert hold.level_at(30 + 250) == 50
    assert hold.level_at(30 + 500) == 0


def test_old_peak_leaves_the_window() -> None:
    hold = LevelHold(4000, 500, 30)
    hold.update(4000, 0)
    assert hold.update(0, 600) == 0


def test_phase_priority() -> None:
    assert (
        listening_phase(
            fatal=True, stream_open=False, capturing=False, last_rms=0, threshold=500
        )
        == ListenPhase.ERROR
    )
    assert (
        listening_phase(
            fatal=False, stream_open=False, capturing=False, last_rms=0, threshold=500
        )
        == ListenPhase.DISCONNECTED
    )
    assert (
        listening_phase(
            fatal=False, stream_open=True, capturing=True, last_rms=0, threshold=500
        )
        == ListenPhase.CAPTURING
    )
    assert (
        listening_phase(
            fatal=False, stream_open=True, capturing=False, last_rms=500, threshold=500
        )
        == ListenPhase.HEARING
    )
    assert (
        listening_phase(
            fatal=False, stream_open=True, capturing=False, last_rms=499, threshold=500
        )
        == ListenPhase.SILENT
    )
```

Create `pmai-mai-core/tests/audio/test_status_payload.py`:

```python
from __future__ import annotations

from pmai_core.api.audio.audio_controller import listening_status_payload
from pmai_core.resources.audio.models import AudioRuntimeStatus, ListenPhase


def test_payload_includes_live_fields() -> None:
    status = AudioRuntimeStatus(
        running=True,
        listening_enabled=True,
        selected_microphone_id="abc",
        selected_microphone_name="USB Mic",
        stream_open=True,
        phase=ListenPhase.HEARING,
        input_level=40,
        wake_word_detected_at=None,
        last_transcript=None,
        last_transcript_at=None,
        last_error=None,
    )
    payload = listening_status_payload(status)
    assert payload["selected_microphone_name"] == "USB Mic"
    assert payload["stream_open"] is True
    assert payload["phase"] == "hearing"
    assert payload["input_level"] == 40
    assert payload["running"] is True
    assert payload["last_transcript"] is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run from `pmai-mai-core`:

```bash
python -m pytest tests/audio/test_level.py tests/audio/test_status_payload.py -v
```

Expected: FAIL with `ModuleNotFoundError` for `level` or `ImportError` for `listening_status_payload` / `ListenPhase`.

- [ ] **Step 3: Write the minimal implementation**

Add to `pmai-mai-core/src/pmai_core/resources/audio/models.py`:

```python
class ListenPhase(StrEnum):
    DISCONNECTED = "disconnected"
    SILENT = "silent"
    HEARING = "hearing"
    CAPTURING = "capturing"
    ERROR = "error"
```

Extend `AudioRuntimeStatus` with these fields after `selected_microphone_id`:

```python
    selected_microphone_name: str | None
    stream_open: bool
    phase: ListenPhase
    input_level: int
```

Create `pmai-mai-core/src/pmai_core/resources/audio/level.py`:

```python
from __future__ import annotations

from pmai_core.resources.audio.models import ListenPhase


class LevelHold:
    def __init__(self, full_scale: int, hold_ms: int, chunk_ms: int) -> None:
        self._full_scale = max(1, full_scale)
        self._hold_ms = hold_ms
        self._chunk_ms = chunk_ms
        self._samples: list[tuple[int, float]] = []

    def update(self, rms: float, now_ms: int) -> int:
        self._samples.append((now_ms, rms))
        return self.level_at(now_ms)

    def level_at(self, now_ms: int) -> int:
        if not self._samples:
            return 0
        newest = self._samples[-1][0]
        window_start = newest - self._hold_ms
        peak = max(rms for stamp, rms in self._samples if stamp >= window_start)
        self._samples = [(stamp, rms) for stamp, rms in self._samples if stamp >= window_start]
        scaled = self._scale(peak)
        gap = now_ms - newest
        if gap <= self._chunk_ms:
            return scaled
        elapsed = gap - self._chunk_ms
        if elapsed >= self._hold_ms:
            return 0
        return int(round(scaled * (1 - elapsed / self._hold_ms)))

    def _scale(self, rms: float) -> int:
        return max(0, min(100, int(round(rms * 100 / self._full_scale))))


def listening_phase(
    *,
    fatal: bool,
    stream_open: bool,
    capturing: bool,
    last_rms: float,
    threshold: float,
) -> ListenPhase:
    if fatal:
        return ListenPhase.ERROR
    if not stream_open:
        return ListenPhase.DISCONNECTED
    if capturing:
        return ListenPhase.CAPTURING
    if last_rms >= threshold:
        return ListenPhase.HEARING
    return ListenPhase.SILENT
```

In `audio_controller.py`, import `AudioRuntimeStatus` and add:

```python
def listening_status_payload(status: AudioRuntimeStatus) -> dict[str, Any]:
    return {
        "running": status.running,
        "listening_enabled": status.listening_enabled,
        "selected_microphone_id": status.selected_microphone_id,
        "selected_microphone_name": status.selected_microphone_name,
        "stream_open": status.stream_open,
        "phase": status.phase.value,
        "input_level": status.input_level,
        "wake_word_detected_at": status.wake_word_detected_at,
        "last_transcript": status.last_transcript,
        "last_transcript_at": status.last_transcript_at,
        "last_error": status.last_error,
    }
```

Change `get_listening_status` to `return listening_status_payload(self._audio_service.get_status())`.

`get_status` must construct the new fields so the service still runs before Task 6 replaces the live values. In `service.py`, import `ListenPhase` and pass these keywords in the existing `AudioRuntimeStatus(...)` call:

```python
                selected_microphone_name=None,
                stream_open=False,
                phase=ListenPhase.DISCONNECTED,
                input_level=0,
```

Task 6 replaces this method with the live phase, name, and level. The payload test constructs `AudioRuntimeStatus` directly and does not call `get_status`.

- [ ] **Step 4: Run the tests to verify they pass**

Run from `pmai-mai-core`:

```bash
python -m pytest tests/audio/test_level.py tests/audio/test_status_payload.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git -C pmai-mai-core add src/pmai_core/resources/audio/level.py src/pmai_core/resources/audio/models.py src/pmai_core/resources/audio/service.py src/pmai_core/api/audio/audio_controller.py tests/audio/test_level.py tests/audio/test_status_payload.py
git -C pmai-mai-core commit -m "$(cat <<'EOF'
Expose microphone phase and input level on the listening status.

EOF
)"
```

---

### Task 6: Wire the listener

**Files:**
- Create: `pmai-mai-core/src/pmai_core/resources/audio/listen_rules.py`
- Create: `pmai-mai-core/tests/audio/test_listen_rules.py`
- Create: `pmai-mai-core/tests/audio/test_service_selection.py`
- Modify: `pmai-mai-core/src/pmai_core/resources/audio/service.py`

**Interfaces:**
- Consumes: `WakeEnergyGate`, `WakeConfirm`, `match_wake_phrase`, `resample_linear`, `FrameSlicer`, `chunk_rms`, `LevelHold`, `listening_phase`, `ListenPhase`, `build_fingerprint` / `MicrophoneInfo`, `listening_status_payload`.
- Produces: `vad_counts_as_speech(vad: Any, chunk: bytes, sample_rate: int, chunk_ms: int) -> bool`. `VadSession` with `counts_as_speech(...) -> bool` and `reset() -> None` (logs `audio_vad_frame_unusable` once). `next_silence_ms(silence_ms: int, chunk_ms: int, recording_ms: int, grace_ms: int, counts_as_speech: bool) -> int`. `capture_should_end(recording_ms: int, silence_ms: int, min_ms: int, long_silence_ms: int, max_ms: int) -> bool`. `AudioService.choose_open_target(microphones: list[MicrophoneInfo]) -> MicrophoneInfo | None`. `AudioService.apply_listen_failure(exc: Exception) -> float`. `AudioService.note_recognizer_failure(message: str) -> None`. `AudioService.note_overflow() -> None`. `get_status()` returns the new fields. `listening_enabled` stays true when the chosen mic disappears.

- [ ] **Step 1: Write the failing tests**

Create `pmai-mai-core/tests/audio/test_listen_rules.py`:

```python
from __future__ import annotations

from pmai_core.resources.audio.listen_rules import (
    VadSession,
    capture_should_end,
    next_silence_ms,
    vad_counts_as_speech,
)


class _Boom:
    def is_speech(self, _chunk: bytes, _rate: int) -> bool:
        raise RuntimeError("bad frame")


class _Speech:
    def is_speech(self, _chunk: bytes, _rate: int) -> bool:
        return True


def test_invalid_vad_frame_counts_as_speech() -> None:
    assert vad_counts_as_speech(_Boom(), b"\x00\x00", 16000, 30) is True
    assert vad_counts_as_speech(_Speech(), b"\x00\x00", 44100, 30) is True


def test_vad_session_logs_once() -> None:
    session = VadSession()
    assert session.counts_as_speech(_Boom(), b"\x00\x00", 16000, 30) is True
    assert session.logged is True
    assert session.counts_as_speech(_Boom(), b"\x00\x00", 16000, 30) is True
    session.reset()
    assert session.logged is False


def test_invalid_frame_does_not_add_silence() -> None:
    assert next_silence_ms(1500, 30, 3000, 2200, True) == 0


def test_silence_grows_only_after_grace_and_nonspeech() -> None:
    assert next_silence_ms(0, 30, 1000, 2200, False) == 0
    assert next_silence_ms(1500, 30, 3000, 2200, False) == 1530


def test_short_pause_does_not_end_capture() -> None:
    assert capture_should_end(3000, 1500, 1000, 1600, 20000) is False
    assert capture_should_end(3000, 1600, 1000, 1600, 20000) is True
    assert capture_should_end(500, 1600, 1000, 1600, 20000) is False
    assert capture_should_end(20000, 0, 1000, 1600, 20000) is True
```

Create `pmai-mai-core/tests/audio/test_service_selection.py`:

```python
from __future__ import annotations

from pmai_core.resources.audio.discovery import build_fingerprint
from pmai_core.resources.audio.models import ListenPhase, MicrophoneInfo
from pmai_core.resources.audio.service import AudioService
from pmai_core.settings import Settings


def _mic(name: str, index: int) -> MicrophoneInfo:
    fingerprint = build_fingerprint(name, "ALSA", 1)
    return MicrophoneInfo(
        microphone_id=fingerprint,
        name=name,
        hostapi_name="ALSA",
        device_index=index,
        hardware_fingerprint=fingerprint,
        channels=1,
        sample_rate=16000,
    )


def test_same_fingerprint_follows_new_index() -> None:
    service = AudioService(Settings())
    first = _mic("USB Mic", 0)
    service.choose_open_target([first])
    again = _mic("USB Mic", 7)
    chosen = service.choose_open_target([again])
    assert chosen is not None
    assert chosen.device_index == 7
    assert chosen.microphone_id == first.microphone_id


def test_missing_mic_stays_selected_and_disconnected() -> None:
    service = AudioService(Settings())
    service.start_listening()
    usb = _mic("USB Mic", 0)
    service.choose_open_target([usb])
    other = _mic("USB Other", 1)
    assert service.choose_open_target([other]) is None
    status = service.get_status()
    assert status.selected_microphone_id == usb.microphone_id
    assert status.selected_microphone_name == "USB Mic"
    assert status.phase == ListenPhase.DISCONNECTED
    assert status.listening_enabled is True
    assert status.last_error == "Micrófono no disponible: USB Mic"


def test_runtime_error_is_phase_error_and_waits_one_second() -> None:
    service = AudioService(Settings())
    delay = service.apply_listen_failure(RuntimeError("Vosk model not found"))
    status = service.get_status()
    assert delay == 1.0
    assert status.phase == ListenPhase.ERROR
    assert status.last_error == "Vosk model not found"


def test_portaudio_failure_is_disconnected_and_waits_two_seconds(monkeypatch) -> None:
    service = AudioService(Settings())
    service.choose_open_target([_mic("USB Mic", 0)])
    monkeypatch.setattr(service, "_is_portaudio", lambda _exc: True)
    delay = service.apply_listen_failure(RuntimeError("device gone"))
    status = service.get_status()
    assert delay == 2.0
    assert status.phase == ListenPhase.DISCONNECTED
    assert status.selected_microphone_name == "USB Mic"


def test_recognizer_failure_keeps_the_stream_open() -> None:
    service = AudioService(Settings())
    service._stream_open = True
    service._fatal = False
    service._last_chunk_rms = 100
    service.note_recognizer_failure("bad json")
    status = service.get_status()
    assert status.stream_open is True
    assert status.phase == ListenPhase.SILENT
    assert status.last_error == "bad json"


def test_overflow_does_not_change_phase() -> None:
    service = AudioService(Settings())
    service._stream_open = True
    service._fatal = False
    service._last_chunk_rms = 800
    service.note_overflow()
    status = service.get_status()
    assert status.phase == ListenPhase.HEARING
    assert status.last_error is None


def _boom(_text: str) -> None:
    raise RuntimeError("turn down")


def test_dispatch_failure_keeps_the_transcript() -> None:
    service = AudioService(Settings())
    service._stream_open = True
    service._fatal = False
    service._last_chunk_rms = 100
    service._chat = _boom
    service._mark_transcript("hey fede hola")
    service._dispatch_transcript("hey fede hola")
    service._capturing = False
    status = service.get_status()
    assert status.last_transcript == "hey fede hola"
    assert status.phase == ListenPhase.SILENT
```

`_dispatch_transcript` already catches the exception from `_boom`. The test then sets `_capturing = False`, which is what the listen loop does after dispatch returns. `start_listening()` only flips the flag; it does not start the audio thread.

- [ ] **Step 2: Run the tests to verify they fail**

Run from `pmai-mai-core`:

```bash
python -m pytest tests/audio/test_listen_rules.py tests/audio/test_service_selection.py -v
```

Expected: FAIL with import or attribute errors (`listen_rules`, `choose_open_target`, `apply_listen_failure`, `get_status` missing the new fields).

- [ ] **Step 3: Write the listen rules**

Create `pmai-mai-core/src/pmai_core/resources/audio/listen_rules.py`:

```python
from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_VAD_RATES = {8000, 16000, 32000, 48000}
_VAD_MS = {10, 20, 30}


def vad_counts_as_speech(vad: Any, chunk: bytes, sample_rate: int, chunk_ms: int) -> bool:
    if chunk_ms not in _VAD_MS or sample_rate not in _VAD_RATES:
        return True
    try:
        return bool(vad.is_speech(chunk, sample_rate))
    except Exception:
        return True


class VadSession:
    def __init__(self) -> None:
        self.logged = False

    def reset(self) -> None:
        self.logged = False

    def counts_as_speech(self, vad: Any, chunk: bytes, sample_rate: int, chunk_ms: int) -> bool:
        invalid_shape = chunk_ms not in _VAD_MS or sample_rate not in _VAD_RATES
        if invalid_shape:
            self._log_once()
            return True
        try:
            return bool(vad.is_speech(chunk, sample_rate))
        except Exception:
            self._log_once()
            return True

    def _log_once(self) -> None:
        if self.logged:
            return
        self.logged = True
        logger.warning("audio_vad_frame_unusable")


def next_silence_ms(
    silence_ms: int,
    chunk_ms: int,
    recording_ms: int,
    grace_ms: int,
    counts_as_speech: bool,
) -> int:
    if recording_ms < grace_ms or counts_as_speech:
        return 0
    return silence_ms + chunk_ms


def capture_should_end(
    recording_ms: int,
    silence_ms: int,
    min_ms: int,
    long_silence_ms: int,
    max_ms: int,
) -> bool:
    if recording_ms >= max_ms:
        return True
    return silence_ms >= long_silence_ms and recording_ms >= min_ms
```

- [ ] **Step 4: Wire AudioService**

In `service.py` `__init__`, after `_active_sample_rate`, add:

```python
        self._selected_microphone_name: str | None = None
        self._stream_open = False
        self._capturing = False
        self._fatal = False
        self._last_chunk_rms = 0.0
        self._level = LevelHold(
            self._audio_settings.level_rms_full_scale,
            self._audio_settings.level_hold_ms,
            self._audio_settings.chunk_ms,
        )
        self._vad_session = VadSession()
```

Replace `get_status` with:

```python
    def get_status(self) -> AudioRuntimeStatus:
        now_ms = int(time.monotonic() * 1000)
        level = self._level.level_at(now_ms)
        with self._state_lock:
            phase = listening_phase(
                fatal=self._fatal,
                stream_open=self._stream_open,
                capturing=self._capturing,
                last_rms=self._last_chunk_rms,
                threshold=self._audio_settings.wake_energy_rms,
            )
            return AudioRuntimeStatus(
                running=self._running,
                listening_enabled=self._listening_enabled,
                selected_microphone_id=self._selected_microphone_id,
                selected_microphone_name=self._selected_microphone_name,
                stream_open=self._stream_open,
                phase=phase,
                input_level=level,
                wake_word_detected_at=self._wake_word_detected_at,
                last_transcript=self._last_transcript,
                last_transcript_at=self._last_transcript_at,
                last_error=self._last_error,
            )
```

Replace `_worker_loop` with:

```python
    def _worker_loop(self) -> None:
        while self._running and not self._stop_event.is_set():
            if not self._listening_enabled:
                self._stop_event.wait(0.5)
                continue
            try:
                self._listen_once()
            except Exception as exc:  # pragma: no cover - runtime resilience
                delay = self.apply_listen_failure(exc)
                if self._is_portaudio(exc):
                    logger.warning("audio_listener_cycle_failed", error=str(exc))
                else:
                    logger.exception("audio_listener_cycle_failed", error=str(exc))
                self._stop_event.wait(delay)
```

Add these methods. `choose_open_target` replaces the old “pick the first mic if the id is missing” behavior inside `_ensure_selected_microphone`. Keep `_ensure_model`, `_extract_transcript`, `_resolve_input_sample_rate`, `_mark_wake_word`, `_mark_transcript`, `_build_transcript_with_wake`, and `_dispatch_transcript`. Delete `_extract_wake_phrase` and `_is_speech`.

```python
    def choose_open_target(self, microphones: list[MicrophoneInfo]) -> MicrophoneInfo | None:
        selected = self._remember_selection(microphones)
        if selected is None:
            self._mark_disconnected()
            return None
        for mic in microphones:
            if mic.microphone_id == selected:
                with self._state_lock:
                    self._selected_microphone_name = mic.name
                return mic
        self._mark_disconnected()
        return None

    def apply_listen_failure(self, exc: Exception) -> float:
        if self._is_portaudio(exc):
            self._mark_disconnected(detail=str(exc))
            return 2.0
        self._set_fatal(str(exc))
        return 1.0

    def note_recognizer_failure(self, message: str) -> None:
        with self._state_lock:
            self._last_error = message
            self._capturing = False
            self._fatal = False
        logger.error("audio_recognizer_failed", error=message)

    def note_overflow(self) -> None:
        logger.warning("audio_input_overflow")

    def _remember_selection(self, microphones: list[MicrophoneInfo]) -> str | None:
        by_id = {mic.microphone_id: mic for mic in microphones}
        selected = self._selected_microphone_id
        if selected in by_id:
            with self._state_lock:
                self._selected_microphone_name = by_id[selected].name
            return selected
        if selected is not None:
            return None
        chosen: str | None = None
        preferred = self._audio_settings.preferred_microphone_id
        if preferred in by_id:
            chosen = preferred
        elif self._audio_settings.auto_select_microphone and microphones:
            chosen = microphones[0].microphone_id
        if chosen is None:
            return None
        with self._state_lock:
            self._selected_microphone_id = chosen
            self._selected_microphone_name = by_id[chosen].name
        return chosen

    def _mark_disconnected(self, detail: str | None = None) -> None:
        name = self._selected_microphone_name or "desconocido"
        message = f"Micrófono no disponible: {name}"
        if detail:
            message = f"{message}. {detail}"
        with self._state_lock:
            self._fatal = False
            self._stream_open = False
            self._capturing = False
            self._last_chunk_rms = 0.0
            self._last_error = message

    def _set_fatal(self, error: str) -> None:
        with self._state_lock:
            self._fatal = True
            self._stream_open = False
            self._capturing = False
            self._last_error = error
        logger.error("audio_listener_error", error=error)

    def _mark_stream_open(self) -> None:
        with self._state_lock:
            self._stream_open = True
            self._fatal = False
            self._last_error = None
            self._capturing = False

    def _mark_stream_closed(self) -> None:
        with self._state_lock:
            self._stream_open = False
            self._capturing = False

    def _note_frame_rms(self, rms: float) -> None:
        now_ms = int(time.monotonic() * 1000)
        self._level.update(rms, now_ms)
        with self._state_lock:
            self._last_chunk_rms = rms

    def _is_portaudio(self, exc: Exception) -> bool:
        return bool(
            sd is not None
            and hasattr(sd, "PortAudioError")
            and isinstance(exc, sd.PortAudioError)
        )

    def _new_wake_recognizer(self, model: Any) -> Any:
        return KaldiRecognizer(
            model,
            16000,
            json.dumps(self._audio_settings.wake_phrases, ensure_ascii=True),
        )
```

Delete `_ensure_selected_microphone`. `list_microphones` and `_sync_selection_with_hardware` call `_remember_selection`. `list_microphones` still returns the stored id:

```python
    def list_microphones(self) -> tuple[list[MicrophoneInfo], str | None]:
        microphones = discover_usb_microphones(preferred_id=self._selected_microphone_id)
        self._remember_selection(microphones)
        return microphones, self._selected_microphone_id
```

`select_microphone` also sets `_selected_microphone_name = mic.name` inside the lock.

Replace `_listen_once` with this body. Imports to add at the top of `service.py`: `time`, `numpy as np`, `FrameSlicer`, `resample_linear`, `WakeEnergyGate`, `chunk_rms`, `WakeConfirm`, `match_wake_phrase`, `LevelHold`, `listening_phase`, `VadSession`, `capture_should_end`, `next_silence_ms`.

```python
    def _listen_once(self) -> None:
        if sd is None:
            raise RuntimeError("sounddevice is not installed")
        if webrtcvad is None:
            raise RuntimeError("webrtcvad is not installed")
        if Model is None or KaldiRecognizer is None:
            raise RuntimeError("vosk is not installed")
        model = self._ensure_model()
        microphones = discover_usb_microphones(preferred_id=self._selected_microphone_id)
        target = self.choose_open_target(microphones)
        if target is None:
            self._stop_event.wait(1.0)
            return

        stream_sample_rate = self._resolve_input_sample_rate(target)
        device_chunk_frames = int(stream_sample_rate * self._audio_settings.chunk_ms / 1000)
        if device_chunk_frames <= 0:
            raise RuntimeError("Invalid audio chunk size")

        vad = webrtcvad.Vad(2)
        self._vad_session.reset()
        wake_recognizer = self._new_wake_recognizer(model)
        command_recognizer = KaldiRecognizer(model, 16000)
        slicer = FrameSlicer(480)
        gate = WakeEnergyGate(
            self._audio_settings.wake_energy_rms,
            self._audio_settings.wake_energy_hangover_ms,
        )
        confirm = WakeConfirm(self._audio_settings.wake_confirm_chunks)
        pre_roll_chunks = max(
            1,
            int(self._audio_settings.preroll_seconds * 1000 / self._audio_settings.chunk_ms),
        )
        pre_roll: deque[bytes] = deque(maxlen=pre_roll_chunks)
        silence_ms = 0
        recording_ms = 0
        active_capture = False
        detected_wake_phrase: str | None = None
        phrases = self._audio_settings.wake_phrases
        partial_match = self._audio_settings.wake_partial_match
        chunk_ms = self._audio_settings.chunk_ms

        with sd.RawInputStream(
            samplerate=stream_sample_rate,
            channels=self._audio_settings.channels,
            dtype="int16",
            blocksize=device_chunk_frames,
            device=target.device_index,
        ) as stream:
            self._mark_stream_open()
            logger.info(
                "audio_stream_opened",
                microphone_id=target.microphone_id,
                microphone_name=target.name,
                sample_rate=stream_sample_rate,
                chunk_ms=chunk_ms,
            )
            try:
                while self._running and self._listening_enabled and not self._stop_event.is_set():
                    pcm_bytes, overflowed = stream.read(device_chunk_frames)
                    if overflowed:
                        self.note_overflow()
                    samples = np.frombuffer(bytes(pcm_bytes), dtype=np.int16)
                    if stream_sample_rate != 16000:
                        samples = resample_linear(samples, stream_sample_rate, 16000)
                    for frame in slicer.push(samples):
                        try:
                            rms = chunk_rms(frame)
                            self._note_frame_rms(rms)
                            pre_roll.append(frame)
                            if not active_capture:
                                if not gate.feed(rms, chunk_ms):
                                    confirm.reset()
                                    continue
                                accepted = wake_recognizer.AcceptWaveform(frame)
                                if accepted:
                                    heard = json.loads(wake_recognizer.Result()).get("text", "")
                                    phrase = match_wake_phrase(heard, phrases, partial_match)
                                    opened = confirm.observe(phrase, True)
                                else:
                                    heard = json.loads(wake_recognizer.PartialResult()).get(
                                        "partial", ""
                                    )
                                    phrase = match_wake_phrase(heard, phrases, partial_match)
                                    opened = confirm.observe(phrase, False)
                                if not opened or phrase is None:
                                    continue
                                active_capture = True
                                self._capturing = True
                                detected_wake_phrase = phrase
                                self._mark_wake_word()
                                command_recognizer = KaldiRecognizer(model, 16000)
                                for historical in pre_roll:
                                    command_recognizer.AcceptWaveform(historical)
                                silence_ms = 0
                                recording_ms = 0
                                logger.info(
                                    "wake_word_detected", microphone_id=target.microphone_id
                                )
                                continue

                            command_recognizer.AcceptWaveform(frame)
                            recording_ms += chunk_ms
                            counts_as_speech = self._vad_session.counts_as_speech(
                                vad, frame, 16000, chunk_ms
                            )
                            silence_ms = next_silence_ms(
                                silence_ms,
                                chunk_ms,
                                recording_ms,
                                self._audio_settings.post_wake_grace_ms,
                                counts_as_speech,
                            )
                            min_ms = int(self._audio_settings.min_recording_seconds * 1000)
                            max_ms = int(self._audio_settings.max_recording_seconds * 1000)
                            if not capture_should_end(
                                recording_ms,
                                silence_ms,
                                min_ms,
                                self._audio_settings.long_silence_ms,
                                max_ms,
                            ):
                                continue
                            transcript = self._extract_transcript(command_recognizer)
                            transcript_with_wake = self._build_transcript_with_wake(
                                transcript,
                                detected_wake_phrase,
                            )
                            if transcript_with_wake:
                                self._mark_transcript(transcript_with_wake)
                                self._dispatch_transcript(transcript_with_wake)
                            else:
                                logger.info("speech_capture_finished_without_text")
                            active_capture = False
                            self._capturing = False
                            detected_wake_phrase = None
                            silence_ms = 0
                            recording_ms = 0
                            pre_roll.clear()
                            wake_recognizer = self._new_wake_recognizer(model)
                            confirm.reset()
                        except Exception as exc:
                            self.note_recognizer_failure(str(exc))
                            active_capture = False
                            detected_wake_phrase = None
                            silence_ms = 0
                            recording_ms = 0
                            pre_roll.clear()
                            wake_recognizer = self._new_wake_recognizer(model)
                            confirm.reset()
            finally:
                self._mark_stream_closed()
```

- [ ] **Step 5: Run the tests to verify they pass**

Run from `pmai-mai-core`:

```bash
python -m pytest tests/audio -v
```

Expected: PASS for every test under `tests/audio`.

- [ ] **Step 6: Commit**

```bash
git -C pmai-mai-core add src/pmai_core/resources/audio/listen_rules.py src/pmai_core/resources/audio/service.py tests/audio/test_listen_rules.py tests/audio/test_service_selection.py
git -C pmai-mai-core commit -m "$(cat <<'EOF'
Reopen the same microphone after USB disconnect and keep short pauses.

EOF
)"
```

---

### Task 7: Chat strip

**Files:**
- Create: `pmas-web-main/src/app/pages/robotics-chat/microphone-status.ts`
- Create: `pmas-web-main/src/app/pages/robotics-chat/microphone-status.spec.ts`
- Modify: `pmas-web-main/src/app/pages/robotics-chat/robotics-chat.ts`
- Modify: `pmas-web-main/src/app/pages/robotics-chat/robotics-chat.html`

**Interfaces:**
- Consumes: `GET ${GATEWAY_URL}/audio/listening-status` with the JSON from `listening_status_payload`. The page already sends the JWT through `authInterceptor`.
- Produces: `microphoneStripLabel({ httpFailed, status }) -> string`. `microphoneLevel({ httpFailed, status }) -> number`. `microphoneDetail({ httpFailed, status }) -> { live, microphone, transcript, error }`. `MicrophoneListeningStatus`.

- [ ] **Step 1: Write the failing test**

Create `pmas-web-main/src/app/pages/robotics-chat/microphone-status.spec.ts`:

```typescript
import { describe, expect, it } from 'vitest';
import {
  microphoneDetail,
  microphoneLevel,
  microphoneStripLabel,
  type MicrophoneListeningStatus,
} from './microphone-status';

function status(patch: Partial<MicrophoneListeningStatus> = {}): MicrophoneListeningStatus {
  return {
    running: true,
    listening_enabled: true,
    selected_microphone_id: 'abc',
    selected_microphone_name: 'USB Mic',
    stream_open: true,
    phase: 'silent',
    input_level: 40,
    wake_word_detected_at: null,
    last_transcript: 'hey fede hola',
    last_transcript_at: null,
    last_error: null,
    ...patch,
  };
}

describe('microphoneStripLabel', () => {
  it('reports a failed poll before any phase', () => {
    expect(microphoneStripLabel({ httpFailed: true, status: status({ phase: 'hearing' }) })).toBe(
      'No se pudo consultar el micrófono',
    );
  });

  it('reports audio disabled when the service is not running', () => {
    expect(microphoneStripLabel({ httpFailed: false, status: status({ running: false }) })).toBe(
      'Micrófono apagado',
    );
  });

  it('reports paused listening before the phase', () => {
    expect(
      microphoneStripLabel({
        httpFailed: false,
        status: status({ listening_enabled: false, phase: 'disconnected' }),
      }),
    ).toBe('Escucha en pausa');
  });

  it('maps each phase', () => {
    expect(microphoneStripLabel({ httpFailed: false, status: status({ phase: 'error' }) })).toBe(
      'Error de audio',
    );
    expect(
      microphoneStripLabel({ httpFailed: false, status: status({ phase: 'disconnected' }) }),
    ).toBe('Desconectado');
    expect(microphoneStripLabel({ httpFailed: false, status: status({ phase: 'capturing' }) })).toBe(
      'Frase reconocida',
    );
    expect(microphoneStripLabel({ httpFailed: false, status: status({ phase: 'hearing' }) })).toBe(
      'Oyendo',
    );
    expect(microphoneStripLabel({ httpFailed: false, status: status({ phase: 'silent' }) })).toBe(
      'Conectado, en silencio',
    );
  });

  it('says nothing until the first response', () => {
    expect(microphoneStripLabel({ httpFailed: false, status: null })).toBe('');
  });
});

describe('microphoneLevel', () => {
  it('drops the bar to zero when the poll fails', () => {
    expect(microphoneLevel({ httpFailed: true, status: status({ input_level: 80 }) })).toBe(0);
  });

  it('clamps the live level', () => {
    expect(microphoneLevel({ httpFailed: false, status: status({ input_level: 40 }) })).toBe(40);
    expect(microphoneLevel({ httpFailed: false, status: status({ input_level: 140 }) })).toBe(100);
  });
});

describe('microphoneDetail', () => {
  it('keeps the last reading and marks a dead poll', () => {
    const detail = microphoneDetail({
      httpFailed: true,
      status: status({ last_error: 'Micrófono no disponible: USB Mic' }),
    });
    expect(detail.live).toBe('Sin lectura en vivo');
    expect(detail.microphone).toBe('USB Mic');
    expect(detail.transcript).toBe('hey fede hola');
    expect(detail.error).toBe('Micrófono no disponible: USB Mic');
  });

  it('uses empty labels when nothing has been heard', () => {
    const detail = microphoneDetail({
      httpFailed: false,
      status: status({
        selected_microphone_name: null,
        last_transcript: '  ',
        last_error: null,
      }),
    });
    expect(detail.live).toBe('');
    expect(detail.microphone).toBe('Ninguno');
    expect(detail.transcript).toBe('Ninguna');
    expect(detail.error).toBe('Ninguno');
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `pmas-web-main`:

```bash
npx ng test --watch=false --include=src/app/pages/robotics-chat/microphone-status.spec.ts
```

Expected: FAIL because `./microphone-status` does not exist.

- [ ] **Step 3: Write the pure helpers**

Create `pmas-web-main/src/app/pages/robotics-chat/microphone-status.ts`:

```typescript
export interface MicrophoneListeningStatus {
  running: boolean;
  listening_enabled: boolean;
  selected_microphone_id: string | null;
  selected_microphone_name: string | null;
  stream_open: boolean;
  phase: 'disconnected' | 'silent' | 'hearing' | 'capturing' | 'error';
  input_level: number;
  wake_word_detected_at: string | null;
  last_transcript: string | null;
  last_transcript_at: string | null;
  last_error: string | null;
}

export function microphoneStripLabel(input: {
  httpFailed: boolean;
  status: MicrophoneListeningStatus | null;
}): string {
  if (input.httpFailed) return 'No se pudo consultar el micrófono';
  const status = input.status;
  if (!status) return '';
  if (!status.running) return 'Micrófono apagado';
  if (!status.listening_enabled) return 'Escucha en pausa';
  switch (status.phase) {
    case 'error':
      return 'Error de audio';
    case 'disconnected':
      return 'Desconectado';
    case 'capturing':
      return 'Frase reconocida';
    case 'hearing':
      return 'Oyendo';
    case 'silent':
      return 'Conectado, en silencio';
    default:
      return 'Error de audio';
  }
}

export function microphoneLevel(input: {
  httpFailed: boolean;
  status: MicrophoneListeningStatus | null;
}): number {
  if (input.httpFailed || !input.status || !Number.isFinite(input.status.input_level)) return 0;
  return Math.max(0, Math.min(100, Math.round(input.status.input_level)));
}

export function microphoneDetail(input: {
  httpFailed: boolean;
  status: MicrophoneListeningStatus | null;
}): { live: string; microphone: string; transcript: string; error: string } {
  const status = input.status;
  return {
    live: input.httpFailed ? 'Sin lectura en vivo' : '',
    microphone: textOr(status?.selected_microphone_name, 'Ninguno'),
    transcript: textOr(status?.last_transcript, 'Ninguna'),
    error: textOr(status?.last_error, 'Ninguno'),
  };
}

function textOr(value: string | null | undefined, empty: string): string {
  const trimmed = (value ?? '').trim();
  return trimmed.length > 0 ? trimmed : empty;
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run from `pmas-web-main`:

```bash
npx ng test --watch=false --include=src/app/pages/robotics-chat/microphone-status.spec.ts
```

Expected: PASS.

- [ ] **Step 5: Poll and render the strip**

In `robotics-chat.ts`, add `OnDestroy` to the `@angular/core` import and to `implements`. Import the three functions and `MicrophoneListeningStatus` from `./microphone-status`.

Add fields:

```typescript
  micStatus = signal<MicrophoneListeningStatus | null>(null);
  micPollFailed = signal(false);
  micDetailOpen = signal(false);
  private micTimer: ReturnType<typeof setInterval> | null = null;

  readonly microphoneLabel = computed(() =>
    microphoneStripLabel({ httpFailed: this.micPollFailed(), status: this.micStatus() }),
  );
  readonly microphoneLevel = computed(() =>
    microphoneLevel({ httpFailed: this.micPollFailed(), status: this.micStatus() }),
  );
  readonly microphoneDetail = computed(() =>
    microphoneDetail({ httpFailed: this.micPollFailed(), status: this.micStatus() }),
  );
```

At the end of `ngOnInit`, call `this.startMicrophoneStatusPoll()`. Add:

```typescript
  ngOnDestroy() {
    if (this.micTimer !== null) {
      clearInterval(this.micTimer);
      this.micTimer = null;
    }
  }

  startMicrophoneStatusPoll() {
    this.refreshMicrophoneStatus();
    this.micTimer = setInterval(() => this.refreshMicrophoneStatus(), 500);
  }

  refreshMicrophoneStatus() {
    this.http.get<MicrophoneListeningStatus>(`${GATEWAY_URL}/audio/listening-status`).subscribe({
      next: (status) => {
        this.micStatus.set(status);
        this.micPollFailed.set(false);
      },
      error: () => this.micPollFailed.set(true),
    });
  }

  toggleMicrophoneDetail() {
    this.micDetailOpen.update((open) => !open);
  }
```

Do not clear `micStatus` on error. Do not change `toggleChatVoiceInput` or `sendChat`.

In `robotics-chat.html`, inside the chat input area and before the quick-options block, insert:

```html
        @if (microphoneLabel()) {
          <div class="mb-2 rounded-2xl border border-outline bg-surface px-3 py-2">
            <button
              type="button"
              (click)="toggleMicrophoneDetail()"
              class="flex w-full items-center gap-3 text-left"
              [attr.aria-expanded]="micDetailOpen()">
              <span class="min-w-0 flex-1 text-xs font-medium text-on-surface">{{ microphoneLabel() }}</span>
              <span
                class="relative h-2 w-24 shrink-0 overflow-hidden rounded-full bg-surface-container-highest"
                role="meter"
                aria-valuemin="0"
                aria-valuemax="100"
                [attr.aria-valuenow]="microphoneLevel()"
                [attr.aria-label]="'Nivel del micrófono ' + microphoneLevel()">
                <span
                  class="absolute inset-y-0 left-0 bg-primary"
                  [style.width.%]="microphoneLevel()"></span>
              </span>
            </button>
            @if (micDetailOpen()) {
              <dl class="mt-2 space-y-1 text-xs text-on-surface-variant">
                @if (microphoneDetail().live) {
                  <div class="text-error">{{ microphoneDetail().live }}</div>
                }
                <div class="flex gap-2"><dt>Micrófono</dt><dd class="text-on-surface">{{ microphoneDetail().microphone }}</dd></div>
                <div class="flex gap-2"><dt>Última frase</dt><dd class="text-on-surface">{{ microphoneDetail().transcript }}</dd></div>
                <div class="flex gap-2"><dt>Último error</dt><dd class="text-on-surface">{{ microphoneDetail().error }}</dd></div>
              </dl>
            }
          </div>
        }
```

Leave the browser mic button as it is.

- [ ] **Step 6: Re-run the label tests**

Run from `pmas-web-main`:

```bash
npx ng test --watch=false --include=src/app/pages/robotics-chat/microphone-status.spec.ts
```

Expected: PASS. The template has no separate unit test. The eight labels, the zeroed meter, and the detail strings are covered by `microphone-status.spec.ts`.

- [ ] **Step 7: Commit**

```bash
git -C pmas-web-main add src/app/pages/robotics-chat/microphone-status.ts src/app/pages/robotics-chat/microphone-status.spec.ts src/app/pages/robotics-chat/robotics-chat.ts src/app/pages/robotics-chat/robotics-chat.html
git -C pmas-web-main commit -m "$(cat <<'EOF'
Show whether the robot microphone is connected and hearing.

EOF
)"
```
