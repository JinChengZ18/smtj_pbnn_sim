#!/usr/bin/env python3
"""First-order sky130 area grounding for the PBNN-CIM tile peripherals + 2T SOT-MTJ cell.

Replaces the 28 nm order-of-magnitude area placeholders in `ppa.tech_params` with
estimates anchored in REAL sky130 data:
  * the digital counter is sized from extracted `sky130_fd_sc_hd` standard-cell areas
    (.lef SIZE, row height 2.72 um);
  * the resistor-string write-DAC from those cell areas + a sky130 hi-res-poly unit
    resistor;
  * the 2T SOT-MTJ cell by design rule (sky130 has no MTJ device): two access FETs
    (write MW / read MR, per eda/hero/schematics/gen_system_sch.py) sized from the
    operating point, with the MTJ pillar (~100 nm, Hikstor IEDM-2024) sitting BEOL on
    top and thus adding ~no planar footprint.

This is a first-order (cell-count x cell-area + design-rule) estimate, not a DRC-clean
GDS extraction -- but it is sky130-grounded rather than a 28 nm guess. The dominant,
robust terms (counter DFF/FA, DAC tap MUX) use measured cell areas; the unit-resistor
area and the cell routing overhead are the softest assumptions and are flagged below.

Run:  python eda/testbenches/area_estimate.py
"""
from __future__ import annotations
import math

# --- sky130_fd_sc_hd standard-cell areas [um^2] -----------------------------------#
# Extracted 2026-06-29 from /opt/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lef/
# sky130_fd_sc_hd.lef (SIZE w BY h; canonical row height = 2.72 um).
A_DFF  = 20.02   # sky130_fd_sc_hd__dfxtp_1   (D flip-flop)
A_FA   = 20.02   # sky130_fd_sc_hd__fa_1      (full adder)
A_TG   = 6.26    # sky130_fd_sc_hd__einvp_1   (tri-state inverter ~ analog pass switch)
A_INV  = 3.75    # sky130_fd_sc_hd__inv_1 / buf_1
UTIL   = 0.70    # standard-cell placement utilization (routing overhead = 1/UTIL)

# --- sky130 device / process constants (documented) -------------------------------#
IDSAT_NFET = 0.52e-3   # nfet_01v8 saturation drive ~0.52 mA/um at VGS=VDS=1.8 V
L_MIN      = 0.15      # drawn channel length (um)
SD_EXT     = 0.50      # source/drain diffusion + contact extension per side (um)
A_RUNIT    = 2.5       # hi-res-poly (res_xhigh_po) unit resistor: ~1um body + 2 contacts (SOFT)
MET1_PITCH = 0.34      # met1 pitch (um) -- for the 5 cell lines BL/SL/WWL/RWL/RBL

# --- array / operating point ------------------------------------------------------#
N      = 256     # array fan-in (configs/array/256x256.yaml)
T_MAX  = 8       # deploy sampling depth the chip is sized for (sweet spot; sweep goes to 64)
B_DAC  = 6       # resistor-string write-DAC resolution (chapter04 §4.6: 6-7 bit)
V_WR   = 0.90    # write voltage (V)
R_SOT  = 776.0   # SOT channel resistance (ohm)
R_P    = 4900.0  # MTJ parallel read resistance (ohm)
V_READ = 0.10    # read bias (V)


def fet_area(W):
    """Active footprint of an nfet of width W: W x (L + 2 contacts/diffusion)."""
    return W * (L_MIN + 2 * SD_EXT)


def counter_area():
    """Per-column accumulator: a w-bit (register + adder) summing popcount(0..N) over T."""
    w = math.ceil(math.log2(N * T_MAX))          # accumulator width (bits)
    a = w * (A_DFF + A_FA) / UTIL
    return a, w


def dac_area():
    """Per-row b-bit resistor-string DAC: 2^b unit resistors + binary tap MUX + buffer."""
    n_r = 2 ** B_DAC
    n_tg = 2 ** B_DAC - 1                          # 2:1 binary tree of analog pass switches
    a = (n_r * A_RUNIT + n_tg * A_TG + A_INV) / UTIL
    return a


def cell_area():
    """2T SOT-MTJ cell: write + read access FETs (MTJ is BEOL, adds ~no planar area)."""
    i_wr = V_WR / R_SOT                            # ~1.16 mA write current through MW
    w_write = i_wr / IDSAT_NFET                    # ~2.2 um
    w_read = max(0.42, (V_READ / R_P) / IDSAT_NFET)   # tiny (~uA read) -> min device
    a_fets = fet_area(w_write) + fet_area(w_read)
    a_cell = a_fets * 1.5                          # +50% for the 5 routing lines + cell overhead
    a_track = 0.10 * 0.30                          # ~MTJ CD (100 nm) x ~3x CD SOT channel (BEOL)
    return a_cell, a_track, w_write, i_wr


if __name__ == "__main__":
    a_counter, w = counter_area()
    a_dac = dac_area()
    a_cell, a_track, w_write, i_wr = cell_area()
    print("sky130-grounded PPA areas (first-order):")
    print(f"  a_smtj_cell = {a_cell:7.3f} um^2   (2T cell; write FET W={w_write:.2f} um @ I_wr={i_wr*1e3:.2f} mA)")
    print(f"  a_sot_track = {a_track:7.3f} um^2   (BEOL SOT channel, ~negligible planar)")
    print(f"  a_dac       = {a_dac:7.1f} um^2   ({2**B_DAC} unit-R + {2**B_DAC-1}-switch tap MUX, b={B_DAC})")
    print(f"  a_counter   = {a_counter:7.1f} um^2   ({w}-bit accumulator, N={N}, T<= {T_MAX})")
    print("  (vs 28 nm placeholders 0.05 / 0.04 / 200 / 50)")
