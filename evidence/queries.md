# 检索协议与检索式（Search protocol and queries）

本文件由 `manifest.json` 的原始归档条目直接导出，检索式与命中数为归档中的原文。

## 一、文献侧：6 个源，5 轮，共 21 个检索式

| 轮 | 取向 | 检索式 | 去重命中 | 源不完整 |
|---|---|---|---|---|
| 1 | 按名称 | `garak LLM vulnerability scanner`；`PyRIT Python Risk Identification Tool generative AI`；`promptfoo LLM red teaming evaluation`；`DeepTeam red teaming framework large language models`；`Agent Security Bench attacks defenses LLM-based agents` | 47 | openaire |
| 2 | 按能力 | `open source library of prompt injection attacks for LLM agents`；`attack toolkit for tool-calling LLM agents`；`collection of adversarial attacks against LLM agents benchmark`；`agent security evaluation framework paired control arms` | 76 | openaire |
| 3 | 换措辞 | `attack method taxonomy for agentic AI systems`；`reproducible adversarial prompt library tool-calling agents`；`agent red teaming benchmark open source code` | 37 | 无 |
| 4 | 按后果终点 | `memory poisoning attack LLM agent`；`audit log tampering LLM agent`；`tool metadata poisoning MCP server`；`data exfiltration tool calling LLM agent`；`resource exhaustion denial of service LLM agent` | 105 | openaire |
| 5 | 按评测方法学 | `paired control evaluation attack success rate LLM agents`；`benchmark attack success rate tool-using LLM agents reproducibility`；`deterministic judge evaluation adversarial LLM agent`；`evidence bundle reproducible evaluation LLM security` | 45 | dblp、openaire |

## 二、仓库侧：元数据取向

| 来源 | 检索式 | 命中 |
|---|---|---|
| GitHub | `agent security attack` | 967 |
| GitHub | `mcp attack poisoning` | 74 |
| GitHub | `prompt injection tool-calling agent` | 72 |
| GitHub | `topic:agent-security` | 1786 |
| GitHub | `awesome agent security` | 151 |
| GitHub | `agent red team benchmark` | 54 |
| GitHub | `topic:mcp-security` | 519 |
| GitHub | `topic:llm-security agent attack` | 224 |
| GitHub | `agent attack method library` | 2 |
| GitHub | `tool poisoning benchmark` | 18 |
| github-topic | `topic:prompt-injection` | 5086 |
| github-topic | `topic:llm-security` | 4280 |
| github-topic | `topic:adversarial-attacks` | 1251 |
| github-topic | `topic:agentic-security` | 82 |
| github-topic | `topic:ai-security-tool` | 144 |
| gitee | `智能体攻击` | None |
| gitee | `提示注入` | None |
| gitee | `大模型安全评测` | None |
| pypi-simple-index | `None` | None |
| GitHub | `"attack method library"` | None |
| GitHub | `"method cards" attack agent` | None |
| GitHub | `"attack catalog" LLM` | None |
| GitHub | `"paired control arm"` | None |
| GitHub | `"benign control arm" injection` | None |
| GitHub | `"attack methods" "tool-calling"` | None |
| GitHub | `"indirect prompt injection" "ground truth" dataset` | None |
| GitHub | `"literature" "attack methods" agent benchmark` | None |

## 三、代码级检索（认证调用）

| 检索式 | 命中 |
|---|---|
| `"attack method library"` | 6 |
| `"method cards" attack agent` | 128 |
| `"attack catalog" LLM` | 936 |
| `"paired control arm"` | 95 |
| `"benign control arm" injection` | 26 |
| `"attack methods" "tool-calling"` | 255 |
| `"indirect prompt injection" "ground truth" dataset` | 3224 |
| `"literature" "attack methods" agent benchmark` | 4536 |

## 四、与本次检索相关的口径

- 逐检索式记录各源命中数；**未答全的源如实入档**（超时与限流不隐去）。
- 收录判据：该工件自身为一套攻击方法集合，且可与"对象与覆盖 / 描述与脚本 / 实测与可信度"三点逐点对照；靶场（环境层）、防御（规则层）、综述与清单仅作分层登记，不作同类比较。
- 核实方式：逐一读取入选仓库的 README、文件树与关键源文件；不依据项目自述作结论。
- 表述纪律：结论一律写作"在本次检索范围内未检索到"，不表述为"不存在"。

