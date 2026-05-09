"""Logging utilities for the simulator.

Provides:
    ``log(msg)`` — timestamped stdout logger (used throughout the codebase).
    ``MetricsLogger`` — persistent per-epoch metrics logger (CSV + JSON).
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


def log(msg: str) -> None:
    """Print a timestamped message to stdout with line-buffered flush."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sys.stdout.write(f"[{ts}] {msg}\n")
    sys.stdout.flush()


class MetricsLogger:
    """Persistent metrics logger that writes per-epoch data to CSV and JSON.

    Each call to :meth:`log_epoch` appends a row to ``metrics.csv`` in
    *out_dir* and prints a summary line to stdout via :func:`log`.  When
    training is complete, call :meth:`dump_summary` to write a final
    ``summary.json`` containing aggregate statistics.

    Usage::

        logger = MetricsLogger(out_dir="runs/my_run", n_epochs=20)
        for epoch in range(1, 21):
            tr_loss, tr_acc = train_one_epoch(...)
            te_loss, te_acc = evaluate(...)
            logger.log_epoch(epoch, tr_loss, tr_acc, te_loss, te_acc, elapsed)
        logger.dump_summary(best_acc=0.97, theta_scale=100)
        logger.close()
    """

    CSV_COLUMNS = [
        "epoch", "train_loss", "train_acc", "test_loss", "test_acc",
        "elapsed_s", "timestamp",
    ]

    def __init__(
        self,
        out_dir: str | Path,
        *,
        n_epochs: Optional[int] = None,
        filename: str = "metrics.csv",
    ) -> None:
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.n_epochs = n_epochs
        self._records: list[dict[str, Any]] = []

        self._csv_path = self.out_dir / filename
        self._csv_file = open(self._csv_path, "w", newline="", encoding="utf-8")
        self._csv_writer = csv.writer(self._csv_file)
        self._csv_writer.writerow(self.CSV_COLUMNS)
        self._csv_file.flush()

    # ------------------------------------------------------------------
    # Per-epoch logging
    # ------------------------------------------------------------------

    def log_epoch(
        self,
        epoch: int,
        train_loss: float,
        train_acc: float,
        test_loss: float,
        test_acc: float,
        elapsed: float,
    ) -> None:
        """Record one epoch's metrics to CSV and stdout.

        Parameters
        ----------
        epoch : int
            1-based epoch index.
        train_loss, train_acc : float
            Training loss and accuracy for this epoch.
        test_loss, test_acc : float
            Test (validation) loss and accuracy for this epoch.
        elapsed : float
            Wall-clock seconds for this epoch.
        """
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [epoch, train_loss, train_acc, test_loss, test_acc, elapsed, ts]
        self._csv_writer.writerow(row)
        self._csv_file.flush()

        record = dict(zip(self.CSV_COLUMNS, row))
        self._records.append(record)

        # Formatted stdout message (matches the style used before MetricsLogger)
        if self.n_epochs is not None:
            prefix = f"epoch {epoch:02d}/{self.n_epochs}"
        else:
            prefix = f"epoch {epoch:02d}"
        log(f"{prefix}  "
            f"train loss={train_loss:.4f} acc={train_acc:.4f}   "
            f"test loss={test_loss:.4f} acc={test_acc:.4f}  "
            f"({elapsed:.1f}s)")

    # ------------------------------------------------------------------
    # Summary dump
    # ------------------------------------------------------------------

    def dump_summary(self, **extra: Any) -> None:
        """Write ``summary.json`` to *out_dir*.

        The summary contains aggregate statistics (best metrics, total
        training time) plus any extra keyword arguments (e.g.
        ``best_acc``, ``theta_scale``).
        """
        if not self._records:
            return

        total_time = sum(r["elapsed_s"] for r in self._records)
        best_train_acc = max(r["train_acc"] for r in self._records)
        best_test_acc = max(r["test_acc"] for r in self._records)
        best_test_epoch = max(
            self._records, key=lambda r: r["test_acc"]
        )["epoch"]

        summary: dict[str, Any] = {
            "total_epochs": len(self._records),
            "total_time_s": round(total_time, 2),
            "best_train_acc": round(best_train_acc, 6),
            "best_test_acc": round(best_test_acc, 6),
            "best_test_epoch": best_test_epoch,
            "metrics": self._records,
        }
        summary.update(extra)

        summary_path = self.out_dir / "summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        log(f"Summary saved to {summary_path}")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Flush and close the CSV file handle."""
        if not self._csv_file.closed:
            self._csv_file.close()

    def __enter__(self) -> "MetricsLogger":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()
