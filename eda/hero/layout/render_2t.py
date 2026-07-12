#!/usr/bin/env python3
"""Headless top-view render of cell2t.gds with sky130 layer colors.

Needs GUI libs but no display -- run with the offscreen Qt platform:
  QT_QPA_PLATFORM=offscreen klayout -z -nc -r render_2t.py
Output: figures/panels/ch04_22_a.png (raw, unnumbered; deck adds letters).
"""
import os

import pya

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(REPO, "figures", "panels", "ch04_22_a.png")
LYP = "/opt/pdk/sky130A/libs.tech/klayout/tech/sky130A.lyp"

app = pya.Application.instance()
# clean render for the article figure: no display grid, no mini scale ruler
# (a large 1 um scale bar is stamped afterwards by add_scalebar.py)
app.set_config("grid-visible", "false")
app.set_config("grid-show-ruler", "false")

mw = pya.MainWindow.instance()
view = mw.view(mw.create_view())
cell_index = view.create_layout(True)
layout = view.active_cellview().layout()
layout.read(os.path.join(HERE, "cell2t.gds"))
view.active_cellview().cell = layout.top_cell()
if os.path.exists(LYP):
    view.load_layer_props(LYP)
view.add_missing_layers()          # bring in 200/0, 201/0 (not in the lyp)
# style the black-box annotation layers; hide the areaid marker
for li in view.each_layer():
    if li.source_layer == 200:
        li.fill_color = li.frame_color = 0x8E24AA   # MTJ pillar: purple
        li.dither_pattern = 0                        # solid
        li.width = 2
        li.visible = True
    if li.source_layer == 201:
        li.fill_color = li.frame_color = 0xEF6C00   # SOT track: orange
        li.dither_pattern = 2
        li.width = 2
        li.visible = True
    if li.source_layer == 235:
        li.visible = False
view.max_hier_levels = 10
# frame the design bbox (markers excluded), small margin
view.zoom_box(pya.DBox(-1.75, -1.1, 4.35, 3.3))
view.save_image(OUT, 2400, 1730)
print("RENDER_SAVED", OUT)
