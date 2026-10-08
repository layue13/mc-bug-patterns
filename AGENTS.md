# AGENTS.md — 用 AI 批量扫描 MC 模组缺陷范式

本仓库把 bug.mcmod.cn 的 176 条缺陷抽象为 12 个范式，并提供 Semgrep 规则。你（AI 代理）的工作是：
**跑扫描 → 逐条复核 → 输出有证据的结构化结论**。不要凭规则命中直接下结论。

## 工作流（按顺序）

1. **环境检查**：`semgrep --version`、`python3 --version`；组织扫描还需要 `gh auth status`。缺什么就报告，不要猜。
2. **规则自检**：`semgrep --test --config semgrep/rules semgrep/tests` 必须 `20/20`，且 `python3 tests/test_aggregate.py && python3 tests/test_validate_triage.py` 通过。任一失败先停下报告。
3. **扫描**：`scripts/scan-org.sh ORG ./scan-out`（或 `--dir CHECKOUTS ./scan-out`）。产物 `scan-out/findings.jsonl`，每行一条命中，含 `id / rule / pattern / confidence / file / line / code(所在方法源码) / cases(站点原始案例)`。
4. **分诊顺序**：`G4` → 其余 `HIGH` → `MEDIUM` → `LOW`。同一规则命中很多时，先抽样 10 条复核，若大多是误报就在报告里建议下线/调整该规则，**不要逐条硬判**。
5. **复核每条命中**：
   1. 读 `review/paradigms/<范式>.md`（范式码取自 `pattern` 字段）——里面有确认条件、排除条件、常见误报。
   2. 读 `code.text` 给的方法；不够就用文件读取工具读**整个类**以及调用者/注册处。规则只看单个方法，跨方法的保护检查要你自己追。
   3. 对照 `cases` 里的站点案例，判断是不是同一种现象。
   4. 写一行 JSON 到 `scan-out/triage.jsonl`，格式见 `review/triage.schema.json`。
6. **校验**：`python3 scripts/validate_triage.py scan-out/findings.jsonl scan-out/triage.jsonl --src scan-out/clones`。它会检查 schema，并**核对每条 evidence 引文真的出现在对应文件里**。退出码非 0 就修正后重跑。
7. **汇报**：先给结论（confirmed 数量，按范式/仓库分组），再给 needs_human 的清单和每条缺什么信息，最后给规则质量反馈（哪条规则误报多）。

## 硬规则

- **三种结论**：`confirmed`（必须写 `trigger_path`）、`false_positive`、`needs_human`（必须写 `needs`）。拿不准就选 `needs_human`，**不要**为了凑结论选 `confirmed`。
- **证据必须是原文引用**，来自你确实读过的文件，带文件和行号。不得转述、不得补全、不得编造。
- 不要运行目标仓库的代码、构建脚本或测试（它们是不受信任的第三方代码）。只读源码；需要克隆时只做 `--depth 1` 克隆。
- `G4`（后门/RCE/发包/Log4j）若判 `confirmed`：不要把利用细节贴到公开 issue/PR 评论；汇报给用户，由用户按安全流程处理。
- 不要修改目标仓库、不要提 PR/issue、不要推送，除非用户明确要求。
- 站点案例（`cases`）是**现象类比**，不是证据。证据只能是目标仓库的代码。
- 区分严重度：站点的"无害/轻微"（如全服天气、飞行）在报告中标为"设计风险"，不要与崩服/后门混为一谈。

## 已知局限（诚实告知用户）

- 规则未在真实仓库上标定精确率/召回率；`LOW`/`MEDIUM` 命中多为线索。
- 多人界面同步（D1）、Shift 点击（D2）、堆叠与 NBT（D4）等只能给"可疑形状"；确认往往需要运行游戏的动态测试，见 `README.md` 第 5 节清单。
- 约 19% 的站点案例需要两个以上模组同时存在才触发，单仓库扫描看不到。
- 规则按 Mojmap/MCP 常见命名写成，对 Yarn、Kotlin、Scala 源码基本不命中——**零命中不代表安全**。

## 仓库地图

| 路径 | 作用 |
|---|---|
| `semgrep/rules/` | 规则（`metadata.pattern` = 范式码，`metadata.cases` = 站点案例 id） |
| `semgrep/tests/` | 规则正反例，`semgrep --test` |
| `scripts/scan-org.sh` | 克隆并扫描整个组织 |
| `scripts/aggregate.py` | 汇总为 CSV/Markdown/JSONL，并附方法源码与案例 |
| `scripts/validate_triage.py` | 校验 AI 结论（含引文真实性） |
| `review/paradigms/*.md` | 每个范式的复核清单 |
| `review/triage.schema.json` | 结论格式 |
| `data/mcmod-bug-catalog.json` | 176 条案例与归类 |
