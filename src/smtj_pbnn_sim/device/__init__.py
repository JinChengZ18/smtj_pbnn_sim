"""Device-level behavioral models for stochastic SOT-MTJ junctions.

The compact-model entry points are :mod:`arrhenius`. Resistance description
includes both the read path (R_P, R_AP, TMR) and the SOT write channel
(R_SOT) since this is a three-terminal device. Variation sampling targets
the dimensionless thermal stability factor ``Delta`` (per Chapter 2.3,
which decomposes process variation into a Brinkman-derived CV(Delta) of
about 7.7% as a Gaussian on Delta).
"""

from .arrhenius import (
    psw_neel_brown,
    psw_sigmoid,
    vth_neel_brown,
    sigmoid_params_from_neel_brown,
)
from .tmr import (
    MTJResistance,
    conductance_from_state,
    sot_write_energy,
)
from .variation import (
    VariationConfig,
    VariationSampler,
    VariationFields,
)
from .calibration import (
    fit_sigmoid_params,
    fit_per_device_direction,
    fit_neel_brown_from_vth_vs_tw,
    SigmoidParams,
    NBParams,
)

__all__ = [
    "psw_neel_brown",
    "psw_sigmoid",
    "vth_neel_brown",
    "sigmoid_params_from_neel_brown",
    "MTJResistance",
    "conductance_from_state",
    "sot_write_energy",
    "VariationConfig",
    "VariationSampler",
    "VariationFields",
    "fit_sigmoid_params",
    "fit_per_device_direction",
    "fit_neel_brown_from_vth_vs_tw",
    "SigmoidParams",
    "NBParams",
]
