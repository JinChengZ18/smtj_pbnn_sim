# MTJ 版图/结构/物理实现研究计划（2026-07-08，三档论证）

> 来源：2026-07-08 核验工作流 run `wf_370c1031-56e`（5 个联网事实核验 + 1 个仓库钩子核查；两个智能体因瞬时 API 错误未完成——SOT 材料项已由 Hikstor 核验组覆盖并由主会话补核 Pai 2012，综合由主会话完成）。所有文献带 DOI/arXiv；unverified 条目单列于文末。
> **底线判断**：现有数据**够做** L1「抽象 BEOL 集成版图」与 L2「结构物理自洽与设计窗」两档，**不够也不应做** L3「可制造 MTJ 版图」——后者在开源生态今天不存在实现路径（连 sky130B ReRAM 的官方 DRC 都从未发布），且 sMTJ 垂直堆叠细节属 Hikstor 专有。L3 应写成生态事实而非自我设限。
> 状态标记：⬜ 未开始 · ◑ 进行中 · ✅ 完成。

## 数据边界（核验后精确划线）

**可公开引用、可写进版图黑盒规格的几何**（全部出自 Hikstor EDL 2024：DOI 10.1109/LED.2024.3454609, arXiv:2404.09125，全文已读）：MTJ 柱物理 CD≈80 nm；底电极间距 200 nm；SOT track 与顶电极宽 200 nm；SOT 层 = **W，t=4 nm，ρ=250 µΩ·cm，θ_SH=−0.3**；top-pinned 堆叠序 SOT/CoFeB/MgO/CoFeB/SAF，350°C 30 min 退火；R_SOT=776 Ω（729 颗晶圆均值，与本项目标定值逐位相同）；器件级 CV：R_P 8.98%、TMR 3.21%、R_SOT 7.19%；300 mm 平台。

**只能以「合作方晶圆实测标定」身份出现、不得画进可复现版图的**：D_elec=65 nm（实为专有 RA/R_P 之商：16.6/4900 µm² → 65.7 nm，派生量）；t_FL=1.1 nm、MgO 1.4 nm、RA=16.6 Ω·µm²、R_P=4.9 kΩ、Δ=4.91——Hikstor 无任何公开 sMTJ 论文（公开器件是 RA=36、R_P=10.89 kΩ、Δ≈59–64 的记忆级堆叠，不同产品线）。SOT 沟道 240×200×4.3 nm+ρ=278 µΩ·cm 的拆分是拟合标定（构造性复出 776 Ω），其中仅宽 200 nm 与标称 4 nm/250 µΩ·cm 公开。

## L1 · 2T 单元抽象 BEOL 集成版图 ⬜（数据充分；规模 S–M）

**动机（审稿人视角）**：「你的面积数是纸面估算还是版图」——当前 a_smtj_cell=4.6 µm² 是 cell-count×design-rule 一阶估算（`area_estimate.py:15-18` 自认非 DRC-clean GDS）；画出真实 2T 单元把面积从估算升级为提取，同时给 T3-5 列级重放提供带真实寄生的单元模板。

**学术合法性（引用锚，均已核验）**：混合 CMOS/磁性 PDK 惯例——MTJ = 未改动 CMOS 之上经 via 连接的 BEOL 附加层 + abstract view 进标准流程（Prenat ICCAD 2011, DOI 10.1109/ICCAD.2011.6105334；SOT 标准单元直接对口先例 Di Pendina ASP-DAC 2014, DOI 10.1109/ASPDAC.2014.6742971）；开源学术 PDK 上叠 MTJ 层的先例 MagPDK（SBCCI 2016, DOI 10.1109/SBCCI.2016.7724055，基于本就不可制造的 FreePDK45——学术版图研究不以可流片为前提）；sky130 生态官方口径「NVM 是不动 FEOL 的 BEOL 模块」（sky130_fd_pr_reram 官方文档）。对照 NVSim/NeuroSim（DOI 10.1109/TCAD.2012.2185930、10.1109/TCAD.2018.2789723）零版图的领域常规，本项目做到 CMOS 部分 DRC-clean 属超出常规的严谨性。

- **依托设施**：`eda/hero/layout/gen_sa_layout.py` 的 Sky130()+place() PCell 模式可直接复用（两个 nmos18，w=2.2/0.42 µm，WSL `klayout -b -r`）；DRC/PEX 流程已验证（器件级 0 违例、35.25 fF）；ch4:299 已有黑盒+不可制造声明口径。
- **执行草案**：(1) 2T 单元 GDS：写管 W≈2.2 µm + 读管 0.42 µm（`area_estimate.py:71-79` 推导链），FEOL+金属 DRC-clean；(2) 伪 BEOL 黑盒层：MTJ 柱（80 nm 包络，公开 CD）+ SOT track（200 nm 宽，公开）画在保留 GDS 层，插层位置参照 sky130B ReRAM 的 met1–met2（via1 加倍）模板或 IHP MEMRES 的 M2–M3 方案作类比论证；(3) Magic PEX 提取（黑盒除外），报提取面积 vs 4.6 µm² 估算；(4) **输出单元 pitch**（写管宽 2.2 µm 定 x 向、5×MET1_PITCH=1.7 µm 定下限、√4.6≈2.1 µm 方形假设三口径并报）——L2c 的输入；(5) 剖面示意图（结构叙事用，标注公开/标定两类参数来源）；(6) 可选抬升：把黑盒方法整理成最小「sMTJ 抽象层」套件（层定义+pcell+提取 deck，MagPDK 交付形态），须明示与 MagPDK 差异（sky130A 底座、SOT 三端、超顺磁无稳态）。
- **措辞约束**：只声称 CMOS 部分 DRC-clean，全文不出现「全芯片 DRC-clean」；「不可制造声明」写成方法学选择（sky130A 无 MRAM 模块、MTJ 层无官方 DRC deck），是综合既有先例的归纳、非引用某文献的既定术语。
- **DoD**：GDS + DRC 报告（CMOS 层 0 违例）+ 提取面积对比 + pitch 三口径 + 剖面图入库；题注含不可制造声明。
- **风险**：2T 单元器件间布线可能与 SA 一样卡 GUI（1.7 同类问题）——但 2 管+直连远简于 11 管 SA，脚本化布线概率高；若卡住则退化为「器件摆放+黑盒+估算布线」仍可交付面积上界。

### L1 执行级决策附录（2026-07-08 补，执行前逐条确认）

1. **插层位置（已定建议）**：黑盒跨 **met2–met3**——SOT track/底电极落 met2（与 R3 设计规则「写线走 met2+」直接耦合，写电流路径 = met2 写线 → BE → SOT track → BE → met2），MTJ 柱顶电极上引 met3 读线；同时与 IHP MEMRES 的 M2–M3 方案同构（sky130B ReRAM 的 met1–met2 作为另一模板在剖面图注里并引）。黑盒属注记层，此决策可逆、零 DRC 代价。
2. **黑盒 GDS 层映射**：选两个 sky130A techfile **未占用**的 GDS layer/datatype 对（一个给 MTJ 柱包络、一个给 SOT track），映射表写进 `eda/hero/layout/README.md`。Magic 读 GDS 时忽略未知层 → extract/extresist 不受影响；KLayout DRC deck 只跑 CMOS 层。执行时用 `sky130A.tech` 的层清单反查空位，勿凭记忆挑号。
3. **交付文件与流程**：`eda/hero/layout/gen_2t_cell.py`（复制 `gen_sa_layout.py` 的 `Sky130()`+`place()` 模式；nmos18 w=2.2 与 0.42 µm 各一）→ `cell2t.gds`；DRC 复用 `run_drc.sh` 模式（WSL + ASCII build dir）；PEX 复用 `run_pex.sh` 模式；**LVS 范围界定**：仅两管器件级、MTJ 作端口黑盒 subckt（可选项，不进 DoD）。
4. **排程修正**：L1 主路线是 `klayout -b` 脚本，**不依赖 GUI 窗口**——「与 1.7 同窗口」只在脚本布线失败落到 GUI 时才成立；且 T3-5（列级重放）以 L1 的 2T 单元为模板，若 T3-5 要赶答辩展示，L1 应提前单独做。
5. **回灌**：L1 提取出真实 pitch 后，把 L2c 串扰证书里的 √4.6≈2.1 µm 假设换成提取值重跑一次 `structure_consistency.py`（一行参数）。

## L2 · 器件结构自洽与设计窗研究 ◑（核心已执行，见 EXECUTION.md B4；2026-07-08 状态同步）

> **B4 完成（`eda/testbenches/structure_consistency.py` + summary JSON + `figures/structure_consistency.png`，commit 5d8567f）**：L2a ✅（保持 Δ=48.5 kT vs 公开带 59.3–64，K_eff 81.1% 补偿的敏感度解读 + CV(Δ)=7.7% 的微观离散解释）；L2c ✅（dp/dB=0.275/mT；2T 间距 δp≈1e-5；1% 临界间距 211 nm，含 ×1.5 点阵和裕量）；L2b 设计窗已算出但**双 CD 候选被修正降格**——同叠层达 Δ≈4.9 需 D_elec→17.2 nm（非早前按面积线性猜的 ~70 nm），17 nm 级光刻使空间双模阵列吸引力大降，sMTJ 更可能是近补偿叠层变体。
> **残留（按价值排序）**：(1) 稿件整合——版图/结构小节入 ch4，等并行编辑落定（EXECUTION B4 余步；**须含口径修正 #5 的 θ_SH 区分句**）；(2) L2c 的 LLG 侧交叉核验未做——`replace(constants, h_ex_z=...)` 重放 ser case 对 dp/dB=0.275/mT 做独立核对（可选但兑现双模型锚，半天量级）；(3) L2b 双 CD 新颖性查证降为「先决定去留」——若保留只作设计窗图的一句讨论，不再作候选贡献点；(4) L1 完成后用提取 pitch 回灌 L2c 证书（现用 √4.6≈2.1 µm 假设，一行更新）。

### L2a 结构↔电学自洽闭环（S）✅ 2026-07-08

几何参数组 (Ki, Ms, t_FL, D_elec) → 保持势垒 Δ_ret = µ0·Ms·H_k_eff·v/(2kB·T)。**实现缺口只有一个约十行的组合式**（核验确认：`configs.py:194-195` Heff、`:189-191` 体积、`demag.py:27-72` 精确扁椭球退磁因子全部现成；`initialize.py:87-90` 已隐式用 1/(2Δ)）。**口径陷阱（写作时必须区分，vendor `docs/parameter_validation.md:24` 已明示）**：几何预测的是**保持** Δ；本模型标定的 **Δ=4.91 是 Néel-Brown 开关律指数**，两者不可直接比。研究内容 = 算出该 sMTJ 堆叠的几何保持 Δ，与 NB 开关 Δ、实测 τ(0V)=67.8 ns 三方对账：若吻合则「结构参数组自洽」成为标定可信度的独立证据；若有张力（类似 η_c 亚畴缺口）则如实记录为单宏自旋模型的已知边界——两种结果都有论文价值。同步做 RA×A→R_P、ρl/(wd)→R_SOT 的构造性闭合表（标明哪些是拟合、哪些是公开标称）。

### L2b CD 设计窗与双 CD 双模阵列候选（S–M）◑（设计窗已算出；双 CD 候选经 B4 修正降格，见上方状态框）

固定堆叠下扫 MTJ 直径 D：Δ_ret(D)∝面积、R_P(D)=RA/A、写电流密度、V_T 变化 → 「结构设计窗」图。**候选亮点（新颖性未核验，动笔前须查）**：PBNN（Δ=4.91@D=80 nm）与 RC（Δ≈3.8）的势垒差按面积比折算 D≈70 nm——**同一膜层、两种光刻直径的空间分区双模阵列**，是对第五章 VCMA 时分复用「三位一体」提案（errata R7 收口）的静态替代：无需栅控、无模式切换，代价是分区固定。若文献查证无先例，可作 ch5.6 双模架构小节的增量贡献点；已知最近邻 = Kent 组 STT 驱动可调 RTN（arXiv:2509.13458）与 VCMA 调势垒谱系，双 CD 静态分区未见（unverified-absence，须再查「dual diameter / heterogeneous barrier MTJ array probabilistic」类关键词）。

### L2c 磁场敏感度与偶极串扰界（S；新颖性判定 = partially-preempted，小节级）✅ 2026-07-08（解析实现；LLG 侧交叉核验为可选残留）

**主会话预算（用项目实参 Ms=0.625e6、D_elec=65 nm、t_FL=1.1 nm，m=2.28×10⁻¹⁸ A·m²）**：邻居轴向偶极耦合在 2.1 µm 单元间距 ≈ 2.7×10⁻⁵ kT（完全可忽略）；0.5 µm ≈ 2×10⁻³ kT；0.2 µm ≈ 3×10⁻² kT——对 p≈0.5 工作点即 ~1.5% 系统性概率偏移，与 ch5 读出噪声地板同量级。**故结论有真实拐点**：写 FET 决定的 2T 间距下磁串扰不构成约束（定量证明黑盒抽象在磁学上自洽），无 FET 密集 BEOL 阵列（亚 µm）才进入需预算区。反解「Δp_sw=1% 界」的临界间距即设计规则，与确定性 MRAM 的 30–100 nm 规则（Caçoilo arXiv:2312.05245）并列——低势垒阵列的磁串扰临界间距比确定性 MRAM 松约一个数量级、却严于直觉。

- **先例定位（核验完毕）**：原料全部已发表——STT-MRAM 耦合因子 Ψ=2% 密度判据（Wu, arXiv:2011.11349，会议版 DATE 2020）；确定性 p-MTJ 阵列 pitch 界（Caçoilo arXiv:2312.05245：常规 30 nm 即够、PSA 需 >100 nm）；p-bit 建模中的偶极项先例（Camsari 双自由层模型，PRApplied 15, 044049, DOI 10.1103/PhysRevApplied.15.044049）；sMTJ 驻留时间场敏感性实验（Hayakawa, PRL 126, 117202, DOI 10.1103/PhysRevLett.126.117202）；有意偶极耦合 p-bit 提案（McCray, Sci. Rep. 10, 2020, DOI 10.1038/s41598-020-68996-y，150–250 nm 间距、仿真）。**「超顺磁/p-bit 阵列偶极串扰 pitch 设计规则」的系统研究检索未见**（unverified-absence）——作为小节级设计规则分析未被抢先，撑不起独立章/独立论文。
- **必须处理的三个审稿人问题**：(i) 邻居是 RTN 涨落源、时间均值为零——静态最坏情形（全邻居同态）与涨落伪相关两条通道分开算；(ii) 器件内 SAF/固定层静态杂散场大若干数量级、靠叠层补偿——先引 AIP Advances 2017（DOI 10.1063/1.5006422）与 IEEE 文档 6479127 交代这一层再谈邻居场；(iii) 近间距点偶极失效——有限尺寸修正 + 近邻外点阵求和（×1.2–2）。
- **dH→dp_sw 通道（核验确认可行）**：LLG 侧 `replace(constants, h_ex_z=...)` 重放 `ser_sot_no_vcma_thermal`（场方向取易轴 z 或 ±y，**勿取与 σ_SH 共线的 x**，`configs.py:103-124` 有约定警告；先例模式 `analysis/variability.py:157-170`）；行为侧经 Δ 通道（dH→dΔ→`vth_neel_brown` 解析 dV_th）或复用 `sigma_sense_offset_V` 加性偏移结构——两侧都不动运行时内核，顺带兑现双模型锚。

**L2 整体 DoD**：自洽闭合表 + Δ 三方对账 + CD 设计窗图 + 串扰 pitch 规则图入库，全部可由入库脚本复现；双 CD 候选完成新颖性查证后决定是否升格为贡献点。

## L3 · 可制造 MTJ 版图 ——明确不做（生态不可行 + 数据不足，写成事实）

核验结论：开源生态今天不存在任何 MRAM/MTJ BEOL 模块或公开 MTJ 设计规则（sky130A/B、gf180mcu、IHP SG13G2 多源检索零命中）。唯一 BEOL NVM 先例 sky130B ReRAM 的现状是警示：met1–met2 插层、via1 高度加倍需专用 PDK 变体，官方 DRC 规则从未发布（issues #1/#2 自 2021-11 开到 2026-04 仓库归档仍 open），模型为未编译 Verilog-A 需社区补丁；IHP MEMRES（TiN/HfO2/TiN，M2–M3）按申请获取、不在开源 PDK；IHP 路线图（SignHep）RRAM 在研、MTJ 无时间表。叠加 sMTJ 垂直堆叠专有（上节数据边界）与 D5 的 IP 隔离纪律，「可制造 MTJ 版图」既无规则可依也无数据可画。**论文写法**：作为生态事实陈述（可引 sky130B ReRAM 与 IHP 公告佐证），支撑「以器件实测标定+行为级黑盒为锚」的方法论选择；展望段可提开源 BEOL NVM 模块正在到来但以 RRAM 为先。

## 前置口径修正（动笔前完成，均为一句话级；2026-07-08 状态：#1 ✅ A2、#2 ✅ A7 用户全文自查保留原数字、#3/#4 已入 EXECUTION 阶段 C 跨仓库项、#5 已挂到 B4 稿件段余步）

1. **chapter04.md:233**：「约100 nm 临界尺寸…由第二章晶圆标定给出」存在归属张力——~100 nm 出自 Hikstor IEDM-2024 无沟道论文（另一结构、付费墙数字，开放网络核不出），第二章标定器件是 80 nm 带沟道结构。改为明确归于工艺参照并与 80/65 nm 分开表述；若作者无 IEDM 全文自查，改引 EDL 的 80 nm（DOI 10.1109/LED.2024.3454609）或 Materials Futures 的 sub-100 nm/28 nm-node 平台表述（DOI 10.1088/2752-5724/ae53fe）。
2. **ch4 脚注 [^hikstor_data] 的数字**（660 µA、1.18/0.54 pJ/bit、16.5%/39.2%）开放网络不可核验，只能以 IEDM 原文全文为据——作者持有全文则自查后保留，否则降格/换锚。
3. **D_elec=65 nm 出处**：在第二章（02MRAMSim/vgsot-sim 仓库）加一句「由实测 RA 与 R_P 推导的电学有效直径（65.7≈65 nm），物理/电学 CD 之别是本文标定处理」——vendor `docs/parameter_validation.md:21` 已有对账，交付正文没有。跨仓库项，随 VA 同步窗口处理。
4. **configs.py:42 注释「e.g. β-IrMn」陈旧**：该器件 SOT 层是 β-W（EDL 公开 W/4 nm/250 µΩ·cm/θ_SH=−0.3；β-W 巨自旋霍尔角经典出处 Pai 2012, APL 101, 122404, DOI 10.1063/1.4753947，|θ_SH|=0.30±0.02，本会话已核验）。跨仓库项，并入 `pending_vgsot_destale` 清单。
5. **θ_SH 双口径预警**：vgsot-sim 重标定的有效 θ_SH=0.066 与 EDL 公开材料值 −0.3 相差约 4.5×——写结构章节时须加一句「材料自旋霍尔角 vs 器件级有效效率（自旋透明度/几何因子）」的区分，否则是现成的审稿人问题。

## unverified 清单（引用落笔前须再核）

- IEDM 2024 无沟道论文的具体数字（~100 nm、660 µA、pJ/bit 系列）：付费墙，须作者以全文自查。
- 双 CD 双模阵列候选的新颖性：本轮未查，动笔前专项检索。
- IEEE 文档 6479127（杂散场对垂直 MTJ 翻转的影响）：仅 Xplore 条目级。
- sky130B ReRAM 的 open_pdks changelog 条目、open-source-silicon.dev 讨论页：直接抓取失败，内容经搜索摘要核对。
- IHP 铁电/FeFET 开源模块：unverified-absence（检索零命中）。
- Wu 等耦合因子论文的 DATE DOI（10.23919/DATE48585.2020.9116444）转引自 arXiv 页面，未独立点验。

## 与既有计划的关系

- L1 完成即闭 `PPA_grounding_plan.md` 精修项 1（DRC-clean GDS 面积），并为 `plans/2026-07-06_defense_hardening.md` T3-5（列级重放）提供带寄生的单元模板——建议 L1 排在 T3-5 之前。
- L2c 的场敏感度通道与 T3-4（V_th 慢漂移）共用 variation 层注入模式，可合并实现。
- L2b 双 CD 候选若查证存活，挂到 ch5.6 双模架构小节（与 errata R7 的 VCMA 时分复用提案并列为两条路线）。
- 排程建议：口径修正 1/2 并入阶段 A（答辩前必做）；L2a/L2c 为 S 级纯 Python/重放，可与阶段 B 并行；L1 与 1.7 SA 布线同窗口做（同为 KLayout/GUI 性质）；L2b 查证后定级。
