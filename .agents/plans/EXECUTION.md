# 执行队列（合并排程，live 状态；2026-07-08 建）

> 由 `README.md` 排程 + `2026-07-08_mtj_layout_structure.md` 前置口径修正合并而成的**唯一执行顺序清单**。每完成一项就地打勾并在 `../MEMORY.md` 记一行。规则：改 `article/*.md` 后等 watcher 重生 `.docx` 一起提交；数字改动必须以规范 run/入库脚本为准。

## 阶段 A（答辩前必做，当前窗口）

- [x] **A1 = T3-1 步骤 0**（2026-07-08 完成）：表 4.6 修正为规范 run 值——**两行**变动（sMTJ 7.90/12.73 J + stoch-ReRAM 448.40/453.22 J，指南 §7.1 原「仅 sMTJ 一行」的 diff 声明不完整已订正）；图 4.13 题注与 §4.5 正文（排名改「仅次于 STT-MRAM 与 FeRAM」、1.14×→1.22×、4.2×→3.9×）；[^nv_ranking] 重写并附旧占位值来历；图 4.13 经 deck 换图重导出（slide 13 blob 替换 + 纵横比修正 + dpi 419 裁剪）；guide/status.md 同步。规范 run 的 CSV 未入库（runs/ 整体 gitignored，见阻塞项登记的 guide 措辞问题）。⏳ 待 watcher 重生 chapter04.docx 后一并提交。
- [x] **A2 = MTJ 计划口径修正 #1**（2026-07-08 完成）：chapter04.md「约100 nm」改归属——标定器件临界尺寸改为约 80 nm（第二章口径），无沟道工艺以「(临界尺寸约100 nm)」括注保留在对照句中。
- [x] **A3 = T3-1 步骤 1–3**（2026-07-08 完成）：`experiments/22_energy_sensitivity.py`（18 参数、三档带宽、基线对规范 run 自校验、闭式反转点）。实测：p-bit/sMTJ 包络 **1.5–10.9×**（方向全程不变，宽端来自 5 pJ 锚点自身 ±3×；统筹报告预跑的 2.7–4.8× 系未扫锚点本身，已被实测取代）；sMTJ/STT 包络 **0.72–1.64×** 跨 1（反转点：e_int8_mac ×2.03、stt.read ×1.64；对 FeRAM：×1.78/×1.49）；带内共 19 处名次反转（reversal_boundaries.csv）。§4.5 增包络句 + [^energy_sens] 脚注（并列 6.4×/3.1× 两口径，同时闭环 R5 残余）。**待定**：龙卷风图 `figures/22_energy_sensitivity_tornado.png` 暂为仓库级证据，是否经 deck 收进正文/附录由用户定夺；runs/ 下两个 CSV 因 gitignore 未入库（脚本确定性可再生，另见 runs 入库任务芯片）。
- [ ] **A4 = T3-2**：EOT 自适应攻击审计（先修 `_eval_pgd` 口径不一致 + FULL_STACK no_grad 补丁，再跑攻击矩阵；GPU）。
- [ ] **A5 = T3-3**：真 IPC 正交化（metrics.py 规范 IPC + rank 上界自检 + 重跑 exp18 面板 (c)(d) + 图 5.6/正文联动）。
- [ ] **A6 = T3-4**：V_th 慢漂移压力测试与再校准配方（variation 层 OU/随机游走注入 + 节拍公式）。
- [ ] **A7 = MTJ 口径修正 #2**：[^hikstor_data] 数字以 IEDM 全文自查（**阻塞于用户**：需原文全文）；核不出则换锚 EDL 80 nm / Materials Futures sub-100 nm。

## 阶段 B（答辩前争取）

- [ ] **B1 = T1-1**：免复位马尔可夫采样（先做一天期前置检查：sigmoid(θ) 中段质量 + AP→P 双极性标定可用性，再决定投入深度）。
- [ ] **B2 = T1-3**：PBNN 原生 UQ（依赖 A1/A3 的能量口径收口）。
- [ ] **B3 = T2-1**：逐层采样预算分配。
- [ ] **B4 = MTJ L2a/L2c**：几何→保持 Δ 自洽闭环（十行函数）+ 偶极串扰界/场敏感度（可与 T3-4 合并 variation 注入实现）。

## 阶段 C（答辩后/期刊）

- [ ] T1-2 位翻转闭式认证界（窗口收窄，若 B 段进度快可提前）
- [ ] T1-4 电报储备池 ESP 认证
- [ ] T2-2 全温度自洽 · T2-3 计数式 RC 读出（窗口窄）
- [ ] T3-5 确定性重放列级共仿（先做 MTJ L1 的 2T 单元版图供其模板）
- [ ] MTJ L1 抽象 BEOL 版图（与 1.7 SA 布线同窗口）· L2b CD 设计窗（双 CD 候选先查新颖性）
- [ ] 跨仓库口径修正：ch2 D_elec 派生量说明、configs.py「β-IrMn」注释（并入 pending_vgsot_destale，随 VA 同步窗口）

## 阻塞项登记

- A7 需用户提供 IEDM 2024 全文自查页（或授权换锚）。
- 1.7 SA GUI 布线（解锁 1.8–1.10）需 GUI 会话。
- VA 同步窗口等 canonical vgsot-sim 验证通过（`../eda/VA_SYNC_RUNBOOK.md`）。
