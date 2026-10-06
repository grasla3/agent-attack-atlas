# 校验规则实现覆盖率（`docs/ci-coverage.md`）

| 项 | 值 |
|---|---|
| 生成方式 | **由 `tools/gen_ci_coverage.py` 从 `tools/cardcheck.py` 的 `RULES` 表生成**，不是手写 |
| 一致性 | Gate 0 `ci_coverage_sync` 断言本文件与代码一致；不一致即构建失败 |
| 规则来源 | `spec/method-card.schema.json` 的 `x-validation-rules`，共 **47** 条 |
| 已实现 | **40** 条（有可执行检查） |
| 结构保证 | **4** 条（由 schema 的 type/enum/pattern/required 直接保证） |
| **登记缺口** | **3** 条（下表逐条给出原因与解除条件） |
| 未映射 | **无** |

> **为什么要有这张表**：设计规格 F6 的 DoD 写着「任何一条 `x-validation-rules` 若尚未实现，必须在 `docs/ci-coverage.md` 显式列为缺口」。
> 只把规则写在 schema 里、却没有任何执行器，等于没有规则——本项目已经因为「Gate 1 全是 `[TODO]` 占位」
> 而漏掉过一次真实的契约冲突（`primary_asset` / `provenance_components` / `preconditions` 三处）。

## 1. 已实现（40 条）

| # | rule_id | 规则摘要 | fixture 反例 |
|---|---|---|---|
| 1 | `unique_method_id` | method_id 全局唯一，且其前缀必须等于 case_id。 | ✅ |
| 2 | `verifier_registered` | judge.verifier 必须存在于 judges/ 注册表；未注册一律拒绝，禁止在卡内发明判据。 | — |
| 3 | `negative_control_ref` | negative_control.kind != 'none' 时，negative_control.method_id 必须指向一张存在的卡片；kind='none' 仅允许用于 anchor=fa | ✅ |
| 6 | `mechanism_ref_shape` | mechanism_ref 必填且必须匹配 ^(ATK-[A-Z]+-[0-9]{2}\|S_L[0-9]+_[a-z_]+\|EXT-[A-Za-z0-9_-]+)$；变换族名（chatml/mot | ✅ |
| 7 | `min_mechanisms` | 同一 case_id 下，【不同的 mechanism_ref 值】的数量必须 >= 该场景清单声明的 min_mechanisms（默认 30）。【口径】本字段衡量的是**机制覆盖度**，**不是方 | ✅ |
| 8 | `variant_excluded_from_count` | variant_of 非空的卡片不计入 min_mechanisms 与 min_methods 的分子；其 mechanism_ref 必须与其基准卡一致。 | — |
| 9 | `script_exists` | execution.mode == 'script_hook' 时，execution.script 必填，且该脚本必须存在于仓库中。 | ✅ |
| 10 | `cleanup_fields` | cleanup.required == true 时，cleanup.reader 与 cleanup.expected_postcondition 均为必填。 | ✅ |
| 12 | `variant_ref_exists` | variant_of 非空时，其指向的 method_id 必须存在，且两卡的 case_id 相同。 | ✅ |
| 13 | `min_methods` | 同一 case_id 下，variant_of 为空的卡片数必须 >= 该场景清单声明的 min_methods（默认 30）。 | — |
| 14 | `self_attested_debt_list` | judge.self_attested == true 的卡片允许入库，但 scoring 阶段 C 恒为 0；CI 必须输出这类卡片的清单作为技术债。 | — |
| 15 | `design_class_negative_control` | design_class == 'reverse_captcha' 时 negative_control.kind 必须为 format_matched_benign 或 semantic_match | ✅ |
| 16 | `control_follow_rate` | design_class 为 'reverse_captcha' 或 'obfuscation' 的卡片，其 judge.params 必须显式记录 control_follow_rate；只报 at | ✅ |
| 17 | `required_actions_in_profile` | trigger_path.required_actions 的每个动作必须在目标能力画像中存在；否则该卡在目标上记 untested 而非 fail。 | — |
| 21 | `dual_grade_present` | source_grade 与 numeric_evidence 均为必填且不得为空；缺任一即拒绝（双等级严格分列，不得出现 'S/A' 这类复合值）。 | — |
| 22 | `report_dependent_flagged` | judge 若依赖被测 agent 可自述的内容（自报上下文、自报是否泄露），必须在 judges/ 注册表中标记 report_dependent: true；此类判据不得单独支撑任何 confir | — |
| 23 | `canary_required` | 缺少唯一秘密（canary）时，'真泄露'与'泛化自述'在本目标上不可分辨，此类方法的状态必须为 inconclusive，不得记 pass 也不得记 fail（D14 的根因）。 | — |
| 25 | `physical_needs_state_judge` | physical_consequence ∉ {'none','D09'} 时，judge.verifier 在 judges/registry.json 中必须满足 supports_physica | ✅ |
| 26 | `composition_of` | provenance_kind == composition 时 composition_of 必填且 minItems >= 1，且每个元素可在共享文献池或 reused-components.js | ✅ |
| 27 | `ext_ratio_20pct` | provenance_kind == ext 的方法数 / 全部方法数 <= 20%（硬规矩 C）。超标即拒绝，不得靠下调 provenance_kind 蒙混。 | ✅ |
| 28 | `source_grade_dash_iff_ext` | source_grade == '—' 当且仅当 provenance_kind == ext；其余 provenance_kind 使用 '—' 即拒绝（不得用空等级掩盖缺文献）。 | ✅ |
| 29 | `preconditions_kim7` | preconditions 的键必须 ∈ spec/target-profile.schema.json 的 design_dimensions 的 7 个键（input_trust / access | ✅ |
| 30 | `preconditions_levels` | preconditions 的每个取值为整数 1/2/3；出现其它取值即拒绝。 | ✅ |
| 31 | `primary_asset_dispute_warn` | primary_asset == case_id 时视为无争议；primary_asset != case_id 时该卡记为【边界争议卡】并由门禁报 WARN（不是 ERROR），争议清单必须出现在报 | — |
| 33 | `text_layer_needs_fallback` | evidence_layer == 'text' 时，该 case 的 allow_text_fallback 必须为 true；否则拒绝（D 类状态后果不得以文本层作为成功判据）。 | ✅ |
| 34 | `declared_vs_reached_cap` | judge.evidence_layer 声明为 'text' 的方法不得被强制要求达到 state 层；反之声明为 'state' 而实测只到 behavior 的方法，其 I 必须被封顶（CAP_ | — |
| 35 | `variant_provenance_identical` | variant_of 非空时，其 mechanism_ref 与 provenance_components 必须与其基准卡逐字段一致（变体只改包装，不改出处）。 | — |
| 36 | `primary_asset_union` | 全部方法卡的 primary_asset 并集必须等于 {T01..T08}；缺任一类即报 unassigned（该类尚无方法）。 | — |
| 37 | `judge_registry_consistency` | judge.verifier 必须命中 judges/registry.json；judge.evidence_layer 必须 ∈ 该判据的 evidence_layers 集合；judge.par | ✅ |
| 38 | `canary_params_required` | judges/registry.json 中 requires_canary == true 的判据，其方法卡 judge.params.canary_id 必填；缺 canary 时该格只能记 in | ✅ |
| 39 | `mechanism_prefix_kind_binding` | 机制出处前缀与 provenance_kind 互为充要：`EXT-` ⟺ `provenance_kind == ext`；`LIT-` ⟹ `provenance_kind ∈ {interpol | ✅ |
| 40 | `lit_resolvable_in_bibliography` | `LIT-<bib_id><可选机制后缀>` 的每一处引用都必须能解析到 docs/bib-*.md 或 docs/shared-bibliography.md 中真实存在的 bib_id。**两种形 | ✅ |
| 41 | `lit_unique_per_paper_mechanism` | 同一个 `LIT-` 值（含后缀）在全库出现的次数 <= 1。**注意它约束的是机制级标识，不是论文**：一篇文献切出多个独立机制时，应各用一个后缀（`LIT-B-113` 与 `LIT-B-113B | — |
| 42 | `c11_distinctness_evidence` | C11：本卡主张自己在某一轴上与同 case_id 下的基准卡不同时（即存在同 `mechanism_ref` 但该轴取值不同的另一张卡），`distinctness_evidence` 必填，且其  | ✅ |
| 43 | `c4_five_axis_identity` | C4 五轴身份：计数与去重按【注入入口 / 目标资产 / 机制首步 / 交互形态 / 判据层】五轴进行，**不得**按 `mechanism_ref` 单轴去重，**不得**按四分量元组去重（后者见  | — |
| 44 | `required_actions_identifier` | `trigger_path.required_actions` 的每个元素必须匹配 ^[a-z][a-z0-9_]*$（动作标识，不是描述）；前置条件属于 `preconditions`（Kim 7  | ✅ |
| 46 | `atk_prefix_whitelist` | `ATK-<前缀>-NN` 的前缀必须来自 **表1 的 8 个既有前缀**白名单：`APP` / `CODE` / `EMB` / `INJ` / `MAS` / `MEM` / `SUP` / ` | ✅ |
| 47 | `original_table_needs_locator` | `numeric_evidence == 'original_table'` 时，卡上必须有**至少一处表号/图号引用**（形如 `Table 5` / `Fig. 3` / `表 2` / `图 4 | ✅ |

## 2. 由 schema 结构直接保证（4 条）

| # | rule_id | 规则摘要 | 由什么保证 |
|---|---|---|---|
| 5 | `case_container` | case_id 属于 T01..T08 时方可作为方法卡容器。D01..D10B 只能出现在 target_consequence 标签中；baseline 是 | 由 case_id / target_consequence 的 enum 在 schema 层保证 |
| 11 | `impact_class_letters` | impact_class 的每个字母必须在 A/B/C/D/E/F 之内；含未定义字母即拒绝。 | 由 impact_class.items.enum 保证 |
| 24 | `case_container_strict` | case_id 必须属于 T01..T08。D01..D10B、baseline 与 T09/T10 一律不得作为方法卡容器。 | 由 case_id enum 保证（且 schema 已拒绝 D/baseline/T09/T10） |
| 32 | `physical_consequence_required` | physical_consequence 必填且为单值；它直接决定 scoring.md §1.2 的 I_physical。 | 由 required 列表 + physical_consequence.enum 保证 |

## 3. 登记缺口（3 条）

| # | rule_id | 规则摘要 | 为什么现在实现不了 | 解除条件 |
|---|---|---|---|---|
| 18 | `per_dimension_table_in_report` | dimensions 长度 >= 2 时，该卡的报告必须逐维出表；CI 校验报告产物中存在 per-dimension 表，仅含聚合标量的报告拒绝发布。 | 需要报告产物；报告器属二期 | 报告器落地时 |
| 19 | `index_only_flag` | 任何聚合值必须带 index_only: true 标记；未标记的聚合值不得作为 verdict 依据（D13：benign_fill 端点差 -0.111 判 | 需要报告产物；报告器属二期 | 报告器落地时 |
| 20 | `superseded_removed_from_index` | supersedes 非空时，被作废的旧结论必须从所有活跃报告索引中移除，并在报告头列出 superseded 清单。 | 需要报告索引产物；报告器属二期 | 报告索引落地时 |

## 4. 部分实现的规则（主检查已实现，仍有一处待补）

| # | rule_id | 已实现什么 | 还缺什么 |
|---|---|---|---|
| 26 | `composition_of` | 结构与枚举层面的检查 | composition_of 元素对共享文献池的可解析性待 spec/shared-bibliography 索引化后补 |

## 5. 正反用例

`tests/fixtures/cards/` 下有 **1 套合法 + N 套违规**，每套只破坏一处；生成器是 `tools/gen_card_fixtures.py`。
Gate 1 的 `card_fixtures` 断言：违规样本**全部被拒**、合法样本**通过**。

为什么这是必需的：`methods/` 为空时，所有规则都「通过」——因为无事可做。**一个从不失败的检查等于没有检查。**
