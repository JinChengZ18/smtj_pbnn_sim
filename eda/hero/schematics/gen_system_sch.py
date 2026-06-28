#!/usr/bin/env python3
"""Generate the COMBINED full-system schematic: one sMTJ p-bit / reservoir compute lane.

This is the true transistor-level integration (replacing the old block-diagram architecture):
  write-DAC -> CMOS write driver -> write line (BL) -> 2T SOT-MTJ cell -> source line (SL),
  and on read: RBL -> transimpedance R_TI -> StrongARM comparator (p-bit decision) with a
  column-shared SAR tapping the same column for reservoir read-out. The bit-cell, the write
  driver, the transimpedance resistor and the comparator are drawn at device level; the deep
  sub-blocks already detailed in their own figures (write-DAC string, SAR logic) are shown as
  labelled blocks with real I/O nets. Array multiplicity (rows/columns) is annotated.
Symbols: sym/{nfet,pfet,res,comp,sot_mtj}.sym + devices/{vdd,gnd,ipin,opin,lab_pin}.sym.
"""
import os

NFET, PFET, RES, COMP, SOT = "sym/nfet.sym", "sym/pfet.sym", "sym/res.sym", "sym/comp.sym", "sym/sot_mtj.sym"
PINS = {"n": {"D": (20, -30), "G": (-20, 0), "S": (20, 30), "B": (20, 0)},
        "p": {"S": (20, -30), "G": (-20, 0), "D": (20, 30), "B": (20, 0)},
        "r": {"P": (0, -30), "M": (0, 30)},
        "comp": {"INP": (-40, -15), "INN": (-40, 15), "OUT": (45, 0)},
        "sot": {"Tin": (-40, 20), "Tsl": (40, 20), "Trd": (0, -40)}}

# (name, type, x, y, rot)
DEV = [
    ("MDp", "p", 320, 360, 0), ("MDn", "n", 320, 460, 0),   # CMOS write driver (inverter)
    ("MW", "n", 560, 420, 1),                                # write-access FET (rot1: in-line)
    ("MR", "n", 680, 330, 0),                                # read-access FET
    ("X1", "sot", 700, 420, 0),                              # 2T SOT-MTJ cell
    ("Rti", "r", 700, 250, 0),                               # transimpedance R_TI
    ("CMP", "comp", 920, 320, 0),                            # StrongARM comparator (p-bit)
]
DT = {n: t for n, t, *_ in DEV}
XY = {n: (x, y) for n, t, x, y, r in DEV}
ROT = {n: r for n, t, x, y, r in DEV}


def _rot(dx, dy, r):
    return [(dx, dy), (-dy, dx), (-dx, -dy), (dy, -dx)][r]


def pin(n, p):
    x, y = XY[n]; dx, dy = _rot(*PINS[DT[n]][p], ROT[n]); return x + dx, y + dy


def main():
    o = ["v {xschem version=3.4.4 file_version=1.2}\nG {}\nK {}\nV {}\nS {}\nE {}\n"]
    sz = {"MDp": 8, "MDn": 4, "MW": 3, "MR": 2}
    for n, t, x, y, r in DEV:
        if t in ("n", "p"):
            o.append("C {%s} %d %d 0 %d {name=%s model=sky130_fd_pr__%sfet_01v8 W=%g L=0.15 nf=1 m=1}\n"
                     % (NFET if t == "n" else PFET, x, y, r, n, t, sz[n]))
        elif t == "r":
            o.append("C {%s} %d %d 0 %d {name=%s value=R_TI}\n" % (RES, x, y, r, n))
        elif t == "comp":
            o.append("C {%s} %d %d 0 %d {name=%s}\n" % (COMP, x, y, r, n))
        elif t == "sot":
            o.append("C {%s} %d %d 0 %d {name=%s}\n" % (SOT, x, y, r, n))

    W = []
    # --- write-DAC block output -> driver input bus -> both gates ---
    W += [(240, 420, 280, 420), (280, 360, 280, 460), (280, 360, 300, 360), (280, 460, 300, 460)]
    # --- driver rails / bulks / output ---
    W += [(340, 330, 340, 300), (340, 360, 340, 330)]       # MDp.S->VDD, MDp.B->S
    W += [(340, 460, 340, 490), (340, 490, 340, 520)]       # MDn.B->S, MDn.S->GND
    W += [(340, 390, 340, 430)]                             # driver output node
    # --- BL: driver out -> write-access source ; MW.D -> Tin ; SL ---
    W += [(340, 430, 340, 440), (340, 440, 530, 440)]       # BL
    W += [(590, 440, 660, 440)]                             # MW.D -> Tin
    W += [(740, 440, 740, 560)]                             # Tsl -> SL
    # --- read: MR -> Trd ; RBL node ; R_TI -> VREF ; sense -> comparator ; SAR tap ---
    W += [(700, 360, 700, 380)]                             # MR.S -> Trd
    W += [(700, 300, 700, 280)]                             # RBL node -> Rti.M
    W += [(700, 220, 700, 190)]                             # Rti.P -> VREF
    W += [(700, 300, 880, 300), (880, 300, 880, 305)]       # sense -> CMP.INP
    W += [(820, 300, 820, 450)]                             # sense tap -> SAR block
    W += [(965, 320, 1000, 320)]                            # CMP.OUT -> p-bit out
    for seg in W:
        o.append("N %d %d %d %d {}\n" % seg)

    def box(x1, y1, x2, y2):
        o.append("L 4 %d %d %d %d {}\n" % (x1, y1, x2, y1))
        o.append("L 4 %d %d %d %d {}\n" % (x2, y1, x2, y2))
        o.append("L 4 %d %d %d %d {}\n" % (x2, y2, x1, y2))
        o.append("L 4 %d %d %d %d {}\n" % (x1, y2, x1, y1))

    box(80, 380, 240, 460)                                  # write-DAC block
    box(790, 450, 1030, 570)                                # column-shared SAR block
    o.append("N 790 530 750 530 {}\n")                      # SAR CLK stub
    o.append("N 1030 520 1065 520 {}\n")                    # SAR code-out stub

    nid = [0]
    def lab(px, py, rot, name, sym="lab_pin.sym"):
        nid[0] += 1
        o.append("C {sym/%s} %d %d 0 %d {name=l%d lab=%s}\n" % (sym, px, py, rot, nid[0], name))

    def stublab(pc, vec, rot, name, sym="lab_pin.sym"):
        px, py = pc; ex, ey = px + vec[0], py + vec[1]
        o.append("N %d %d %d %d {}\n" % (px, py, ex, ey)); lab(ex, ey, rot, name, sym)

    def txt(s, x, y, size=0.3):
        o.append("T {%s} %d %d 0 0 %g %g {}\n" % (s, x, y, size, size))

    # supplies / refs
    lab(340, 300, 0, "VDD", "vdd.sym")
    lab(340, 520, 0, "GND", "gnd.sym")
    lab(700, 190, 1, "VREF", "ipin.sym")
    stublab(pin("MW", "B"), (0, 25), 0, "GND", "gnd.sym")
    stublab(pin("MR", "B"), (45, 0), 0, "GND", "gnd.sym")
    stublab(pin("CMP", "INN"), (-40, 0), 2, "VCM", "ipin.sym")
    lab(740, 560, 0, "SL", "lab_pin.sym")
    # word lines (from row decoder/driver) + cell I/O
    stublab(pin("MW", "G"), (0, -40), 1, "WWL", "ipin.sym")
    stublab(pin("MR", "G"), (-55, 0), 2, "RWL", "ipin.sym")
    lab(1000, 320, 0, "p_out", "opin.sym")
    lab(750, 530, 2, "CLK", "ipin.sym")
    lab(1065, 520, 0, "rc", "opin.sym")
    # net names
    txt("BL", 440, 428, 0.22)
    txt("RBL", 716, 306, 0.22)
    # block labels
    txt("write-DAC", 110, 412, 0.26)
    txt("R-string + IR", 96, 436, 0.22)
    txt("column-shared SAR", 830, 505, 0.28)
    txt("(reservoir read-out)", 835, 532, 0.22)
    # functional annotations
    txt("CMOS write driver", 250, 300, 0.26)
    txt("2T SOT-MTJ cell", 600, 490, 0.26)
    txt("R_TI (TIA)", 724, 248, 0.24)
    txt("StrongARM comparator", 855, 250, 0.26)
    txt("(p-bit read-out)", 875, 274, 0.22)
    txt("sMTJ p-bit / reservoir compute lane", 360, 110, 0.34)
    txt("x N rows (shared BL / SL / RBL)   .   x M columns (WWL / RWL shared; SAR shared across columns)",
        180, 620, 0.24)

    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, "system_lane.sch"), "w").write("".join(o))
    print("wrote system_lane.sch (%d devices + 2 blocks)" % len(DEV))


if __name__ == "__main__":
    main()
