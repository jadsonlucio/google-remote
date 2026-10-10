from gtv_remote.config import Tv, load_tv, save_tv


def test_roundtrip(tmp_path):
    save_tv(tmp_path, Tv("Living room", "192.168.1.20"))
    assert load_tv(tmp_path) == Tv("Living room", "192.168.1.20")


def test_missing_or_corrupt_file_gives_none(tmp_path):
    assert load_tv(tmp_path) is None
    (tmp_path / "tv.json").write_text("{not json")
    assert load_tv(tmp_path) is None
    (tmp_path / "tv.json").write_text('{"name": "x"}')
    assert load_tv(tmp_path) is None
