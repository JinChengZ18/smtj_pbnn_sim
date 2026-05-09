"""Latency estimation for sMTJ-PBNN inference."""

from __future__ import annotations

from .tech_params import TechParams


def per_mac_latency(tech: TechParams) -> float:
    """Latency of one MAC unfold step.

    Pipelined view: the DAC settle and the sMTJ write happen in parallel
    with the previous step's readout, so steady-state cycle time is
    max(t_dac_step, t_write, t_smtj_read, t_count_inc).
    """
    return max(tech.t_dac_step, tech.t_write,
               tech.t_smtj_read, tech.t_count_inc)


def layer_inference_latency(rows: int, cols: int, T: int,
                            tech: TechParams) -> float:
    """Latency for one inference call: pipelined T-step sweep.

    The factor of T captures the time-domain unfolding cost; rows are
    activated in parallel within one tile. Cross-tile partial-sum
    aggregation is not modeled here.
    """
    return per_mac_latency(tech) * T
