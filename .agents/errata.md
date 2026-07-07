# 勘误与待修正清单 (Errata)

统一记录论文 (`article/`) 与仿真器代码 (`src/`) 中的已知错误、过度声明与待验证论断。
完整调研记录见 [`../.agents/eda/research/2026-06-26_eda_assessment.md`](../.agents/eda/research/2026-06-26_eda_assessment.md)。

许多条目的「修正」依赖尚未开展的可信 EDA 仿真 (见 [`../.agents/eda/ROADMAP.md`](../.agents/eda/ROADMAP.md))，
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
- **状态**：`进行中(first-cut)`。P3 `diff_column.py` 证实 MTJ 级差分消除（匹配线性 err 9e-6 popcount），器件失配（σ_Rp7%/σ_TMR4%）残余仅 ~0.06·√N popcount（N=256 仍 sub-LSB）——claim(a) 在 MTJ 层稳健。**SA 失调已在 sky130 真测**（`eda/hero/run_offset_mc.py`，WSL ngspice+sky130，**N=120 MC firmed**）：plain StrongARM σ_offset=**9.21mV=0.39·V_T**、3σ=1.18·V_T（N=24 早值 11.05/0.47 为小样本偏高，firmed SE≈0.6mV）—— SA 输入折合失调与器件 Sigmoid 斜率 V_T 同级，再注入 Exp.08 认定致命的每列 V_th 偏移类误差。**这把 claim(a)/(c) 改写为「MTJ 层偏置消除，但 SA 失调重新引入它」——hero 发现**。精度侧（`hero_mnist_sweep.py`）：per-cell 随机失调被平均化（欠估），但 SA 失调是**每输出列系统性**（一列一个 SA），per-column 模型 σ=0→8 popcount → 97.0%→96.35%。**闭环已合拢**（`eda/hero/readout_mapping.py`，B5 读出映射）：读出跨阻 R_TI 把 mV 桥到 popcount，`LSB_V=LSB_I·R_TI`、`σ_pc=σ_offset_V/LSB_V`，协同律 `σ_pc=σ_offset_V·2·PC_FS/V_in`（取动态范围允许的最大增益）。**精炼结论**：在最大增益读出下，plain SA 的 0.39·V_T 仅映射到 σ_pc≈2–4 popcount → 精度跌 **<0.15pp**（R_TI≈400–700Ω）——即**正确预算的读出跨阻大体吸收了 plain SA 失调**；仅当 V_in 偏小（0.4V）且扇入大（layer2）时 σ_pc 越过曲线膝点。故论断从「必须自调零」精炼为**量化设计边界**：MNIST 级扇入 + V_in≥0.5V 时 plain SA 即够（可省自调零面积/能量），低压/宽扇入/欠预算增益才需自调零或加大 SA 面积。注：AVT 是 sky130 量级假设、130nm 偏悲观，报比值 σ_offset/V_T 而非绝对 mV；PC_FS=3√F、线性跨阻、BN 参考理想为 first-cut。**版后（2026-06-26）**：SA 版图器件集已修正为 **11 器件**（补 Mp3/Mp4）、**DRC 0 违例**、Magic extract+ext2spice 与 netgen LVS 工具链已打通（设备级；完整 LVS 待器件间布线，见 `eda/hero/layout/LVS_GUI_CHECKLIST.md`）。`sa_postlayout.py` 给出版后设计律：失调由失配主导（9.21mV），**对称的 da/db、outp/outn 布线**可使版图不对称失调 ≪9mV → 「两侧布线匹配」为 R2 的版图级规则。**C1 Pareto 收口**（`hero/pareto_offset_cancellation.py`，含噪声地板 0.15pp）：在斜率匹配最大增益读出下，{无/4×面积/单容自调零/两相斩波} × 读出工作点扫描显示 —— **V_in≥0.5V、MNIST 级扇入时 plain SA 即 Pareto 最优**（0.39·V_T 落在 σ_pc~2–4 膝点下，精度差落在单次 MNIST 噪声内，自调零/斩波只白加面积+能量）；**仅 V_in≤0.4V/宽扇入(F=1024)/欠预算增益**角落里 plain SA 越膝点（layer2@0.4V 掉 0.24pp>噪声），自调零才挣回成本（+0.11pp）。边界：layer1 V_in≤0.29V、layer2≤0.34V（σ firmed 11.05→9.21mV 后 plain-SA-足够区更宽）。**故 R2 终结为「按 V_T 预算失调、非 TMR 余量；除非读出增益预算所迫，否则省去自调零」的量化设计边界**，非「必须自调零」。**C2 校准半边**（`hero/write_dac_trim.py`）：剩余的**每列**系统性 V_th/失调由既有写-DAC 加 **3–4 trim-bit** 近免费抵消（σ_col=8 popcount：96.35%→b3 96.82%≈基线；静态每列码摊销→<1% 写能，因写占 98.7%）——即 C1（省自调零）+ C2（写-DAC 微调）共同把每列失调压回噪声地板。

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
- **状态**：`进行中(first-cut)`。P7a `telegraph_lowbarrier.py` 已器件级验证低势垒 τ(V)/⟨s⟩ 旋钮（Δ=3.8，τ_max=22.35ns，rel-err<1.6e-4）——RC 前提成立。`rc_readout_noise.py` first-cut 证实**读出精度是限制者**：mean-field MC0=6.38，per-node ADC≤10bit 或读噪声≥2% 显著掉 MC（10bit→62%、2%噪→47%）。**矛盾已用等能量套利解开**（`eda/testbenches/rc_isoenergy.py`，三方 {N, M=读出节点数, b=ADC位}）。**2.4 已用提取数地标 ADC 能量**：SAR ADC `E_adc(b)=b·E_comp + 2^b·E_capDAC`，**E_comp=48 fJ 取自提取的 sky130 StrongARM SA**（`sa_postlayout.py`；SAR 比较器即该 SA），E_capDAC0≈1.1 fJ（sky130 单位电容）。结论（地标后，比早先粗糙 2^b 模型更诚实）：读出**确非免费**且**主导 RC 能量**——比较器即使 b=3 也占 **88–99% 能量**，故 `reservoir_energy.py` 把读出当免费**根本错**；但比较器项是 **b-线性**（非 2^b），故分辨率惩罚**温和**：b=3→b=10 仅 **38× 能量换 3.66× MC**（非粗模型的 ~230×）。**故真正的能量杠杆不是降位数，而是摊销比较器**：**列共享 SA + 下采样读出（M<N 仍在前沿）**，中高分辨（b~8）可负担。**R6 终结为**：`reservoir_energy.py` 必须计入**主导性的列共享比较器读出成本**，并靠**跨列/跨节点共享**优化、而非降分辨。**~38× 已复核（Plan 2.5，`eda/testbenches/rc_energy_recompute.py`）**：用 Ch5 规范配置（N=100/ens=96/L=1000，源自 `experiments/16_rc_hardware_ppa.py`）+ 地标 ADC，sMTJ-RC 270.9nJ vs 数字 ESN 10204nJ = 38×（无 ADC）→ 加地标 SAR ADC 后 **~30×（per-node 8bit）/ ~35×（列共享 8bit）**，**优势稳健**（数字 ESN 的 O(N²) matmul 10.2µJ 压倒哪怕含 ADC 的 RC 读出）。故诚实 Ch5 论断 = **~30–35×（非 38×）**，且 `reservoir_energy.py` 应补一个真实 ADC 项（列共享中分辨）。**待**：sky130 TIA 前端偏置能量（列共享、量级）。注：mean-field MC；E_comp 来自提取 SA，E_capDAC/E_dev 量级，结论为**前沿形状+比较器主导+稳健优势**（比值）。

### R7 — 「三位一体」时分复用隐含势垒冲突
- **位置**：RC 论述 / 全文主线 (第 1、4、5 章「同一阵列承担两类任务」)。
- **问题**：PBNN p-bit 要 $\Delta=4.91$，RC 节点要 $\Delta\approx3.5\text{–}4.3$ (ns 级跳变)。**一块流片阵列不可能同时是两个势垒**，除非势垒可电/场调；且未见单一已发表 macro 在同一物理 sMTJ 阵列上时分复用 p-bit-写 与 RC-自由演化。
- **行动**：把时分复用作为**提案/受限架构**陈述 (非已证明能力)；EDA 阶段 7 仿真模式 MUX 与读模式漏电对自由节点的扰动，并显式登记势垒冲突为限制。
- **状态**：`已收口（受限架构可行性包络）`。`eda/testbenches/trinity_barrier.py` 量化：PBNN(Δ=4.91, τ_max=67.8ns) ↔ RC(Δ=3.8, τ_max=22.4ns) 需势垒摆幅 **ΔΔ=1.11 = ΔE_b 28.7meV = 22.6%·E_b** —— 经 **VCMA 栅 ~0.56V**（@~2kT/V，在已证范围内：Kent A-sMTJ arXiv:2509.13458 2025、HKUST VCMA 双功能宏 VLSI 2026）或 **+88K**（不可控）可达。**但**：(i) 两模式时间互斥（mode-MUX，非并发）；(ii) RC 低势垒与 PBNN 写/保持及读扰动冲突；(iii) 无已发表宏在同一物理阵列时分复用 p-bit 写与 RC 自由演化。**故论文须把"三位一体"写成受限、时分复用、VCMA 栅控的提案 + 量化调谐包络 + 势垒冲突限制，非已证并发能力**。注：VCMA kT/V 为文献量级，报需求+比值。

---

## S — 多智能体仿真器评估与修正 (2026-06-28)

> 一次按同类仿真器规范 (DNN+NeuroSim 的逐算子能量/校准-占位纪律、IBM aihwkit 硬件感知训练、
> Sandia CrossSim/MemTorch 的交叉阵列非理想、p-bit 与 RC 文献) 对 `smtj_pbnn_sim` 的独立评估：
> 6 个维度并行评审 + 对每条高/严重发现做对抗式代码核查。**总体判定：六维一致为「基本合理、存在可控缺口」**——
> 核心物理/数学正确、校准-占位卫生诚实、方法学可与 NeuroSim/aihwkit 对标；缺口具体且收敛。
> 本节登记**已修**、**经核查被驳回**、与**有据缓办**三类结果。

### S-A 本次已修 (代码 + 必要的论文/图回填)

| 编号 | 级别 | 问题 | 修正 | 位置 |
|---|---|---|---|---|
| DPM-01 | 高 | delta 变异模式直接以裸 NB 半切电压 (843 mV) 为每单元 $V_\mathrm{th}$ 中心，较写-DAC 实际使用的标定中心 (894 mV) 系统性偏低约 50 mV，使整个变异研究带偏置 | 变异场**均值锚定到标定工作点** $(V_\mathrm{th,nom},V_T)$、仅以 $\Delta$ 离散驱动**单元间离散**：$V_\mathrm{th}=V_\mathrm{th,nom}+(V_\mathrm{th}^\mathrm{NB}-\overline{V_\mathrm{th}^\mathrm{NB}})$、$V_T=V_{T,\mathrm{nom}}\Delta_\mathrm{nom}/\Delta$ (eta_c 在此比值中抵消)。从源头消除偏差，取代原「重抽+推理禁用」的绕行 | `device/variation.py`；回归测试 `tests/test_variation.py`；论文 `chapter04.md` §4.3 易错点段重写 |
| ARR-1 | 高 | `ir_drop.py` 上次重写为按行签名后，`test_array_pure.py` 4/4 用例仍按旧 `cols=` 签名调用 → 全失败 | 测试改按行签名 (写线沿列向下、随行数标度)，并新增 N=256 提取值钉点 | `tests/test_array_pure.py` |
| DPM-02 | 中 | eta_c 默认 5.34 与 44.6 V⁻¹ 参考斜率不自洽 (5.34×7.94=42.4≠44.6)，docstring 又声称精确一致 | 以 44.6/7.94=**5.62** 校正 44.6 系列默认/配置 + docstring；自动拟合配置 (β_s=42.71) 的 5.34 自洽，保留 | `arrhenius.py`、`pbnn_linear.py`、`_mnist_{train,eval}.py`、`configs/experiment/mnist_lenet.yaml`、`05a_*` |
| ARR-2/3/4/5 | 中 | `crossbar.bitline_current` 名为「差分」实为单端 (含共模项)；多处 docstring 过度声明 (resistive-ladder solver、「invoked by full_stack」) | `bitline_current` 改为真差分 (减互补列、共模相消)；更正 docstring 并注明这些是**参考原语、不在训练前向路径上** | `array/crossbar.py`、`array/ir_drop.py`、`array/tile.py`、`array/periphery.py` |
| RC-02 | 高 | exp18 把「原始单项式上保留 $r^2$ 之和」标注为 Dambre 信息处理容量 (IPC)；论文图5.6/§5.2 据此引 Dambre | 全部更正为「处理容量代理 (各阶延迟单项式保留 $r^2$ 之和)」，明确非正交化 IPC、仅作相对比较；重生图5.6 (风格不变、仅标签) | `experiments/18_rc_benchmarks.py`、`chapter05.md` §5.2/§5.5、图5.6、`README.md` |
| PPA-3/4 | 中 | 储备池逐器件 sense 与逐节点 ADC 计费口径不一致；5 fJ/器件 sense 来源不明 | 在 docstring 明确读出架构 = **逐器件模拟缓冲 → 节点共享求和线 → 逐节点 SAR ADC** (二者本就自洽)；`e_dev_read` 如实标为数量级占位 (同 DAC/计数器)。**不改能量数** | `ppa/reservoir_energy.py` |
| — | — | 上次将读出能量地标到 48 fJ 后，`test_per_mac_energy_dominated_by_smtj_write` 阈值 (0.95) 失配 (实为 0.94) | 阈值改 0.9 并注明读出已地标 | `tests/test_ppa.py` |

全套 95 项单元测试通过。图5.6 已重生并复制到 `article/figs/Chapter05_local_06.png` (exp18 带种子、数据不变、仅更正标签与标题)。

### S-B 经对抗核查被驳回 / 无需改 (记录留痕)

- **NN-01**（硬件感知前向对变异不敏感）：核查属实——但论文**已正确表述**为「硬件感知训练使**梯度**感知 D2D 失配」(§4.3、§4.1)，并非声称前向鲁棒；硬-二值前向 + 软-反向 STE 亦如实描述。**无过度声明，无需改**。
- **NN-02**（θ×100 使全栈塌缩为近确定性）：机理 (θ 缩放推 p 趋饱和) 属实，但「近确定性」结论**被交付稿自身的 T 扫描经验数据驳回**：表4.1 与图 A.3/A.4 显示全栈精度随 T 显著上升 (CIFAR T=1→64：34%→62%)；因 θ~$O(1/\sqrt N)$、θ×100 给 p≈0.96 而非 1，残余逐样本随机性真实且 T 平均确实有效。**故全栈结果确为随机、无需改写**。

### S-C 有据缓办 (登记为已知限制，本次未改)

- **exp05a CNN 附录** (Fashion/CIFAR，用 delta 变异)：DPM-01 重心修正会扰动其变异场，但 (a) 硬件感知训练前向对变异不敏感、(b) θ×100 主导 → 对最终精度影响 <0.1pp、低于附录已声明的逐次运行噪声；CNN 需从头重训 (非仅评估) → 图 A.3/A.4 未重生，eta_c 已为将来重跑更新为 5.62。
- **PPA-1/PPA-2** (面积/延迟模型未含 ADC/SA/SAR 电容阵列)：真实完整性缺口；面积/延迟现以相对标度报告、绝对值已标占位。待 sky130 SA/ADC 面积与延迟提取后补 `a_*`/`t_*` 项 (镜像已地标的能量项)。
- **DPM-03/04/06/07、NN-03..08、RC-01/03..07、SE-01..07**：诚实的建模/工程缺口与未来工作 (线性势垒律未对 LLG 交叉验证、D2D 仅单通道无 $R_P$/$\Delta$ 相关、无回声状态属性运行时检查、IPC 未正交化、RC 实验无 seed 清单与 resolved-config、CLT 独立性假设未校验等)。均不改变核心结论，登记备查、择期处理。

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

## 回填论文检查表 (拿到 EDA 数值后逐项勾销；2026-07-06 逐项对照正文核验)

- [x] R1 → §4.5 能量分解已改为「28nm 占位→4.6 节 sky130 提取/估算」口径 (读 48 fJ、DAC ~34 fJ、计数 ~19 fJ，写占比 98.7%→93.8%)。实测落点：外围占比 ~1%→~11%，**低于本表预期的 20–40%**，写仍主导 ~89%——预期方向对、幅度小。残余：版后布线 PEX 后的精修 (PLAN 1.10)。
- [x] R2 → §4.6 已含 SA 失调通道、斜率匹配协同律与 plain-SA Pareto 边界 (chapter04.md §4.6，图 4.15)。
- [x] R3 → §4.6 已给写线 IR 真实提取数 (N=256 met2 ≈128 Ω=16.5%，chapter04.md:265) 与设计指引。残余：路由后列级 popcount 误差 vs N (PLAN 3.2)。
- [x] R4 → §4.6 已并列报告器件级 0.78 pJ 与端到端 ~1.6 pJ (chapter04.md:265，图 4.16)。
- [x] R5 → 正文未采用本表建议的 6.95 pJ/bit 重定基准，而是把 5 pJ 锚点落到 Camsari 2019 APR 综述 + Borders/Sutton 原型机作边界 (chapter04.md:205 脚注 [^cmos_pbit_camsari]，DOI 已核)，并单列端到端写能 1.6 pJ。**残余口径已于 2026-07-08 闭环**：§4.5 新增单参数敏感性扫描句与 [^energy_sens] 脚注 (exp22)——并列器件级 6.4× 与端到端 3.1× 两个口径、注明均与总能耗 3.9× 同向；p-bit/sMTJ 包络 1.5–10.9× (对 5 pJ 锚点线性敏感、方向全程不变)，sMTJ/STT 包络 0.7–1.6× 跨越持平点故改口「同档」。
- [x] R6 → 第五章已重算 (~30×/~35×，chapter05.md:104) 并显式解释「读出非免费、比较器主导、列共享摊销」协同 (chapter05.md:108，图 5.8/5.9)；`reservoir_energy.py` 已补地标 ADC 项。残余：TIA 前端偏置能量 (量级)。
- [x] R7 → 第五章已改述为受限、时分复用、VCMA 栅控的提案 + 22.6% 势垒摆幅 + 三条限制 (chapter05.md:126)。
- [~] 全部 → `.docx` 由 watcher 自动重生；当前工作树有 chapter04/05 `.docx` 未提交的重生版 (与 `.md` 一起提交即闭环)。
