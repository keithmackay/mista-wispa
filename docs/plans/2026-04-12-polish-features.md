# Polish Features Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add error notifications, robust clipboard preservation, and a proper .app bundle to mista-wispa.

**Architecture:** Error notifications use macOS `NSUserNotification` via rumps. Clipboard preservation saves/restores all pasteboard types (rich text, images, files), not just plain text. The .app bundle uses `py2app` to create a standalone macOS application.

**Tech Stack:** PyObjC (NSPasteboard, NSUserNotification), rumps notifications, py2app

---

### Task 1: Error Notifications

**Files:**
- Create: `src/mista_wispa/notify.py`
- Create: `tests/test_notify.py`
- Modify: `src/mista_wispa/app.py`
- Modify: `src/mista_wispa/insertion.py`

**Step 1: Write failing tests**

```python
# tests/test_notify.py
from unittest.mock import patch, MagicMock

from mista_wispa.notify import notify


def test_notify_calls_rumps_notification():
    with patch("mista_wispa.notify.rumps.notification") as mock_notif:
        notify("Title", "Body text")
    mock_notif.assert_called_once_with(
        title="Title",
        subtitle="",
        message="Body text",
        sound=False,
    )


def test_notify_with_subtitle():
    with patch("mista_wispa.notify.rumps.notification") as mock_notif:
        notify("Title", "Body", subtitle="Sub")
    mock_notif.assert_called_once_with(
        title="Title",
        subtitle="Sub",
        message="Body",
        sound=False,
    )
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_notify.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write implementation**

```python
# src/mista_wispa/notify.py
import rumps


def notify(title: str, message: str, *, subtitle: str = ""):
    rumps.notification(
        title=title,
        subtitle=subtitle,
        message=message,
        sound=False,
    )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_notify.py -v`
Expected: 2 passed

**Step 5: Update insertion.py to return success/failure**

Change `insert_text` to return a bool indicating success:

In `src/mista_wispa/insertion.py`, change the `insert_text` function:

```python
def insert_text(text: str) -> bool:
    if not text:
        return False
    if _insert_via_accessibility(text):
        return True
    _insert_via_clipboard(text)
    return True
```

**Step 6: Update existing insertion tests**

In `tests/test_insertion.py`, update `test_insert_text_empty_string_is_noop`:

```python
def test_insert_text_empty_string_is_noop():
    with patch("mista_wispa.insertion._insert_via_accessibility") as mock_ax:
        with patch("mista_wispa.insertion._insert_via_clipboard") as mock_clip:
            result = insert_text("")
    mock_ax.assert_not_called()
    mock_clip.assert_not_called()
    assert result is False
```

And update `test_insert_text_tries_accessibility_first`:

```python
def test_insert_text_tries_accessibility_first():
    with patch("mista_wispa.insertion._insert_via_accessibility", return_value=True) as mock_ax:
        with patch("mista_wispa.insertion._insert_via_clipboard") as mock_clip:
            result = insert_text("hello")
    mock_ax.assert_called_once_with("hello")
    mock_clip.assert_not_called()
    assert result is True
```

And `test_insert_text_falls_back_to_clipboard`:

```python
def test_insert_text_falls_back_to_clipboard():
    with patch("mista_wispa.insertion._insert_via_accessibility", return_value=False) as mock_ax:
        with patch("mista_wispa.insertion._insert_via_clipboard") as mock_clip:
            result = insert_text("hello")
    mock_ax.assert_called_once_with("hello")
    mock_clip.assert_called_once_with("hello")
    assert result is True
```

**Step 7: Add notifications to _process_audio in app.py**

Update `_process_audio` in `src/mista_wispa/app.py`:

```python
def _process_audio(self, audio: np.ndarray):
    try:
        trimmed = trim_silence(audio)
        if trimmed is None:
            notify("mista-wispa", "No speech detected")
            return

        text = transcribe(trimmed)
        if not text:
            notify("mista-wispa", "Transcription returned empty")
            return

        text = rule_based_cleanup(text)
        if not text:
            return

        if self.settings.llm_cleanup_enabled:
            text = llm_cleanup(text, server_url=self.settings.llm_server_url)

        insert_text(text)
    except Exception as e:
        notify("mista-wispa", f"Error: {e}")
    finally:
        self.title = TITLE_IDLE
```

Add the import at the top of app.py:

```python
from mista_wispa.notify import notify
```

**Step 8: Run all tests**

Run: `uv run pytest -v`
Expected: All pass

**Step 9: Commit**

```bash
git add src/mista_wispa/notify.py tests/test_notify.py src/mista_wispa/app.py src/mista_wispa/insertion.py tests/test_insertion.py
git commit --no-gpg-sign -m "feat: add error notifications via macOS notification center"
```

---

### Task 2: Robust Clipboard Preservation

**Files:**
- Modify: `src/mista_wispa/insertion.py`
- Modify: `tests/test_insertion.py`

Currently `_insert_via_clipboard` only saves/restores plain text (`public.utf8-plain-text`). If the user had rich text, an image, or a file reference on the clipboard, it's lost after dictation. This task preserves all pasteboard types.

**Step 1: Write failing tests**

Add to `tests/test_insertion.py`:

```python
def test_clipboard_preserves_all_types():
    with patch("mista_wispa.insertion._get_pasteboard") as mock_pb_fn:
        mock_pb = MagicMock()
        mock_pb_fn.return_value = mock_pb

        # Simulate clipboard with multiple types
        mock_pb.types.return_value = ["public.utf8-plain-text", "public.rtf"]
        mock_pb.dataForType_.side_effect = lambda t: f"data-for-{t}".encode()

        with patch("mista_wispa.insertion._simulate_paste"):
            with patch("mista_wispa.insertion.time.sleep"):
                _insert_via_clipboard("new text")

        # Should have restored clipboard contents
        assert mock_pb.clearContents.call_count >= 2  # once to set, once to restore


def test_clipboard_handles_empty_clipboard():
    with patch("mista_wispa.insertion._get_pasteboard") as mock_pb_fn:
        mock_pb = MagicMock()
        mock_pb_fn.return_value = mock_pb
        mock_pb.types.return_value = []

        with patch("mista_wispa.insertion._simulate_paste"):
            with patch("mista_wispa.insertion.time.sleep"):
                _insert_via_clipboard("new text")

        # Should set text and not try to restore (nothing to restore)
        mock_pb.setString_forType_.assert_called_with("new text", "public.utf8-plain-text")
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_insertion.py -v`
Expected: Some new tests fail (old clipboard code doesn't call `types()`)

**Step 3: Rewrite _insert_via_clipboard**

Replace `_insert_via_clipboard` in `src/mista_wispa/insertion.py`:

```python
def _save_clipboard():
    pb = _get_pasteboard()
    types = pb.types()
    if not types:
        return None
    saved = []
    for t in types:
        data = pb.dataForType_(t)
        if data:
            saved.append((t, data))
    return saved


def _restore_clipboard(saved):
    if saved is None:
        return
    pb = _get_pasteboard()
    pb.clearContents()
    for ptype, data in saved:
        pb.setData_forType_(data, ptype)


def _insert_via_clipboard(text: str):
    pb = _get_pasteboard()
    saved = _save_clipboard()

    # Set our text
    pb.clearContents()
    pb.setString_forType_(text, "public.utf8-plain-text")

    # Paste
    _simulate_paste()

    # Restore after delay
    time.sleep(0.15)
    _restore_clipboard(saved)
```

Also remove the old `_insert_via_clipboard` implementation.

**Step 4: Update existing test**

Update `test_insert_via_clipboard_sets_and_restores` to match the new API:

```python
def test_insert_via_clipboard_sets_and_restores():
    with patch("mista_wispa.insertion._get_pasteboard") as mock_pb_fn:
        mock_pb = MagicMock()
        mock_pb_fn.return_value = mock_pb
        mock_pb.types.return_value = ["public.utf8-plain-text"]
        mock_pb.dataForType_.return_value = b"old clipboard data"

        with patch("mista_wispa.insertion._simulate_paste"):
            with patch("mista_wispa.insertion.time.sleep"):
                _insert_via_clipboard("new text")

        mock_pb.setString_forType_.assert_any_call("new text", "public.utf8-plain-text")
        assert mock_pb.clearContents.call_count >= 2
```

**Step 5: Run all tests**

Run: `uv run pytest -v`
Expected: All pass

**Step 6: Commit**

```bash
git add src/mista_wispa/insertion.py tests/test_insertion.py
git commit --no-gpg-sign -m "feat: preserve all clipboard types during paste fallback"
```

---

### Task 3: Proper .app Bundle

**Files:**
- Create: `setup_app.py` (py2app setup script)
- Create: `scripts/build_app.sh`
- Modify: `pyproject.toml` (add py2app to dev deps)

This task creates a standalone macOS .app bundle using py2app.

**Step 1: Add py2app to dev dependencies**

In `pyproject.toml`, update `[project.optional-dependencies]`:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-mock",
    "py2app",
]
```

**Step 2: Install updated deps**

Run: `uv pip install -e ".[dev]"`

**Step 3: Create py2app setup script**

```python
# setup_app.py
"""
Build mista-wispa as a macOS .app bundle.

Usage: python setup_app.py py2app
"""
from setuptools import setup

APP = ["src/mista_wispa/app.py"]
DATA_FILES = []
OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "CFBundleName": "mista-wispa",
        "CFBundleDisplayName": "mista-wispa",
        "CFBundleIdentifier": "com.mistawispa.app",
        "CFBundleVersion": "0.1.0",
        "CFBundleShortVersionString": "0.1.0",
        "LSUIElement": True,  # Menu bar app — no dock icon
        "NSMicrophoneUsageDescription": "mista-wispa needs microphone access for voice dictation.",
    },
    "packages": ["mista_wispa", "rumps", "mlx_whisper", "silero_vad", "torch", "numpy", "sounddevice", "openai"],
    "includes": [
        "AppKit",
        "ApplicationServices",
        "CoreFoundation",
        "Quartz",
    ],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
```

**Step 4: Create build script**

```bash
#!/bin/bash
# scripts/build_app.sh
# Build mista-wispa.app bundle
set -e

echo "Building mista-wispa.app..."
python setup_app.py py2app

echo ""
echo "Build complete: dist/mista-wispa.app"
echo ""
echo "To install, copy to /Applications:"
echo "  cp -r dist/mista-wispa.app /Applications/"
echo ""
echo "To run:"
echo "  open /Applications/mista-wispa.app"
```

Make it executable: `chmod +x scripts/build_app.sh`

**Step 5: Test the build**

Run: `uv run python setup_app.py py2app`
Expected: Creates `dist/mista-wispa.app`

If py2app has issues with the src layout, the build script may need adjustment. The key thing is to verify `dist/mista-wispa.app` is created and can launch:

Run: `open dist/mista-wispa.app`
Expected: App launches, MW appears in menu bar

**Step 6: Run all tests (ensure nothing broke)**

Run: `uv run pytest -v`
Expected: All pass

**Step 7: Commit**

```bash
git add setup_app.py scripts/build_app.sh pyproject.toml
git commit --no-gpg-sign -m "feat: add py2app build for macOS .app bundle"
```

---

## Summary

| Task | Feature | Files | Complexity |
|------|---------|-------|------------|
| 1 | Error notifications | notify.py, app.py, insertion.py | Low |
| 2 | Robust clipboard preservation | insertion.py | Medium |
| 3 | .app bundle | setup_app.py, build script | Medium |

**Dependency chain:** Tasks 1 and 2 are independent. Task 3 depends on 1 and 2 being done first (so the bundle includes everything).
