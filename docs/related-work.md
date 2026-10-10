# 检索证据：智能体攻击方法集的同类工作检索

**检索基准日**：2026-10-06。星数、仓库结构与推送日均为该日读数。

**本文件回答的问题**：公开文献与公开工件中是否已有同类工作，即**面向智能体的攻击方法集**。

**同类判定标准**（三条，缺一不可）：

- **对象与覆盖**：面向工具调用型智能体，后果落在记忆、审计记录、权限、控制面、工具定义、系统提示、服务可用性与业务数据；且类别足够广、方法足够多。
- **描述与脚本**：每条方法一份描述（含公开出处）配一个可执行脚本，成对存在。
- **实测与可信度**：是否完成实测、结论能否被第三方检验；确定性判定规则、同任务对照臂、逐次证据留存与离线复算均计入本条。

**边界**：靶场（环境）类工作不属同类——其产出为场景、任务与运行环境，攻击在其中是环境自带的注入点或评测项，不是可逐条引用的方法资产。故下文将靶场、大模型红队工具、防御与综述一并单列，只说明关系。

---

## 一、检索方式

**文献源 6 个**：Crossref、DBLP、arXiv、OpenAIRE、Europe PMC、OpenAlex。逐检索式记录各源命中数；未答全的源如实入档（超时与限流不隐去）。

**文献侧 5 轮 21 个检索式**：

| 轮 | 取向 | 检索式 | 去重命中 | 源不完整 |
|---|---|---|---|---|
| 1 | 按名称 | `garak LLM vulnerability scanner`；`PyRIT Python Risk Identification Tool generative AI`；`promptfoo LLM red teaming evaluation`；`DeepTeam red teaming framework large language models`；`Agent Security Bench attacks defenses LLM-based agents` | 47 | OpenAIRE |
| 2 | 按能力 | `open source library of prompt injection attacks for LLM agents`；`attack toolkit for tool-calling LLM agents`；`collection of adversarial attacks against LLM agents benchmark`；`agent security evaluation framework paired control arms` | 76 | OpenAIRE |
| 3 | 换措辞 | `attack method taxonomy for agentic AI systems`；`reproducible adversarial prompt library tool-calling agents`；`agent red teaming benchmark open source code` | 37 | 无 |
| 4 | 按后果终点 | `memory poisoning attack LLM agent`；`audit log tampering LLM agent`；`tool metadata poisoning MCP server`；`data exfiltration tool calling LLM agent`；`resource exhaustion denial of service LLM agent` | 105 | OpenAIRE |
| 5 | 按实测方法学 | `paired control evaluation attack success rate LLM agents`；`benchmark attack success rate tool-using LLM agents reproducibility`；`deterministic judge evaluation adversarial LLM agent`；`evidence bundle reproducible evaluation LLM security` | 45 | DBLP · OpenAIRE |

合计去重命中 310 条。Crossref 每式返回上限 40 条，命中数不等于相关条数；文献源命中者基本为有论文的工作，工具与方法库类工件几乎不出现。

**仓库侧 16 组元数据取向**：

| 取向 | 结果总数 | 代表性命中 |
|---|---|---|
| `agent security attack` | 967 | `gadievron/raptor`（★3876）· `capitalone/VulnHunter`（★1082）· `ethz-spylab/agentdojo`（★899） |
| `mcp attack poisoning` | 74 | `adithyan-ak/AgentHound`（★446）· `Agent-Threat-Rule/agent-threat-rules`（★409） |
| `prompt injection tool-calling agent` | 72 | `StackOneHQ/defender`（★126）· `pie-script/llm-agent-testbed`（★16） |
| `topic:agent-security` | 1786 | `NVIDIA/SkillSpector`（★19745）· `Tencent/AI-Infra-Guard`（★6799）· `msoedov/agentic_security`（★2019） |
| `awesome agent security` | 151 | `scadastrangelove/awesome-ai-security-tools`（★1596） |
| `agent red team benchmark` | 54 | `Yeti-791/Awesome-Offensive-AI-Agentic-Landscape`（★344）· `msaleme/red-team-blue-team-agent-fabric`（★32） |
| `topic:mcp-security` | 519 | `nolabs-ai/nono`（★4410）· `stacklok/toolhive`（★2259） |
| `topic:llm-security agent attack` | 224 | `adithyan-ak/AgentHound`（★446）· `getagentseal/agentseal`（★377） |
| `agent attack method library` | 2 | 无相关命中 |
| `tool poisoning benchmark` | 18 | `AI45Lab/OpenART`（★232）· `zhiqiangwang4/MCPTox-Benchmark`（★13） |

另按"定位措辞 + 更新时间"补检 6 个取向（`attack library LLM agents` · `attack suite agent security` · `adversarial attack collection LLM` · `attack catalog prompt injection` · `agent attack methods` · `llm attack toolkit benchmark`），命中者多为 ★0–3 的小项目。

**代码级检索 8 个检索式**（认证调用），用于发现藏于其他仓库子目录或文档正文中的方法集：

| 检索式 | 命中 | 代表性命中 |
|---|---|---|
| `"attack method library"` | 6 | 全部指向同一项目（`Tencent/AI-Infra-Guard`）的 prompt-eval 文档及其副本仓库 |
| `"method cards" attack agent` | 128 | `carbonphysicsai/Carbon` |
| `"attack catalog" LLM` | 936 | `icdev-ai/icdev` |
| `"paired control arm"` | 95 | `AgentEvalHQ/AgentEval` |
| `"benign control arm" injection` | 26 | `provael/provael` · `QuantaMinds/QuantaMind` · `sattyamjjain/agent-airlock` |
| `"attack methods" "tool-calling"` | 255 | `LLMSecurity/awesome-agent-skills-security` · `Tencent/AI-Infra-Guard` |
| `"indirect prompt injection" "ground truth" dataset` | 3 224 | `Abraheem13/iobnt-agentjack` · `ydyjya/Awesome-LLM-Safety` |
| `"literature" "attack methods" agent benchmark` | 4 536 | 以清单与综述类仓库为主 |

**其它源**：GitHub topics 长尾 5 组（`prompt-injection` · `llm-security` · `adversarial-attacks` · `agentic-security` · `ai-security-tool`）；PyPI 全量包名索引 908 422 条，按"智能体相关且攻击相关"收紧后得 58 个候选，逐一核实；Gitee 同一批检索式返回空；HuggingFace 本机不可直连，仅经外部检索间接覆盖。

**核实方式**：逐一读取入选仓库的 README、文件树（含目录级计数）与关键源文件；不依据项目自述作结论。逐检索式的原始响应按轮次归档，检索式可逐条重跑。

---

## 二、检出结果与差异

### 2.1 不同层的工作

- **大模型红队工具**（garak、promptfoo、PyRIT、DeepTeam；HarmBench、StrongREJECT 等越狱评测）：用途是检测**模型输出的内容安全**（越狱、有害内容、提示泄露），不涉及智能体调用工具之后的后果——记忆写入、审计删改、权限绕过、控制面调用。
- **靶场**（AgentDojo、Agent Security Bench、InjecAgent、CyberGym）：用途是提供任务与环境，供不同智能体或防御在同一场景下比较；攻击是环境自带的注入点，且多只覆盖提示注入一条通道。CyberGym 评测的是"智能体能否挖出真实漏洞"（1507 个 C/C++ 任务），对象为能力，而非被攻击面。
- **防御**（Agent-Threat-Rule、Janus、agent-airlock）：用途是拦截，在防御侧，不提供攻击方法。
- **综述与清单**（Kim 2026 SoK、Wu、Deng、AgentAtlas；各类 awesome 清单）：用途是综述与索引，无实现、无实测。

### 2.2 同层对象（六家）

| 项目 | 它是什么，为什么不是同类 |
|---|---|
| `msaleme/red-team-blue-team-agent-fabric`（★32） | 面向**已部署**智能体的安全验收与合规留痕命令行工具，用于判定部署能否通过验收、合规证据是否齐备。非攻击方法库：测试按协议域（MCP / A2A / x402）组织，未核实到逐条文献出处与逐次证据复算 |
| `aminrj-labs/mcp-attack-labs`（★21） | 教学实验合集，每 lab 含脆弱靶标、一个攻击与对应防御；用途是教学演示 |
| `invariantlabs-ai/mcp-injection-experiments`（★206） | 随研究发布的复现片段；用途是可行性演示，仅覆盖间接提示注入 |
| `pie-script/llm-agent-testbed`（★16） | 面向自建智能体的抗攻击回归测试床（按已知真值判分）；用途是版本回归验证 |
| `Samgar-kz/agentprobe`（★0，PyPI `agentprobe-injection`） | 面向**防御**的长期回归工具，用于观测防御随时间的强弱变化；攻击目录由 intents × transforms 组合生成，仅覆盖间接注入 |
| `sentinelden/agent-injection-bench`（★0，PyPI） | 提示注入基准与打分框架，报告攻陷率与过度拒绝率；仅覆盖提示注入 |

### 2.3 检出但不属同类

| 项目 | 它是什么，为什么不是同类 |
|---|---|
| `AgentEvalHQ/AgentEval`（★155） | **用途是智能体能力与质量评测**（工具调用合规性、RAG 质量、模型对比），非攻击；其中 `paired control arm` 为其确定性代码评测的统计手法 |
| `sattyamjjain/agent-airlock`（★16） | **用途是拦截不合规的工具调用**（默认拒绝的类型检查与契约层），在防御侧 |
| `QuantaMinds/QuantaMind`（★15） | **用途是评测自托管大模型承载智能体的能力**，与攻击无关 |
| `provael/provael`（★7） | **用途是红队 VLA 机器人策略并报告攻击成功率**；域为机器人控制，非 LLM 智能体。方法学上已用良性对照与 95% Wilson 区间，须同报 |
| `icdev-ai/icdev`（★5） | **用途是 SDLC 与合规自动化**（NIST 800-53、FedRAMP 等）；红队仅为其产品内的一份 YAML 清单 |
| `Abraheem13/iobnt-agentjack`（★0） | **用途是研究生物纳米（IoBNT）分子通信信道中的提示注入**，域为分子通信 |
| `LLMSecurity/awesome-agent-skills-security`（★245） | **用途是资源索引**（清单），无实现 |

### 2.4 三点对照

| 工作 | ① 智能体攻击方法覆盖（类别 / 数量） | ② 方法描述与脚本 | ③ 实测与可信度 |
|---|---|---|---|
| **本工作** | **8 类 / 188 条**（每类 17–29 条；按后果终点划分；逐条登记公开出处） | **每条一描述 + 一脚本，188 : 188** | **237 个评测单元实测**；12 类确定性判定规则；同任务对照臂；逐次证据留存，离线复算 143 / 152 |
| red-team-blue-team-agent-fabric | 按协议 / 域 / 属性组织，非攻击类别轴 | 测试即脚本；未核实到逐条文献出处 | 有 PASS / FAIL / INCONCLUSIVE 与目标形态哨兵；未核实到逐次证据复算 |
| mcp-attack-labs | 9 个教学 lab | 每 lab 有攻击脚本；无逐条出处 | 无 |
| mcp-injection-experiments | 3 个复现片段 | 有脚本，无描述 | 无 |
| llm-agent-testbed | 5 类 × 1–2 用例 | 用例即代码 | 真值判分；无实测记录 |
| agentprobe | 单一注入类型（组合生成） | 有生成器；无逐条描述 | 两条判定信号（金丝雀、未授权外发）；无证据复算 |
| agent-injection-bench | 单一注入类型 | 数据集 + harness | 报告两个独立比率；无证据复算 |

![图 1](figures/related-work-matrix.png)

**计数单位不可比**：本工作的 188 是"逐条对应一篇公开文献中的一个具体攻击机制"；上面 640 是"可执行测试"；DeepTeam 的 20+ 是"攻击策略"（还需乘 50+ 漏洞类别）；garak 的 ≈66 是"探针类"；promptfoo 的 157 是"风险类别插件"；ASB 的 ≈16 是"benchmark 内的攻击实例"。**不同单位不可直接比大小。**

---

## 三、结论

**① 智能体攻击方法**：按攻击类别组织且规模达 8 类 188 条者，本次检索未检出第二家。同层对象按用途可分三类——面向已部署智能体的验收与回归（red-team-blue-team-agent-fabric、llm-agent-testbed）、面向防御的回归（agentprobe）、教学与演示（mcp-attack-labs、mcp-injection-experiments）——另有单一注入类型的基准（agent-injection-bench）；**均非以汇总攻击方法为目的的方法库**，规模亦不在同一量级（9 个 lab、3 个片段、5 类用例）。文献中的智能体攻击研究多依附靶场出现（AgentDojo、Agent Security Bench、InjecAgent 等），攻击为环境的组成部分且以提示注入为主；将其中机制逐条剥离为可引用、可执行、可判定的资产，是另一件事。

**② 每条方法一份描述与一个脚本、1:1 对应**：未检索到同类做法。同层对象或"测试即脚本"，或"有脚本、无逐条描述"，或仅为数据集与运行框架。

**③ 实测与可信度**：未检索到同时具备确定性判定、同任务对照臂、逐次证据留存与离线复算的同类工作。最接近的两家各具其一——`llm-agent-testbed` 采用真值判分而非模型打分，`red-team-blue-team-agent-fabric` 具备目标形态哨兵与工件校验——均未见逐次证据的离线复算。

**须同报**：VLA 机器人策略域已有工作（`provael/provael`）以"良性对照 + 95% Wilson 区间"报告攻击成功率，并给出跨来源可比性标准。故对照臂与区间估计本身不构成本工作的差异；实测可信度的主张落在确定性判定规则、逐次证据留存与离线复算。

**本工作的不足**：

- 方法条目 188 条中，可在现有被测系统投放者 69 条、已完成实测者 26 条；**约七成条目尚未实测**。
- 单条方法样本量多为 5–10 次；可估计区间的 126 个评测单元中，仅 79 个差值区间不含零，其余不主张有效果。
- **判定规则自身的判别力尚未校验**（未以人为设定成败的目标形态逐条验证其能判对亦能判错），为可信度链条上唯一的空缺。
- 离线复算中 9 个评测单元结果不一致；3 个单元因被测系统缺少独立读回通道而判定不可用。
- 被测系统独立来源两个（自建与公开各一）；跨靶标不合并。

![图 2](figures/measurement-funnel.png)

**结论边界**：Crossref 单次返回上限 40 条；OpenAIRE 在第 1、2、4、5 轮部分失败，DBLP 在第 5 轮部分失败；最近同层对象由第 10 个仓库取向检出，`attack method library` 的代码级命中 6 条且全部指向同一项目。故以上结论限定为"**在本次检索范围内未检索到**"，不表述为"不存在"，亦不使用"首个 / 唯一"等措辞。凡"未核实到"的判断，依据限于公开文档与仓库目录结构，未逐文件审计实现代码；代码级检索覆盖 GitHub 已索引的公开仓库默认分支，结果按相关度截断。上游读数可变，星数与仓库结构以基准日为准。