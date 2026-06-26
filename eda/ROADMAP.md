# EDA 协同设计路线图 (可落实为 agentic 工作流)

本路线图按**阶段 (phase)** 组织，每个阶段对应一个可由 agentic 工作流执行的单元：
有明确输入、可并行的子步骤、产出物、以及**验证门 (gate)**。会话 todo (TaskCreate) 与本文件同步——
本文件是持久副本 (todo 可能不跨会话保留)。

> **续传入口**：当前状态、各阶段 DoD、决策账本、验证账本见 [`STATUS.md`](STATUS.md)（长时程任务的**单一续传点**）。本文件是阶段细节；STATUS 是"我们到哪了 / 如何续传"。

依赖关系 (拓扑序)：`P0 → P1 → {P2 ∥ P3 ∥ P7a} → {P4 (需P3) ∥ P5 (需P1+版图)} → P6 (汇总) ；P7 全程并行`

图例：⚙️=配置/决策 🔬=仿真 🧪=回归/验证门 🔌=接口回灌 📝=回填论文/勘误

---

## ⭐ 创新优先重排（2026-06-27 顶刊重审后；详见 [`research/2026-06-27_innovation_replan.md`](research/2026-06-27_innovation_replan.md)）

**判断**：下面的 P1–P7 是**验证层**（复现/确认/打通），不是顶刊贡献；且多数"新电路"2024–26 已被做掉（V_th 驱动、自调零 SA、可调势垒三位一体均有 2024–26 先验）。真正的新颖性 = **① 规格反转 + ② 闭环 + ③ 反向设计方法学**，非新原语。**P1–P7 first-cut 自此降为「基础/支撑层」**，主线改为：

- **Hero（C1+C2，~60%，唯一 strong）**：斜率匹配 p-bit 读出 —— SA 输入失调按器件 **V_T=23.4mV（伯努利判决窗口）** 预算（非 TMR 余量；非显然：finding(c) 说 V_T 被 BN 吸收"无关精度"，但它决定读出成本）；闭环 σ_offset→`device/variation.py`→MNIST **92.8%→~97%**；摊销写-DAC 微调（写占 98.7%，校准近免费）。**关 errata R2**。
- **第二篇（C3）**：RC 等能量三方套利 **{N,M,b}** 的 MC/焦耳 + **列共享低分辨 ADC**，修复 `rc_readout_noise`(读出限制) vs `reservoir_energy`(读出免费) 矛盾；证明 MC-最优读出是廉价低分辨/时域。**修 R6**。
- **降级（引为先验，不独立成文）**：V_th 跟踪驱动、自调零 SA-as-invention、三位一体可调势垒（Kent A-sMTJ 2025 / HKUST VLSI 2026 已抢先）、自适应-T、开源 `.va`。
- **目标期刊**：IEEE **TCAS-I / TVLSI / TED**（**不投 Nat.Electron./ISSCC**——2025 已有实测 130nm CMOS p-bit ASIC，sky130 纯仿会秒拒；46 点晶圆校准是"近硅"锚点）。

**👉 可分步执行清单（带 DoD + 本会话状态）见 [`PLAN_execution.md`](PLAN_execution.md)** —— 把下面的阶段拆成有序步骤 1.1…3.5 与"立即可开工的 5 个动作"。

**新阶段序（替换验证优先）**：
- **Phase 0 网关**：WSL2 + IIC-OSIC-TOOLS Docker（Xschem/Magic/Netgen/ngspice + sky130A）+ 共享 OpenVAF `.osdi`。← 即用户正在装的 PDK，解锁所有版图/GDS/PEX。
- **Phase 1 Hero**：C1+C2 设计→优化→版图→PEX→闭环 MNIST（全工件集 + hero 图）。
- **Phase 2**：C3 读出协同（MC/焦耳等高线 + 一个 sky130 TIA+低分辨 ADC 切片）。
- **Phase 3**：旧 P2/P3/V_th 驱动/自适应-T/.va → 支撑证据/复现性支柱。
- **纪律**：阵列只到单列/原理图标注级，**绝不做 256×256 全 DRC-clean GDS**。
- **诚实支柱（必写）**：RNG 在 Python harness；结论用比值不报绝对(130nm 悲观)；Magic 电阻 PEX 仅量级级；能量基准用端到端 6.95 pJ/bit；`.va` RC 低势垒区未独立验证。

> 下面的 P0–P7 保留作**基础层记录**：已完成的 first-cut 是这条创新主线的脚手架与证据（P1 模型、P3 差分残余、P6 接口、P7 读出噪声都直接喂入上面的 Hero/第二篇）。

---

## 两层贡献层级（大论文 vs 小论文/顶刊）

> 学位论文(**大论文**)要的是**完整、正确归因的系统**；顶刊(**小论文**)要的是**新颖性**。"已被做掉"的电路对大论文是**合格的工程基础**（引先验 + 实现 + 表征），对顶刊不独立成文。两层**并行写进计划**：Tier A 是创新亮点，Tier B 是大论文完整性（同时也是 Tier A 的脚手架/证据）。

### Tier A — 创新层（小论文/顶刊亮点；大论文的"创新点"）
| ID | 内容 | 驱动结论 | 新颖性 | 工件 |
|---|---|---|---|---|
| **A0** | 反向设计方法学（finding→PEX 数→论断位移→闭回 PyTorch 栈） | 全局 | binding | 全链路 + 闭环图 |
| **A1** | Hero(C1): 斜率匹配 p-bit 读出（SA 失调↔V_T=23.4mV，非 TMR 余量） | (a)(c)/R2 | **strong** | SA 原理图/版图/GDS/PEX + 闭环精度恢复图 |
| **A2** | Hero(C2): 摊销写-DAC 的 V_th 微调（写占 98.7%，校准近免费） | (c)/R4 | moderate(捆绑 A1) | DAC+driver 原理图/PEX |
| **A3** | 第二篇(C3): RC 等能量 {N,M,b} 套利 + 列共享 ADC | (e)/R6 | moderate | MC/焦耳等高线 + sky130 ADC 切片 |

### Tier B — 基础/工程层（大论文完整性；单独不投顶刊，**引先验为实现基础**）
| ID | 内容 | 驱动结论 | 先验（须引） | 状态 |
|---|---|---|---|---|
| **B1** | 校准 Verilog-A SOT-sMTJ 紧凑模型 + 双仿真器回归 | P1 | ARM s-LLGS / Rajpoot NGSPICE | ✅ R²=1.0 |
| **B2** | 写通路：5b DAC + SOT 驱动 + 0.75ns 脉冲 + 随机写 | (b)(d)/R4 | arXiv:2403.19374 SOT-PBNN-CIM | ◑ first-cut |
| **B3** | V_th 补偿写驱动（副本参考/温漂） | (c) | 闭环 sMTJ Nano Lett.2024 / arXiv:2407.08665 | ⬜（并入 A2） |
| **B4** | 差分读 + 自调零/斩波 SA（原语） | (a)/R2 | ISSCC2018 失调消除 SA；US9111623 | ◑ P3 first-cut（SA 并入 A1） |
| **B5** | 读出 CSA/ADC + 外围能量提取 | /R1 | NeuroSim ADC；arXiv:2404.06553 | ⬜（旧 P4） |
| **B6** | 单列/小 tile 版图 + 开源 PEX（IR-drop） | (c2)/R3 | Magic ext2spice PEX | ⬜（旧 P5） |
| **B7** | 三位一体可调势垒 mode-MUX（**仅受限架构可行性包络**） | (R7) | Kent A-sMTJ arXiv:2509.13458；HKUST VLSI 2026 | ⬜（仅可行性） |
| **B8** | 自适应-T 置信度早退采样控制器 | T 甜点 (Exp.06) | 随机计算 SPRT / DNN 早退 | ⬜ |
| **B9** | 接口回灌 + 全栈 PPA 重算 + **闭环精度恢复基础设施** | /R1/R2 | — | ◑ first-cut（含 `variation.py` 的 R2 通道 + `hero_closed_loop.py`） |

横向支柱：勘误维护(R1–R7)、诚实支柱(种子/版本钉死、比值非绝对、Magic 电阻量级级、MTJ 不可制造声明、6.95pJ/bit 基准)、复现性。

### 大论文章节映射（建议）
新增一章「**器件-电路协同设计与 EDA 验证**」（置于 PBNN/RC 仿真章后、结论章前）：
- 5.1 反向设计方法学 + 开源 EDA 流程（A0, B1）
- 5.2 **[创新]** 斜率匹配 p-bit 读出协同设计（A1+A2）← 主创新，hero 图
- 5.3 **[创新]** RC 读出等能量协同优化（A3）
- 5.4 **[基础]** 全栈电路实现与表征（B2 写驱动 / B4 差分读 / B5 ADC / B6 版图）
- 5.5 **[基础/受限]** 可调势垒三位一体可行性包络（B7）+ 自适应-T（B8）
- 5.6 接口回灌与系统级 PPA 修正（B9）；5.7 限制与诚实支柱

---

## P0 — 基础与决策 (无 EDA，1 周)  ⚙️
**目标**：把后续一切的前提钉死。
- [ ] 确认大学 Cadence/Synopsys 席位 + Europractice/foundry-PDK 访问；论文算教学/研究用途。
- [x] **据访问结果二选一**：采用开源路线 (ngspice≥43 + OpenVAF-Reloaded + sky130/IHP SG13G2)；商用路线留待许可证可用。
- [ ] 钉死工具链版本 (写入本目录决策备忘)。
- [ ] **定 Verilog-A 回归目标工作点** = 自动拟合值 $V_\mathrm{th}=895.8$ mV、$V_T=23.4$ mV、$\beta_s=42.7$ V⁻¹ (勘误 N1)。
- [ ] 确定 MTJ 模型基底：fork ARM s-LLGS (加 SOT 分支) 或 Rajpoot NGSPICE (索取代码)。

**产出**：`eda/` 决策备忘 (工具链 + PDK + 回归目标 + 模型基底)。**门**：访问与版本确认。

---

## P1 — Verilog-A SOT-sMTJ 器件模型 (keystone)  🔬🧪  — ✅ **完成**
**目标**：一个种子可复现、能重现 Ch.2.3 标定的 Verilog-A 器件——解锁后续一切。
> 实现修正：OpenVAF 不支持可靠的 in-`.va` 随机/`@cross`，故 `.va` 保持**代数** + 把 Sigmoid/τ/⟨s⟩ 作**观测**，随机性放 harness（决策 D4）。
- [x] **(模型)** `models/smtj_sot.va`：三端宏，SOT 写支路 ($R_\mathrm{SOT}=776$)、双态读支路 ($R_P=4.9$k/$R_\mathrm{AP}=9.8$k，状态由控制节点 `st`)、Sigmoid/τ(V)/⟨s⟩ 观测节点。
- [x] **(Python 金标准)** `testbenches/gen_golden.py`：对实测 46 点 R²=0.9919、写能量 0.783 pJ、τ(0V)=67.8 ns（PASS）。
- [x] **(随机写 harness)** `testbenches/psw_mc_harness.py`：seeded Bernoulli 复现 Sigmoid（max\|err\|=0.019 < 4σ）+ 写能量积分（开源路对 in-`.va` 随机的替代）。
- [x] **(ngspice 回归)** `run_regression.py`：DC 扫描 `V(psw)` vs 金标准 **R²=1.000000**（ngspice-46 + OpenVAF-reloaded；OSDI 经 cwd `.spiceinit` 的 `osdi` 命令在解析前加载，器件用 `.model smtj_sot smtj_sot` 卡）。
- [~] **(telegraph τ(V) 电路级随机轨迹)** 留 P7 / Spectre 全-VA 路。

**产出**：`models/smtj_sot.va`、`testbenches/{gen_golden,psw_mc_harness,run_regression}.py`、`golden_*`。
**门 🧪**：四项全 PASS ✅ — **P1 完成**。DoD 见 [`STATUS.md`](STATUS.md)。

---

## P2 — 写路径 (单次最高价值仿真；P1 后)  🔬📝  — first-cut ✅
**目标**：验证 (b)(d) 并测可行性。
> **first-cut 已完成**（`testbenches/write_path.spice` + `write_mc_harness.py`，Python-in-the-loop）：理想脉冲+串阻驱动下 0.75ns rise≈40ps 可行、信道能量≈0.80pJ、10Ω 驱动开销 1.3%、P_sw 在交付电压上复现（errata R4 首个电路级数）。**待**：sky130 CMOS 写驱动替换理想脉冲，量化真实开销/短路能量 + 5-bit DAC。
- [ ] 5 比特 DAC + SOT 电流驱动 + 0.75ns 脉冲发生器 + 随机写测试台。
- [ ] 瞬态：0.75ns 脉冲在 776Ω 上是否真能建立 (slew + 线 RC)。
- [ ] 含驱动/DAC 开销的**真实写能量** (预期 > 0.78 pJ) → 勘误 R4。
- [ ] 多种子 → 复现 P_sw(V_wr) Sigmoid。

**产出**：写能量 (器件级 + 端到端) 数；可行性结论。**门 📝**：更新勘误 R1/R4。

---

## P3 — 差分读 + 灵敏放大 (P1 后，可与 P2 并行)  🔬📝  — first-cut ✅
**目标**：把 (a) 从代数断言变成实测；测 (c)。
> **first-cut 已完成**（`testbenches/diff_column.py`，MTJ 电阻级，无需 sky130）：匹配时差分消除精确（线性 err 9e-6 popcount）；MTJ 失配（σ_Rp7%/σ_TMR4%）残余失调 ~0.06·√N popcount（N=16/64/256→0.30/0.62/0.97，sub-LSB 至 N≈256）——claim(a) 在 MTJ 层稳健。**待**：sky130 晶体管电流型灵敏放大 + 其输入失调（~10–30mV vs V_T，errata R2）。
- [ ] 2T2MTJ 差分列 + 电流型灵敏放大；±V_read/2 驱动。
- [ ] Spectre MC 失配 (注入 CV(Δ)=7.7% + SA 失配) → 残余共模/CMRR vs 列高 N、TMR。
- [ ] 量化 SA 输入折合失调 (~10–30mV) 是否与 $V_T=23.4$mV 竞争。

**产出**：残余失调/CMRR vs N 曲线；SA 失调分布。**门 📝**：更新勘误 R2 (可能撼动论断 c)。

---

## P4 — 读出与 ADC (2–3 周；P3 后)  🔬📝
**目标**：最大「诚实度升级」，改写 (b)。
- [ ] CSA (1bit 比较器 + popcount 加法) vs 电荷积分 + 低分辨 ADC，两种都仿。
- [ ] 灵敏裕度 → 真实子阵列尺寸上限；替换 `e_smtj_read`/`t_smtj_read` 占位。
- [ ] 每 T 样本 ADC 能量 → 重算外围占比 (预期 <1% → 20–40%)。

**产出**：读出能量/延迟/噪底、子阵列上限。**门 📝**：更新勘误 R1。

---

## P5 — IR-drop PEX (冲刺, 1–2 周；P1 + 版图后)  🔬📝
**目标**：把 (c2) 从空桩变成提取数。
- [ ] 版图单列/小 tile；Quantus QRC (或开源 PEX) 提取 BL/WL 线 RC。
- [ ] DC 线扫描 → 远端 V_read/**V_wr (低阻 776Ω 写线)** 压降、popcount 误差 vs 阵列尺寸 128/256/512/1024。

**产出**：真实压降 vs 尺寸。**门 📝**：坐实/推翻「可忽略」，更新勘误 R3。

---

## P6 — 接口：回灌 `smtj_pbnn_sim` (汇总 P2/P4(/P5))  🔌📝  — first-cut ✅
**目标**：把提取数值变成仿真器可读配置——「替换不成熟内容」落地。
> **first-cut 已完成**（`interface/load_tech_params.py` + `extraction/peripheral_energy.yaml`）：单向读 extraction → 重算 per-MAC + MNIST PPA。当前仅写能量为 P2 提取（per-MAC 793→818 fJ +3%，MNIST T=4 5.91→6.09µJ）；read/DAC/counter 仍占位。**待 P4** 把 sky130 ADC/sense 数填入同一 YAML，本脚本即报外围占比 <1%→20–40% 的位移（R1，无需改码）。
- [ ] `extraction/` 把列在 (θ,T,corner) 上特征化成 LUT/能量-面积表。
- [ ] `interface/` Python 胶水：由提取值构造 `TechParams`/重写 `per_mac_energy`/替换 `estimate_ir_drop`；单向注入，仿真器不依赖 `eda/`。
- [ ] 用提取数重跑 MNIST PPA；(可选) wreal AMS 把一小撮 MAC 从 PyTorch 流过提取网表 → 「一个 MNIST 数字穿过提取的 sMTJ 列」杀手图。

**产出**：由 EDA 数驱动的 PPA；接口模块。**门 📝**：勘误 R1/R2 标记为已解决并回填论文。

---

## P7 — 储池 (RC) 路径 (并行轨)  🔬📝  — P7a first-cut ✅
**目标**：验证/修正 (e)，文档化三位一体限制。
> **P7a first-cut 已完成**（`testbenches/telegraph_lowbarrier.py`）：低势垒 Δ=3.8（`.model` 卡覆盖）下 `.va` 的 τ(V)/⟨s⟩ 观测对照解析，τ_max(0V)=22.35ns、τ rel-err<1.6e-4、⟨s⟩ abs-err<1.2e-4——RC 两旋钮（衰落记忆+非线性）器件级成立。
> **读出噪声 first-cut 已完成**（`testbenches/rc_readout_noise.py`，R6）：mean-field MC0=6.38，per-node ADC≤10bit 或读噪声≥2% 显著掉 MC（10bit→62%、2%噪→47%）→ **读出精度是限制者**，与 `reservoir_energy.py` 把读出当~免费矛盾。**待**：读出能量映射（NeuroSim ADC/TIA）、无扰动读+读回作用界、三位一体势垒冲突（R7）。
- [ ] **(P7a, 可与 P1 并行)** 低势垒 (Δ≈3.8) telegraph 节点瞬态噪声验证 τ(V)/tanh。
- [ ] 无扰动 4 端读 + 读回作用界 (读偏置移动 τ 多少)。
- [ ] 模拟读出 TIA+ADC 噪声 → 脊回归记忆容量损失 (论断 e)；解决 `reservoir_energy.py` 读出近乎免费 vs 正文矛盾。
- [ ] 模式 MUX 漏电对自由节点扰动；登记势垒冲突 (Δ=4.91 vs 3.8) 为限制。

**产出**：τ(V) 验证、读出噪声 Pareto、三位一体限制陈述。**门 📝**：更新勘误 R6/R7。

---

## 跨阶段 — 勘误维护与回填  📝
每阶段拿到可信数后，更新 [`../docs/errata.md`](../docs/errata.md) 状态，并 (有结果后) 回填论文数值 + 重生成 `.docx`。

---

## Agentic 工作流映射

把上面落实为 `Workflow` 时的骨架 (每阶段一个 workflow，串行推进、阶段内 fan-out + 验证门)：

```
// 每个 phase 一个 workflow 调用；P0 决策由人确认后再启动 P1。
phase('P1: device model')
  parallel([
    () => agent('编写 Verilog-A 三端 SOT-sMTJ，事件驱动 seeded 切换 ...', {schema: MODEL})         // 模型
  ])
  // 验证门：对抗式回归智能体——是否真复现 46 点 sigmoid / τ(V) / 0.78pJ？种子是否可复现？
  const gate = await agent('对照 calibration.py/telegraph.py 复算并判定 PASS/FAIL ...', {schema: GATE})
  if (!gate.pass) { /* 回修 */ }

phase('P2∥P3 (P1 通过后 fan-out)')
  await parallel([
    () => agent('写路径：DAC+SOT驱动+0.75ns 脉冲，测可行性与端到端写能量 ...', {schema: FINDING}),
    () => agent('差分列+SA：MC 失配，残余失调/CMRR vs N，SA 失调 vs V_T ...', {schema: FINDING}),
  ])
  // 每个发现都接一个对抗式验证智能体 (refute) + 把数值映射回某条勘误项

phase('P4 (P3 后) / P5 (P1+版图后)')   // 同上 fan-out + gate
phase('P6: 汇总回灌')  // 合并提取 LUT → 构造 TechParams → 重跑 MNIST PPA → 更新勘误状态
phase('P7: RC 并行轨')  // τ(V)/读出噪声/三位一体限制
```

**模式要点**：
- 每个仿真阶段 = fan-out 多个独立子任务 (`parallel`/`pipeline`)，每个子任务后接**对抗式验证门** (它真复现了目标吗？数值是否撼动论断？种子可复现吗？)。
- **验证门是硬门**：回归不过则回修，不进入下一阶段。
- P6 是**汇总/综合**阶段：把各提取结果合并，单向写入仿真器配置，重跑端到端。
- 勘误维护是**横向支柱**：每条数值落地即更新 `docs/errata.md` 状态。
