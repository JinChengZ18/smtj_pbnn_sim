# 创新优先 · 可分步执行方案 (execution plan)

> 把 [`research/2026-06-27_innovation_replan.md`](research/2026-06-27_innovation_replan.md) 与
> [`ROADMAP.md`](ROADMAP.md) 的创新主线（A0 方法学 / A1+A2 Hero / A3 第二篇）**落实成带 DoD 的有序步骤**。
> 续传真相源仍是 [`STATUS.md`](STATUS.md)；本文件是"下一步具体做什么"的执行清单。
> 图例：✅ 完成 · ◑ first-cut · ⬜ 未开始 · 🖱️ 需 GUI/人工收尾

## 0. 本会话后的状态快照 (2026-06-26)
- **工具链已原生齐备**（无需 Docker）：`Ubuntu-24.04-EDA` 内 ngspice-46 + OpenVAF-Reloaded +
  sky130A + KLayout + **Magic 8.3.668** + **netgen 1.5.321 (LVS, `~/eda/netgen/bin`)**。
- **真实提取数已落地**：写线 IR-drop（R3，`extraction/writeline/`）、SA 版后寄生/能量（R1/R5，
  `hero/sa_postlayout.py`）、SA 器件集 9→11 + DRC 0 违例 + LVS 工具链打通。
- **闭环基础设施在位**：`hero/readout_mapping.py`（mV→popcount→精度）、`hero/hero_mnist_sweep.py`、
  `interface/load_tech_params.py`、`device/variation.py` 的 `sigma_sense_offset` 通道。

---

## Phase 0 — 工具链网关 ✅ (本会话达成；Docker 改为可选)
| | 步骤 | 工具 | DoD | 状态 |
|---|---|---|---|---|
|0.1| ngspice+OpenVAF→OSDI→DC 回归 | ngspice-46 | `run_regression.py` R²=1.0 | ✅ |
|0.2| Magic ≥8.3.306 + sky130A techfile 加载 | Magic 8.3.668 | techfile 无版本错 | ✅ |
|0.3| KLautout sky130 PCell DRC | KLayout | `run_drc.sh` 0 违例 | ✅ |
|0.4| Magic 提取链 (extract→ext2spice / extresist) | Magic | `run_pex.sh`/`run_extresist.sh` 通 | ✅ |
|0.5| LVS netgen (Tim Edwards) | netgen 1.5.321 | `-batch lvs` 跑通 sky130A_setup | ✅ |
> 结论：Phase 0 **满足**。IIC-OSIC-TOOLS Docker 仅作可移植性备份，非阻塞。

---

## Phase 1 — Hero (A1 斜率匹配 p-bit 读出 + A2 摊销写-DAC) — 主线 ~60%
**目标**：min 读出能量+面积 @ iso-精度(≥97% MNIST)；产出 accuracy-vs-(V_offset/V_T) Pareto + 闭环图。**关 R2**。

| | 步骤 | 工具 | DoD | 状态 |
|---|---|---|---|---|
|1.1| StrongARM SA sky130 原理图级仿真 | ngspice+sky130 | vind→outp 翻转正确 | ✅ `hero/strongarm_sa.spice` |
|1.2| SA 输入折合失调 MC | ngspice MC | σ_offset/V_T 数（=0.47） | ✅ `run_offset_mc.py` |
|1.3| 闭环 σ_offset→MNIST | PyTorch | per-column σ→精度曲线 | ✅ `hero_mnist_sweep.py`(97.0→96.35%) |
|1.4| 读出跨阻映射 mV→popcount→精度 | Python | 协同律 + 设计边界 | ✅ `readout_mapping.py` |
|1.5| SA 器件版图 GDS + DRC | KLayout | 11 器件 DRC 0 违例 | ✅ `layout/`(23.1×18.7µm) |
|1.6| SA 版后寄生 C + 能量/失调估算 | Magic PEX | 器件 C 提取 + 能量量级 | ◑ `sa_postlayout.py`(35.25fF;23–74fJ) |
|1.7| **SA 器件间布线 (tail/交叉耦合/输入栅/precharge)** | KLayout/Magic GUI | 连通且 DRC 0 | 🖱️ `layout/LVS_GUI_CHECKLIST.md` |
|1.8| **Netgen LVS = layout vs `strongarm_sa_core.spice`** | netgen | "Circuits match uniquely" | 🖱️ 待 1.7 |
|1.9| **路由后 PEX (extresist R+C) → tt/ss/ff 后仿** | Magic+ngspice | 版后失调/延迟/能量含寄生 | ⬜ 待 1.8 |
|1.10| **回填**：真实 `e_smtj_read`(~50fJ 量级)→P6 接口→重跑 MNIST PPA | Python | 外围占比位移数 | ⬜ 待 1.9（关 R1）|
|1.11| Pareto：accuracy vs (V_offset/V_T)，{无/4×面积/单容自调零/两相斩波} | Python | Pareto + 设计边界 | ✅ `pareto_offset_cancellation.py`（V_in≥0.5 plain 最优；≤0.4 才需自调零）|
|1.12| **C2 摊销写-DAC**：3–4 trim-bit V_th 微调，代价<1% 写预算 | Python | trim→精度恢复曲线 | ✅ `write_dac_trim.py`（σ_col=8: 96.35%→b3 96.82%≈基线；静态码摊销→<1%写能）|
|1.13| Xschem 原理图+`.sym`+测试台 → SVG/PDF（"导出原理图"工件）| Xschem | hero 原理图图 | ⬜（需装 Xschem）|
|1.14| Hero 闭环图（σ_offset→栈→92.8%→~97% @ iso 读能）| Python/绘图 | 论文 hero 图 | ⬜ 汇总 1.10/1.11 |

**Phase 1 下一步（最小动作）**：1.7 GUI 布线 → 1.8 LVS → 1.9 路由后 PEX → 1.10 回填。1.11/1.13/1.14 可并行（不依赖布线）。

---

## Phase 2 — 第二篇 (A3/C3 RC 等能量套利) — 修 R6
| | 步骤 | 工具 | DoD | 状态 |
|---|---|---|---|---|
|2.1| 低势垒 τ(V)/⟨s⟩ 器件级验证 | .va+ngspice | Δ=3.8 旋钮成立 | ✅ `telegraph_lowbarrier.py` |
|2.2| 读出 ADC/噪声→记忆容量 first-cut | Python | 读出是限制者 | ◑ `rc_readout_noise.py`(MC0=6.38) |
|2.3| **三方 {N,M,b} MC/焦耳等高线** | Python | iso-能量 frontier | ✅ `rc_isoenergy.py`（读出非免费；效率拐点 b~5–6 列共享；b10=230×能量换3.66×MC）|
|2.4| **sky130 ADC 能量地标**（SAR 比较器=提取的 SA 48fJ）→ 回灌 2.3 | Python（吃 sa_postlayout）| 地标 E_adc(b) | ✅ 迭代进 `rc_isoenergy.py`（读出主导88–99%；b线性→惩罚温和；杠杆=摊销比较器）；TIA 前端偏置能量待 |
|2.5| 重算 ~38× vs 数字 ESN（端到端口径，含 2.4 地标 ADC 读出）| Python | 诚实比值 | ⬜ 2.4 已解锁（读出主导已证）；**需 Ch5 RC 规范配置**（n_nodes/ensemble/n_outputs/memory/n_steps）方能对上 38×，勿臆造 |

---

## Phase 3 — 支撑/基础层 (Tier B，引先验，不独立成文)
| | 步骤 | DoD | 状态 |
|---|---|---|---|
|3.1| 写通路 sky130 CMOS 驱动端到端（替理想脉冲）→ R4 端到端写能 | 含短路/开关能量数 | ✅ `run_write_driver.sh`（交付0.9V→端到端1.61pJ=2.05×欧姆；需稳压写轨）|
|3.2| 写线 IR-drop 路由后列级 popcount 误差 vs N → R3 坐实 | 列级误差曲线 | ◑（B6；Track B 已给金属 R vs N）|
|3.3| 差分列失配残余（已 first-cut）整理为 B4 证据 | — | ◑ `diff_column.py` |
|3.4| 自适应-T 早退控制器（B8）量化省写能量 | T-甜点省能数 | ✅ `testbenches/adaptive_t.py`（SPRT 早退：iso-精度下 E[T]≈9.6 vs 固定 T=22 → **~57% 少写**，~50% 跨前沿）|
|3.5| 三位一体可调势垒 mode-MUX **仅受限架构可行性包络**（B7）| 可行性 + 势垒冲突登记 | ✅ `testbenches/trinity_barrier.py`（ΔΔ=1.11=22.6%·E_b → VCMA ~0.56V/+88K；时分互斥+势垒冲突=限制；关 R7）|
|3.6| **双模型策略（指令②）**：行为级为主力迭代 + LLG（vgsot-sim）做验证 | Python | LLG↔行为 sigmoid 一致性（R²/阈值）| ✅ `testbenches/llg_validate.py`（自热ON：阈值 LLG 0.896V vs 行为 0.8958V 差 0.01·V_T；R²=0.92；高压过驱平台为已知 LLG 特征）|

> **设备模型策略（指令② 2026-06-26）**：保留两套器件模型。**主力 = 标定行为级**（`eda/models/smtj_sot.va` + `gen_golden.py`，便宜、用于全工作流迭代）；**验证 = LLG 宏自旋求解器**（`eda/vendor/vgsot-sim`，计算量大，物理一手核对）。`llg_validate.py` 是桥：定期用 LLG 复核行为级 sigmoid/阈值。**可选**：vgsot-sim 亦可转写 Verilog-A 直接进 ngspice 共仿（重；非当前主线，记为后续）。

---

## 横向（持续）
- **勘误回填**：R1(1.10)、R2(1.8/1.9)、R3(3.2)、R4(3.1)、R5(2.5/1.9)、R6(2.5)、R7(3.5) → 拿到数即回填 `article/` 与 `docs/errata.md` 的「回填检查表」。
- **诚实支柱**（每篇必写）：RNG 在 Python harness；报比值非绝对(130nm 悲观)；Magic R-PEX 仅量级；端到端能量基线 6.95 pJ/bit；MTJ-in-GDS=黑盒+不可制造声明；`.va` RC 区未独立验证。
- **纪律**：阵列只到单列/原理图标注级，**绝不做 256×256 全 DRC-clean GDS**。
- **`.docx` 同步**：改 `article/*.md` 后 watcher ~4–5min 重生 `.docx`，与 `.md` 一起提交。

## 立即可开工的 5 个动作（按杠杆排序）
1. **1.7 GUI 布线 SA**（解锁 1.8–1.10 整条 Hero 版后链；清单已备 `LVS_GUI_CHECKLIST.md`）。
2. **1.11 Pareto 扫描**（纯 Python，不等布线；把 1.4 的设计边界扩成 accuracy-vs-V_offset/V_T 曲线）。
3. **2.3 RC {N,M,b} 等高线**（纯 Python，扩 `rc_readout_noise.py`；推进第二篇）。
4. **1.13 装 Xschem + 画 hero 原理图**（"导出原理图"工件；与布线并行）。
5. **3.1 sky130 写驱动端到端**（ngspice+sky130，给 R4 端到端写能，补 Track B 的写侧）。
