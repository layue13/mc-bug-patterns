# Benchmark report

186 cases evaluated, 0 skipped.

- cases where some rule shows a **fixed-signal**: 2 (1%)
- cases where **no rule fires at all** (silent): 165 (88%)

## By split

`tuning` repos were used to adjust the rules (numbers are optimistic); `holdout` repos were not.

| split | cases | fixed-signal | persistent only | silent |
|---|---:|---:|---:|---:|
| holdout | 47 | 0 | 7 | 40 |
| tuning | 139 | 2 | 12 | 125 |

## By message-keyword label (unverified)

| label | cases | with fixed-signal |
|---|---:|---:|
| ? | 5 | 0 |
| C? | 141 | 1 |
| D? | 37 | 0 |
| G? | 3 | 1 |

## By rule (cases in which the rule fired in a changed file)

| rule | fixed-signal | persistent | introduced |
|---|---:|---:|---:|
| mc-g1-world-edit-without-protection-check | 1 | 10 | 1 |
| mc-c2-client-class-in-common-code | 1 | 7 | 1 |
| mc-d5-fluid-handler-ignores-action | 0 | 3 | 0 |
| mc-c1-nullable-entity-hit | 0 | 1 | 0 |
| mc-d2-manual-quickmove | 0 | 1 | 0 |
| mc-d3-handler-ignores-simulate | 0 | 1 | 0 |

## Cases with a fixed-signal

- `mekanism-b5d6066fa` 2021-10-25 — Make cardboard boxes obey spawn protection and also check the block break event ...
    - mc-g1-world-edit-without-protection-check in BlockCardboardBox.java: 1 → 0
    - mc-g1-world-edit-without-protection-check in ItemBlockCardboardBox.java: 1 → 0
- `mekanism-e667947ed` 2021-05-26 — Actually fix some modules causing the server to crash due to client side only code being loaded
    - mc-c2-client-class-in-common-code in ModuleGeigerUnit.java: 1 → 0
    - mc-c2-client-class-in-common-code in ModuleDosimeterUnit.java: 1 → 0
