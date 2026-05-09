"""Baseline comparison hooks.

This module is a stub. The intended baselines are:

* Digital BNN (Courbariaux et al.) -- can be re-trained inside this same
  package by replacing PBNNLinear with a deterministic sign-of-real-weights
  layer. A reference implementation is left as a TODO.
* STT-BNN (Pham et al., 2022) -- numbers are extracted from the published
  paper; place them in ``configs/baseline/stt_bnn.yaml`` and read here.
* SOT-BNN (Fan & Angizi, 2017) -- same convention as above.
* aihwkit baseline -- a thin adapter that runs aihwkit's analog Linear and
  records its accuracy + PPA estimate. Requires ``aihwkit`` installed; the
  import is deferred.

The actual comparison plots are produced in ``experiments/08_ppa_compare_baseline.py``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BaselineResult:
    """Single baseline entry for the comparison table."""
    name: str
    dataset: str
    network: str
    accuracy: float
    energy_per_inference_J: float
    latency_per_inference_s: float
    note: str = ""


def load_published_baselines(path: str) -> list[BaselineResult]:
    """Load a YAML list of published baselines.

    The expected schema mirrors :class:`BaselineResult`.
    """
    from ..utils.io import load_yaml
    raw = load_yaml(path)
    items = raw.get("baselines", [])
    return [BaselineResult(**item) for item in items]
