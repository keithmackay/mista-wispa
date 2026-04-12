# mista-wispa Design

A local-first voice dictation tool for macOS that replaces Wispr Flow. Built in Python on Apple Silicon, using MLX Whisper for transcription and macOS Accessibility APIs for system-wide text insertion.

## Core Principles

- **Fully local** — no cloud services, all processing on-device
- **Push-to-talk** — hold Fn (Globe) key to record, release to insert
- **Fast by default** — rule-based cleanup for low latency, optional local LLM for higher quality
- **System-wide** — works in any app via Accessibility API with clipboard fallback

## Architecture

```
┌─────────────────────────────────────────────┐
│              Menu Bar App (rumps)            │
│  ┌─────────┐  ┌──────────┐  ┌───────────┐  │
│  │ Hotkey   │  │ Audio    │  │ Text      │  │
│  │ Listener │→ │ Capture  │→ │ Insertion │  │
│  │ (Quartz) │  │(snddev) │  │ (AX/Clip) │  │
│  └─────────┘  └────┬─────┘  └─────┬─────┘  │
│                     │              ↑         │
│              ┌──────▼──────────────┤         │
│              │  Voice Pipeline     │         │
│              │  ┌───────┐ ┌─────┐ │         │
│              │  │Silero │→│MLX  │ │         │
│              │  │VAD    │ │Whis.│ │         │
│              │  └───────┘ └──┬──┘ │         │
│              │           ┌───▼──┐ │         │
│              │           │Clean │ │         │
│              │           │up    │ │         │
│              │           └──────┘ │         │
│              └────────────────────┘         │
└─────────────────────────────────────────────┘
         Optional: LM Studio (local LLM)
```

## Components

### Hotkey Listener (`hotkey.py`)

Monitors Fn/Globe key via Quartz event tap (`CGEventTap`). Intercepts `NSSystemDefined` events. Requires Accessibility permissions.

State machine:

```
IDLE ──(Fn press)──→ RECORDING ──(Fn release)──→ PROCESSING ──→ IDLE
```

The event tap runs on the main thread's run loop (required by macOS). Key press starts audio capture, key release triggers the voice pipeline.

### Audio Capture (`audio.py`)

Records from the default input device at 16kHz mono using `sounddevice`. Audio frames are buffered in memory on a background thread while the key is held. No audio hits disk.

### Voice Pipeline (`pipeline.py`)

Processes the audio buffer after Fn release:

1. **VAD trim** — Silero VAD strips leading/trailing silence. If the entire buffer is silence (accidental key press), skip transcription and return to idle.
2. **Whisper transcription** — MLX Whisper (large-v3-turbo, Q4 quantized) processes the trimmed audio. Returns punctuated text.

Performance: VAD ~50ms, Whisper ~200-500ms for typical 5-15 second utterances.

### Text Cleanup (`cleanup.py`)

Two modes:

**Rule-based (always runs):**
- Remove filler words: "um", "uh", "like", "you know", "I mean", "so", "basically"
- Normalize whitespace and fix double punctuation
- Capitalize after sentence-ending punctuation
- Processing time: <10ms

**LLM cleanup (optional, toggled in settings):**
- Sends cleaned text to local LLM via OpenAI-compatible API at `127.0.0.1:1234`
- System prompt: preserve meaning exactly, fix grammar, improve punctuation, format lists if detected, do not add or remove content
- Timeout: 3 seconds — falls back to rule-based output if LLM is slow or unavailable
- Processing time: 500-2000ms depending on model and text length

### Text Insertion (`insertion.py`)

**Primary — Accessibility API (AXUIElement):**
1. Get focused application via `NSWorkspace`
2. Get focused UI element via `AXUIElementCopyAttributeValue` with `kAXFocusedUIElementAttribute`
3. Check element supports `kAXValueAttribute`
4. Get current value and insertion point (`kAXSelectedTextRangeAttribute`)
5. Splice in new text, set updated value
6. Update selection range to place cursor after inserted text

**Fallback — Clipboard paste:**
1. Save current clipboard contents via `NSPasteboard`
2. Set clipboard to transcribed text
3. Simulate Cmd+V via `CGEventCreateKeyboardEvent`
4. After ~100ms delay, restore original clipboard

**Edge cases:**
- No focused text field — play subtle error sound, do nothing
- Password fields — detect `kAXIsSecureTextFieldAttribute`, skip insertion
- Large text fields — insert at cursor position, don't replace

### Menu Bar App (`app.py`)

Built with `rumps`. Shows state via icon changes:
- Idle: mic icon
- Recording: red dot
- Processing: hourglass

Settings accessible from menu bar dropdown: LLM cleanup toggle, LLM server URL.

### Settings (`settings.py`)

User preferences stored as JSON in `~/.config/mista-wispa/settings.json`:
- `llm_cleanup_enabled`: bool (default false)
- `llm_server_url`: string (default `http://127.0.0.1:1234/v1`)

### Permissions

On first launch, prompt user to add the app to System Settings > Privacy & Security > Accessibility. Open the settings pane directly. The user must also disable the system Fn/Globe dictation binding in System Settings > Keyboard.

## Total Latency Budget

- Without LLM: ~300-600ms (key release to text insertion)
- With LLM: ~800-2500ms

## Dependencies

- `rumps` — menu bar app
- `pyobjc-framework-Cocoa` — NSWorkspace, NSPasteboard
- `pyobjc-framework-Quartz` — CGEventTap for global hotkey
- `pyobjc-framework-ApplicationServices` — AXUIElement APIs
- `mlx-whisper` — local Whisper on Apple Silicon
- `silero-vad` / `torch` — voice activity detection
- `sounddevice` — audio capture
- `openai` — optional local LLM client
- `numpy` — audio buffer handling

Python 3.12+, managed with `uv`.

## Reference

Built on the local voice pipeline approach from [kwindla/macos-local-voice-agents](https://github.com/kwindla/macos-local-voice-agents).
