"""Runs the asyncio loop on a background thread so the AppKit main thread stays free."""

import asyncio
import threading
from collections.abc import Awaitable, Callable
from typing import Any


class Runner:
    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run, name="tv-loop", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def call(self, fn: Callable[..., Any], *args: Any) -> None:
        """Run a plain function on the loop thread."""
        self.loop.call_soon_threadsafe(fn, *args)

    def submit(
        self,
        make_coro: Callable[[], Awaitable[Any]],
        on_done: Callable[[Any, BaseException | None], None] | None = None,
    ) -> None:
        """Run a coroutine on the loop. on_done(result, error) fires on the loop thread."""

        async def wrapper() -> None:
            try:
                result = await make_coro()
            except Exception as exc:  # noqa: BLE001 - reported to caller
                if on_done:
                    on_done(None, exc)
            else:
                if on_done:
                    on_done(result, None)

        asyncio.run_coroutine_threadsafe(wrapper(), self.loop)
