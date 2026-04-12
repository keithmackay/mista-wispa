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

TITLE_IDLE = "MW"
TITLE_RECORDING = "MW●"
TITLE_PROCESSING = "MW…"


class MistaWispaApp(rumps.App):
    def __init__(self):
        super().__init__(TITLE_IDLE, quit_button="Quit")
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
        self.title = TITLE_RECORDING
        self.recorder.start()

    def _on_fn_release(self):
        self.title = TITLE_PROCESSING
        audio = self.recorder.stop()
        if audio is None:
            self.title = TITLE_IDLE
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
            self.title = TITLE_IDLE


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
    app.run()


if __name__ == "__main__":
    main()
