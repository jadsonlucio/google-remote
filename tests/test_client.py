import pytest
from androidtvremote2 import CannotConnect, ConnectionClosed, InvalidAuth

from gtv_remote.client import Status, TvClient
from gtv_remote.keys import Key


class FakeRemote:
    def __init__(self, connect_results=()):
        self.connect_results = list(connect_results)
        self.sent = []
        self.texts = []
        self.available_cb = None
        self.invalid_auth_cb = None
        self.closed = False
        self.paired_with = None
        self.pairing_started = False

    async def async_generate_cert_if_missing(self):
        return False

    def add_is_available_updated_callback(self, cb):
        self.available_cb = cb

    async def async_connect(self):
        result = self.connect_results.pop(0) if self.connect_results else None
        if isinstance(result, Exception):
            raise result

    def keep_reconnecting(self, cb):
        self.invalid_auth_cb = cb

    def send_key_command(self, name):
        if self.closed:
            raise ConnectionClosed("closed")
        if name == "BOGUS":
            raise ValueError(name)
        self.sent.append(name)

    def send_text(self, text):
        if self.closed:
            raise ConnectionClosed("closed")
        self.texts.append(text)

    def disconnect(self):
        pass

    async def async_start_pairing(self):
        self.pairing_started = True

    async def async_finish_pairing(self, code):
        if code != "ABC123":
            raise InvalidAuth("bad code")
        self.paired_with = code


async def make(tmp_path, remote, statuses=None):
    async def no_sleep(_):
        return None

    client = TvClient(
        "10.0.0.5",
        tmp_path,
        on_status=(statuses.append if statuses is not None else lambda s: None),
        remote_factory=lambda *a: remote,
        sleep=no_sleep,
    )
    await client.start()
    await client._task
    return client


async def test_connects_and_sends_keys(tmp_path):
    remote = FakeRemote()
    statuses = []
    client = await make(tmp_path, remote, statuses)
    assert client.status is Status.READY
    assert statuses == [Status.CONNECTING, Status.READY]
    assert client.send(Key.HOME) is True
    assert client.send("DPAD_UP") is True
    assert remote.sent == ["HOME", "DPAD_UP"]


async def test_unreachable_tv_retries_with_status_flip(tmp_path):
    remote = FakeRemote([CannotConnect(), CannotConnect(), None])
    statuses = []
    client = await make(tmp_path, remote, statuses)
    assert client.status is Status.READY
    assert Status.DISCONNECTED in statuses


async def test_not_paired_goes_to_needs_pairing(tmp_path):
    remote = FakeRemote([InvalidAuth()])
    client = await make(tmp_path, remote)
    assert client.status is Status.NEEDS_PAIRING
    assert client.send(Key.HOME) is False


async def test_keys_are_dropped_not_queued_while_disconnected(tmp_path):
    remote = FakeRemote()
    client = await make(tmp_path, remote)
    remote.available_cb(False)
    assert client.status is Status.DISCONNECTED
    assert client.send(Key.OK) is False
    remote.available_cb(True)
    assert remote.sent == []  # nothing replayed after reconnect
    assert client.send(Key.OK) is True


async def test_lost_connection_during_send_returns_false(tmp_path):
    remote = FakeRemote()
    client = await make(tmp_path, remote)
    remote.closed = True
    assert client.send(Key.OK) is False
    assert client.send_text("hi") is False


async def test_unknown_raw_key_returns_false(tmp_path):
    client = await make(tmp_path, FakeRemote())
    assert client.send("BOGUS") is False


async def test_invalid_auth_during_reconnect_flips_to_needs_pairing(tmp_path):
    remote = FakeRemote()
    client = await make(tmp_path, remote)
    remote.invalid_auth_cb()
    assert client.status is Status.NEEDS_PAIRING


async def test_send_text_ignores_empty(tmp_path):
    remote = FakeRemote()
    client = await make(tmp_path, remote)
    assert client.send_text("") is False
    assert client.send_text("héllo ✓") is True
    assert remote.texts == ["héllo ✓"]


async def test_pairing_flow_then_connects(tmp_path):
    remote = FakeRemote([InvalidAuth(), None])
    client = await make(tmp_path, remote)
    assert client.status is Status.NEEDS_PAIRING
    await client.start_pairing()
    assert remote.pairing_started
    await client.finish_pairing(" ABC123 ")
    await client._task
    assert remote.paired_with == "ABC123"
    assert client.status is Status.READY


async def test_wrong_pairing_code_raises_and_stays_unpaired(tmp_path):
    remote = FakeRemote([InvalidAuth()])
    client = await make(tmp_path, remote)
    await client.start_pairing()
    with pytest.raises(InvalidAuth):
        await client.finish_pairing("000000")
    assert client.status is Status.NEEDS_PAIRING
