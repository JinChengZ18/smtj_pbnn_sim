#!/usr/bin/env python3
"""Redraw Chapter-4 fig 4.1 as an architecture/dataflow diagram aligned to the ACTUAL EDA design.

Replaces the outdated block diagram (generic MRAM cylinders, vague "p=g(a)/(u) generator" write block,
no real read-out). Keeps the closed-loop forward dataflow but names each block with the circuit actually
designed and validated in sky130, and grounds the arrays with SOT-MTJ device icons:
  x(r) -> 2T SOT-MTJ XNOR-CIM array -> slope-matched read-out (R_TI+StrongARM | column-shared SAR)
       -> probability mapper + write path (R-string write-DAC, IR pre-distortion, CMOS driver)
       -> stochastic SOT-MTJ sampling array -> x(r+1) (loop back); read-out -> expectation averaging -> E[s].
Monochrome, exported via the same Xschem -> cairosvg pipeline as the transistor-level figures.
"""
import os


def main():
    o = ["v {xschem version=3.4.4 file_version=1.2}\nG {}\nK {}\nV {}\nS {}\nE {}\n"]

    def box(x1, y1, x2, y2):
        o.append("L 4 %d %d %d %d {}\n" % (x1, y1, x2, y1))
        o.append("L 4 %d %d %d %d {}\n" % (x2, y1, x2, y2))
        o.append("L 4 %d %d %d %d {}\n" % (x2, y2, x1, y2))
        o.append("L 4 %d %d %d %d {}\n" % (x1, y2, x1, y1))

    def txt(s, x, y, size=0.22):
        o.append("T {%s} %d %d 0 0 %g %g {}\n" % (s, x, y, size, size))

    def L(x1, y1, x2, y2):
        o.append("L 4 %d %d %d %d {}\n" % (x1, y1, x2, y2))

    def arrow(x1, y1, x2, y2):
        L(x1, y1, x2, y2)
        if y1 == y2 and x2 > x1:   L(x2 - 10, y2 - 5, x2, y2); L(x2 - 10, y2 + 5, x2, y2)
        elif y1 == y2 and x2 < x1: L(x2 + 10, y2 - 5, x2, y2); L(x2 + 10, y2 + 5, x2, y2)
        elif x1 == x2 and y2 > y1: L(x2 - 5, y2 - 10, x2, y2); L(x2 + 5, y2 - 10, x2, y2)
        elif x1 == x2 and y2 < y1: L(x2 - 5, y2 + 10, x2, y2); L(x2 + 5, y2 + 10, x2, y2)

    def mtj_icon(cx, cy):
        L(cx - 12, cy - 8, cx + 12, cy - 8); L(cx + 12, cy - 8, cx + 12, cy + 8)
        L(cx + 12, cy + 8, cx - 12, cy + 8); L(cx - 12, cy + 8, cx - 12, cy - 8)
        L(cx - 15, cy + 4, cx + 15, cy - 4)                     # free-layer tunability arrow
        L(cx, cy - 8, cx, cy - 20); L(cx, cy + 8, cx, cy + 20)  # leads (SOT track / read)

    # --- boxes ---
    box(40, 250, 200, 350)        # B1 input
    box(260, 220, 460, 390)       # B2 XNOR-CIM array
    box(520, 220, 740, 390)       # B3 read-out
    box(800, 215, 1020, 395)      # B4 mapper + write path
    box(1080, 220, 1290, 390)     # B5 sampling array
    box(520, 470, 740, 560)       # B6 expectation averaging
    box(1190, 478, 1300, 552)     # E[s] output

    # --- block labels ---
    txt("stochastic", 70, 290, 0.24); txt("input  x(r)", 70, 314, 0.24)
    txt("2T SOT-MTJ", 300, 246, 0.24); txt("XNOR-CIM array", 290, 270, 0.24)
    mtj_icon(320, 330); mtj_icon(400, 330)
    txt("I_col ~ S XNOR(x,w)", 282, 374, 0.18)
    txt("slope-matched", 560, 244, 0.24); txt("read-out", 560, 268, 0.24)
    txt("R_TI + StrongARM", 548, 300, 0.2); txt("(p-bit decision)", 556, 322, 0.18)
    txt("| column-shared SAR", 548, 350, 0.2); txt("(reservoir)", 568, 372, 0.18)
    txt("probability mapper", 820, 240, 0.22); txt("+ write path:", 820, 264, 0.22)
    txt("R-string write-DAC", 820, 300, 0.2)
    txt("IR pre-distortion", 820, 330, 0.2)
    txt("CMOS write driver", 820, 360, 0.2)
    txt("stochastic SOT-MTJ", 1100, 244, 0.22); txt("sampling array", 1110, 268, 0.22)
    mtj_icon(1150, 330); mtj_icon(1230, 330)
    txt("(thermal switching)", 1105, 374, 0.18)
    txt("expectation averaging", 540, 504, 0.22); txt("(T samples)", 575, 530, 0.2)
    txt("E[s]", 1218, 522, 0.3)

    # --- dataflow arrows ---
    arrow(200, 300, 260, 300); txt("x(r)", 208, 290, 0.18)
    arrow(460, 300, 520, 300); txt("I_col", 466, 290, 0.18)
    arrow(740, 305, 800, 305); txt("a", 760, 295, 0.18)
    arrow(1020, 305, 1080, 305); txt("write", 1026, 295, 0.18)
    arrow(630, 390, 630, 470); txt("T samples", 636, 426, 0.18)   # read-out -> averaging
    arrow(740, 515, 1190, 515)                                    # averaging -> E[s]
    # closed loop: sampling array x(r+1) -> back to input
    L(1290, 360, 1340, 360); L(1340, 360, 1340, 600); L(1340, 600, 120, 600)
    arrow(120, 600, 120, 350)
    txt("x(r+1)", 700, 586, 0.2)

    # title strip
    txt("sMTJ-PBNN closed-loop forward  (circuit-accurate architecture)", 300, 150, 0.26)

    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, "ch41_arch.sch"), "w").write("".join(o))
    print("wrote ch41_arch.sch")


if __name__ == "__main__":
    main()
