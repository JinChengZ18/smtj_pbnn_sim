# `eda/hero/layout/` — StrongARM 灵敏放大版图 → GDS

StrongARM 比较器的 sky130 器件版图与提取流程。

| 文件 | 作用 |
|---|---|
| `gen_sa_layout.py` | KLayout-Python 生成器：以带保护环的 sky130 PCell（`nmos18`/`pmos18`）实例化 StrongARM 的 11 个晶体管（对照 `../strongarm_sa_core.spice`），展平并写出 GDS |
| `sa_devices.gds` | 输出 GDS（顶层单元 `strongarm_sa_devs`，23.1×18.7 µm，11 器件，sky130 图层） |
| `run_drc.sh` | sky130 DRC（`sky130A_mr.drc`）；器件级 0 违例 |
| `run_pex.sh` | Magic 寄生提取（`gds read → extract → ext2spice`）；器件级 35.25 fF |
| `LVS_GUI_CHECKLIST.md` | 互连 / LVS 的逐网连接表与步骤 |

运行（WSL）：

```bash
klayout -b -r gen_sa_layout.py     # 生成 sa_devices.gds
bash run_drc.sh                     # DRC（0 违例）
bash run_pex.sh                     # 寄生提取（35.25 fF）
```

DRC/PEX 在一个持久化 ext4 构建目录中运行（WSL 的 `/tmp` 在分发空闲停机时会被清空），报告写入该目录。
器件以 1.5 µm 间距加保护环，故器件级 0 违例；加入互连布线后再做布线 DRC 与 Netgen LVS（LVS 用 Tim
Edwards 的 netgen，而非 apt 的网格生成器 netgen）。
