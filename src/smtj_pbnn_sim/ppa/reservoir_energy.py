"""Inference-energy model for the sMTJ reservoir computer and its baselines.

Composed from the same Chapter-2.3-grounded primitives as the PBNN PPA layer
(:mod:`tech_params`), so the RC numbers sit on the same footing as the PBNN
ones in experiment 13.

sMTJ reservoir, per processed input step
----------------------------------------
The reservoir holds ``n_nodes`` logical nodes, each backed by ``ensemble``
physical sMTJs, biased for a step of duration ``dt``:

    E_step =  E_drive + E_dac + E_sense + E_readout
      E_drive   = (V_drive^2 / R_dev) * dt * (n_nodes * ensemble)   # Ohmic bias
      E_dac     = e_dac_step * n_nodes                              # per-node drive set
      E_sense   = e_smtj_read * n_nodes * ensemble                  # one sense / device
      E_readout = e_int8_mac * n_nodes * n_outputs                  # trained linear layer

``substeps`` is a numerical-integration granularity, not extra physics: the
device is biased for the same total ``dt`` regardless, so it does not enter the
energy. The whole inference is ``E_step * n_steps``.

Digital echo-state-network baseline, per step
---------------------------------------------
A dense ESN costs its recurrent matrix-vector product every step:

    E_step = (n_nodes^2 + n_nodes*(n_inputs + n_outputs)) * e_mac

where ``e_mac`` bundles one INT8 multiply-accumulate with one weight read from
the chosen memory (SRAM-CIM or STT-MRAM, via :func:`get_memory`). This is the
``n_nodes^2`` term that the analog sMTJ reservoir replaces with a per-device
linear cost.
"""

from __future__ import annotations

from dataclasses import dataclass

from .tech_params import TechParams, get_memory


@dataclass
class ReservoirHW:
    """Hardware-mapping parameters for the sMTJ reservoir."""
    n_nodes: int
    ensemble: int
    dt: float                      # reservoir step [s]
    n_outputs: int = 1
    n_inputs: int = 1
    V_drive: float = 0.05          # typical bias across the MTJ during a step [V]
    R_dev: float = 4900.0          # MTJ read-path resistance [ohm] (R_P)


def smtj_rc_step_energy(hw: ReservoirHW, tech: TechParams) -> dict[str, float]:
    """Per-step energy breakdown [J] for the sMTJ reservoir."""
    n_dev = hw.n_nodes * hw.ensemble
    return {
        "drive": (hw.V_drive ** 2 / hw.R_dev) * hw.dt * n_dev,
        "DAC": tech.e_dac_step * hw.n_nodes,
        "sense": tech.e_smtj_read * n_dev,
        "readout": tech.e_int8_mac * hw.n_nodes * hw.n_outputs,
    }


def smtj_rc_inference_energy(hw: ReservoirHW, tech: TechParams,
                             n_steps: int) -> float:
    """Total energy [J] to process an ``n_steps``-long sequence."""
    return sum(smtj_rc_step_energy(hw, tech).values()) * n_steps


def digital_esn_step_energy(n_nodes: int, tech: TechParams, *,
                            n_inputs: int = 1, n_outputs: int = 1,
                            memory: str = "sram_cim",
                            digital_mac: bool = True) -> float:
    """Per-step energy [J] of a dense echo-state network.

    ``digital_mac=True`` charges a full INT8 multiply-accumulate plus weight
    read per connection (a conventional digital accelerator). ``False`` drops
    the compute term and keeps only the in-array weight read — an optimistic
    analog compute-in-memory lower bound (ADC overhead not included). The two
    bracket where a real CIM ESN lands.
    """
    mem = get_memory(memory)
    e_mac = mem.e_read_per_bit * mem.bits_per_weight
    if digital_mac:
        e_mac += tech.e_int8_mac
    n_mac = n_nodes * n_nodes + n_nodes * (n_inputs + n_outputs)
    return n_mac * e_mac


def digital_esn_inference_energy(n_nodes: int, tech: TechParams, n_steps: int,
                                 *, n_inputs: int = 1, n_outputs: int = 1,
                                 memory: str = "sram_cim",
                                 digital_mac: bool = True) -> float:
    """Total energy [J] for a digital ESN over ``n_steps``."""
    return digital_esn_step_energy(
        n_nodes, tech, n_inputs=n_inputs, n_outputs=n_outputs,
        memory=memory, digital_mac=digital_mac) * n_steps
