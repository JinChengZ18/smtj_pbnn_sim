# EDA 协同设计路线图 (可落实为 agentic 工作流)

本路线图按**阶段 (phase)** 组织，每个阶段对应一个可由 agentic 工作流执行的单元：
有明确输入、可并行的子步骤、产出物、以及**验证门 (gate)**。会话 todo (TaskCreate) 与本文件同步——
本文件是持久副本 (todo 可能不跨会话保留)。

依赖关系 (拓扑序)：`P0 → P1 → {P2 ∥ P3 ∥ P7a} → {P4 (需P3) ∥ P5 (需P1+版图)} → P6 (汇总) ；P7 全程并行`

图例：⚙️=配置/决策 🔬=仿真 🧪=回归/验证门 🔌=接口回灌 📝=回填论文/勘误

---

## P0 — 基础与决策 (无 EDA，1 周)  ⚙️
**目标**：把后续一切的前提钉死。
- [ ] 确认大学 Cadence/Synopsys 席位 + Europractice/foundry-PDK 访问；论文算教学/研究用途。
- [ ] **据访问结果二选一**：商用路线 (Virtuoso+Spectre+ASAP7/FreePDK45) 或 开源路线 (ngspice≥43 + OpenVAF-Reloaded + sky130/IHP SG13G2)。
- [ ] 钉死工具链版本 (写入本目录决策备忘)。
- [ ] **定 Verilog-A 回归目标工作点** = 自动拟合值 $V_\mathrm{th}=895.8$ mV、$V_T=23.4$ mV、$\beta_s=42.7$ V⁻¹ (勘误 N1)。
- [ ] 确定 MTJ 模型基底：fork ARM s-LLGS (加 SOT 分支) 或 Rajpoot NGSPICE (索取代码)。

**产出**：`eda/` 决策备忘 (工具链 + PDK + 回归目标 + 模型基底)。**门**：访问与版本确认。

---

## P1 — Verilog-A SOT-sMTJ 器件模型 (keystone, 2–3 周)  🔬🧪
**目标**：一个种子可复现、能重现你 Ch.2.3 标定的 Verilog-A 器件——解锁后续一切。
并行子步骤：
- [ ] **(模型)** 三端宏：SOT 写分支 ($R_\mathrm{SOT}=776$)、MTJ 读分支 ($R_P=4.9$k/$R_\mathrm{AP}=9.8$k)、
      事件驱动随机切换 (概率写：`@(cross/timer)` 触发 seeded `$rdist`；telegraph：精确两态传播子按 dt 步进)。
- [ ] **(回归)** 对照 Python：重放 46 点 Sigmoid (R²≥0.99、还原 $V_\mathrm{th}/V_T$)、$\tau(V)$ 自相关 vs `relaxation_time()`、
      $\langle s\rangle=\tanh$ vs `stationary_mean()`、$\int V\!\cdot\!I=0.78$ pJ。镜像 `tests/test_calibration.py`/`test_telegraph.py`。
- [ ] **(协议)** 种子 + 版本钉死的 MC 协议文档。

**产出**：`models/smtj_sot.va`、`testbenches/regression_*`。**门 🧪**：回归全过、种子可复现。

---

## P2 — 写路径 (单次最高价值仿真, 2–3 周；P1 后)  🔬📝
**目标**：验证 (b)(d) 并测可行性。
- [ ] 5 比特 DAC + SOT 电流驱动 + 0.75ns 脉冲发生器 + 随机写测试台。
- [ ] 瞬态：0.75ns 脉冲在 776Ω 上是否真能建立 (slew + 线 RC)。
- [ ] 含驱动/DAC 开销的**真实写能量** (预期 > 0.78 pJ) → 勘误 R4。
- [ ] 多种子 → 复现 P_sw(V_wr) Sigmoid。

**产出**：写能量 (器件级 + 端到端) 数；可行性结论。**门 📝**：更新勘误 R1/R4。

---

## P3 — 差分读 + 灵敏放大 (2–3 周；P1 后，可与 P2 并行)  🔬📝
**目标**：把 (a) 从代数断言变成实测；测 (c)。
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

## P6 — 接口：回灌 `smtj_pbnn_sim` (2 周；汇总 P2/P4(/P5))  🔌📝
**目标**：把提取数值变成仿真器可读配置——「替换不成熟内容」落地。
- [ ] `extraction/` 把列在 (θ,T,corner) 上特征化成 LUT/能量-面积表。
- [ ] `interface/` Python 胶水：由提取值构造 `TechParams`/重写 `per_mac_energy`/替换 `estimate_ir_drop`；单向注入，仿真器不依赖 `eda/`。
- [ ] 用提取数重跑 MNIST PPA；(可选) wreal AMS 把一小撮 MAC 从 PyTorch 流过提取网表 → 「一个 MNIST 数字穿过提取的 sMTJ 列」杀手图。

**产出**：由 EDA 数驱动的 PPA；接口模块。**门 📝**：勘误 R1/R2 标记为已解决并回填论文。

---

## P7 — 储池 (RC) 路径 (并行轨, 3–4 周)  🔬📝
**目标**：验证/修正 (e)，文档化三位一体限制。
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
