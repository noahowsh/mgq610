"""Minimal JSON cache used by the API clients."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JSONCache:
    """Helper that persists API payloads under `data/raw`."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, relative: Path | str) -> Path:
        path = self.root / Path(relative)
        if path.suffix != ".json":
            path = path.with_suffix(".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def read(self, relative: Path | str) -> Any | None:
        path = self._resolve(relative)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def write(self, relative: Path | str, payload: Any) -> None:
        path = self._resolve(relative)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def exists(self, relative: Path | str) -> bool:
        path = self._resolve(relative)
        return path.exists()
