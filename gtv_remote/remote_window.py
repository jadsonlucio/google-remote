"""Floating remote control window (AppKit via PyObjC)."""

from collections.abc import Callable

import objc
from AppKit import (
    NSApp,
    NSBackingStoreBuffered,
    NSBezelStyleRounded,
    NSButton,
    NSEventModifierFlagCommand,
    NSFloatingWindowLevel,
    NSMakeRect,
    NSPanel,
    NSText,
    NSTextField,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskTitled,
)
from Foundation import NSObject

from .keys import LAYOUT, Key, key_for_event

CELL_W, CELL_H, GAP, MARGIN = 64, 40, 8, 16
COLS = 3
ROWS = 1 + max(row for row, *_ in LAYOUT)
WIDTH = MARGIN * 2 + COLS * CELL_W + (COLS - 1) * GAP
STATUS_H, TEXT_H = 18, 24
HEIGHT = (
    MARGIN * 2 + STATUS_H + GAP + ROWS * CELL_H + (ROWS - 1) * GAP + GAP * 2 + TEXT_H
)


class _KeyPanel(NSPanel):
    def canBecomeKeyWindow(self):
        return True

    def keyDown_(self, event):
        handler = getattr(self, "key_handler", None)
        editing = isinstance(self.firstResponder(), NSText)
        if handler and not editing and handler(event):
            return
        objc.super(_KeyPanel, self).keyDown_(event)


class _Controller(NSObject):
    def initWithOwner_(self, owner):
        self = objc.super(_Controller, self).init()
        self.owner = owner
        return self

    @objc.IBAction
    def pressed_(self, sender):
        self.owner._press(int(sender.tag()))

    @objc.IBAction
    def sendText_(self, sender):
        self.owner._send_text()


class RemoteWindow:
    """on_key(Key) and on_text(str) must return False when the TV isn't ready."""

    def __init__(self, on_key: Callable[[Key], bool], on_text: Callable[[str], bool]) -> None:
        self._on_key = on_key
        self._on_text = on_text
        self._controller = _Controller.alloc().initWithOwner_(self)
        self._buttons = []

        style = NSWindowStyleMaskTitled | NSWindowStyleMaskClosable
        self._panel = _KeyPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, WIDTH, HEIGHT), style, NSBackingStoreBuffered, False
        )
        self._panel.setTitle_("TV Remote")
        self._panel.setLevel_(NSFloatingWindowLevel)
        self._panel.setReleasedWhenClosed_(False)
        self._panel.setHidesOnDeactivate_(False)
        self._panel.key_handler = self._handle_event
        self._panel.center()
        content = self._panel.contentView()

        self._status = NSTextField.labelWithString_("")
        self._status.setFrame_(NSMakeRect(MARGIN, HEIGHT - MARGIN - STATUS_H, WIDTH - 2 * MARGIN, STATUS_H))
        content.addSubview_(self._status)

        grid_top = HEIGHT - MARGIN - STATUS_H - GAP
        for index, (row, col, label, _key) in enumerate(LAYOUT):
            x = MARGIN + col * (CELL_W + GAP)
            y = grid_top - (row + 1) * CELL_H - row * GAP
            button = NSButton.alloc().initWithFrame_(NSMakeRect(x, y, CELL_W, CELL_H))
            button.setTitle_(label)
            button.setBezelStyle_(NSBezelStyleRounded)
            button.setTag_(index)
            button.setTarget_(self._controller)
            button.setAction_("pressed:")
            button.setRefusesFirstResponder_(True)  # keep arrows/space for the window
            content.addSubview_(button)
            self._buttons.append(button)

        send_w = 56
        self._field = NSTextField.alloc().initWithFrame_(
            NSMakeRect(MARGIN, MARGIN, WIDTH - 2 * MARGIN - send_w - GAP, TEXT_H)
        )
        self._field.setPlaceholderString_("Type to TV…")
        self._field.setTarget_(self._controller)
        self._field.setAction_("sendText:")  # Enter in the field sends
        content.addSubview_(self._field)
        send = NSButton.alloc().initWithFrame_(
            NSMakeRect(WIDTH - MARGIN - send_w, MARGIN - 2, send_w, TEXT_H + 4)
        )
        send.setTitle_("Send")
        send.setBezelStyle_(NSBezelStyleRounded)
        send.setTarget_(self._controller)
        send.setAction_("sendText:")
        send.setRefusesFirstResponder_(True)
        content.addSubview_(send)

    def show(self) -> None:
        NSApp.activateIgnoringOtherApps_(True)
        self._panel.makeKeyAndOrderFront_(None)
        self._panel.makeFirstResponder_(self._panel)

    def set_status(self, text: str) -> None:
        self._status.setStringValue_(text)

    def _handle_event(self, event) -> bool:
        cmd = bool(event.modifierFlags() & NSEventModifierFlagCommand)
        key = key_for_event(event.charactersIgnoringModifiers() or "", int(event.keyCode()), cmd)
        if key is None:
            return False
        self._on_key(key)
        return True

    def _press(self, index: int) -> None:
        self._on_key(LAYOUT[index][3])

    def _send_text(self) -> None:
        text = self._field.stringValue()
        if text and self._on_text(text):
            self._field.setStringValue_("")
        self._panel.makeFirstResponder_(self._panel)
