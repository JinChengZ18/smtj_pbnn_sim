#!/usr/bin/env python3
"""Circuit-architecture (tile-level) diagram: how each peripheral module couples to the sMTJ array.

Distinct from fig 4.1 (conceptual dataflow) and the per-module schematics (figs 6-9): this shows the
floorplan-level coupling only -- a central 2T SOT-MTJ array with write column-drivers (top, drive
BL/SL), a row decoder + WL drivers (left, drive WWL/RWL), a column read-out (bottom, sense RBL/SL;
StrongARM p-bit + column-shared SAR), and a mode/timing controller (right) orchestrating phases.
No module internals are drawn -- only the bus coupling (BL/SL, WWL/RWL, RBL) between blocks and array.
Polished SVG (same design language as fig 4.1), rasterised with cairosvg.
"""
import os

FILL = "#ece9f6"; FILL2 = "#e0d8f1"; STROKE = "#6a4fa3"
TITLE = "#3f2a7a"; SUB = "#6a4fa3"; BODY = "#2b2b2b"; ARR = "#5b3f96"; ACC = "#c0392b"
HM = "#b9a7e0"; PIN = "#c9bbe8"; FREE = "#e8e1f6"

S = []
def rr(x, y, w, h, fill=FILL, stroke=STROKE, sw=2, rx=12):
    S.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
def tx(x, y, s, size=15, color=BODY, w="normal", a="middle", it=0):
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    st = ' font-style="italic"' if it else ''
    S.append(f'<text x="{x}" y="{y}" font-family="Helvetica,Arial,sans-serif" font-size="{size}" fill="{color}" font-weight="{w}" text-anchor="{a}"{st}>{s}</text>')
def ln(x1, y1, x2, y2, color=ARR, sw=1.6, dash=0):
    d = ' stroke-dasharray="6 4"' if dash else ''
    S.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}"{d}/>')
def arr(x1, y1, x2, y2, color=ARR, sw=2.6, dash=0):
    d = ' stroke-dasharray="6 4"' if dash else ''
    S.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}" marker-end="url(#ah)"{d}/>')
def cell(cx, cy):
    S.append(f'<rect x="{cx-12}" y="{cy+7}" width="24" height="4" rx="2" fill="{HM}" stroke="{STROKE}" stroke-width="1"/>')
    S.append(f'<rect x="{cx-6}" y="{cy-1}" width="12" height="7" fill="{FREE}" stroke="{STROKE}" stroke-width="1"/>')
    S.append(f'<rect x="{cx-6}" y="{cy-10}" width="12" height="7" fill="{PIN}" stroke="{STROKE}" stroke-width="1"/>')
    S.append(f'<line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy+5}" stroke="{ACC}" stroke-width="1.2" marker-end="url(#ar)"/>')


def main():
    W, H = 1130, 700
    S.append(f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="Helvetica,Arial,sans-serif">')
    S.append('<defs>'
             f'<marker id="ah" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="{ARR}"/></marker>'
             f'<marker id="ar" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 z" fill="{ACC}"/></marker>'
             '</defs>')
    S.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="white"/>')
    tx(565, 46, "sMTJ p-bit / reservoir compute tile  —  module ↔ array coupling", 17, TITLE, "bold")

    AX, AY, AW, AH = 410, 270, 300, 200
    cols = [480, 560, 640]; rows = [330, 410]

    # ---- central array ----
    rr(AX, AY, AW, AH, "#f4f1fb")
    tx(AX + AW/2, AY + 24, "2T SOT-MTJ Array", 14, TITLE, "bold")
    tx(AX + AW/2, AY + 42, "N rows × M columns", 11, SUB, it=1)
    for cx in cols:
        ln(cx, AY + 52, cx, AY + AH - 8, STROKE, 1.2)
    for cy in rows:
        ln(AX + 14, cy, AX + AW - 14, cy, STROKE, 1.2)
    for cx in cols:
        for cy in rows:
            cell(cx, cy)

    # ---- write column drivers (top) ----
    rr(405, 95, 310, 95)
    tx(560, 122, "Write Column Drivers", 15, TITLE, "bold")
    tx(560, 146, "Write-DAC + IR-aware pre-distortion + CMOS driver", 12, BODY)
    tx(560, 168, "per column  (× M)", 11, SUB, it=1)

    # ---- row decoder + WL drivers (left) ----
    rr(80, 270, 235, 200)
    tx(197, 320, "Row Decoder", 15, TITLE, "bold")
    tx(197, 344, "+ WWL / RWL drivers", 12, BODY)
    tx(197, 392, "row select &", 11, SUB)
    tx(197, 410, "write/read enable", 11, SUB)
    tx(197, 440, "(per row, × N)", 11, SUB, it=1)

    # ---- column read-out (bottom) ----
    rr(405, 552, 310, 100)
    tx(560, 580, "Column Read-out", 15, TITLE, "bold")
    tx(560, 604, "R_TI + StrongARM  →  p-bit decision", 12, BODY)
    tx(560, 626, "column-shared SAR  →  reservoir (multi-bit)", 12, ACC, "bold")

    # ---- mode & timing controller (right) ----
    rr(800, 270, 252, 200)
    tx(926, 300, "Mode & Timing Controller", 14, TITLE, "bold")
    for i, t in enumerate(["• write / read phase sequencing",
                            "• p-bit  vs  reservoir mode mux",
                            "• T-sample averaging control",
                            "• column-share SAR select"]):
        tx(820, 332 + i*26, t, 12, BODY, a="start")

    # ---- coupling arrows (the point of the figure) ----
    arr(560, 190, 560, AY)                                   # write -> array
    tx(640, 232, "BL / SL", 12, BODY); tx(640, 250, "(write V)", 10, SUB, it=1)
    arr(560, AY + AH, 560, 552)                              # array -> read
    tx(642, 512, "RBL / SL", 12, BODY); tx(642, 530, "(read I)", 10, SUB, it=1)
    arr(315, 370, AX, 370)                                   # row -> array
    tx(362, 360, "WWL / RWL", 11, BODY)

    # ---- controller orchestration (dashed control) ----
    ln(800, 320, 745, 320, ARR, 1.6, dash=1); ln(745, 320, 745, 142, ARR, 1.6, dash=1); arr(745, 142, 716, 142, ARR, 2.2, dash=1)
    ln(800, 410, 745, 410, ARR, 1.6, dash=1); ln(745, 410, 745, 602, ARR, 1.6, dash=1); arr(745, 602, 716, 602, ARR, 2.2, dash=1)
    ln(800, 285, 800, 72, ARR, 1.6, dash=1); ln(800, 72, 197, 72, ARR, 1.6, dash=1); arr(197, 72, 197, 270, ARR, 2.2, dash=1)
    tx(905, 64, "control / clock phases (Φ_w, Φ_r)", 11, ARR, it=1)

    # column-share note
    tx(560, 672, "1 SAR shared across M columns via read mux;  two read modes time-multiplexed", 11, SUB, it=1)

    S.append('</svg>')
    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, "arch_tile.svg"), "w", encoding="utf-8").write("\n".join(S))
    print("wrote arch_tile.svg")


if __name__ == "__main__":
    main()
