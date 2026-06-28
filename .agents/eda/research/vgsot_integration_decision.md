# vgsot-sim 整合决策 (回答 ②)

仓库：`git@github.com:JinChengZ18/vgsot-sim.git`（2026-06 检视）。

## 它到底是什么

| 物件 | 是什么 | 对 P1 的价值 |
|---|---|---|
| **`src/vgsot_sim/`** | **你自己的** Python 物理模型：完整宏自旋 LLG（球坐标 Euler + Cayley 矢量积分器）+ VCMA + STT/SOT + FDT 热噪声 + 自加热 RC + TMR(V)，校准到实验，复现 §2.3.3 Sigmoid、NB V_th(t_w)、§2.3.5 变异预算 | **物理 ground-truth**（上游）|
| **`scripts/02_pdk/sotmodel.va`** | **第三方 Hikstor 40nm SOT-MRAM PDK**（(c) Zhejiang Hikstor，xiexuejie@hikstor.com）。Spectre 语法、**确定性电流阈值翻转**、参数不同（Rsot=800/Rp=11k/TMR=1.2/电流驱动 Iop=800µA） | 仅**结构参考**（3 端 p/q/n、KCL 注入、@cross 脉宽计时）|
| `article/chapter02.md` + `scripts/05_.../raw/` | 第 2 章器件原稿 + 实测 Psw 原始数据 | 校准数据源 |

**关键判断：`vgsot-sim` 是 Python 的（你说得对）；仓库里那个 `.va` 不是你的模型，而是 Hikstor 厂商 PDK——既不是随机 p-bit（无 Néel-Brown/伯努利）、又是别的器件、还是 Spectre 专用、且有版权，不能并入 MIT 仓库。**

## 决策一：Verilog-A——新写，不port LLG、不复用 Hikstor

- ❌ **不把完整 LLG 转写成 Verilog-A**：没必要。`smtj_pbnn_sim` 的紧凑 Sigmoid/NB 模型已经是 LLG 校准后的抽象；电路仿真要的就是这个紧凑层。
- ❌ **不复用 Hikstor `.va`**：版权 + 确定性 + 别的器件 + Spectre 专用。只把它的**三端拓扑与 @cross 脉宽计时**当写法参考（用于 P2 的 Spectre 路，若将来有许可证）。
- ✅ **新写一个 MIT 紧凑模型**：已完成 → [`../../../eda/models/smtj_sot.va`](../../../eda/models/smtj_sot.va)。复现校准 Sigmoid/τ(V)/⟨s⟩，OpenVAF 安全（随机性在 harness）。本次 Python 金标准对实测 46 点 **R²=0.9919**、写能量 0.783 pJ，均 PASS。

## 决策二：submodule——把 vgsot-sim 挂在 eda/ 下做 ground-truth，不并入核心 sim

三层器件表示及其关系：

```
vgsot_sim (Python 全 LLG, 上游真值)
        │  校准/抽象
        ▼
smtj_pbnn_sim/device (紧凑 Sigmoid+NB+telegraph, 仿真器运行时)   ← 回归主目标 (errata N1)
        │  编码
        ▼
eda/models/smtj_sot.va (Verilog-A, 电路仿真)                     ← P1 产物
```

- **建议**：将 `vgsot-sim` 作为 **git submodule 挂在 `eda/vendor/vgsot-sim`**，仅作 **LLG 交叉验证参考**（例如 P1/P7 可选地让 `.va`/紧凑模型再对一遍 vgsot 的 LLG τ(V)、V_th(t_w)）。
- **不并入 `smtj_pbnn_sim` 核心**：核心已有自己的校准 `device/` 层（与 vgsot 同源、同 §2.3 数据），并入会重复且增加耦合。保持单向引用即可。
- ⚠️ **版权隔离**：submodule 引入后，`scripts/02_pdk/sotmodel.va`（Hikstor）**不得**复制进本 MIT 仓库或论文交付物；如需在论文里引用其行为，注明厂商来源与 NDA 状态。

> **已执行（2026-06-26）**：`git submodule add git@github.com:JinChengZ18/vgsot-sim.git eda/vendor/vgsot-sim`
> （at v0.1.1-11-gf35123c，`.gitmodules` 已落仓）。可选后续：`eda/interface/vgsot_crosscheck.py`
> 让 LLG τ(V)/V_th 与紧凑模型 / `.va` 三方对账（P7 用）。
> ⚠️ 版权隔离：submodule 内含 Hikstor 专有 `scripts/02_pdk/sotmodel.va`，**不得**复制进本 MIT 仓库或论文交付物。

## 小结

P1 不被"模型是 Python"卡住——紧凑层才是电路要的，已新写成 MIT `.va` 并经金标准验证。
vgsot-sim 的最佳位置是 `eda/vendor/` 下的 LLG 真值参考（submodule），而非并入核心仿真器；
其中的 Hikstor PDK 文件须做版权隔离。
