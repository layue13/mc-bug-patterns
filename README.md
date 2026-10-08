# MC 模组缺陷范式（来源：MC百科 bug.mcmod.cn）+ 组织级扫描

目标：把 [bug.mcmod.cn](https://bug.mcmod.cn/)（MC百科「MOD特性警示」）里收录的缺陷抽象成可复用的**范式**，
并配套一套 Semgrep 规则 + 批量脚本，在组织仓库里大规模找"同类问题"。

> 状态说明（诚实版）
> - ✅ 已验证：176 条全部抓取并逐条阅读、人工归类；19 条 Semgrep 规则 + 1 条构建文件规则通过 `semgrep --test`（20/20，正反例）；扫描脚本在夹具仓库上端到端跑通。
> - ⚠️ 未验证：规则在**真实模组仓库上的精确率/召回率**——本会话只能访问 `layue13/layue13`（没有 Java 代码），没有拿真实代码测过。
>   `confidence: LOW/MEDIUM` 的规则请当作"人工复核线索"，不要当作缺陷结论。

## 1. 数据与方法

| 项 | 内容 |
|---|---|
| 抓取 | 首页列表 176 条 → 逐条抓详情页（`/item/<id>.html`），提取：涉及模组、版本、威胁等级、复现描述、解决方案 |
| 归类 | 人工读完每条后给**唯一主类**（互斥，不用关键词自动归类——试过，33 条未命中且多标签重叠，不可信） |
| 数据集 | [`data/mcmod-bug-catalog.json`](data/mcmod-bug-catalog.json)（元数据 + 截断摘要 + 归类，附原文链接；原站内容 CC BY-NC-SA 3.0） |
| 局限 | 站点样本偏 **1.7.10 / 1.12.2 老模组**（Forge 老 API，IC2/Thaumcraft/BC 时代），且是**玩家与服主视角**的现象描述，不是代码级根因。范式里的"代码形状"是我从现象反推的**假设**，需要用真实代码验证 |

威胁等级分布：致命 24 / 严重 71 / 轻微 37 / 无害 21 / 客户端 16 / 暂无 7。

## 2. 范式总表（176 条，主类互斥）

| 码 | 范式 | 条数 | 严重度构成 | 静态可查？ |
|---|---|---:|---|---|
| **D1** | 多人/并发 GUI 状态不同步 → 复制 | 17 | 严重14 轻微3 | 部分（线索级） |
| **D2** | Shift 点击 / 槽位索引 / 热键搬运 → 复制 | 7 | 严重7 | 部分（线索级） |
| **D3** | 加工·合成·自动化传输 不消耗/多倍产出 | 19 | 严重8 轻微10 | **是**（simulate 参数） |
| **D4** | 堆叠·NBT·物品/实体状态携带 → 复制 | 20 | 严重15 轻微5 | 部分 |
| **D5** | 流体与容量边界 → 复制 | 5 | 严重2 轻微3 | **是**（FluidAction） |
| **G1** | 无视领地/权限/禁用方块 | 28 | 严重19 轻微8 | **是**（缺保护检查） |
| **G2** | 免费区块常加载 | 5 | 轻微5 | **是** |
| **G3** | 全局世界状态与平衡破坏（天气/时间/飞行） | 17 | 无害15 | **是** |
| **G4** | 后门 / RCE / 越权命令 / 未校验发包 | 4 | 致命4 | **是** |
| **C1** | 服务端崩溃·卡顿·资源失控 | 27 | 致命19 严重4 暂无3 | 部分 |
| **C2** | 客户端崩溃·渲染·跨模组兼容 | 15 | 客户端13 | 部分 |
| O | 其他/非安全功能缺陷 | 12 | — | 否 |

合计"复制类 D1–D5" 68 条（39%），"绕过类 G1–G4" 54 条（31%），"崩溃类 C1–C2" 42 条（24%）。
**致命(24)里 C1 占 19 条**——崩服比复制更致命；**严重(71)里复制类占 46 条**。

## 3. 各范式：成因 → 代码形状 → 规则 → 修法

### D1 多人/并发 GUI 状态不同步 → 复制（17）
- 典型：玩家 A 开着界面，玩家 B 拆/传送/搬走容器（末影接口、传送器、箱子宝宝、末影之手）；或"开界面→切换到另一个容器→取物"（私人箱子、信件）；或**不关界面直接下线**，物品回档重现（采花袋、饰品盒、无底袋）。
- 根因：同一份物品状态有两个可写视图（界面槽位 vs 方块实体/物品 NBT），写回时机只有"关界面"，且 `stillValid` 不校验底层对象是否还是同一个。
- 代码形状：`stillValid()` 恒 `true`；物品背包类 Menu 只在 `removed()/onContainerClosed()` 里写 NBT；槽位按下标绑定到物品而不是物品 UUID。
- 规则：`mc-d1-menu-always-valid`(MEDIUM)、`mc-d1-item-backed-menu-saves-on-close-only`(LOW)
- 修法：槽位变化即时落盘；`stillValid` 校验方块/物品身份与距离；玩家登出时强制 `closeContainer`；打开界面时对物品加"锁"标记。
- **静态不可证**：必须靠下面第 5 节的并发用例动态验证。

### D2 Shift 点击 / 槽位索引 / 热键搬运 → 复制（7）
- 典型：化学清洗机/液体储罐"背包第 31 格 / 9–27 格 + Shift 点击翻倍"，Dank Storage 右键+Q，/dev/null 数字键。
- 根因：`quickMoveStack` 手写槽位区间，与玩家背包槽位重叠；移动后源槽未 `shrink`。
- 规则：`mc-d2-manual-quickmove`(LOW)——手写 `set/putStack/setItem` 且未使用 `moveItemStackTo/mergeItemStack`。
- 修法：用原版 `moveItemStackTo`；对每个 Menu 做"遍历全部槽位 Shift 点击，物品总数必须守恒"的测试。

### D3 加工·合成·自动化传输 不消耗/多倍产出（19）
- 典型：传送带+漏斗（机械动力）、自动合成器空输入持续产出、扩展合成台漏斗无消耗、物流整理机/提取管道 64 倍、拆解台（拆合成同物品）、木炭堆 1 换 4。
- 根因：`insertItem/extractItem` 忽略 `simulate`，管道先模拟再执行就多给；输入不足时仍匹配配方；合成剩余物(`getRemainingItems`)处理错。
- 规则：**`mc-d3-handler-ignores-simulate`(HIGH)**——方法签名带 `simulate` 但方法体从未使用。
- 修法：模拟与执行走同一代码路径，仅在最后一步判断 `simulate`；对每个 `IItemHandler` 写"模拟前后状态不变 + 执行后守恒"的单测。

### D4 堆叠·NBT·物品/实体状态携带 → 复制（20）
- 典型：背包类物品可叠加，叠在一起共享库存 NBT（旅行手袋）；灵魂绑定背包+墓碑双份；灵魂瓶捕捉带箱子的驴/骡；生物球装 BOSS；黑洞存储器 NBT 可被改写；拔刀剑合成无上限叠加。
- 根因：带库存的物品没有 `maxStackSize = 1`；实体/物品序列化时把容器内容一起复制；跨模组事件顺序（死亡掉落 vs 墓碑 vs 绑定诅咒）。
- 规则：`mc-d4-inventory-item-stackable`(LOW)、`mc-d4-entity-save-to-item`(LOW)
- 修法：库存物品 `stacksTo(1)`；实体入物品时剔除容器 NBT 并设 BOSS 黑名单；死亡掉落路径统一走一个入口。

### D5 流体与容量边界 → 复制（5）
- 典型：液体漏斗不消耗地灌入、装瓶机 >1001mB 无限流体、木桶 >61 单位翻倍、流体球低价换高价。
- 根因：`fill/drain` 忽略 `FluidAction/doFill`；容量比较用错单位；容器 NBT 保留旧流体。
- 规则：**`mc-d5-fluid-handler-ignores-action`(HIGH)**
- 修法：同 D3，另加"边界值 0 / 容量 / 容量+1"属性测试。

### G1 无视领地/权限/禁用方块（28，最大单类）
- 典型：采矿机/高级采矿机/镭射枪/约束之镐/洛基之戒/拉普达碎片/建筑之杖/天使方块/搬运类物品/爆炸物，无视领地破坏或放置；包裹/手掌花绕过"服务器禁止放置的方块"。
- 根因：领地/保护类插件通常监听 `BlockEvent.BreakEvent/PlaceEvent` 或 `mayInteract`。模组直接 `setBlock/destroyBlock/removeBlock` **绕开了这个统一检查点**。
- 规则：`mc-g1-world-edit-without-protection-check`(MEDIUM)、`mc-g1-unbounded-explosion-power`(MEDIUM)
- 修法：所有改世界的路径先 `mayInteract`/发 `BreakEvent`；使用 `FakePlayer` 时带上真实所有者；爆炸威力加配置上限。

### G2 免费区块常加载（5）
- 末影采石场/岩浆泵/采石场/发射控制器/数字采矿机锚点：摆下即生效、无能耗。
- 规则：`mc-g2-forced-chunk-loading`(MEDIUM)。修法：配置开关 + 能耗 + 玩家在线条件。

### G3 全局世界状态与平衡破坏（17，几乎全是"无害"）
- 一个物品改全服天气/时间（晴天娃娃、日晷、造雨机、被褥坐一下全服时间 3 秒 1 小时），或无条件创造飞行（神龙胸甲、天使指环）。
- 规则：`mc-g3-global-world-state-from-gameplay`、`mc-g3-creative-like-flight`（均 INFO 级）。修法：加配置项/权限节点，默认对非 OP 关闭。

### G4 后门 / RCE / 越权命令 / 未校验发包（4，全部"致命"）
- Log4j 远程执行；魔改版"耀月"给硬编码玩家名 OP；Create 蓝图 NBT 夹带命令方块；作弊端发包（神秘研究全解锁/刷物品/数据溢出崩服，因服务端未校验包内容）。
- 规则：`mc-g4-op-grant-or-shell`(HIGH, ERROR)、`mc-g4-packet-handler-unchecked-position`(MEDIUM)、`mc-g4-vulnerable-log4j`(HIGH, ERROR，扫 gradle/pom/properties)
- 修法：服务端永远不信任客户端；包处理器校验距离/已加载/菜单；用户上传的结构 NBT 过滤命令方块与物品；依赖审计。
- **这是组织级扫描优先级最高的一类**：条数最少，但全是致命且一眼可查。

### C1 服务端崩溃·卡顿·资源失控（27，致命的主力）
- 子型：① 缺配方/空值 NPE（Gaia 机器放无配方物品；钓鱼竿钩到实体）② 无上限放大（信标增强器：1 个 0.5 秒 → 5 个半小时 lag；毁灭新星威力随火药指数增长；树苗长出十几区块大的树；温泉器无限溢水）③ 高频红石重入（Translocation Matrix 栈溢出）④ 数据膨胀（引路线卷 playerdata NBT 超 40kB 掉线且无法上线）⑤ 多方块/活塞搬运破坏状态（搬运 Mek 多方块、活塞推 ME 驱动器）。
- 规则：`mc-c1-recipe-optional-get`(HIGH)、`mc-c1-nullable-entity-hit`(LOW)、`mc-c1-redstone-reentrant-action`(LOW)
- 修法：所有 tick 内的循环/递归/范围加上限与配置；配方查询用 `ifPresent`；用 `scheduleTick` 去抖；NBT 增长加硬上限。

### C2 客户端崩溃·渲染·跨模组兼容（15）
- 彩蛋日期分支（4/1、12/9）崩溃、Blur 导致别的 GUI 消失、TOP+Crafting++ 同装崩、公共代码引用客户端类。
- 规则：`mc-c2-client-class-in-common-code`(MEDIUM)、`mc-c2-date-triggered-branch`(MEDIUM)
- 修法：注入 `Clock` 并用伪造日期测试；客户端类隔离到 `client` 包 + `DistExecutor`。

## 4. 跨范式的四条元规律（比单条规则更值得审查）

1. **同一状态两份副本 → 写回时机不一致**（D1/D2/D4/D5）：界面槽位 vs 方块实体、模拟 vs 执行、物品 NBT vs 世界实体。审查要点：每个"读-改-写"之间有没有别的玩家/管道/事件能插进来。
2. **绕开统一检查点**（G1/G3/G4）：保护插件、权限、网络校验都挂在事件/入口上，直接调底层 API 就绕过。审查要点：grep 底层写世界 API，看同一方法里有没有检查点调用。
3. **无上限放大器**（C1/G1/G2）：数量×系数、递归、范围、NBT 增长，没有 `min/clamp`。审查要点：任何随玩家输入线性或指数增长的量，是否有配置上限。
4. **跨模组契约**（集中在 D3/D4/D1）：33/176（19%）的条目在「涉及模组」里列了 2 个以上模组（AE2×Quark 活塞、Carry On×Mekanism、IC2 锡×热力膨胀桶），这是下限——单模组条目里也有依赖原版/通用 API 契约的。单仓库静态扫描**看不到**，需要在整合包层面做组合测试。

## 5. 使用

```bash
pip install semgrep            # 已在会话中用 1.180.0 验证
# 0) 规则自测
semgrep --test --config mc-bug-patterns/semgrep/rules mc-bug-patterns/semgrep/tests

# 1) 扫整个组织（需要 gh 已登录；默认跳过归档仓库与 fork）
mc-bug-patterns/scripts/scan-org.sh YOUR_ORG ./scan-out
#   JOBS=8 REPO_FILTER='mod|craft' INCLUDE_FORKS=1 可调

# 2) 已经 clone 好的一批仓库
mc-bug-patterns/scripts/scan-org.sh --dir ~/checkouts ./scan-out
```

输出：`scan-out/findings.csv`（repo / rule / 范式 / 置信度 / 文件:行 / 对应 mcmod 条目 id）、`scan-out/SUMMARY.md`（按范式、规则、仓库汇总）。
`cases` 字段对应 `data/mcmod-bug-catalog.json` 的条目 `id`，可直接回查原始现象。

**建议的分诊顺序**：先看 `HIGH`（G4 / D3 / D5 / C1 配方）→ `MEDIUM`（G1 / G2 / G3 / C2）→ 最后才看 `LOW`。
误报用 `// nosemgrep: <rule-id>` 就地压制并写明理由。

### 静态扫描覆盖不到的：动态用例清单（建议做成 GameTest / 集成测试）

| 范式 | 用例 |
|---|---|
| D1 | 玩家 A 开界面放入物品 → 玩家 B 拆除/传送/杀死载体 → A 取物；A 开界面后直接断线，重登检查物品 |
| D1 | 开界面后在同一 tick 切换到另一个同类容器再取物 |
| D2 | 对每个 Menu 的每个槽位做 Shift 点击，断言物品总数守恒；快捷键(数字键/Q/Ctrl+Q) 同理 |
| D3/D5 | 漏斗/管道/传送带连接每个 `IItemHandler/IFluidHandler`，运行 N tick 断言输入=输出+残留 |
| D4 | 叠加 2+ 个库存物品并放入物品；灵魂绑定+墓碑+死亡不掉落三组合 |
| G1 | 用 `FakePlayer`+保护事件取消，验证每个改世界的物品/机器都被拦住 |
| C1 | 空输入槽 + 燃料、对每种实体/掉落物使用每个工具、高频红石拉杆压测 |
| C2 | 伪造系统日期跑 4/1、12/9 等节日；专用服务器 classload 冒烟 |

## 5.5 让 AI 批量复核

扫描结果可交给 AI 逐条复核，入口是 [`AGENTS.md`](AGENTS.md)：

```
scan-org.sh → findings.jsonl（命中 + 所在方法源码 + 站点案例）
   → AI 按 review/paradigms/<范式>.md 逐条判断 → triage.jsonl
   → scripts/validate_triage.py（schema + 引文必须真实存在于文件）
```

- 三种结论：`confirmed`（需触发路径）/ `false_positive` / `needs_human`（需说明缺什么）。
- 校验器能挡住"编造证据"，**不能**证明结论正确；`confirmed` 仍建议人工抽查。
- 11 份范式清单、结论格式和提示词模板见 [`review/`](review/)。

## 6. 已知局限与下一步

- 规则基于 Mojmap/MCP 常见命名写成，**对 Yarn/Fabric、Kotlin、Scala 源码基本不命中**；1.7.10 老写法只覆盖了一部分。
- Semgrep 无跨文件/跨模组数据流，D1/D4 的规则只能给"可疑形状"。
- 下一步建议：先拿组织里 5–10 个已知出过 bug 的仓库试跑，人工标注命中，统计每条规则的精确率，再据此调 `confidence` 或下线噪声规则。
- 站点的 176 条是"已被玩家发现并核实"的样本，存在幸存者偏差；范式代表"人们已经踩过的坑"，不是缺陷的完整空间。

## 目录

```
mc-bug-patterns/
├── README.md                      # 本文档
├── data/mcmod-bug-catalog.json    # 176 条元数据 + 人工归类
├── semgrep/rules/mc-java.yml      # 19 条 Java 规则
├── semgrep/rules/mc-build.yml     # 依赖/构建文件规则 (Log4j)
├── semgrep/tests/                 # 规则正反例（semgrep --test）
├── scripts/{scan-org.sh,aggregate.py,validate_triage.py}
├── review/                        # AI 复核：范式清单 + 结论 schema + 提示词
├── tests/                         # 聚合与校验脚本的单测
└── AGENTS.md                      # AI 代理工作流与硬规则
```
