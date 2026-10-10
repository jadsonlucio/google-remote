from androidtvremote2 import remotemessage_pb2 as pb

from gtv_remote.keys import LAYOUT, Key, key_for_event


def test_every_key_is_a_real_android_keycode():
    names = set(pb.RemoteKeyCode.keys())
    for key in Key:
        assert f"KEYCODE_{key.value}" in names


def test_layout_has_no_overlaps_and_fits_three_columns():
    cells = [(r, c) for r, c, _, _ in LAYOUT]
    assert len(cells) == len(set(cells))
    assert all(0 <= c <= 2 for _, c in cells)


def test_every_key_but_none_is_reachable_from_layout():
    assert {k for *_, k in LAYOUT} == set(Key)


def test_arrow_keys():
    assert key_for_event("", 126) is Key.UP
    assert key_for_event("", 125) is Key.DOWN
    assert key_for_event("", 123) is Key.LEFT
    assert key_for_event("", 124) is Key.RIGHT


def test_enter_escape_backspace_space():
    assert key_for_event("\r", 36) is Key.OK
    assert key_for_event("", 53) is Key.BACK
    assert key_for_event("", 51) is Key.BACK
    assert key_for_event(" ", 49) is Key.PLAY_PAUSE


def test_letters_and_volume():
    assert key_for_event("h", 4) is Key.HOME
    assert key_for_event("H", 4) is Key.HOME
    assert key_for_event("m", 46) is Key.MUTE
    assert key_for_event("+", 24) is Key.VOL_UP
    assert key_for_event("=", 24) is Key.VOL_UP
    assert key_for_event("-", 27) is Key.VOL_DOWN


def test_cmd_p_is_power_and_other_cmd_combos_are_ignored():
    assert key_for_event("p", 35, cmd=True) is Key.POWER
    assert key_for_event("h", 4, cmd=True) is None
    assert key_for_event("p", 35) is None


def test_unbound_key_is_none():
    assert key_for_event("z", 6) is None
