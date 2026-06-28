#!/usr/bin/env python3
"""Architecture figure: exploded device -> cell/array -> CMOS periphery -> system hierarchy.

Follows the field convention (stacked / exploded hierarchy for heterogeneous spintronic+CMOS
integration; cf. eda/research/2026-06-28_figure_conventions.md) rather than a flat floorplan that
reads as a simplified schematic. Four tiers left-to-right -- SOT-MTJ device (entropy+compute) ->
2T XNOR-CIM array -> sky130 CMOS periphery (the EDA-designed blocks) -> operating modes -- with a
bottom band mapping each tier to its abstraction layer and its sky130 grounding. One accent colour
(red) marks the stochastic free layer and the sky130-extracted periphery. Rasterised via cairosvg.
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
def arrow(x1, y1, x2, y2, color=ARR, sw=3, dash=0):
    d = ' stroke-dasharray="6 4"' if dash else ''
    S.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}" marker-end="url(#ah)"{d}/>')

def cellglyph(cx, cy):
    S.append(f'<rect x="{cx-11}" y="{cy+6}" width="22" height="4" rx="2" fill="{HM}" stroke="{STROKE}" stroke-width="1"/>')
    S.append(f'<rect x="{cx-5}" y="{cy-1}" width="10" height="6" fill="{FREE}" stroke="{STROKE}" stroke-width="1"/>')
    S.append(f'<rect x="{cx-5}" y="{cy-9}" width="10" height="6" fill="{PIN}" stroke="{STROKE}" stroke-width="1"/>')
    S.append(f'<line x1="{cx}" y1="{cy-1}" x2="{cx}" y2="{cy+4}" stroke="{ACC}" stroke-width="1.2"/>')

def devstack(cx, cy):
    # heavy-metal SOT track
    S.append(f'<rect x="{cx-42}" y="{cy+30}" width="84" height="13" rx="3" fill="{HM}" stroke="{STROKE}" stroke-width="1.6"/>')
    for k in range(-3, 4):
        ln(cx + k*12, cy + 43, cx + k*12 - 5, cy + 51, STROKE, 1)
    ln(cx - 58, cy + 36, cx - 42, cy + 36, STROKE, 1.6); ln(cx + 42, cy + 36, cx + 58, cy + 36, STROKE, 1.6)
    tx(cx - 64, cy + 40, "T1", 11, SUB, a="end"); tx(cx + 64, cy + 40, "T2", 11, SUB, a="start")
    # free layer (switchable, accent) adjacent to the track
    S.append(f'<rect x="{cx-20}" y="{cy+6}" width="40" height="22" fill="{FREE}" stroke="{STROKE}" stroke-width="1.6"/>')
    S.append(f'<line x1="{cx}" y1="{cy+10}" x2="{cx}" y2="{cy+24}" stroke="{ACC}" stroke-width="2" marker-start="url(#ar)" marker-end="url(#ar)"/>')
    tx(cx + 50, cy + 21, "free (switchable)", 10, ACC, a="start")
    # tunnel barrier + pinned
    ln(cx - 20, cy + 4, cx + 20, cy + 4, STROKE, 2)
    tx(cx + 50, cy + 2, "MgO barrier", 10, SUB, a="start")
    S.append(f'<rect x="{cx-20}" y="{cy-22}" width="40" height="24" fill="{PIN}" stroke="{STROKE}" stroke-width="1.6"/>')
    S.append(f'<line x1="{cx-9}" y1="{cy-10}" x2="{cx+9}" y2="{cy-10}" stroke="{STROKE}" stroke-width="2" marker-end="url(#ahs)"/>')
    tx(cx + 50, cy - 12, "pinned (fixed)", 10, SUB, a="start")
    # read terminal
    ln(cx, cy + 28, cx, cy + 30, STROKE, 1.6)
    ln(cx, cy - 22, cx, cy - 46, STROKE, 1.6); tx(cx, cy - 52, "read", 10, SUB)


def main():
    W, H = 1250, 720
    S.append(f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="Helvetica,Arial,sans-serif">')
    S.append('<defs>'
             f'<marker id="ah" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="{ARR}"/></marker>'
             f'<marker id="ahs" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="{STROKE}"/></marker>'
             f'<marker id="ar" markerWidth="7" markerHeight="7" refX="3.5" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7 z" fill="{ACC}"/></marker>'
             '</defs>')
    S.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="white"/>')
    tx(625, 40, "sMTJ p-bit / reservoir compute architecture", 18, TITLE, "bold")
    tx(625, 62, "device  →  XNOR-CIM array  →  sky130 CMOS periphery  →  system", 13, SUB, it=1)

    YT, YB = 95, 455          # tier band
    MY = 300                  # arrow row

    # ---- Tier 1: device ----
    rr(36, YT, 200, YB - YT)
    tx(136, YT + 26, "SOT-MTJ device", 15, TITLE, "bold")
    tx(136, YT + 45, "(entropy + compute)", 11, SUB, it=1)
    devstack(136, 250)
    tx(136, 408, "P_sw(V) = σ((V−V_th)/V_T)", 11, BODY)
    tx(136, 428, "thermal stochastic switching", 10, SUB, it=1)

    # ---- Tier 2: array ----
    rr(300, YT, 230, YB - YT)
    tx(415, YT + 26, "2T SOT-MTJ XNOR-CIM", 14, TITLE, "bold")
    tx(415, YT + 45, "array  (N rows × M cols)", 11, SUB, it=1)
    cols = [360, 415, 470]; rows = [210, 285, 360]
    for cx in cols:
        ln(cx, 185, cx, 388, STROKE, 1.1)
    for cy in rows:
        ln(338, cy, 492, cy, STROKE, 1.1)
    for cx in cols:
        for cy in rows:
            cellglyph(cx, cy)
    tx(415, 415, "I_col ∝ Σ XNOR(x, w)", 12, BODY); tx(415, 433, "Kirchhoff popcount", 10, SUB, it=1)

    # ---- Tier 3: CMOS periphery ----
    rr(594, YT, 380, YB - YT)
    tx(784, YT + 24, "sky130 CMOS periphery", 15, TITLE, "bold")
    rr(610, YT + 40, 348, 58, FILL2)
    tx(784, YT + 62, "write path", 12, TITLE, "bold")
    tx(784, YT + 82, "R-string DAC · IR pre-distortion · CMOS driver  → BL/SL", 11, BODY)
    rr(610, YT + 106, 348, 70, FILL2)
    tx(784, YT + 127, "read path", 12, TITLE, "bold")
    tx(784, YT + 147, "TIA + StrongARM  → p-bit", 11, BODY)
    tx(784, YT + 165, "| column-shared SAR  → reservoir   ← RBL", 11, BODY)
    rr(610, YT + 184, 168, 56, FILL2)
    tx(694, YT + 206, "row / col decode", 11, TITLE, "bold"); tx(694, YT + 224, "+ WL drivers", 10, BODY)
    rr(790, YT + 184, 168, 56, FILL2)
    tx(874, YT + 206, "mode & timing", 11, TITLE, "bold"); tx(874, YT + 224, "controller", 10, BODY)
    tx(784, YB - 12, "couples to the array via BL/SL · WWL/RWL · RBL", 10, SUB, it=1)

    # ---- Tier 4: system / modes ----
    rr(1038, YT, 176, YB - YT)
    tx(1126, YT + 26, "operating modes", 14, TITLE, "bold")
    tx(1126, YT + 45, "(time-multiplexed)", 11, SUB, it=1)
    rr(1052, YT + 64, 148, 92, FILL2)
    tx(1126, YT + 88, "p-bit inference", 12, TITLE, "bold")
    tx(1126, YT + 110, "T Bernoulli", 11, BODY); tx(1126, YT + 128, "samples → E[s]", 11, BODY)
    rr(1052, YT + 168, 148, 100, FILL2)
    tx(1126, YT + 192, "reservoir", 12, TITLE, "bold")
    tx(1126, YT + 214, "low-Δ free", 11, BODY); tx(1126, YT + 232, "evolution →", 11, BODY)
    tx(1126, YT + 250, "shared read-out", 11, BODY)

    # ---- inter-tier arrows + closed loop ----
    arrow(236, MY, 300, MY); arrow(530, MY, 594, MY); arrow(974, MY, 1038, MY)
    tx(268, MY - 8, "cell", 10, BODY); tx(562, MY - 8, "I_col", 10, BODY); tx(1006, MY - 8, "code", 10, BODY)
    ln(1126, YT, 1126, 78, ARR, 1.6, dash=1); ln(1126, 78, 415, 78, ARR, 1.6, dash=1); arrow(415, 78, 415, YT, ARR, 2.2, dash=1)
    tx(770, 74, "closed-loop sampling  x(r+1)", 11, ACC, it=1)

    # ---- bottom band: abstraction <-> sky130 grounding ----
    tx(40, 506, "abstraction layer  ↔  grounding:", 12, TITLE, "bold", a="start")
    bands = [(36, 200, "device", "wafer-calibrated compact model + LLG cross-check", 0),
             (300, 230, "array", "behavioural XNOR-CIM, T-step unroll", 0),
             (594, 380, "periphery", "sky130 EXTRACTED — StrongARM read 48 fJ · write-line IR · SAR cap-DAC", 1),
             (1038, 176, "system", "PPA energy / latency model", 0)]
    for x, w, lab, desc, grounded in bands:
        rr(x, 520, w, 70, "#f4f1fb" if not grounded else "#fbecec",
           ACC if grounded else STROKE, 2)
        tx(x + w/2, 543, lab, 12, ACC if grounded else TITLE, "bold")
        # wrap desc into <=2 lines
        words = desc.split("  ·  ") if "  ·  " in desc else [desc]
        if len(desc) > 34 and len(words) == 1:
            mid = desc.rfind(" ", 0, 36)
            words = [desc[:mid], desc[mid+1:]]
        for i, wln in enumerate(words[:2]):
            tx(x + w/2, 563 + i*16, wln, 9.5, BODY if not grounded else ACC)

    S.append('</svg>')
    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, "arch_stack.svg"), "w", encoding="utf-8").write("\n".join(S))
    print("wrote arch_stack.svg")


if __name__ == "__main__":
    main()
