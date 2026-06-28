# Figure conventions in sMTJ / p-bit / MRAM-CIM hardware papers (2026-06-28)

Web survey (8 representative arxiv/journal papers, 2023–2026) of how the field draws ARCHITECTURE and
CIRCUIT/ARRAY figures, to guide the thesis architecture figure (task ②) and the fig-4.1 augmentation
(task ④). Internal record; deliverable figures live in article/.

## Per-paper notes
- **arXiv:2511.03203** (SOT-MRAM spiking CIM macro, 28 nm): architecture = block/dataflow, 128×128
  crossbar grid centre + peripheral functions as labelled boxes, grayscale. Cells transistor-level
  (MTJ = resistor+arrow; 3T-2MTJ J1/J2; RBL/WL labels). (a)(b)(c) sub-panels.
- **arXiv:2412.08017** (integrated p-computer, VC-MTJ entropy): hybrid schematic-conceptual core; sMTJ
  as layered stack with free/fixed magnetisation arrows wired to NMOS drain; node labels V_D/V_S/V_IN;
  device-integration panel = 3D isometric + cross-section (nm layers) + micrograph. Grayscale + accent
  data traces.
- **Nat. Commun. 2024 (PMC11096331)** (sMTJ + MoS2 p-bit core): layered-stack / 3D-isometric device
  schematics + micrographs; grayscale + accent data colours; left→right hierarchical panels.
- **arXiv:2302.06457** (full-stack p-bit review): hierarchical full-stack layered tiers (digital /
  mixed-signal / hybrid) with bidirectional dataflow arrows; p-bit symbolic (layered pillar + arrows),
  blocks PRNG/tanh-LUT/threshold; single accent colour.
- **arXiv:2606.25313** (1M p-bit programmable computer, 2026): hierarchical exploded view logical graph
  → partition → FPGA hardware; p-bits as node-link graph; labelled interconnect (FMC/UCIe); single
  accent (red hardware vs blue baseline).
- **arXiv:2312.17453** (RHS-TRNG, STT-MTJ): system = block diagram with labelled buses; cells
  transistor-level 1T1MTJ (NMOS selector + MTJ resistor+arrow, BL/SL/WL); waveforms with dual y-axes +
  vertical dashed phase markers (Pre-charge, Voltage-development).
- **arXiv:2404.14307** (1 trillion bits, FPGA-actuated MTJ): functional block schematic; MTJ simplified
  layered stack (RL/MgO/FL) with P/AP; DAC + transimpedance amp as distinct blocks; monochrome.
- **arXiv:2304.05949** (Camsari, CMOS + stochastic nanomagnets): "stacked" hybrid hierarchy — device
  stack (layer bars + magnetisation arrows + P/AP + R values) → transistor p-bit (two branches → op-amp
  triangle ±) → FPGA die photo; signal-flow arrows; grayscale + one accent (yellow); dense (a)–(h).

## Conventions to imitate
### Architecture figure (task ②)
1. Hybrid **block-dataflow**, not a literal floorplan: array as an explicit grid anchor, peripherals as
   labelled boxes, joined by labelled directional dataflow lines (L→R or T→B).
2. A **"stack"/exploded hierarchy** is the cleanest way to show heterogeneous integration: device stack
   → bit-cell/p-bit circuit → CMOS/host, connected by signal-flow arrows.
3. Array drawn as a grid (representative tile + "…"); everything else named boxes; detail goes in the
   separate circuit figure.
4. **Grayscale base + ONE accent colour** (emphasis or hardware-vs-baseline). No multi-colour palettes.
5. Buses/couplings as **labelled directional arrows**; name them (BL/SL/WL/RBL, ctrl/clk); bidirectional
   for handshakes (weights-out / samples-back).
6. Optionally pair schematic + micrograph/die-photo for an experimental claim.

### Circuit / array figures (refinements)
7. MTJ symbol by altitude, consistently: in **schematics** resistor+diagonal-arrow; in **device/physics**
   layered pillar (FL/MgO/RL) + magnetisation arrows + P/AP. Don't mix within one schematic.
8. Bit-cell transistor-level with standard SPICE symbols (1T1MTJ, 3T-2MTJ, p-bit→inverter/op-amp).
9. Real array-signal names on lines; tile a small repeated grid with shared peripherals + "…" for scale.
10. In-schematic subscripted node labels; external trace legends; waveforms with dashed phase markers.

### Cross-cutting
- (a)(b)(c) parenthetical panel labels; order schematic → fabrication → characterization.
- Sans-serif (Arial/Helvetica) for labels; serif for equations/Greek.
- Declarative element-first captions below the figure.

## Sources
arXiv:2511.03203 · 2412.08017 · Nat.Commun.2024 PMC11096331 · 2302.06457 · 2606.25313 ·
2312.17453 · 2404.14307 · 2304.05949
