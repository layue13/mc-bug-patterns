# 基准集：用真实修复提交测规则

问题：规则写出来了，但它们在真实代码上到底有没有用？这里用开源模组的**修复提交**回答：
对每个修复提交取修复前（`<sha>^`）和修复后（`<sha>`）两版被改动的 `.java` 文件，各跑一遍规则，比较命中数。

| 结论 | 含义 |
|---|---|
| `fixed-signal` | 某规则在修复前命中、修复后减少 → 规则确实指向了被修掉的东西（**唯一能当作"抓到真 bug"的证据**） |
| `persistent` | 修复前后命中数不变 → 规则与这次修复无关（可能是噪声，也可能是别处的隐患，需要人看） |
| `introduced` | 只在修复后命中 → 噪声 |
| `silent` | 两个版本都没有任何命中 → 这类真实 bug 目前**没有被任何规则覆盖** |

## 用法

```bash
scripts/fetch_benchmark_repos.sh ~/bench-repos          # 克隆 5 个仓库(各取最近 4000 个提交)，末行打印运行命令
python3 scripts/run_benchmark.py --repo mekanism=... --repo ae2=... ...   # 全量约 10 秒
# 结果: benchmark/out/REPORT.md, results.json
```

`cases.json` 只存提交引用（仓库、SHA、改动的文件名、提交信息首行），**不含第三方代码**。

## 样本如何选的（以及偏差）

- 在 5 个仓库（Mekanism、AE2、Create、Botania、Refined Storage）自 2021 年起的历史里，用同一组关键词过滤提交信息
  （`dupe/duplication/exploit/crash/bypass protection/void items/...`），且只含 ≤6 个非测试 `.java` 文件。共 186 条。
- 另有 1 条人工加入（`mekanism-b5d6066fa`，`source: manual`）：关键词漏掉了它，但它是 G1 的典型真例，并带 `expect`。
- **`split`**：`tuning` = 用来调规则的仓库（Mekanism/AE2/Create，数字偏乐观）；`holdout` = 调规则之后才加入、再未据其改规则的仓库（Botania/Refined Storage）。**看 holdout 的数字。**
- `auto_label` 只是按提交信息关键词的猜测，**不是**核实过的范式。
- 偏差：提交信息里没写"dupe/crash"的修复不在样本里；崩溃类（C?）占多数且大量是客户端渲染；只有开源、活跃维护的大模组。

## 局限

- 只衡量规则对"被改动的文件"的反应，不是整仓精确率；`persistent` 里的命中是否真是 bug，需人工读。
- 不能证明规则"抓到了同一个 bug"，只能说命中随修复一起消失。
- 提交的 SHA 固定，但各仓库当前分支的历史可能被改写；若 `parent revision unavailable`，加大 `DEPTH`。

结果与解读见 [`FINDINGS.md`](FINDINGS.md)，本次运行快照见 [`REPORT.md`](REPORT.md)。
