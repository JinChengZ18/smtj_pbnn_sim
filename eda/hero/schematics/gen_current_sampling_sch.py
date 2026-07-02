#!/usr/bin/env python3
"""Generate a compact, journal-style Xschem schematic for the CURRENT-SAMPLING sense
amplifier (matches eda/hero/comparators/current_sampling.spice -- 21 FETs + 2 hold caps).

Two-phase, current-mode. Phase 1 (clk low -> local clkb high, SAMPLE): the V-to-I input
NMOS Min1/Min2 (W=win=4) sink their branch currents through the sampling PMOS Mps1/Mps2,
which are diode-connected via the clkb-gated switches swd1/swd2; the Vgs carrying the
actual current is stored on hold nodes sp1/sp2 (Ch1/Ch2 = 25f to VDD + gate cap). The
series sample switches sws1/sws2 (clkb) close the m1/m2 -> d1/d2 path. Phase 2 (clk
high, EVALUATE): swd/sws open (currents held), transmission gates swep/swen (clkb/clk)
steer the two held currents into the charge-up latch: clkb-gated PMOS head Mhd -> th,
cross-coupled pairs Mcp1/Mcp2 + Mcn1/Mcn2, and clkb-gated reset NMOS Mr1/Mr2 that
precharge outp/outn LOW during sampling. The larger held current charges its side faster.

House conventions (same as gen_strongarm_sch.py / gen_double_tail_sch.py): local cleaned
sky130 symbols; ALL gate labels exit left; NMOS bulks -> VSS gnd stubs right; PMOS bulks
tied to source ONLY where source==vdd in the netlist (swep1/2 and Mcp1/2 have bulk=vdd
but source=m/th, so they get explicit VDD bulk stubs instead); the differential feedback
(cross-couple, TG->outp/outn) is label-routed. The testbench offset sources Vo1..Vo6 are
instrumentation and are not drawn; gates carry their signal nets (vinp, sp1, outp, ...).
Displayed device names = netlist names minus the X spice-prefix (the symbol re-adds it).
swen1/2 are drawn with D/S vertically swapped (symmetric pass switches; D=out, S=m in
the netlist); the drawn net connectivity is exact.
"""
import os

NFET, PFET = "sym/nfet.sym", "sym/pfet.sym"
# pin offsets (rot 0), from the symbol bounding boxes
P = {"n": {"D": (20, -30), "G": (-20, 0), "S": (20, 30), "B": (20, 0)},
     "p": {"S": (20, -30), "G": (-20, 0), "D": (20, 30), "B": (20, 0)}}

VDD_Y, VSS_Y = 110, 630
X1, X2 = 460, 980                       # side-1 / side-2 leg columns
XHD, XA, XB = 1640, 1550, 1730          # latch: head column, outn column, outp column
XR2, XR1 = 1400, 1890                   # latch reset columns (outn | outp side)

# (name, type, x, y, W, L)  -- W/L exactly as in current_sampling.spice (win=4.0 um,
# the value used by the committed N=120 offset-MC run, offset_mc_current_sampling.json)
DEV = [
    # local inverted clock (clkb = !clk)
    ("invp", "p", 140, 210, 2, 0.15), ("invn", "n", 140, 520, 1, 0.15),
    # side 1: vinp -> V-to-I -> sampled/held current -> outp
    ("Mps1",  "p", X1,       210, 16, 0.5),   # sampling PMOS (holds I1)
    ("swd1",  "n", X1 - 120, 300, 2, 0.15),   # diode-connect switch (clkb)
    ("sws1",  "n", X1,       380, 4, 0.15),   # sample switch m1->d1 (clkb)
    ("Min1",  "n", X1,       520, 4, 0.15),   # V-to-I input NMOS (W=win)
    ("swep1", "p", X1 + 130, 370, 4, 0.15),   # evaluate TG, PMOS half (clkb)
    ("swen1", "n", X1 + 250, 370, 2, 0.15),   # evaluate TG, NMOS half (clk)
    # side 2: vinn -> ... -> outn
    ("Mps2",  "p", X2,       210, 16, 0.5),
    ("swd2",  "n", X2 - 120, 300, 2, 0.15),
    ("sws2",  "n", X2,       380, 4, 0.15),
    ("Min2",  "n", X2,       520, 4, 0.15),
    ("swep2", "p", X2 + 130, 370, 4, 0.15),
    ("swen2", "n", X2 + 250, 370, 2, 0.15),
    # current-comparison charge-up latch (precharged LOW, clkb-gated head)
    ("Mhd",  "p", XHD, 210, 4, 0.15),
    ("Mcp1", "p", XA,  340, 2, 0.15), ("Mcp2", "p", XB, 340, 2, 0.15),
    ("Mr2",  "n", XR2, 520, 2, 0.15), ("Mcn1", "n", XA, 520, 2, 0.15),
    ("Mcn2", "n", XB,  520, 2, 0.15), ("Mr1",  "n", XR1, 520, 2, 0.15),
]
CAPS = [("Ch1", X1 - 200, 150, "25f"), ("Ch2", X2 - 200, 150, "25f")]
DT = {n: t for n, t, *_ in DEV}
XY = {n: (x, y) for n, t, x, y, w, l in DEV}


def pin(n, p):
    x, y = XY[n]; dx, dy = P[DT[n]][p]; return x + dx, y + dy


def main():
    o = ["v {xschem version=3.4.4 file_version=1.2}\nG {}\nK {}\nV {}\nS {}\nE {}\n"]
    for n, t, x, y, w, l in DEV:
        o.append("C {%s} %d %d 0 0 {name=%s model=sky130_fd_pr__%sfet_01v8 W=%g L=%g nf=1 m=1}\n"
                 % (NFET if t == "n" else PFET, x, y, n, ("n" if t == "n" else "p"), w, l))
    for n, x, y, v in CAPS:
        o.append("C {sym/cap.sym} %d %d 0 0 {name=%s value=%s m=1}\n" % (x, y, n, v))

    W = []
    # ---- rails ----
    W.append((160, VDD_Y, pin("Mhd", "S")[0], VDD_Y))
    W.append((160, VSS_Y, pin("Mr1", "S")[0], VSS_Y))

    # ---- local clk inverter ----
    W.append(pin("invp", "S") + (pin("invp", "S")[0], VDD_Y))
    W.append(pin("invp", "B") + pin("invp", "S"))                      # bulk=source=vdd
    W.append(pin("invp", "D") + pin("invn", "D"))                      # clkb spine
    W.append(pin("invn", "S") + (pin("invn", "S")[0], VSS_Y))

    # ---- sampling sides ----
    for i, X in ((1, X1), (2, X2)):
        ps, swd, sws, mi = "Mps%d" % i, "swd%d" % i, "sws%d" % i, "Min%d" % i
        ep, en = "swep%d" % i, "swen%d" % i
        capx = X - 200
        W.append(pin(ps, "S") + (pin(ps, "S")[0], VDD_Y))              # PMOS source -> VDD
        W.append(pin(ps, "B") + pin(ps, "S"))                          # bulk=source=vdd
        # sp node: cap column -> PMOS gate, with a tap down to the diode switch drain
        W.append((capx, 210) + pin(ps, "G"))
        W.append((capx, 180, capx, 210))                               # cap M -> sp line
        W.append((capx, 120, capx, VDD_Y))                             # cap P -> VDD
        W.append(pin(swd, "D") + (pin(swd, "D")[0], 210))              # swd drain -> sp line
        # m node: swd source -- leg -- TG tops (single y=330 line, split at junctions)
        W.append(pin(ps, "D") + pin(sws, "D"))                         # m leg
        W.append(pin(swd, "S") + (X + 20, 330))
        W.append((X + 20, 330) + (pin(ep, "S")[0], 330))
        W.append((pin(ep, "S")[0], 330) + (pin(en, "D")[0], 330))
        W.append((pin(ep, "S")[0], 330) + pin(ep, "S"))                # TG top stubs
        W.append((pin(en, "D")[0], 330) + pin(en, "D"))
        # (swep bulk is vdd, NOT its source m -- explicit VDD stub added below)
        # TG bottoms -> outp/outn label bus
        W.append(pin(ep, "D") + (pin(ep, "D")[0], 430))
        W.append(pin(en, "S") + (pin(en, "S")[0], 430))
        W.append((pin(ep, "D")[0], 430, pin(en, "S")[0], 430))
        # d node: sample switch -> input NMOS; input NMOS source -> VSS
        W.append(pin(sws, "S") + pin(mi, "D"))
        W.append(pin(mi, "S") + (pin(mi, "S")[0], VSS_Y))

    # ---- latch ----
    W.append(pin("Mhd", "S") + (pin("Mhd", "S")[0], VDD_Y))
    W.append(pin("Mhd", "B") + pin("Mhd", "S"))                        # bulk=source=vdd
    W.append(pin("Mhd", "D") + (pin("Mhd", "D")[0], 270))
    W.append((pin("Mcp1", "S")[0], 270, pin("Mcp2", "S")[0], 270))     # th bus
    for n in ("Mcp1", "Mcp2"):
        W.append(pin(n, "S") + (pin(n, "S")[0], 270))
    OUT_Y = 420
    for n in ("Mcp1", "Mcp2"):                                         # cp drains -> out bus
        W.append(pin(n, "D") + (pin(n, "D")[0], OUT_Y))
    for n in ("Mr2", "Mcn1", "Mcn2", "Mr1"):                           # n drains -> out bus
        W.append(pin(n, "D") + (pin(n, "D")[0], OUT_Y))
        W.append(pin(n, "S") + (pin(n, "S")[0], VSS_Y))
    W.append((pin("Mr2", "D")[0], OUT_Y, pin("Mcn1", "D")[0], OUT_Y))  # outn bus
    W.append((pin("Mcn2", "D")[0], OUT_Y, pin("Mr1", "D")[0], OUT_Y))  # outp bus

    for seg in W:
        o.append("N %d %d %d %d {}\n" % seg)

    nid = [0]

    def lab(px, py, rot, name, sym="lab_pin.sym"):
        nid[0] += 1
        o.append("C {sym/%s} %d %d 0 %d {name=l%d lab=%s}\n" % (sym, px, py, rot, nid[0], name))

    def stublab(pc, vec, rot, name, sym="lab_pin.sym"):
        px, py = pc; ex, ey = px + vec[0], py + vec[1]
        o.append("N %d %d %d %d {}\n" % (px, py, ex, ey)); lab(ex, ey, rot, name, sym)

    # ---- gate net-labels (all exit LEFT, house convention) ----
    GATE = (
        ("invp", "clk"), ("invn", "clk"),
        ("swd1", "clkb"), ("sws1", "clkb"), ("swep1", "clkb"), ("swen1", "clk"),
        ("swd2", "clkb"), ("sws2", "clkb"), ("swep2", "clkb"), ("swen2", "clk"),
        ("Mhd", "clkb"), ("Mr2", "clkb"), ("Mr1", "clkb"),
        ("Mcp1", "outp"), ("Mcp2", "outn"), ("Mcn1", "outp"), ("Mcn2", "outn"),
    )
    for n, net in GATE:
        stublab(pin(n, "G"), (-30, 0), 2, net)
    stublab(pin("Min1", "G"), (-30, 0), 2, "vinp", "ipin.sym")
    stublab(pin("Min2", "G"), (-30, 0), 2, "vinn", "ipin.sym")

    # ---- internal net labels (on existing wires) ----
    lab(160, 440, 0, "clkb")                                           # inverter output spine
    for i, X in ((1, X1), (2, X2)):
        lab(X - 100, 240, 0, "sp%d" % i)                               # hold node (swd drain riser)
        lab(X + 20, 290, 0, "m%d" % i)                                 # sampling PMOS drain leg
        lab(X + 20, 450, 0, "d%d" % i)                                 # V-to-I drain
        lab(X + 210, 430, 0, "outp" if i == 1 else "outn")             # TG steer -> latch (label-routed)
    lab(pin("Mhd", "D")[0], 255, 0, "th")                              # latch head node

    # ---- output ports (stub up from the out buses, house style) ----
    onx = (pin("Mr2", "D")[0] + pin("Mcn1", "D")[0]) // 2
    opx = (pin("Mcn2", "D")[0] + pin("Mr1", "D")[0]) // 2
    for x, net in ((onx, "outn"), (opx, "outp")):
        o.append("N %d %d %d %d {}\n" % (x, OUT_Y, x, OUT_Y - 25))
        lab(x, OUT_Y - 25, 1, net, "opin.sym")

    # ---- bulk ties ----
    for n in ("swd1", "sws1", "Min1", "swen1", "swd2", "sws2", "Min2", "swen2",
              "invn", "Mr2", "Mcn1", "Mcn2", "Mr1"):                   # NMOS bulks -> VSS
        stublab(pin(n, "B"), (25, 0), 0, "VSS", "gnd.sym")
    for n in ("swep1", "swep2", "Mcp1", "Mcp2"):                       # bulk=vdd, source!=vdd
        stublab(pin(n, "B"), (25, 0), 0, "VDD", "vdd.sym")

    # ---- rails ----
    stublab((160, VDD_Y), (0, -28), 1, "VDD", "vdd.sym")
    stublab((300, VSS_Y), (0, 28), 3, "VSS", "gnd.sym")

    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, "current_sampling.sch"), "w", newline="\n").write("".join(o))
    print("wrote current_sampling.sch (compact, %d FETs + %d caps)" % (len(DEV), len(CAPS)))


if __name__ == "__main__":
    main()
