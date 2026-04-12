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
    # Cmd+V down
    cmd_down = Quartz.CGEventCreateKeyboardEvent(src, 0x09, True)  # 0x09 = 'v'
    Quartz.CGEventSetFlags(cmd_down, Quartz.kCGEventFlagMaskCommand)
    Quartz.CGEventPost(Quartz.kCGAnnotatedSessionEventTap, cmd_down)
    # Cmd+V up
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
