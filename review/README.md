# AI 复核

`scripts/scan-org.sh` 产出 `findings.jsonl` 后，由 AI 逐条复核。完整工作流见仓库根目录的 [`AGENTS.md`](../AGENTS.md)。

## 一条 findings.jsonl 的样子

```json
{
  "id": "30f174086e",
  "repo": "some-mod",
  "rule": "mc-d3-handler-ignores-simulate",
  "pattern": "D3",
  "confidence": "HIGH",
  "file": "/abs/path/some-mod/src/main/java/.../MyHandler.java",
  "line": 42,
  "message": "IItemHandler.insertItem/extractItem 没有使用 simulate 参数 ...",
  "code": {"start": 40, "end": 55, "text": "   40 | public ItemStack insertItem(...) {\n   42>| ..."},
  "cases": [{"id": 2, "name": "传送带 (Mechanical Belt)", "level": "严重", "url": "https://bug.mcmod.cn/item/....html", "summary": "..."}]
}
```

`code.text` 是命中位置所在方法的源码（`>` 标记命中行，最多 120 行；定位失败时回退为前后 30 行）。
这是**启发式**提取，类声明、字段、调用者不在其中——需要时请读完整文件。

## 一条 triage.jsonl 的样子

```json
{"finding_id": "30f174086e", "verdict": "confirmed", "confidence": "high",
 "evidence": [{"file": "/abs/.../MyHandler.java", "line": 42, "quote": "this.items[slot] = stack;"}],
 "reasoning": "D3 清单第1条：方法在 simulate=true 时同样写入库存，管道先模拟会造成多给。",
 "trigger_path": "漏斗(simulate=true) 询问 → 库存被改 → 随后 simulate=false 再写一次 → 物品翻倍",
 "suggested_fix": "仅在 !simulate 时写入 this.items[slot]。"}
```

字段约束见 [`triage.schema.json`](triage.schema.json)；用 `scripts/validate_triage.py` 校验（会核对引文真实存在）。

## 复核清单

每个范式一份，在 [`paradigms/`](paradigms/)：判定目标 → 必读代码 → 确认条件 → 排除条件（常见误报）→ 需要人工的情形 → 修法 → 对应站点案例。

## 提示词模板（给不具备 AGENTS.md 自动加载的 AI 工具）

> 你在复核 `scan-out/findings.jsonl` 中 id 为 `<ID>` 的一条静态扫描命中。
> 1. 读 `review/paradigms/<pattern>.md`，严格按"确认条件/排除条件"判断。
> 2. 读命中方法所在的整个类，以及调用者或注册处，必要时跨文件追踪保护检查。
> 3. 只输出一行符合 `review/triage.schema.json` 的 JSON。`evidence.quote` 必须逐字来自你读过的文件。
> 4. 拿不准用 `needs_human` 并写明缺什么；不要为了给出结论而选 `confirmed`。
> 5. 不要运行目标仓库的任何代码。

## 校验器防什么

LLM 复核最常见的失败是**编造证据**。`validate_triage.py` 会拒绝：引文在文件里找不到、`confirmed` 缺少触发路径、`needs_human` 缺少说明、重复判定、未知 id。
它**不能**证明结论正确——只能证明结论有真实代码支撑。
