"""Tiny YAML I/O wrapper used by configs and calibration outputs."""

from __future__ import annotations

from datetime import datetime
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


def make_run_dir(name: str, base: str | Path = "runs") -> Path:
    """Create a timestamped run directory ``<base>/<name>_<YYYYMMDD_HHMMSS>/``."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    d = Path(base) / f"{name}_{ts}"
    d.mkdir(parents=True, exist_ok=True)
    return d
