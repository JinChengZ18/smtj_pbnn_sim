#!/usr/bin/env python3
"""Generate a compact, journal-style Xschem schematic for the Yoon-style sMTJ p-bit
driver chain (sMTJ/NMOS divider -> variable-threshold inverter -> output inverter).

Matches the phase-5 full-chain deck emitted by eda/design_survey/repro/yoon_pbit_driver.py
(measure_chain): 1 sMTJ + 11 FETs.  Device names are the deck names minus the X spice-
prefix (the symbol re-adds it); net names (vdiv, Vp1/Vp2/Vn1/Vn2, vtcout, final, vb,
enp1/enp2/enn1/enn2) are the deck's.  Widths are the run-selected values recorded in
yoon_pbit_driver_summary.json: divider NMOS W=1 um (the paper's 1/3/9/27-um row, W=1
selected by centering margin); VTC leg widths wp=(0.42, 13), wn=(0.42, 2.1) um with each
leg gated by a series enable device of 2x the leg width; output inverter 2/0.84 um.
Displayed W = EFFECTIVE width (deck bin-W x m), so enable devices read 0.84/26/0.84/4.2.

sMTJ: local sym/sot_mtj.sym = the committed two-state OSDI read branch (R_P=4.9k,
R_AP=9.8k) from VDD to the divider node; the SOT track is unbiased in the deck (wr tied
to com), drawn as one track terminal wired to vdiv and the other label-routed to vdiv.  The deck's state/offset
sources (Vst, Ven*, Vo*) are instrumentation and are not drawn; enable gates carry their
net labels.  House conventions (gen_strongarm_sch.py / gen_current_sampling_sch.py):
gate labels exit left; NMOS bulks -> VSS gnd stubs right; PMOS bulk tied to source only
where source==vdd (VPI1/VPI2 have bulk=vdd but source=vtcout -> explicit VDD stubs).
VPE1/VPE2 are drawn with D/S vertically swapped (deck order d=vdd, s=Vp; symmetric
devices), as are VPI1/VPI2 (deck d=Vp, s=vtcout); the drawn net connectivity is exact.
"""
import os

NFET, PFET, SOT = "sym/nfet.sym", "sym/pfet.sym", "sym/sot_mtj.sym"
# pin offsets (rot 0), from the symbol bounding boxes
P = {"n": {"D": (20, -30), "G": (-20, 0), "S": (20, 30), "B": (20, 0)},
     "p": {"S": (20, -30), "G": (-20, 0), "D": (20, 30), "B": (20, 0)}}
MTJ = {"Tin": (-40, 20), "Tsl": (40, 20), "Trd": (0, -40)}

VDD_Y, VSS_Y = 110, 630
XM = 200                                # divider column (sMTJ + NMOS centre line)
XA, XB = 430, 600                       # VTC leg-1 / leg-2 columns
XO, GJX = 800, 760                      # output inverter column / its gate-join x
PE_Y, PI_Y, NI_Y, NE_Y = 210, 320, 440, 550   # VTC rows
BUS_Y = 380                             # vtcout bus (also the inverter mid-height)

# (name, type, x, y, W_eff) -- W_eff = deck bin-W x m (yoon_pbit_driver_summary.json)
DEV = [
    ("DN",   "n", XM - 20, 440, 1),     # divider NMOS, paper row W=1 um selected
    ("VPE1", "p", XA, PE_Y, 0.84),      # PU leg 1 enable (2 x wp1)
    ("VPI1", "p", XA, PI_Y, 0.42),      # PU leg 1 input (wp1)
    ("VNI1", "n", XA, NI_Y, 0.42),      # PD leg 1 input (wn1)
    ("VNE1", "n", XA, NE_Y, 0.84),      # PD leg 1 enable (2 x wn1)
    ("VPE2", "p", XB, PE_Y, 26),        # PU leg 2 enable (2 x wp2)
    ("VPI2", "p", XB, PI_Y, 13),        # PU leg 2 input (wp2)
    ("VNI2", "n", XB, NI_Y, 2.1),       # PD leg 2 input (wn2)
    ("VNE2", "n", XB, NE_Y, 4.2),       # PD leg 2 enable (2 x wn2)
    ("BP",   "p", XO, PI_Y, 2),         # output inverter
    ("BN",   "n", XO, NI_Y, 0.84),
]
DT = {n: t for n, t, *_ in DEV}
XY = {n: (x, y) for n, t, x, y, w in DEV}
MTJ_XY = (XM, 190)


def pin(n, p):
    x, y = XY[n]; dx, dy = P[DT[n]][p]; return x + dx, y + dy


def mpin(p):
    dx, dy = MTJ[p]; return MTJ_XY[0] + dx, MTJ_XY[1] + dy


def main():
    o = ["v {xschem version=3.4.4 file_version=1.2}\nG {}\nK {}\nV {}\nS {}\nE {}\n"]
    o.append("C {%s} %d %d 0 0 {name=Nsm}\n" % (SOT, MTJ_XY[0], MTJ_XY[1]))
    for n, t, x, y, w in DEV:
        o.append("C {%s} %d %d 0 0 {name=%s model=sky130_fd_pr__%sfet_01v8 W=%g L=0.15 nf=1 m=1}\n"
                 % (NFET if t == "n" else PFET, x, y, n, ("n" if t == "n" else "p"), w))

    W = []
    # ---- rails ----
    W.append((140, VDD_Y, pin("BP", "S")[0], VDD_Y))
    W.append((XM, VSS_Y, pin("BN", "S")[0], VSS_Y))

    # ---- divider: sMTJ read branch VDD -> vdiv; SOT track tied (wr = com) ----
    # Tsl wired down into vdiv; Tin label-routed to vdiv (avoids a closed-loop
    # rectangle under the symbol; the tie is stated by the V_wr = 0 note).
    W.append(mpin("Trd") + (XM, VDD_Y))
    W.append(mpin("Tsl") + (mpin("Tsl")[0], 260))
    W.append((mpin("Tsl")[0], 260, XM, 260))
    W.append((XM, 260) + pin("DN", "D"))               # vdiv riser
    W.append(pin("DN", "S") + (XM, VSS_Y))

    # ---- VTC cell: 2 PU + 2 PD legs, enable devices toward the rails ----
    for X in (XA, XB):
        xc = X + 20
        W.append((xc, PE_Y - 30, xc, VDD_Y))           # PE source -> VDD
        W.append((xc, PE_Y, xc, PE_Y - 30))            # PE bulk = source = vdd
        W.append((xc, PE_Y + 30, xc, PI_Y - 30))       # Vp node (enable -> input)
        W.append((xc, PI_Y + 30, xc, BUS_Y))           # input -> vtcout bus
        W.append((xc, BUS_Y, xc, NI_Y - 30))           # bus -> PD input
        W.append((xc, NI_Y + 30, xc, NE_Y - 30))       # Vn node (input -> enable)
        W.append((xc, NE_Y + 30, xc, VSS_Y))           # NE source -> VSS
    W.append((XA + 20, BUS_Y, XB + 20, BUS_Y))         # vtcout bus, split at junctions
    W.append((XB + 20, BUS_Y, GJX, BUS_Y))             # bus -> output inverter gates

    # ---- output inverter ----
    W.append(pin("BP", "S") + (pin("BP", "S")[0], VDD_Y))
    W.append(pin("BP", "B") + pin("BP", "S"))          # bulk = source = vdd
    W.append(pin("BP", "D") + (XO + 20, BUS_Y))        # final node, split at opin tap
    W.append((XO + 20, BUS_Y) + pin("BN", "D"))
    W.append(pin("BN", "S") + (pin("BN", "S")[0], VSS_Y))
    W.append(pin("BP", "G") + (GJX, PI_Y))             # gate join (vtcout)
    W.append((GJX, PI_Y, GJX, BUS_Y))
    W.append((GJX, BUS_Y, GJX, NI_Y))
    W.append((GJX, NI_Y) + pin("BN", "G"))

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
    for n, net in (("VPE1", "enp1"), ("VPE2", "enp2"), ("VNE1", "enn1"), ("VNE2", "enn2"),
                   ("VPI1", "vdiv"), ("VPI2", "vdiv"), ("VNI1", "vdiv"), ("VNI2", "vdiv")):
        stublab(pin(n, "G"), (-30, 0), 2, net)
    stublab(pin("DN", "G"), (-30, 0), 2, "vb", "ipin.sym")
    stublab(mpin("Tin"), (-30, 0), 2, "vdiv")          # SOT-track tie (wr = com)

    # ---- internal net labels (on existing wires) ----
    lab(XM, 330, 0, "vdiv")                            # divider node riser
    lab((XA + XB) // 2, BUS_Y, 0, "vtcout")            # VTC output bus
    for X, sfx in ((XA, "1"), (XB, "2")):
        lab(X + 20, 265, 0, "Vp" + sfx)                # enable/input mid nodes
        lab(X + 20, 495, 0, "Vn" + sfx)

    # ---- output port ----
    stublab((XO + 20, BUS_Y), (40, 0), 0, "final", "opin.sym")

    # ---- bulk ties ----
    for n in ("DN", "VNI1", "VNE1", "VNI2", "VNE2", "BN"):       # NMOS bulks -> VSS
        stublab(pin(n, "B"), (25, 0), 0, "VSS", "gnd.sym")
    for n in ("VPI1", "VPI2"):                         # bulk=vdd, source!=vdd
        stublab(pin(n, "B"), (25, 0), 0, "VDD", "vdd.sym")

    # ---- rails ----
    stublab((140, VDD_Y), (0, -28), 1, "VDD", "vdd.sym")
    stublab((280, VSS_Y), (0, 28), 3, "VSS", "gnd.sym")

    # ---- sMTJ two-state annotation (committed device: R_P=4.9k, R_AP=9.8k) ----
    o.append("T {R_P = 4.9k} 52 158 0 0 0.2 0.2 {}\n")
    o.append("T {R_AP = 9.8k} 52 178 0 0 0.2 0.2 {}\n")
    o.append("T {SOT track tied:} 28 272 0 0 0.18 0.18 {}\n")
    o.append("T {V_wr = 0} 28 292 0 0 0.18 0.18 {}\n")

    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, "yoon_pbit_driver.sch"), "w", newline="\n").write("".join(o))
    print("wrote yoon_pbit_driver.sch (compact, 1 sMTJ + %d FETs)" % len(DEV))


if __name__ == "__main__":
    main()
