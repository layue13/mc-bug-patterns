# 基准集发现（2026-10-08，5 仓库 186 个修复提交）

> 规则版本：本分支提交时的 `semgrep/rules/mc-java.yml`。数字可由 `scripts/run_benchmark.py` 复现。

## 一、规则在真实修复上的表现

| split | 案例数 | 有 fixed-signal | 只有 persistent | 完全 silent |
|---|---:|---:|---:|---:|
| tuning（Mekanism/AE2/Create，已据此调过规则） | 139 | 2 | 12 | 125 |
| **holdout**（Botania/Refined Storage，未据此改规则） | 47 | **0** | 7 | 40 |

- 全部 fixed-signal 只有 2 例，且都在 tuning 集：`mekanism-b5d6066fa`（G1，纸板箱缺保护检查，**我人工加入并据此改了规则，所以是自证**）、`mekanism-e667947ed`（C2，服务端加载了客户端类）。
- **holdout 上 0/47。** 目前规则对真实修复的覆盖率在统计上接近零，不能指望它们"批量发现已知类型的 bug"。
- 关键词标 `D?`（复制）的 37 条里，按提交标题我读下来约 27 条是真实的复制修复（其余是 "dedupe" 性能优化、功能提交等）；**这 27 条规则一条都没抓到**。

## 二、基准集帮我发现并修掉的规则缺陷

1. G1 的世界修改 API 列表漏了 `setBlockAndUpdate`（真实代码最常用）。
2. G1 把 `!isClientSide` 当成"保护检查"放行 → 恰好过滤了真 bug。`isClientSide` 只区分端，不是权限。
3. G1 父类匹配漏了 `BlockMekanism` 这类不以 `Block` 结尾的名字。
4. G1 把 `canAccess` 这类**模组自带安全系统**的辅助方法当成领地保护；领地插件靠事件与 `mayInteract`。
5. G1 对 BlockEntity 修改自身位置（设激活/朝向/能量等级）大量误报 → 加了"自身位置"排除。
6. C2 只按路径排除客户端代码，没识别 `@OnlyIn`/`@EventBusSubscriber` → 17 个持续命中降到 5。

修复后 `semgrep --test` 仍 20/20，并新增了对应的测试用例（用我自己写的释义，不拷贝第三方代码）。

## 三、真实复制 bug 长什么样 → 规则缺口

抽读了若干修复 diff，真实 bug 多是**逻辑形状**，而不是"方法忽略 simulate 参数"：

| 真实例子（修复提交） | 形状 | 现有规则 |
|---|---|---|
| Refined Storage `a47dc16`（Interface 复制）：`ItemStack remainder = stack;` → `copyStackWithSize(stack, size)` | **别名**：把参数赋给局部变量后当作可变结果，没拷贝 | 无 |
| AE2 `c6aa4aceb`（终端流体复制） | **SIMULATE 与 MODULATE 的数量不一致**：用 A 步骤的模拟结果去 MODULATE 另一个量 | 无（`mc-d5` 只查"是否用了参数"） |
| Botania `08b1ee8e0`（矿车魔力池） | 同一对象在两条销毁路径上各掉落一次 | 无 |
| AE2 `540c06358`（ME 箱子开着菜单时拆 cell） | 菜单持有的存储对象在其生命周期内被替换（D1，API 契约） | `mc-d1-*` 过粗，未触发 |
| Mekanism `7279fc0ba`（Ejector） | 局部变量与字段混用，句柄没真正设置 | 无 |

## 四、对结论的影响（对用户的坦白）

1. 先前文档里"规则可批量发现这类漏洞"只在**很窄的范围**成立：G4（后门/Log4j）、C2（客户端类进服务端）、G1（缺保护检查）的少数形状。对**复制类**，当前规则基本无效。
2. AI 复核层（`AGENTS.md`）不能弥补规则的低召回：AI 只会复核规则命中的那部分。要提升召回，需要要么扩规则，要么让 AI 直接读代码审查（成本高、需要它自己的基准）。
3. 下一步最有性价比的是**从真实修复 diff 里挖新规则**，例如：
   - "ItemStack/FluidStack 别名"：`T r = param;` 后对 `r` 做 `shrink/grow/setCount/setAmount` 或直接返回（有拷贝则不报）。
   - "SIMULATE 与 MODULATE 的参数来源不同"。
   - 每条新规则都要在 holdout 上先测，再并入。
4. 目前 `persistent` 命中的精确率：我抽读了 tuning 集 G1 的 20 处命中，约 4 处值得人看（挖矿机、Nixie 管上色、背包拾取等）；这是**对被调过的文件的小样本人工判断**，不是精确率估计。
