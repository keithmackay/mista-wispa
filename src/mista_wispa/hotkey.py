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
