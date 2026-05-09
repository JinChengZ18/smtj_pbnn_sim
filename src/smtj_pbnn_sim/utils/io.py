"""Tiny YAML I/O wrapper used by configs and calibration outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml


def load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r") as f:
        return yaml.safe_load(f) or {}


def dump_yaml(obj: Any, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as f:
        yaml.safe_dump(obj, f, sort_keys=False)
