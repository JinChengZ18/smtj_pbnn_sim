#!/usr/bin/env python3
"""Generate a compact, journal-style Xschem schematic of the PICO-RAM-style comparator
power-gating pair (matches the GATED netlist emitted by eda/design_survey/repro/
picoram_gating.py: build_netlist("gated", ...)).

WHAT IS DRAWN (and how it maps to the simulated netlist)
--------------------------------------------------------
* CMP1  = the precise comparator: the committed StrongARM latch (netlist XMtail1/XM11..16/
  XMp11..14, 11 FETs, W=2 latch+precharge / W=4 input+tail, L=0.15), drawn as a compact
  sym/comp.sym block (house convention, cf. sar_readout.sch) -- its transistor-level figure
  is strongarm_sa.sch. Block INP/INN = vinp/vinn; the drawn single-ended OUT is outp1 of the
  differential latch (outn1 complementary, not drawn in the block abstraction).
* CMP2A/CMP2B = the two near-minimum coarse comparators (netlist XM2*a / XM2*b, 11 FETs each,
  all W=0.42 L=0.15), same StrongARM topology, decision thresholds at the +Vg / -Vg offset
  references ("set by Vref" in PICO-RAM; ideal series sources in the sim -- instrumentation,
  NOT drawn; annotated as "ref +Vg"/"ref -Vg"). Drawn OUT of CMP2A is its complement output
  outna (= NOT(vin > +Vg), the polarity the NAND consumes); drawn OUT of CMP2B is its true
  output outpb (= vin > -Vg). Both are strobed by clk2 (coarse strobe, leads clk_raw).
* Clock-gating logic at transistor level, exact netlist devices/W/L:
    amb   = INV(NAND(outna, outpb))   -> XNa1..XNa4 (W=1) + XIa1 (W=1)/XIa2 (W=2)
    cclk1 = INV(NAND(clk_raw, amb))   -> XNb1..XNb4 (W=1) + driver XIb1 (W=2)/XIb2 (W=4)
  (netlist node clk1raw is displayed as clk_raw, the name used in the repro's mapping notes).
  The gated clock cclk1 is routed as a REAL wire from the driver back into CMP1's strobe.
* Shared differential inputs vinp/vinn feed all three comparators from two vertical rails.

NOT drawn (instrumentation / harness): the +-Vg offset sources Vo*, the per-block metering
supplies (vdd1/vdd2a/vdd2b/vddl -> unified VDD here), the 4 dummy load FETs XDa*/XDb* on the
unused coarse outputs (loading balance), and the baseline-mode buffer XIb1n..XIb2p. The
final answer mux (amb ? Cmp1 : Cmp2a) lives in the measurement harness, not the netlist.

House conventions (gen_strongarm_sch.py / gen_current_sampling_sch.py): local cleaned sky130
symbols; gate labels exit left; NMOS bulks -> VSS gnd stubs right; PMOS bulks tied to source
(source==vdd for every drawn PMOS); far nets label-routed; displayed device names = netlist
names minus the X spice-prefix (the symbol re-adds it).
"""
import os

NFET, PFET, COMP = "sym/nfet.sym", "sym/pfet.sym", "sym/comp.sym"
P = {"n": {"D": (20, -30), "G": (-20, 0), "S": (20, 30), "B": (20, 0)},
     "p": {"S": (20, -30), "G": (-20, 0), "D": (20, 30), "B": (20, 0)},
     "comp": {"INP": (-40, -15), "INN": (-40, 15), "OUT": (45, 0)}}

# gating-logic FETs: (name, type, x, y, W); L=0.15 for all (exact W/L of GATED_LOGIC in
# eda/design_survey/repro/picoram_gating.py)
XA, XA2 = 560, 700            # NAND_a columns (stack | 2nd pfet)
XIA = 840                     # INV_a column
XB, XB2 = 1080, 1220          # NAND_b columns
XIB = 1360                    # INV_b (driver) column
YP, YN1, YN2 = 200, 330, 420  # pfet row, NMOS-stack rows
DEV = [
    ("Na3", "p", XA,  YP,  1), ("Na4", "p", XA2, YP,  1),   # NAND(outna, outpb) pull-up
    ("Na1", "n", XA,  YN1, 1), ("Na2", "n", XA,  YN2, 1),   # ... pull-down stack (n1/nx)
    ("Ia2", "p", XIA, YP,  2), ("Ia1", "n", XIA, YN1, 1),   # INV -> amb
    ("Nb3", "p", XB,  YP,  1), ("Nb4", "p", XB2, YP,  1),   # NAND(clk_raw, amb) pull-up
    ("Nb1", "n", XB,  YN1, 1), ("Nb2", "n", XB,  YN2, 1),   # ... pull-down stack (n2/ny)
    ("Ib2", "p", XIB, YP,  4), ("Ib1", "n", XIB, YN1, 2),   # driver INV -> cclk1
]
# compact comparator blocks: (name, x, y)
CMPS = [("CMP2A", 320, 180), ("CMP2B", 320, 340), ("CMP1", 320, 620)]
DT = {n: t for n, t, *_ in DEV}
DT.update({n: "comp" for n, *_ in CMPS})
XY = {n: (x, y) for n, t, x, y, w in DEV}
XY.update({n: (x, y) for n, x, y in CMPS})

XIN_P, XIN_N = 120, 170       # shared vinp / vinn input rails
YFB = 720                     # cclk1 feedback bus (below everything)
XFB = 1470                    # cclk1 feedback riser (right of the driver)


def pin(n, p):
    x, y = XY[n]; dx, dy = P[DT[n]][p]; return x + dx, y + dy


def main():
    o = ["v {xschem version=3.4.4 file_version=1.2}\nG {}\nK {}\nV {}\nS {}\nE {}\n"]
    for n, t, x, y, w in DEV:
        o.append("C {%s} %d %d 0 0 {name=%s model=sky130_fd_pr__%sfet_01v8 W=%g L=0.15 nf=1 m=1}\n"
                 % (NFET if t == "n" else PFET, x, y, n, ("n" if t == "n" else "p"), w))
    for n, x, y in CMPS:
        o.append("C {%s} %d %d 0 0 {name=%s}\n" % (COMP, x, y, n))

    W = []
    # ---- shared differential inputs: two vertical rails, taps into all three blocks ----
    # (ipins staggered: vinn enters higher so its arrow clears the vinp label text)
    for xr, pname, ytop in ((XIN_P, "INP", 120), (XIN_N, "INN", 90)):
        ys = [pin(c, pname)[1] for c, _, _ in CMPS]
        W.append((xr, ytop, xr, max(ys)))                      # rail (ipin at the top)
        for c, _, _ in CMPS:
            px, py = pin(c, pname); W.append((xr, py, px, py)) # tap
    # ---- comparator strobes: bottom-corner entry (block abstraction) ----
    for c, _, _ in CMPS[:2]:                                   # clk2 into the coarse pair
        x, y = XY[c]
        W += [(x - 25, y + 30, x - 25, y + 55), (x - 25, y + 55, 240, y + 55)]
    # ---- coarse outputs -> net labels consumed by the NAND ----
    W.append(pin("CMP2A", "OUT") + (410, pin("CMP2A", "OUT")[1]))
    W.append(pin("CMP2B", "OUT") + (410, pin("CMP2B", "OUT")[1]))
    W.append(pin("CMP1", "OUT") + (410, pin("CMP1", "OUT")[1]))

    # ---- the two NAND2s: parallel pull-up bus + series pull-down stack ----
    for xs, x2 in ((XA, XA2), (XB, XB2)):
        W.append((xs + 20, YP + 30, x2 + 20, YP + 30))         # output bus (both pfet drains)
        W.append((xs + 20, YP + 30, xs + 20, YN1 - 30))        # bus -> top NMOS drain
        W.append((xs + 20, YN1 + 30, xs + 20, YN2 - 30))       # series node (nx / ny)
    # ---- the two INVs: gate rail + drain-drain output ----
    for xi in (XIA, XIB):
        W += [(xi - 20, YP, xi - 50, YP), (xi - 20, YN1, xi - 50, YN1),
              (xi - 50, YP, xi - 50, YN1),                     # input rail
              (xi + 20, YP + 30, xi + 20, YN1 - 30)]           # output (drains)
    # ---- stage links: NAND output -> INV input rail ----
    W.append((XA + 20, 265, XIA - 50, 265))                    # n1
    W.append((XB + 20, 265, XIB - 50, 265))                    # n2
    # ---- gated clock cclk1: driver output -> real feedback wire -> CMP1 strobe ----
    x1, y1 = XY["CMP1"]
    W += [(XIB + 20, 265, XFB, 265), (XFB, 265, XFB, YFB),
          (XFB, YFB, x1 - 25, YFB), (x1 - 25, YFB, x1 - 25, y1 + 30)]
    # ---- PMOS bulk -> source ties (all drawn PMOS sit on VDD) ----
    for n in ("Na3", "Na4", "Ia2", "Nb3", "Nb4", "Ib2"):
        W.append(pin(n, "B") + pin(n, "S"))
    for seg in W:
        o.append("N %d %d %d %d {}\n" % seg)

    nid = [0]

    def lab(px, py, rot, name, sym="lab_pin.sym"):
        nid[0] += 1
        o.append("C {sym/%s} %d %d 0 %d {name=l%d lab=%s}\n" % (sym, px, py, rot, nid[0], name))

    def stublab(pc, vec, rot, name, sym="lab_pin.sym"):
        px, py = pc; ex, ey = px + vec[0], py + vec[1]
        o.append("N %d %d %d %d {}\n" % (px, py, ex, ey)); lab(ex, ey, rot, name, sym)

    def txt(s, x, y, size=0.22):
        o.append("T {%s} %d %d 0 0 %g %g {}\n" % (s, x, y, size, size))

    # ---- gate net-labels (exit left, house convention) ----
    for n, net in (("Na3", "outna"), ("Na1", "outna"), ("Na4", "outpb"), ("Na2", "outpb"),
                   ("Nb3", "clk_raw"), ("Nb1", "clk_raw"), ("Nb4", "amb"), ("Nb2", "amb")):
        stublab(pin(n, "G"), (-30, 0), 2, net)
    # ---- supplies: PMOS sources -> VDD up; NMOS stack feet -> VSS down; NMOS bulks right ----
    for n in ("Na3", "Na4", "Ia2", "Nb3", "Nb4", "Ib2"):
        stublab(pin(n, "S"), (0, -25), 1, "VDD", "vdd.sym")
    for n in ("Na2", "Ia1", "Nb2", "Ib1"):
        stublab(pin(n, "S"), (0, 25), 3, "VSS", "gnd.sym")
    for n in ("Na1", "Na2", "Ia1", "Nb1", "Nb2", "Ib1"):
        stublab(pin(n, "B"), (25, 0), 0, "VSS", "gnd.sym")

    # ---- IO / net labels ----
    lab(XIN_P, 120, 1, "vinp", "ipin.sym"); lab(XIN_N, 90, 1, "vinn", "ipin.sym")
    lab(240, XY["CMP2A"][1] + 55, 2, "clk2"); lab(240, XY["CMP2B"][1] + 55, 2, "clk2")
    lab(410, pin("CMP2A", "OUT")[1], 0, "outna")
    lab(410, pin("CMP2B", "OUT")[1], 0, "outpb")
    lab(410, pin("CMP1", "OUT")[1], 0, "outp1", "opin.sym")
    lab(700, 265, 0, "n1"); lab(XB + 130, 265, 0, "n2")
    lab(XIA + 20, 265, 0, "amb")                               # INV_a output (label-routed)
    lab(600, YFB, 0, "cclk1")                                  # the gated-clock feedback bus

    # ---- annotations ----
    for c, ref in (("CMP2A", "ref +Vg"), ("CMP2B", "ref -Vg")):
        x, y = XY[c]
        txt(ref, x - 18, y + 36); txt("W=0.42 (near-min)", x - 18, y + 58, 0.2)
    txt("committed StrongARM", x1 - 18, y1 + 36, 0.2)
    txt("W=2-4, L=0.15", x1 - 18, y1 + 58, 0.2)
    txt("NAND2", XA - 12, 502); txt("NAND2", XB - 12, 502)
    txt("INV", XIA + 6, 412); txt("INV (drv)", XIB - 14, 412)
    txt("amb = AND(outna, outpb)", XA, 540, 0.24)
    txt("cclk1 = AND(clk_raw, amb)", XB, 540, 0.24)

    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, "picoram_gating.sch"), "w", newline="\n").write("".join(o))
    print("wrote picoram_gating.sch (compact, %d FETs + %d comparator blocks)"
          % (len(DEV), len(CMPS)))


if __name__ == "__main__":
    main()
