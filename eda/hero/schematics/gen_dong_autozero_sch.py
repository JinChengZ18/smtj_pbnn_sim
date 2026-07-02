#!/usr/bin/env python3
"""Generate a compact, journal-style Xschem schematic for the single-capacitor
auto-zeroed StrongARM sense amplifier (Dong lineage), matching
eda/hero/comparators/dong_autozero.spice -- 23 transistors + 2 offset-storage caps.

Three sections, left to right:
  1. offset-storage front end: per side, an azb-gated input switch (XSi*) and an
     az-gated vcm switch (XSc*) onto the cap top plate (tp*); the 60 fF cap (Cc*)
     stores the offset on the floating gate node gi*.
  2. auto-zero loop: azb-gated PMOS header XPz + PMOS diodes XPd1/XPd2 (finite-gain
     load on da/db during AZ), unity-feedback switches XSf1/XSf2 (da/db -> gi1/gi2)
     and the az-gated AZ tail XMtz (ntail).
  3. StrongARM core: cross-coupled latch XM3-XM6 with clk precharge XMp1/XMp2,
     clk-gated isolation switches XI1/XI2 (s3/s4 -> da/db), input pair XM1/XM2,
     pcn-gated da/db precharge XMp3/XMp4 and the clk tail XMtail.

The testbench Vo* offset-injection sources and the local az/azb/pcn pulse sources
are NOT drawn (instrumentation); gates carry their signal nets (az, azb, pcn, clk,
gi1/gi2, outp/outn). Following the house convention (cf. gen_strongarm_sch.py),
the latch cross-couple and the block-to-block nets da/db/gi1/gi2/ntail are routed
by net labels instead of long wrap-around wires. All devices use the local cleaned
sky130 symbols (sym/nfet.sym, sym/pfet.sym, sym/cap.sym).
"""
import os

NFET, PFET, CAP = "sym/nfet.sym", "sym/pfet.sym", "sym/cap.sym"
# pin offsets (rot 0), from the symbol bounding boxes
P = {"n": {"D": (20, -30), "G": (-20, 0), "S": (20, 30), "B": (20, 0)},
     "p": {"S": (20, -30), "G": (-20, 0), "D": (20, 30), "B": (20, 0)}}

VDD_Y, VSS_Y = 110, 870

# (name, type, x, y, W)   -- W per dong_autozero.spice (win default 4.0 for XM1/XM2)
DEV = [
    # ---- 1. offset-storage front end (input + vcm switches, one row per side) ----
    ("XSi1", "n", 150, 210, 8), ("XSc1", "n", 310, 210, 2),
    ("XSi2", "n", 150, 500, 8), ("XSc2", "n", 310, 500, 2),
    # ---- 2. auto-zero loop: PMOS-diode load, feedback switches, AZ tail ----
    ("XPz",  "p", 590, 190, 4),
    ("XPd1", "p", 510, 310, 3), ("XPd2", "p", 670, 310, 3),
    ("XSf1", "n", 510, 450, 2), ("XSf2", "n", 670, 450, 2),
    ("XMtz", "n", 580, 610, 1),
    # ---- 3. StrongARM core (legs at x=1060 / 1280) ----
    ("XMp2", "p", 910, 210, 2), ("XM5", "p", 1060, 210, 2),
    ("XM6", "p", 1280, 210, 2), ("XMp1", "p", 1430, 210, 2),
    ("XM3", "n", 1060, 380, 2), ("XM4", "n", 1280, 380, 2),
    ("XMp3", "p", 850, 520, 2), ("XI1", "n", 1060, 520, 6),
    ("XI2", "n", 1280, 520, 6), ("XMp4", "p", 1490, 520, 2),
    ("XM1", "n", 1060, 680, 4), ("XM2", "n", 1280, 680, 4),
    ("XMtail", "n", 1170, 820, 4),
]
CAPS = [("Cc1", 250, 310), ("Cc2", 250, 600)]     # 60 fF offset-storage caps
DT = {n: t for n, t, *_ in DEV}
XY = {n: (x, y) for n, t, x, y, w in DEV}


def pin(n, p):
    x, y = XY[n]; dx, dy = P[DT[n]][p]; return x + dx, y + dy


def main():
    o = ["v {xschem version=3.4.4 file_version=1.2}\nG {}\nK {}\nV {}\nS {}\nE {}\n"]
    for n, t, x, y, w in DEV:
        o.append("C {%s} %d %d 0 0 {name=%s model=sky130_fd_pr__%sfet_01v8 W=%g L=0.15 nf=1 m=1}\n"
                 % (NFET if t == "n" else PFET, x, y, n, ("n" if t == "n" else "p"), w))
    for n, x, y in CAPS:
        o.append("C {%s} %d %d 0 0 {name=%s value=60f m=1}\n" % (CAP, x, y, n))

    W = []
    # ================= 1. front end (two identical rows, dy=290) =================
    for dy in (0, 290):
        si_d, si_s = pin("XSi1", "D"), pin("XSi1", "S")
        sc_d, sc_s = pin("XSc1", "D"), pin("XSc1", "S")
        # input switch drain -> left (vinp/vinn ipin added below)
        W += [(si_d[0], si_d[1] + dy, si_d[0], si_d[1] - 30 + dy),
              (si_d[0], si_d[1] - 30 + dy, 120, si_d[1] - 30 + dy)]
        # vcm switch drain -> up (vcm label added below)
        W.append((sc_d[0], sc_d[1] + dy, sc_d[0], sc_d[1] - 30 + dy))
        # tp bus (cap top plate): both switch sources drop onto it
        tp_y = si_s[1] + 30 + dy
        W += [(si_s[0], si_s[1] + dy, si_s[0], tp_y),
              (sc_s[0], sc_s[1] + dy, sc_s[0], tp_y),
              (si_s[0], tp_y, sc_s[0], tp_y)]
        # cap P plate stub up to the tp bus; M plate stub down (gi label below)
        cx, cy = CAPS[0][1], CAPS[0][2] + dy
        W += [(cx, cy - 30, cx, tp_y), (cx, cy + 30, cx, cy + 60)]

    # ================= 2. auto-zero loop =================
    # PMOS header XPz: source to the VDD rail, drain onto the m1s bus
    W += [pin("XPz", "S") + (pin("XPz", "S")[0], VDD_Y),
          pin("XPz", "D") + (pin("XPz", "D")[0], 250)]
    W.append((pin("XPd1", "S")[0], 250, pin("XPd2", "S")[0], 250))       # m1s bus
    for n in ("XPd1", "XPd2"):                                           # diode sources
        sx, sy = pin(n, "S"); W.append((sx, sy, sx, 250))
    # PMOS diode gate->drain ties + da/db spine down to the feedback switches
    for n, sf in (("XPd1", "XSf1"), ("XPd2", "XSf2")):
        gx, gy = pin(n, "G"); dx_, dy_ = pin(n, "D")
        W += [(gx, gy, gx - 15, gy), (gx - 15, gy, gx - 15, dy_ + 20),
              (gx - 15, dy_ + 20, dx_, dy_ + 20), (dx_, dy_, dx_, dy_ + 20),
              (dx_, dy_ + 20, dx_, pin(sf, "D")[1])]
    for n in ("XSf1", "XSf2"):                                           # fb switch sources
        sx, sy = pin(n, "S"); W.append((sx, sy, sx, sy + 30))
    # AZ tail: drain stub up (ntail label), source stub down (VSS gnd)
    W += [pin("XMtz", "D") + (pin("XMtz", "D")[0], pin("XMtz", "D")[1] - 25),
          pin("XMtz", "S") + (pin("XMtz", "S")[0], pin("XMtz", "S")[1] + 25)]

    # ================= 3. StrongARM core =================
    W.append((pin("XPz", "S")[0], VDD_Y, pin("XMp4", "S")[0], VDD_Y))    # VDD rail
    W.append((pin("XM1", "S")[0], VSS_Y, pin("XM2", "S")[0], VSS_Y))    # VSS rail
    for n in ("XMp2", "XM5", "XM6", "XMp1", "XMp3", "XMp4"):             # PMOS -> VDD
        px, py = pin(n, "S"); W.append((px, py, px, VDD_Y))
    # output nodes: precharge drains join the latch legs at y=270
    W += [pin("XMp2", "D") + (pin("XMp2", "D")[0], 270),
          (pin("XMp2", "D")[0], 270, pin("XM5", "D")[0], 270),
          pin("XMp1", "D") + (pin("XMp1", "D")[0], 270),
          (pin("XMp1", "D")[0], 270, pin("XM6", "D")[0], 270)]
    W += [pin("XM5", "D") + pin("XM3", "D"), pin("XM6", "D") + pin("XM4", "D")]
    # latch NMOS -> isolation switch -> input pair (s3/s4 and da/db legs)
    W += [pin("XM3", "S") + pin("XI1", "D"), pin("XM4", "S") + pin("XI2", "D"),
          pin("XI1", "S") + pin("XM1", "D"), pin("XI2", "S") + pin("XM2", "D")]
    # pcn precharge of da/db (outer columns, drains joined at y=600)
    W += [pin("XMp3", "D") + (pin("XMp3", "D")[0], 600),
          (pin("XMp3", "D")[0], 600, pin("XI1", "S")[0], 600),
          pin("XMp4", "D") + (pin("XMp4", "D")[0], 600),
          (pin("XMp4", "D")[0], 600, pin("XI2", "S")[0], 600)]
    # input-pair sources -> ntail bus -> clk tail -> VSS rail
    s1, s2, td = pin("XM1", "S"), pin("XM2", "S"), pin("XMtail", "D")
    W += [(s1[0], s1[1], s1[0], 760), (s2[0], s2[1], s2[0], 760), (s1[0], 760, s2[0], 760),
          (td[0], 760, td[0], td[1]),
          pin("XMtail", "S") + (pin("XMtail", "S")[0], VSS_Y)]
    # PMOS bulk -> source ties (bulk = source = VDD for all but the diodes)
    for n in ("XPz", "XMp2", "XM5", "XM6", "XMp1", "XMp3", "XMp4"):
        bx, by = pin(n, "B"); sx, sy = pin(n, "S"); W.append((bx, by, sx, sy))
    for seg in W:
        o.append("N %d %d %d %d {}\n" % seg)

    nid = [0]

    def lab(px, py, rot, name, sym="lab_pin.sym"):
        nid[0] += 1
        o.append("C {sym/%s} %d %d 0 %d {name=l%d lab=%s}\n" % (sym, px, py, rot, nid[0], name))

    def stublab(pc, vec, rot, name, sym="lab_pin.sym"):
        px, py = pc; ex, ey = px + vec[0], py + vec[1]
        o.append("N %d %d %d %d {}\n" % (px, py, ex, ey)); lab(ex, ey, rot, name, sym)

    # ---- gate net-labels, all exiting LEFT (house convention) ----
    GATE = (
        ("XSi1", "azb"), ("XSi2", "azb"), ("XPz", "azb"),           # decision-connect
        ("XSc1", "az"), ("XSc2", "az"),                             # AZ phase
        ("XSf1", "az"), ("XSf2", "az"), ("XMtz", "az"),
        ("XMp3", "pcn"), ("XMp4", "pcn"),                           # handover precharge
        ("XMp2", "clk"), ("XMp1", "clk"),                           # decision phase
        ("XI1", "clk"), ("XI2", "clk"), ("XMtail", "clk"),
        ("XM5", "outp"), ("XM3", "outp"),                           # cross-couple
        ("XM6", "outn"), ("XM4", "outn"),
        ("XM1", "gi1"), ("XM2", "gi2"),                             # corrected inputs
    )
    for n, net in GATE:
        stublab(pin(n, "G"), (-30, 0), 2, net)

    # ---- front-end IO + net labels ----
    lab(120, 150, 2, "vinp", "ipin.sym"); lab(120, 440, 2, "vinn", "ipin.sym")
    lab(330, 150, 1, "vcm"); lab(330, 440, 1, "vcm")                # AZ common-mode
    lab(250, 370, 3, "gi1"); lab(250, 660, 3, "gi2")                # cap storage nodes

    # ---- AZ-loop net labels (da/db spines, gi/ntail stubs) ----
    lab(530, 390, 0, "da"); lab(690, 390, 0, "db")
    lab(530, 510, 3, "gi1"); lab(690, 510, 3, "gi2")
    lab(pin("XMtz", "D")[0], pin("XMtz", "D")[1] - 25, 1, "ntail")
    lab(pin("XMtz", "S")[0], pin("XMtz", "S")[1] + 25, 3, "VSS", "gnd.sym")

    # ---- core net labels ----
    lab(pin("XM5", "D")[0], 270, 0, "outn", "opin.sym")
    lab(pin("XM6", "D")[0], 270, 0, "outp", "opin.sym")
    lab(pin("XI1", "S")[0], 620, 0, "da"); lab(pin("XI2", "S")[0], 620, 0, "db")
    lab(1090, 760, 0, "ntail")

    # ---- bulk ties: NMOS -> VSS gnd stub (right); diode PMOS bulks -> VDD label ----
    for n, t, x, y, w in DEV:
        if t == "n":
            stublab(pin(n, "B"), (25, 0), 0, "VSS", "gnd.sym")
    for n in ("XPd1", "XPd2"):
        stublab(pin(n, "B"), (25, 0), 0, "VDD")

    # ---- rails ----
    stublab((pin("XPz", "S")[0], VDD_Y), (0, -28), 1, "VDD", "vdd.sym")
    stublab((pin("XM1", "S")[0], VSS_Y), (0, 28), 3, "VSS", "gnd.sym")

    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, "dong_autozero.sch"), "w").write("".join(o))
    print("wrote dong_autozero.sch (compact, %d devices)" % (len(DEV) + len(CAPS)))


if __name__ == "__main__":
    main()
