# `eda/hero/layout/` — Hero (A1) layout export → GDS (the "导出版图/GDS" deliverable)

## What's here
- `gen_sa_layout.py` — KLayout-Python generator: instantiates the StrongARM's **11 transistors**
  (5 NMOS tail/input-pair/latch + 6 PMOS latch/precharge — matching `../strongarm_sa.spice`) as
  **guard-ringed sky130 PCells** (`nmos18`/`pmos18`, library `SKY130`), flattens, and writes GDS.
  *(2026-06-26: device count fixed 9→11 — the first cut omitted the Mp3/Mp4 da/db precharge PMOS.)*
- `sa_devices.gds` — the output GDS (✅ top cell `strongarm_sa_devs`, **23.1×18.7 µm, 11 devices**, on
  the correct sky130 layers — diff 65/20, poly 66/20, licon 66/44, li1 67/20, mcon 67/44, met1 68/20,
  nwell 64/20, …).
- `run_drc.sh` — reproducible sky130 DRC via an ASCII build dir (✅ **0 violations**; see below).
- `run_pex.sh` — reproducible Magic parasitic extraction (`gds read → extract → ext2spice`), via the
  same ASCII build dir (✅ **11 devices + 35.25 fF** parasitic C extracted; see "Next steps").
- `LVS_GUI_CHECKLIST.md` — the routing/LVS last-mile (per-net connection table + GUI steps); LVS
  toolchain (netgen 1.5.321 + sky130A_setup) is validated, routing is the remaining interactive step.

Run (in WSL):  `klayout -b -r eda/hero/layout/gen_sa_layout.py`

## Why KLayout was used for the GDS (Magic now also available)
The GDS was first produced with the **KLayout sky130 PCell** flow because, at the time, the installed
**Magic 8.3.105 was too old** for the sky130A techfile (which **requires Magic 8.3.306**:
`sky130A.tech` version error → fatal, no layers load). **Magic has since been upgraded to 8.3.668**
(2026-06-26; see `../../MANUAL_SETUP_NEEDED.md §1`), so the Magic/TCL `routing → LVS → PEX` route is
now available too. The KLayout GDS stays the canonical deliverable — both tools read the same
`sa_devices.gds`. (KLayout uses system python 3.12; the sky130 PCell package needs `pandas`,
installed via `pip3 install --break-system-packages pandas`.)

## DRC status — ✅ PASS (0 violations), via the ASCII build-dir runner
**`sa_devices.gds` passes `sky130A_mr.drc` with 0 violations** (device-level; routing DRC follows
once interconnect is drawn). Reproduce with **`run_drc.sh`**:

```bash
wsl -d Ubuntu-24.04-EDA -- bash -lc \
  'cd "<repo>/eda/hero/layout" && bash run_drc.sh'
# -> staged 123626 bytes ; DRC done: 0 violations
```

It stages the GDS into a persistent ASCII ext4 dir (`/home/lenovo/smtj_eda_build`) and runs DRC
there, so the report lands in `$BUILD/sa_drc.xml` + `$BUILD/drc.log`.

**Why the build dir** (kept so it isn't re-hit): the batch chain
Windows→GitBash→`wsl.exe -- bash -lc`→tool had compounding gotchas. **One is now historical:** the
**non-ASCII project path** (`毕业设计/仿真`) used to break KLayout's `-rd input=<path>` UTF-8 arg
parsing — but the repo moved to a **pure-English path** on 2026-06-26, so that no longer applies.
**Still live:** (1) `/tmp` is **tmpfs and is wiped when the WSL distro idle-stops** between calls;
(2) ASCII `$VAR`/`$HOME` set *inside the `bash -lc '…'` arg string* get lost in the GitBash→wsl
marshalling. So the runner still stages into a **persistent ASCII ext4** dir
(`/home/lenovo/smtj_eda_build`) and reads variables from a **script file** (not the `-lc` arg). The
PCell devices are foundry-correct and spaced 1.5 µm with guard rings, so 0 device-level violations is
expected; real DRC content will appear when inter-device routing is added.

## Next steps (the routing/interactive boundary)
- **Routing**: connect the devices per the StrongARM schematic (tail→gnd, latch cross-couple,
  input gates, precharge) — the labor-intensive part; scriptable in KLayout-Python but slow blind,
  or done in the KLayout/Magic GUI.
- **Netgen LVS** (layout vs `eda/hero/strongarm_sa.spice`) once routed. ⚠ `/usr/bin/netgen` (apt) is
  the *mesh-generator* netgen, NOT the LVS netgen (Tim Edwards) — verify/install the right one first.
- **PEX**: Magic `ext2spice` toolchain is verified (`run_pex.sh`, 9 devices + parasitic C on the
  device-level GDS); once routed, add `extresist` for R → post-layout offset/energy (errata R3/R5).
- Render a PNG figure (KLayout `save_image`, needs xvfb headless) for the paper.
