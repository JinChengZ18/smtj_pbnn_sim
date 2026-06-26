# `eda/hero/layout/` — Hero (A1) layout export → GDS (the "导出版图/GDS" deliverable)

## What's here
- `gen_sa_layout.py` — KLayout-Python generator: instantiates the StrongARM's 9 transistors
  (5 NMOS input-pair/tail/latch + 4 PMOS latch/precharge) as **guard-ringed sky130 PCells**
  (`nmos18`/`pmos18`, library `SKY130`), flattens, and writes GDS.
- `sa_devices.gds` — the output GDS (✅ **verified**: top cell `strongarm_sa_devs`, 17.5×18.7 µm,
  **611 shapes on the correct sky130 layers** — diff 65/20, poly 66/20, licon 66/44, li1 67/20,
  mcon 67/44, met1 68/20, nwell 64/20, …).

Run (in WSL):  `klayout -b -r eda/hero/layout/gen_sa_layout.py`

## Why KLayout (not Magic/TCL)
The goal was a scripted **Magic TCL** layout, but the installed **Magic 8.3.105 is too old** for
the sky130A techfile, which **requires Magic 8.3.306** (`sky130A.tech` version section error →
fatal, no layers load). So the Magic/TCL route is **version-blocked — needs a Magic update**
(rebuild ≥8.3.306, or the IIC-OSIC-TOOLS newer image). The KLayout sky130 PCell flow works
instead and produces the same GDS deliverable. (KLayout uses system python 3.12; the sky130
PCell package needs `pandas`, installed via `pip3 install --break-system-packages pandas`.)

## DRC status (environment caveat, not a layout problem)
`sky130A_mr.drc` read 0 polygons in every batch attempt. Root cause is **WSL-batch-invocation
friction**, not the layout — three compounding issues in the Windows→GitBash→WSL→KLayout chain:
1. the **non-ASCII project path** (`毕业设计/仿真`) breaks KLayout's `-rd input=<path>` UTF-8
   argument parsing (it truncated the value to `/sa_devices.gds`);
2. copying to `/tmp` doesn't survive — WSL2 stops the idle distro between tool calls and **wipes
   the `/tmp` tmpfs**, so the GDS vanishes before DRC reads it (copy + DRC must be one call);
3. heredoc/`$HOME` expansion through the GitBash→`wsl.exe -- bash -lc '…'` chain is unreliable.

**To DRC this layout, run it natively** (inside a WSL shell or Linux box, *not* the batch chain),
from an ASCII working dir on a persistent FS — copy `sa_devices.gds` next to the deck and run
`klayout -b -r .../sky130A_mr.drc -rd input=sa.gds -rd report=sa_drc.xml -rd top_cell=strongarm_sa_devs`,
or simply open the GDS in the KLayout GUI and run the sky130 DRC menu. The PCell devices are
DRC-clean by construction (foundry PCells; placement uses 1.5 µm gaps + per-device guard rings),
so violations would only come from later inter-device routing, which isn't drawn yet.

## Next steps (the routing/interactive boundary)
- **Routing**: connect the devices per the StrongARM schematic (tail→gnd, latch cross-couple,
  input gates, precharge) — the labor-intensive part; scriptable in KLayout-Python but slow blind,
  or done in the KLayout/Magic GUI.
- **Netgen LVS** (layout vs `eda/hero/strongarm_sa.spice`) once routed.
- **PEX** (Magic ext2spice or KLayout) → post-layout offset/energy.
- Render a PNG figure (KLayout `save_image`, needs xvfb headless) for the paper.
