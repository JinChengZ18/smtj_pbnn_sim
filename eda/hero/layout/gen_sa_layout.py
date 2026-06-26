#!/usr/bin/env python3
"""Hero (A1) layout export via KLayout sky130 PCells -> GDS (the "导出版图/GDS" deliverable).

NOTE: this GDS was produced with KLayout's sky130 PCells (nmos18/pmos18, library "SKY130")
because the then-installed Magic 8.3.105 was too old for the sky130A techfile (requires
8.3.306). Magic has since been upgraded to 8.3.668 (2026-06-26), so the Magic/TCL route is
available too; this KLayout flow stays the canonical GDS generator (both read the same GDS).

This first cut places the StrongARM's transistors as guard-ringed sky130 PCell instances
(a real, DRC-aware device layout) and writes GDS. Full inter-device routing (DRC-clean
StrongARM) is the next step.

Run IN WSL via KLayout batch:
  klayout -b -r eda/hero/layout/gen_sa_layout.py
"""
import os
import sys

import pya

PCELL_DIR = "/opt/pdk/sky130A/libs.tech/klayout/pymacros"
sys.path.insert(0, PCELL_DIR)
from sky130_pcells import Sky130            # noqa: E402

Sky130()                                    # register PCell library "SKY130"

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "sa_devices.gds")

ly = pya.Layout()
ly.dbu = 0.001
top = ly.create_cell("strongarm_sa_devs")

# StrongARM CMOS devices: NMOS tail/input-pair/latch (nmos18) + PMOS latch/precharge (pmos18).
NMOS = [("Mtail", 4.0), ("M1", 4.0), ("M2", 4.0), ("M3", 2.0), ("M4", 2.0)]
PMOS = [("M5", 2.0), ("M6", 2.0), ("Mp1", 2.0), ("Mp2", 2.0)]


def place(pcell, w, x_um, y_um):
    c = ly.create_cell(pcell, "SKY130", {"w": w, "l": 0.15, "nf": 1, "gr": 1})
    if c is None:
        raise RuntimeError(f"create_cell({pcell}) returned None")
    top.insert(pya.CellInstArray(
        c.cell_index(), pya.Trans(pya.Point(int(x_um / ly.dbu), int(y_um / ly.dbu)))))
    return c.bbox().width() * ly.dbu, c.bbox().height() * ly.dbu


x = 0.0
for nm, w in NMOS:                                   # NMOS row at y=0
    wpx, _ = place("nmos18", w, x, 0.0)
    x += wpx + 1.5
x = 0.0
for nm, w in PMOS:                                   # PMOS row above
    wpx, _ = place("pmos18", w, x, 15.0)
    x += wpx + 1.5

top.flatten(-1, True)        # flatten device hierarchy into the top cell (DRC-ready)
ly.write(OUT)
bb = top.bbox()
print("GDS_WRITTEN %s" % OUT)
print("top_bbox_um = %.2f x %.2f   instances=%d   cells=%d"
      % (bb.width() * ly.dbu, bb.height() * ly.dbu,
         top.child_instances(), ly.cells()))
