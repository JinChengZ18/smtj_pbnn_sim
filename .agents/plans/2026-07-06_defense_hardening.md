# Tier 3 · 答辩加固计划（5 项，按紧迫性排序）

> 状态标记：⬜ 未开始 · ◑ 进行中 · ✅ 完成。完成后在此就地更新，并回写 [`../MEMORY.md`](../MEMORY.md)。

## T3-1 表 4.6 占位常数敏感性审计（含必做步骤 0）——✅ 2026-07-08 完成（步骤 0：实际**两行**变动 sMTJ + stoch-ReRAM；步骤 1–3：`experiments/22_energy_sensitivity.py`，实测包络 p-bit/sMTJ 1.5–10.9×方向稳健、sMTJ/STT 0.72–1.64×跨 1 改口同档；§4.5 已带包络句与 [^energy_sens] 脚注。残留待定：龙卷风图是否收进正文/附录）

**动机（审稿人视角）**：「1 pJ/MAC 的出处和不确定度是什么」一句即可动摇整张 9 架构训练能耗表。且**表 4.6 相对当前 master 代码已陈旧，本条已于 2026-07-06 独立复现属实**：重跑 `experiments/13_training_energy.py`（run `runs/13_training_energy_20260706_225408`）得 sMTJ **12.73 J**（表中 11.91 J）、sMTJ/STT-MRAM **1.22×**（正文 1.14×）、p-bit/sMTJ **3.89×**（头条 4.2×）——sky130 重地标（读 48 fJ 等）落进代码后实验 13 未重跑回填。步骤 0 是必做修正，非可选加固。

- **依托设施**：`src/smtj_pbnn_sim/ppa/tech_params.py`（dataclass 可用 `dataclasses.replace` 替换；「28-nm provisional defaults」自述已核实）、`ppa/training_energy.py`（接受 tech/memory 参数）、`experiments/13_training_energy.py`。正式实现组织为 `experiments/` 下对照实验 13 结构的新实验。
- **执行草案**：
  0. 用当前 `default_28nm()` 重新生成表 4.6，同步回改 4.5 节正文、脚注 `[^nv_ranking]`、图 4.13 与题注（图 `figures/13a_training_energy_breakdown.png` 重生后经 `article/ppt/` 合成，勿直拷）。
  1. 按出处分三档带宽扫描：物理接地的 `e_smtj_write`（晶圆标定，窄带或不扫）；sky130 提取的 read/DAC/counter（±2×）；provisional 的 `e_int8_mac`/`e_mram_read/write`/`e_sram_byte`/MEMORIES 条目与 5 pJ p-bit、3 fJ PRNG（±3× 或文献区间）。
  2. 产出龙卷风图（英文 Arial、图源无编号）+ 每对架构名次反转边界表。
  3. 口径改写：预跑已证实 sMTJ/STT 差距在 `e_int8_mac`±3× 内反转（×3→0.91），1.14×/1.22× 须改口「不确定度内不可分辨」；p-bit/sMTJ 方向稳健（2.7–4.8×），头条软化为「约 3–5×，方向对占位常数稳健」。
- **文献锚**：Horowitz ISSCC 2014（DOI 10.1109/ISSCC.2014.6757323）、Singh 2024（DOI 10.1038/s41467-024-46645-6）、Kurebayashi 2026（DOI 10.1038/s42254-025-00918-1）、Borders 2019（DOI 10.1038/s41586-019-1557-9）。
- **DoD**：表 4.6 与代码一致可复现；龙卷风图与反转边界表入库；正文头条带不确定度包络；`.docx` 随 `.md` 同步提交。
- **风险**：主要是文档返工量（一段正文+一个脚注+一个题注+表格重生成）；结论方向已由预跑证实，风险可控。**规模 S**。

## T3-2 EOT 自适应攻击审计：PGD 优势是真鲁棒还是梯度混淆 ⬜

**动机**：「随机前向的 PGD 优势是 obfuscated gradients 吧」（Athalye 2018, arXiv:1802.00420；Tramèr 2020, arXiv:2002.08347）——答辩命中概率最高的一问。对照 Lammie 2025（Nat. Commun. 16:1756, DOI 10.1038/s41467-025-56595-2，PCM 芯片，经全文核验未做 EOT），先做即成为评测严谨性的差异点。

- **依托设施**：`experiments/07_baseline_comparison.py`（PGD-10 与三模型对照）、HARDWARE_AWARE 模式可回传梯度、`demo/03_mnist_noise_grid.py`。
- **执行草案**：(1) 先修评测口径不一致：`_eval_pgd` 对 PBNN 终评用的是 HARDWARE_AWARE 而非其余各行的 FULL_STACK T=4；(2) FULL_STACK 的 no_grad 约 5 行补丁（仅 Bernoulli 采样保持 detach）；(3) 攻击矩阵：EOT-PGD（K=10–20）× 更多步数/重启 + FP-NN 与确定性 BNN 梯度的 transfer 攻击，终评一律 FULL_STACK T=4；(4) 按结果修订表 4.4、图 4.8（PGD 曲线在图 4.8，非 4.9）与 §4.5 措辞；把 BNN 对照写进结论——现有数据显示确定性 BNN 已达 50.03%（比 FP 高 13.2 pp，机制解释见 ARBiBench arXiv:2312.13575），随机性专属份额仅约 2 pp，诚实表述大概率是「优势主要源于二值化而非随机采样」；(5) 失败调参过程按论文规范留一条脚注。
- **DoD**：EOT 后数字入表、措辞与数据一致；若残余随机性优势存活，对标 Lammie 2025 补一句严谨性差异。
- **风险**：大概率负面结果（15 pp 优势大部分蒸发）——这正是该项存在的意义，工作量风险低。**规模 S**。

## T3-3 真 IPC 正交化：以 Dambre 基替换第 5 章容量代理 ⬜

**动机**：「你的容量指标是 Dambre IPC 吗」——脚注 `[^ipc_proxy]` 自认非正交可能重复计数，是第五章最易被击中的方法学软肋；自旋电子领域已把 IPC 当默认口径（涡旋 STO 先例 arXiv:2603.01351）。

- **依托设施**：`reservoir/metrics.py`（memory_capacity 与 RidgeReadout 骨架）、`experiments/18_rc_benchmarks.py`（面板 (c)(d) 与偏置扫描）、`reservoir/tasks.py`（输入恰为 i.i.d. U(−1,1)，Legendre 正交前提已满足）、meanfield/stochastic 双模式。
- **执行草案**：(1) `metrics.py` 新增规范 IPC：Legendre 基、跨延迟正交化、输入洗牌显著性阈值（协议按 Dambre 2012, doi:10.1038/srep00514；有限样本设计参照 arXiv:2605.19152）；(2) rank(状态矩阵) 总容量上界自检；(3) 重跑实验 18 面板 (c)(d)，meanfield 加长序列（T≥10^4），stochastic 只报过阈容量并脚注注明；(4) 联动修订图 5.6 题注、脚注与正文数字，检验「升偏置释放二次容量、总容量大致守恒」在正交口径下是否依旧成立；(5) stochastic 模式 IPC 缺口解读引 Kubota（arXiv:1906.04608）与 Polloreno（arXiv:2302.10862、arXiv:2601.07257）作框架，只作表征数据不作发现。
- **DoD**：正交 IPC 与代理值前后对照入库；上界自检通过；第五章相关表述按正交口径定稿。
- **风险**：有限样本、有噪状态下正交化病态需正则化控制；stochastic 过阈 IPC 大概率显著低于代理值——更诚实但更难看的数字，第五章多处联动返工属预期成本。**规模 S 偏上**。

## T3-4 V_th 慢漂移压力测试与再校准配方 ⬜

**动机**：「V_th 随时间漂移怎么办」——4.7 节只有一句限制声明，而消融已确立 V_th 绝对位置是唯一显著瓶颈；此项为消融矩阵增加时间轴，并让 C2 trim 获得失配+老化双重身份。

- **依托设施**：`experiments/08_nonideality_ablation.py` Part 2（FULL_STACK + `VariationConfig(mode='sigmoid_direct')` 路径，静态抽样改逐批更新即可）、`eda/hero` 的 C2 trim 链路（`write_dac_trim_summary.json`：σ_col=8→96.824% 恢复）、`calibrate_bn()`（实际位于 `train/train_loop.py:92`）、附录 C。
- **执行草案**：(1) 在 harness/variation 层注入 V_th 的 OU/随机游走与 Δ 单调退化（不动 device/ 物理核心，保护回归测试，符合「随机数留在 harness」约定）；(2) 扫漂移幅度-相关时间（σ_drift/V_T 与相关时间为轴，时间轴用操作计数而非物理秒），量化精度衰减时间常数；(3) 给出「漂移超过 x·V_T 时每 N 次写入刷新 trim/BN」的再校准节拍公式与能量开销，并入实验 04/13 的 PPA 与训练能耗口径；(4) 与器件层在线反馈（PRApplied 23, 054073, DOI 10.1103/PhysRevApplied.23.054073）和阵列级静态补偿（arXiv:2410.16915）显式区分，论证 trim/BN 路线复用既有电路、无需每器件监测，是互补的第三层；(5) 换锚：主锚用 arXiv:2403.11988（非平稳 Langevin 建模）与 Nat. Commun. 2024（DOI 10.1038/s41467-024-48152-0，漂移为公开挑战的实验记录）；arXiv:2505.00538 不提供漂移幅度（原引为幅度锚是误引），降为 RTN 时间尺度参考。
- **DoD**：漂移容忍包络+节拍公式以脚注/小节成文（不扩独立章）；口径为包络/比值，明确不做寿命预测；Hikstor 无实测漂移统计如实标注。
- **风险**：漂移幅度只能取文献量级；若包络显示需高频再标定反而暴露新弱点，须诚实呈现。**规模 S**。

## T3-5 确定性重放式列级随机共仿 ⬜（Tier 3 最重，排答辩窗口后段/期刊方法节）

**动机**：「你的随机性从没进过电路仿真，凭什么电路级结论对随机行为成立」——当前答案只有设计决策解释而非证据；一次全列重放把读出链可信度从分项标定升级为端到端交叉验证（行为级 vs SPICE 统计比对是 CIM 领域成熟做法，NeuroSim V1.5, arXiv:2505.02314），是答辩最有力的展示物。

- **依托设施**：`eda/models/smtj_sot.va`（st 控制节点 + harness-RNG 架构在头注明文预留，正是为此类重放设计）+ OSDI 回归（86 点 R²=1.000000）、`eda/extraction/writeline` 的 extresist 流程（0.5% 自校验，可复制为 readline）、`strongarm_sa.spice`、`diff_column.py`。**注意**：`psw_mc_harness.py` 的 ngspice backend 是 NotImplementedError 存根；列级网表生成器、readline 提取、KS 比对 harness 均为新写（候选原称「MC 夹具现成」有夸大）。
- **执行草案**：(1) readline extresist 提取；(2) 列级网表生成器，N=64 先行（单网表内多 trial 顺序 SA 选通、PWL 驱动各 st 节点摊薄开销），256 为扩展；(3) Python 按标定 P_sw 预抽整列伯努利态 → 含提取寄生的 ngspice 暂态确定性重放 → 电路级 popcount；(4) KS 检验/二项置信区间对行为级管线预测（合理功效需约 500–1000 次列级暂态，单次秒级），报告统计功效；(5) 把 `ir_drop.py` 中「读工作点 popcount 路径压降可忽略」的既有文档化论断从断言升级为实测证据；(6) 以验证小节/附录呈现，与附录 D 双模型验证方法论并列。
- **措辞约束**：不得写「开源链随机性无法进电路仿真」（ngspice 原生有 TRRANDOM/trnoise RTS 源，预生成波形注入是既有技术），诚实框定为「保持单一标定随机源、逐 trial 可复现、可做统计检验」并备好「为何不用 TRRANDOM」的答辩口径；声明重放验证的是读出链联合效应（读线 IR+建立+失调+SA 动态+kickback）而非磁化动力学。
- **DoD**：KS 统计量+置信区间+功效报告入库；若发现电荷共享/kickback 等系统偏差，如实订正 σ_pc 口径。
- **风险**：结论强度受 trial 吞吐限制，上限是「可检验统计精度内一致」；大概率联合效应与逐项一致——按验证而非贡献点写。**规模 M**。
