"""Process-technology constants for the PPA estimator (SOT-MTJ).

Defaults are set to the Chapter 2.3 measurement point: SOT-MTJ on 300 mm
wafer, beta-W channel of R_SOT = 776 ohm, 0.75 ns write pulse at V_wr ~
0.9 V, giving E_write ~ 0.78 pJ per cell. CMOS peripherals (DAC, counter,
read sense) follow standard 28 nm order-of-magnitude figures and SHOULD
be replaced with NeuroSim V1.5 floorplan output before reporting absolute
numbers.

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
    e_dac_step: float    = 5.0e-15     # one DAC code-set, per cell
    e_smtj_read: float   = 5.0e-15     # bit-line read of one row activation
    e_count_inc: float   = 0.5e-15     # one counter increment (CMOS digital)
    e_sram_byte: float   = 5.0e-12     # one byte read from local SRAM
    e_dram_byte: float   = 6.4e-10     # one byte read from off-chip DRAM (Horowitz)

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
    name: str = "28nm-sot-default"
    note: str = ("Chapter-2.3-grounded SOT-MTJ defaults plus 28 nm CMOS "
                 "order-of-magnitude. Replace with NeuroSim V1.5 floorplan "
                 "for accurate absolute numbers.")

    @property
    def e_smtj_write(self) -> float:
        """Single-shot SOT write energy via Ohmic dissipation in the channel."""
        return (self.V_wr_nom ** 2 / self.R_SOT) * self.t_write


def default_28nm() -> TechParams:
    """Return the default Chapter-2.3-grounded tech-parameter set."""
    return TechParams()
