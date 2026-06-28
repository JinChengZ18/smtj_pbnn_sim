"""Ground the two remaining CMOS-peripheral *energy* placeholders (e_dac_step,
e_count_inc) in sky130, replacing the 28 nm order-of-magnitude guesses in
``src/smtj_pbnn_sim/ppa/tech_params.py``.

Method (honest about what is measured vs estimated):
  * DAC code-set -- the chosen write path is a voltage-mode resistor-string DAC
    (Vspan=200 mV, b=7; see eda/hero/write_dac_summary.json) whose tap feeds the
    CMOS write driver. The ANALOG core (string + tap transmission-gate + the
    write-driver gate load) is measured directly with an ngspice transient on the
    sky130 models. The small DIGITAL part (b-bit one-hot decode toggling on a code
    change) is added analytically from sky130 gate capacitance, because the
    sky130_fd_sc_hd Liberty is not installed in this WSL image.
  * Counter increment -- a binary popcount counter toggles ~2 bit-cells per
    increment on average (sum 1/2^k). Without the Liberty we ground one DFF-toggle
    from sky130 gate/junction capacitance (documented constants), x2 toggles.

Both are grounded in the SAME sky130 PDK that grounds the read/write energies, so
they are consistent and reproducible; the residual uncertainty (no extracted
layout parasitics, no Liberty) is stated and tracked in
``.agents/eda/PPA_grounding_plan.md``. Areas remain placeholders (need layout).

Run in WSL (native ngspice + sky130):
    wsl -d Ubuntu-24.04-EDA -- bash -lc 'cd <repo>/eda/testbenches && python3 dac_counter_energy.py'
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
LIB = "/opt/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"

# ---- sky130 PDK constants (documented; 1.8 V core devices) -------------------#
VDD = 1.8
VSPAN = 0.200            # write-DAC reference span (write_dac_summary.json)
NBITS = 7               # resistor-string bits (LSB ~1.6 mV < V_T/14)
COX = 8.6               # gate-ox cap density [fF/um^2]  (eps0*3.9 / tox~4nm -> 8.6 fF/um^2)
CJ_WIRE = 0.20          # local metal routing cap [fF/um] (met1, sky130 ~0.1-0.3)
# write-driver input transistor sizing (from eda/hero write-driver study: Wp~8um
# pull-up delivers ~0.9-1.0 V into 776 ohm; matched Wn)
W_DRV = 8.0; L_DRV = 0.15
C_DRV_GATE = COX * (2 * W_DRV) * L_DRV            # p+n driver input gate cap [fF] ~20 fF
# one-hot decode: a code change flips ~2 address-buffer gates + de-/asserts 2 word
# lines, each driving one tap transmission-gate (Wn~1um/Wp~2um) -> gate load
C_TG_GATE = COX * (1.0 + 2.0) * 0.15             # one tap-TG gate cap [fF]
C_DECODE_SW = 2 * (COX * 1.0 * 0.15) + 2 * C_TG_GATE   # switched per code change [fF]
# effective switched cap of one sky130_fd_sc_hd DFF per toggle (data+internal nodes;
# documented estimate ~3 fF -> ~10 fJ at 1.8 V; Liberty not installed for exact value)
C_DFF_EFF = 3.0          # [fF]


def _ngspice_dac_analog():
    """Transient-measure the analog DAC code-set energy from the reference rail:
    string static over the settle window + charging the driver-gate load to the
    selected tap through the tap transmission-gate. Returns energy in joules."""
    cl = round(C_DRV_GATE + 4.0, 2)              # driver gate + tap-node routing [fF]
    rtop, rbot = 51200.0, 153600.0              # b=7 string (~205 kohm), mid code
    deck = f"""* sky130 resistor-string write-DAC -- analog code-set energy
.lib {LIB} tt
Vref vref 0 dc {VSPAN}
Rtop vref tap {rtop}
Rbot tap 0 {rbot}
Vtg vtg 0 dc {VDD}
Vg  g  0 PULSE(0 {VDD} 2n 50p 50p 60n 120n)
Vgb gb 0 PULSE({VDD} 0 2n 50p 50p 60n 120n)
XN tap g out 0 sky130_fd_pr__nfet_01v8 W=1 L=0.15
XP tap gb out vtg sky130_fd_pr__pfet_01v8 W=2 L=0.15
Cl out 0 {cl}f
.ic v(out)=0
.tran 5p 8n uic
.meas tran q_stat integ i(vref) from=0 to=2n
.meas tran q_acc  integ i(vref) from=2n to=4n
.end
"""
    with tempfile.NamedTemporaryFile("w", suffix=".spice", dir="/tmp", delete=False) as f:
        f.write(deck); path = f.name
    out = subprocess.run(["ngspice", "-b", path], capture_output=True, text=True).stdout
    def meas(name):
        m = re.search(rf"{name}\s*=\s*([-\d.eE+]+)", out)
        return float(m.group(1)) if m else None
    q_stat, q_acc = meas("q_stat"), meas("q_acc")
    if q_stat is None or q_acc is None:
        raise RuntimeError("ngspice .meas parse failed:\n" + out[-800:])
    # energy from the reference over the 2 ns access window (|charge|*Vref);
    # this includes both the string static loss and the dynamic tap charging
    e_analog = abs(q_acc) * VSPAN
    return e_analog, dict(cl_fF=cl, q_stat=q_stat, q_acc=q_acc)


def main():
    # ---- DAC ----
    try:
        e_dac_analog, dbg = _ngspice_dac_analog()
        method = "ngspice (sky130 analog core) + analytical decode"
    except Exception as exc:                      # ngspice unavailable -> analytical
        # analog fallback: string static (V^2/R*t) + dynamic 1/2 C V_tap^2 * 2
        e_dac_analog = (VSPAN ** 2 / 2.05e5) * 1e-9 + (C_DRV_GATE + 4.0) * 1e-15 * 0.15 ** 2
        dbg = {"fallback": str(exc)[:200]}
        method = "analytical (ngspice unavailable)"
    e_dac_digital = C_DECODE_SW * 1e-15 * VDD ** 2        # one-hot decode CV^2
    e_dac_step = e_dac_analog + e_dac_digital

    # ---- counter ----
    # DFF effective switched cap per toggle (sky130 stdcell estimate, C_DFF_EFF)
    e_dff_toggle = C_DFF_EFF * 1e-15 * VDD ** 2
    avg_toggles = 2.0                                     # sum_k 1/2^k for a binary up-counter
    e_count_inc = avg_toggles * e_dff_toggle

    res = {
        "method": method,
        "sky130_constants": {"VDD": VDD, "VSPAN": VSPAN, "NBITS": NBITS,
                             "Cox_fF_per_um2": COX, "C_drv_gate_fF": round(C_DRV_GATE, 2),
                             "C_decode_switched_fF": round(C_DECODE_SW, 3)},
        "e_dac_step": e_dac_step,
        "e_dac_analog": e_dac_analog,
        "e_dac_digital": e_dac_digital,
        "e_count_inc": e_count_inc,
        "e_dff_toggle": e_dff_toggle,
        "ngspice_debug": dbg,
    }
    out = HERE / "dac_counter_energy_summary.json"
    out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"DAC  e_dac_step  = {e_dac_step*1e15:6.2f} fJ "
          f"(analog {e_dac_analog*1e15:.2f} + decode {e_dac_digital*1e15:.2f})  [{method}]")
    print(f"CNT  e_count_inc = {e_count_inc*1e15:6.2f} fJ "
          f"(2 x DFF toggle {e_dff_toggle*1e15:.2f} fJ)")
    print(f"-> {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
