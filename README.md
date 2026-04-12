# mista-wispa

A local-first voice dictation tool for macOS. Hold a key, speak, release — cleaned-up text appears at your cursor. All processing happens on-device using Apple Silicon. No cloud services, no subscriptions, no data leaves your machine.

Built as a local alternative to [Wispr Flow](https://wisprflow.ai), inspired by the voice pipeline architecture in [kwindla/macos-local-voice-agents](https://github.com/kwindla/macos-local-voice-agents).

## How It Works

1. **Hold Fn (Globe) key** — audio recording starts, menu bar icon shows a red dot
2. **Speak naturally** — audio is captured at 16kHz mono, buffered in memory
3. **Release Fn** — the pipeline runs:
   - **Silero VAD** trims leading/trailing silence (skips accidental key presses)
   - **MLX Whisper** (large-v3-turbo) transcribes speech to text locally
   - **Rule-based cleanup** removes filler words ("um", "uh"), fixes punctuation, capitalizes sentences
   - **Optional LLM cleanup** sends text through a local model for grammar and formatting polish
4. **Text is inserted** at your cursor via macOS Accessibility API, or clipboard paste as fallback

Typical latency: **300-600ms** without LLM, **800-2500ms** with LLM.

## Requirements

- macOS on Apple Silicon (M1/M2/M3/M4)
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- [LM Studio](https://lmstudio.ai) (optional, for LLM cleanup)

## Installation

```bash
git clone https://github.com/your-username/mista-wispa.git
cd mista-wispa
uv venv
uv pip install -e ".[dev]"
```

The first run will download model weights (~1-2 GB for Whisper, ~500 MB for Silero VAD). Subsequent launches are fast.

## Usage

```bash
uv run mista-wispa
```

On first launch:
1. Grant **Accessibility** permission when prompted (System Settings > Privacy & Security > Accessibility)
2. Disable the system dictation shortcut (System Settings > Keyboard > Dictation > Shortcut > Off)
3. Grant **Microphone** permission if prompted

Then open any text field, hold Fn, speak, and release.

### Menu Bar

The app lives in your menu bar with a custom icon. Click it to access:

- **LLM Cleanup** — toggle on/off. When enabled, transcriptions are polished by a local LLM before insertion.
- **Quit** — stop the app.

### Menu Bar States

| State | Indicator |
|-------|-----------|
| Idle | MW icon only |
| Recording | MW icon + red dot (●) |
| Processing | MW icon + ellipsis (…) |

### Audio Feedback

A subtle "Tink" sound plays when recording starts and a "Pop" sound when recording stops, so you don't need to watch the menu bar.

### Error Notifications

If something goes wrong (no speech detected, transcription fails), a macOS notification appears instead of silent failure.

### LLM Cleanup

For higher-quality text formatting, enable LLM cleanup in the menu bar and run a local model in LM Studio:

1. Install [LM Studio](https://lmstudio.ai)
2. Download a small, fast model (recommended: **Gemma 3N E4B**, **Phi-4 Mini**, or **Qwen 3 4B**)
3. Start the local server (default: `http://127.0.0.1:1234/v1`)
4. Toggle **LLM Cleanup** on in the mista-wispa menu bar

The LLM has a 3-second timeout — if it's slow or unavailable, the app falls back to rule-based cleanup automatically.

### Settings

Stored at `~/.config/mista-wispa/settings.json`:

```json
{
  "llm_cleanup_enabled": false,
  "llm_server_url": "http://127.0.0.1:1234/v1"
}
```

## Building as a macOS App

To create a standalone `.app` bundle:

```bash
uv pip install py2app
uv run python setup_app.py py2app
```

Then copy to Applications:

```bash
cp -r dist/mista-wispa.app /Applications/
open /Applications/mista-wispa.app
```

The `.app` bundle includes `LSUIElement=True` (no dock icon) and declares microphone usage.

## Architecture

```
src/mista_wispa/
├── app.py          # Menu bar app, wires everything together
├── hotkey.py       # Fn key monitoring via Quartz event tap
├── audio.py        # Microphone capture with sounddevice
├── pipeline.py     # Silero VAD + MLX Whisper transcription
├── cleanup.py      # Rule-based + optional LLM text cleanup
├── insertion.py    # Accessibility API + clipboard paste fallback
├── notify.py       # macOS notification center alerts
└── settings.py     # JSON config persistence
```

### Text Insertion Strategy

1. **Primary: Accessibility API** — uses `AXUIElement` to directly set the value of the focused text field and position the cursor. Works in most native macOS apps.
2. **Fallback: Clipboard paste** — saves all clipboard contents (rich text, images, files), sets our text, simulates Cmd+V, waits briefly, then restores the original clipboard.

Password fields are detected and skipped for safety.

### Text Cleanup Pipeline

**Rule-based (always runs, <10ms):**
- Removes non-word fillers: "um", "uh", "uhm", "umm", "ah", "er"
- Removes contextual fillers at sentence start: "like", "so", "well", "right", "actually"
- Removes filler phrases at sentence start: "you know", "I mean", "kind of", "sort of"
- Preserves these words in mid-sentence ("I like pizza" stays intact)
- Fixes double punctuation, preserves ellipses
- Normalizes whitespace, capitalizes after sentence endings

**LLM cleanup (optional, 500-2000ms):**
- Sends text to a local model with instructions to fix grammar, improve punctuation, and format lists
- Preserves meaning — does not add or remove content
- Falls back to rule-based output on timeout or error

## Development

### Running Tests

```bash
uv run pytest -v
```

54 tests covering all modules with mocked system APIs.

### Regenerating Icons

If you modify the SVG source files (`mista-wispa-appicon.svg`, `mista-wispa-menubar.svg`):

```bash
uv run python scripts/generate_icons.py
```

This generates menu bar PNGs (1x and 2x), app icon PNGs at all sizes, and the `.icns` bundle.

## Potential Features

### Usability
- **Configurable hotkey** — let users choose a different activation key (right Cmd, double-tap Fn, custom shortcut) instead of hardcoded Fn
- **Startup on login** — add a macOS Launch Agent so the app runs automatically after login
- **Streaming transcription** — begin Whisper processing while still recording (for longer dictations) rather than waiting for key release

### Intelligence
- **Context-aware formatting** — detect the active application (Slack, Mail, VS Code, etc.) and adjust the LLM cleanup prompt to match the expected tone and format
- **Multi-language support** — pass a language hint to Whisper or let the user select their language in settings
- **Custom vocabulary** — let users add domain-specific words or proper nouns that Whisper tends to get wrong
- **Smart punctuation** — detect questions, exclamations, and lists from speech patterns and intonation

### Power Features
- **Command mode** — detect a trigger phrase (e.g., "command:") and execute text editing operations via the LLM: "make this more formal", "turn this into a bulleted list", "fix the grammar in the selected text"
- **Voice-driven editing** — highlight text with the mouse, hold Fn, speak an editing instruction, and have the LLM transform the selection
- **MCP integration** — connect to MCP servers for tool calling, allowing voice-driven actions beyond text insertion
- **Clipboard dictation** — a mode that copies transcribed text to the clipboard instead of inserting it, for use with apps that don't support accessibility insertion

### Polish
- **Animated menu bar icon** — show a waveform or pulsing animation during recording instead of a static dot
- **Usage statistics** — track dictation count, average latency, and words per minute in the menu bar dropdown
- **Transcription history** — keep a log of recent dictations accessible from the menu bar, with the ability to re-insert or copy
- **Configurable sounds** — let users choose or disable the audio feedback sounds
- **Auto-update** — check for new versions and prompt the user to update

## References

- [kwindla/macos-local-voice-agents](https://github.com/kwindla/macos-local-voice-agents) — the project that inspired mista-wispa's local voice pipeline architecture. Demonstrates fully local voice-to-voice AI on Apple Silicon using [Pipecat](https://github.com/pipecat-ai/pipecat), MLX Whisper, Silero VAD, and Kokoro TTS. mista-wispa adapts the STT and VAD patterns from this project into a push-to-talk dictation tool, replacing the conversational agent loop with text insertion.

## License

MIT
