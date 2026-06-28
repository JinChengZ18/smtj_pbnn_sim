# `.agents/` — 维护 Agent 协作中心 (cross-agent coordination hub)

> 本目录是**所有维护 agent（Claude / Codex / 其它）对本仓库"项目理解 + 协作管理"文件的唯一归口**。
> 新接手的 agent：先读本文件 → 再跳到对应领域的「续传点」(§1)。
> 这里放 agent 协作/编排/环境元信息，以及 EDA 的**内部规划/状态/调研记录**（`.agents/eda/` —— STATUS、ROADMAP、PLAN_execution、OPEN_SOURCE_FEASIBILITY、MANUAL_SETUP_NEEDED、research/，原在 `eda/` 主目录，现统一归此）。
> **用户向内容**（论文交付稿 `article/`、复现文档 `docs/` 与各 `README.md`）留在各自目录。

## 0. 一分钟定位 (where am I)
- **仓库** `smtj_pbnn_sim` —— sMTJ 概率位神经网络 (PBNN) + 蓄水池计算 (RC) 的**标定行为级仿真器**，
  外加正在推进的 **EDA 晶体管级验证/创新层**（`eda/`）。毕业设计（学位论文）配套代码。
- **仓库根**（当前，纯英文路径）：`D:\Documents\Graduation Project-2026\04PBNNSim\smtj_pbnn_sim`
- **用户**：中文母语，论文阶段；要研究深度、并希望结论以「论文贡献」来表述。
- **Git**：remote `git@github.com:JinChengZ18/smtj_pbnn_sim.git`，master 为主。

## 1. 续传点 (authoritative resume points — 勿在本文件复制其内容)
| 领域 | 单一真相源 | 说明 |
|---|---|---|
| EDA 晶体管级验证/创新 | `.agents/eda/STATUS.md` | **长时程任务唯一续传点**（当前状态 / 决策账本 D1–D8 / 验证账本 / 各阶段 DoD）。读它，再读 `.agents/eda/ROADMAP.md`。 |
| 论文交付稿 | `article/` | 只放交付内容；**禁止**写本地引用 / TODO / 勘误指针（见 §2）。 |
| 勘误总表 | `docs/errata.md` | E1/E2 已修；R1–R7 待 EDA 验证；N1–N3 注记。 |
| Claude-CLI 私有跨会话记忆 | `<user>\.claude\projects\…-smtj-pbnn-sim\memory\` | Claude Code 自动记忆（**仓库外**，按 cwd 派生）。本目录是**仓库内**的跨 agent 通道；二者各自维护、内容保持一致。 |

## 2. 多 agent 协作约定 (conventions — 违反会互相踩踏)
- **并行 worktree**：用户同时跑多个 Claude worktree（`.claude/worktrees/*`），改动相互独立。
- **同步靠 merge 进 master**：用户在 **MAIN checkout 的 `master` 上直接提交**。你的分支同步方式 =
  **把分支 merge 进 master**（master 一旦分叉，FF-only 会失败）；小心保留用户的提交。
  直接 push 到 `master` 被 auto-mode 安全闸拦截 → 工作流：本地 master 提交 →
  `git push origin master:<feature-branch>` → 用户 FF/merge。
- **`article/` 是交付稿**：保持干净，本地草稿 / 文件引用 / 勘误指针不要写进去。
- **`.md`→`.docx` 自动 watcher**：用户本地 watcher 在每次 `.md` 编辑后约 4–5 分钟自动重生
  `article/*.docx`；**总是把自动重生的 `.docx` 与 `.md` 一起提交**，不要当成"不是我的改动"排除。
- **EDA 诚实支柱**（写论文时必须守）：RNG 留在 Python harness；报**比值**不报绝对值（sky130 130nm 偏悲观）；
  Magic R-PEX 粗 → IR 仅给**量级**；端到端能量基线 **6.95 pJ/bit**；MTJ-in-GDS = 抽象黑盒 + 不可制造声明。

## 3. 环境关键事实 (environment facts)
- **WSL 发行版名 = `Ubuntu-24.04-EDA`**（不是 plain `Ubuntu-24.04`）。已装：ngspice-46、
  OpenVAF-Reloaded(20260616)、sky130A(`/opt/pdk/sky130A`)、KLayout、**Magic 8.3.668**。
- **Magic 升级已完成并验证**（2026-06-26）：`/usr/local/bin/magic` = 8.3.668 ≥ 8.3.306，
  sky130A techfile 正常加载 ⇒ Magic/TCL **routing → LVS → PEX** 路线**已解锁**
  （Magic extract→ext2spice 已实跑通，9 器件 + 寄生 C 提取成功）。详见 `.agents/eda/MANUAL_SETUP_NEEDED.md`。
- **LVS netgen 注意**：`/usr/bin/netgen`(apt) 是**网格生成器**(Schoeberl/Vienna)，**不是** LVS netgen
  (Tim Edwards)。做 LVS 前先确认装了正确的 netgen（open_pdks 版）。
- **Windows 工具路径**（ngspice/openvaf）记于 `eda/tools.local.json`（gitignored，逐机重建）。
- **WSL 跑 sky130 工具**：用 **ASCII ext4 build dir** `/home/lenovo/smtj_eda_build`
  （见 `eda/hero/layout/run_drc.sh` / `run_pex.sh` 模式）。现在保留它的**唯一原因**是 `/tmp` tmpfs
  空闲清空；CJK 路径破坏 `-rd input` 的老原因已随 2026-06-26 迁移到英文路径而消失。

## 4. 迁移记录 & 当前「可立刻开工」方向
- **路径迁移（2026-06-26）已完成**：旧 CJK 路径 `D:\Documents\毕业设计-2026年5月10日\04PBNN仿真`
  → 新英文路径（见 §0）。worktree 已重连新路径（`git worktree list` 无 prunable）。
  详细 append-only 日志见 [`MEMORY.md`](MEMORY.md)。
- **Phase 0 工具链网关已原生达成**（本会话）：Magic 8.3.668 + netgen 1.5.321 (`~/eda/netgen/bin`)
  + ngspice/OpenVAF/sky130A/KLayout 全齐，IIC-OSIC-TOOLS Docker 改为可选。
- **本会话已落地的真实提取数**：写线 IR-drop（R3，`eda/extraction/writeline/`：N=256→16.5%·776Ω，
  li1 灾难）、SA 版后寄生/能量（R1/R5，`eda/hero/sa_postlayout.py`：35.25fF，23–74fJ/决策）、
  SA 器件集 9→11 + DRC 0 违例 + netgen LVS 工具链打通。
- **可分步执行清单（带 DoD + 状态）= [`eda/PLAN_execution.md`](eda/PLAN_execution.md)**（创新主线
  A0/A1+A2 Hero/A3 第二篇拆成步骤 + "立即可开工 5 动作"）。**SA 的 routing→全 LVS 是 GUI 收尾**
  （`eda/hero/layout/LVS_GUI_CHECKLIST.md`）。续传真相源仍是 `.agents/eda/STATUS.md`。
