#!/usr/bin/env python3
"""Track B — write-line IR-drop (errata R3) + write-energy overhead (errata R5).

Grounding: sky130 sheet resistances are Magic's own techfile values (sky130A.tech `resist`
section), VALIDATED here by a Magic `extresist` run on a calibration strap:
poly extracted = 47.96 Ohm/sq vs techfile 48.2 Ohm/sq (0.5%). See run_extresist.sh.

Model: the calibrated sMTJ write point is 0.9 V across the 776 Ohm write device for 0.75 ns
(E_dev = 0.783 pJ).  The on-chip column write path adds *series metal resistance*:
  bit line (driver -> selected cell) + source line (cell -> sink),
each of length L = N_cells * cell_pitch.  We report the ROUND-TRIP metal R (BL+SL) as the
parasitic in series with the 776 Ohm device, then the IR-drop, headroom loss, and the extra
energy E_extra = I_write^2 * R_par * t_write  (fraction vs 776 Ohm = R_par/776, identical for
energy and for series-R because I and t are common).

Honesty: ratios, not absolutes; sky130 130 nm is pessimistic; cell pitch is an explicit assumption.
"""
import json
import os

# --- calibrated write operating point (from gen_golden / write_mc_harness) ---
V_WRITE = 0.9          # V across the write device
R_DEV = 776.0          # Ohm, sMTJ+access write resistance ("the 776 Ohm write line")
T_WRITE = 0.75e-9      # s
I_WRITE = V_WRITE / R_DEV          # 1.16 mA
E_DEV = I_WRITE**2 * R_DEV * T_WRITE   # 0.783 pJ (== V*I*t)

# --- sky130 sheet R (Ohm/sq), Magic sky130A.tech; TT + high corner. poly TT cross-checked 47.96 ---
RS_TT = {"li1": 12.8, "met1": 0.125, "met2": 0.125, "met3": 0.047, "met4": 0.047, "met5": 0.029}
RS_HI = {"li1": 17.0, "met1": 0.145, "met2": 0.145, "met3": 0.056, "met4": 0.056, "met5": 0.035}
# contact R (Ohm each), Magic techfile
RC = {"mcon": 9.3, "via1": 4.5, "via2": 3.41}

def r_line(layer, n_cells, pitch_um, w_um, rs=RS_TT):
    """Round-trip metal R (bit line + source line) for an N-cell column, Ohm."""
    squares = (n_cells * pitch_um) / w_um
    return 2.0 * rs[layer] * squares           # x2 = BL + SL return

def report(n_cells, pitch_um, w_um, layer, rs=RS_TT):
    rpar = r_line(layer, n_cells, pitch_um, w_um, rs)
    ir = I_WRITE * rpar
    frac = rpar / R_DEV
    e_extra = I_WRITE**2 * rpar * T_WRITE
    return dict(N=n_cells, layer=layer, pitch_um=pitch_um, w_um=w_um,
                R_par_ohm=rpar, IR_mV=ir*1e3, headroom_loss_pct=ir/V_WRITE*100,
                pct_of_776=frac*100, E_extra_fJ=e_extra*1e15, E_overhead_pct=frac*100)

def fmt(r):
    return ("N=%-5d %-4s W=%.1fum pitch=%.1fum | R_par=%8.1f ohm  IR=%6.1f mV  "
            "headroom=%5.1f%%  =%5.1f%% of 776ohm  E_extra=%6.1f fJ" %
            (r["N"], r["layer"], r["w_um"], r["pitch_um"], r["R_par_ohm"], r["IR_mV"],
             r["headroom_loss_pct"], r["pct_of_776"], r["E_extra_fJ"]))

print("=" * 96)
print("Write-line IR-drop (R3) + energy overhead (R5)  --  sky130, Magic-validated sheet R")
print("I_write=%.3f mA  R_dev=776 ohm  t=0.75 ns  E_dev=%.3f pJ" % (I_WRITE*1e3, E_DEV*1e12))
print("=" * 96)

print("\n[1] Realistic column on met2, W=1um, pitch=2um  (IR-drop grows with column height N):")
rows = [report(n, 2.0, 1.0, "met2") for n in (16, 64, 256, 1024)]
for r in rows:
    print("   " + fmt(r))

print("\n[2] At N=256 (worst column): routing-layer & width trade (why NOT li1; wider/higher = better):")
sweep = []
for layer in ("li1", "met1", "met2", "met3"):
    for w in (0.5, 1.0, 2.0):
        sweep.append(report(256, 2.0, w, layer))
for r in sweep:
    print("   " + fmt(r))

print("\n[3] High-corner (worst-case process) for the realistic met2 W=1um pitch=2um column:")
rows_hi = [report(n, 2.0, 1.0, "met2", RS_HI) for n in (64, 256, 1024)]
for r in rows_hi:
    print("   " + fmt(r))

# contacts: a driver/cell end-stack li1->met2 = mcon + via1; both ends ~2 stacks
r_contacts = 2 * (RC["mcon"] + RC["via1"])
print("\n[4] End via-stacks (li1->met1->met2, 2 ends): +%.1f ohm (=%.1f%% of 776) -- reducible by "
      "paralleling vias." % (r_contacts, r_contacts/R_DEV*100))

concl = (
    "R3 finding: column write-line IR-drop is NEGLIGIBLE for small columns (N<=64 on metal: "
    "<5%% of the 776 ohm device) but becomes SIGNIFICANT for tall columns (N=256 -> ~16%% on "
    "met1/met2 W=1um; ~6%% on met3), and is CATASTROPHIC on li1 (kohm). Design guidance: route the "
    "write line on met2+ (never li1/poly), widen it, or segment tall columns; budget ~10-20%% write "
    "headroom/energy for N>=256. This refines errata R3 (IR-drop) and adds the R_par/776 series "
    "overhead to the R5 end-to-end write energy (E_dev=0.783 pJ -> +%.1f%% at N=256 met2)."
    % (report(256,2.0,1.0,'met2')['pct_of_776']))
print("\n" + "=" * 96 + "\n" + concl + "\n" + "=" * 96)

out = dict(operating_point=dict(I_write_mA=I_WRITE*1e3, R_dev_ohm=R_DEV, t_write_ns=T_WRITE*1e9,
                                E_dev_pJ=E_DEV*1e12),
           sheet_R_validation=dict(poly_extracted_ohm_sq=47.96, poly_techfile_ohm_sq=48.2),
           sheet_R_TT=RS_TT, contacts_ohm=RC,
           realistic_met2_W1_pitch2=rows, n256_layer_width_sweep=sweep,
           high_corner_met2=rows_hi, end_via_stacks_ohm=r_contacts, conclusion=concl)
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ir_drop_summary.json")
with open(p, "w") as f:
    json.dump(out, f, indent=2)
print("wrote %s" % p)
