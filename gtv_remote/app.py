"""Menu-bar app: wires the runner, TV client and remote window together."""

import rumps
from androidtvremote2 import CannotConnect, ConnectionClosed, InvalidAuth
from PyObjCTools import AppHelper

from . import discovery
from .client import Status, TvClient
from .config import Tv, config_dir, load_tv, save_tv
from .keys import Key
from .remote_window import RemoteWindow
from .runner import Runner

TITLES = {
    Status.READY: "📺",
    Status.CONNECTING: "📺…",
    Status.DISCONNECTED: "📺✕",
    Status.NEEDS_PAIRING: "📺?",
}
LABELS = {
    Status.READY: "Connected",
    Status.CONNECTING: "Connecting…",
    Status.DISCONNECTED: "TV unreachable – retrying",
    Status.NEEDS_PAIRING: "Not paired",
}


class RemoteApp(rumps.App):
    def __init__(self) -> None:
        super().__init__("TV Remote", title="📺✕", quit_button=None)
        self.dir = config_dir()
        self.runner = Runner()
        self.client: TvClient | None = None
        self._pairing = False
        self._open_when_ready = False
        self.tv: Tv | None = load_tv(self.dir)
        self.window = RemoteWindow(self.on_key, self.on_text)
        self.status_item = rumps.MenuItem("No TV selected")
        self.menu = [
            rumps.MenuItem("Show Remote", callback=lambda _: self.window.show()),
            self.status_item,
            None,
            rumps.MenuItem("Find TV…", callback=lambda _: self.find_tv()),
            rumps.MenuItem("Enter TV IP…", callback=lambda _: self.enter_ip()),
            rumps.MenuItem("Re-pair", callback=lambda _: self.pair()),
            None,
            rumps.MenuItem("Quit", callback=lambda _: self.quit()),
        ]
        self.window.set_status("No TV selected")

    # -- startup ---------------------------------------------------------
    @rumps.timer(0.2)
    def _first_run(self, timer) -> None:
        timer.stop()
        if self.tv:
            self.connect(self.tv)
        else:
            self.window.show()
            self.find_tv()

    # -- status ----------------------------------------------------------
    def _status_changed(self, status: Status) -> None:
        # Called on the loop thread; hop to the main thread for UI work.
        AppHelper.callAfter(self._show_status, status)

    def _show_status(self, status: Status) -> None:
        self.title = TITLES[status]
        name = self.tv.name if self.tv else "TV"
        text = f"{name}: {LABELS[status]}"
        self.status_item.title = text
        self.window.set_status(text)
        if status is Status.NEEDS_PAIRING:
            self.pair()
        elif status is Status.READY and self._open_when_ready:
            self._open_when_ready = False
            self.window.show()

    # -- connection ------------------------------------------------------
    def connect(self, tv: Tv) -> None:
        self.tv = tv
        save_tv(self.dir, tv)
        old = self.client

        self._pairing = False

        def start() -> None:
            if old:
                old.stop()
            client = TvClient(tv.host, self.dir, on_status=self._status_changed)
            self.client = client
            self.runner.submit(client.start, self._report_error)

        self.runner.call(start)

    def _report_error(self, _result, error) -> None:
        if error is not None:
            AppHelper.callAfter(rumps.alert, "TV Remote", f"Error: {error}")

    def find_tv(self) -> None:
        self.status_item.title = "Searching for TVs…"
        self.window.set_status("Searching for TVs…")

        def done(tvs, error) -> None:
            AppHelper.callAfter(self._found, tvs or [])

        self.runner.submit(discovery.discover, done)

    def _found(self, tvs: list[Tv]) -> None:
        if not tvs:
            rumps.alert("TV Remote", "No Google TV found. Make sure the TV is on and on the same Wi-Fi, or enter its IP address.")
            return self.enter_ip()
        if len(tvs) == 1:
            return self.connect(tvs[0])
        listing = "\n".join(f"{i}) {tv.name} ({tv.host})" for i, tv in enumerate(tvs, 1))
        reply = rumps.Window(f"Several TVs found:\n{listing}", "Choose TV", default_text="1", ok="Use", cancel="Cancel").run()
        if reply.clicked and reply.text.strip().isdigit() and 1 <= int(reply.text) <= len(tvs):
            self.connect(tvs[int(reply.text) - 1])

    def enter_ip(self) -> None:
        reply = rumps.Window("TV IP address (TV Settings → Network shows it):", "Enter TV IP", default_text=self.tv.host if self.tv else "", ok="Connect", cancel="Cancel").run()
        host = reply.text.strip()
        if reply.clicked and host:
            self.connect(Tv(name=host, host=host))

    # -- pairing ---------------------------------------------------------
    def pair(self) -> None:
        client = self.client
        if client is None:
            return self.find_tv()
        if self._pairing:  # a second start would make the TV drop the code it is showing
            return
        self._pairing = True

        def started(_result, error) -> None:
            if error is not None:
                self._pairing = False
                msg = "Couldn't reach the TV to pair." if isinstance(error, CannotConnect) else f"Pairing failed: {error}"
                return AppHelper.callAfter(rumps.alert, "TV Remote", msg)
            AppHelper.callAfter(self._ask_code, client)

        self.runner.submit(client.start_pairing, started)

    def _ask_code(self, client: TvClient) -> None:
        reply = rumps.Window("Enter the 6-character code shown on the TV:", "Pair with TV", ok="Pair", cancel="Cancel").run()
        if not reply.clicked:
            self._pairing = False
            return
        code = reply.text

        def finished(_result, error) -> None:
            self._pairing = False
            if error is None:
                self._open_when_ready = True
            if isinstance(error, InvalidAuth):
                AppHelper.callAfter(rumps.alert, "TV Remote", "Wrong code. Choose Re-pair to try again.")
            elif isinstance(error, ConnectionClosed):
                AppHelper.callAfter(rumps.alert, "TV Remote", "Pairing was cancelled on the TV. Choose Re-pair to try again.")
            elif error is not None:
                AppHelper.callAfter(rumps.alert, "TV Remote", f"Pairing failed: {error}")

        self.runner.submit(lambda: client.finish_pairing(code), finished)

    # -- sending ---------------------------------------------------------
    def _ready(self) -> bool:
        if self.client and self.client.status is Status.READY:
            return True
        self.window.set_status("Not connected – key dropped")
        return False

    def on_key(self, key: Key) -> bool:
        if not self._ready():
            return False
        client = self.client
        self.runner.call(client.send, key)
        return True

    def on_text(self, text: str) -> bool:
        if not self._ready():
            return False
        client = self.client
        self.runner.call(client.send_text, text)
        return True

    def quit(self) -> None:
        if self.client:
            self.runner.call(self.client.stop)
        rumps.quit_application()


def main() -> None:
    RemoteApp().run()
