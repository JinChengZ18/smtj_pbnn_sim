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
      E_sense   = e_dev_read * n_nodes * ensemble                   # light per-device analog read
      E_readout = e_int8_mac * n_nodes * n_outputs                  # trained linear layer
                + adc_nodes_frac * n_nodes * (b*e_adc_comp + 2^b*e_adc_capdac0)  # SAR ADC

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
    e_dev_read: float = 5.0e-15    # light per-device analog state read [J] (order-of-magnitude;
                                   # NOT the column StrongARM decision -- that is billed once per
                                   # ADC conversion below via e_adc_comp, column-shared)
    # --- analog-to-digital readout (grounded in the sky130 StrongARM extraction) -------#
    # The node states must be digitised before the trained linear layer; the earlier model
    # omitted this. A successive-approximation ADC costs b comparisons plus a binary-weighted
    # cap-DAC: E_adc(b) = b * e_adc_comp + 2^b * e_adc_capdac0, where the comparator is the
    # extracted StrongARM sense amp. adc_nodes_frac<1 models a column-shared/time-mux ADC.
    adc_bits: int = 8
    adc_nodes_frac: float = 1.0    # fraction of nodes digitised per step (1=per-node, <1=shared)
    e_adc_comp: float = 48e-15     # SAR comparator = extracted sky130 StrongARM SA [J]
    e_adc_capdac0: float = 1.1e-15  # sky130 unit-cap SAR DAC step [J]


def smtj_rc_step_energy(hw: ReservoirHW, tech: TechParams) -> dict[str, float]:
    """Per-step energy breakdown [J] for the sMTJ reservoir.

    ``readout`` bundles the analog->digital conversion (a SAR ADC, comparator grounded in the
    sky130 StrongARM extraction) with the trained linear-layer MAC. Earlier versions billed only
    the MAC and treated the ADC as free; the ADC term is added here so the readout cost is
    physical (set ``hw.adc_nodes_frac`` < 1 for a column-shared/time-mux converter).
    """
    n_dev = hw.n_nodes * hw.ensemble
    e_adc_conv = hw.adc_bits * hw.e_adc_comp + (2 ** hw.adc_bits) * hw.e_adc_capdac0
    e_adc = hw.adc_nodes_frac * hw.n_nodes * e_adc_conv
    return {
        "drive": (hw.V_drive ** 2 / hw.R_dev) * hw.dt * n_dev,
        "DAC": tech.e_dac_step * hw.n_nodes,
        "sense": hw.e_dev_read * n_dev,
        "readout": tech.e_int8_mac * hw.n_nodes * hw.n_outputs + e_adc,
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
