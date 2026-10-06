# 目标画像（`targets/`）

| 项 | 值 |
|---|---|
| 用途 | 存放 **TargetProfile**（目标画像）。`spec/target-profile.schema.json` 是权威 schema；`cardcheck` 对每个 `*.json` 做结构校验 |
| 消费者 | `cardcheck` 规则 17（适用性覆盖）· `score/prior.py`（先验分需要画像）· runner |
| 状态 | 2026-10-01 **第一份画像登记**（此前本目录为空，规则 17 恒报"不可判"） |

## 1. 已登记的画像

| `target_id` | 类型 | 说明 |
|---|---|---|
| `agentdojo-workspace` | 开源参考靶标 | AgentDojo `workspace` suite。`docs/` **D15** 定为一期首选靶场 |
| `injecagent-toolkits` | 公开基准的工具集（**纸面画像**） | InjecAgent（`uiuc-kang-lab/InjecAgent`）的 38 个 toolkit / 330 个工具名。**本仓库没有它的适配器 ⇒ 只出先验分，不出实测分**。工具清单由 本项目取证记录 按该仓库自己的命名规则（`src/utils.py:124`）导出，再经**机械** snake_case 归一化（schema 要求 `^[a-z][a-z0-9_]*$`） |
| `poisonedrag-rag-pipeline` | 公开基准的评测管线（**纸面画像**） | PoisonedRAG（USENIX Sec 2025，`sleeepeer/PoisonedRAG`）的 RAG 管线：BEIR 语料 + 稠密检索器 + 生成。**只出先验分，不出实测分**。工具名取**代码自己的符号**（`encode_corpus` / `encode_queries` / `wrap_prompt` / `query`），由 本项目取证记录 **逐条回源校验**（上游一改就构建失败）。<br>⚠️ **污染风险**：T01 有 2 张卡把 PoisonedRAG 本身当机制来源 ⇒ 该方法是针对这个目标调过的，**任何实测结论都不得基于它** |

> **为什么补这份 RAG 画像**：反事实分析（本项目取证记录）算出，
> 在另两份画像之上**只差 `knowledge_retrieve` 一个动作的卡有 16 张**（T01×15 + T07×1），
> 是全部候选能力里最大的一条；而这些卡的前置条件多为 `{action:2, tool:2}` ——
> 按 设计规格 §4.5.1 的 Kim 三档定义，`action=2` 恰好就是"响应 + 检索"，即 RAG 的形状。
> ⇒ 补这份画像让三份合计覆盖从 **25 → 40** 个不同方法。

> ⚠️ `targets/capability-aliases.yaml` **不是画像**，见 §2.4。它故意不用 `.json`，
> 因为 `cardcheck` 用 `targets/**/*.json` 收画像并逐份做 schema 校验。

## 2. 加一份画像时的三条硬要求

1. **工具清单必须直读目标源码**，不得凭印象或转述。`agentdojo-workspace` 的 24 个工具是**解码 `default_suites/v1/workspace/task_suite.py` 的 `TOOLS` 列表**得到的（不是从论文摘要抄的），并与 `docs/benchmark-matrix.md` 的"24 个工具 / 10 个 consequential"两个数字交叉对上。
2. **`model` 未 pin 前不得开跑。** 本项目的复现纪律要求 pin 版本 + 哈希（设计决策记录 B2）；AgentDojo 是模型无关框架，故画像里该字段标 `[待 pin]`。
3. **`cleanup_supported` / `receipt_supported` 要如实填 `false`。** 填 `false` 的后果是相关结论只能记 `inconclusive`——**那是正确行为，不是缺陷**。为了"让结论好看"而填 `true` 是本项目最不能接受的一类错误。

### 2.4 加了画像还不够：还要写**能力对齐**

**只加画像提不了覆盖率。** 实测：全库 152 个 `required_actions` 名字里，与 AgentDojo 的
26 个工具名**逐字相同的只有 3 个**（`user_turn` / `response_generate` / `send_email`）。
⇒ 纯字符串口径下，"适用性"取决于**巧合**；再多的画像也救不了。

故加一份画像要同时写 `targets/capability-aliases.yaml` 里的一段：

| 要写什么 | 纪律 |
|---|---|
| `capabilities[].source` | **目标侧机制证据**（源码文件 + 符号），不引论文摘要或转述 |
| `capabilities[].reason` | 为什么该机制**足以承载**卡上的那一步 |
| `excluded[]` | 目标**不具备**的能力族 + 理由。**不写排除项等于默认全都通** |

**别名只增加"结构上可行"**（`spec/prior.md` V6 那一问），不改变六态语义：
投放面/观测装置是否具备是另一回事（D17：投失败记 `untested`、装置不足记 `not_applicable`）。

⚠️ **两个覆盖率必须并列报告**：`cardcheck` 规则 17 是**纯字符串口径**（不认别名），
`score/targets.py` 是**展开口径**。只报大的那个 = 隐瞒了口径。

> 这是**临时机制**。真正的修法是给 `required_actions` 定受控词表（`ROADMAP.md` **G-3**）。

## 3. ⚠️ 两个必须知道的实测发现（2026-10-01）

### 3.1 `required_actions` **没有受控词表**

加入第一份画像后，规则 17 由"不可判"变为可判，给出：

```
targets/agentdojo-workspace  适用性覆盖：20/186 张卡的 required_actions ⊆ 本目标 tools；
                             166 张在本目标上记 untested（缺 149 种动作）
```

**恰好 20** —— 与 `docs/benchmark-matrix.md` §3 的独立预测（"57 个方法里能跑约 20 个，且全部来自 T06"）**对上了**：卡从 57 涨到 186，能跑的仍是同一批 20 张（全在 T06）。

原因不是一个类"更好"，而是 **T06 的 `required_actions` 只有 2 个值**（`user_turn` / `response_generate`），恰好落在任何 agent 都有的通用动作上。全库实测：

| 项 | 值 |
|---|---|
| 不同动作名 | **152 个** |
| (卡, 动作) 组合 | 506 |
| 只在单一类别内出现的动作名 | **141 个** |
| 跨类共用的动作名 | 11 个（`agent_message` / `tool_call` / `tool_list` / `memory_write` / …） |
| 单类词表最大者 | **T04：46 个** |

⇒ **该字段目前既不可跨类比较，也不与任何真实目标的工具清单挂钩。** 规则 44 只查格式 `^[a-z][a-z0-9_]*$`，查不出这一点。
**这是一处已登记的结构性缺口，不是任何类别会话的过错**（各会话互不可见，各自发明了合理的动作名）。

### 3.2 规则 17 原先把"不适用"报成了 ERROR（**已修**）

第一版把"卡的 `required_actions` 不在目标 tools 里"报 **ERROR**，而它自己的文案写着"该卡在此目标上应记 `untested` 而非 `fail`"。
**`untested` 是六态之一（R1/R2），是"测不了"，不是"卡错了"。** 实测触发时报出 **448 条 ERROR**，逐条看全是 `untested`。
已改为**逐目标报适用性覆盖计数（INFO）**，不报 ERROR；`required_actions` 的**格式**问题仍由规则 44 管。

## 4. "无攻击者"的靶场只能当靶场，不能当方法来源

SafeAgentBench（`2412.13178`）· Nuclear Deployed（`2502.11355`）· Defining and Evaluating Physical Safety（`2411.02317`）三者，
其危害**来自用户指令本身**，原文明确 *without instruction or induction by an attacker*（见 `ROADMAP.md` A-2）。
⇒ 它们**可以登记为目标画像**（提供靶场），但**不得作为方法来源**（无独立攻击构造，过不了 C11）。
**加画像时不要把这两件事混起来。**

## 5. 相关文档

- `docs/benchmark-matrix.md` —— 八类 × 候选靶场匹配矩阵（哪些类有靶场、哪些没有）
- `docs/benchmark-matrix.md` —— AgentDojo 可行性评估（结构性障碍、三处口径缺口、依赖顺序）
- `docs/` **D15** —— 把实测结果纳入交付，以及 "benchmark" 一词的解除条件