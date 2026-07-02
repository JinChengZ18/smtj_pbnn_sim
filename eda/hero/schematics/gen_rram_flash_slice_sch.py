#!/usr/bin/env python3
"""Generate a compact, journal-style Xschem schematic for the 3-bit FLASH-ADC readout
SLICE of the RRAM XNOR-BNN macro (Yin et al., IEEE TED 67(10):4185, 2020; open
preprint arXiv:1909.07514), matching the simulated same-flow reproduction
eda/design_survey/repro/rram_flash_slice.py (netlist builders ladder(), mux(),
7x sa_instance()).

Topology drawn 1:1 from the reproduction netlist:
  * 7-tap reference ladder on the dedicated vddl rail (100 uA standing current):
    RlT (6.75k) - Rl7..Rl2 (6x 750) - RlB (6.75k), with the 0.5 pF per-tap
    decoupling caps Cdec1..7 the script sizes against StrongARM strobe kickback.
  * SEVEN comparators as compact comp.sym blocks (house convention, cf.
    sar_readout.sch: the StrongARM transistor level is its own figure,
    strongarm_sa.sch, 11 FETs each): INP = shared mux node vin, INN = tap k,
    OUT = thermometer bit t_k (netlist op_k; the complementary on_k of the
    differential latch is not drawn at block level). All 7 strobed in parallel.
  * 8:1 CMOS transmission-gate input mux: channels 0 (selected) and 7 (off) drawn,
    ch1..ch6 elided as dots -- all 8 are identical columns: R_TI = 1225 ohm (TIA
    Thevenin source resistance) -> TG nfet 2/0.15 + pfet 4/0.15 (repo TG sizing).
    Netlist select nets mseln0/mselp0 (on) and moffn/moffp (off channels) are
    drawn as per-channel selects sel0/sel0b and sel7/sel7b; the off channels'
    shared dummy source dum0 is drawn as its column input (col7).
  * C_ADC = 3.5 pF (= 7 x C_tap) kick-matching cap DIRECTLY on the shared vin node.
Offset-injection sources (the per-comparator Vth MC sources), the swept input
source Vsrc and the static select/dummy drivers are testbench instrumentation and
are not drawn.

House conventions (gen_strongarm_sch.py / gen_current_sampling_sch.py): local
cleaned sky130 symbols; gate labels exit left; NMOS bulks -> GND stubs right; TG
PMOS bulks -> VDD stubs (body_p=vdd in the netlist); grounds are node 0 ->
gnd.sym lab=GND. vin is bus-routed: the vertical riser crosses the seven tap
wires without junctions (standard flash-ADC drawing convention).
"""
import os

RES, CAP = "sym/res.sym", "sym/cap.sym"
NFET, PFET, COMP = "sym/nfet.sym", "sym/pfet.sym", "sym/comp.sym"
# pin offsets (rot 0), from the symbol bounding boxes
P = {"n": {"D": (20, -30), "G": (-20, 0), "S": (20, 30), "B": (20, 0)},
     "p": {"S": (20, -30), "G": (-20, 0), "D": (20, 30), "B": (20, 0)},
     "res": {"P": (0, -30), "M": (0, 30)},
     "cap": {"P": (0, -30), "M": (0, 30)},
     "comp": {"INP": (-40, -15), "INN": (-40, 15), "OUT": (45, 0)}}

LADX, CDX = 160, 100            # ladder column, per-tap decap column
BUSX, CMPX, OUTX = 520, 620, 700  # vin riser, comparator column, thermometer pins
PITCH, YTOP = 110, 120          # comparator pitch, SA7 (top) center y
XA, XB = 350, 710               # mux channel columns: ch0 (selected), ch7 (off)
MUX_IN, RAIL_Y = 970, 1200      # mux column-input row, shared vin rail


def tapy(k):                    # ladder tap k (1..7), tap7 at top (highest V)
    return YTOP + 15 + (7 - k) * PITCH


def compy(k):                   # comparator k center (INN at compy+15 = tapy(k))
    return YTOP + (7 - k) * PITCH


def main():
    o = ["v {xschem version=3.4.4 file_version=1.2}\nG {}\nK {}\nV {}\nS {}\nE {}\n"]

    def res(name, x, y, val):
        o.append("C {%s} %d %d 0 0 {name=%s value=%s m=1}\n" % (RES, x, y, name, val))

    def cap(name, x, y, val):
        o.append("C {%s} %d %d 0 0 {name=%s value=%s m=1}\n" % (CAP, x, y, name, val))

    def fet(name, sym, x, y, w):
        o.append("C {%s} %d %d 0 0 {name=%s model=sky130_fd_pr__%sfet_01v8 W=%g L=0.15 nf=1 m=1}\n"
                 % (sym, x, y, name, "n" if sym == NFET else "p", w))

    # ---- devices: reference ladder (netlist ladder(): RlT/Rl7..Rl2/RlB + Cdec1..7)
    res("RlT", LADX, 75, "6.75k")
    for k in range(7, 1, -1):
        res("Rl%d" % k, LADX, tapy(k) + 55, "750")
    res("RlB", LADX, 850, "6.75k")
    for k in range(1, 8):
        cap("Cdec%d" % k, CDX, tapy(k) + 30, "0.5p")

    # ---- devices: 7 comparators (compact blocks; netlist = StrongARM sa_instance k)
    for k in range(1, 8):
        o.append("C {%s} %d %d 0 0 {name=SA%d}\n" % (COMP, CMPX, compy(k), k))

    # ---- devices: mux channels 0 and 7 (of 8) + kick-matching input cap
    for tag, X in (("0", XA), ("7", XB)):
        res("Rti%s" % tag, X, 1020, "1225")
        fet("TGp%s" % tag, PFET, X - 70, 1110, 4)
        fet("TGn%s" % tag, NFET, X + 70, 1110, 2)
    cap("Cadc", 450, 1230, "3.5p")

    W = []
    # ---- ladder spine (vddl at top -> RlT -> tap7 .. tap1 -> RlB -> GND)
    W.append((LADX, 105, LADX, 135))                       # RlT M -> tap7
    for k in range(7, 1, -1):                              # tap_k -> Rl_k -> tap_{k-1}
        W.append((LADX, tapy(k), LADX, tapy(k) + 25))
        W.append((LADX, tapy(k) + 85, LADX, tapy(k) + 110))
    W.append((LADX, 795, LADX, 820))                       # tap1 -> RlB P
    # ---- taps: decap stub (left) + reference wire to comparator INN (right)
    for k in range(1, 8):
        y = tapy(k)
        W.append((CDX, y, LADX, y))                        # Cdec_k P -> tap_k
        W.append((LADX, y, CMPX - 40, y))                  # tap_k -> SA_k INN
    # ---- shared vin: riser + INP stubs + comparator outputs
    W.append((BUSX, 105, BUSX, RAIL_Y))                    # vin riser (crosses taps)
    for k in range(1, 8):
        yc = compy(k)
        W.append((BUSX, yc - 15, CMPX - 40, yc - 15))      # vin -> SA_k INP
        W.append((CMPX + 45, yc, OUTX, yc))                # SA_k OUT -> t_k
    # ---- mux channels: col -> R_TI -> TG (pfet || nfet) -> vin rail
    for X in (XA, XB):
        W.append((X, MUX_IN, X, 990))                      # col pin -> Rti P
        W.append((X, 1050, X, 1080))                       # Rti M -> min node
        W.append((X - 50, 1080, X + 90, 1080))             # min: pfet S + nfet D
        W.append((X - 50, 1140, X + 90, 1140))             # out: pfet D + nfet S
        W.append((X + 20, 1140, X + 20, RAIL_Y))           # drop to vin rail
    W.append((XA + 20, RAIL_Y, XB + 20, RAIL_Y))           # vin rail
    for seg in W:
        o.append("N %d %d %d %d {}\n" % seg)

    nid = [0]

    def lab(px, py, rot, name, sym="lab_pin.sym"):
        nid[0] += 1
        o.append("C {sym/%s} %d %d 0 %d {name=l%d lab=%s}\n" % (sym, px, py, rot, nid[0], name))

    def stublab(pc, vec, rot, name, sym="lab_pin.sym"):
        px, py = pc
        ex, ey = px + vec[0], py + vec[1]
        o.append("N %d %d %d %d {}\n" % (px, py, ex, ey))
        lab(ex, ey, rot, name, sym)

    # ---- ladder rails + tap net names
    stublab((LADX, 45), (0, -28), 1, "vddl", "vdd.sym")    # dedicated ladder rail
    stublab((LADX, 880), (0, 25), 3, "GND", "gnd.sym")
    for k in range(1, 8):
        lab(240, tapy(k), 0, "tap%d" % k)
        stublab((CDX, tapy(k) + 60), (0, 15), 3, "GND", "gnd.sym")
    # ---- comparator IO
    for k in range(1, 8):
        lab(OUTX, compy(k), 0, "t%d" % k, "opin.sym")      # thermometer bits
    lab(BUSX, 870, 0, "vin")                               # shared input node
    # ---- mux channels
    for tag, X in (("0", XA), ("7", XB)):
        lab(X, MUX_IN, 1, "col%s" % tag, "ipin.sym")
        stublab((X - 90, 1110), (-30, 0), 2, "sel%sb" % tag)          # pfet gate
        stublab((X + 50, 1110), (-30, 0), 2, "sel%s" % tag)           # nfet gate
        stublab((X - 50, 1110), (25, 0), 0, "VDD", "vdd.sym")         # pfet bulk
        stublab((X + 90, 1110), (25, 0), 0, "GND", "gnd.sym")         # nfet bulk
    stublab((450, 1260), (0, 15), 3, "GND", "gnd.sym")     # Cadc ground
    # ---- annotations: elided channels 1..6, parallel strobe
    o.append("T {. . .} 440 1020 0 0 0.4 0.4 {}\n")
    o.append("T {strobed in parallel (clk)} 610 50 0 0 0.24 0.24 {}\n")

    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, "rram_flash_slice.sch"), "w", newline="\n").write("".join(o))
    print("wrote rram_flash_slice.sch (9+2 res, 7+1 caps, 4 TG FETs, 7 comparator blocks)")


if __name__ == "__main__":
    main()
