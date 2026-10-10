"""Where the app keeps its certificate, key and saved TV."""

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Tv:
    name: str
    host: str


def config_dir() -> Path:
    base = os.environ.get("GTV_REMOTE_HOME")
    path = Path(base) if base else Path.home() / ".config" / "gtv-remote"
    path.mkdir(parents=True, exist_ok=True)
    path.chmod(0o700)
    return path


def load_tv(directory: Path) -> Tv | None:
    try:
        data = json.loads((directory / "tv.json").read_text())
        return Tv(name=data["name"], host=data["host"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def save_tv(directory: Path, tv: Tv) -> None:
    path = directory / "tv.json"
    path.write_text(json.dumps(asdict(tv)))
    path.chmod(0o600)
