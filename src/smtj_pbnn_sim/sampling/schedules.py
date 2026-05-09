"""Schedules for the per-layer sample count T and the inverse temperature beta."""

from __future__ import annotations

from typing import Sequence


def constant_T(num_layers: int, T: int) -> list[int]:
    """Same T at every layer."""
    return [int(T)] * int(num_layers)


def layer_depth_T(num_layers: int, T_first: int, T_last: int) -> list[int]:
    """Linear interpolation of T from ``T_first`` (input layer) to ``T_last``.

    Useful for studying whether deeper layers benefit from more samples to
    counter the variance accumulated through earlier stochastic layers.
    """
    if num_layers <= 1:
        return [int(T_first)]
    return [int(round(T_first + (T_last - T_first) * k / (num_layers - 1)))
            for k in range(num_layers)]


def beta_schedule(epoch: int, total_epochs: int,
                  beta_init: float = 1.0, beta_final: float = 1.0) -> float:
    """Inverse-temperature schedule across training epochs.

    Linearly anneal from ``beta_init`` to ``beta_final``. Defaults to
    constant beta = 1, which is the standard PBNN training regime.
    """
    if total_epochs <= 1:
        return float(beta_final)
    frac = epoch / (total_epochs - 1)
    return float(beta_init + (beta_final - beta_init) * frac)
