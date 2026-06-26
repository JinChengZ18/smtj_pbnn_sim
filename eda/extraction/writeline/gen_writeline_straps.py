#!/usr/bin/env python3
"""Track B (errata R3/R5): sky130 metal sheet-R calibration straps for write-line IR-drop.

Each strap is a known-geometry rectangle on one routing layer with a label at each end.
Magic `extresist` (run_extresist.sh) then reports the end-to-end R, from which we back out the
effective sheet resistance Rs = R * W / L for that layer. analyze_ir_drop.py scales Rs to a real
column write line and compares the parasitic IR-drop / energy to the 776 ohm sMTJ write device.

L=200 um, W=0.5 um  ->  L/W = 400 squares (gives a comfortably measurable R on the low-R metals).

Run IN WSL via KLayout batch:
  klayout -b -r eda/extraction/writeline/gen_writeline_straps.py
"""
import os
import pya

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "writeline_straps.gds")

L_UM, W_UM, PITCH_UM = 200.0, 0.5, 5.0

# layer name -> (draw datatype, label datatype) on the sky130 GDS layer number
LAYERS = [
    ("poly", 66, 20, 5),
    ("li1", 67, 20, 5),
    ("met1", 68, 20, 5),
    ("met2", 69, 20, 5),
    ("met3", 70, 20, 5),
]

ly = pya.Layout()
ly.dbu = 0.001
top = ly.create_cell("writeline_straps")
L = int(L_UM / ly.dbu)
W = int(W_UM / ly.dbu)

for i, (name, lnum, draw_dt, lab_dt) in enumerate(LAYERS):
    y = int(i * PITCH_UM / ly.dbu)
    draw = ly.layer(lnum, draw_dt)
    lab = ly.layer(lnum, lab_dt)
    top.shapes(draw).insert(pya.Box(0, y, L, y + W))
    # a label at each end, on the sky130 label datatype so Magic attaches them as net names
    ta = pya.Text("%s_a" % name, pya.Trans(pya.Point(int(0.5 / ly.dbu), y + W // 2)))
    tb = pya.Text("%s_b" % name, pya.Trans(pya.Point(L - int(0.5 / ly.dbu), y + W // 2)))
    top.shapes(lab).insert(ta)
    top.shapes(lab).insert(tb)

ly.write(OUT)
bb = top.bbox()
print("GDS_WRITTEN %s" % OUT)
print("straps=%d  L=%.1fum W=%.2fum squares=%.0f  bbox_um=%.1f x %.1f"
      % (len(LAYERS), L_UM, W_UM, L_UM / W_UM, bb.width() * ly.dbu, bb.height() * ly.dbu))
