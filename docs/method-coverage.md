# 方法归类总表（`docs/method-coverage.md`）

| 项 | 值 |
|---|---|
| 用途 | 8 个攻击类别会话**各自追加一行/一表**；每张卡的 `(机制, 通道, 手法类, 变换)` 四分量与『是否过可区分判据』必须在此可见 |

| 状态 | **T02 已列出**；**T01 已列出**；其余 6 类待各会话追加 |
| 纪律 | 四分量**逐列填**（不得合并成一列）；`是否过可区分判据` 必须逐行给"是/否 + 理由"（`03-disciplines.md` C4）|

> **本表不含负向断言。** 凡『未收录』一律写成『本次不收录 + 理由』。

---
> **⚠️ 2026-10-01（`docs/` D14）**：各表的「距 30」列**已作废**——「每类 30」的规模目标已取消，不再对着 30 报缺口。表中原值保留作历史记录。


## T02 · 审计与日志破坏（终点资产 = 审计记录 / 可追溯性；`impact_class` = E）

**机制清单（9 个，`min_mechanisms` = 9）** —— 证据等级：`original_table`（已回 PDF 并定位表/图号）

| # | `mechanism_ref` | 机制名 | 通道 `vector` | 手法类 `technique` | 变换 `transform` | 来源论文 | 证据 | 过可区分判据？ | 卡片状态 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `ATK-AUD-01` | 轨迹自删 | 用户输入（对 agent 的指令） | 手工设计 | 无 | arXiv:2609.30266 §2 | original_table | **是**：注入入口=指令、目标资产=trace 存储、机制首步=删除文件，与其余 8 条均不同 | **已落卡** |
| 2 | `ATK-AUD-02` | 执行承载字段改写 | 系统提示词/响应路径 | 参数操纵 | 无 | arXiv:2605.02187 §4-§5 | original_table | **是**：入口=relay 响应路径（唯一非提示词入口），机制首步=改写单个 schema-valid 字段 | **已落卡** |
| 3 | `ATK-AUD-03` | log-substrate 注入 · S2 伪造权威 | 检索文档（日志字段） | 手工设计 | 角色扮演 | arXiv:2605.24421 §3 | original_table | **是**：机制首步=伪造权威主张（原文 §3 与 S3 并列定义） | **已落卡** |
| 4 | `ATK-AUD-04` | log-substrate 注入 · S3 结构模仿 | 检索文档（日志字段） | 手工设计 | semantic | arXiv:2605.24421 §3 | original_table | **是**：机制首步=结构性模仿可信输出；目标资产=摘要输出（与 S2 的分类标签不同） | **已落卡** |
| 7 | `ATK-AUD-07` | 语义规范漂移 + 信任洗白链 | 检索文档（文档上传通道） | 手工设计 | semantic | arXiv:2605.22842 §3 | original_table | **是**：机制首步=经 Trust Laundering Chain 使 provenance 丧失；目标资产=归因结论 | **已落卡** |
| 8 | `ATK-AUD-08` | 紧凑事实伪装绕过输入审计 | 记忆写入（仅查询） | 自动生成 | semantic | arXiv:2608.03844 §3 + Table 1 | original_table | **是**：机制首步=memory probing + 预算分配使注入具检索竞争力；其卖点是绕过 input audit | **已落卡** |
| 9 | `ATK-AUD-09` | 日志解读逃逸 | 检索文档（日志条目） | 手工设计 | semantic | arXiv:2607.24174 §4 + Table 1 | original_table | **待写卡时判定**：与 #3/#4/#10 同属 log-injection，须逐条比对载荷与判据 | **已落卡** |
| — | ~~`ATK-AUD-12`~~ | ~~trust-level 降级即抑制~~ | 配置（分级策略） | 手工设计 | 无 | IETF draft-sharif-agent-audit-trail-06 §5.3 | none（无实验） | **不收录**：无独立论文、无实验 ⇒ 按 `00-mission.md` §3 第 4 条不计方法（不是负向断言） | 不收录 |

**同论文内不收录的载荷变体**（`03-disciplines.md` C1/C7 的执行）：

| 变体 | 所属论文 | 不收录理由（原文数字） |
|---|---|---|
| S1 Direct Override | arXiv:2605.24421 | 分类任务抑制率 **0.00**（原文摘要与 Table 2） |
| S4 Obfuscated Payload | arXiv:2605.24421 | 摘要任务 **SR 0.00 / ISR 0.00**（Table 2） |

**本类计数**（两个口径分别报告，`03-disciplines.md` C8）：

| 口径 | 值 |
|---|---|
| 机制数（主口径，`min_mechanisms`） | **9**（保守口径；乐观口径 11，见下） |
| 方法数（辅助口径） | **9**（无变体卡） |
| 距 30 的缺口 | 21（保守口径）；19（乐观口径） |

> **计数说明（9 与 11 分别怎么来的）**：本类共收录 **11** 个机制（上表 #1–#11）。
> 其中 `ATK-AUD-05`（终点或为动作路由 T04）与 `ATK-AUD-06`（终点或为记忆 T01）**终点资产可能不属本类**，
> ⇒ 于是有两个口径，**两个都报**（`03-disciplines.md` C8 精神）：
> · **保守 9** = 11 − 2（假定这两条最终外流到 T04 / T01）
> · **乐观 11** = 全部 11 条都过谓词
> `manifest.json` 的 `min_mechanisms` 取**保守值 9**，避免用乐观值掩盖不确定性。
> 另：`ATK-AUD-12`（IETF 草案的 trust-level 降级抑制）**不计入任何口径**——无独立论文、无实验。

---

## T01 · 知识库与记忆投毒（终点资产 = 知识库 / 长期记忆；`impact_class` = B）

**机制清单（27 个去重方法，`min_methods` = 27 / `min_mechanisms` = 27）** —— 卡片 28 张；其中两张同 `mechanism_ref` 的档位卡（PoisonedRAG 黑/白盒）在五轴上重合 1 张（重合率 3%）。

| 项 | 值 |
|---|---|
| 方法-类别实例数 | 28 |
| 去重方法数 N | **27** |
| 距 30 | **3** |
| `EXT-` 占比 | **0.0%（0/28）** |
| 来源等级分布 | `S 9 / A 12 / B 7` |
| `allow_text_fallback` | false |

| # | `method_id` | 机制 ref | 通道 `vector` | 手法类 `technique` | 变换 `transform` | `provenance_kind` | 过 C4/C11？ |
|---|---|---|---|---|---|---|---|
| 1 | `T01.LIT-B-25.select_existing_vulnerable_sample` | LIT-B-25 | 检索文档 | 手工设计 | 无 | interpolation | 是（基准卡） |
| 2 | `T01.LIT-B-26.benign_fragment_decomposition` | LIT-B-26 | 检索文档 | 手工设计 | 无 | composition | 是（机制首步） |
| 3 | `T01.LIT-B-44.retriever_guided_word_refinement` | LIT-B-44 | 检索文档 | 自动生成 | 无 | interpolation | 是（机制首步） |
| 4 | `T01.LIT-B-27.reward_subspace_projection` | LIT-B-27 | 检索文档 | 自动生成 | 无 | interpolation | 是（机制首步） |
| 5 | `T01.LIT-B-28.perturbation_triple_insertion` | LIT-B-28 | 检索文档 | 自动生成 | 无 | interpolation | 是（机制首步） |
| 6 | `T01.LIT-B-37.graph_topology_integrity` | LIT-B-37 | 检索文档 | 自动生成 | 无 | interpolation | 是（机制首步） |
| 7 | `T01.LIT-B-36.cluster_pgd_multimodal` | LIT-B-36 | 检索文档 | 自动生成 | 编码 | interpolation | 是（机制首步） |
| 8 | `T01.LIT-B-38.local_global_dual_path` | LIT-B-38 | 检索文档 | 自动生成 | 编码 | interpolation | 是（机制首步） |
| 9 | `T01.LIT-B-35.visual_sleeper_memory` | LIT-B-35 | 记忆写入 | 具身与多模态 | 编码 | interpolation | 是（机制首步） |
| 10 | `T01.LIT-B-31.coordinated_beam_search` | LIT-B-31 | 检索文档 | 自动生成 | 无 | interpolation | 是（机制首步） |
| 11 | `T01.LIT-B-32.word_level_trigger` | LIT-B-32 | 检索文档 | 自动生成 | 编码 | interpolation | 是（机制首步） |
| 12 | `T01.LIT-B-39.single_doc_adversarial_cot` | LIT-B-39 | 检索文档 | 自动生成 | 无 | interpolation | 是（机制首步） |
| 13 | `T01.LIT-B-40.embedding_space_optimization` | LIT-B-40 | 检索文档 | 自动生成 | 无 | interpolation | 是（机制首步） |
| 14 | `T01.LIT-B-41.single_poison_overpower` | LIT-B-41 | 检索文档 | 自动生成 | 无 | interpolation | 是（机制首步） |
| 15 | `T01.LIT-B-29.deceptive_semantic_reasoning` | LIT-B-29 | 检索文档 | 自动生成 | 无 | interpolation | 是（机制首步） |
| 16 | `T01.LIT-B-43.category_oriented` | LIT-B-43 | 检索文档 | 自动生成 | 无 | interpolation | 是（机制首步） |
| 17 | `T01.LIT-B-30.persistent_memory_write` | LIT-B-30 | 记忆写入 | 手工设计 | 外壳模板 | interpolation | 是（机制首步） |
| 18 | `T01.LIT-B-34.link_injection` | LIT-B-34 | 检索文档 | 手工设计 | 无 | interpolation | 是（机制首步） |
| 19 | `T01.ATK-MEM-01.embedding_trigger_backdoor` | ATK-MEM-01 | 记忆写入 | 自动生成 | 无 | interpolation | 是（目标资产） |
| 20 | `T01.ATK-MEM-02.blackbox_knowledge_corruption` | ATK-MEM-02 | 检索文档 | 自动生成 | 无 | interpolation | 是（机制首步） |
| 21 | `T01.ATK-MEM-02.whitebox_knowledge_corruption` | ATK-MEM-02 | 检索文档 | 自动生成 | 无 | interpolation | 是（机制首步） |
| 22 | `T01.ATK-MEM-03.query_only_memory_injection` | ATK-MEM-03 | 用户输入 | 多轮分阶段 | 无 | interpolation | 是（注入入口） |
| 23 | `T01.ATK-INJ-01.retrieval_corpus_ipi` | ATK-INJ-01 | 检索文档 | 手工设计 | 无 | interpolation | 是（注入入口） |
| 24 | `T01.ATK-INJ-02.remote_resource_ipi` | ATK-INJ-02 | 检索文档 | 手工设计 | 无 | interpolation | 是（注入入口） |
| 25 | `T01.ATK-INJ-03.persistent_memory_ipi` | ATK-INJ-03 | 记忆写入 | 手工设计 | 外壳模板 | interpolation | 是（注入入口） |
| 26 | `T01.ATK-INJ-04.agent_to_agent_ipi` | ATK-INJ-04 | 智能体间消息 | 手工设计 | 无 | interpolation | 是（注入入口） |
| 27 | `T01.ATK-INJ-12.self_replicating_worm` | ATK-INJ-12 | 智能体间消息 | 自动生成 | 无 | interpolation | 是（机制首步） |
| 28 | `T01.ATK-MAS-01.single_image_jailbreak` | ATK-MAS-01 | 记忆写入 | 具身与多模态 | 编码 | interpolation | 是（机制首步） |

### 未归入本类（跨类 / 非攻击 / 无法归类）

| 来源 | 处置 |
|---|---|
| B-30 SpAIware（FGCS 2026） | 通道属 T01（持久记忆），终点资产疑为凭据/数据 ⇒ **副类 T08，主类待 κ** |
| B-42 RAGOrigin（IEEE S&P 2026） | **防御/归因框架**，按 C6 不计方法；收录供判据层对照 |
| B-33 Uncovering Competing Poisoning Attacks（KDD 2026） | 多攻击者竞争设定落 `dimensions`，贡献含 PoisonArena 基准 ⇒ **不计方法** |
| WWW'24 联邦知识图谱嵌入投毒 | 终点为联邦 KGE、不面向 agent 知识库 ⇒ 记为 **`unassigned`**（计数 1），登记 `ROADMAP.md` |
