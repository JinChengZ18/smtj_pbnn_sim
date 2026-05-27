"""Reservoir-computing layer built on the stateful sMTJ telegraph model.

This package repurposes the same calibrated sMTJ device physics used by the
PBNN as the dynamical substrate of a physical reservoir computer: a fixed
random pool of superparamagnetic nodes whose voltage-tunable relaxation time
provides fading memory, read out by a trained linear layer.
"""

from .node import ReservoirConfig, SMTJReservoir
from .readout import RidgeReadout
from .metrics import nrmse, memory_capacity
from . import tasks

__all__ = [
    "ReservoirConfig",
    "SMTJReservoir",
    "RidgeReadout",
    "nrmse",
    "memory_capacity",
    "tasks",
]
