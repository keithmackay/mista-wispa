# mista-wispa Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a local-first macOS voice dictation tool that captures speech via push-to-talk (Fn key), transcribes with MLX Whisper, cleans up text, and inserts it at the cursor system-wide.

**Architecture:** Single Python process — a rumps menu bar app that monitors the Fn key via a Quartz event tap, captures audio with sounddevice, runs Silero VAD + MLX Whisper for transcription, applies rule-based (and optional LLM) text cleanup, then inserts text via Accessibility API or clipboard fallback.

**Tech Stack:** Python 3.12+, uv, PyObjC, rumps, sounddevice, mlx-whisper, silero-vad (torch), openai (for optional local LLM)

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/mista_wispa/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

**Step 1: Create pyproject.toml**

```toml
[project]
name = "mista-wispa"
version = "0.1.0"
description = "Local-first voice dictation for macOS"
requires-python = ">=3.12"
dependencies = [
    "rumps>=0.4.0",
    "pyobjc-framework-Cocoa",
    "pyobjc-framework-Quartz",
    "pyobjc-framework-ApplicationServices",
    "mlx-whisper",
    "silero-vad",
    "torch",
    "sounddevice",
    "numpy",
    "openai",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-mock",
]

[project.scripts]
mista-wispa = "mista_wispa.app:main"

[build-system]
requires = ["setuptools>=75.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Step 2: Create package init**

```python
# src/mista_wispa/__init__.py
```

(Empty file — just marks the package.)

**Step 3: Create test scaffolding**

```python
# tests/__init__.py
```

```python
# tests/conftest.py
```

(Empty files for now.)

**Step 4: Install dependencies**

Run: `cd /Users/Michael.Stricklen/dev/mista-wispa && uv venv && uv pip install -e ".[dev]"`
Expected: Successful install, all dependencies resolved.

**Step 5: Verify pytest runs**

Run: `uv run pytest --co -q`
Expected: "no tests ran" (no test files yet), exit 0 or 5 (no tests collected is fine).

**Step 6: Commit**

```bash
git add pyproject.toml src/ tests/
git commit -m "chore: scaffold project structure and dependencies"
```

---

### Task 2: Settings Module

**Files:**
- Create: `src/mista_wispa/settings.py`
- Create: `tests/test_settings.py`

**Step 1: Write failing tests**

```python
# tests/test_settings.py
import json
from pathlib import Path

from mista_wispa.settings import Settings


def test_default_settings():
    s = Settings()
    assert s.llm_cleanup_enabled is False
    assert s.llm_server_url == "http://127.0.0.1:1234/v1"


def test_load_from_file(tmp_path):
    config = {"llm_cleanup_enabled": True, "llm_server_url": "http://localhost:9999/v1"}
    config_file = tmp_path / "settings.json"
    config_file.write_text(json.dumps(config))

    s = Settings(config_path=config_file)
    assert s.llm_cleanup_enabled is True
    assert s.llm_server_url == "http://localhost:9999/v1"


def test_save_creates_file(tmp_path):
    config_file = tmp_path / "subdir" / "settings.json"
    s = Settings(config_path=config_file)
    s.llm_cleanup_enabled = True
    s.save()

    loaded = json.loads(config_file.read_text())
    assert loaded["llm_cleanup_enabled"] is True


def test_missing_file_uses_defaults(tmp_path):
    config_file = tmp_path / "nonexistent" / "settings.json"
    s = Settings(config_path=config_file)
    assert s.llm_cleanup_enabled is False
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_settings.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mista_wispa.settings'`

**Step 3: Write implementation**

```python
# src/mista_wispa/settings.py
import json
from pathlib import Path

_DEFAULT_PATH = Path.home() / ".config" / "mista-wispa" / "settings.json"

_DEFAULTS = {
    "llm_cleanup_enabled": False,
    "llm_server_url": "http://127.0.0.1:1234/v1",
}


class Settings:
    def __init__(self, config_path: Path | None = None):
        self._path = config_path or _DEFAULT_PATH
        data = _DEFAULTS.copy()
        if self._path.exists():
            with open(self._path) as f:
                data.update(json.load(f))
        self.llm_cleanup_enabled: bool = data["llm_cleanup_enabled"]
        self.llm_server_url: str = data["llm_server_url"]

    def save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(
                {
                    "llm_cleanup_enabled": self.llm_cleanup_enabled,
                    "llm_server_url": self.llm_server_url,
                },
                f,
                indent=2,
            )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_settings.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add src/mista_wispa/settings.py tests/test_settings.py
git commit -m "feat: add settings module with JSON persistence"
```

---

### Task 3: Text Cleanup — Rule-Based

**Files:**
- Create: `src/mista_wispa/cleanup.py`
- Create: `tests/test_cleanup.py`

**Step 1: Write failing tests**

```python
# tests/test_cleanup.py
from mista_wispa.cleanup import rule_based_cleanup


def test_removes_filler_words():
    assert rule_based_cleanup("I um think this is uh good") == "I think this is good"


def test_removes_filler_phrases():
    assert rule_based_cleanup("You know I mean it was basically fine") == "It was fine"


def test_normalizes_whitespace():
    assert rule_based_cleanup("hello   world") == "Hello world"


def test_fixes_double_punctuation():
    assert rule_based_cleanup("hello..  world") == "Hello. World"


def test_capitalizes_after_sentence_end():
    assert rule_based_cleanup("first sentence. second sentence") == "First sentence. Second sentence"


def test_capitalizes_first_word():
    assert rule_based_cleanup("hello world") == "Hello world"


def test_empty_input():
    assert rule_based_cleanup("") == ""


def test_only_fillers():
    assert rule_based_cleanup("um uh like") == ""


def test_preserves_meaning():
    assert rule_based_cleanup("The meeting is at 3 PM.") == "The meeting is at 3 PM."


def test_filler_at_start():
    assert rule_based_cleanup("So basically the plan is good") == "The plan is good"


def test_question_mark_capitalization():
    assert rule_based_cleanup("is it done? yes it is") == "Is it done? Yes it is"


def test_exclamation_capitalization():
    assert rule_based_cleanup("wow! that is great") == "Wow! That is great"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cleanup.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write implementation**

```python
# src/mista_wispa/cleanup.py
import re

_FILLER_WORDS = {
    "um", "uh", "uhm", "umm", "ah", "er",
    "like", "basically", "literally", "actually",
    "so", "well", "right",
}

_FILLER_PHRASES = [
    "you know",
    "i mean",
    "kind of",
    "sort of",
]


def rule_based_cleanup(text: str) -> str:
    if not text.strip():
        return ""

    t = text

    # Remove filler phrases (case-insensitive)
    for phrase in _FILLER_PHRASES:
        t = re.sub(rf"\b{phrase}\b", "", t, flags=re.IGNORECASE)

    # Remove filler words (case-insensitive, whole words only)
    words = t.split()
    words = [w for w in words if w.strip(".,!?;:").lower() not in _FILLER_WORDS]
    t = " ".join(words)

    # Normalize whitespace
    t = re.sub(r"\s+", " ", t).strip()

    # Fix double/triple punctuation
    t = re.sub(r"([.!?])[.!?]+", r"\1", t)

    # Ensure space after sentence-ending punctuation
    t = re.sub(r"([.!?])(\s*)([a-zA-Z])", lambda m: f"{m.group(1)} {m.group(3).upper()}", t)

    # Capitalize first character
    if t:
        t = t[0].upper() + t[1:]

    # Clean up if everything was fillers
    t = t.strip(" .,!?")

    return t
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cleanup.py -v`
Expected: All passed. If any fail, adjust the regex logic until all pass.

**Step 5: Commit**

```bash
git add src/mista_wispa/cleanup.py tests/test_cleanup.py
git commit -m "feat: add rule-based text cleanup with filler removal and formatting"
```

---

### Task 4: Text Cleanup — LLM

**Files:**
- Modify: `src/mista_wispa/cleanup.py`
- Create: `tests/test_cleanup_llm.py`

**Step 1: Write failing tests**

```python
# tests/test_cleanup_llm.py
from unittest.mock import MagicMock, patch

import pytest

from mista_wispa.cleanup import llm_cleanup


@pytest.fixture
def mock_openai():
    with patch("mista_wispa.cleanup.OpenAI") as mock_cls:
        client = MagicMock()
        mock_cls.return_value = client
        choice = MagicMock()
        choice.message.content = "The meeting is at three PM tomorrow."
        client.chat.completions.create.return_value = MagicMock(choices=[choice])
        yield client


def test_llm_cleanup_calls_api(mock_openai):
    result = llm_cleanup("the meeting is at three pm tomorrow", server_url="http://localhost:1234/v1")
    assert result == "The meeting is at three PM tomorrow."
    mock_openai.chat.completions.create.assert_called_once()


def test_llm_cleanup_sends_system_prompt(mock_openai):
    llm_cleanup("hello", server_url="http://localhost:1234/v1")
    call_args = mock_openai.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert "preserve meaning" in messages[0]["content"].lower()


def test_llm_cleanup_returns_original_on_timeout():
    with patch("mista_wispa.cleanup.OpenAI") as mock_cls:
        client = MagicMock()
        mock_cls.return_value = client
        client.chat.completions.create.side_effect = Exception("timeout")
        result = llm_cleanup("original text", server_url="http://localhost:1234/v1")
    assert result == "original text"


def test_llm_cleanup_returns_original_on_empty_response():
    with patch("mista_wispa.cleanup.OpenAI") as mock_cls:
        client = MagicMock()
        mock_cls.return_value = client
        choice = MagicMock()
        choice.message.content = ""
        client.chat.completions.create.return_value = MagicMock(choices=[choice])
        result = llm_cleanup("original text", server_url="http://localhost:1234/v1")
    assert result == "original text"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cleanup_llm.py -v`
Expected: FAIL — `ImportError: cannot import name 'llm_cleanup'`

**Step 3: Add llm_cleanup to cleanup.py**

Append to `src/mista_wispa/cleanup.py`:

```python
from openai import OpenAI

_LLM_SYSTEM_PROMPT = (
    "You are a text cleanup assistant. The user will provide raw speech-to-text output. "
    "Clean it up: fix grammar, improve punctuation, format lists if detected. "
    "Preserve meaning exactly. Do not add or remove content. "
    "Return only the cleaned text, nothing else."
)


def llm_cleanup(text: str, *, server_url: str, model: str = "local-model", timeout: float = 3.0) -> str:
    if not text.strip():
        return text
    try:
        client = OpenAI(base_url=server_url, api_key="not-needed")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _LLM_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            timeout=timeout,
        )
        result = response.choices[0].message.content
        return result if result and result.strip() else text
    except Exception:
        return text
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cleanup_llm.py -v`
Expected: All passed

**Step 5: Run all tests**

Run: `uv run pytest -v`
Expected: All tests pass (settings + cleanup + llm)

**Step 6: Commit**

```bash
git add src/mista_wispa/cleanup.py tests/test_cleanup_llm.py
git commit -m "feat: add optional LLM text cleanup with timeout fallback"
```

---

### Task 5: Audio Capture Module

**Files:**
- Create: `src/mista_wispa/audio.py`
- Create: `tests/test_audio.py`

**Step 1: Write failing tests**

```python
# tests/test_audio.py
import numpy as np
from unittest.mock import patch, MagicMock

from mista_wispa.audio import AudioRecorder


def test_recorder_initial_state():
    with patch("mista_wispa.audio.sd"):
        rec = AudioRecorder(sample_rate=16000)
        assert rec.is_recording is False
        assert rec.get_audio() is None


def test_start_sets_recording_flag():
    with patch("mista_wispa.audio.sd"):
        rec = AudioRecorder(sample_rate=16000)
        rec.start()
        assert rec.is_recording is True


def test_stop_returns_audio_array():
    with patch("mista_wispa.audio.sd") as mock_sd:
        rec = AudioRecorder(sample_rate=16000)
        rec.start()
        # Simulate some audio frames being captured
        fake_audio = np.zeros((1600,), dtype=np.float32)
        rec._frames.append(fake_audio)
        audio = rec.stop()
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert len(audio) == 1600


def test_stop_when_not_recording_returns_none():
    with patch("mista_wispa.audio.sd"):
        rec = AudioRecorder(sample_rate=16000)
        assert rec.stop() is None


def test_stop_with_no_frames_returns_none():
    with patch("mista_wispa.audio.sd"):
        rec = AudioRecorder(sample_rate=16000)
        rec.start()
        audio = rec.stop()
        assert audio is None
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_audio.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write implementation**

```python
# src/mista_wispa/audio.py
import threading

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_SIZE = 1024


class AudioRecorder:
    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self._sample_rate = sample_rate
        self._stream: sd.InputStream | None = None
        self._frames: list[np.ndarray] = []
        self._lock = threading.Lock()
        self.is_recording = False

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        with self._lock:
            if self.is_recording:
                self._frames.append(indata[:, 0].copy())

    def start(self):
        with self._lock:
            self._frames.clear()
            self.is_recording = True
        self._stream = sd.InputStream(
            samplerate=self._sample_rate,
            channels=CHANNELS,
            blocksize=BLOCK_SIZE,
            dtype=np.float32,
            callback=self._audio_callback,
        )
        self._stream.start()

    def stop(self) -> np.ndarray | None:
        if not self.is_recording:
            return None
        self.is_recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        with self._lock:
            if not self._frames:
                return None
            audio = np.concatenate(self._frames)
            self._frames.clear()
        return audio

    def get_audio(self) -> np.ndarray | None:
        with self._lock:
            if not self._frames:
                return None
            return np.concatenate(self._frames)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_audio.py -v`
Expected: All passed

**Step 5: Commit**

```bash
git add src/mista_wispa/audio.py tests/test_audio.py
git commit -m "feat: add audio capture module with sounddevice"
```

---

### Task 6: Voice Pipeline — VAD + Whisper

**Files:**
- Create: `src/mista_wispa/pipeline.py`
- Create: `tests/test_pipeline.py`

**Step 1: Write failing tests**

```python
# tests/test_pipeline.py
import numpy as np
from unittest.mock import patch, MagicMock

from mista_wispa.pipeline import trim_silence, transcribe


def test_trim_silence_returns_none_for_silent_audio():
    # 1 second of silence
    silent = np.zeros((16000,), dtype=np.float32)
    with patch("mista_wispa.pipeline._vad_model") as mock_model:
        with patch("mista_wispa.pipeline.get_speech_timestamps", return_value=[]):
            result = trim_silence(silent, sample_rate=16000)
    assert result is None


def test_trim_silence_returns_speech_segments():
    audio = np.random.randn(32000).astype(np.float32) * 0.1
    speech_chunk = np.ones((8000,), dtype=np.float32) * 0.5

    with patch("mista_wispa.pipeline.get_speech_timestamps", return_value=[{"start": 0, "end": 8000}]):
        with patch("mista_wispa.pipeline.collect_chunks", return_value=MagicMock(numpy=MagicMock(return_value=speech_chunk))):
            result = trim_silence(audio, sample_rate=16000)
    assert result is not None
    assert len(result) == 8000


def test_transcribe_returns_text():
    audio = np.random.randn(16000).astype(np.float32)
    with patch("mista_wispa.pipeline.mlx_whisper") as mock_whisper:
        mock_whisper.transcribe.return_value = {"text": "Hello world"}
        result = transcribe(audio)
    assert result == "Hello world"


def test_transcribe_strips_whitespace():
    audio = np.random.randn(16000).astype(np.float32)
    with patch("mista_wispa.pipeline.mlx_whisper") as mock_whisper:
        mock_whisper.transcribe.return_value = {"text": "  Hello world  "}
        result = transcribe(audio)
    assert result == "Hello world"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write implementation**

```python
# src/mista_wispa/pipeline.py
import numpy as np
import torch
import mlx_whisper
from silero_vad import load_silero_vad, get_speech_timestamps, collect_chunks

WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"

_vad_model = None


def _get_vad_model():
    global _vad_model
    if _vad_model is None:
        _vad_model = load_silero_vad()
    return _vad_model


def trim_silence(audio: np.ndarray, sample_rate: int = 16000) -> np.ndarray | None:
    model = _get_vad_model()
    wav = torch.from_numpy(audio).float()
    timestamps = get_speech_timestamps(wav, model, sampling_rate=sample_rate)
    if not timestamps:
        return None
    speech = collect_chunks(timestamps, wav)
    return speech.numpy()


def transcribe(audio: np.ndarray) -> str:
    result = mlx_whisper.transcribe(audio, path_or_hf_repo=WHISPER_MODEL)
    return result["text"].strip()
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_pipeline.py -v`
Expected: All passed

**Step 5: Commit**

```bash
git add src/mista_wispa/pipeline.py tests/test_pipeline.py
git commit -m "feat: add voice pipeline with Silero VAD and MLX Whisper"
```

---

### Task 7: Text Insertion

**Files:**
- Create: `src/mista_wispa/insertion.py`
- Create: `tests/test_insertion.py`

**Step 1: Write failing tests**

These tests mock the PyObjC APIs since they require macOS Accessibility permissions at runtime.

```python
# tests/test_insertion.py
from unittest.mock import patch, MagicMock, call

from mista_wispa.insertion import insert_text, _insert_via_accessibility, _insert_via_clipboard


def test_insert_via_clipboard_sets_and_restores():
    with patch("mista_wispa.insertion._get_pasteboard") as mock_pb_fn:
        mock_pb = MagicMock()
        mock_pb_fn.return_value = mock_pb
        # Simulate existing clipboard content
        mock_pb.stringForType_.return_value = "old clipboard"
        with patch("mista_wispa.insertion._simulate_paste") as mock_paste:
            with patch("mista_wispa.insertion.time.sleep"):
                _insert_via_clipboard("new text")
        # Should have set "new text" on pasteboard
        mock_pb.clearContents.assert_called()
        mock_pb.setString_forType_.assert_any_call("new text", "public.utf8-plain-text")


def test_insert_text_tries_accessibility_first():
    with patch("mista_wispa.insertion._insert_via_accessibility", return_value=True) as mock_ax:
        with patch("mista_wispa.insertion._insert_via_clipboard") as mock_clip:
            insert_text("hello")
    mock_ax.assert_called_once_with("hello")
    mock_clip.assert_not_called()


def test_insert_text_falls_back_to_clipboard():
    with patch("mista_wispa.insertion._insert_via_accessibility", return_value=False) as mock_ax:
        with patch("mista_wispa.insertion._insert_via_clipboard") as mock_clip:
            insert_text("hello")
    mock_ax.assert_called_once_with("hello")
    mock_clip.assert_called_once_with("hello")


def test_insert_text_empty_string_is_noop():
    with patch("mista_wispa.insertion._insert_via_accessibility") as mock_ax:
        with patch("mista_wispa.insertion._insert_via_clipboard") as mock_clip:
            insert_text("")
    mock_ax.assert_not_called()
    mock_clip.assert_not_called()
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_insertion.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write implementation**

```python
# src/mista_wispa/insertion.py
import time

from AppKit import NSPasteboard, NSStringPboardType
from ApplicationServices import (
    AXUIElementCreateSystemWide,
    AXUIElementCopyAttributeValue,
    AXUIElementSetAttributeValue,
)
from CoreFoundation import CFRange
import Quartz


def _get_pasteboard():
    return NSPasteboard.generalPasteboard()


def _insert_via_accessibility(text: str) -> bool:
    try:
        system_wide = AXUIElementCreateSystemWide()
        err, focused = AXUIElementCopyAttributeValue(system_wide, "AXFocusedUIElement", None)
        if err != 0 or focused is None:
            return False

        # Check if it's a password field
        err, is_secure = AXUIElementCopyAttributeValue(focused, "AXIsSecureTextField", None)
        if err == 0 and is_secure:
            return False

        # Check if element has a value attribute
        err, current_value = AXUIElementCopyAttributeValue(focused, "AXValue", None)
        if err != 0:
            return False

        # Get selected text range (cursor position)
        err, selected_range = AXUIElementCopyAttributeValue(focused, "AXSelectedTextRange", None)
        if err != 0:
            # No selection info — append to end
            new_value = (current_value or "") + text
            AXUIElementSetAttributeValue(focused, "AXValue", new_value)
            return True

        # Insert at cursor position
        loc = selected_range.location
        length = selected_range.length
        before = current_value[:loc]
        after = current_value[loc + length:]
        new_value = before + text + after
        AXUIElementSetAttributeValue(focused, "AXValue", new_value)

        # Move cursor to end of inserted text
        new_range = CFRange(loc + len(text), 0)
        AXUIElementSetAttributeValue(focused, "AXSelectedTextRange", new_range)

        return True
    except Exception:
        return False


def _simulate_paste():
    src = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateCombinedSessionState)
    # Cmd down
    cmd_down = Quartz.CGEventCreateKeyboardEvent(src, 0x09, True)  # 0x09 = 'v'
    Quartz.CGEventSetFlags(cmd_down, Quartz.kCGEventFlagMaskCommand)
    Quartz.CGEventPost(Quartz.kCGAnnotatedSessionEventTap, cmd_down)
    # Cmd up
    cmd_up = Quartz.CGEventCreateKeyboardEvent(src, 0x09, False)
    Quartz.CGEventSetFlags(cmd_up, Quartz.kCGEventFlagMaskCommand)
    Quartz.CGEventPost(Quartz.kCGAnnotatedSessionEventTap, cmd_up)


def _insert_via_clipboard(text: str):
    pb = _get_pasteboard()
    # Save old clipboard
    old = pb.stringForType_("public.utf8-plain-text")

    # Set new text
    pb.clearContents()
    pb.setString_forType_(text, "public.utf8-plain-text")

    # Paste
    _simulate_paste()

    # Restore after delay
    time.sleep(0.15)
    if old is not None:
        pb.clearContents()
        pb.setString_forType_(old, "public.utf8-plain-text")


def insert_text(text: str):
    if not text:
        return
    if not _insert_via_accessibility(text):
        _insert_via_clipboard(text)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_insertion.py -v`
Expected: All passed

**Step 5: Commit**

```bash
git add src/mista_wispa/insertion.py tests/test_insertion.py
git commit -m "feat: add text insertion via Accessibility API with clipboard fallback"
```

---

### Task 8: Hotkey Listener

**Files:**
- Create: `src/mista_wispa/hotkey.py`
- Create: `tests/test_hotkey.py`

**Step 1: Write failing tests**

The Fn key monitoring requires a Quartz event tap which only works with Accessibility permissions on a real macOS session. Tests verify the callback logic in isolation.

```python
# tests/test_hotkey.py
from unittest.mock import MagicMock

from mista_wispa.hotkey import FnKeyMonitor


def test_initial_state():
    monitor = FnKeyMonitor(on_press=MagicMock(), on_release=MagicMock())
    assert monitor.is_pressed is False


def test_press_callback():
    on_press = MagicMock()
    on_release = MagicMock()
    monitor = FnKeyMonitor(on_press=on_press, on_release=on_release)

    monitor._handle_fn_event(pressed=True)
    assert monitor.is_pressed is True
    on_press.assert_called_once()
    on_release.assert_not_called()


def test_release_callback():
    on_press = MagicMock()
    on_release = MagicMock()
    monitor = FnKeyMonitor(on_press=on_press, on_release=on_release)

    monitor._handle_fn_event(pressed=True)
    monitor._handle_fn_event(pressed=False)
    assert monitor.is_pressed is False
    on_release.assert_called_once()


def test_duplicate_press_ignored():
    on_press = MagicMock()
    monitor = FnKeyMonitor(on_press=on_press, on_release=MagicMock())

    monitor._handle_fn_event(pressed=True)
    monitor._handle_fn_event(pressed=True)
    assert on_press.call_count == 1


def test_release_without_press_ignored():
    on_release = MagicMock()
    monitor = FnKeyMonitor(on_press=MagicMock(), on_release=on_release)

    monitor._handle_fn_event(pressed=False)
    on_release.assert_not_called()
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_hotkey.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write implementation**

```python
# src/mista_wispa/hotkey.py
from typing import Callable

import Quartz


class FnKeyMonitor:
    def __init__(self, on_press: Callable, on_release: Callable):
        self._on_press = on_press
        self._on_release = on_release
        self.is_pressed = False
        self._tap = None

    def _handle_fn_event(self, pressed: bool):
        if pressed and not self.is_pressed:
            self.is_pressed = True
            self._on_press()
        elif not pressed and self.is_pressed:
            self.is_pressed = False
            self._on_release()

    def _event_callback(self, proxy, event_type, event, refcon):
        if event_type == Quartz.NSEventTypeSystemDefined:
            ns_event = Quartz.NSEvent.eventWithCGEvent_(event)
            if ns_event and ns_event.subtype() == 6:  # Fn key subtype
                # Bit 0 of data1 indicates Fn key state
                fn_pressed = bool(ns_event.data1() & 0x01)
                self._handle_fn_event(pressed=fn_pressed)
        return event

    def start(self):
        mask = Quartz.NSEventMaskSystemDefined
        self._tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionListenOnly,
            mask,
            self._event_callback,
            None,
        )
        if self._tap is None:
            raise PermissionError(
                "Could not create event tap. "
                "Grant Accessibility permission in System Settings > Privacy & Security > Accessibility."
            )
        source = Quartz.CFMachPortCreateRunLoopSource(None, self._tap, 0)
        loop = Quartz.CFRunLoopGetCurrent()
        Quartz.CFRunLoopAddSource(loop, source, Quartz.kCFRunLoopCommonModes)
        Quartz.CGEventTapEnable(self._tap, True)

    def stop(self):
        if self._tap:
            Quartz.CGEventTapEnable(self._tap, False)
            self._tap = None
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_hotkey.py -v`
Expected: All passed

**Step 5: Commit**

```bash
git add src/mista_wispa/hotkey.py tests/test_hotkey.py
git commit -m "feat: add Fn key monitor via Quartz event tap"
```

---

### Task 9: Menu Bar App — Integration

**Files:**
- Create: `src/mista_wispa/app.py`

This is the integration task that wires everything together. Testing is manual — launch the app, hold Fn, speak, verify text appears.

**Step 1: Write the app**

```python
# src/mista_wispa/app.py
import threading

import numpy as np
import rumps

from mista_wispa.audio import AudioRecorder
from mista_wispa.cleanup import rule_based_cleanup, llm_cleanup
from mista_wispa.hotkey import FnKeyMonitor
from mista_wispa.insertion import insert_text
from mista_wispa.pipeline import trim_silence, transcribe
from mista_wispa.settings import Settings

ICON_IDLE = "🎙"
ICON_RECORDING = "🔴"
ICON_PROCESSING = "⏳"


class MistaWispaApp(rumps.App):
    def __init__(self):
        super().__init__(ICON_IDLE, quit_button="Quit")
        self.settings = Settings()
        self.recorder = AudioRecorder()
        self.hotkey = FnKeyMonitor(on_press=self._on_fn_press, on_release=self._on_fn_release)

        self.menu = [
            rumps.MenuItem("LLM Cleanup", callback=self._toggle_llm),
        ]
        self._update_llm_menu()

    def _update_llm_menu(self):
        self.menu["LLM Cleanup"].state = self.settings.llm_cleanup_enabled

    def _toggle_llm(self, sender):
        self.settings.llm_cleanup_enabled = not self.settings.llm_cleanup_enabled
        self.settings.save()
        self._update_llm_menu()

    def _on_fn_press(self):
        self.title = ICON_RECORDING
        self.recorder.start()

    def _on_fn_release(self):
        self.title = ICON_PROCESSING
        audio = self.recorder.stop()
        if audio is None:
            self.title = ICON_IDLE
            return
        # Process in background thread to keep UI responsive
        threading.Thread(target=self._process_audio, args=(audio,), daemon=True).start()

    def _process_audio(self, audio: np.ndarray):
        try:
            trimmed = trim_silence(audio)
            if trimmed is None:
                return

            text = transcribe(trimmed)
            if not text:
                return

            text = rule_based_cleanup(text)
            if not text:
                return

            if self.settings.llm_cleanup_enabled:
                text = llm_cleanup(text, server_url=self.settings.llm_server_url)

            insert_text(text)
        finally:
            self.title = ICON_IDLE


def main():
    app = MistaWispaApp()
    # Start hotkey listener on main run loop (rumps runs the CFRunLoop)
    app.hotkey.start()
    app.run()


if __name__ == "__main__":
    main()
```

**Step 2: Test manually**

Run: `uv run mista-wispa`

1. Verify menu bar icon appears (🎙)
2. If Accessibility permission prompt appears, grant it in System Settings
3. Open a text editor (e.g. TextEdit)
4. Hold Fn key — icon should change to 🔴
5. Speak a sentence
6. Release Fn — icon should change to ⏳ then back to 🎙
7. Verify text appeared in TextEdit

**Step 3: Commit**

```bash
git add src/mista_wispa/app.py
git commit -m "feat: add menu bar app integrating all components"
```

---

### Task 10: First-Launch Permission Guidance

**Files:**
- Modify: `src/mista_wispa/app.py`

**Step 1: Add permission check on startup**

Add to `app.py` before `app.run()`:

```python
def _check_accessibility():
    from ApplicationServices import AXIsProcessTrustedWithOptions
    from CoreFoundation import CFDictionaryCreate, kCFBooleanTrue

    options = {
        "AXTrustedCheckOptionPrompt": kCFBooleanTrue,
    }
    trusted = AXIsProcessTrustedWithOptions(options)
    if not trusted:
        rumps.alert(
            title="Accessibility Permission Required",
            message=(
                "mista-wispa needs Accessibility access to capture the Fn key "
                "and insert text.\n\n"
                "Go to System Settings > Privacy & Security > Accessibility "
                "and enable mista-wispa.\n\n"
                "You may also need to disable the system dictation shortcut:\n"
                "System Settings > Keyboard > Dictation > Shortcut > Off"
            ),
        )
```

Call `_check_accessibility()` in `main()` before `app.hotkey.start()`.

**Step 2: Test manually**

Run: `uv run mista-wispa`
Expected: If Accessibility not yet granted, an alert dialog appears with instructions.

**Step 3: Commit**

```bash
git add src/mista_wispa/app.py
git commit -m "feat: add first-launch accessibility permission guidance"
```

---

## Summary

| Task | Component | Testable | Estimated Complexity |
|------|-----------|----------|---------------------|
| 1 | Project scaffolding | N/A | Low |
| 2 | Settings | Unit tests | Low |
| 3 | Text cleanup (rules) | Unit tests | Low |
| 4 | Text cleanup (LLM) | Mocked tests | Low |
| 5 | Audio capture | Mocked tests | Medium |
| 6 | Voice pipeline (VAD + Whisper) | Mocked tests | Medium |
| 7 | Text insertion | Mocked tests | High |
| 8 | Hotkey listener | Unit + manual | High |
| 9 | Menu bar app | Manual | Medium |
| 10 | Permission guidance | Manual | Low |

**Critical path:** Tasks 1-6 are independent foundations. Task 7-8 are the hardest macOS integration pieces. Task 9 wires everything together. Task 10 is polish.

**First milestone:** After Task 9, you have a working end-to-end dictation tool.
