#!/usr/bin/env python3
"""Polished redraw of Chapter-4 fig 4.1 (closed-loop forward dataflow), matching the original
diagram's design language (rounded lavender blocks, purple palette, MTJ cell glyphs, clean arrows)
but with circuit-accurate block contents aligned to the sky130 EDA design:
  Stochastic input -> 2T SOT-MTJ XNOR-CIM array -> {slope-matched read-out ; write path}
  -> stochastic SOT-MTJ sampling array -> x(r+1) (closed loop); read-out -> expectation -> E[s].
Authored as SVG (Xschem cannot match this polish) and rasterised with cairosvg.
"""
import os

# palette (purple family, matching the original)
FILL = "#ece9f6"; FILL2 = "#e0d8f1"; STROKE = "#6a4fa3"
TITLE = "#3f2a7a"; SUB = "#6a4fa3"; BODY = "#2b2b2b"; ARR = "#5b3f96"; ACC = "#c0392b"
HM = "#b9a7e0"; PIN = "#c9bbe8"; FREE = "#e8e1f6"

S = []
def rr(x, y, w, h, fill=FILL, stroke=STROKE, sw=2, rx=12):
    S.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
def tx(x, y, s, size=15, color=BODY, w="normal", a="middle", it=0):
    st = ' font-style="italic"' if it else ''
    S.append(f'<text x="{x}" y="{y}" font-family="Helvetica,Arial,sans-serif" font-size="{size}" fill="{color}" font-weight="{w}" text-anchor="{a}"{st}>{s}</text>')
def ln(x1, y1, x2, y2, color=ARR, sw=2):
    S.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}"/>')
def arr(x1, y1, x2, y2, color=ARR, sw=2.6):
    S.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}" marker-end="url(#ah)"/>')

def cell(cx, cy):
    # heavy-metal SOT track + free/pinned pillar + read lead + red switchable arrow
    S.append(f'<rect x="{cx-14}" y="{cy+8}" width="28" height="5" rx="2" fill="{HM}" stroke="{STROKE}" stroke-width="1.2"/>')
    S.append(f'<rect x="{cx-7}" y="{cy-2}" width="14" height="8" fill="{FREE}" stroke="{STROKE}" stroke-width="1.2"/>')
    S.append(f'<rect x="{cx-7}" y="{cy-12}" width="14" height="8" fill="{PIN}" stroke="{STROKE}" stroke-width="1.2"/>')
    ln(cx, cy - 12, cx, cy - 19, STROKE, 1.4)
    # free-layer switchable arrow (accent)
    S.append(f'<line x1="{cx}" y1="{cy-1}" x2="{cx}" y2="{cy+5}" stroke="{ACC}" stroke-width="1.4" marker-start="url(#ar)" marker-end="url(#ar)"/>')


def main():
    W, H = 1080, 600
    S.append(f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="Helvetica,Arial,sans-serif">')
    S.append('<defs>'
             f'<marker id="ah" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="{ARR}"/></marker>'
             f'<marker id="ar" markerWidth="7" markerHeight="7" refX="3.5" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7 z" fill="{ACC}"/></marker>'
             '</defs>')
    S.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="white"/>')

    MY = 280  # main-row vertical centre for arrows

    # ---- Box 1: stochastic input ----
    rr(24, 205, 140, 150)
    tx(94, 240, "Stochastic", 15, TITLE, "bold"); tx(94, 260, "Input", 15, TITLE, "bold")
    tx(94, 305, "x", 30, BODY, "bold", a="middle")
    S.append(f'<text x="106" y="296" font-family="Helvetica,Arial,sans-serif" font-size="16" fill="{BODY}">(r)</text>')

    # ---- Box 2: 2T SOT-MTJ XNOR-CIM array ----
    rr(200, 95, 270, 365)
    tx(335, 124, "2T SOT-MTJ XNOR-CIM Array", 15, TITLE, "bold")
    tx(335, 143, "(deterministic in-memory MAC)", 12, SUB, it=1)
    # BL/WL grid + 2x2 cell glyphs
    for cx in (288, 382):
        ln(cx, 175, cx, 360, STROKE, 1.4)                       # bit line
    for cy in (235, 320):
        ln(248, cy, 422, cy, STROKE, 1.4)                       # word line
    for cx in (288, 382):
        for cy in (235, 320):
            cell(cx, cy)
    tx(232, 180, "WL", 11, SUB, a="end"); tx(288, 170, "BL", 11, SUB); tx(382, 170, "SL", 11, SUB)
    # column-current sum
    arr(288, 360, 288, 392); arr(382, 360, 382, 392)
    tx(335, 414, "I_col  ∝  Σ XNOR(x, w)", 13, BODY)
    tx(335, 432, "(Kirchhoff popcount)", 11, SUB, it=1)

    # ---- Box 3: probability mapper + write path ----
    rr(510, 95, 270, 365)
    tx(645, 124, "Probability Mapper + Write Path", 15, TITLE, "bold")
    # sub-box A: read-out
    rr(528, 150, 234, 120, FILL2)
    tx(645, 174, "Slope-matched read-out", 13, TITLE, "bold")
    tx(645, 198, "R_TI  +  StrongARM  (p-bit)", 12, BODY)
    tx(645, 220, "| column-shared SAR", 12, BODY)
    tx(645, 242, "(reservoir, multi-bit)", 11, SUB, it=1)
    tx(645, 262, "digitise  I_col  →  a", 11, SUB)
    # mapping arrow A -> B
    arr(645, 270, 645, 300); tx(700, 290, "p = g(a)", 12, BODY)
    # sub-box B: write path
    rr(528, 300, 234, 142, FILL2)
    tx(645, 324, "Write path", 13, TITLE, "bold")
    tx(645, 348, "R-string write-DAC", 12, BODY)
    tx(645, 372, "IR-aware pre-distortion", 12, ACC, "bold")
    tx(645, 396, "CMOS write driver", 12, BODY)
    tx(645, 422, "→ write stimulus u", 11, SUB)

    # ---- Box 4: stochastic SOT-MTJ sampling array ----
    rr(820, 95, 236, 365)
    tx(938, 124, "Stochastic SOT-MTJ", 15, TITLE, "bold")
    tx(938, 143, "Sampling Array", 15, TITLE, "bold")
    tx(938, 161, "(thermal switching)", 12, SUB, it=1)
    for k, cy in enumerate((215, 285)):
        # write pulse glyph
        S.append(f'<path d="M848,{cy+6} h10 v-14 h10 v14 h8" fill="none" stroke="{ARR}" stroke-width="1.6"/>')
        cell(905, cy)
        # thermal-noise squiggle
        S.append(f'<path d="M945,{cy} q6,-9 12,0 t12,0 t12,0" fill="none" stroke="{ACC}" stroke-width="1.6"/>')
    tx(938, 250, "P_sw(V, t)", 11, SUB)
    rr(842, 345, 192, 88, FILL2)
    tx(938, 372, "New Stochastic State", 12, TITLE, "bold")
    tx(938, 398, "x", 20, BODY, "bold")
    S.append(f'<text x="950" y="392" font-family="Helvetica,Arial,sans-serif" font-size="12" fill="{BODY}">(r+1)</text>')
    tx(938, 420, "~ 2·Bernoulli(p) − 1", 11, SUB)

    # ---- Box 5: expectation averaging ----
    rr(510, 498, 270, 74)
    tx(645, 526, "Expectation Averaging", 14, TITLE, "bold")
    tx(645, 550, "(spatial / temporal, T samples)", 12, SUB, it=1)

    # ---- arrows between blocks ----
    arr(164, MY, 200, MY); tx(182, MY - 8, "x(r)", 11, BODY)
    arr(470, MY, 510, MY); tx(490, MY - 8, "I_col", 11, BODY)
    arr(780, MY, 820, MY); tx(800, MY - 8, "u", 11, BODY)
    # read-out -> expectation
    arr(645, 460, 645, 498); tx(700, 484, "T samples", 11, BODY)
    # expectation -> E[s]
    arr(780, 535, 858, 535); tx(905, 540, "≈ E[s]", 18, TITLE, "bold")
    # closed loop x(r+1) -> input
    ln(938, 460, 938, 585); ln(938, 585, 94, 585); arr(94, 585, 94, 355)
    tx(516, 578, "x(r+1)   (closed-loop feedback)", 12, ACC)

    S.append('</svg>')
    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, "ch41_polished.svg"), "w", encoding="utf-8").write("\n".join(S))
    print("wrote ch41_polished.svg")


if __name__ == "__main__":
    main()
