# Plan 3.1 — sky130 CMOS write-driver end-to-end energy (errata R4)

`run_write_driver.sh` (WSL ngspice + sky130 `tt`) drives a CMOS inverter (pfet/nfet_01v8, VDD=1.8 V)
into the 776 Ω SOT write load, 0.75 ns pulse, sweeping the pull-up width W_p. The device write branch
== R_SOT = 776 Ω (the `.va` value), so this isolates the **driver** overhead the 0.783 pJ Ohmic-only
number omits: Ron IR-loss (the driver/776 Ω divider) + short-circuit + switching.

## Results
| W_p (µm) | vflat (V) | I_dev,pk (mA) | E_dev (pJ) | E_vdd (pJ) | driver overhead |
|---|---|---|---|---|---|
| 1 | 0.188 | 0.24 | 0.023 | 0.271 | 1088 % |
| 4 | 0.589 | 0.76 | 0.305 | 1.001 | 228 % |
| 6 | 0.824 | 1.06 | 0.616 | 1.423 | 131 % |
| **7** | **0.927** | **1.20** | **0.785** | **1.607** | **105 %** |
| 8 | 1.017 | 1.31 | 0.951 | 1.769 | 86 % |
| 16 | 1.421 | 1.83 | 1.886 | 2.500 | 33 % |
| 32 | 1.644 | 2.12 | 2.548 | 2.922 | 15 % |
| 64 | 1.758 | 2.27 | 2.934 | 3.163 | 8 % |

(At W_p=7 µm the delivered 0.927 V → **E_dev=0.785 pJ matches the 0.783 pJ Ohmic baseline**, validating
the setup.)

## R4 conclusion
- The 0.783 pJ is **device-Ohmic only**. With a real **1.8 V sky130 CMOS driver delivering the
  calibrated ~0.9 V** to the 776 Ω SOT load (W_p≈7 µm), the **supply draws ≈1.61 pJ → ~105 % driver
  overhead → end-to-end ≈ 2.05× the Ohmic number**. The overhead is the Ron/776 Ω divider: to get
  0.9 V from 1.8 V, ~half the voltage (and energy) drops across the driver.
- **The two naive escapes both lose:** shrinking the driver (W_p≤4) under-delivers (vflat<0.6 V →
  write fails / huge %overhead); enlarging it (W_p≥16) overdrives toward 1.8 V → E_dev balloons to
  1.9–2.9 pJ (V² loss) even though overhead-% falls. **The efficient write needs a regulated ~0.9 V
  write rail** (LDO/charge-pump), not the 1.8 V core supply — then the driver Ron drop is small.
- **Report both numbers** in the thesis: device-Ohmic **0.783 pJ** and end-to-end **~1.6 pJ**
  (1.8 V driver, ~0.9 V delivered) / ~2× — and the regulated-rail design lever. Closes errata R4.
- This supersedes the P2 first-cut's optimistic "1.3 % overhead" (which assumed an unrealistic 10 Ω
  ideal driver that also sagged delivery to 0.889 V).

Reproduce: `wsl -d Ubuntu-24.04-EDA -- bash -lc 'cd "<repo>/eda/testbenches" && bash run_write_driver.sh'`
