# `eda/hero/` — 读出与写通路电路设计（sky130）

本目录是 sMTJ-PBNN 外围的 sky130 电路设计：斜率匹配概率位读出（跨阻 + StrongARM 灵敏放大）、
电压型电阻串写-DAC 与 IR 感知写预畸变，以及列共享读出。`schematics/` 导出期刊级原理图，
`layout/` 给出脚本化版图。电路脚本需在 WSL 中调用 ngspice（含 sky130 模型）；精度耦合脚本在
Windows/GPU 上调用 `smtj_pbnn_sim`。

## 脚本与运行

| 文件 | 作用 | 运行 |
|---|---|---|
| `strongarm_sa_core.spice` | StrongARM 锁存比较器（11 器件，LVS 参考） | ngspice / Netgen（WSL） |
| `run_offset_mc.py` | 输入折合失调蒙特卡洛（Pelgrom 阈值失配）对 $$V_T$$ | `python3`（WSL） |
| `sa_postlayout.py` | 提取器件电容后的判决能量 | `python3`（WSL） |
| `run_readout_frontend.py` | 斜率匹配读出前端：popcount 电流 → 跨阻 → StrongARM，在环验证 | `python3`（WSL，ngspice） |
| `readout_mapping.py` | 把失调（mV）经跨阻折算到 popcount 域与精度 | `python3` |
| `pareto_offset_cancellation.py` | 精度跌幅对剩余失调的帕累托（含失调消除选项） | `python3` |
| `run_write_dac.py` | 电压型电阻串写-DAC：单调性、最低有效位、量程 | `python3`（WSL，ngspice） |
| `ir_aware_writedac.py` | IR 感知逐行写预畸变（远端写概率补偿） | `python3` |
| `write_dac_trim.py` | 摊销式逐列阈值微调 | `python3` |
| `layout/gen_sa_layout.py` | 脚本化 sky130 SA 器件版图 → GDS | KLayout（WSL） |
| `schematics/build_schematics.sh` | 由 Xschem 导出原理图（图 6–10） | WSL（见 `schematics/`） |

## 主要结果（sky130；失配系数为该工艺量级假设，故以比值报告）

- StrongARM 在 sky130 工作：差分 +20 mV 输入即判决至轨。
- 平凡比较器输入折合失调 $$\sigma_\mathrm{off}=9.2\,\mathrm{mV}=0.39\,V_T$$（120 次蒙特卡洛）。
- 斜率匹配读出：扇入 1024、$$V_\mathrm{in}=0.6\,\mathrm V$$ 下 $$R_\mathrm{TI}=613\,\Omega$$，
  在环提取 $$\sigma_\mathrm{pc}\approx2.5$$ 个 popcount，落在精度曲线膝点之下 → 该扇入下平凡比较器即足够。
- 失调-面积协同：增大输入对面积按 $$1/\sqrt{\text{area}}$$ 降低失调；低压宽扇入区才需自调零。

电路设计的器件级原理图与说明见 `schematics/`；其在论文中的定位与对比见
[`../../article/supplement_eda_codesign.md`](../../article/supplement_eda_codesign.md)。
