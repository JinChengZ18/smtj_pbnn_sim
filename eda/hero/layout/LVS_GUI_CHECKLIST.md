# Hero (A1) SA — LVS completion checklist (the GUI last-mile)

**Status (2026-06-26, scripted best-effort done):**
- ✅ Device set reconciled to **11** (added Mp3/Mp4); matches `../strongarm_sa_core.spice`.
- ✅ **DRC 0 violations** (`run_drc.sh`); 11 devices extract (`run_pex.sh`, 35.25 fF device C).
- ✅ **LVS toolchain validated** end-to-end: Magic `ext2spice lvs` (cap-free) → netgen 1.5.321 +
  `sky130A_setup.tcl` runs and recognizes nfet/pfet.
- ⏳ **GAP = inter-device ROUTING.** The layout devices are isolated, so net topology can't match
  the schematic (netgen sees merged/isolated devices, 40 vs 10 nets). Routing is the remaining step;
  it needs interactive GUI work because the sky130 KLayout PCells **do not expose PMOS gate contacts**
  (gr=1 seals them; gr=0 omits well/taps), so a headless script can't cleanly finish it.

## What to draw in the GUI (KLayout or Magic), per `strongarm_sa_core.spice`
Connect these nets (S/D are interchangeable — netgen permutes them):

| net | terminals to connect |
|---|---|
| **vss** | Mtail source + **all NMOS guard rings** → VSS rail |
| **vdd** | all PMOS sources + **all PMOS guard rings (nwell taps)** → VDD rail |
| **clk** | Mtail.g, Mp1.g, Mp2.g, Mp3.g, Mp4.g |
| **ntail** | Mtail.d, M1.s, M2.s |
| **da** | M1.d, M3.s, Mp3.d |
| **db** | M2.d, M4.s, Mp4.d |
| **outp** | M4.d, M6.d, Mp1.d, **M3.g, M5.g** (cross-couple) |
| **outn** | M3.d, M5.d, Mp2.d, **M4.g, M6.g** (cross-couple) |
| **vinp** | M1.g |
| **vinn** | M2.g |

Notes for the GUI step:
- **Add PMOS gate contacts** (poly pad ≥0.33 µm + licon + li1 + met1) — the PCell omits them.
- Keep the **da/db and outp/outn routing symmetric** (left/right matched) so layout asymmetry doesn't
  add to the 11.05 mV mismatch offset (see `../sa_postlayout.py`, errata R2).
- Place text labels `vdd vss clk vinp vinn outp outn` on the routed metal for LVS port matching.

## After routing — reproduce LVS + post-layout PEX
```bash
# DRC
wsl -d Ubuntu-24.04-EDA -- bash -lc 'cd "<repo>/eda/hero/layout" && bash run_drc.sh'
# PEX (R+C): add `extresist all` + `ext2spice extresist on` to run_pex.sh's TCL for post-layout R
wsl -d Ubuntu-24.04-EDA -- bash -lc 'cd "<repo>/eda/hero/layout" && bash run_pex.sh'
# LVS (cap-free): Magic `ext2spice lvs` -> sa_lvs.spice, then:
~/eda/netgen/bin/netgen -batch lvs "sa_lvs.spice strongarm_sa_devs" \
   "<repo>/eda/hero/strongarm_sa_core.spice strongarm_sa_core" \
   /opt/pdk/sky130A/libs.tech/netgen/sky130A_setup.tcl
# expect: "Circuits match uniquely." Then re-run sa_postlayout.py with the real switching-node C.
```
A clean LVS unlocks the precise post-layout SA offset/energy (replacing the bounded estimate in
`../sa_postlayout.py`).
