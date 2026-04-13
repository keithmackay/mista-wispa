# src/mista_wispa/app.py
import os
import threading

import numpy as np
import rumps
from AppKit import NSSound

from mista_wispa.audio import AudioRecorder
from mista_wispa.cleanup import rule_based_cleanup, llm_cleanup
from mista_wispa.config_dialog import show_config_dialog
from mista_wispa.hotkey import FnKeyMonitor
from mista_wispa.insertion import insert_text
from mista_wispa.notify import notify
from mista_wispa.pipeline import trim_silence, transcribe, warmup
from mista_wispa.settings import Settings

_RESOURCES = os.path.join(os.path.dirname(__file__), "..", "..", "resources")
MENUBAR_ICON = os.path.join(_RESOURCES, "menubar-icon.png")


def _play_sound(name: str):
    sound = NSSound.soundNamed_(name)
    if sound:
        sound.play()


class MistaWispaApp(rumps.App):
    def __init__(self):
        super().__init__("mista-wispa", icon=MENUBAR_ICON, template=True, quit_button="Quit")
        self.settings = Settings()
        self.recorder = AudioRecorder(device=self.settings.input_device)
        self.hotkey = FnKeyMonitor(on_press=self._on_fn_press, on_release=self._on_fn_release)

        self.menu = [
            rumps.MenuItem("Settings…", callback=self._open_settings),
        ]

    def _open_settings(self, sender):
        if show_config_dialog(self.settings):
            # Apply updated device selection
            self.recorder = AudioRecorder(device=self.settings.input_device)

    def _on_fn_press(self):
        self.title = "●"
        _play_sound("Tink")
        self.recorder.start()

    def _on_fn_release(self):
        self.title = "…"
        _play_sound("Pop")
        audio = self.recorder.stop()
        if audio is None:
            self.title = None
            return
        # Process in background thread to keep UI responsive
        threading.Thread(target=self._process_audio, args=(audio,), daemon=True).start()

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
            self.title = None


def _check_accessibility():
    from ApplicationServices import AXIsProcessTrustedWithOptions
    from CoreFoundation import kCFBooleanTrue

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


def main():
    # Register as a menu bar (accessory) app so macOS shows our status item
    from AppKit import NSApplication
    NSApplication.sharedApplication().setActivationPolicy_(1)  # NSApplicationActivationPolicyAccessory

    app = MistaWispaApp()
    _check_accessibility()
    app.hotkey.start()

    # Pre-load models in background so first dictation is fast
    threading.Thread(target=warmup, daemon=True).start()

    app.run()


if __name__ == "__main__":
    main()
