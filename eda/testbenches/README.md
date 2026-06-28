# `eda/testbenches/` — 电路测试台与回归

ngspice 测试台，以及对照 `smtj_pbnn_sim` Python 模型的双仿真器回归。除原理图导出外，命令均在本目录
下用 `python3` 运行；电路台需 ngspice + 编译好的 `smtj_sot.osdi`（见 `../SETUP_opensource.md`），
`.spiceinit` 已配置 `osdi smtj_sot.osdi`。

| 文件 | 作用 | 运行 |
|---|---|---|
| `gen_golden.py` | 由标定数据生成金标准 $$P_\mathrm{sw}(V)$$ | `python3 gen_golden.py` |
| `run_regression.py` | 编译 `.va` → ngspice DC 扫描 → 对金标准断言 | `python3 run_regression.py`（86 点，$$R^2=1.0$$） |
| `write_mc_harness.py` + `write_path.spice` | 写路径瞬态：能量、驱动开销、随机写 | `python3 write_mc_harness.py` |
| `psw_mc_harness.py` | 种子化伯努利随机写复现 Sigmoid | `python3 psw_mc_harness.py` |
| `diff_column.py` | 差分列读出、popcount 最低有效位电流 | `python3 diff_column.py` |
| `sar_capdac_energy.py` | 列共享 SAR 电容阵列各位开关能量 | `python3 sar_capdac_energy.py` |
| `rc_isoenergy.py` / `rc_readout_noise.py` | 储备池等能量前沿 / 读出噪声极限 | `python3 …` |
| `adaptive_t.py` | 置信度序贯早退采样 | `python3 adaptive_t.py` |
| `telegraph_lowbarrier.py` / `trinity_barrier.py` | 低势垒随机电报噪声 / 势垒时分复用包络 | `python3 …` |
| `sa_tran_tb.spice` / `write_tran_tb.spice` + `plot_waveforms.py` | StrongARM 再生与写脉冲瞬态波形 | ngspice → `python plot_waveforms.py` |
| `plot_pipeline.py` | 工作模式流水线时序图 | `python plot_pipeline.py` |

随机蒙特卡洛均记录种子以保证可复现。各 `*_summary.json` 为对应脚本的结果摘要。回归断言与
`tests/test_calibration.py`、`tests/test_telegraph.py` 的契约一致。
