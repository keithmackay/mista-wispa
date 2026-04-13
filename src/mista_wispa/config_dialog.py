# src/mista_wispa/config_dialog.py
import sounddevice as sd
from AppKit import (
    NSAlert,
    NSAlertFirstButtonReturn,
    NSButton,
    NSFont,
    NSOffState,
    NSOnState,
    NSPopUpButton,
    NSSwitchButton,
    NSTextField,
    NSView,
)

from mista_wispa.settings import Settings


def _get_input_devices() -> list[str]:
    """Return names of available audio input devices."""
    devices = sd.query_devices()
    seen = set()
    result = []
    for d in devices:
        if d["max_input_channels"] > 0:
            name = d["name"]
            if name not in seen:
                seen.add(name)
                result.append(name)
    return result


def show_config_dialog(settings: Settings) -> bool:
    """Show the configuration dialog. Returns True if user clicked OK."""
    alert = NSAlert.alloc().init()
    alert.setMessageText_("mista-wispa Settings")
    alert.setInformativeText_("")
    alert.addButtonWithTitle_("OK")
    alert.addButtonWithTitle_("Cancel")

    # Build accessory view
    view = NSView.alloc().initWithFrame_(((0, 0), (300, 80)))

    # Input device label + dropdown
    device_label = NSTextField.labelWithString_("Input Device:")
    device_label.setFont_(NSFont.systemFontOfSize_(13))
    device_label.setFrame_(((0, 52), (100, 20)))
    view.addSubview_(device_label)

    device_popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(((105, 50), (190, 24)), False)
    devices = _get_input_devices()
    device_popup.addItemWithTitle_("System Default")
    for name in devices:
        device_popup.addItemWithTitle_(name)

    # Select current device
    if settings.input_device and settings.input_device in devices:
        device_popup.selectItemWithTitle_(settings.input_device)
    else:
        device_popup.selectItemAtIndex_(0)
    view.addSubview_(device_popup)

    # LLM Cleanup checkbox
    llm_checkbox = NSButton.alloc().initWithFrame_(((0, 10), (300, 24)))
    llm_checkbox.setButtonType_(NSSwitchButton)
    llm_checkbox.setTitle_("Enable LLM Cleanup")
    llm_checkbox.setFont_(NSFont.systemFontOfSize_(13))
    llm_checkbox.setState_(NSOnState if settings.llm_cleanup_enabled else NSOffState)
    view.addSubview_(llm_checkbox)

    alert.setAccessoryView_(view)

    # Show dialog
    result = alert.runModal()
    if result != NSAlertFirstButtonReturn:
        return False

    # Save choices
    selected = device_popup.titleOfSelectedItem()
    settings.input_device = None if selected == "System Default" else selected
    settings.llm_cleanup_enabled = llm_checkbox.state() == NSOnState
    settings.save()
    return True
