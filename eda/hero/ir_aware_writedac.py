#!/usr/bin/env python3
"""Forward design (simulator-discovery-driven): IR-aware per-row write-voltage pre-distortion.

This is a DESIGN that the extraction DICTATED, not a corrected claim. The write-line IR-drop study
showed that delivering one write voltage to the column base leaves a cell at row r seeing
V_target - I_write * R_par(r): on a tall column the far cell droops below the calibrated write point,
so the per-cell write PROBABILITY (the p-bit sigmoid output) varies catastrophically with position.

Design: fold a per-row pre-distortion code into the existing write-DAC. When addressing row r, drive
V_drive(r) = V_target + I_write * R_par(r), with R_par(r) computed from the EXTRACTED sky130 sheet
resistance and the column geometry, so every cell sees V_target regardless of position. Combined
with the per-column V_th trim (device-mismatch compensation), this gives a position+device-aware
write-DAC: V_drive(col,row) = V_target + I_write*R_par(row) + trim(col). The pre-distortion is a
static per-row look-up from known geometry -- near-free in control; it only asks the driver for
~I_write*R_par(N) of extra headroom on the far rows.

sky130 sheet R from Magic extraction (met2 0.125 Ohm/sq, validated vs techfile). Honesty: ratios;
round-trip R_par(r)=2*Rs*(r*pitch/W); cell pitch is an explicit assumption.
"""
from __future__ import annotations
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent

VTH, VT, RSOT = 0.895783, 0.023414, 776.0
I_WRITE = 0.9 / RSOT                     # 1.16 mA (calibrated write current)
RS = {"met1": 0.125, "met2": 0.125, "met3": 0.047}   # Ohm/sq, Magic-extracted
PITCH_UM, W_UM, LAYER = 2.0, 1.0, "met2"


def r_par(r):                            # round-trip (bit line + source line) metal R to row r
    return 2.0 * RS[LAYER] * (r * PITCH_UM / W_UM)


def psw(v):
    return 1.0 / (1.0 + math.exp(-(v - VTH) / VT))


def main():
    N = 256
    # target a representative write probability (e.g. 0.9) -> V_target
    p_target = 0.90
    V_target = VTH + VT * math.log(p_target / (1 - p_target))
    rows = list(range(0, N + 1, N // 8))

    print("=" * 92)
    print("Forward design: IR-aware per-row write pre-distortion (sky130 extracted R, %s, N=%d)"
          % (LAYER, N))
    print("V_target=%.4f V (-> p_sw=%.2f at the near cell); I_write=%.2f mA; pitch=%.1f um W=%.1f um"
          % (V_target, p_target, I_WRITE * 1e3, PITCH_UM, W_UM))
    print("=" * 92)
    print("  row    R_par(Ohm)  IR(mV)   V_cell no-predist  p_sw no-pd   V_cell predist  p_sw pd")
    out_rows = []
    for r in rows:
        ir = I_WRITE * r_par(r)
        v_nopd = V_target - ir                       # base-driven: far cell droops
        v_pd = V_target                              # pre-distorted: cell sees target
        print("  %4d    %7.1f   %6.1f      %.4f         %.3f        %.4f       %.3f" %
              (r, r_par(r), ir * 1e3, v_nopd, psw(v_nopd), v_pd, psw(v_pd)))
        out_rows.append(dict(row=r, R_par_ohm=round(r_par(r), 1), IR_mV=round(ir * 1e3, 2),
                             v_cell_nopd=round(v_nopd, 4), psw_nopd=round(psw(v_nopd), 4),
                             v_cell_pd=round(v_pd, 4), psw_pd=round(psw(v_pd), 4),
                             predist_code_mV=round(ir * 1e3, 2)))
    p_nopd = [psw(V_target - I_WRITE * r_par(r)) for r in range(N + 1)]
    spread_nopd = max(p_nopd) - min(p_nopd)
    max_code_mV = I_WRITE * r_par(N) * 1e3
    bits = max(1, math.ceil(math.log2(max_code_mV / (VT * 1e3) * 4)))   # ~LSB <= V_T/4

    concl = ("Without pre-distortion the per-cell write probability spreads %.2f (near cell %.2f -> "
             "far cell %.3f) purely from position-dependent IR-drop -- the tall column writes its far "
             "rows essentially not at all. The per-row pre-distortion code spans 0..%.0f mV "
             "(~%d write-DAC bits at an LSB of V_T/4), is a static look-up from the extracted sheet "
             "resistance and column geometry, and flattens the write probability to the target at "
             "every row. Folded with the per-column V_th trim it yields a position+device-aware "
             "write-DAC -- a circuit dictated by the IR-drop extraction, at near-zero control cost "
             "(only far-row driver headroom). Honesty: ratios; round-trip metal R; assumed cell pitch."
             % (spread_nopd, p_nopd[0], p_nopd[-1], max_code_mV, bits))
    print("\n" + "=" * 92 + "\n" + concl + "\n" + "=" * 92)
    out = dict(N=N, layer=LAYER, pitch_um=PITCH_UM, W_um=W_UM, V_target=round(V_target, 4),
               p_target=p_target, I_write_mA=round(I_WRITE * 1e3, 3),
               psw_spread_nopd=round(spread_nopd, 4), max_predist_code_mV=round(max_code_mV, 1),
               predist_bits=bits, rows=out_rows, conclusion=concl)
    (HERE / "ir_aware_writedac_summary.json").write_text(json.dumps(out, indent=2))
    print("wrote ir_aware_writedac_summary.json")


if __name__ == "__main__":
    main()
