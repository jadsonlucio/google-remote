"""Find Google TVs on the LAN via mDNS."""

import asyncio

from zeroconf import IPVersion, ServiceStateChange
from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo, AsyncZeroconf

from .config import Tv

SERVICE_TYPE = "_androidtvremote2._tcp.local."


async def discover(timeout: float = 4.0) -> list[Tv]:
    found: dict[str, Tv] = {}
    azc = AsyncZeroconf()

    async def resolve(name: str) -> None:
        info = AsyncServiceInfo(SERVICE_TYPE, name)
        if await info.async_request(azc.zeroconf, 3000):
            addresses = info.parsed_addresses(IPVersion.V4Only)
            if addresses:
                found[name] = Tv(name=name.removesuffix("." + SERVICE_TYPE), host=addresses[0])

    tasks: set[asyncio.Future] = set()

    def on_change(zeroconf, service_type, name, state_change) -> None:
        if state_change in (ServiceStateChange.Added, ServiceStateChange.Updated):
            tasks.add(asyncio.ensure_future(resolve(name)))

    browser = AsyncServiceBrowser(azc.zeroconf, SERVICE_TYPE, handlers=[on_change])
    try:
        await asyncio.sleep(timeout)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        await browser.async_cancel()
        await azc.async_close()
    return sorted(found.values(), key=lambda tv: tv.name)
