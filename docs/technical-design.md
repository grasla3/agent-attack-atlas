# 技术设计文档

| 项 | 值 |
|---|---|
| 文档标识 | `technical-design-v1` |
| 状态 | **草案 —— 依赖 `docs/technical-design.md` 的选型，该文件尚未冻结** |

| 最后修改 | 2026-09-29 |

> **本文的空值规则**
> - 一切**数字**（阈值、数量、超时、并发、版本号、精度）一律写作 `<待人工确认>`；
> - 一切**选型结论**（框架、库、协议、存储形态）一律写作 `[待确认]`；
> - 一切**已由 设计规格 定死的事实**照实写出，并标出处章节。
> - **不得**用估计值填空。占位符本身就是验收项：冻结时须逐项清零。

---

## 0. 本文范围与不做什么

**范围**：目录分层、全局数据模型、接口契约、模块依赖、前端页面与组件。

**不做**：
- 不复述 设计规格 的功能需求与 DoD；
- 不定义算法细节（评分公式、先验公式、判据规则以 `spec/*.md` 为准）；
- 不做选型（以 `docs/technical-design.md` 为准）；
- 不写实现代码。

**依赖关系**：设计规格 → `docs/technical-design.md` → **本文** → 实现。

---

## 1. 项目目录分层结构

### 1.1 设计原则

| # | 原则 | 理由 |
|---|---|---|
| **D1** | **按"开/闭源边界"分层**，不按技术类型分层 | 设计规格 §2.2.1 要求框架层开源、实例层闭源；同层不得跨边界 |
| **D2** | **依赖单向向下**：`spec` → `methods/judges/score` → `report` → `apps` | 防止评分逻辑被 UI 反向污染 |
| **D3** | **`spec/` 是唯一真值源**，代码只消费 | 设计规格 F3：常数表单点引用，无内联硬编码 |
| **D4** | **`harness/` 是复用层的薄壳**，不含业务逻辑 | 设计规格 §7.2 复用边界 |
| **D5** | **每个目录必须有 `README.md`**（哪怕三行） | 设计规格 §7.3 DoD |

### 1.2 目录树与职责

> 标注：`[开源]` / `[闭源]` 对应 设计规格 §2.2.1 的六层边界。

```
<repo-root>/
├── README.md                     [开源] 首屏四问：这是什么 / 谁该用 / 怎么跑 / 不做什么
├── LICENSE  SECURITY.md  CONTRIBUTING.md  CHANGELOG.md  CITATION.cff
├── Makefile                      [开源] 唯一入口命令集（见 §4.4）
│
├── spec/                         [开源] 规范层：全部契约与常数的唯一真值源，不含可执行逻辑
│   ├── README.md                     本目录各规范的职责与冻结状态一览
│   ├── scoring.md                    评分规范：常数表、分数定义、汇总口径
│   ├── prior.md                      先验规范：Prior_I / Prior_EXP 公式、因子出处、区间方法
│   ├── judge.md                      判据规范：判据层定义、效度三级、复用边界
│   ├── glossary.md                   术语表（唯一化，禁同义词并存）
│   ├── taxonomy.yaml                 三轴分类坐标（风险域 / 攻击面 / 传播范围）
│   ├── negative-assertion-patterns.txt  负向断言检索模式表（R18）
│   ├── reused-components.json        复用件登记：name/source_url/version/sha256/license（C6）
│   ├── external-anchors.json         外部锚点登记：含 not_self_built:true
│   ├── method-card.schema.json       方法卡契约（26 必填 / 37 属性 / 44 校验规则）
│   ├── report-header.schema.json     报告头 13 字段
│   ├── judge-registry.schema.json    判据注册表 5 字段
│   ├── scenario-manifest.schema.json 类别清单（含 min_methods / allow_text_fallback）
│   ├── target-profile.schema.json    目标画像（Kim 7 维 × 3 档 + 工程属性）
│   └── judge-regression.md           判据回归断言集
│
├── methods/                      [开源] 方法层：240 张方法卡（每类 30，允许跨类重合）
│   ├── README.md                     卡的写法与分量级出处要求（硬规矩 E/F）
│   ├── T01/manifest.json + *.yaml    T01 类别清单 + 该类别的方法卡
│   ├── T02/ … T08/                   同上
│   └── _generated/                   批量校验与计数的产物（可重建，不进版本控制）
│
├── judges/                       [开源] 判据层：注册表 + 可执行实现（含复用件的 pin 版本）
│   ├── README.md                     判据的注册方式与确定性要求
│   ├── registry.json                 判据注册表（5 字段/条）
│   ├── deterministic/                确定性判据实现
│   └── adapted/                      对复用判据的适配层（**薄**，不得修改复用件语义）
│
├── score/                        [开源] 评分层：纯函数式，无随机数/时间戳/无序遍历（C2）
│   ├── README.md                     函数清单与不变量
│   ├── measured.py                   实测分 R_m
│   ├── prior.py                      先验评级 Prior_SR（含区间）
│   ├── stats.py                      Wilson / bootstrap / 秩相关（唯一的统计实现）
│   └── constants.py                  **只做读取** spec/scoring.md §1 常数表，不内联任何值
│
│   ├── README.md                     复用边界声明与"不重写"清单
│
├── targets/                      [混合] 目标层：接口规范开源，实例按 §2.2.1 分界
│   ├── README.md                     目标接入方式与开闭源说明
│   ├── manifest.json             [开源] 目标集清单
│   ├── agentdojo/                [开源] 参考目标（`pip` 依赖，不 vendor）
│   ├── t3-domain-twin/           [闭源] 自建参考靶标（防护层可开关，支撑 11 臂消融）
│
├── calibration/                  [闭源] 校准电池的档位产物（含 target 绑定）
├── report/                       [开源] 报告生成：JSON + Markdown + 图
│   ├── README.md                     产物清单与生成命令
│   ├── render_json.py                机器可读报告
│   ├── render_md.py                  人可读报告
│   └── plots.py                      两张热图 + 一张分布图
│
├── judge_regression/             [开源] 判据回归断言的可执行实现（含正反向用例）
├── validation/                   [开源] 验证链：预注册、外部锚点对账、逐分量诊断
│   ├── README.md                     四步链的执行方式
│   ├── prereg.py                     预注册文件的生成与哈希
│   └── reconcile.py                  逐分量对账（Prior_I vs I；Prior_EXP vs EXP）
│
├── tools/                        [开源] 批量与运维脚本
│   ├── verify_coverage.py            覆盖率与类容量校验
│   ├── count_identity.py             双计数（240 实例 / 去重方法数 N）
│   ├── scan_negative_assertions.py   负向断言检索（R18）
│   └── verify_dod_count.py           设计规格 DoD 计数复算
│
├── apps/                         [开源] 应用层：唯一允许依赖下层全部模块的层
│   ├── README.md                     形态说明（取决于 技术栈 决策）
│   ├── cli/                          CLI 入口（**必做**，四旅程均可纯 CLI 完成）
│   └── web/                          [待确认] 前端（形态未定，见 §5）
│
├── tests/                        [开源] 测试
│   ├── unit/                         纯函数与常数的单测
│   ├── regression/                   判据 19 条 + 评分回归用例
│   └── e2e/                          端到端：离线一键跑通
│
├── docs/                         [开源] 文档层（非规范，可自由增补）
│   ├── README.md                     文档索引
│   ├── lit-landscape-v1.md           文献与生态定位（已产出）
│   ├── docs/technical-design.md                 技术栈（未冻结）
│   ├── technical-design.md           本文件
│   ├── method-capacity-audit.md      方法容量盘点（R19，未产出）
│   ├── category-taxonomy.md          8 类划分原则与谓词（未产出）
│   ├── identity-card.md              双计数说明（未产出）
│   ├── preregistration.md            预注册（未产出）
│   ├── validation-report.md          验证报告（未产出）
│   ├── narrative-guardrails.md       可主张/禁主张清单（未产出）
│   ├── external-anchors.md           外部锚点说明（未产出）
│   ├── judge-failure-taxonomy.md     判据失效分类学（未产出）
│   ├── benchmark-comparison.md       对标表（未产出）
│   ├── evidence-discipline.md        证据纪律（未产出）
│   └── `ROADMAP.md`                 未完成项登记（未产出）
│
└── results/                      [开源] 实测台账与逐试验证据
    ├── README.md                     必读清单与阅读顺序
    ├── 00-mission.md                 任务边界与交付物
    ├── 01-domain-and-literature.md   领域、文献轴线、外部锚点
    ├── 02-scoring-and-judge.md       评分框架与判据规范摘要
    ├── 03-disciplines.md             纪律、禁令、已知失效模式
    ├── 04-category-workbook.md       单类别作业模板
    └── 05-facts-and-citations.md     已知事实与出处速查
```

### 1.3 层间依赖规则（**CI 可断言**）

```
apps  →  report / validation / tools / score / judges / harness / spec
report → score / spec
validation → score / judges / targets / spec
score → spec（只读 constants）
judges → spec / harness
methods → spec（仅 schema 校验时）
targets → harness / spec
spec → （无依赖，最底层）
```

**禁止**：`spec` 依赖任何代码；`score` 依赖 `report` 或 `apps`；`harness` 依赖 `score`；`[开源]` 目录依赖 `[闭源]` 目录。

---

## 2. 全局数据模型

### 2.1 实体总览与外键关系

```
Category (8)
   ▲ case_id
   │
MethodCard (240) ──variant_of──▶ MethodCard (自引用)
   │  └─negative_control.method_id──▶ MethodCard (自引用)
   │
   ├──▶ Trial (N × n)   ◀──target_id── TargetProfile (N)
   ├──▶ CellResult      ◀──target_id── TargetProfile
   └──▶ PriorRating     ◀──target_id── TargetProfile（可空）

Judgement ──judge_id──▶ Judge ──reused_component_ref──▶ ReusedComponent
CellResult ──judge_id──▶ Judge
Trial ──judge_id──▶ Judge

ReportHeader ──target_id──▶ TargetProfile
ReportHeader ──batch_id──▶ Batch
Batch ──positive_control_method_id──▶ MethodCard

ValidationRun ──anchor_ref──▶ ExternalAnchor
Preregistration ──(无外键，被 ValidationRun 引用)──▶ ValidationRun

CalibrationProfile ──target_id──▶ TargetProfile
```

**基数**：

| 关系 | 基数 |
|---|---|
| Category → MethodCard | 1 : `<待人工确认>`（目标 30，允许跨类重合） |
| MethodCard → Trial | 1 : n |
| MethodCard × TargetProfile → CellResult | 多对多，一格一条 |
| MethodCard → PriorRating | 1 : 1（每方法一条，或按目标分条 —— `[待确认]`） |
| Batch → ReportHeader | 1 : 1 |
| ExternalAnchor → ValidationRun | 1 : N |

### 2.2 `Category`（攻击类别）

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `case_id` | string | **PK**，枚举 `T01`–`T08` | 类别标识 |
| `name` | string | 必填 | 类别名 |
| `division_principle` | string | 必填 | 本类的划分依据（一句话） |
| `predicate` | string | 必填 | **区域谓词**：判定某方法属本类的可执行条件（硬规矩 D/E） |
| `covered_impact_classes` | string[] | 必填，枚举 `A`–`F` | 本类覆盖的后果类别 |
| `min_methods` | integer | 必填，`<待人工确认>` | 类内方法数下限 |
| `allow_text_fallback` | boolean | 必填，缺省 `false` | 是否接受文本层兜底 |
| `anchor_methods` | string[] | 必填 | 该类锚点方法 id 列表，每类 ≤ `<待人工确认>` |
| `mechanisms_shortfall_rationale` | string\|null | 未达 `min_methods` 时必填 | 不足理由 |
| `purpose` | string | 必填 | 类别的用途说明 |

### 2.3 `MethodCard`（方法卡）

<!-- schema-authority: spec/method-card.schema.json -->
> 字段全集见 `spec/method-card.schema.json`。此处只列**建模必需**与**本轮新增**字段。
>
> **⚠️ 本节与 schema 曾冲突过一次**：本表引入了 `provenance_components`/`provenance_kind`/`composition_of`
> 三个 schema 里没有的字段，而本节又声明「字段全集见 schema」——两个工件互相指认对方为权威。
> 现由 Gate 0 的 `card_contract_sync` 机械校验：**本节出现的任何 snake_case 字段名都必须能在
> 上面那行 schema 里找到**，找不到即构建失败。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `method_id` | string | **PK**，pattern `^T0[1-8]\..+` | 类别内编号 |
| `case_id` | string | **FK → Category.case_id** | 所属类别 |
| `mechanism_ref` | string | 必填，pattern `^(ATK-[A-Z]+-[0-9]{2}\|S_L[0-9]+_[a-z_]+\|EXT-[A-Za-z0-9_-]+)$` | 机制出处 |
| **`provenance_components`** | object | **本轮新增，必填** | 分量级出处（硬规矩 E） |
| ├ `mechanism` | `{ref, source}` | 必填 | 机制出处 |
| ├ `vector` | `{ref, source}` | 必填 | 通道出处（Kim 2026） |
| ├ `technique` | `{ref, source}` | 必填 | 手法类出处 |
| └ `transform` | `{ref, source}` | 可空 | 变换出处 |
| **`provenance_kind`** | enum | **本轮新增**，`interpolation` \| `composition` \| `ext` | 三档之一 |
| **`composition_of`** | string[] | `provenance_kind == composition` 时必填 | 跨文献组合的出处列表（硬规矩 F） |
| `variant_of` | string\|null | **FK → MethodCard.method_id** | 非空则不计入方法数 |
| `dimensions` | object | ≥2 维时报告须出逐维表 | 正交维度档位 |
| `trigger_path` | object | 必填 | 触发路径（支撑三联数） |
| `design_class` | enum | 必填 | 对照设计类别 |
| `judge` | object | 必填 | 见 §2.4 |
| `negative_control` | object | 必填 | `{method_id: FK → MethodCard}` |
| `preconditions` | object | 必填 | **落在 Kim 7 维上**（维度 → 最低档位） |
| `execution` | object | 必填 | `mode: declarative \| script_hook`；`script_hook` 时 `script` 必填 |
| `target_consequence` | string[] | 可空，默认 `[]` | D 系列标签，**不参与评分** |
| `source_grade` | enum | 必填 | `S`/`A`/`B`/`C`/`—` |
| `numeric_evidence` | enum | 必填 | `原表`/`摘要`/`无`（**与 `source_grade` 严格分列**） |
| `supersedes` | string[] | 可空 | 被本卡取代的旧卡 id |

### 2.4 `Judge`（判据，`MethodCard` 内嵌 + 注册表）

<!-- schema-authority: spec/judge-registry.schema.json -->

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `judge_id` | string | **PK** | 判据标识 |
| `deterministic` | boolean | 必填 | 是否确定性实现 |
| `report_dependent` | boolean | 必填 | 是否依赖被测方自述 |
| `params_schema` | object | 必填 | 参数 schema |
| `evidence_layer_default` | enum | 必填，`text`\|`behavior`\|`authorization`\|`state`\|`causal` | 默认证据层 |
| `reused_component_ref` | string\|null | **FK → ReusedComponent.name** | 非空表示复用外部判据 |
| `JUDGE_DETERMINISM` | number | 由 `deterministic` + `report_dependent` 派生；**取值表在 `spec/scoring.md` §1** | **禁止在代码中内联** |

### 2.5 `TargetProfile`（目标画像）

<!-- schema-authority: spec/target-profile.schema.json -->

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `target_id` | string | **PK** | 目标标识 |
| `display_name` | string | 必填 | 可读名 |
| `design_dimensions` | object | 必填 | 7 键，每键取值枚举 `{1,2,3}`：`input_trust` / `access_sensitivity` / `workflow` / `action` / `memory` / `tool` / `user_interface` |
| `defense_stack` | object\|null | 参考靶标必填 | 9 层开关配置 |
| `receipt_supported` | boolean | 必填 | 是否支持请求绑定回执 |
| `cleanup_supported` | boolean | 必填 | 是否支持幂等 restore + 独立 reader |
| `model` | string | 必填 | 模型标识 |
| `agent_scaffold` | string\|null | 纯 LLM 为 null | Agent 框架标识 |
| `deployment` | enum | 必填，`local` \| `remote_authorized` | 部署形态 |
| `provenance` | enum | 必填，`self_built` \| `public_weights` \| `authorized_env` | 来源 |
| `reproducibility_note` | string | 必填 | 如何复现 |

### 2.6 `Trial`（一次执行）

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `trial_id` | string | **PK** | 试验标识 |
| `method_id` | string | **FK → MethodCard** | |
| `target_id` | string | **FK → TargetProfile** | |
| `judge_id` | string | **FK → Judge** | |
| `seed` | integer | 必填 | 靶标回放种子 |
| `started_at` / `completed_at` | datetime | 必填 | ISO-8601 带时区 |
| `outcome` | enum | 必填 | `<待人工确认>`：与判据六态对齐 |
| `reached_layer` | enum | 必填 | `text`\|`behavior`\|`authorization`\|`state`\|`causal` |
| `deepest_reached` | string | 必填 | `LAYER_ORDER` 成员或 `real_effect` / `no_observation` |
| `receipt` | object\|null | | 请求绑定回执 |
| `cleanup_readback` | object\|null | | 独立 reader 的读回结果 |
| `artifacts` | string[] | | 产物路径列表 |

### 2.7 `CellResult`（方法 × 目标 的格子结果）

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `cell_id` | string | **PK** | |
| `method_id` | string | **FK → MethodCard** | |
| `target_id` | string | **FK → TargetProfile** | |
| `state` | enum | 必填 | `pass`\|`fail`\|`not_applicable`\|`tested_no_number`\|`untested`\|`inconclusive` |
| `n` | integer | 必填 | 试验数 |
| `k` | integer | 必填 | 命中数 |
| `p_lo` / `p_hi` / `point` | number | n≥`<待人工确认>` 时必填 | Wilson 区间 |
| `I` (`impact`) | object | | `{value, I_infosec, I_physical, caps_applied[]}` |
| `EXP` | object | | `{value, EXP_method, EXP_instance, components{}}` |
| `C` (`confidence`) | number | | 取值区间见 `spec/scoring.md` |
| `R_m` | number\|null | | `untested` 时为 **null，不是 0**（P4） |
| **`source`** | enum | 必填，`analytic` \| `measured` | **P7：缺此字段报告无效** |
| `reason_codes` | string[] | | 如 `cleanup_unverified` / `degenerate_ablation` |

### 2.8 `PriorRating`（先验评级）

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `prior_id` | string | **PK** | |
| `method_id` | string | **FK → MethodCard** | |
| `target_id` | string\|null | **FK → TargetProfile** | 空 = 方法级先验 |
| `prior_i` | `{point, lo, hi}` | 必填 | 后果先验 |
| `prior_exp` | `{point, lo, hi}` | 必填 | 可利用性先验 |
| `prior_sr` | `{point, lo, hi}` | 必填 | = `min(prior_i.point + prior_exp.point × k, 10)`；`k` 为缩放系数 `[待校准]` |
| `factors` | object | 必填 | 各因子取值**及其四类来源标注**（`[文献支撑]`/`[纪律]`/`[自研分量]`/`[待校准]`） |
| `mc_seed` | integer | 必填 | 蒙特卡洛种子（进报告头，C2） |
| `source` | string | 固定 `"analytic"` | P7 |

### 2.9 `Batch` / `ReportHeader` / `ValidationRun` / `Preregistration` / `ReusedComponent` / `ExternalAnchor` / `CalibrationProfile`

| 实体 | 关键字段 | 约束 |
|---|---|---|
| `Batch` | `batch_id`(PK) / `scope` / `positive_control_method_id`(FK→MethodCard) / `disposition`(枚举，含 `tool_self_intercept`) / `created_at` | positive control 失败 ⇒ 整批作废 |
| `ReportHeader` | 13 字段，见 `spec/report-header.schema.json` | **缺任一则报告无效** |
| `ValidationRun` | `validation_id`(PK) / `anchor_ref`(FK→ExternalAnchor) / `sample_n` / `metric`(枚举：`precision`\|`recall`\|`krippendorff_alpha`\|`weighted_kappa`\|`spearman`\|`bias`\|`mae`\|`dissent_rate`) / `value` / `ci_lo` / `ci_hi` | 效标须 `not_self_built: true` |
| `Preregistration` | `prereg_id`(PK) / `formula_sha256` / `weights_sha256` / `sampling_plan` / `thresholds` / `frozen_at` | **`frozen_at` 须早于任何实测产物的时间戳** |
| `ReusedComponent` | `name`(PK) / `source_url` / `version` / `sha256` / `license` | 未登记不得进评分路径 |
| `ExternalAnchor` | `name`(PK) / `source_url` / `version` / `sha256` / `not_self_built` | 同上 |
| `CalibrationProfile` | `calibration_id`(PK) / `target_id`(FK→TargetProfile) / `reach` / `adapt` / `pairs[]` | 报告中 `calibration.target == target_id`，否则拒绝评分 |

### 2.10 一致性约束（**CI 可断言**）

| # | 约束 |
|---|---|
| **M1** | 每张卡的 `preconditions` 的键必须 ∈ `TargetProfile.design_dimensions` 的 7 个键 |
| **M2** | `applicable(method, target) ⇔ ∀(dim, lvl) ∈ preconditions: target.design_dimensions[dim] ≥ lvl`，且**有单一实现** |
| **M3** | 每个 `(method, target)` 格子要么有 `CellResult`，要么为 `not_applicable`，无第三态 |
| **M4** | `R_m is null` ⟺ `state ∈ {untested, not_applicable, inconclusive}` |
| **M5** | 任何进入报告的 number 字段都必须带 `source` |
| **M6** | `provenance_kind == composition` ⟹ `composition_of` 非空且每个元素可在 `reused-components.json` 或文献引用表内解析 |
| **M7** | `EXT-` 前缀的卡占比 ≤ `<待人工确认>` |
| **M8** | `Category.predicate` 对全部 240 张卡求值，每个方法**至少命中一个类**（穷尽性） |---

## 3. 接口契约

### 3.1 形态前提（**待确认，影响本节写法**）

`docs/technical-design.md` §2.7 尚未决定前端形态。因此本节分两支写：

| 支 | 前提 | 本节的适用部分 |
|---|---|---|
| **支 A（无服务端）** | 前端为纯静态报告，或无前端；一切操作走 CLI | §3.2 逻辑操作 + §3.5 CLI 映射 |
| **支 B（有服务端）** | FastAPI/Flask + SPA 或 Streamlit | §3.2 逻辑操作 + §3.3 HTTP 映射 + §3.4 错误码 |

**两支共用 §3.2 的逻辑操作清单**——操作语义与形态无关，这是刻意的：**形态未定时，先冻结语义。**

### 3.2 逻辑操作清单（**与形态无关，先冻结**）

> 约定：`<>` 为待确认数值/选型；`[待确认]` 为待确认结论。

| # | 操作 | 输入 | 输出 | 副作用 | 幂等 | 旅程 |
|---|---|---|---|---|---|---|
| **OP-01** | `list_categories` | —— | `Category[]` | 无 | 是 | A |
| **OP-02** | `get_category` | `case_id` | `Category` + 方法数统计 | 无 | 是 | A/B |
| **OP-03** | `list_methods` | `case_id?` / 分页 | `MethodCard[]`（摘要） | 无 | 是 | A/B |
| **OP-04** | `get_method` | `method_id` | `MethodCard`（全字段） | 无 | 是 | A/B |
| **OP-05** | `validate_method_card` | `MethodCard` 原文 | `{ok, errors[], reason_codes[]}` | 无 | 是 | B |
| **OP-06** | `generate_negative_control` | `method_id` | `MethodCard`（负控卡草案） | **写文件** | 否 | B |
| **OP-07** | `count_identity` | —— | `{slots, distinct_methods, ext_ratio, per_category{}}` | 无 | 是 | 治理 |
| **OP-08** | `verify_coverage` | —— | `{predicate_hits[][], unassigned[], class_capacity{}}` | 无 | 是 | 治理 |
| **OP-09** | `list_targets` | —— | `TargetProfile[]` | 无 | 是 | A |
| **OP-10** | `register_target` | `TargetProfile` | `target_id` | **写文件** | 否 | A |
| **OP-11** | `run_calibration` | `target_id` | `CalibrationProfile` | 写产物 | 否 | A |
| **OP-12** | `run_matrix` | `target_id` / `case_id[]` / `method_ids[]` / `n` | `Batch` | **执行攻击，有靶标副作用** | 否 | A |
| **OP-13** | `get_batch_status` | `batch_id` | `Batch` + 进度 | 无 | 是 | A |
| **OP-14** | `abort_batch` | `batch_id` | `Batch`（`disposition=aborted`） | 终止执行 + **回滚清场** | 否 | A |
| **OP-15** | `compute_prior` | `method_ids[]` / `target_id?` | `PriorRating[]` | 无 | 是（同种子） | D |
| **OP-16** | `create_preregistration` | 先验公式 + 权重 + 抽样方案 + 阈值 | `Preregistration` | **写文件 + 冻结哈希** | 否 | D |
| **OP-17** | `get_preregistration` | —— | `Preregistration` | 无 | 是 | D |
| **OP-18** | `run_validation` | `anchor_names[]` / `sample_n` | `ValidationRun[]` | 执行参考目标 | 否 | D |
| **OP-19** | `get_validation_report` | —— | 四张对账表 | 无 | 是 | D |
| **OP-20** | `list_reused_components` | —— | `ReusedComponent[]` | 无 | 是 | C |
| **OP-21** | `list_external_anchors` | —— | `ExternalAnchor[]` | 无 | 是 | C/D |
| **OP-22** | `generate_report` | `batch_id` | `ReportHeader` + 报告产物 | **写产物** | 是（同输入同哈希） | A/C |
| **OP-23** | `get_report` | `report_id` | 报告（JSON/MD/图） | 无 | 是 | A/C |
| **OP-24** | `recompute_report` | `report_id` + 四个哈希的对应文件 | 复算结果 + 逐位比对 | 无 | 是 | C |
| **OP-25** | `submit_counterexample` | 反例描述 + 输入 + 期望 | `judge_regression` 用例草案 | **写文件** | 否 | C |
| **OP-26** | `scan_negative_assertions` | 扫描根目录 | `{hits[], files[]}` | 无 | 是 | 治理 |
| **OP-27** | `verify_dod_count` | —— | `{total, per_section{}, appendix_claim, match}` | 无 | 是 | 治理 |

### 3.3 HTTP 映射（**支 B 适用；支 A 忽略**）

> **前缀**：`/api/v1`　**方法**：只读用 `GET`，有副作用用 `POST`，删除用 `DELETE`。
> **通用请求头**：`X-Request-Id`（必填，用于日志关联）；`[待确认]` 是否加鉴权。
> **通用响应包封**：`{ "ok": bool, "data": <T>|null, "error": {code, message, details}|null, "request_id": string }`

| 操作 | 方法 | 路径 | 关键入参 | 成功码 | 备注 |
|---|---|---|---|---|---|
| OP-01 | GET | `/categories` | —— | 200 | |
| OP-02 | GET | `/categories/{case_id}` | —— | 200 | 404 若不存在 |
| OP-03 | GET | `/methods` | `case_id?` / `page` / `size` | 200 | 分页 `size` ≤ `<待确认>` |
| OP-04 | GET | `/methods/{method_id}` | —— | 200 | |
| OP-05 | POST | `/methods/validate` | `MethodCard` 原文 | 200 | **校验失败仍 200**，`data.ok=false` + `reason_codes` |
| OP-06 | POST | `/methods/{method_id}/negative-control` | —— | 201 | 返回草案，不自动落盘（`[待确认]`） |
| OP-07 | GET | `/identity` | —— | 200 | 双计数 |
| OP-08 | GET | `/coverage` | —— | 200 | 类容量矩阵 |
| OP-09 | GET | `/targets` | —— | 200 | |
| OP-10 | POST | `/targets` | `TargetProfile` | 201 | 409 若 `target_id` 已存在 |
| OP-11 | POST | `/targets/{target_id}/calibration` | —— | 202 | 异步，返回 `calibration_id` |
| OP-12 | POST | `/batches` | `target_id` / `case_ids[]` / `method_ids[]` / `n` | 202 | **有副作用**，须带授权范围 |
| OP-13 | GET | `/batches/{batch_id}` | —— | 200 | |
| OP-14 | DELETE | `/batches/{batch_id}` | —— | 202 | **须先回滚清场** |
| OP-15 | POST | `/prior/compute` | `method_ids[]` / `target_id?` / `seed` | 200 | 同种子幂等 |
| OP-16 | POST | `/preregistrations` | 公式 + 权重 + 抽样 + 阈值 | 201 | 冻结后不可改 |
| OP-17 | GET | `/preregistrations/current` | —— | 200 | 404 若未冻结 |
| OP-18 | POST | `/validations` | `anchor_names[]` / `sample_n` | 202 | |
| OP-19 | GET | `/validations/report` | —— | 200 | 四张对账表 |
| OP-20 | GET | `/reused-components` | —— | 200 | |
| OP-21 | GET | `/external-anchors` | —— | 200 | |
| OP-22 | POST | `/reports` | `batch_id` | 201 | 返回 `report_id` + 报告头 |
| OP-23 | GET | `/reports/{report_id}` | `format=json\|md\|png` | 200 | |
| OP-24 | POST | `/reports/{report_id}/recompute` | 四个哈希对应文件 | 200 | 返回逐位比对结果 |
| OP-25 | POST | `/judge-regression/counterexamples` | 反例 | 201 | |
| OP-26 | GET | `/governance/negative-assertions` | —— | 200 | |
| OP-27 | GET | `/governance/dod-count` | —— | 200 | |

**健康检查**：`GET /healthz` → `{ok, version}`。`[待确认]` 版本字段来源。

### 3.4 错误码表（**支 B 适用**）

| code | HTTP | 含义 | 触发场景 | `details` 内容 |
|---|---|---|---|---|
| `OK` | 200 | 成功 | —— | —— |
| `VALIDATION_FAILED` | 200 | 校验未通过（**语义失败，非传输失败**） | OP-05 schema / 47 条规则不通过 | `[{rule_id, field, message}]` |
| `NOT_FOUND` | 404 | 实体不存在 | `case_id` / `method_id` / `target_id` / `batch_id` / `report_id` 不存在 | `{entity, id}` |
| `CONFLICT` | 409 | 唯一性冲突 | `target_id` 已存在；`report_id` 重复 | `{entity, id}` |
| `SCHEMA_VERSION_MISMATCH` | 409 | schema 版本与卡不匹配 | 卡的 `schema_version` ≠ 当前 | `{card_version, current}` |
| `MECHANISM_REF_INVALID` | 422 | `mechanism_ref` 不匹配 pattern，或指向分类学条目 | 硬规矩；R19 | `{value, pattern, reason}` |
| `COMPOSITION_UNRESOLVED` | 422 | `composition_of` 有元素解析不到 | 硬规矩 F | `{unresolved: [...]}` |
| `EXT_RATIO_EXCEEDED` | 422 | `EXT-` 占比超上限 | 硬规矩 C | `{actual, limit}` |
| `NEGATIVE_CONTROL_INVALID` | 422 | 负控指向不存在的卡 | F1 DoD | `{method_id, referenced}` |
| `CLEANUP_UNVERIFIED` | 409 | 清场未验证 | 评分前检查 | `{batch_id, arm}` |
| `POSITIVE_CONTROL_FAILED` | 409 | 正控未命中 ⇒ **整批作废** | F2 C1 | `{batch_id, disposition: "tool_self_intercept"}` |
| `CALIBRATION_TARGET_MISMATCH` | 409 | 校准档的 `target` ≠ 本次 `target_id` | §3.2 防串用 | `{calibration_target, request_target}` |
| `JUDGE_NOT_REGISTERED` | 422 | 判据不在注册表内 | P1 | `{judge_id}` |
| `JUDGE_NOT_DETERMINISTIC` | 422 | 判据非确定性且被要求出分 | P1 | `{judge_id, report_dependent}` |
| `REUSED_COMPONENT_NOT_PINNED` | 422 | 复用件未登记版本/哈希 | C6 | `{name}` |
| `ANCHOR_NOT_EXTERNAL` | 422 | 效标 `not_self_built != true` | R13 循环性 | `{name}` |
| `PREREG_MISSING_OR_LATE` | 409 | 预注册缺失，或冻结时间戳晚于实测产物 | R13 / F7 | `{prereg_at, first_run_at}` |
| `THRESHOLD_MUTATED` | 409 | 预注册阈值被事后修改 | F7 DoD | `{field, frozen_sha256, current_sha256}` |
| `NUMBER_WITHOUT_SOURCE` | 422 | 报告中数字缺 `source` | P7 | `{path}` |
| `PRIOR_USED_IN_CONCLUSION` | 422 | 先验分出现在结论段 | P8 | `{path}` |
| `R_M_NULL_VIOLATION` | 422 | 无分态却输出 `R_m` | M4 / P4 | `{state, R_m}` |
| `CAP_VIOLATION` | 422 | 封顶未按规则施加 | P3 | `{reached, declared, expected_cap}` |
| `GRADE_UNREACHABLE` | 422 | 档位在可行域内不可达 | R14 | `{grade, max_achievable}` |
| `OFFLINE_VIOLATION` | 422 | 必要路径出现网络调用 | NF2 | `{module, call}` |
| `OUT_OF_SCOPE` | 422 | 越界请求（如把 D 当容器、写 `T09`） | §2.3 | `{requested}` |
| `RATE_LIMITED` | 429 | 超出并发上限 | `[待确认]` 上限 | `{limit, retry_after_s}` |
| `INTERNAL` | 500 | 未分类内部错误 | —— | `{trace_id}` |
| `NOT_IMPLEMENTED` | 501 | 该操作在一期不做 | `[待确认]` 清单 | `{op}` |

**错误码纪律**：

| # | 纪律 |
|---|---|
| **E1** | **语义失败不得用 4xx/5xx 表达**——如方法卡校验不通过返回 200 + `data.ok=false`；4xx 只用于"请求本身不可受理" |
| **E2** | 每个错误码必须能映射到**一条 设计规格 DoD 或一节规范**（上表"触发场景"列即该映射） |
| **E3** | 错误码一经发布不得改变语义；废弃须标记 `deprecated` 并保留 `<待人工确认>` 个版本 |
| **E4** | 所有 `details` 字段**不得包含载荷正文、凭据、真实目标地址**（NF3） |

### 3.5 CLI 映射（**支 A 适用；与 §3.3 语义等价**）

> CLI **必须**能独立完成四个旅程。命令名 `[待确认]`，此处按 `make` 目标写。

| 操作 | `make` 目标 | 备注 |
|---|---|---|
| OP-01/02/03/04 | `make list` / `make show METHOD=<id>` | |
| OP-05 | `make validate METHOD=<id>\|ALL` | 退出码：0 通过 / 1 校验失败 / 2 用法错误（**`[待确认]` 退出码表**） |
| OP-06 | `make negctl METHOD=<id>` | |
| OP-07/08 | `make identity` / `make coverage` | |
| OP-09/10 | `make targets` / `make target-add FILE=<path>` | |
| OP-11 | `make calibrate TARGET=<id>` | |
| OP-12 | `make run TARGET=<id> CASE=<id>\|ALL N=<n>` | **有副作用** |
| OP-13/14 | `make status BATCH=<id>` / `make abort BATCH=<id>` | abort 必须回滚清场 |
| OP-15 | `make prior METHOD=<id>\|ALL SEED=<n>` | |
| OP-16/17 | `make prereg` / `make prereg-show` | |
| OP-18/19 | `make validate-anchors` / `make validation-report` | |
| OP-20/21 | `make reused` / `make anchors` | |
| OP-22/23 | `make report BATCH=<id>` | |
| OP-24 | `make recompute REPORT=<id>` | |
| OP-25 | `make counterexample FILE=<path>` | |
| OP-26/27 | `make scan-negative` / `make dod-count` | |
| 旅程 A 一键 | `make eval-offline` | 离线全流程 |
| 旅程 D 一键 | `make validate-on-agentdojo` | 参考目标上的验证链 |

**CLI 纪律**：

| # | 纪律 |
|---|---|
| **E5** | `make eval-offline` 与 `make validate-on-agentdojo` 必须在**断网**下跑通（NF2） |
| **E6** | 所有写操作须支持 `--dry-run`（`[待确认]`） |
| **E7** | 有靶标副作用的操作（OP-12/14）必须打印**本次授权范围**与**回滚状态** |
| **E8** | CLI 输出须有 `--json` 开关，产出与 §3.3 的 `data` 同构（保证两形态语义等价） |---

## 4. 模块依赖与调用关系

### 4.1 分层与依赖方向

```
┌──────────────────────────────────────────────────────────────┐
│  apps/          应用层（CLI 必做；web [待确认]）                │
│                 唯一允许依赖下层全部模块的层                    │
└───────┬──────────────┬───────────────┬───────────────────────┘
        │              │               │
        ▼              ▼               ▼
┌───────────────┐ ┌──────────┐ ┌──────────────┐
│ report/       │ │validation/│ │ tools/       │
│ 报告生成      │ │ 验证链    │ │ 批量与运维    │
└───┬───────────┘ └────┬─────┘ └──────┬───────┘
    │                  │              │
    ▼                  ▼              ▼
┌──────────────────────────────────────────────────────────────┐
│  score/       纯函数式评分（measured / prior / stats）         │
│  judges/      判据注册与实现                                   │
└───────┬───────────────────────┬──────────────────────────────┘
        │                       │
        ▼                       ▼
┌───────────────┐      ┌──────────────────┐
│ harness/      │      │ targets/         │
│ 复用层薄壳     │◀─────│ 目标层           │
└───────┬───────┘      └──────────────────┘
        │
        ▼
┌───────────────────────────────┐
└───────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  spec/        规范层：无代码依赖，被所有层只读消费               │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 依赖矩阵（**行依赖列**；`●` = 允许，`○` = 禁止）

| ↓依赖 / 被依赖→ | spec | harness | targets | judges | score | report | validation | tools | apps |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **spec** | — | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ |
| **harness** | ● | — | ○ | ○ | ○ | ○ | ○ | ○ | ○ |
| **targets** | ● | ● | — | ○ | ○ | ○ | ○ | ○ | ○ |
| **judges** | ● | ● | ○ | — | ○ | ○ | ○ | ○ | ○ |
| **score** | ● | ○ | ○ | ○ | — | ○ | ○ | ○ | ○ |
| **report** | ● | ○ | ○ | ○ | ● | — | ○ | ○ | ○ |
| **validation** | ● | ● | ● | ● | ● | ○ | — | ○ | ○ |
| **tools** | ● | ● | ● | ○ | ● | ○ | ○ | — | ○ |
| **apps** | ● | ● | ● | ● | ● | ● | ● | ● | — |

**三条硬规则（CI 可断言）**：

| # | 规则 | 理由 |
|---|---|---|
| **L1** | **依赖图必须无环** | 有环即无法单独测试任一层 |
| **L2** | **`[开源]` 目录不得依赖 `[闭源]` 目录** | 设计规格 §2.2.1：否则开源层无法单独发布 |
| **L3** | **`score/` 不得依赖 `harness/` / `targets/` / `judges/` 的实现** | 评分只消费**已落盘的结果**，不参与执行；这是"门禁与评分分离"的结构保证 |

### 4.3 关键调用序列

**序列 1：旅程 A —— 给目标打分（`make eval-offline` / `make run`）**

```
apps/cli
  └─▶ targets 载入 TargetProfile
        └─▶ harness/target_adapter 建立连接
  └─▶ harness/calibration_battery 跑 B1–B5
        └─▶ 产出 CalibrationProfile（绑定 target_id）
  └─▶ apps 组装 (method × target) 执行计划
        └─▶ harness/causal_slice 跑五臂
              └─▶ harness/defense_layers 记录 deepest_reached
              └─▶ harness/evidence_lifecycle 落证据
        └─▶ judges/* 判定
              └─▶ 产出 Judgement（含 reached_layer）
        └─▶ 落 Trial
  └─▶ score/measured 计算 CellResult（I / EXP / C / R_m）
        └─▶ score/stats Wilson 下界
        └─▶ score/constants 读取 spec/scoring.md 常数
  └─▶ score/measured 汇总 Scenario / Target 级
  └─▶ report/* 渲染（JSON + MD + 图）
        └─▶ 写 ReportHeader（13 字段 + 四个哈希）
```

**序列 2：旅程 B —— 加一个新方法**

```
apps/cli
  └─▶ tools/verify_coverage 校验 predicate 命中与类容量
  └─▶ judges 校验 judge 已在注册表
  └─▶ score/constants 校验常数未内联
  └─▶ apps 生成负控草案
  └─▶ judge_regression 跑 anchor 回归（防破坏既有结论）
  └─▶ 通过 ⇒ 落 methods/<CASE>/*.yaml
```

**序列 3：旅程 D —— 验证打分方法**

```
apps/cli
  └─▶ validation/prereg 读 docs/preregistration.md，校验 frozen_at 早于实测产物
  └─▶ score/prior 计算 Prior_I / Prior_EXP / Prior_SR（含区间，显式种子）
  └─▶ targets/agentdojo 载入参考目标
        └─▶ judges/adapted 调用 AgentDojo security()（复用件，pin 版本）
  └─▶ score/measured 计算实测 I / EXP
  └─▶ validation/reconcile 逐分量对账
        └─▶ score/stats Spearman / MAE / Krippendorff α
  └─▶ 写 docs/validation-report.md（四张表）
  └─▶ 校验：每个效标 ∈ spec/external-anchors.json 且 not_self_built == true
```

**序列 4：旅程 C —— 复算**

```
apps/cli
  └─▶ 读 ReportHeader 的四个哈希
  └─▶ 校验哈希与实际文件一致
  └─▶ score/* 用同一 spec + 同方法库 + 同靶标 + 同种子重算
  └─▶ 逐位比对（浮点容差 0）
  └─▶ 不一致 ⇒ 输出首个分歧点的字段路径
```

### 4.4 入口命令（`Makefile` 目标清单）

> 目标名 `[待确认]`。

| 目标 | 作用 | 对应操作 | 是否离线可用 |
|---|---|---|---|
| `make eval-offline` | 离线全流程（旅程 A） | OP-09…OP-23 | **必须** |
| `make validate-on-agentdojo` | 参考目标上的验证链（旅程 D） | OP-18/19 | **必须** |
| `make validate` | 方法卡批量校验 | OP-05 | 是 |
| `make coverage` | 覆盖率与类容量 | OP-08 | 是 |
| `make identity` | 双计数 | OP-07 | 是 |
| `make report` | 生成报告 | OP-22 | 是 |
| `make recompute` | 复算比对 | OP-24 | 是 |
| `make scan-negative` | 负向断言检索 | OP-26 | 是 |
| `make dod-count` | DoD 计数复算 | OP-27 | 是 |
| `make test` | 全部测试 | —— | 是 |
| `make ci` | 三处门禁 | —— | 是（含禁网 job） |

### 4.5 跨模块不变量（**跨层生效，CI 可断言**）

| # | 不变量 | 检查方式 |
|---|---|---|
| **X1** | 常数只在 `spec/scoring.md` §1 定义一次，代码经 `score/constants.py` 单点读取 | 静态检查：`score/` 与 `report/` 内不出现裸数值字面量（白名单除外） |
| **X2** | 报告里每个 number 带 `source` | 对 `report.json` 全字段扫描 |
| **X3** | `R_m is null` ⟺ 无分态 | 对 `CellResult` 全量断言 |
| **X4** | `applicable()` 只有一个实现，在 `score/` 或 `harness/` 之一（**`<待确认>`**），其余调用它 | 全仓库检索该函数名 |
| **X5** | 靶标副作用操作必有回滚，回滚结果落盘 | `tools/` 检查每个 `run_*` 的 finally 分支 |
| **X6** | 复用件调用点必须携带版本断言 | `judges/adapted` 内每个复用调用前断言版本 |
| **X7** | 预注册哈希在验证报告中被引用且一致 | `validation/` 交叉校验 |

---

## 5. 前端页面清单与组件划分

> ⚠️ **本节整体依赖 `docs/technical-design.md` §2.7 的前端形态决策。**
> **若结论为"不做前端"**：§5.1–§5.4 仍有用——**它们定义了"静态报告必须回答什么"**，可直接转为 `report/render_md.py` 的章节清单（见 §5.5）。

### 5.1 页面清单

| # | 页面 | 回答的问题 | 主要用户 | 依赖操作 | 形态 |
|---|---|---|---|---|---|
| **P1** | **首页 / 定位** | 这是什么、谁该用、怎么跑、不做什么 | 全部 | —— | 静态 |
| **P2** | **方法目录** | 8 个攻击类别各有哪些方法、哪些是真跑过的 | 红队、研究者 | OP-01/02/03 | 需列表 |
| **P3** | **方法详情** | 这个方法的出处、机制、适用前提、判据、实测明细 | 红队、复现者 | OP-04 | 需详情 |
| **P4** | **类别容量矩阵** | 每类实际有几个方法、距 `min_methods` 还差多少 | 治理、评审 | OP-08 | 表格/热图 |
| **P5** | **目标画像** | 目标在 Kim 7 维上的档位、防护层配置 | 甲方、选型 | OP-09 | 表单/详情 |
| **P6** | **运行批次** | 这次跑了什么、进度、正控是否通过 | 红队 | OP-12/13/14 | 需状态刷新 |
| **P7** | **报告 · 方法效力榜（主）** | 哪些方法有效、多强、适用目标集、置信下界 | 红队、研究者 | OP-23 | 表格 + 图 |
| **P8** | **报告 · 目标易攻榜（副）** | 这个目标多容易被攻破 | 甲方 | OP-23 | 表格 + 图 |
| **P9** | **报告 · 防护消融** | 该修哪一层（`ΔL_i` 与归一化 `layer_importance`） | 防守方 | OP-23 | 图 |
| **P10** | **报告 · 状态清单** | 哪些没测 / 不适用 / 不可判 | 全部 | OP-23 | 表格 |
| **P11** | **先验评级** | 240 格的先验分与区间、`source: analytic` | 研究者 | OP-15 | 表格 + 区间图 |
| **P12** | **验证报告** | 判据/严重度/先验三层对账结果 | 方法论研究者 | OP-19 | 四张表 |
| **P13** | **复算与质疑** | 输入四个哈希复算、提交反例 | 质疑者 | OP-24/25 | 表单 |
| **P14** | **治理看板** | 双计数、`EXT-` 占比、负向断言、DoD 计数 | 治理 | OP-07/26/27 | 卡片 |
| **P15** | **复用件与外部锚点** | 借了谁、什么版本、什么哈希、是不是自造的 | 质疑者 | OP-20/21 | 表格 |

**一期页面范围**：`[待确认]`（建议 P1/P2/P3/P7/P10 为一期最小集，其余二期）。

### 5.2 组件划分（通用组件）

| 组件 | 职责 | 被哪些页面用 | 关键 props |
|---|---|---|---|
| `<SourceBadge>` | 显示 `analytic` / `measured` 标记 | P7/P8/P11 | `source` |
| `<UncertaintyCell>` | 显示 `point [lo, hi]` 与 n | P7/P8/P11 | `point, lo, hi, n` |
| `<StatePill>` | 六态徽标，`untested` 与 `0 分`视觉区分 | P7/P10 | `state` |
| `<ProvenanceTable>` | 四分量出处表（机制/通道/手法类/变换） | P3/P15 | `components[]` |
| `<DisciplineTag>` | 四类来源标注徽标（文献支撑/纪律/自研分量/待校准） | P3/P11 | `tag` |
| `<DimensionRadar>` | Kim 7 维档位雷达图 | P5 | `dimensions{}` |
| `<LayerAblationChart>` | `ΔL_i` 与 `layer_importance` 条形图 | P9 | `deltas{}, importance{}` |
| `<ConclusionBanner>` | 结论受限横幅（`coverage_s < FLOOR` 或 `Q < FLOOR` 或回归未过） | P7/P8 | `limited, reasons[]` |
| `<HashBadge>` | 四个哈希的短显示 + 校验状态 | P13 | `hashes{}` |
| `<RejectList>` | 校验失败的 reason code 列表 | P3/P6 | `errors[]` |

### 5.3 页面 → 组件 → 操作 映射

| 页面 | 主要组件 | 调用的操作 |
|---|---|---|
| P2 | 列表 + `<StatePill>` + 搜索/筛选 | OP-03 |
| P3 | `<ProvenanceTable>` + `<DisciplineTag>` + `<RejectList>` | OP-04/05 |
| P4 | 矩阵表 + 容量条 + 缺口标注 | OP-08 |
| P5 | `<DimensionRadar>` + 防护层开关表 | OP-09/10 |
| P6 | 进度条 + `<RejectList>` + 回滚状态 | OP-13/14 |
| P7 | `<UncertaintyCell>` + `<SourceBadge>` + `<ConclusionBanner>` | OP-23 |
| P8 | 同 P7 | OP-23 |
| P9 | `<LayerAblationChart>` | OP-23 |
| P10 | `<StatePill>` + 完整状态清单 | OP-23 |
| P11 | `<UncertaintyCell>` + `<DisciplineTag>` | OP-15 |
| P12 | 四张对账表组件 | OP-19 |
| P13 | `<HashBadge>` + 复算表单 + 反例表单 | OP-24/25 |
| P14 | 指标卡 + `<SourceBadge>` | OP-07/26/27 |
| P15 | `<ProvenanceTable>` + 版本/哈希列 | OP-20/21 |

### 5.4 前端纪律（**无论形态都必须遵守**）

| # | 纪律 | 理由 |
|---|---|---|
| **U1** | **`Prior_SR` 不得出现在任何"安全/危险结论"区块** | P8（先验不得支撑断言） |
| **U2** | **`source` 标记必须与数字同屏可见**，不得只在 tooltip 里 | P7 |
| **U3** | **`untested` 必须与 `R = 0` 视觉可区分** | P4（没测 ≠ 没风险） |
| **U4** | **聚合值必须带 `index_only` 标记**，且逐维表可展开 | B 类断言通则 |
| **U5** | **先验榜与实测榜不得同屏混排** | P7（两估计量不混排） |
| **U6** | **结论受限时必须显示横幅**，不得只在页脚小字 | 报告纪律 |
| **U7** | **不得在前端做任何计算**——一切数值来自后端/产物 | C2（逐位可复算） |

### 5.5 若不单独做前端：静态报告必须回答的问题

把 §5.1 的"回答的问题"列直接转成 `report/render_md.py` 的章节：

| # | 报告章节 | 对应页面 |
|---|---|---|
| 1 | 这是什么 / 不做什么 | P1 |
| 2 | 方法效力榜（含适用目标集、置信下界、`source`） | P7 |
| 3 | 目标易攻榜 | P8 |
| 4 | 防护消融与层贡献度 | P9 |
| 5 | 状态清单（六态，`untested` 显式列出） | P10 |
| 6 | 先验评级概览（含区间，标注 `analytic`） | P11 |
| 7 | 验证与对账小结 | P12 |
| 8 | 复算指引（四个哈希 + 命令） | P13 |
| 9 | 治理指标（双计数 / `EXT-` 占比） | P14 |
| 10 | 复用件与外部锚点清单 | P15 |
| 11 | 类别容量矩阵 | P4 |

> **结论**：P1–P15 的**内容需求**与技术栈决策无关；形态只决定它们是"网页"还是"报告章节"。**因此 §5 可以在前端形态未定时先冻结。**

---

## 6. 待人工确认清单（**本文档的验收项**）

| # | 待确认项 | 所在 | 阻塞什么 |
|---|---|---|---|
| T-01 | Python 版本 | 技术栈 §2.1 | 全部实现 |
| T-02 | 包管理与 lockfile | 技术栈 §2.1 | C3/C6 |
| T-03 | 方法卡载体格式（YAML/JSON） | 技术栈 §2.2 | §2.3 解析 |
| T-04 | `x-validation-rules` 28 条中哪些归 schema、哪些归 CI | 技术栈 §2.2 | OP-05 实现 |
| T-05 | trial 级数据是否入库 | 技术栈 §2.3 | §2.6 存储 |
| T-06 | 数值库与蒙特卡洛实现 | 技术栈 §2.4 | C2 |
| T-07 | 是否禁用多线程 BLAS | 技术栈 §2.4 | C2 |
| T-08 | Spearman / κ / α 自实现或调库 | 技术栈 §2.4 | F7 |
| T-09 | **文本层判据是否接受离线例外** | 技术栈 §2.5 | **C3 的唯一可能破口** |
| T-10 | 严重度标尺：复用代码 vs 重实现 rubric | 技术栈 §2.5 | F3 |
| T-11 | AgentDojo 版本号；是否 vendor | 技术栈 §2.5 | C6 |
| T-12 | **前端形态** | 技术栈 §2.7 | §5 全节 |
| T-13 | 绘图库 | 技术栈 §2.6 | OP-23 |
| T-14 | CI 平台与禁网 job 实现 | 技术栈 §2.8 | NF2 |
| T-15 | `applicable()` 的唯一实现在哪层 | §4.5 X4 | L3 |
| T-16 | CLI 命令名与退出码表 | §3.5 | E8 |
| T-17 | 一期页面范围 | §5.1 | 工作量 |
| T-18 | 并发上限与超时 | §3.4 `RATE_LIMITED` | OP-12 |
| T-19 | `EXT-` 占比上限的最终值 | §2.10 M7 | 硬规矩 C |
| T-20 | `min_methods` 与每类锚点数上限的最终值 | §2.2 | F1 |

**验收规则**：本文冻结时，上表 20 项**逐项清零**（给出值或标"一期不做"）。未清零项不得进入实现。
---

## 7. 形态决策生效后的调整（**2026-09-29 追加**）

`docs/technical-design.md` §6 已确认 **A2 = 纯静态报告，不做前端**。本文相应调整如下。

| 位置 | 调整 |
|---|---|
| **§3.1** | **支 A 生效**。§3.3（HTTP 映射）与 §3.4（错误码表）**降级为"若将来做服务端时的备用设计"**，不在一期实现，但**保留不删**——因为错误码承载了 设计规格 DoD 的映射关系（错误码纪律 E2），是规范资产 |
| **§3.5** | **为一期唯一接口形态**。CLI 纪律 E5–E8 全部生效 |
| **§5.1** | 页面清单转为**报告章节清单**。一期范围 = **P1 / P2 / P3 / P7 / P10 的内容需求** |
| **§5.2–§5.4** | 组件划分转为**报告模板的分节**；前端纪律 U1–U7 **逐条转为报告生成器的断言**（U7"不得在前端做任何计算"转为"报告生成器不得重算数值，只读评分产物"） |
| **§5.5** | **由"若不单独做前端"转为正式清单**（见下） |
| **§4.1 / §4.2** | `apps/web` 目录**一期不建**；`apps/cli` 为一期唯一应用入口 |
| **§6 T-12** | 前端形态 **已确认**（不做前端），该待确认项关闭 |
| **§6 T-07** | 因 B4（纯标准库自实现）**自动消解**，无需禁用 BLAS |

### 7.1 一期报告章节清单（**正式，取代 §5.1 的页面形态**）

| # | 报告章节 | 来源页面 | 必答问题 |
|---|---|---|---|
| 1 | 这是什么 / 不做什么 | P1 | 定位、范围外、`EXT-` 占比、双计数 |
| 2 | 方法目录（按 8 类分组） | P2 | 每类有哪些方法、哪些有实测 |
| 3 | 方法详情 | P3 | 四分量出处、适用前提、判据、实测明细、`source` 标记 |
| 4 | **方法效力榜（主）** | P7 | 适用目标集、成功数/适用目标数、Wilson 下界、`source` |
| 5 | **状态清单** | P10 | 六态完整列出，`untested` 与 `0 分` 视觉可分 |
| 6 | 复算指引 | P13（部分） | 四个哈希 + 命令 |
| 7 | 治理指标 | P14（部分） | 双计数 / `EXT-` 占比 / 负向断言扫描结果 |

> 其余章节（目标易攻榜 P8、防护消融 P9、先验评级 P11、验证报告 P12、复用件清单 P15、类别容量矩阵 P4）**列为二期**，但**生成器须留出章节插槽**且插槽为空时显式输出"二期"而非留白。