"""Minimal stdout logger; experiment scripts can replace with tensorboard, etc."""

from __future__ import annotations

import sys
from datetime import datetime


def log(msg: str) -> None:
    """Print a timestamped message to stdout with line-buffered flush."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sys.stdout.write(f"[{ts}] {msg}\n")
    sys.stdout.flush()
