"""PBNNLinear: stochastic binary fully-connected layer with three forward modes.

The layer holds a real-valued latent parameter ``theta`` of shape
``(out_features, in_features)``. The same ``theta`` is interpreted in three
ways depending on ``mode``:

* ``ForwardMode.SOFTWARE``      -- p_ij = sigmoid(theta_ij). No device
  modeling at all. Used to reproduce published PBNN baselines and as a
  sanity check for the device-aware path.

* ``ForwardMode.HARDWARE_AWARE`` -- per-cell write voltages
  V_ij = V_th_ij + V_T_ij * theta_ij are mapped through the device
  Sigmoid p_ij = sigmoid((V_ij - V_th_ij) / V_T_ij) -- which simplifies to
  sigmoid(theta_ij) when V_T_ij is constant, but couples theta to per-cell
  variation when it is not. The forward then uses CLT-Gaussian sampling of
  the preactivation. This is the default training mode.

* ``ForwardMode.FULL_STACK``    -- explicit T-step Bernoulli sampling
  through the device Sigmoid, returning the empirical mean of the
  preactivation. Used at evaluation time and to feed PPA estimators.

Per-cell variation is sampled at first-call time. Two variation modes are
supported:

* ``mode = "delta"``       -- sample Delta_i ~ N(Delta_nom, (CV * Delta_nom)^2)
                              and propagate through the NB->Sigmoid bridge.
                              Matches the Chapter 2.3 PDK-baseline physics.
* ``mode = "sigmoid_direct"`` -- sample V_th_i and V_T_i directly with
                              relative Gaussian noise. Useful when only
                              the operating-point distribution is known.

In all three modes, the post-activation binarization uses the STE sign.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import torch
from torch import Tensor

from .clt import bernoulli_pm1_clt_forward
from .ste import sign_ste
from ..device.arrhenius import psw_sigmoid
from ..device.variation import VariationConfig, VariationSampler, VariationFields
from ..sampling.bernoulli_smtj import _bernoulli_pm1


class ForwardMode(str, Enum):
    SOFTWARE       = "software"
    HARDWARE_AWARE = "hardware_aware"
    FULL_STACK     = "full_stack"


@dataclass
class DeviceLayerParams:
    """Nominal device parameters threaded from calibration into the layer.

    Defaults follow the Chapter 2.3 primary reference: Device A, P->AP,
    t_w = 0.75 ns. ``Delta_nom`` and ``V_c0_nom`` are required only when the
    variation sampler is configured with ``mode = "delta"``.
    """
    V_th_nom: float = 0.894
    V_T_nom: float = 1.0 / 44.6      # = 0.02242 V
    R_P_nom: float = 4.9e3
    TMR_nom: float = 1.0
    R_SOT_nom: float = 776.0
    Delta_nom: float = 4.91
    V_c0_nom: float = 0.857
    eta_c: float = 5.34
    tau_0: float = 1.0e-9
    t_p: float = 0.75e-9


class PBNNLinear(torch.nn.Module):
    """Stochastic binary fully-connected layer with CLT and explicit-sample paths."""

    def __init__(
        self,
        in_features: int,
        out_features: int,
        *,
        bias: bool = True,
        device_params: Optional[DeviceLayerParams] = None,
        variation_cfg: Optional[VariationConfig] = None,
        T_full_stack: int = 16,
        binarize_output: bool = True,
    ):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.binarize_output = binarize_output
        self.T_full_stack = int(T_full_stack)

        self.theta = torch.nn.Parameter(torch.empty(out_features, in_features))
        if bias:
            self.bias = torch.nn.Parameter(torch.zeros(out_features))
        else:
            self.register_parameter("bias", None)

        # Initialize theta around 0 so that p_ij ~ 1/2 at the start, the
        # maximum-entropy initialization for stochastic binary weights.
        with torch.no_grad():
            self.theta.normal_(mean=0.0, std=1.0 / max(1, in_features) ** 0.5)

        self.device_params = device_params or DeviceLayerParams()
        self.variation_cfg = variation_cfg

        # Variation field: drawn lazily on first call once device placement
        # is known. Buffers are registered to be moved by .to(device).
        self.register_buffer("V_th_field", torch.empty(0), persistent=True)
        self.register_buffer("V_T_field",  torch.empty(0), persistent=True)
        self._variation_drawn = False

    # ------------------------------------------------------------------#
    # Variation field bookkeeping                                        #
    # ------------------------------------------------------------------#

    def _load_from_state_dict(self, state_dict, prefix, local_metadata,
                              strict, missing_keys, unexpected_keys,
                              error_msgs):
        # Variation buffers are lazily initialized with shape (0,). When
        # loading from a checkpoint that has the populated buffers, we must
        # resize them before the base class tries to copy_ the values.
        for buf_name in ("V_th_field", "V_T_field"):
            key = prefix + buf_name
            if key in state_dict and state_dict[key].shape != getattr(self, buf_name).shape:
                # Keep the buffer on the current device (may already be on
                # CUDA from a prior .to() call); the base class copy_()
                # handles cross-device transfer from the state dict.
                cur_dev = getattr(self, buf_name).device
                setattr(self, buf_name,
                        torch.empty(state_dict[key].shape,
                                    device=cur_dev,
                                    dtype=state_dict[key].dtype))
        super()._load_from_state_dict(
            state_dict, prefix, local_metadata, strict,
            missing_keys, unexpected_keys, error_msgs)
        # Mark variation as drawn if the buffers were loaded from checkpoint.
        if self.V_th_field.numel() > 0:
            self._variation_drawn = True

    def _ensure_variation(self, device: torch.device) -> None:
        if self._variation_drawn:
            return
        shape = (self.out_features, self.in_features)
        dp = self.device_params
        if self.variation_cfg is None:
            V_th = torch.full(shape, dp.V_th_nom, device=device)
            V_T  = torch.full(shape, dp.V_T_nom,  device=device)
        else:
            sampler = VariationSampler(self.variation_cfg)
            fields: VariationFields = sampler.sample(
                shape,
                V_th_nom=dp.V_th_nom,
                V_T_nom=dp.V_T_nom,
                R_P_nom=dp.R_P_nom,
                TMR_nom=dp.TMR_nom,
                Delta_nom=dp.Delta_nom,
                V_c0_nom=dp.V_c0_nom,
                tau_0=dp.tau_0,
                t_p=dp.t_p,
                eta_c=dp.eta_c,
                device=device,
            )
            V_th = fields.V_th
            V_T  = fields.V_T
        self.V_th_field = V_th
        self.V_T_field  = V_T
        self._variation_drawn = True

    # ------------------------------------------------------------------#
    # p_ij computation per forward mode                                  #
    # ------------------------------------------------------------------#

    def _p_software(self) -> Tensor:
        """Binary p for SOFTWARE mode (train and eval)."""
        return self._harden(torch.sigmoid(self.theta))

    def _p_hardware(self) -> Tensor:
        """Binary p for HARDWARE_AWARE mode (train and eval).

        theta is a dimensionless logit; the layer maps it to a write
        voltage about each cell's local center, then the device Sigmoid
        gives the per-cell switching probability. The result is snapped
        to {0, 1} via the STE trick so that the forward always uses
        binary weights w = sign(theta) ∈ {-1, +1}.
        """
        V_wr = self.V_th_field + self.V_T_field * self.theta
        p_soft = psw_sigmoid(V_wr, self.V_th_field, self.V_T_field)
        return self._harden(p_soft)

    def _p_soft_for_sampling(self) -> Tensor:
        """True (soft) switching probability for FULL_STACK Bernoulli sampling.

        After training with hard binary weights, the learned theta will have
        large magnitudes, so ``sigmoid(theta)`` is near 0 or 1, making the
        Bernoulli samples near-deterministic. This is the intended behavior:
        FULL_STACK converges quickly when the weights are well-trained.
        """
        V_wr = self.V_th_field + self.V_T_field * self.theta
        return psw_sigmoid(V_wr, self.V_th_field, self.V_T_field)

    def _harden(self, p_soft: Tensor) -> Tensor:
        """Snap p to {0, 1} with STE-style gradient.

        Forward:  ``p_hard ∈ {0, 1}``  →  ``w = 2p_hard - 1 = sign(θ)``
        Backward: gradient flows through ``p_soft = sigmoid(θ)`` giving
        ``dp/dθ = p_soft · (1 − p_soft)`` — smooth, never-clipped.

        This is applied in SOFTWARE and HARDWARE_AWARE modes (both train
        and eval) so that the forward always uses binary weights and the
        BN running statistics are consistent across modes.
        """
        p_hard = (self.theta >= 0).float()
        return p_hard.detach() + p_soft - p_soft.detach()

    # ------------------------------------------------------------------#
    # Forward                                                            #
    # ------------------------------------------------------------------#

    def forward(
        self,
        x: Tensor,
        *,
        mode: ForwardMode = ForwardMode.HARDWARE_AWARE,
        T: Optional[int] = None,
        sample: bool = True,
    ) -> Tensor:
        self._ensure_variation(x.device)

        if mode is ForwardMode.SOFTWARE:
            p = self._p_software()
            z = bernoulli_pm1_clt_forward(p, x, sample=sample)
        elif mode is ForwardMode.HARDWARE_AWARE:
            p = self._p_hardware()
            z = bernoulli_pm1_clt_forward(p, x, sample=sample)
        elif mode is ForwardMode.FULL_STACK:
            T_eff = self.T_full_stack if T is None else int(T)
            z = self._forward_full_stack(x, T_eff)
        else:
            raise ValueError(f"Unknown ForwardMode: {mode!r}")

        if self.bias is not None:
            z = z + self.bias

        if self.binarize_output:
            return sign_ste(z)
        return z

    # ------------------------------------------------------------------#

    def _forward_full_stack(self, x: Tensor, T: int) -> Tensor:
        if T <= 0:
            raise ValueError(f"T must be positive, got {T}")
        with torch.no_grad():
            p = self._p_soft_for_sampling()  # soft p for Bernoulli draws
            acc: Optional[Tensor] = None
            for _ in range(T):
                w = _bernoulli_pm1(p)
                z_t = torch.nn.functional.linear(x, w)
                acc = z_t if acc is None else (acc + z_t)
            return acc / T
