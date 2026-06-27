#!/usr/bin/env python3
"""Generate a fully-wired Xschem schematic (.sch) for the StrongARM sense amplifier.

Canonical differential layout matching eda/hero/strongarm_sa_core.spice (11 devices): VDD rail on
top, VSS rail on bottom, two stacked legs (M5-M3-M1 | M6-M4-M2), tail at the bottom, four precharge
PMOS, and the cross-coupled latch drawn explicitly (outp -> left-leg gates, outn -> right-leg gates).
The distributed clock (precharge + tail gates) uses net labels, as is standard even in textbook
figures; everything structural is drawn as wires. Export with build_schematics.sh.

sky130 pins (rot 0): nfet D(20,-30) G(-20,0) S(20,30) B(20,0); pfet S(20,-30) G(-20,0) D(20,30) B(20,0).
"""
import os

NFET, PFET = "sky130_fd_pr/nfet_01v8.sym", "sky130_fd_pr/pfet_01v8.sym"
P = {"n": {"D": (20, -30), "G": (-20, 0), "S": (20, 30), "B": (20, 0)},
     "p": {"S": (20, -30), "G": (-20, 0), "D": (20, 30), "B": (20, 0)}}

# name, type, x, y, W   (y down)
DEV = [
    ("M5",  "p", 440, 240, 2), ("M6",  "p", 740, 240, 2),
    ("Mp2", "p", 240, 240, 2), ("Mp1", "p", 940, 240, 2),
    ("M3",  "n", 440, 480, 2), ("M4",  "n", 740, 480, 2),
    ("Mp3", "p", 120, 480, 2), ("Mp4", "p", 1060, 480, 2),
    ("M1",  "n", 440, 700, 4), ("M2",  "n", 740, 700, 4),
    ("Mtail", "n", 590, 900, 4),
]
DT = {n: t for n, t, *_ in DEV}
XY = {n: (x, y) for n, t, x, y, w in DEV}


def pin(name, p):
    x, y = XY[name]; dx, dy = P[DT[name]][p]
    return x + dx, y + dy


def main():
    o = ["v {xschem version=3.4.4 file_version=1.2}\nG {}\nK {}\nV {}\nS {}\nE {}\n"]
    for n, t, x, y, w in DEV:
        sym = NFET if t == "n" else PFET
        o.append("C {%s} %d %d 0 0 {name=%s model=sky130_fd_pr__%sfet_01v8 W=%g L=0.15 nf=1 m=1}\n"
                 % (sym, x, y, n, ("n" if t == "n" else "p"), w))
    W = []  # wire segments (x1,y1,x2,y2)
    VDD_Y, VSS_Y = 120, 1000
    W += [(120, VDD_Y, 1080, VDD_Y), (400, VSS_Y, 780, VSS_Y)]
    # PMOS sources up to VDD
    for n in ("M5", "M6", "Mp2", "Mp1", "Mp3", "Mp4"):
        px, py = pin(n, "S"); W.append((px, py, px, VDD_Y))
    # latch legs: outn (M5.D-M3.D), outp (M6.D-M4.D); da (M3.S-M1.D), db (M4.S-M2.D)
    W += [pin("M5", "D") + pin("M3", "D"), pin("M6", "D") + pin("M4", "D"),
          pin("M3", "S") + pin("M1", "D"), pin("M4", "S") + pin("M2", "D")]
    # precharge drains into the nodes (route down then across to the leg verticals)
    def join(src, legx, ymid):
        sx, sy = src; W.append((sx, sy, sx, ymid)); W.append((sx, ymid, legx, ymid))
    join(pin("Mp2", "D"), pin("M5", "D")[0], 330)     # -> outn
    join(pin("Mp1", "D"), pin("M6", "D")[0], 330)     # -> outp
    join(pin("Mp3", "D"), pin("M3", "S")[0], 560)     # -> da
    join(pin("Mp4", "D"), pin("M4", "S")[0], 560)     # -> db
    # ntail: M1.S + M2.S + Mtail.D
    s1, s2, td = pin("M1", "S"), pin("M2", "S"), pin("Mtail", "D")
    W += [(s1[0], s1[1], s1[0], 800), (s2[0], s2[1], s2[0], 800), (s1[0], 800, s2[0], 800),
          (td[0], 800, td[0], td[1])]
    W.append((pin("Mtail", "S")[0], pin("Mtail", "S")[1], pin("Mtail", "S")[0], VSS_Y))
    # cross-couple: outp -> M5.G & M3.G (left gate bus x=420); outn -> M6.G & M4.G (right gate bus x=700)
    lg = pin("M5", "G")[0]                              # 420
    W += [(lg, pin("M5", "G")[1], lg, pin("M3", "G")[1])]        # left gate bus
    rg = pin("M6", "G")[0]                              # 720-20=700
    W += [(rg, pin("M6", "G")[1], rg, pin("M4", "G")[1])]        # right gate bus
    W += [(pin("M6", "D")[0], 400, lg, 400)]            # outp(x=760) -> left gate bus (crosses rg = X)
    W += [(pin("M5", "D")[0], 300, rg, 300)]            # outn(x=460) -> right gate bus (crosses, X)
    # bulk ties: pmos & tail bulk -> source (short); nmos input/latch bulk -> VSS label
    for n in ("M5", "M6", "Mp2", "Mp1", "Mp3", "Mp4", "Mtail"):
        bx, by = pin(n, "B"); sx, sy = pin(n, "S"); W.append((bx, by, sx, sy))
    for seg in W:
        o.append("N %d %d %d %d {}\n" % seg)
    # labels: clk (distributed gates), nmos bulk = VSS, and IO pins
    def lab(sym, px, py, rot, nm, extra=""):
        o.append("C {devices/%s} %d %d 0 %d {name=%s %s}\n" % (sym, px, py, rot, nm, extra))
    nid = 0
    for n in ("Mp2", "Mp1", "Mp3", "Mp4", "Mtail"):
        nid += 1; gx, gy = pin(n, "G"); o.append("N %d %d %d %d {}\n" % (gx, gy, gx - 30, gy))
        lab("lab_pin.sym", gx - 30, gy, 2, "k%d" % nid, "lab=clk")
    for n in ("M3", "M4", "M1", "M2"):
        nid += 1; bx, by = pin(n, "B"); o.append("N %d %d %d %d {}\n" % (bx, by, bx + 25, by))
        lab("lab_pin.sym", bx + 25, by, 0, "b%d" % nid, "lab=VSS")
    # IO pins
    lab("ipin.sym", pin("M1", "G")[0] - 30, pin("M1", "G")[1], 2, "ivp", "lab=vinp")
    o.append("N %d %d %d %d {}\n" % (pin("M1", "G") + (pin("M1", "G")[0] - 30, pin("M1", "G")[1])))
    lab("ipin.sym", pin("M2", "G")[0] - 30, pin("M2", "G")[1], 2, "ivn", "lab=vinn")
    o.append("N %d %d %d %d {}\n" % (pin("M2", "G") + (pin("M2", "G")[0] - 30, pin("M2", "G")[1])))
    lab("opin.sym", pin("M5", "D")[0], 300, 0, "oon", "lab=outn")   # on the outn->rg wire
    lab("opin.sym", pin("M6", "D")[0], 400, 0, "oop", "lab=outp")   # on the outp->lg wire
    # name the supply rails
    o.append("N %d %d %d %d {}\n" % (120, VDD_Y, 120, VDD_Y - 30))
    lab("lab_pin.sym", 120, VDD_Y - 30, 1, "vddl", "lab=VDD")
    o.append("N %d %d %d %d {}\n" % (400, VSS_Y, 400, VSS_Y + 30))
    lab("lab_pin.sym", 400, VSS_Y + 30, 3, "vssl", "lab=VSS")
    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, "strongarm_sa.sch"), "w").write("".join(o))
    print("wrote strongarm_sa.sch: %d devices, %d wire segs" % (len(DEV), len(W)))


if __name__ == "__main__":
    main()
