#!/usr/bin/env python3
"""Hero (A1) Track A — post-layout SA parasitics: energy + offset-symmetry (errata R1/R5/R2).

FIRM (Magic-extracted, run_pex.sh on the DRC-clean 11-device sa_devices.gds):
  - 11 MOSFETs (5 nfet_01v8 + 6 pfet_01v8) extract and match the schematic device set.
  - total device parasitic C = 35.25 fF (124 caps), dominated by RAIL-TIED, NON-SWITCHING
    junctions: NMOS source/bulk node ~22.1 fF + six PMOS nwell-substrate caps ~3.53 fF each.

ESTIMATE (floorplan + Magic-validated sky130 caps; precise value needs the routed+labeled
layout = the GUI last-mile in eda/hero/layout/LVS_GUI_CHECKLIST.md):
  - switching nodes are da/db (input-pair drains) + outp/outn (latch outputs).
  - SA dynamic energy per decision ~ C_switch * Vdd^2 (rail-to-rail evaluate).

Honesty: report a RANGE; sky130 130 nm is pessimistic; the firm number is the device C, the
energy is an order-of-magnitude bound until the routed-LVS extraction lands.
"""
import json
import os

VDD = 1.8
# --- firm, extracted (sum of cap VALUES; per-node sums would double-count node-to-node caps) ---
C_DEV_TOTAL_fF = 35.25
# the extracted C is dominated by RAIL-TIED, NON-SWITCHING junctions: the NMOS source/bulk node
# alone shows ~22 fF and each of the six PMOS nwell-substrate caps ~3.5 fF. The switching-node C
# (da/db/outp/outn) is the small residual and is NOT separable without net labels (routed-LVS).
C_DEV_SWITCH_fF = 2.0     # nominal residual switching device-junction C floor (un-separable here)

# --- estimate: routing C of the 4 SA signal nets inside the ~23x19 um cell ---
# sky130 min-width met1 over field ~0.13 fF/um (area+fringe to substrate). Internal SA nets are
# short; take a 10-40 um/net range for a 23x19 um block.
MET1_C_fF_per_um = 0.13
NET_LEN_LO, NET_LEN_HI = 10.0, 40.0
N_SIG_NETS = 4
C_route_lo = N_SIG_NETS * NET_LEN_LO * MET1_C_fF_per_um
C_route_hi = N_SIG_NETS * NET_LEN_HI * MET1_C_fF_per_um

C_switch_lo = C_DEV_SWITCH_fF + C_route_lo
C_switch_hi = C_DEV_SWITCH_fF + C_route_hi
E_lo = C_switch_lo * 1e-15 * VDD**2     # J
E_hi = C_switch_hi * 1e-15 * VDD**2

# the per-read placeholder currently in extraction/peripheral_energy.yaml
E_READ_PLACEHOLDER = 5.0e-15

print("=" * 90)
print("Hero(A1) post-layout SA parasitics  (Vdd=%.1f V)" % VDD)
print("=" * 90)
print("FIRM (extracted): 11 devices DRC-clean; total device parasitic C = %.2f fF" % C_DEV_TOTAL_fF)
print("   dominated by rail-tied junctions (NMOS bulk node ~22 fF + six PMOS wells ~3.5 fF each,")
print("   all non-switching); switching-node C is the small residual (~%.1f fF floor, needs labels)"
      % C_DEV_SWITCH_fF)
print("ESTIMATE (floorplan routing): %d signal nets x [%g..%g] um x %.2f fF/um = [%.1f..%.1f] fF"
      % (N_SIG_NETS, NET_LEN_LO, NET_LEN_HI, MET1_C_fF_per_um, C_route_lo, C_route_hi))
print("-> SA switching C ~ [%.1f .. %.1f] fF" % (C_switch_lo, C_switch_hi))
print("-> SA dynamic energy/decision ~ C*Vdd^2 = [%.0f .. %.0f] fJ" % (E_lo*1e15, E_hi*1e15))
print("-" * 90)
print("R1 indicator: this [%.0f..%.0f] fJ is %.0f-%.0fx the 5 fF read placeholder in "
      "peripheral_energy.yaml" % (E_lo*1e15, E_hi*1e15, E_lo/E_READ_PLACEHOLDER, E_hi/E_READ_PLACEHOLDER))
print("   -> sky130 readout SA energy is UNDER-counted by the 28nm placeholder; periphery %% (now "
      "~1.3%%) shifts up. Pin down with routed-LVS extraction.")
print("-" * 90)
print("R2 (offset): input-referred offset is mismatch-dominated (sigma=9.21mV=0.39*V_T, run_offset_mc N=120")
print("   MC). A SYMMETRIC da/db & outp/outn layout keeps the parasitic-asymmetry offset << 11mV;")
print("   any layout imbalance adds in quadrature -> design rule: match the two SA sides' routing.")
print("=" * 90)

out = dict(
    firm=dict(devices=11, drc_violations=0, C_dev_total_fF=C_DEV_TOTAL_fF,
              C_dev_switch_floor_fF=round(C_DEV_SWITCH_fF, 2),
              note="extracted C dominated by rail-tied bulk(~22fF)+wells(6x~3.5fF); switching-node C needs labels"),
    estimate=dict(C_route_fF=[round(C_route_lo, 1), round(C_route_hi, 1)],
                  C_switch_fF=[round(C_switch_lo, 1), round(C_switch_hi, 1)],
                  E_sa_fJ=[round(E_lo*1e15, 1), round(E_hi*1e15, 1)],
                  vs_read_placeholder_x=[round(E_lo/E_READ_PLACEHOLDER, 1), round(E_hi/E_READ_PLACEHOLDER, 1)]),
    caveat="device C extracted; routing C + energy are floorplan estimates pending routed-LVS PEX",
)
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sa_postlayout_summary.json")
with open(p, "w") as f:
    json.dump(out, f, indent=2)
print("wrote %s" % p)
