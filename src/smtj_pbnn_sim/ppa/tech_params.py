"""Process-technology constants for the PPA estimator (SOT-MTJ).

Defaults are set to the Chapter 2.3 measurement point: SOT-MTJ on 300 mm
wafer, beta-W channel of R_SOT = 776 ohm, 0.75 ns write pulse at V_wr ~
0.9 V, giving E_write ~ 0.78 pJ per cell. The read-sense energy is now
grounded in a sky130 StrongARM sense-amplifier extraction (``eda/``,
errata R1): ``e_smtj_read = 48 fJ`` replaces the former 28 nm 5 fJ
placeholder, so the simulator reports a credible read fraction without an
external override. The DAC code-set and counter-increment energies are now
grounded in sky130 as well (``eda/testbenches/dac_counter_energy.py``: ngspice
analog core + a sky130 stdcell-capacitance estimate for the digital decode /
flip-flops, since the sky130_fd_sc_hd Liberty is not installed). Only the AREAS
remain 28 nm order-of-magnitude and SHOULD be replaced with sky130 layout
extraction before reporting their absolute numbers (see
``.agents/eda/PPA_grounding_plan.md``).

NOTE (see ``.agents/errata.md``, item E1): NeuroSim does NOT model the sMTJ
stochastic SOT write -- that energy is physically grounded here via
``V_wr**2 / R_SOT * t_write``. The NeuroSim/Spectre replacement above
applies only to the CMOS-peripheral constants (DAC, read sense, counter,
areas). The transistor-level extraction effort lives under ``eda/``.

Per-operation primitives are listed; layer-level energy is composed in
:mod:`energy` and :mod:`latency`.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TechParams:
    """Process-technology parameter set.

    Energies in joules, times in seconds, areas in square micrometers.
    """
    # ---- SOT-MTJ device-level (computed from V_wr^2 / R_SOT * t_p) -------#
    V_wr_nom: float      = 0.90        # nominal write voltage [V]
    R_SOT: float         = 776.0       # SOT channel resistance [ohm]
    t_write: float       = 0.75e-9     # write pulse width [s]

    # ---- CMOS peripheral energies (28 nm order of magnitude) -------------#
    e_dac_step: float    = 3.4e-14     # sky130 R-string write-DAC code-set: ngspice analog core ~0.6 fJ + decode ~33 fJ (eda/testbenches/dac_counter_energy.py; ~2x uncertainty pending stdcell extraction)
    e_smtj_read: float   = 4.8e-14     # sky130 StrongARM SA decision, ~48 fJ (eda/ extraction; errata R1)
    e_count_inc: float   = 1.9e-14     # sky130 popcount-counter increment: ~2 DFF toggles x ~10 fJ at 1.8 V (eda/testbenches/dac_counter_energy.py; ~2x uncertainty pending Liberty)
    e_sram_byte: float   = 5.0e-12     # one byte read from local SRAM
    e_dram_byte: float   = 6.4e-10     # one byte read from off-chip DRAM (Horowitz)

    # ---- Digital MAC and MRAM (for FP-NN baseline comparison, exp 13) ----#
    # All values are 28-nm provisional defaults that bracket the published
    # STT-MRAM CIM literature (NeuroSim V1.5, ISSCC 2020-2024 prototypes).
    # An 8-bit MAC in a digital CIM tile is 1-2 pJ when sense-amp + control
    # overhead is included; STT-MRAM cell read is 50-500 fJ per bit; write
    # is 0.5-2 pJ per bit.
    e_int8_mac: float    = 1.0e-12     # 1 pJ per 8-bit MAC (compute + ctrl)
    e_mram_read: float   = 0.1e-12     # 0.1 pJ per bit read from STT-MRAM
    e_mram_write: float  = 1.0e-12     # 1 pJ per bit write to STT-MRAM
    t_mram_write: float  = 5.0e-9      # MRAM cell write latency
    mram_bits_per_weight: int = 8      # INT8 quantization for FP weights

    # ---- Latencies (s) ---------------------------------------------------#
    t_dac_step: float    = 1.0e-9
    t_smtj_read: float   = 2.0e-9
    t_count_inc: float   = 0.5e-9

    # ---- Areas (um^2) ----------------------------------------------------#
    a_smtj_cell: float   = 0.05        # 1T-1MTJ unit cell (read path)
    a_sot_track: float   = 0.04        # extra area for the SOT channel
    a_dac: float         = 200.0
    a_counter: float     = 50.0

    # ---- Identifying meta -----------------------------------------------#
    name: str = "sky130-read-sot-default"
    note: str = ("Chapter-2.3-grounded SOT-MTJ write + sky130-grounded read "
                 "(48 fJ), DAC code-set (~34 fJ) and counter (~19 fJ); only "
                 "areas remain 28 nm order-of-magnitude pending sky130 layout.")

    @property
    def e_smtj_write(self) -> float:
        """Single-shot SOT write energy via Ohmic dissipation in the channel."""
        return (self.V_wr_nom ** 2 / self.R_SOT) * self.t_write


def default_28nm() -> TechParams:
    """Return the default Chapter-2.3-grounded tech-parameter set."""
    return TechParams()


# Memory-cell library for the Experiment-13 architecture-energy comparison.
# 28-nm-class order-of-magnitude defaults that bracket published CIM ranges
# (relative comparison only, not absolute). Per-entry one-line refs live in the
# `citation=` fields below; representative ranges: STT-MRAM read 0.05-0.5 /
# write 0.5-2 pJ; ReRAM 0.05-0.2 / 10-100 pJ; PCRAM ~1 / 50-200 pJ; FeRAM
# 0.05-0.2 / 1-10 pJ; SRAM-CIM ~0.05 / ~0.5 fJ; sMTJ physics-grounded
# V^2/R*t = 0.78 pJ/sample. Probabilistic-device refs (used by
# training_energy.pbnn_stoch_step_energy): stoch-ReRAM Lin 2018 IEEE EDL 39(7)
# ~50 pJ; CMOS p-bit Camsari 2020 Proc IEEE 108(8) / Borders 2019 Nature 573 /
# Sutton 2020 Sci Adv 6 ~5 pJ/update; CMOS-PRNG/LFSR optimistic ~3 fJ/draw.


@dataclass
class MemoryParams:
    """Per-device-technology memory-cell parameters for Experiment 13.

    All energies in joules, times in seconds.  ``bits_per_weight`` is the
    number of physical cells used to represent one logical INT-N weight in
    the digital architectures; for sMTJ it is interpreted as the number of
    stochastic samples T.
    """
    name: str
    e_read_per_bit: float       # one cell read [J/bit]
    e_write_per_cell: float     # one cell write [J/cell]
    t_write: float              # cell write latency [s]
    bits_per_weight: int        # cells per logical weight
    volatile: bool = False      # True for SRAM-CIM, False for non-volatile
    citation: str = ""          # one-line literature pointer


# Registry of CIM memory cells (extend here when adding new technologies)
MEMORIES: dict[str, MemoryParams] = {
    "stt_mram": MemoryParams(
        name="STT-MRAM",
        e_read_per_bit=0.1e-12,
        e_write_per_cell=1.0e-12,
        t_write=5.0e-9,
        bits_per_weight=8,
        volatile=False,
        citation=("Apalkov 2013 IEEE TMag 49(7); "
                  "Kent & Worledge 2015 Nat Nanotechnol 10"),
    ),
    "reram": MemoryParams(
        name="ReRAM (HfO_x)",
        e_read_per_bit=0.1e-12,
        e_write_per_cell=50e-12,
        t_write=100e-9,
        bits_per_weight=8,
        volatile=False,
        citation=("Wong 2012 Proc IEEE 100(6); "
                  "Sebastian 2020 Nat Rev Mater 5"),
    ),
    "pcram": MemoryParams(
        name="PCRAM (Ge2Sb2Te5)",
        e_read_per_bit=1e-12,
        e_write_per_cell=100e-12,
        t_write=50e-9,
        bits_per_weight=8,
        volatile=False,
        citation=("Burr 2016 Adv Phys X 1; Sebastian 2020 Nat Rev Mater 5"),
    ),
    "feram": MemoryParams(
        name="FeRAM (HZO)",
        e_read_per_bit=0.1e-12,
        e_write_per_cell=5e-12,
        t_write=10e-9,
        bits_per_weight=8,
        volatile=False,
        citation=("Mikolajick 2021 Adv Electron Mater 7; "
                  "Khan 2020 Nat Electron 3"),
    ),
    "sram_cim": MemoryParams(
        name="SRAM-CIM",
        e_read_per_bit=0.05e-15,
        e_write_per_cell=0.5e-15,
        t_write=1e-9,
        bits_per_weight=8,
        volatile=True,
        citation=("Khwa 2018 ISSCC; Yu 2018 Proc IEEE 106(2)"),
    ),
    "smtj": MemoryParams(
        name="sMTJ (SOT-MTJ stochastic, PBNN)",
        e_read_per_bit=4.8e-14,           # sky130 StrongARM SA (eda/ extraction; errata R1)
        e_write_per_cell=0.78e-12,        # physics-grounded V^2/R * t
        t_write=0.75e-9,
        bits_per_weight=4,                 # T (default sweet-spot from exp 06)
        volatile=False,
        citation=("Garello 2019 VLSI; Manchon 2019 Rev Mod Phys 91; "
                  "read sky130 StrongARM SA (eda/)"),
    ),
}


def get_memory(name: str) -> MemoryParams:
    """Look up a `MemoryParams` by registry key (e.g., 'stt_mram')."""
    if name not in MEMORIES:
        raise KeyError(
            f"unknown memory {name!r}; "
            f"available: {sorted(MEMORIES.keys())}")
    return MEMORIES[name]
