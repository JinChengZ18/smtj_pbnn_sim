# `eda/hero/layout/` — Hero (A1) layout export → GDS (the "导出版图/GDS" deliverable)

## What's here
- `gen_sa_layout.py` — KLayout-Python generator: instantiates the StrongARM's 9 transistors
  (5 NMOS input-pair/tail/latch + 4 PMOS latch/precharge) as **guard-ringed sky130 PCells**
  (`nmos18`/`pmos18`, library `SKY130`), flattens, and writes GDS.
- `sa_devices.gds` — the output GDS (✅ **verified**: top cell `strongarm_sa_devs`, 17.5×18.7 µm,
  **611 shapes on the correct sky130 layers** — diff 65/20, poly 66/20, licon 66/44, li1 67/20,
  mcon 67/44, met1 68/20, nwell 64/20, …).
- `run_drc.sh` — reproducible sky130 DRC via an ASCII build dir (✅ **0 violations**; see below).

Run (in WSL):  `klayout -b -r eda/hero/layout/gen_sa_layout.py`

## Why KLayout (not Magic/TCL)
The goal was a scripted **Magic TCL** layout, but the installed **Magic 8.3.105 is too old** for
the sky130A techfile, which **requires Magic 8.3.306** (`sky130A.tech` version section error →
fatal, no layers load). So the Magic/TCL route is **version-blocked — needs a Magic update**
(rebuild ≥8.3.306, or the IIC-OSIC-TOOLS newer image). The KLayout sky130 PCell flow works
instead and produces the same GDS deliverable. (KLayout uses system python 3.12; the sky130
PCell package needs `pandas`, installed via `pip3 install --break-system-packages pandas`.)

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

**Why the build dir** (this tripped up several earlier attempts — kept here so it isn't re-hit):
the batch chain Windows→GitBash→`wsl.exe -- bash -lc`→KLayout has three compounding gotchas, none
of them a layout problem: (1) the **non-ASCII project path** (`毕业设计/仿真`) breaks KLayout's
`-rd input=<path>` UTF-8 arg parsing (truncates the value); (2) `/tmp` is **tmpfs and is wiped when
the WSL distro idle-stops** between calls; (3) ASCII `$VAR`/`$HOME` set *inside the `bash -lc '…'`
arg string* get lost in the GitBash→wsl marshalling. The runner sidesteps all three: a literal `cd`
into the CJK dir (which the chain tolerates) + a **relative** GDS name + a **script file** bash reads
directly (so its variables are real) + a **persistent ASCII ext4** staging dir. The PCell devices
are foundry-correct and spaced 1.5 µm with guard rings, so 0 device-level violations is expected;
real DRC content will appear when inter-device routing is added.

## Next steps (the routing/interactive boundary)
- **Routing**: connect the devices per the StrongARM schematic (tail→gnd, latch cross-couple,
  input gates, precharge) — the labor-intensive part; scriptable in KLayout-Python but slow blind,
  or done in the KLayout/Magic GUI.
- **Netgen LVS** (layout vs `eda/hero/strongarm_sa.spice`) once routed.
- **PEX** (Magic ext2spice or KLayout) → post-layout offset/energy.
- Render a PNG figure (KLayout `save_image`, needs xvfb headless) for the paper.
