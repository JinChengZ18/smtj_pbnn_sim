"""Process-technology constants for the PPA estimator (SOT-MTJ).

Defaults are set to the Chapter 2.3 measurement point: SOT-MTJ on 300 mm
wafer, beta-W channel of R_SOT = 776 ohm, 0.75 ns write pulse at V_wr ~
0.9 V, giving E_write ~ 0.78 pJ per cell. The read-sense energy is now
grounded in a sky130 StrongARM sense-amplifier extraction (``eda/``,
errata R1): ``e_smtj_read = 48 fJ`` replaces the former 28 nm 5 fJ
placeholder, so the simulator reports a credible read fraction without an
external override. The remaining CMOS peripherals (DAC, counter, areas)
are still 28 nm order-of-magnitude and SHOULD be replaced with sky130 /
NeuroSim floorplan output before reporting their absolute numbers.

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
    e_dac_step: float    = 5.0e-15     # one DAC code-set, per cell (28 nm placeholder; awaits sky130 DAC)
    e_smtj_read: float   = 4.8e-14     # sky130 StrongARM SA decision (eda/ extraction, ~48 fJ central; range 23-74); replaces 28 nm 5 fJ placeholder (errata R1)
    e_count_inc: float   = 0.5e-15     # one counter increment (CMOS digital; 28 nm placeholder)
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
    note: str = ("Chapter-2.3-grounded SOT-MTJ write + sky130-extracted "
                 "StrongARM read (e_smtj_read=48 fJ); DAC/counter/areas "
                 "remain 28 nm order-of-magnitude pending sky130 floorplan.")

    @property
    def e_smtj_write(self) -> float:
        """Single-shot SOT write energy via Ohmic dissipation in the channel."""
        return (self.V_wr_nom ** 2 / self.R_SOT) * self.t_write


def default_28nm() -> TechParams:
    """Return the default Chapter-2.3-grounded tech-parameter set."""
    return TechParams()


# ===========================================================================
# Memory-cell library for the multi-architecture training-energy comparison
# (Experiment 13).
#
# Each entry is a `MemoryParams` dataclass populated with bracketed numbers
# from the CIM-memory literature.  These are 28-nm-class order-of-magnitude
# defaults — sufficient for *relative* architecture comparisons but should
# be replaced with vendor PDK data for absolute energy claims.
#
# Citations (per device technology):
#
#   STT-MRAM      : Apalkov et al. 2013, IEEE TMag 49(7) 4045-4051;
#                   Kent & Worledge 2015, Nat Nanotechnol 10(3) 187-191;
#                   reads 0.05-0.5 pJ/bit, writes 0.5-2 pJ/bit, 5-20 ns.
#   ReRAM (HfO_x) : Wong et al. 2012, Proc IEEE 100(6) 1951-1970;
#                   Sebastian et al. 2020, Nat Rev Mater 5 489-507;
#                   reads 0.05-0.2 pJ/bit, writes 10-100 pJ/cell, 10-100 ns.
#   PCRAM         : Burr et al. 2016, Adv Phys X 1 e1099875;
#                   Sebastian et al. 2020 (above);
#                   reads ~1 pJ/bit, writes 50-200 pJ/cell, 10-100 ns.
#   FeRAM (HZO)   : Mikolajick et al. 2021, Adv Electron Mater 7 2000820;
#                   Khan et al. 2020, Nat Electron 3 588-597;
#                   reads 0.05-0.2 pJ/bit, writes 1-10 pJ/bit, 1-10 ns.
#   SRAM-CIM      : Khwa et al. 2018, ISSCC 2018 496-498;
#                   Yu 2018, Proc IEEE 106(2) 260-285;
#                   reads ~0.05 fJ/bit, writes ~0.5 fJ/bit, 1 ns.
#   sMTJ (PBNN)   : Garello et al. 2019, IEEE Symp VLSI Circuits;
#                   Manchon et al. 2019, Rev Mod Phys 91 035004;
#                   physics-grounded V^2/R * t = 0.78 pJ/sample at the
#                   Chapter 2.3 operating point.
#
# Probabilistic-binary device references (used by `pbnn_stoch_step_energy`
# in src/smtj_pbnn_sim/ppa/training_energy.py):
#
#   stoch-ReRAM PBNN   : Lin et al. 2018, IEEE EDL 39(7);
#                         per-sample stochastic SET/RESET 50 pJ.
#   CMOS p-bit ASIC    : Camsari et al. 2020, Proc IEEE 108(8) "p-Bits for
#                         probabilistic spin logic" (doi:10.1109/JPROC.2020.2966869);
#                         Borders et al. 2019, Nature 573 (sMTJ-augmented integer
#                         factorizer); Sutton et al. 2020, Sci Adv 6, eabb2823
#                         (autonomous probabilistic coprocessing);
#                         5 pJ per p-bit update at 5 ns clock.
#   CMOS-PRNG (LFSR)   : synthesizable lower bound — LFSR step + SRAM read +
#                         comparator ≈ 3 fJ per Bernoulli draw, no NV device
#                         (Hayashida 2020 Nat Electron 3 cites comparable
#                         per-sample LFSR cost).  Useful as an *optimistic*
#                         all-CMOS reference; the Camsari 2020 ASIC entry above
#                         is the *measured-published* point.
# ===========================================================================


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
