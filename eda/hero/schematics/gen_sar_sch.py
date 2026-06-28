#!/usr/bin/env python3
"""Generate a compact, journal-style Xschem schematic for the COLUMN-SHARED SAR READOUT.

Topology (matches the column-shared, time-multiplexed SAR readout in sar_capdac_energy.py /
rc_isoenergy.py): several column taps are time-multiplexed by sample switches onto a single
charge-redistribution capacitive DAC (binary-weighted top plates on the shared node Vx, bottom
plates steered to VREF/GND by the SAR bit switches); a StrongARM comparator (drawn as the standard
comparator triangle -- its transistor-level netlist is the separate StrongARM figure) resolves Vx
against VCM; the SAR logic drives the bit switches and emits the code. One comparator + one cap-DAC
are amortised across columns -- the energy lever quantified in the reservoir-readout study.
"""
import os

NFET, CAP, SW, COMP = "sym/nfet.sym", "sym/cap.sym", "sym/sw.sym", "sym/comp.sym"
P = {"n": {"D": (20, -30), "G": (-20, 0), "S": (20, 30), "B": (20, 0)},
     "cap": {"P": (0, -30), "M": (0, 30)},
     "sw": {"C": (0, -25), "A": (-12, 25), "B": (12, 25)},
     "comp": {"INP": (-40, -15), "INN": (-40, 15), "OUT": (45, 0)}}

# (name, type, x, y)
DEV = [
    ("MS0", "n", 160, 110), ("MS1", "n", 280, 110),         # column-share sample switches
    ("C2", "cap", 420, 240), ("C1", "cap", 540, 240), ("C0", "cap", 660, 240),  # binary cap-DAC
    ("S2", "sw", 420, 330), ("S1", "sw", 540, 330), ("S0", "sw", 660, 330),     # bit ref switches
    ("CMP", "comp", 880, 210),                               # StrongARM comparator (triangle)
]
DT = {n: t for n, t, *_ in DEV}
XY = {n: (x, y) for n, t, x, y in DEV}
CAPVAL = {"C2": "4C", "C1": "2C", "C0": "C"}


def pin(n, p):
    x, y = XY[n]; dx, dy = P[DT[n]][p]; return x + dx, y + dy


def main():
    o = ["v {xschem version=3.4.4 file_version=1.2}\nG {}\nK {}\nV {}\nS {}\nE {}\n"]
    for n, t, x, y in DEV:
        if t == "n":
            o.append("C {%s} %d %d 0 0 {name=%s model=sky130_fd_pr__nfet_01v8 W=2 L=0.15 nf=1 m=1}\n"
                     % (NFET, x, y, n))
        elif t == "cap":
            o.append("C {%s} %d %d 0 0 {name=%s value=%s}\n" % (CAP, x, y, n, CAPVAL[n]))
        elif t == "sw":
            bit = {"S2": "b2", "S1": "b1", "S0": "b0"}[n]
            o.append("C {%s} %d %d 0 0 {name=%s}\n" % (SW, x, y, bit))
        elif t == "comp":
            o.append("C {%s} %d %d 0 0 {name=%s}\n" % (COMP, x, y, n))

    W = []
    # --- column inputs -> sample switches -> shared top-plate node Vx ---
    W += [(180, 50, 180, 80), (180, 140, 180, 180)]          # col0 -> MS0 -> Vx
    W += [(300, 50, 300, 80), (300, 140, 300, 180)]          # col1 -> MS1 -> Vx
    W += [(180, 180, 760, 180)]                              # Vx bus
    # --- cap top plates -> Vx ---
    for cx in (420, 540, 660):
        W += [(cx, 180, cx, 210)]
    # --- cap bottom plates -> bit switch common ---
    for cx in (420, 540, 660):
        W += [(cx, 270, cx, 305)]
    # --- bit switches -> VREF rail (throw A) and GND rail (throw B) ---
    for cx in (420, 540, 660):
        W += [(cx - 12, 355, cx - 12, 400)]                  # throwA -> VREF rail
        W += [(cx + 12, 355, cx + 12, 445)]                  # throwB -> GND rail (crosses VREF, no-connect)
    W += [(404, 400, 720, 400)]                              # VREF rail
    W += [(404, 445, 700, 445)]                              # GND rail
    # --- Vx -> comparator INP ; comparator OUT -> SAR logic ---
    W += [(760, 180, 820, 180), (820, 180, 820, 195), (820, 195, 840, 195)]
    W += [(925, 210, 925, 300)]                              # OUT -> SAR box top
    for seg in W:
        o.append("N %d %d %d %d {}\n" % seg)

    # --- SAR logic box (rectangle + ports) ---
    o.append("L 4 860 300 1010 300 {}\n")
    o.append("L 4 1010 300 1010 430 {}\n")
    o.append("L 4 1010 430 860 430 {}\n")
    o.append("L 4 860 430 860 300 {}\n")
    o.append("N 860 330 820 330 {}\n")                       # CLK stub
    o.append("N 1010 360 1055 360 {}\n")                     # Dout stub
    o.append("N 860 400 820 400 {}\n")                       # b[2:0] stub

    nid = [0]
    def lab(px, py, rot, name, sym="lab_pin.sym"):
        nid[0] += 1
        o.append("C {sym/%s} %d %d 0 %d {name=l%d lab=%s}\n" % (sym, px, py, rot, nid[0], name))

    def stublab(pc, vec, rot, name, sym="lab_pin.sym"):
        px, py = pc; ex, ey = px + vec[0], py + vec[1]
        o.append("N %d %d %d %d {}\n" % (px, py, ex, ey)); lab(ex, ey, rot, name, sym)

    def txt(s, x, y, size=0.3, layer=None):
        tag = "{layer=%d}" % layer if layer else "{}"
        o.append("T {%s} %d %d 0 0 %g %g %s\n" % (s, x, y, size, size, tag))

    # ports / nets
    lab(180, 50, 1, "col0", "ipin.sym")
    lab(300, 50, 1, "col1", "ipin.sym")
    stublab(pin("MS0", "G"), (-25, 0), 2, "sel0")
    stublab(pin("MS1", "G"), (-25, 0), 2, "sel1")
    stublab(pin("MS0", "B"), (25, 0), 0, "GND", "gnd.sym")
    stublab(pin("MS1", "B"), (25, 0), 0, "GND", "gnd.sym")
    lab(720, 400, 0, "VREF")
    lab(700, 445, 0, "GND", "gnd.sym")
    stublab(pin("CMP", "INN"), (-40, 0), 2, "VCM", "ipin.sym")
    lab(820, 330, 2, "CLK", "ipin.sym")
    lab(1055, 360, 0, "Dout", "opin.sym")
    lab(820, 400, 2, "b[2:0]")
    # internal node names
    txt("Vx", 470, 168, 0.22)
    txt("cmp", 935, 250, 0.22)
    txt("SAR logic", 888, 360, 0.3)
    # functional group annotations
    txt("column-shared", 20, 22, 0.26)
    txt("input mux", 20, 44, 0.26)
    txt("(time-mux)", 20, 66, 0.24)
    txt("charge-redistribution cap-DAC (binary-weighted, b bits)", 380, 132, 0.26)
    txt("ref switches: VREF / GND per bit", 410, 490, 0.24)
    txt("StrongARM comparator", 820, 120, 0.28)
    txt("-> shared comparator + DAC amortised across columns", 470, 540, 0.24, layer=7)

    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, "sar_readout.sch"), "w").write("".join(o))
    print("wrote sar_readout.sch (%d devices + SAR box)" % len(DEV))


if __name__ == "__main__":
    main()
