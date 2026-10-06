# T07 非方法件登记（`methods/T07/CONTROLS.md`）

| 项 | 值 |
|---|---|
| 用途 | 登记**收录但不计方法数**的文献（防御 / 检测 / 分类学 / 综述），使"为什么本类 24 而不是 26"可被复核 |
| 为什么**不写成卡** | `tools/cardcheck.py` 与 `tools/count_identity.py` 用 `methods_dir.rglob(\"*.y*ml\")` 递归扫**整个 `methods/`**（实测：放到 `methods/T07/controls/` 仍被计入，T07 一度被算成 28 个方法）⇒ 写成卡会让本类方法数**虚高 2**，违反 R3（`not_applicable`/不计项与计入项必须分开数）。故按纪律**不落 YAML**，改在本文件登记 |
| 依据 | `docs/judgment-discipline.md` **C5 / C6**；`docs/method-identity`… 见 本项目取证记录 §四 |

## 1. 不计方法的已收录文献

| bib_id | 题名 | venue | 性质 | 为什么计 0 | 直读到的证据 |
|---|---|---|---|---|---|
| **B-140** | SHIELD: An Auto-Healing Agentic Defense Framework for LLM Resource Exhaustion Attacks（arXiv `2601.19174`） | arXiv 2026 | **防御框架** | C5/C6：防御件不是攻击方法 | 多智能体 + 三阶段防御 + 提示优化器（Fig. 2/3）；防御侧延迟表 Table 2 |
| （未占号） | **OllamaDrama: Designing and Deploying a Honeypot to Measure Attacks on Exposed LLM Infrastructure**（arXiv `2609.29757`） | arXiv 2026 | **蜜罐测量** | 测量研究不是攻击构造（C5/C6） | 4 个部署 · **84 天** · **290,887 次交互** · **2,793 个源 IP**；自陈观测到 model management abuse / path traversal / SSRF / RCE / **resource exhaustion attempts** / prompt injection / agent-oriented tool use（Table 5 含 MITRE ATLAS 映射）。**它是本类的生态验证证据**：资源耗尽在野外真实发生 |
| **B-141** | When Agents Do Not Stop: Uncovering Infinite Agentic Loops in LLM Agents（工具 **IAL-SCAN**，arXiv `2607.01641`） | arXiv 2026 | **静态分析 / 检测** | 检测/测量型不是攻击构造；无界循环的成因是**开发者漏配终止条件**，不是攻击者构造 | Agent IR → ALDG 流水线（Fig. 3/4/5）；缺界重试环与工具调用环（Fig. 6/7） |
| （未占号） | Rethinking Denial-of-Service: A Conditional Taxonomy Unifying Availability and Sustainability Threats（arXiv `2508.19283`） | arXiv 2025 | **分类学** | C5/C6：分类学条目不算方法 | 取得全文，仅作本类边界与"经济可持续性是否属本类"这一口径问题的**外部依据** |
| （未占号） | Energy-Latency Attacks: A New Adversarial Threat to Deep Learning（arXiv `2503.04963`） | arXiv 2025 | **综述** | C5/C6：综述不算方法 | 取得全文；用于确认 energy-latency 一条轴的谱系与术语 |


**在此之前不计入**——按 `docs/` §3 第 4 条与 C5/C6，**检测/测量型不得计为方法**。

## 3. 对覆盖率口径的影响（**必须同报**）

| 项 | 值 |
|---|---|
| `methods/T07/cards/*.yaml` | **29**（= 本类方法数） |
| `methods/T07/scripts/*.py` | **29**（每卡一份派生脚本） |
| 本文件登记的**非方法件** | **2 篇占号（B-140 / B-141）+ 3 篇未占号（分类学 / 综述 / OllamaDrama）** |
| `tools/count_identity.py --case T07` 应输出 | **29**（与卡数一致；若多于 29，说明又混入了非方法卡） |