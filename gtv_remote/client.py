"""Connection to the TV. The only module that talks to the protocol library."""

import asyncio
from collections.abc import Callable
from enum import Enum
from pathlib import Path

from androidtvremote2 import AndroidTVRemote, CannotConnect, ConnectionClosed, InvalidAuth

from .keys import Key

CLIENT_NAME = "Mac Remote"
MAX_BACKOFF = 30.0


class Status(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    READY = "ready"
    NEEDS_PAIRING = "needs_pairing"


def default_remote_factory(host: str, certfile: str, keyfile: str):
    return AndroidTVRemote(CLIENT_NAME, certfile, keyfile, host)


class TvClient:
    """Must be created and used on a running asyncio loop."""

    def __init__(
        self,
        host: str,
        cert_dir: Path,
        on_status: Callable[[Status], None] = lambda s: None,
        remote_factory=default_remote_factory,
        sleep=asyncio.sleep,
    ) -> None:
        self.host = host
        self.status = Status.DISCONNECTED
        self._certfile = cert_dir / "cert.pem"
        self._keyfile = cert_dir / "key.pem"
        self._on_status = on_status
        self._remote = remote_factory(host, str(self._certfile), str(self._keyfile))
        self._sleep = sleep
        self._task: asyncio.Task | None = None

    def _set(self, status: Status) -> None:
        if status is not self.status:
            self.status = status
            self._on_status(status)

    async def ensure_cert(self) -> None:
        await self._remote.async_generate_cert_if_missing()
        for f in (self._certfile, self._keyfile):
            if f.exists():
                f.chmod(0o600)

    async def start(self) -> None:
        await self.ensure_cert()
        self._remote.add_is_available_updated_callback(self._on_available)
        self._task = asyncio.create_task(self._connect())

    def stop(self) -> None:
        if self._task:
            self._task.cancel()
        self._remote.disconnect()
        self._set(Status.DISCONNECTED)

    def _on_available(self, available: bool) -> None:
        self._set(Status.READY if available else Status.DISCONNECTED)

    def _on_invalid_auth(self) -> None:
        self._set(Status.NEEDS_PAIRING)

    async def _connect(self) -> None:
        delay = 0.5
        while True:
            self._set(Status.CONNECTING)
            try:
                await self._remote.async_connect()
            except InvalidAuth:
                self._set(Status.NEEDS_PAIRING)
                return
            except (CannotConnect, ConnectionClosed):
                self._set(Status.DISCONNECTED)
                await self._sleep(delay)
                delay = min(delay * 2, MAX_BACKOFF)
                continue
            self._remote.keep_reconnecting(self._on_invalid_auth)
            self._set(Status.READY)
            return

    async def start_pairing(self) -> None:
        """Make the TV show a pairing code. Raises CannotConnect."""
        if self._task:
            self._task.cancel()
        await self._remote.async_start_pairing()

    async def finish_pairing(self, code: str) -> None:
        """Raises InvalidAuth (wrong code) or ConnectionClosed (cancelled on TV)."""
        await self._remote.async_finish_pairing(code.strip())
        self._task = asyncio.create_task(self._connect())

    def send(self, key: Key | str) -> bool:
        """Send one key press. Dropped (False) unless ready: never queued."""
        if self.status is not Status.READY:
            return False
        name = key.value if isinstance(key, Key) else key
        try:
            self._remote.send_key_command(name)
        except (ConnectionClosed, ValueError):
            return False
        return True

    def send_text(self, text: str) -> bool:
        if self.status is not Status.READY or not text:
            return False
        try:
            self._remote.send_text(text)
        except ConnectionClosed:
            return False
        return True
