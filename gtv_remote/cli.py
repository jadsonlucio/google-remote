"""Terminal pairing: `python -m gtv_remote pair <tv-ip>`.

Keeps the pairing connection open until you type the code (the TV hides the code
as soon as that connection drops).
"""

import asyncio

from androidtvremote2 import CannotConnect, ConnectionClosed, InvalidAuth

from .client import Status, TvClient
from .config import Tv, config_dir, save_tv


async def pair(host: str) -> int:
    directory = config_dir()
    client = TvClient(host, directory)
    await client.ensure_cert()
    try:
        await client.start_pairing()
    except CannotConnect:
        print(f"Couldn't reach {host}:6467. Is the TV on and on the same Wi-Fi?")
        return 1
    print("A code is now showing on the TV. Type it here and press Enter.")
    code = await asyncio.get_running_loop().run_in_executor(None, input, "Code: ")
    try:
        await client.finish_pairing(code)
    except InvalidAuth:
        print("Wrong code.")
        return 1
    except ConnectionClosed:
        print("The TV closed the pairing session (cancelled, or timed out). Try again.")
        return 1
    save_tv(directory, Tv(name=host, host=host))
    await client._task
    status = client.status
    client.stop()
    print("Status:", status.value)
    return 0 if status is Status.READY else 1
