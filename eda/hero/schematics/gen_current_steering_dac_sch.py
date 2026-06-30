#!/usr/bin/env python3
"""Generate a compact, journal-style Xschem schematic for the BINARY-WEIGHTED CURRENT-STEERING
write-DAC (the current-mode topology benchmarked in eda/hero/run_write_dac.py :: net_current_steering).

Faithful to the simulated netlist (current_steering generator, 6-bit, full array drawn):
  XMref vbias vbias vdd vdd pfet W=1  L=0.5        # diode-connected reference PMOS
  Rref  vbias 0     147k                           # sets the unit current I_u
  XMb0  load  vbias vdd vdd pfet W=1  L=0.5        # bit 0  (W = 2^0)
  XMb1  load  vbias vdd vdd pfet W=2  L=0.5        # bit 1
  XMb2  load  vbias vdd vdd pfet W=4  L=0.5        # bit 2
  XMb3  load  vbias vdd vdd pfet W=8  L=0.5        # bit 3
  XMb4  load  vbias vdd vdd pfet W=16 L=0.5        # bit 4
  XMb5  load  vbias vdd vdd pfet W=32 L=0.5        # bit 5 (MSB)
  Rload load 0      776                            # sMTJ write load

The 6 binary-weighted PMOS branches share the vbias gate bus (mirror of Mref) and sum their drain
currents directly into the low-impedance 776 ohm load (current-mode, no buffer = its native form).
Devices use local cleaned symbols (sym/pfet.sym, sym/res.sym, sym/gnd.sym, sym/vdd.sym, sym/opin.sym).
"""
import os

PFET, RES = "sym/pfet.sym", "sym/res.sym"
# pin offsets (y increases downward)
P = {"p": {"S": (20, -30), "G": (-20, 0), "D": (20, 30), "B": (20, 0)},
     "r": {"P": (0, -30), "M": (0, 30)}}

# ---- layout grid -----------------------------------------------------------------------------
VDD_Y = 200          # VDD rail
DEV_Y = 300          # PMOS row (all current sources at the same height -> single gate bus)
GATE_Y = DEV_Y       # vbias bus runs through every gate pin
DRAIN_BUS_Y = 430    # horizontal "load" summing bus below the array
LOAD_DEV_Y = 520     # Rload resistor centre
VSS_Y = 610          # ground rail level for Rref / Rload bottoms

REF_X = 200          # reference PMOS column
ARR_X0 = 400         # first array column (bit 0 / LSB)
ARR_DX = 140         # column pitch
LOAD_X = ARR_X0 + 5 * ARR_DX + 130   # load resistor column (just right of the MSB branch)

# (name, type, x, y, W)
BITS = [0, 1, 2, 3, 4, 5]
DEV = [("Mref", "p", REF_X, DEV_Y, 1)]
DEV += [("Mb%d" % b, "p", ARR_X0 + b * ARR_DX, DEV_Y, 2 ** b) for b in BITS]
DT = {n: t for n, t, *_ in DEV}
XY = {n: (x, y) for n, t, x, y, w in DEV}


def pin(n, p):
    x, y = XY[n]
    dx, dy = P[DT[n]][p]
    return x + dx, y + dy


def main():
    o = ["v {xschem version=3.4.4 file_version=1.2}\nG {}\nK {}\nV {}\nS {}\nE {}\n"]

    # --- PMOS devices (reference + binary-weighted array) ---
    for n, t, x, y, w in DEV:
        o.append("C {%s} %d %d 0 0 {name=%s model=sky130_fd_pr__pfet_01v8 W=%g L=0.5 nf=1 m=1}\n"
                 % (PFET, x, y, n, w))
    # --- reference resistor Rref (vbias -> gnd) and load resistor Rload (load -> gnd) ---
    o.append("C {%s} %d %d 0 0 {name=Rref value=147k}\n" % (RES, REF_X, LOAD_DEV_Y))
    o.append("C {%s} %d %d 0 0 {name=Rload value=776}\n" % (RES, LOAD_X, LOAD_DEV_Y))

    W = []
    # --- VDD rail + every PMOS source up to it ---
    src_xs = [pin(n, "S")[0] for n, *_ in DEV]
    W.append((min(src_xs), VDD_Y, max(src_xs), VDD_Y))
    for n, *_ in DEV:
        sx, sy = pin(n, "S")
        W.append((sx, sy, sx, VDD_Y))
        # bulk -> source (short tie)
        bx, by = pin(n, "B")
        W.append((bx, by, sx, sy))

    # --- vbias gate bus: Mref drain -> Mref gate (diode) -> across to all array gates ---
    mref_d = pin("Mref", "D")          # (REF_X+20, DEV_Y+30)
    mref_g = pin("Mref", "G")          # (REF_X-20, DEV_Y)
    # diode connection: drain down then left then up to the gate, forming vbias node on the left
    W.append((mref_d[0], mref_d[1], mref_d[0], GATE_Y + 60))         # drain stub down
    W.append((mref_g[0] - 60, GATE_Y + 60, mref_d[0], GATE_Y + 60))  # along the bottom
    W.append((mref_g[0] - 60, GATE_Y, mref_g[0] - 60, GATE_Y + 60))  # up to gate level
    W.append((mref_g[0] - 60, GATE_Y, mref_g[0], GATE_Y))            # into Mref gate
    # vbias bus runs right at gate level to every array gate
    last_g = pin("Mb5", "G")
    W.append((mref_g[0] - 60, GATE_Y, last_g[0], GATE_Y))
    for b in BITS:
        gx, gy = pin("Mb%d" % b, "G")
        # bus already at gate_y; the small connect from bus to gate pin is collinear (same y) -> covered
        # but the array gate pins sit at gx (=x-20); bus passes through them, so nothing extra needed.
        pass

    # --- Rref: vbias node -> Rref.P, Rref.M -> gnd ---
    rref_p = (REF_X, LOAD_DEV_Y + P["r"]["P"][1])   # top of Rref
    rref_m = (REF_X, LOAD_DEV_Y + P["r"]["M"][1])   # bottom of Rref
    # tie vbias bus down to Rref: from the diode bottom corner (mref_g[0]-60, GATE_Y+60) down to bus x=REF_X
    W.append((mref_g[0] - 60, GATE_Y + 60, REF_X, GATE_Y + 60))      # bus corner -> over Rref column
    W.append((REF_X, GATE_Y + 60, REF_X, rref_p[1]))                 # down to Rref top
    W.append((REF_X, rref_m[1], REF_X, VSS_Y))                       # Rref bottom -> gnd rail level

    # --- drain summing bus: every array drain -> DRAIN_BUS_Y -> right to load column ---
    arr_drain_xs = [pin("Mb%d" % b, "D")[0] for b in BITS]
    for b in BITS:
        dx, dy = pin("Mb%d" % b, "D")
        W.append((dx, dy, dx, DRAIN_BUS_Y))                         # drain down to bus
    W.append((min(arr_drain_xs), DRAIN_BUS_Y, LOAD_X, DRAIN_BUS_Y))  # the summing bus -> load col
    # load column: bus -> Rload top, Rload bottom -> gnd
    rload_p = (LOAD_X, LOAD_DEV_Y + P["r"]["P"][1])
    rload_m = (LOAD_X, LOAD_DEV_Y + P["r"]["M"][1])
    W.append((LOAD_X, DRAIN_BUS_Y, LOAD_X, rload_p[1]))
    W.append((LOAD_X, rload_m[1], LOAD_X, VSS_Y))

    for seg in W:
        o.append("N %d %d %d %d {}\n" % seg)

    # --- labels ---
    nid = [0]

    def lab(px, py, rot, name, sym="lab_pin.sym"):
        nid[0] += 1
        o.append("C {sym/%s} %d %d 0 %d {name=l%d lab=%s}\n" % (sym, px, py, rot, nid[0], name))

    def stublab(pc, vec, rot, name, sym="lab_pin.sym"):
        px, py = pc
        ex, ey = px + vec[0], py + vec[1]
        o.append("N %d %d %d %d {}\n" % (px, py, ex, ey))
        lab(ex, ey, rot, name, sym)

    def txt(s, x, y, size=0.3, layer=None):
        tag = "{layer=%d}" % layer if layer else "{}"
        o.append("T {%s} %d %d 0 0 %g %g %s\n" % (s, x, y, size, size, tag))

    # rails: VDD at top-left of the rail, grounds for Rref and Rload
    lab((min(src_xs), VDD_Y), (0, 0), 0, "VDD", "vdd.sym") if False else None
    stublab((min(src_xs), VDD_Y), (0, -28), 1, "VDD", "vdd.sym")
    stublab((REF_X, VSS_Y), (0, 0), 0, "VSS", "gnd.sym")
    stublab((LOAD_X, VSS_Y), (0, 0), 0, "VSS", "gnd.sym")

    # output node "load" (the write line into the sMTJ) -- on the summing bus, broken out as a port
    lab(LOAD_X, DRAIN_BUS_Y, 0, "load", "opin.sym")

    # internal node names
    txt("vbias", mref_g[0] - 56, GATE_Y - 8, 0.22)

    # (module-group titles are redrawn as colored dashed box captions by postprocess; not in-schematic)
    # per-branch bit weights above each array device (LSB .. MSB)
    for b in BITS:
        gx, gy = XY["Mb%d" % b]
        txt("b%d (W=%d)" % (b, 2 ** b), gx - 28, DEV_Y - 58, 0.2)
    txt("Iu", REF_X - 24, DEV_Y - 58, 0.2)

    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, "current_steering_dac.sch"), "w").write("".join(o))
    print("wrote current_steering_dac.sch (%d devices: %d PMOS + 2 R)"
          % (len(DEV) + 2, len(DEV)))


if __name__ == "__main__":
    main()
