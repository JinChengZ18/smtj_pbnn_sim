#!/usr/bin/env python3
"""Generate a compact, journal-style Xschem schematic for the StrongARM sense amplifier.

Matches eda/hero/strongarm_sa_core.spice (11 devices). Rails, legs (M5/M3/M1 | M6/M4/M2), four
precharge PMOS, input pair and tail are drawn as wires; the cross-coupled latch is indicated by
outp/outn gate net-labels (the standard convention for a COMPACT differential latch -- a fully drawn
X requires routing room that defeats compactness). Devices use local symbols (sym/nfet.sym,
sym/pfet.sym = the sky130 symbols with the verbose model-name text stripped; name + W/L kept).
"""
import os

NFET, PFET = "sym/nfet.sym", "sym/pfet.sym"
P = {"n": {"D": (20, -30), "G": (-20, 0), "S": (20, 30), "B": (20, 0)},
     "p": {"S": (20, -30), "G": (-20, 0), "D": (20, 30), "B": (20, 0)}}
# compact layout (y down)
DEV = [
    ("M5", "p", 300, 210, 2), ("M6", "p", 520, 210, 2),
    ("Mp2", "p", 150, 210, 2), ("Mp1", "p", 670, 210, 2),
    ("M3", "n", 300, 380, 2), ("M4", "n", 520, 380, 2),
    ("Mp3", "p", 90, 380, 2), ("Mp4", "p", 730, 380, 2),
    ("M1", "n", 300, 540, 4), ("M2", "n", 520, 540, 4),
    ("Mtail", "n", 410, 690, 4),
]
DT = {n: t for n, t, *_ in DEV}
XY = {n: (x, y) for n, t, x, y, w in DEV}
VDD_Y, VSS_Y = 110, 790


def pin(n, p):
    x, y = XY[n]; dx, dy = P[DT[n]][p]; return x + dx, y + dy


def main():
    o = ["v {xschem version=3.4.4 file_version=1.2}\nG {}\nK {}\nV {}\nS {}\nE {}\n"]
    for n, t, x, y, w in DEV:
        o.append("C {%s} %d %d 0 0 {name=%s model=sky130_fd_pr__%sfet_01v8 W=%g L=0.15 nf=1 m=1}\n"
                 % (NFET if t == "n" else PFET, x, y, n, ("n" if t == "n" else "p"), w))
    W = [(70, VDD_Y, 750, VDD_Y), (300 + 20, VSS_Y, 520 + 20, VSS_Y)]
    for n in ("M5", "M6", "Mp2", "Mp1", "Mp3", "Mp4"):
        px, py = pin(n, "S"); W.append((px, py, px, VDD_Y))
    W += [pin("M5", "D") + pin("M3", "D"), pin("M6", "D") + pin("M4", "D"),
          pin("M3", "S") + pin("M1", "D"), pin("M4", "S") + pin("M2", "D")]

    def join(src, legx, ym):
        sx, sy = src; W.append((sx, sy, sx, ym)); W.append((sx, ym, legx, ym))
    join(pin("Mp2", "D"), pin("M5", "D")[0], 270); join(pin("Mp1", "D"), pin("M6", "D")[0], 270)
    join(pin("Mp3", "D"), pin("M3", "S")[0], 440); join(pin("Mp4", "D"), pin("M4", "S")[0], 440)
    s1, s2, td = pin("M1", "S"), pin("M2", "S"), pin("Mtail", "D")
    W += [(s1[0], s1[1], s1[0], 630), (s2[0], s2[1], s2[0], 630), (s1[0], 630, s2[0], 630),
          (td[0], 630, td[0], td[1]), (pin("Mtail", "S")[0], pin("Mtail", "S")[1], pin("Mtail", "S")[0], VSS_Y)]
    # pmos & tail bulk -> source (short tie)
    for n in ("M5", "M6", "Mp2", "Mp1", "Mp3", "Mp4", "Mtail"):
        bx, by = pin(n, "B"); sx, sy = pin(n, "S"); W.append((bx, by, sx, sy))
    for seg in W:
        o.append("N %d %d %d %d {}\n" % seg)

    nid = [0]
    def lab(px, py, rot, lab, sym="lab_pin.sym"):
        nid[0] += 1; o.append("C {sym/%s} %d %d 0 %d {name=l%d lab=%s}\n" % (sym, px, py, rot, nid[0], lab))

    def stublab(pinc, vec, rot, name, sym="lab_pin.sym"):
        px, py = pinc; ex, ey = px + vec[0], py + vec[1]
        o.append("N %d %d %d %d {}\n" % (px, py, ex, ey)); lab(ex, ey, rot, name, sym)

    # cross-couple via gate labels: left-leg gates=outp, right-leg gates=outn
    stublab(pin("M5", "G"), (-30, 0), 2, "outp"); stublab(pin("M3", "G"), (-30, 0), 2, "outp")
    stublab(pin("M6", "G"), (-30, 0), 2, "outn"); stublab(pin("M4", "G"), (-30, 0), 2, "outn")
    # clk on precharge + tail gates
    for n in ("Mp2", "Mp1", "Mp3", "Mp4", "Mtail"):
        stublab(pin(n, "G"), (-30, 0), 2, "clk")
    # nmos input/latch bulk -> VSS
    for n in ("M3", "M4", "M1", "M2"):
        stublab(pin(n, "B"), (25, 0), 0, "VSS", "gnd.sym")
    # IO + rails
    stublab(pin("M1", "G"), (-30, 0), 2, "vinp", "ipin.sym")
    stublab(pin("M2", "G"), (-30, 0), 2, "vinn", "ipin.sym")
    lab(pin("M5", "D")[0], 270, 0, "outn", "opin.sym")   # outn node (on Mp2 join)
    lab(pin("M6", "D")[0], 270, 0, "outp", "opin.sym")   # outp node
    stublab((70, VDD_Y), (0, -28), 1, "VDD", "vdd.sym"); stublab((300 + 20, VSS_Y), (0, 28), 3, "VSS", "gnd.sym")

    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, "strongarm_sa.sch"), "w").write("".join(o))
    print("wrote strongarm_sa.sch (compact, %d devices)" % len(DEV))


if __name__ == "__main__":
    main()
