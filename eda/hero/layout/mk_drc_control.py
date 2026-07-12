#!/usr/bin/env python3
"""Positive control for the sky130 DRC deck (audit-mandated, 2026-07-08).

Injects a deliberate met1 width violation (0.05 um sliver) into a copy of
cell2t.gds; running run_drc_2t.sh's deck invocation against the copy MUST
report at least an m1.1 (met1 width 0.14) item. If it reports 0, the deck
invocation is broken (e.g. feature flags missing -- the failure mode that
produced the 2026-06-26 false-negative "0 violations") and no clean result
from it may be trusted.

Run IN WSL from this directory:
  klayout -b -r mk_drc_control.py
  # then DRC the control:
  #   klayout -b -r $DECK -rd input=cell2t_control.gds -rd report=ctl.xml \
  #     -rd top_cell=cell2t_smtj -rd feol=1 -rd beol=1 -rd offgrid=1
  #   grep -c "<item>" ctl.xml     -> must be >= 1
"""
import os

import pya

HERE = os.path.dirname(os.path.abspath(__file__))
ly = pya.Layout()
ly.read(os.path.join(HERE, "cell2t.gds"))
top = ly.top_cell()
met1 = ly.layer(68, 20)
top.shapes(met1).insert(pya.Box(5000, 5000, 5050, 6000))  # 0.05um sliver < m1.1 (0.14)
opt = pya.SaveLayoutOptions()
opt.gds2_write_timestamps = False
out = os.path.join(HERE, "cell2t_control.gds")
ly.write(out, opt)
print(f"control GDS written: {out} (expect >=1 DRC item, e.g. m1.1)")
