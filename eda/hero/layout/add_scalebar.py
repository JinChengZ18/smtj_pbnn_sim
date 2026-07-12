#!/usr/bin/env python3
"""Stamp a legible 1 um scale bar onto the KLayout render of the 2T cell.

render_2t.py (WSL KLayout, grid and mini-ruler disabled) writes the raw frame;
this Windows-side step draws the article-grade scale bar in-place. The px/um
factor is exact because render_2t.py uses a fixed zoom box and image size:
zoom DBox(-1.75, -1.1, 4.35, 3.3) = 6.1 um wide -> 2400 px => 393.44 px/um.

Run from the repo root (after the WSL render):
    python eda/hero/layout/add_scalebar.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[3]
PANEL = REPO / "figures" / "panels" / "ch04_22_a.png"
PX_PER_UM = 2400 / 6.1
BAR_UM = 1.0

im = Image.open(PANEL).convert("RGB")
dr = ImageDraw.Draw(im)
font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 56)

bar_px = round(BAR_UM * PX_PER_UM)
x0, y0 = 70, im.height - 80          # bottom-left, clear of the layout content
dr.rectangle([x0, y0, x0 + bar_px, y0 + 16], fill="black")
for xe in (x0, x0 + bar_px):         # end ticks
    dr.rectangle([xe - 3, y0 - 14, xe + 3, y0 + 30], fill="black")
label = "1 µm"
tw = dr.textlength(label, font=font)
dr.text((x0 + bar_px / 2 - tw / 2, y0 - 82), label, fill="black", font=font)
im.save(PANEL)
print(f"scale bar stamped: {PANEL.relative_to(REPO)} ({bar_px} px = {BAR_UM} um)")
