# Runner 设计（`docs/runner-design.md`）

| 项 | 值 |
|---|---|
| 状态 | **Draft v1**（2026-10-01） |
| 用途 | 定义 `harness/` 的执行层：把方法卡 → 靶标 → 证据 → 判据 → 实测分，跑成一条可复算的链 |
| 对应操作 | `docs/technical-design.md` §3.2 的 **OP-12 `run_matrix`**（输入 `target_id` / `case_id[]` / `method_ids[]` / `n`；输出 `Batch`；**副作用：执行攻击，有靶标副作用**；**非幂等**）。配套 OP-13 查状态、OP-14 中止并回滚清场 |

| 依据 | `docs/` **D15**（实测结果纳入交付）· **D1**（文件为真相源）· `docs/benchmark-matrix.md` §7（依赖顺序） |

---

## 0. 一句话

> **Runner 不知道任何类别、也不知道任何靶标。** 它只认四个契约；八类的差异全部落在**类模块**里，靶标的差异全部落在**适配器**里。

**首跑目标是 T06 × AgentDojo**（唯一已论证的组合），但骨架按八类写——
因为第二个靶标、第二个类会立刻到来，而"先写专用再重构"在本项目已经发生过多次。

---

## 1. 为什么做成通用骨架而不是 T06 专用

`docs/benchmark-matrix.md` 实测：6 类有候选靶场。也就是说**第二个类很快就要上**。
若首跑写成 T06 专用，第二个类来时必须重构，而重构会动摇已跑出的数字的可比性。

**代价**：首跑要多写一层间接。**收益**：第二个类的接入成本≈写一个适配器。

> **反过来说清楚**：通用骨架**不等于**八类都能跑。`targets/agentdojo-workspace` 的实测覆盖率是 **20/186**——
> 只有 T06 的 20 张卡 `required_actions ⊆ 本靶标 tools`，其余 166 张在本靶标上记 `untested`。
> **骨架通用 ≠ 覆盖通用。**

---

## 2. Runner 只依赖五个契约

| 契约 | 文件 | Runner 用到什么 |
|---|---|---|
| **类模块** | `spec/method-script-interface.md`（冻结） | `spec_from_card(method_id)` · `build_plan(spec)` · `plan_grid(spec)` · `validate(spec)` · （可选扩展）`status_of(observables, spec)` |
| **靶标** | `spec/target-profile.schema.json` + `harness/protocol.py` 的 `TargetAdapter` | `tools()` · `caps()` · `design_dimensions()` · `reset()` · `inject()` · `run_task()` · `observe()` · `cleanup()` |
| **判据** | `judges/registry.json` + `harness/protocol.py` 的 `Judge` | `judge_id` · `judge(params, **obs) -> Verdict` · （可选扩展）`params_for(card)` |
| **评分** | `score/core.py` | `wilson` · `depth_from_layer` · `exp` · `impact` · `confidence` · `r_measured` |
| **副观测** | `harness/protocol.py` 的 `Observer` + `harness/observers.py` | `observer_id` · `observer(card, observations, request_text, payload_text)` |

**第五个契约是 2026-10-02 加的**（`docs/` **D16**）。它**不是**判据：
判据产出"成没成"（六态），副观测产出"成得怎么样"（连续诊断量），
**不进六态、不进 `R_m`、不进 `Prior_SR`**（R9：两把尺子不混排）。
`run_matrix(observers=...)` 默认为空；副观测抛异常不连坐判定。
详见 `docs/`。

**除此之外没有第六个。** 任何"runner 里需要知道 T06 是什么"的写法，都是设计错误。

---

## 3. 目录

```
harness/
├── protocol.py            TargetAdapter / Judge / Observer 三个协议 + 两个注册表
├── evidence.py            证据束（EvidenceBundle）的形状与采集纪律
├── store.py               runs/ 落盘（D1：文件为真相源）
├── runner.py              run_matrix 的通用骨架
└── adapters/
    └── agentdojo_workspace.py
```

---

## 4. 一次 run 的七个阶段（**六态在哪一步产生，是硬约束**）

| # | 阶段 | 产出 | 归属 |
|---|---|---|---|
| 1 | **读卡** | `MethodSpec` | —— |
| 2 | **适用性判定** | `required_actions ⊆ target.tools()`？ | **`untested`**（不适用时）。**不是 `fail`**——这是规则 17 在运行时的对应物 |
| 3 | **前置条件判定** | `preconditions ⊆ target.design_dimensions`？ | **`not_applicable`**（不满足时）。**不拉低覆盖率**（R4） |
| 4 | **清场 + 复位** | 靶标回到初始态 | 清不了 ⇒ 本 trial 记 `inconclusive`，**不记 fail** |
| 5 | **投放 + 执行** | 原始输出、靶标状态、回执 | —— |
| 6 | **判据** | `Verdict` ∈ {`pass`,`fail`,`inconclusive`,`not_applicable`} | **判据只出这四态** |
| 7 | **评分** | `R_m` + `C` + `[lo,hi]` + `source: measured` | `n` 不足以支撑比例时记 **`tested_no_number`** |

**六态的分工写死在这里**：
- `untested` / `not_applicable` / `tested_no_number` 由 **runner** 产出；
- `pass` / `fail` / `inconclusive` 由 **判据** 产出。

判据**不得**产出 `untested`——它拿不到"这个目标有没有这个工具"这一层信息。

---

## 5. 三条不可协商的纪律（都有对应的历史事故）

| # | 纪律 | 对应事故 |
|---|---|---|
| 1 | **`untested` ≠ `fail`**，`not_applicable` ≠ `untested` | `docs/judgment-discipline.md` R1–R4；规则 17 曾把 `untested` 报成 ERROR（2026-10-01 修） |
| 2 | **判据的输入里不得有"我方请求正文"能污染的量** | D1/D2：T08 报 9/9 泄露，泄露值却来自我方请求正文 |
| 3 | **每格必须带 `[lo, hi]` 与 `source`**，`n=3` 只给到 **4.38 上限** | R2 · `docs/benchmark-matrix.md` §5.1 |

---

## 6. 落盘格式（D1：文件为真相源）

```
runs/<batch_id>/
├── batch.json                       批次元数据：target_id / case_ids / method_ids / n / 四个哈希
├── <method_id>/
│   └── <target_id>/
│       ├── trial-0.json             单次 trial 的全部证据与判定
│       ├── trial-1.json
│       └── trial-2.json
└── summary.json                     逐格汇总（含六态计数与 R_m）
```

- `runs/` **已在 `.gitignore` 里**（运行产物不入库，但可重建）
- 单 trial 记录**必须自足**：只看这一个 JSON 就能复算出该格的 `R_m`
- **不得只存汇总**——汇总不可复算，这是 D1 存在的全部理由

---

## 7. 已知缺口（**跑之前必须知道**）

| # | 缺口 | 影响 |
|---|---|---|
| G-1 | **防御栈不可配置**：AgentDojo 的防御是固定实现，拿不到 9 臂 `leave_one_out` | `C` 因子的一半依据缺失 ⇒ 报告里必须写明"防御集固定" |
| G-2 | `cleanup_supported=false`（AgentDojo 无幂等 restore + 独立 cleanup reader） | 依赖清场的结论**只能记 `inconclusive`**（画像已如实填 false） |
| G-3 | **先验基线不存在**：`score/prior.py` 未产出 | 现在只能得到**孤立的 `R_m`**，**不是对账结果** |
| G-4 | **传递依赖未逐条 hash-pin** | "逐位可复算"对本靶标**尚未满足**（见 `requirements-target.txt`） |
| G-5 | **`required_actions` 无受控词表**（152 个动作名 / 141 个只在单类出现） | 阶段 2 的适用性判定**只对本靶标有效**，不可跨靶标推断 |

**G-3 最容易被忽略**：没有先验基线，跑出来的数字回答不了"我们的刻度准不准"——
而那正是实测分**唯一**的职责（instrument validation）。

---

## 7.1 实现期实测出的两条（**写进设计，免得后人重踩**）

### 7.1.1 本项目有**两套都叫 "layer" 的词汇表**

| 函数 | 认的词汇 | 含义 |
|---|---|---|
| `impact()` 的 `declared_layer` / `reached_layer` | **证据层**：`text` / `behavior` / `authorization` / `state` / `causal` | 判据**判到哪一层** |
| `depth_from_layer()` | **防御层**：`LAYER_ORDER` 的 9 个名字，或 `real_effect` / `no_observation` | 攻击**被拦在第几层** |

实现首日即踩：把证据层喂给 `depth_from_layer()` 会抛「未知防护层」。
**两者不可互换**，故 `Observations` 里单独立了 `deepest_defense_layer` 字段，
并在字段注释里写明这条区别。

### 7.1.2 G-1（防御栈不可配置）的**具体下游后果**

`depth` 是 `EXP` 五分量之一，而它需要"被拦在第几个防御层"。
AgentDojo 的防御是**固定实现**、不映射到本项目的 9 层 ⇒ **这个分量拿不到**。

⇒ runner 的处理是 **`tested_no_number` + `reason="depth_unavailable"`**，
**不是**拿四个分量硬凑一个 `R_m`。硬凑出来的分数不可解释，而"不可解释的分数"
比"没有分数"危险得多。

**这条把 G-1 从"登记的风险"变成了"已发生的、有代码落点的限制"。**

---

## 7.2 配对对照指标 `Adv̂`（2026-10-01 接入）

### 为什么

`docs/judgment-discipline.md` 的第一原则：**不得用自己的分验证自己的分。**
而 `R_m` 与 `Prior_SR` 共用 `impact()` / `exp()` 同一套函数形式 ⇒
拿 `R_m` 当效标只能验证"解析估的输入和实测的输入一致吗"，**验证不了模型本身**。

⇒ 实测通道改用**外部有出处的指标形式**：`Adv̂ = v_adv − v_ctrl`。
出处：**AgentSecBench（`arXiv:2605.26269`）定义 4**，原文
*"subtracts spontaneous emission on the paired control"*。

**不减对照就是把模型的自发行为算成方法的功劳。** 同型真实事故：
判据 **D2** —— T08 报 9/9 泄露，而独立探针 **7/7 未泄露**。

### 怎么做

**每个 trial 跑两臂**，共用同一段代码，**差异只在 `payload_for` 给出的载荷**：

```
run_matrix(payload_for=lambda card, plan, trial, arm: ...)   # arm ∈ {adversarial, control}
```

- 证据**两臂各存各的**（`trial-N.json` / `trial-N-control.json`）；
  配对关系靠 `(index, arm)` 复原，**不靠汇总**（D1：汇总不可复算）。
- 对照探针必须与对抗探针**同形**（同句式、同约束强度），只是语义良性。
  不同形就不是配对，`Adv̂` 会减掉一个不可比的东西。

### 一条口径变更（**重要**）

| | 旧口径 | 新口径（2026-10-01 起） |
|---|---|---|
| `six_state` 由什么决定 | `R_m` 算不算得出来 | **攻击成没成**（`v_adv`） |
| `depth` 拿不到时 | 整格 `tested_no_number` | 只影响 `R_m` 那一路，记入 `r_unavailable_reason` |

**为什么改**：设计规格:376` 把 "benchmark" 一词的解除条件绑在
「产出含 `source: measured` 标记的**分数**」上。旧口径下攻击明明成功、
格却是 `tested_no_number` ⇒ **这个词永远解不开**。新口径下格有状态、有指标，
`R_m` 的不可得性被单独记录——**两件事不再互相污染**。

### 三条由测试钉住的纪律

| # | 纪律 | 理由 |
|---|---|---|
| 1 | **`Adv̂ ≤ 0` 必须显式报警**："本格的『成功』不能归因于该方法" | 否则一个 `pass` 会静静地躺在一个零增益旁边 |
| 2 | **一臂给不出判定 ⇒ 整格 `inconclusive`** | 配对不成立时，另一臂的数字没有意义 |
| 3 | **任何 trial 不可判 ⇒ 整格不给率** | 曾在实现里写成"在可用子集上算率"，被测试抓出——那是 §5.2 的 **M1–M5 聚合掩盖**的重演 |

---

## 8. 本设计**不做**的事

1. **不做并发**（默认并发 = 1；并发 > 1 会降低逐位可复现性）。
2. **不做报告生成**（OP-22 是另一个模块；runner 只落 `runs/`）。
3. **不实现判据**（判据在 `judges/`；runner 只按 `judge_id` 分派）。
4. **不碰 `targets/`**（靶标画像由 OP-10 管；runner 只读）。

---

## 9. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| `runner-design-v1` | 2026-10-01 | 初版。四契约分层、七阶段与六态归属、落盘格式、五项已知缺口 |
| `runner-design-v1.1` | 2026-10-01 | 补 §7.1：两套 layer 词汇表不可互换；G-1 的具体下游后果 |
| `runner-design-v1.2` | 2026-10-01 | 补 §7.2：配对对照指标 `Adv̂`（AgentSecBench 定义 4）；**六态口径变更**——状态由攻击成败决定，`depth` 不可得只影响 `R_m` 那一路 |