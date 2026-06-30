#!/usr/bin/env python3
"""Generate a compact, journal-style Xschem schematic for the DOUBLE-StrongARM two-stage latch comparator.

Matches eda/hero/comparators/dsa.spice (22 FETs = two identical 11-device StrongARM stages). The first
StrongARM stage (left) resolves the input differential rail-to-rail on the clk edge (latch nets s1n/s1p);
the second StrongARM stage (right) re-samples that already-resolved differential on the SAME clk edge
(its input pair gates are driven by s1p/s1n), suppressing second-stage mismatch. Rails VDD/VSS are
shared. Each stage = clocked tail + NMOS input pair + cross-coupled latch (2x NMOS / 2x PMOS) +
four precharge PMOS (two on the latch outputs, two on the input-pair drains s*da/s*db).

Layout follows the StrongARM house figure: every FET is drawn un-mirrored (gate pin on the LEFT, bulk
on the RIGHT), so all gate/clk/input/cross-couple net-labels exit to the left and all bulk ties exit to
the right -- the two never collide, and column spacing is chosen so a left-going label never reaches the
device to its left. The cross-coupled latch is shown via the gate net-labels on the latch FETs
(s1p/s1n, outp/outn), the standard compact convention. Devices use the repo-local sky130 symbols
(sym/nfet.sym, sym/pfet.sym; name + W/L kept, model text stripped).

The thesis testbench injects the input-referred offset via series DC sources Vo1..Vo4 on the 1st-stage
input-pair and latch-NMOS gates; that is testbench instrumentation, so those gates are drawn at their
signal nets (vinp/vinn, s1p/s1n) and the injection is noted in a caption -- all 22 comparator FETs are
present and faithful to the netlist.
"""
import os

NFET, PFET = "sym/nfet.sym", "sym/pfet.sym"
# symbol pin offsets (match sym/{n,p}fet.sym B-port positions); all FETs un-mirrored
P = {"n": {"D": (20, -30), "G": (-20, 0), "S": (20, 30), "B": (20, 0)},
     "p": {"S": (20, -30), "G": (-20, 0), "D": (20, 30), "B": (20, 0)}}

# y rows (down), shared across both stages
VDD_Y, VSS_Y = 110, 760
ROW_P    = 210   # latch PMOS (legs) + precharge-out PMOS (flanks)
ROW_N    = 380   # latch NMOS (legs) + precharge-da/db PMOS (flanks)
ROW_IN   = 540   # input pair
ROW_TAIL = 670   # clocked tail
OUT_Y    = 290   # latch-output tap row (between ROW_P and ROW_N)
DA_Y     = 460   # input-pair-drain (s*da/s*db) tap row (between ROW_N and ROW_IN)
COMM_Y   = 610   # input-pair common-source / tail-drain node row

# columns relative to a stage x-origin (origin = left leg)
LEGL, LEGR = 0, 230      # the two latch legs (wide enough for a left-going label between them)
FLKL, FLKR = -160, 390   # outer flanking precharge PMOS columns
TAILX = 115              # tail x (centered between legs)


def stage_devices(name, ox):
    """One StrongARM stage at x-origin ox. Returns (name, type, x, y, W)."""
    L, R = ox + LEGL, ox + LEGR
    return [
        (name + "p1",  "p", L,           ROW_P, 2), (name + "p2",  "p", R,           ROW_P, 2),
        (name + "pr1", "p", ox + FLKL,   ROW_P, 2), (name + "pr2", "p", ox + FLKR,   ROW_P, 2),
        (name + "n1",  "n", L,           ROW_N, 2), (name + "n2",  "n", R,           ROW_N, 2),
        (name + "prd1","p", ox + FLKL,   ROW_N, 2), (name + "prd2","p", ox + FLKR,   ROW_N, 2),
        (name + "in1", "n", L,           ROW_IN,4), (name + "in2", "n", R,           ROW_IN,4),
        (name + "tail","n", ox + TAILX,  ROW_TAIL,4),
    ]


STAGE1_OX = 360
STAGE2_OX = 1010
DEV = stage_devices("S1", STAGE1_OX) + stage_devices("S2", STAGE2_OX)
DT = {n: t for n, t, *_ in DEV}
XY = {n: (x, y) for n, t, x, y, w in DEV}


def pin(n, p):
    x, y = XY[n]
    dx, dy = P[DT[n]][p]
    return x + dx, y + dy


def main():
    o = ["v {xschem version=3.4.4 file_version=1.2}\nG {}\nK {}\nV {}\nS {}\nE {}\n"]
    for n, t, x, y, w in DEV:
        o.append("C {%s} %d %d 0 0 {name=%s model=sky130_fd_pr__%sfet_01v8 W=%g L=0.15 nf=1 m=1}\n"
                 % (NFET if t == "n" else PFET, x, y, n, ("n" if t == "n" else "p"), w))

    W = []
    nid = [0]

    def lab(px, py, rot, name, sym="lab_pin.sym"):
        nid[0] += 1
        o.append("C {sym/%s} %d %d 0 %d {name=l%d lab=%s}\n" % (sym, px, py, rot, nid[0], name))

    def stublab(pc, vec, rot, name, sym="lab_pin.sym"):
        px, py = pc
        ex, ey = px + vec[0], py + vec[1]
        W.append((px, py, ex, ey))
        lab(ex, ey, rot, name, sym)

    def txt(s, x, y, size=0.3, layer=None):
        tag = "{layer=%d}" % layer if layer else "{}"
        o.append("T {%s} %d %d 0 0 %g %g %s\n" % (s, x, y, size, size, tag))

    # global rails (span both stages)
    RAIL_X0 = STAGE1_OX + FLKL - 40
    RAIL_X1 = STAGE2_OX + FLKR + 40
    W.append((RAIL_X0, VDD_Y, RAIL_X1, VDD_Y))
    W.append((RAIL_X0, VSS_Y, RAIL_X1, VSS_Y))

    def wire_stage(name, ox):
        L, R = ox + LEGL, ox + LEGR
        # PMOS sources -> VDD (latch P legs + 4 precharge flanks)
        for d in (name + "p1", name + "p2", name + "pr1", name + "pr2",
                  name + "prd1", name + "prd2"):
            px, py = pin(d, "S")
            W.append((px, py, px, VDD_Y))
        # latch-PMOS drain -> latch-NMOS drain (the leg)
        for legp, legn in ((name + "p1", name + "n1"), (name + "p2", name + "n2")):
            pd = pin(legp, "D"); nd = pin(legn, "D")
            W.append((pd[0], pd[1], nd[0], nd[1]))
        # latch-NMOS source -> input drain (continue the leg)
        for legn, legi in ((name + "n1", name + "in1"), (name + "n2", name + "in2")):
            ns = pin(legn, "S"); idr = pin(legi, "D")
            W.append((ns[0], ns[1], idr[0], idr[1]))
        # precharge-out PMOS drain -> latch output node (jog to leg at OUT_Y)
        for pr, legx in ((name + "pr1", L), (name + "pr2", R)):
            sx, sy = pin(pr, "D")
            W.append((sx, sy, sx, OUT_Y))
            W.append((sx, OUT_Y, legx + 20, OUT_Y))   # leg drain x = legx+20
        # precharge-da/db PMOS drain -> input-pair-drain node (jog to leg at DA_Y)
        for prd, legx in ((name + "prd1", L), (name + "prd2", R)):
            sx, sy = pin(prd, "D")
            W.append((sx, sy, sx, DA_Y))
            W.append((sx, DA_Y, legx + 20, DA_Y))
        # input-pair sources -> common node -> tail drain
        s1 = pin(name + "in1", "S"); s2 = pin(name + "in2", "S")
        td = pin(name + "tail", "D")
        W.append((s1[0], s1[1], s1[0], COMM_Y))
        W.append((s2[0], s2[1], s2[0], COMM_Y))
        W.append((s1[0], COMM_Y, s2[0], COMM_Y))
        W.append((td[0], COMM_Y, td[0], td[1]))
        # tail source -> VSS
        ts = pin(name + "tail", "S")
        W.append((ts[0], ts[1], ts[0], VSS_Y))
        # PMOS & tail bulk -> own source (short tie, exits right then up/down to source)
        for d in (name + "p1", name + "p2", name + "pr1", name + "pr2",
                  name + "prd1", name + "prd2", name + "tail"):
            bx, by = pin(d, "B"); sx, sy = pin(d, "S")
            W.append((bx, by, sx, sy))

    wire_stage("S1", STAGE1_OX)
    wire_stage("S2", STAGE2_OX)

    def stage_labels(name, ox, inL, inR, outL, outR, in_sym):
        L, R = ox + LEGL, ox + LEGR
        # latch cross-couple gate labels (all gates exit LEFT):
        #   left-leg gate driven by RIGHT output ; right-leg gate driven by LEFT output
        stublab(pin(name + "p1", "G"), (-28, 0), 2, outR)
        stublab(pin(name + "n1", "G"), (-28, 0), 2, outR)
        stublab(pin(name + "p2", "G"), (-28, 0), 2, outL)
        stublab(pin(name + "n2", "G"), (-28, 0), 2, outL)
        # clk on the four precharge PMOS gates + tail gate (all exit LEFT)
        for d in (name + "pr1", name + "prd1", name + "pr2", name + "prd2", name + "tail"):
            stublab(pin(d, "G"), (-28, 0), 2, "clk")
        # NMOS bulk -> VSS (latch NMOS + input pair); exits RIGHT (bulk pin side)
        for d in (name + "n1", name + "n2", name + "in1", name + "in2"):
            stublab(pin(d, "B"), (24, 0), 0, "VSS", "gnd.sym")
        # input-pair gate labels (signal nets), exit LEFT
        stublab(pin(name + "in1", "G"), (-28, 0), 2, inL, in_sym)
        stublab(pin(name + "in2", "G"), (-28, 0), 2, inR, in_sym)
        # latch-output opins on the two legs at OUT_Y (tap node already wired)
        lab(L + 20, OUT_Y, 0, outL, "opin.sym")
        lab(R + 20, OUT_Y, 0, outR, "opin.sym")

    # Stage 1: inputs vinp/vinn (ipin) ; latch outputs s1n (left) / s1p (right)
    stage_labels("S1", STAGE1_OX, "vinp", "vinn", "s1n", "s1p", "ipin.sym")
    # Stage 2: input gates driven by stage-1 outputs s1p (left) / s1n (right); outputs outn/outp
    stage_labels("S2", STAGE2_OX, "s1p", "s1n", "outn", "outp", "lab_pin.sym")

    # rails terminals: VDD at far-left of rail; VSS dropped under stage-1 tail
    stublab((RAIL_X0, VDD_Y), (0, -28), 1, "VDD", "vdd.sym")
    stublab((STAGE1_OX + TAILX + 20, VSS_Y), (0, 28), 3, "VSS", "gnd.sym")

    # offset-injection note (testbench instrumentation, layer-7 accent)
    txt("offset Vo1-4 injected on stage-1 input/latch gates (testbench)",
        RAIL_X0, VSS_Y + 64, 0.26, layer=7)

    for seg in W:
        o.append("N %d %d %d %d {}\n" % seg)

    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, "dsa.sch"), "w").write("".join(o))
    print("wrote dsa.sch (compact, %d FETs = two StrongARM stages)" % len(DEV))


if __name__ == "__main__":
    main()
