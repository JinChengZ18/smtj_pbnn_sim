"""Device-to-device (D2D) variation for sMTJ arrays.

Following Chapter 2.3, the dominant process variation channel is the
dimensionless thermal stability factor ``Delta``, with CV(Delta) ~= 7.7%
on a 300 mm wafer (Brinkman-decomposed: 66% from MTJ-pillar diameter
geometry, 27% from interface anisotropy H_k, 7% from saturation
magnetization). The variation is therefore sampled as

    Delta_i ~ N( mu_Delta, (CV * mu_Delta)^2 ),

and propagated to per-cell ``(V_th, V_T)`` via the NB->Sigmoid bridge.
The runtime overhead of the propagation is amortised: the variation field
is drawn once at array instantiation and held fixed.

Implementation notes
--------------------

The variation field is drawn in NumPy, then converted to torch tensors
only when a torch ``device`` is supplied. This lets standalone callers
(e.g., calibration scripts, unit tests, the Monte Carlo wafer-average
plot of Chapter 2.3) instantiate variation fields without torch present.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Literal, Any
import math
import numpy as np


@dataclass
class VariationConfig:
    """Configuration for D2D variation sampling.

    Attributes:
        mode: ``"delta"`` (default) samples Delta_i and propagates via NB
            bridge; ``"sigmoid_direct"`` samples V_th and V_T directly.
        cv_delta: CV(Delta) for the ``delta`` mode (default 0.077).
        sigma_V_th_rel: Relative std-dev of V_th for ``sigmoid_direct`` mode.
        sigma_V_T_rel:  Relative std-dev of V_T for ``sigmoid_direct`` mode.
        sigma_RP_rel:   Relative std-dev of parallel-state resistance.
        sigma_TMR_rel:  Relative std-dev of TMR ratio.
        sigma_sense_offset_V: Std-dev [V] of an additive per-cell decision-threshold
            shift that models the readout sense-amplifier input-referred offset
            (errata R2): an SA offset acts as a per-column V_th shift -- exactly the
            error class Exp.08 finds dominant. Fed by the EDA hero block's extracted
            offset distribution. Default 0.0 = no sense offset (legacy behaviour).
        seed: RNG seed for the variation draw. None = nondeterministic.
    """
    mode: Literal["delta", "sigmoid_direct"] = "delta"
    cv_delta: float = 0.077
    sigma_V_th_rel: float = 0.05
    sigma_V_T_rel: float = 0.10
    sigma_RP_rel: float = 0.05
    sigma_TMR_rel: float = 0.10
    sigma_sense_offset_V: float = 0.0
    seed: Optional[int] = None


@dataclass
class VariationFields:
    """Per-cell static offsets, all of identical shape.

    Tensors are torch tensors when ``device != None`` was passed to
    :meth:`VariationSampler.sample`, otherwise NumPy arrays. The two cases
    can be distinguished by ``isinstance(field.V_th, np.ndarray)``.
    """
    V_th: Any
    V_T: Any
    R_P: Any
    TMR: Any


def _to_torch(arr: np.ndarray, device: Any):
    """Convert a NumPy array to a torch tensor on the given device."""
    import torch
    return torch.from_numpy(arr).to(device).detach()


class VariationSampler:
    """Draws and stores per-cell variation fields for an array of given shape."""

    def __init__(self, cfg: VariationConfig):
        self.cfg = cfg

    def sample(
        self,
        shape: tuple[int, ...],
        *,
        # Operating-point Sigmoid parameters (always required).
        V_th_nom: float,
        V_T_nom: float,
        R_P_nom: float,
        TMR_nom: float,
        # NB parameters; required when mode == "delta".
        Delta_nom: Optional[float] = None,
        V_c0_nom: Optional[float] = None,
        tau_0: float = 1e-9,
        t_p: float = 0.75e-9,
        eta_c: float = 1.0,
        device: Optional[Any] = None,
    ) -> VariationFields:
        """Draw a fresh per-cell variation field of the given shape.

        Returns a :class:`VariationFields` whose tensors are NumPy arrays
        when ``device`` is None, or torch tensors on ``device`` otherwise.
        """
        rng = np.random.default_rng(self.cfg.seed)

        def _draw_rel(nominal: float, sigma_rel: float) -> np.ndarray:
            return (nominal * (1.0 + sigma_rel * rng.standard_normal(shape))
                    ).astype(np.float32)

        R_P = np.maximum(_draw_rel(R_P_nom, self.cfg.sigma_RP_rel), 1.0)
        TMR = np.maximum(_draw_rel(TMR_nom, self.cfg.sigma_TMR_rel), 0.05)

        if self.cfg.mode == "delta":
            if Delta_nom is None or V_c0_nom is None:
                raise ValueError(
                    "VariationConfig(mode='delta') requires Delta_nom and V_c0_nom."
                )
            Delta_field = np.maximum(
                _draw_rel(Delta_nom, self.cfg.cv_delta), 0.5
            )
            log_term = math.log(t_p / tau_0 / math.log(2.0))
            V_th = (V_c0_nom * (1.0 - log_term / Delta_field)).astype(np.float32)
            # Analytic NB slope at V = V_th: beta_NB = 2 ln(2) (Delta/V_c0).
            beta_NB = 2.0 * math.log(2.0) * (Delta_field / V_c0_nom)
            beta_s = eta_c * beta_NB
            V_T = np.maximum(1.0 / beta_s, 1e-4).astype(np.float32)
        elif self.cfg.mode == "sigmoid_direct":
            V_th = _draw_rel(V_th_nom, self.cfg.sigma_V_th_rel)
            V_T = np.maximum(_draw_rel(V_T_nom, self.cfg.sigma_V_T_rel), 1e-4)
        else:
            raise ValueError(f"Unknown variation mode: {self.cfg.mode!r}")

        # Readout sense-amp input-referred offset (errata R2): an additive per-cell
        # decision-threshold shift on top of V_th. Fed by the EDA hero block's
        # extracted SA-offset distribution (eda/interface/hero_closed_loop.py).
        if self.cfg.sigma_sense_offset_V > 0.0:
            V_th = (V_th + self.cfg.sigma_sense_offset_V
                    * rng.standard_normal(shape)).astype(np.float32)

        if device is not None:
            return VariationFields(
                V_th=_to_torch(V_th, device),
                V_T=_to_torch(V_T,  device),
                R_P=_to_torch(R_P,  device),
                TMR=_to_torch(TMR,  device),
            )
        return VariationFields(V_th=V_th, V_T=V_T, R_P=R_P, TMR=TMR)
