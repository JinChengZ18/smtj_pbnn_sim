# 勘误与待修正清单 (Errata)

统一记录论文 (`article/`) 与仿真器代码 (`src/`) 中的已知错误、过度声明与待验证论断。
本表由 2026-06-26 的 EDA 工具/电路设计可行性调研产生 (含一次 7-智能体工作流 + 对抗式事实核查)，
完整调研记录见 [`../eda/research/2026-06-26_eda_assessment.md`](../eda/research/2026-06-26_eda_assessment.md)。

许多条目的「修正」依赖尚未开展的可信 EDA 仿真 (见 [`../eda/ROADMAP.md`](../eda/ROADMAP.md))，
因此本表是一份**活文档**：随 `eda/` 下各阶段产出可信数值后，逐条更新状态并回填论文。

## 图例

| 级别 | 含义 |
|---|---|
| **E** | 现在就应修正的事实性错误 / 内部不一致 (已修或可立即修) |
| **R** | 当前模型下不算错，但属未支撑/占位、且经 EDA 验证后很可能**位移**的论断 |
| **N** | 澄清性说明 (非错误)，主要服务于后续 EDA 工作 |

状态：`已修` / `待EDA验证` / `待回填论文` / `说明`

---

## E — 立即修正项

### E1 — PPA 外围常数的来源被高估为「NeuroSim 校准/硅验证值」
- **位置**：`article/chapter04.md` §4.3 (PPA 层描述段、可信度段)；与 `src/smtj_pbnn_sim/ppa/tech_params.py` 对照。
- **问题**：
  1. 文章原文称 PPA 系数库为「NeuroSim 系列…校准的电路级常数」「经 RRAM-CIM macro post-layout 硅验证后的校准值」。但代码 `tech_params.py` 中这些外围常数 (`e_dac_step=5 fJ`、`e_smtj_read=5 fJ`、`e_count_inc=0.5 fJ`、各 `a_*` 面积) 实为「28 nm 数量级默认值」，注释明确写明「SHOULD be replaced with NeuroSim V1.5 floorplan output before reporting absolute numbers」——即它们是**待替换的占位符，而非已提取的 NeuroSim 值**。§4.5 同处又把它们如实称为「28nm 数字默认值」，故文章存在**内部不一致**。
  2. 原括注「(SRAM 和 **MTJ 读写能量**…)」把 MTJ 读/写能量归于 NeuroSim；但 sMTJ 的 SOT 写能量实由 $V_\mathrm{wr}^2 t_\mathrm{w}/R_\mathrm{SOT}$ 物理标定 (文章自述为「唯一物理量地标定的能量数」)，读出则是 28nm 占位值，二者都不来自 NeuroSim。且 NeuroSim V1.5 的器件库为 SRAM/RRAM/FeFET/nvCap，本身不含 MTJ 单元 (已核实，arXiv:2505.02314)。
- **修正 (已修 `.md` 与代码注释)**：§4.3 改为「采用与 NeuroSim 同级的电路级**数量级**常数…sMTJ 的 SOT 写能量由 $V^2t/R$ 物理标定、读出暂以占位值…绝对数值须经 NeuroSim floorplan 或电路级提取替换后方可作为绝对指标引用」；可信度段相应软化。`tech_params.py` 模块 docstring 增加 NOTE 说明 NeuroSim 替换只覆盖 CMOS 外围、不含物理标定的 sMTJ 写。
- **状态**：`已修` (`chapter04.md`、`tech_params.py`)。⚠️ `article/chapter04.docx` 需由更新后的 `.md` 重新生成。

### E2 — `tech_params.py` 中 NeuroSim 替换范围易被误读为覆盖写能量
- **位置**：`src/smtj_pbnn_sim/ppa/tech_params.py` 模块 docstring。
- **问题**：原注释虽诚实 (称外围为 order-of-magnitude)，但未点明 NeuroSim 替换**不含** sMTJ 写能量；结合 E1 的文章表述易产生「NeuroSim 给出写能量」的误解。
- **修正**：已在 docstring 增补 NOTE，明确 NeuroSim/Spectre 替换仅适用于 CMOS 外围常数，sMTJ 写能量物理标定。
- **状态**：`已修`。

---

## R — 经 EDA 验证后很可能位移的论断 (现暂不改论文数值，待提取结果回填)

> 这些不是「错」，而是建立在占位外围参数或纯解析假设上的结论。EDA 工作的核心价值正是验证/修正它们；
> 在拿到可信数值前**不应**擅自改写论文中的具体数字，只在本表登记并标注预期方向。

### R1 — 「793 fJ/MAC、写占 98.7%、外围优化无意义」(论断 b)
- **位置**：`article/chapter04.md` §4.5；`ppa/energy.py` `per_mac_energy`。
- **问题**：读出仅以 `e_smtj_read=5 fJ` 单项建模，**完全没有**电流灵敏放大、列求和/积分 ADC、参考生成、写驱动、计数器真实翻转能量等条目。已发表 28nm CIM macro 中 SA+模拟+ADC 约占 macro 功耗 36%；模拟 CIM 里 ADC 常是单项最大能耗。提取后外围占比预计从 <1% 升至 **20–40%**，「外围优化无意义」很可能不再成立，设计结论从「优化器件」转向「协同优化 ADC」。
- **行动**：EDA 阶段 4 (读出+ADC) 与阶段 2 (写驱动开销) 完成后，重算 `per_mac_energy`、更新 §4.5 与图 4.14 附近结论。
- **状态**：`进行中`。P6 接口已通（`interface/load_tech_params.py` 读 `extraction/peripheral_energy.yaml` → 重跑 MNIST PPA）；写+驱动开销使 per-MAC 793→818 fJ (+3%，写占比仍 98.7%，因 read/DAC/counter 仍占位)。**首个 sky130 读出能量地标**（`eda/hero/sa_postlayout.py`）：StrongARM SA 动态能 ~**23–74 fJ/决策**（器件 C 提取 35.25 fF + 布线 C 估算），是 `e_smtj_read=5 fJ` 占位的 **5–15×** → 印证读出外围被严重低估、占比将上移。**核心位移（外围 <1%→20–40%）待 P4/sky130 的 ADC/sense 数填入同一 YAML** — 届时脚本无需改码即重算（SA 这块可先以 ~50 fJ 量级回填 `e_smtj_read`）。

### R2 — 「$V_\mathrm{th}$ 绝对位置稳定性是唯一精度瓶颈」(论断 c)
- **位置**：`article/chapter04.md` §4.5 非理想性消融。
- **问题**：精度模型全在写域 ($\sigma_\mathrm{rel}(V_\mathrm{th})=20\%\to92.8\%$)，未含读出灵敏放大的输入折合失调。28nm StrongARM/CLSA SA 失调约 **10–30 mV (1σ)，与 $V_T=23.4$ mV 同量级**，与 $V_\mathrm{th}$ 漂移争夺决策阈值。若 MC 证实其竞争，硬件优先级须从「DAC 校准」扩为「DAC 校准 **+ 灵敏放大失调消除 (auto-zero/chopping/trim)**」。
- **行动**：EDA 阶段 3 的 MC 失配 → 给 `device/variation.py` 增 `sigma_sense_offset` 通道，回灌 MNIST 精度扫描；据结果更新 §4.5 结论。
- **状态**：`进行中(first-cut)`。P3 `diff_column.py` 证实 MTJ 级差分消除（匹配线性 err 9e-6 popcount），器件失配（σ_Rp7%/σ_TMR4%）残余仅 ~0.06·√N popcount（N=256 仍 sub-LSB）——claim(a) 在 MTJ 层稳健。**SA 失调已在 sky130 真测**（`eda/hero/run_offset_mc.py`，WSL ngspice+sky130，N=24 MC）：plain StrongARM σ_offset=**11.05mV=0.47·V_T**、3σ=1.42·V_T —— SA 输入折合失调确与器件 Sigmoid 斜率 V_T 同级，再注入 Exp.08 认定致命的每列 V_th 偏移类误差。**这把 claim(a)/(c) 改写为「MTJ 层偏置消除，但 SA 失调重新引入它」——hero 发现**。精度侧（`hero_mnist_sweep.py`）：per-cell 随机失调被平均化（欠估），但 SA 失调是**每输出列系统性**（一列一个 SA），per-column 模型 σ=0→8 popcount → 97.0%→96.35%。**闭环已合拢**（`eda/hero/readout_mapping.py`，B5 读出映射）：读出跨阻 R_TI 把 mV 桥到 popcount，`LSB_V=LSB_I·R_TI`、`σ_pc=σ_offset_V/LSB_V`，协同律 `σ_pc=σ_offset_V·2·PC_FS/V_in`（取动态范围允许的最大增益）。**精炼结论**：在最大增益读出下，plain SA 的 0.47·V_T 仅映射到 σ_pc≈3–5 popcount → 精度跌 **<0.15pp**（R_TI≈400–700Ω）——即**正确预算的读出跨阻大体吸收了 plain SA 失调**；仅当 V_in 偏小（0.4V）且扇入大（layer2）时 σ_pc 越过曲线膝点。故论断从「必须自调零」精炼为**量化设计边界**：MNIST 级扇入 + V_in≥0.5V 时 plain SA 即够（可省自调零面积/能量），低压/宽扇入/欠预算增益才需自调零或加大 SA 面积。注：AVT 是 sky130 量级假设、130nm 偏悲观，报比值 σ_offset/V_T 而非绝对 mV；PC_FS=3√F、线性跨阻、BN 参考理想为 first-cut。**版后（2026-06-26）**：SA 版图器件集已修正为 **11 器件**（补 Mp3/Mp4）、**DRC 0 违例**、Magic extract+ext2spice 与 netgen LVS 工具链已打通（设备级；完整 LVS 待器件间布线，见 `eda/hero/layout/LVS_GUI_CHECKLIST.md`）。`sa_postlayout.py` 给出版后设计律：失调由失配主导（11.05mV），**对称的 da/db、outp/outn 布线**可使版图不对称失调 ≪11mV → 「两侧布线匹配」为 R2 的版图级规则。**C1 Pareto 收口**（`hero/pareto_offset_cancellation.py`，含噪声地板 0.15pp）：在斜率匹配最大增益读出下，{无/4×面积/单容自调零/两相斩波} × 读出工作点扫描显示 —— **V_in≥0.5V、MNIST 级扇入时 plain SA 即 Pareto 最优**（0.47·V_T 落在 σ_pc~2–4 膝点下，精度差落在单次 MNIST 噪声内，自调零/斩波只白加面积+能量）；**仅 V_in≤0.4V/宽扇入(F=1024)/欠预算增益**角落里 plain SA 越膝点（掉 0.34pp>噪声），自调零才挣回成本（+0.21pp）。边界：layer1 V_in≤0.35V、layer2≤0.40V。**故 R2 终结为「按 V_T 预算失调、非 TMR 余量；除非读出增益预算所迫，否则省去自调零」的量化设计边界**，非「必须自调零」。**C2 校准半边**（`hero/write_dac_trim.py`）：剩余的**每列**系统性 V_th/失调由既有写-DAC 加 **3–4 trim-bit** 近免费抵消（σ_col=8 popcount：96.35%→b3 96.82%≈基线；静态每列码摊销→<1% 写能，因写占 98.7%）——即 C1（省自调零）+ C2（写-DAC 微调）共同把每列失调压回噪声地板。

### R3 — 「256×256、$R_P\sim5$k 下 IR-drop 可忽略」(论断 c2)
- **位置**：`article/chapter04.md` §4.3；`src/smtj_pbnn_sim/array/ir_drop.py` (文档化空桩，从不被调用)。
- **问题**：`estimate_ir_drop()` 仅返回 $r_\mathrm{line}/(r_\mathrm{line}+r_\mathrm{cell})$ 的朴素最坏比值，**无求解器**；「可忽略」无任何求解支撑。尤其**低阻 (776 Ω) 的 SOT 写线** 被空桩完全忽略，远端 $V_\mathrm{wr}$ 跌破 $V_\mathrm{th}$ 是真实风险。
- **行动**：EDA 阶段 5 版图 + Quantus/开源 PEX，DC 线扫描给真实压降与 popcount 误差 vs 阵列尺寸；据结果坐实或推翻「可忽略」。
- **状态**：`进行中(first-cut)`。**sky130 PEX 已给真实数**（`eda/extraction/writeline/`，Magic `extresist`，poly 47.96 vs techfile 48.2 Ω/sq 自校验）：写线往返金属 R（BL+SL）vs 776Ω 写器件——N≤64 **可忽略**（<5%）；**N=256 met1/met2 W=1µm ≈128Ω = 16.5%**（IR≈148mV，高角 19%）；N=1024→66%；**li1 灾难性（kΩ）**。即「IR-drop 可忽略」**仅对小列成立**，高列（N≥256）显著。**新发现**：148mV 压降把远端写电压拉到 ~0.75V，**跌破 0.8958V 标定写点 → p_sw Sigmoid（β_s）位移**，远端写错误率升——具体的器件感知高列上限。设计指引：写线走 **met2+**（勿 li1/poly）、加宽、或分段高列；N≥256 预算 ~10–20% 写裕度。**待**：路由后版图的列级 popcount 误差 vs 尺寸（接 hero SA 读出）。

### R4 — 0.78 pJ 仅为欧姆沟道能量，未含驱动/DAC 开销
- **位置**：`article/chapter04.md` §2.3/§4.3/§4.5；`tech_params.py` `e_smtj_write` 属性。
- **问题**：$E=V_\mathrm{wr}^2 t_\mathrm{w}/R_\mathrm{SOT}$ 不含写驱动晶体管 IR/短路能量、DAC 充电能量、BL/SL 寄生；且 0.75 ns 脉冲的上升/下降沿占比非小。端到端写能量预计 **> 0.78 pJ**。
- **行动**：EDA 阶段 2 transient 测量含开销的真实写能量；论文中**并列报告**器件级 (0.78 pJ) 与含驱动端到端两个数。
- **状态**：`进行中(first-cut)`。`eda/testbenches/write_mc_harness.py` 给出首个电路级数：10Ω 理想驱动下信道能量 E_sot≈0.80 pJ、驱动开销仅 1.3%（**乐观**：假设不现实的 10Ω 理想驱动且交付仅 0.889V）。**已用真实 sky130 CMOS 驱动替换**（`eda/testbenches/run_write_driver.sh`，WSL ngspice+sky130，扫 W_p）：1.8V CMOS 反相器驱 776Ω SOT，**交付 0.9V 时（W_p≈7µm）E_dev=0.785pJ（对上 0.783 基线）但电源取 E_vdd≈1.61pJ → 驱动开销 ~105% → 端到端 ≈2.05× 欧姆数**。开销源于 Ron/776Ω 分压（1.8V 取 0.9V，半压半能耗在驱动）。两条naive逃逸都亏：缩小驱动(W_p≤4)欠驱(vflat<0.6V写失败)；放大(W_p≥16)过驱向 1.8V → E_dev 涨到 1.9–2.9pJ（V²损耗）。**结论=需稳压 ~0.9V 写轨**（LDO/电荷泵），非 1.8V 核心电源。论文**并列报告器件级 0.783pJ 与端到端 ~1.6pJ**。详见 `eda/testbenches/write_driver_results.md`。

### R5 — 「sMTJ 0.78 pJ vs CMOS p-bit 5 pJ = 4.2×」(论断 d) 的基准与口径
- **位置**：`article/chapter04.md` §4.5；`tech_params.py` (Camsari 2020 / 5 pJ 引用块)。
- **问题**：(i) 「Camsari 2020、5 pJ/update」这一锚点**未能从公开源干净核实** (核查发现有据可查的近期 CMOS p-bit 为 6.95 pJ/bit，MDPI Electronics 2024)。(ii) 苹果比橘子：0.78 pJ 是裸器件、CMOS p-bit 数是端到端 cell。
- **行动**：以可核实的 6.95 pJ/bit 重定基准；把 sMTJ 侧也算**端到端 (写+读+数字化)** 再比；预期诚实比值小于 4.2× (但磁性熵源本身 ~2 fJ/随机数，器件级差距亦可论证更大)。停止单引未核实的 5 pJ 点值。
- **状态**：`进行中(first-cut)`。端到端口径已开始落地两块开销：(写侧) 写线 IR 串阻 = R3 的 R_par/776（N=256 met2 **+16.5%** 于 0.783 pJ 器件写）；(读侧) sky130 StrongARM SA 动态能 ~**23–74 fJ/决策**（`eda/hero/sa_postlayout.py`，器件 C 提取=35.25 fF + 布线 C 估算），为 5 fF 读出占位的 **5–15×**——读出能量被占位低估（同 R1）。**待**：6.95 pJ/bit 文献复核 + 路由后 SA 精确读出能 + ADC，给端到端总账与诚实比值。

### R6 — RC 读出在能量模型中近乎免费，与正文「读出是真正瓶颈」(论断 e) 矛盾
- **位置**：`src/smtj_pbnn_sim/ppa/reservoir_energy.py` (读出仅计 `e_int8_mac*n_nodes*n_outputs`) vs `article/chapter05`/RC 论述正文。
- **问题**：行为模型把读出当作微小 INT8-MAC 项，正文却称读出散粒噪声/ADC 是真正能量与精度限制者——二者自相矛盾。
- **行动**：EDA 阶段 7 仿真模拟读出 TIA+ADC 噪声 → 脊回归记忆容量损失；用 NeuroSim/CrossSim 给 ADC+TIA 能量/面积替换 `e_int8_mac` 占位；并列报告 amortized-ADC 与 per-node-ADC 两个括号，复核 ~38× vs 数字 ESN。
- **状态**：`进行中(first-cut)`。P7a `telegraph_lowbarrier.py` 已器件级验证低势垒 τ(V)/⟨s⟩ 旋钮（Δ=3.8，τ_max=22.35ns，rel-err<1.6e-4）——RC 前提成立。`rc_readout_noise.py` first-cut 证实**读出精度是限制者**：mean-field MC0=6.38，per-node ADC≤10bit 或读噪声≥2% 显著掉 MC（10bit→62%、2%噪→47%）。**矛盾已用等能量套利解开**（`eda/testbenches/rc_isoenergy.py`，三方 {N, M=读出节点数, b=ADC位}）。**2.4 已用提取数地标 ADC 能量**：SAR ADC `E_adc(b)=b·E_comp + 2^b·E_capDAC`，**E_comp=48 fJ 取自提取的 sky130 StrongARM SA**（`sa_postlayout.py`；SAR 比较器即该 SA），E_capDAC0≈1.1 fJ（sky130 单位电容）。结论（地标后，比早先粗糙 2^b 模型更诚实）：读出**确非免费**且**主导 RC 能量**——比较器即使 b=3 也占 **88–99% 能量**，故 `reservoir_energy.py` 把读出当免费**根本错**；但比较器项是 **b-线性**（非 2^b），故分辨率惩罚**温和**：b=3→b=10 仅 **38× 能量换 3.66× MC**（非粗模型的 ~230×）。**故真正的能量杠杆不是降位数，而是摊销比较器**：**列共享 SA + 下采样读出（M<N 仍在前沿）**，中高分辨（b~8）可负担。**R6 终结为**：`reservoir_energy.py` 必须计入**主导性的列共享比较器读出成本**，并靠**跨列/跨节点共享**优化、而非降分辨。**待**：sky130 TIA 前端偏置能量（列共享、量级）、复核 ~38× vs 数字 ESN。注：mean-field MC；E_comp 来自提取 SA，E_capDAC/E_dev 量级，结论为**前沿形状+比较器主导**（比值）。

### R7 — 「三位一体」时分复用隐含势垒冲突
- **位置**：RC 论述 / 全文主线 (第 1、4、5 章「同一阵列承担两类任务」)。
- **问题**：PBNN p-bit 要 $\Delta=4.91$，RC 节点要 $\Delta\approx3.5\text{–}4.3$ (ns 级跳变)。**一块流片阵列不可能同时是两个势垒**，除非势垒可电/场调；且未见单一已发表 macro 在同一物理 sMTJ 阵列上时分复用 p-bit-写 与 RC-自由演化。
- **行动**：把时分复用作为**提案/受限架构**陈述 (非已证明能力)；EDA 阶段 7 仿真模式 MUX 与读模式漏电对自由节点的扰动，并显式登记势垒冲突为限制。
- **状态**：`待EDA验证 / 待文献复核`。

---

## N — 澄清性说明 (非错误，服务于 EDA 工作)

### N1 — 两个标定工作点 (894 mV / 44.6 V⁻¹  vs  895.8 mV / 42.7 V⁻¹)
- **位置**：`docs/physics_grounding.md` (Layer-2 表，894/44.6，章节标定值) vs `configs/device/sot_smtj_devA_pAP_0p75ns.yaml` (0.8958/42.71，01 脚本自动拟合值)；`chapter04.md` §4.3 已解释二者差 1.8 mV / 1.9 V⁻¹、属 46 点拟合噪声内。
- **说明**：这**不是错误**——是「章节报告值」与「自动拟合值」两个标注清楚的量。但 Verilog-A 回归测试需要**唯一目标值**。
- **决定**：EDA 工作以仿真器实际使用的**自动拟合值 $V_\mathrm{th}=895.8$ mV、$V_T=23.4$ mV、$\beta_s=42.7$ V⁻¹** 为 Verilog-A 回归目标，并注明其源于章节标定的 894 mV/44.6 V⁻¹ 测量。
- **状态**：`说明`。

### N2 — ARM `mram_simulation_framework` 为 STT/VCMA，不含 SOT
- **位置**：`src/smtj_pbnn_sim/device/llg_dynamics.py` docstring (推荐该工具作外部 s-LLGS 求解器)；`chapter04.md` §4.2 (如实称其为 s-LLGS、Python/Verilog-A 两套实现，未声称 SOT)。
- **说明**：现有文字**无错**。但后续若复用该模型，须知它是**两端 STT/VCMA**，需自行**增加自旋霍尔 (SOT) 写分支 + 三端解耦读/写结构**才能匹配本器件 (β-W、$R_\mathrm{SOT}=776$ Ω)。这是非平凡的额外建模，不是 fork 即用。
- **状态**：`说明`。

### N3 — 开源工具链版本须钉死
- **说明**：开源回退路径需 `ngspice ≥ 43` + `OpenVAF-Reloaded` (OSDI 0.4) — 原 OpenVAF 2023 年底后停维护；**不要用 Xyce** (截至 2024–25 仍用 ADMS、未集成 OpenVAF/OSDI)。所有 MC 须显式记录 seed 与 Spectre `noiseseed` (默认每次跑换新种子，否则不可复现)。
- **状态**：`说明`。

---

## 回填论文检查表 (拿到 EDA 数值后逐项勾销)

- [ ] R1 → 重写 §4.5 每-MAC 能量分解、图 4.14 结论 (外围占比、ADC 协同优化)
- [ ] R2 → 更新 §4.5 非理想性结论 (加入 SA 失调通道与硬件优先级)
- [ ] R3 → §4.3 IR-drop 表述给真实数；必要时新增写线压降讨论
- [ ] R4 → §2.3/§4 并列报告器件级与端到端写能量
- [ ] R5 → §4.5 重定 p-bit 能量基准 (6.95 pJ/bit、端到端口径)
- [ ] R6 → RC 章读出能量重算、解决与 `reservoir_energy.py` 的矛盾
- [ ] R7 → 三位一体改述为提案/受限架构 + 势垒冲突限制
- [ ] 全部 → 由更新后的 `.md` 重新生成对应 `.docx`
