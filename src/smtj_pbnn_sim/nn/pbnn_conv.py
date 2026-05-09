"""PBNNConv2d: stochastic binary 2-D convolution via unfold-as-linear.

The convolution is implemented as ``Unfold -> CLT linear -> Fold-equivalent
reshape``. This reuses the CLT forward path of :class:`PBNNLinear` exactly,
ensuring that any improvement to the linear layer carries over to the
convolutional case without code duplication.
"""

from __future__ import annotations

from typing import Optional, Tuple, Union
import torch
from torch import Tensor

from .clt import bernoulli_pm1_clt_forward
from .ste import sign_ste
from .pbnn_linear import DeviceLayerParams, ForwardMode
from ..device.arrhenius import psw_sigmoid
from ..device.variation import VariationConfig, VariationSampler, VariationFields
from ..sampling.bernoulli_smtj import _bernoulli_pm1


def _pair(x: Union[int, Tuple[int, int]]) -> Tuple[int, int]:
    return (x, x) if isinstance(x, int) else x


class PBNNConv2d(torch.nn.Module):
    """Stochastic binary 2-D convolution layer."""

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: Union[int, Tuple[int, int]],
        *,
        stride: Union[int, Tuple[int, int]] = 1,
        padding: Union[int, Tuple[int, int]] = 0,
        bias: bool = True,
        device_params: Optional[DeviceLayerParams] = None,
        variation_cfg: Optional[VariationConfig] = None,
        T_full_stack: int = 16,
        binarize_output: bool = True,
    ):
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.kernel_size = _pair(kernel_size)
        self.stride = _pair(stride)
        self.padding = _pair(padding)
        self.binarize_output = binarize_output
        self.T_full_stack = int(T_full_stack)

        kH, kW = self.kernel_size
        in_features = in_channels * kH * kW
        out_features = out_channels

        self.theta = torch.nn.Parameter(torch.empty(out_features, in_features))
        if bias:
            self.bias = torch.nn.Parameter(torch.zeros(out_features))
        else:
            self.register_parameter("bias", None)

        with torch.no_grad():
            self.theta.normal_(mean=0.0, std=1.0 / max(1, in_features) ** 0.5)

        self.device_params = device_params or DeviceLayerParams()
        self.variation_cfg = variation_cfg

        self.register_buffer("V_th_field", torch.empty(0), persistent=True)
        self.register_buffer("V_T_field",  torch.empty(0), persistent=True)
        self._variation_drawn = False

    # ------------------------------------------------------------------#

    def _ensure_variation(self, device: torch.device) -> None:
        if self._variation_drawn:
            return
        shape = self.theta.shape
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

    def _p_software(self) -> Tensor:
        return torch.sigmoid(self.theta)

    def _p_hardware(self) -> Tensor:
        V_wr = self.V_th_field + self.V_T_field * self.theta
        return psw_sigmoid(V_wr, self.V_th_field, self.V_T_field)

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

        B, C, H, W = x.shape
        kH, kW = self.kernel_size
        sH, sW = self.stride
        pH, pW = self.padding
        H_out = (H + 2 * pH - kH) // sH + 1
        W_out = (W + 2 * pW - kW) // sW + 1

        cols = torch.nn.functional.unfold(
            x, kernel_size=self.kernel_size, padding=self.padding,
            stride=self.stride,
        )
        L = cols.shape[-1]
        flat = cols.transpose(1, 2).reshape(B * L, -1)

        if mode is ForwardMode.SOFTWARE:
            p = self._p_software()
            z = bernoulli_pm1_clt_forward(p, flat, sample=sample)
        elif mode is ForwardMode.HARDWARE_AWARE:
            p = self._p_hardware()
            z = bernoulli_pm1_clt_forward(p, flat, sample=sample)
        elif mode is ForwardMode.FULL_STACK:
            T_eff = self.T_full_stack if T is None else int(T)
            with torch.no_grad():
                p = self._p_hardware()
                acc: Optional[Tensor] = None
                for _ in range(T_eff):
                    w = _bernoulli_pm1(p)
                    z_t = torch.nn.functional.linear(flat, w)
                    acc = z_t if acc is None else (acc + z_t)
                z = acc / T_eff
        else:
            raise ValueError(f"Unknown ForwardMode: {mode!r}")

        z = z.reshape(B, L, self.out_channels).transpose(1, 2)
        z = z.reshape(B, self.out_channels, H_out, W_out)

        if self.bias is not None:
            z = z + self.bias.view(1, -1, 1, 1)

        if self.binarize_output:
            return sign_ste(z)
        return z
