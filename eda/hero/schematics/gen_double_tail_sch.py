#!/usr/bin/env python3
"""Generate a compact, journal-style Xschem schematic for the DOUBLE-TAIL charge-steering
dynamic comparator (matches eda/hero/comparators/double_tail.spice -- 15 devices).

Two clk-gated tails. Stage 1 (charge-steering pre-amplifier): tail Mt1 + NMOS input pair
Min1/Min2 discharging intermediate nodes di/dib, precharged high by PMOS Mpc1/Mpc2 when clk
is low. Stage 2 (latch): own tail Mt2, NMOS input pair Ml1/Ml2 driven by di/dib, a cross-
coupled NMOS pair Mcn1/Mcn2 + PMOS pair Mcp1/Mcp2, and PMOS precharge Mpo1/Mpo2 that pull
outp/outn high when clk is low.

Devices use the local cleaned sky130 symbols (sym/nfet.sym, sym/pfet.sym = name + W/L kept).
Following the house convention used for the StrongARM figure, the cross-couple feedback and the
di/dib -> latch-input coupling are drawn as gate net-labels (outp/outn/di/dib) rather than long
wrap-around wires -- a fully drawn cross-couple needs routing room that defeats compactness. All
15 transistors are emitted explicitly; only the differential feedback nets are label-routed.
"""
import os

NFET, PFET = "sym/nfet.sym", "sym/pfet.sym"
# pin offsets (rot 0), from the symbol bounding boxes
P = {"n": {"D": (20, -30), "G": (-20, 0), "S": (20, 30), "B": (20, 0)},
     "p": {"S": (20, -30), "G": (-20, 0), "D": (20, 30), "B": (20, 0)}}

# ---- compact layout grid (y increases downward) ----
# Stage-1 legs:   di @ x=210 , dib @ x=390
# Stage-2 legs:   outn @ x=640,790 , outp @ x=970,1120
PMOS_Y, NMOS_Y = 230, 470
T1_Y, T2_Y = 660, 660
VDD_Y, VSS_Y = 110, 820

# (name, type, x, y, W)
DEV = [
    # ---- Stage 1: charge-steering pre-amplifier ----
    ("Mpc1", "p", 210, PMOS_Y, 2), ("Mpc2", "p", 390, PMOS_Y, 2),   # precharge di/dib
    ("Min1", "n", 210, NMOS_Y, 4), ("Min2", "n", 390, NMOS_Y, 4),   # input pair (W={win})
    ("Mt1",  "n", 300, T1_Y, 4),                                     # first tail
    # ---- Stage 2: latch ----
    ("Mcp1", "p", 640, PMOS_Y, 2), ("Mpo2", "p", 790, PMOS_Y, 2),   # xc-PMOS(outn) | precharge outn
    ("Mpo1", "p", 970, PMOS_Y, 2), ("Mcp2", "p", 1120, PMOS_Y, 2),  # precharge outp | xc-PMOS(outp)
    ("Ml1",  "n", 640, NMOS_Y, 2), ("Mcn1", "n", 790, NMOS_Y, 1),   # latch-in(outn) | xc-NMOS(outn)
    ("Mcn2", "n", 970, NMOS_Y, 1), ("Ml2",  "n", 1120, NMOS_Y, 2),  # xc-NMOS(outp) | latch-in(outp)
    ("Mt2",  "n", 880, T2_Y, 4),                                     # second tail
]
DT = {n: t for n, t, *_ in DEV}
XY = {n: (x, y) for n, t, x, y, w in DEV}


def pin(n, p):
    x, y = XY[n]; dx, dy = P[DT[n]][p]; return x + dx, y + dy


def main():
    o = ["v {xschem version=3.4.4 file_version=1.2}\nG {}\nK {}\nV {}\nS {}\nE {}\n"]
    for n, t, x, y, w in DEV:
        o.append("C {%s} %d %d 0 0 {name=%s model=sky130_fd_pr__%sfet_01v8 W=%g L=0.15 nf=1 m=1}\n"
                 % (NFET if t == "n" else PFET, x, y, n, ("n" if t == "n" else "p"), w))

    W = []
    # ---- rails ----
    W.append((150, VDD_Y, 1180, VDD_Y))                 # VDD rail (spans both stages)
    W.append((280, VSS_Y, 920, VSS_Y))                  # VSS rail (under the two tails)

    # ---- all PMOS sources -> VDD ----
    for n in ("Mpc1", "Mpc2", "Mcp1", "Mpo2", "Mpo1", "Mcp2"):
        px, py = pin(n, "S"); W.append((px, py, px, VDD_Y))

    # ===================== Stage 1 =====================
    # di leg: Mpc1.D -- Min1.D ; dib leg: Mpc2.D -- Min2.D
    W.append(pin("Mpc1", "D") + pin("Min1", "D"))
    W.append(pin("Mpc2", "D") + pin("Min2", "D"))
    # input-pair sources -> s1 node -> Mt1 drain
    s1l, s1r, t1d = pin("Min1", "S"), pin("Min2", "S"), pin("Mt1", "D")
    SY1 = 600
    W += [(s1l[0], s1l[1], s1l[0], SY1), (s1r[0], s1r[1], s1r[0], SY1),
          (s1l[0], SY1, s1r[0], SY1), (t1d[0], SY1, t1d[0], t1d[1])]
    # Mt1 source -> VSS
    t1s = pin("Mt1", "S"); W.append((t1s[0], t1s[1], t1s[0], VSS_Y))

    # ===================== Stage 2 =====================
    # outn node: join drains of Mcp1,Mpo2 (top) and Ml1,Mcn1 (bottom)
    OUTN_TOPY, OUTN_BOTY = 320, 380
    for n in ("Mcp1", "Mpo2"):
        px, py = pin(n, "D"); W.append((px, py, px, OUTN_TOPY))
    W.append((pin("Mcp1", "D")[0], OUTN_TOPY, pin("Mpo2", "D")[0], OUTN_TOPY))
    for n in ("Ml1", "Mcn1"):
        px, py = pin(n, "D"); W.append((px, py, px, OUTN_BOTY))
    W.append((pin("Ml1", "D")[0], OUTN_BOTY, pin("Mcn1", "D")[0], OUTN_BOTY))
    # vertical spine tying outn top-row to bottom-row (on the Mpo2 / Mcn1 inner column @ x=810)
    outn_x = pin("Mpo2", "D")[0]
    W.append((outn_x, OUTN_TOPY, outn_x, OUTN_BOTY))

    # outp node: join drains of Mpo1,Mcp2 (top) and Mcn2,Ml2 (bottom)
    for n in ("Mpo1", "Mcp2"):
        px, py = pin(n, "D"); W.append((px, py, px, OUTN_TOPY))
    W.append((pin("Mpo1", "D")[0], OUTN_TOPY, pin("Mcp2", "D")[0], OUTN_TOPY))
    for n in ("Mcn2", "Ml2"):
        px, py = pin(n, "D"); W.append((px, py, px, OUTN_BOTY))
    W.append((pin("Mcn2", "D")[0], OUTN_BOTY, pin("Ml2", "D")[0], OUTN_BOTY))
    outp_x = pin("Mcn2", "D")[0]
    W.append((outp_x, OUTN_TOPY, outp_x, OUTN_BOTY))

    # all Stage-2 NMOS sources -> s2 node -> Mt2 drain
    SY2 = 600
    n2 = ("Ml1", "Mcn1", "Mcn2", "Ml2")
    for n in n2:
        px, py = pin(n, "S"); W.append((px, py, px, SY2))
    W.append((pin("Ml1", "S")[0], SY2, pin("Ml2", "S")[0], SY2))
    t2d = pin("Mt2", "D"); W.append((t2d[0], SY2, t2d[0], t2d[1]))
    t2s = pin("Mt2", "S"); W.append((t2s[0], t2s[1], t2s[0], VSS_Y))

    for seg in W:
        o.append("N %d %d %d %d {}\n" % seg)

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

    # ---- ALL gate net-labels exit to the LEFT (rot 2) -- the gate pin is on the device's
    # ---- left edge, so a leftward stub keeps every label clear of the device body. ----
    GATE = (
        ("Mt1", "clk"), ("Mt2", "clk"),
        ("Mpc1", "clk"), ("Mpc2", "clk"), ("Mpo2", "clk"), ("Mpo1", "clk"),
        ("Mcn1", "outp"), ("Mcn2", "outn"), ("Mcp1", "outp"), ("Mcp2", "outn"),
        ("Ml1", "di"), ("Ml2", "dib"),
    )
    for n, net in GATE:
        stublab(pin(n, "G"), (-30, 0), 2, net)

    # ---------- Stage-1 inputs (ipin, also leftward) ----------
    stublab(pin("Min1", "G"), (-30, 0), 2, "vinp", "ipin.sym")
    stublab(pin("Min2", "G"), (-30, 0), 2, "vinn", "ipin.sym")

    # ---------- di / dib internal nodes (labels on the Stage-1 legs) ----------
    # tap the di/dib legs at a clear midpoint and mark them
    di_y = (PMOS_Y + 30 + NMOS_Y - 30) // 2
    lab(pin("Mpc1", "D")[0], di_y, 0, "di")
    lab(pin("Mpc2", "D")[0], di_y, 0, "dib")

    # ---------- output ports ----------
    lab(outn_x, OUTN_TOPY - 25, 1, "outn", "opin.sym")
    lab(outp_x, OUTN_TOPY - 25, 1, "outp", "opin.sym")
    # short stub up to the opin so it sits clear of the outn/outp spines
    o.append("N %d %d %d %d {}\n" % (outn_x, OUTN_TOPY, outn_x, OUTN_TOPY - 25))
    o.append("N %d %d %d %d {}\n" % (outp_x, OUTN_TOPY, outp_x, OUTN_TOPY - 25))

    # ---------- bulk ties ----------
    # all NMOS bulks -> VSS (short stub right)
    for n in ("Min1", "Min2", "Ml1", "Mcn1", "Mcn2", "Ml2", "Mt1", "Mt2"):
        stublab(pin(n, "B"), (25, 0), 0, "VSS", "gnd.sym")
    # all PMOS bulks -> source (short tie up to its own source stub)
    for n in ("Mpc1", "Mpc2", "Mcp1", "Mpo2", "Mpo1", "Mcp2"):
        bx, by = pin(n, "B"); sx, sy = pin(n, "S"); W2 = (bx, by, sx, sy)
        o.append("N %d %d %d %d {}\n" % W2)

    # ---------- rails ----------
    stublab((150, VDD_Y), (0, -28), 1, "VDD", "vdd.sym")
    stublab((300 + 20, VSS_Y), (0, 28), 3, "VSS", "gnd.sym")

    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, "double_tail.sch"), "w").write("".join(o))
    print("wrote double_tail.sch (compact, %d devices)" % len(DEV))


if __name__ == "__main__":
    main()
