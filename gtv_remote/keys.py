"""Remote keys, the on-screen layout and the keyboard map. Pure data, no I/O."""

from enum import Enum


class Key(Enum):
    """Values are Android key names (without the KEYCODE_ prefix)."""

    UP = "DPAD_UP"
    DOWN = "DPAD_DOWN"
    LEFT = "DPAD_LEFT"
    RIGHT = "DPAD_RIGHT"
    OK = "DPAD_CENTER"
    BACK = "BACK"
    HOME = "HOME"
    POWER = "POWER"
    SETTINGS = "SETTINGS"
    INPUT = "TV_INPUT"
    VOL_UP = "VOLUME_UP"
    VOL_DOWN = "VOLUME_DOWN"
    MUTE = "VOLUME_MUTE"
    PLAY_PAUSE = "MEDIA_PLAY_PAUSE"
    # Brightness keys are experimental: many TVs/projectors ignore them.
    BRIGHT_UP = "BRIGHTNESS_UP"
    BRIGHT_DOWN = "BRIGHTNESS_DOWN"


# (row, col, label, key) on a 3-column grid, row 0 at the top.
LAYOUT = [
    (0, 0, "⏻", Key.POWER),
    (0, 1, "⚙", Key.SETTINGS),
    (0, 2, "Input", Key.INPUT),
    (1, 1, "▲", Key.UP),
    (2, 0, "◀", Key.LEFT),
    (2, 1, "OK", Key.OK),
    (2, 2, "▶", Key.RIGHT),
    (3, 1, "▼", Key.DOWN),
    (4, 0, "Back", Key.BACK),
    (4, 1, "Home", Key.HOME),
    (4, 2, "⏯", Key.PLAY_PAUSE),
    (5, 0, "Vol −", Key.VOL_DOWN),
    (5, 1, "Mute", Key.MUTE),
    (5, 2, "Vol +", Key.VOL_UP),
    (6, 0, "☀ −", Key.BRIGHT_DOWN),
    (6, 2, "☀ +", Key.BRIGHT_UP),
]

# macOS virtual key codes (layout independent).
_KEYCODES = {
    123: Key.LEFT,
    124: Key.RIGHT,
    125: Key.DOWN,
    126: Key.UP,
    36: Key.OK,  # return
    76: Key.OK,  # keypad enter
    53: Key.BACK,  # escape
    51: Key.BACK,  # delete / backspace
    49: Key.PLAY_PAUSE,  # space
}

_CHARS = {
    "h": Key.HOME,
    "m": Key.MUTE,
    "+": Key.VOL_UP,
    "=": Key.VOL_UP,
    "-": Key.VOL_DOWN,
    "s": Key.SETTINGS,
}


def key_for_event(chars: str, keycode: int, cmd: bool = False) -> Key | None:
    """Map a keyboard event to a remote key, or None if it isn't bound."""
    if cmd:
        return Key.POWER if chars.lower() == "p" else None
    if keycode in _KEYCODES:
        return _KEYCODES[keycode]
    return _CHARS.get(chars.lower())
