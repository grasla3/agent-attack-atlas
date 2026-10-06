# 共享文献池（`docs/shared-bibliography.md`）

| 项 | 值 |
|---|---|
| 状态 | **Draft v1 —— 8 个类别会话共同维护** |
| 规则 | **只追加，不删除**（勘误用「备注」列，保留原行） |
| 强制 | 不写入本池的文献，其方法卡**不得进入方法库**（`search-protocol.md` §6 第 7 步） |
| 当前条目 | **24 篇**（来自 `docs/method-capacity-audit.md` 的容量盘点） |

## 0. 字段说明

| 列 | 含义 |
|---|---|
| `bib_id` | 本池内唯一编号，格式 `B-<序号>` |
| `论文` | 题名（简写） |
| `venue` | 正式 venue；预印本标 `arXiv` |
| `年` | 出版年 |
| `等级` | 来源等级 `S`/`A`/`B`/`C`/`—`（定义见 `外部组件` §3） |
| `数字` | 数字证据等级 `原表`/`摘要`/`无` |
| **`类别`** | 归属的 `primary_asset`（T01–T08），**多类用逗号分隔，主类在前** |
| **`可切`** | 该文献可切出的方法数（**不是条目数**） |
| **`收录方`** | 由哪个类别会话收录（`T0X` 或 `盘点`） |
| `备注` | 版本冲突、数字口径、重复关系等 |

---

## 1. 文献池（初始 24 篇，来自容量盘点）

| bib_id | 论文 | venue | 年 | 等级 | 数字 | 类别 | 可切 | 收录方 | 备注 |
|---|---|---|---|---|---|---|---|---|---|
| B-01 | AgentPoison | NeurIPS | 2024 | S | 原表 | T01 | 1 | 盘点 | |
| B-02 | PoisonedRAG | USENIX Security | 2025 | S | 原表 | T01 | **2** | 盘点 | ⚠️ black-box / white-box 两档构造不同；arXiv 版与会议版**数字逐格一致** |
| B-03 | MINJA | NeurIPS | 2025 | S | 原表 | T01 | 1 | 盘点 | |
| B-04 | IKEA / Silent Leaks | ICLR | 2026 | S | 摘要 | T06, T08 | 1 | 盘点 | ⚠️ 两组数字口径不重合，已裁定 `>91% chunks / 96% success` |
| B-05 | Spill the Beans | ICLR | 2025 | S | 摘要 | T06, T08 | 1 | 盘点 | 攻击名 "Prompt-Injected Data Extraction"，"SpillBeans" 非论文自称 |
| B-06 | Greshake et al.（IPI 首篇） | arXiv（AISec 交叉引用） | 2023 | B | 摘要 | T01, T02?, T06 | 4 | 盘点 | ⚠️ 会议归属为交叉引用证据，非 PDF 直接印刷 |
| B-07 | InjecAgent | Findings of ACL | 2024 | A | 原表 | T04?, T08? | 2 | 盘点 | ⚠️ 等级：候选表记 S、统一表记 A → 按标准定 **A** |
| B-08 | AgentDojo | NeurIPS D&B | 2024 | S | 原表 | 多类 | 3 | 盘点 | **本项目参考目标** |
| B-09 | AgentHarm | ICLR | 2025 | S | 原表 | T03?, T04? | 2 | 盘点 | 明确评测 direct prompting，区别于 IPI |
| B-10 | Morris-II | arXiv | 2024/2025 | B | 摘要 | T01 | 1 | 盘点 | ⚠️ **= B-11 的 arXiv 版**；v2 文本内无 "RAGworm" 字样 |
| B-11 | RAGworm | ACM CCS | 2025 | S | 摘要 | T01 | **合并入 B-10** | 盘点 | ⚠️ **与 B-10 同一工作**，正式版；防御名 DonkeyRail |
| B-12 | BadRobot | ICLR | 2025 | S | 原表 | T04 | 3 | 盘点 | |
| B-13 | RoboPAIR | ICRA | 2025 | A | 原表 | T04, T06 | **3 + 1** | 盘点 | ⚠️ 三种威胁模型各配一系统（Dolphins 白盒 / Jackal 灰盒 / Go2 黑盒） |
| B-14 | BadVLA | NeurIPS | 2025 | S | 原表 | T04 | 1 | 盘点 | ⚠️ 原记 "96.7% ASR" 有误，实为**基线干净任务成功率**；真实 ASR 96.1/97.8/98.3 |
| B-15 | SafeAgentBench | arXiv | 2024 | B | 原表 | T04 | 1 | 盘点 | ⚠️ 是**评测基准**，是否算"攻击方法"待人工判定 |
| B-16 | Nuclear Deployed! | Findings of ACL | 2025 | A | 原表 | T04 | 1 | 盘点 | ⚠️ 同上，偏"能力演示" |
| B-17 | ToolSword | ACL | 2024 | A | 原表 | T04, T05? | 4 | 盘点 | ⚠️ 是**评测框架**，攻击者角色由数据集构造者隐式定义 |
| B-18 | Kim et al. SoK | USENIX Security | 2026 | S | **无** | —— | **0** | 盘点 | ⚠️ **分类学条目，已剔除**（贡献 4 条，占表1 的 8.7%）；**但它是本项目 7 维与 V1–V6 的出处** |
| B-19 | CodexLeaks | USENIX Security | 2023 | S | 摘要 | T08 | 1 | 盘点 | |
| B-20 | PentestGPT | USENIX Security | 2024 | S | 摘要 | T04?, T05? | 1 | 盘点 | 作者自评幻觉缓解"可能无法完全阻止" |
| B-21 | EnIGMA | ICML | 2025 | S | 摘要 | T04?, T05? | 1 | 盘点 | 缩写含义论文未提及 |
| B-22 | HPTSA | EACL | 2026 | A | 摘要 | T04?, T05? | 1 | 盘点 | 自称"首个成功完成有意义网络攻击的多智能体系统" |
| B-23 | Agent Smith | ICML | 2024 | S | 摘要 | T01 | 1 | 盘点 | 来源为 `文献深挖_SA2` 第 6 节（回 PDF 提取），权威性高于既有翻译 |
| B-24 | Secret Collusion | NeurIPS | 2024 | S | 摘要+原表 | T07? | 4 | 盘点 | ⚠️ 其四档是**监控者（防御方）能力**，算不算四个方法**待人工判定** |
| B-25 | Exploring the Security Threats of KB Poisoning in RACG | IEEE TSE | 2026 | S | 原表（Table 5/6/8/9） | **T01** | 1 | T01 | 全称 "Knowledge Base Poisoning in Retrieval-Augmented Code Generation"；作者 Bo Lin / Shangwen Wang / Liqian Chen / Xiaoguang Mao；Vol 52, pp.2250-2267。⚠️ **研究/测量型**：主结论是"注入漏洞样例使生成代码脆弱"，是否计为"攻击方法"待判 |
| B-26 | Covert Knowledge Poisoning Attacks in RACG（方法名 **Arachne**） | IEEE TDSC | 2026 | S | 原表（Table I/II/III） | **T01** | 1 | T01 | 作者 Yu Zhang / Miao Chen / Xinlei He / Tianshuo Cong / Ke Xu / Qi Li；Vol 23 No 4, pp.8649-8666。构造：良性片段分解 + 检索驱动补全。⚠️ 与 B-25 **同题域不同团队**（作者零重叠），非同一工作 |
| B-27 | Bias Amplification in RAG（方法名 **BRRA**） | IEEE TDSC | 2026 | S | 原表（Fig. 3/4/5） | **T01** | 1 | T01 | 作者 Linlin Wang / Tianqing Zhu / Laiqiao Qin / Longxiang Gao / Wanlei Zhou；Vol 23, pp.11033-11050 |
| B-28 | Exploring knowledge poisoning attacks to RAG | Information Fusion | 2026 | S | 原表（Table/Fig） | **T01** | 1 | T01 | Vol 127 Part C, ArtNo 103900。⚠️ **同一工作曾名 "RAG Safety: Exploring Knowledge Poisoning Attacks to RAG"**（arXiv，作者一致），引用时并列双名 |
| B-29 | Memory poisoning attacks on RAG LLM agents via deceptive semantic reasoning（方法名 **DSRM**） | Eng. Appl. Artif. Intell. | 2026 | A | 原表（Table 2/3/5） | **T01** | 1 | T01 | Vol 167, ArtNo 113968。ASR_A 41.0% vs PoisonedRAG 34.0%（Table 2） |
| B-30 | SpAIware: persistent memory attack vector in LLM applications | Future Gener. Comput. Syst. | 2026 | A | 原表 | **T01, T08?** | 1 | T01 | Vol 174, ArtNo 107994；作者 Manuel Herrador / Johann Rehberger。⚠️ **跨类**：注入通道是持久记忆（T01），但终点资产疑为凭据/数据（T08），主类待 κ |
| B-31 | SilentRetrieval: Hijacking RAG via Semantically-Preserving Adversarial Data Poisoning | ACM KDD | 2026 | A | 原表（Table 1–11） | **T01** | 1 | T01 | KDD '26 V.2, pp.4012-4023；DOI 10.1145/3770855.3818186；arXiv **2605.28074**。⚠️ **勘误登记**：其编号曾被当前实现误记为 2604.07403，后者实为 RefineRAG |
| B-32 | WARP: Word-Level Backdoor Attack on RAG via Retrieval Corpus Poisoning | ACM KDD | 2026 | A | 原表（Table 1–12） | **T01** | 1 | T01 | KDD '26 V.1, pp.867-878；DOI 10.1145/3770854.3780227。平均 ASR 55.8%（Table 1） |
| B-33 | Uncovering Competing Poisoning Attacks in RAG | ACM KDD | 2026 | A | 原表（Table 1–4） | **T01** | 1 | T01 | KDD '26 V.2；DOI 10.1145/3770855.3818119。提出 m-ASR / m-F1 / 竞争系数与 **PoisonArena** 基准 |
| B-34 | When RAG Lies: Link-Injection Knowledge-Base Poisoning in Code Generation | IEEE SANER | 2026 | B | 摘要+原表 | **T01** | 1 | T01 | SANER 2026 short paper, pp.773-778；DOI 10.1109/saner67736.2026.00090 |
| B-35 | Visual Inception: Compromising Long-term Planning in Agentic Recommenders via Multimodal Memory Poisoning | ACL | 2026 | A | 原表（Table 6/13, Fig. 1–6） | **T01** | 1 | T01 | ACL 2026 Long, pp.20846-20862；DOI 10.18653/v1/2026.acl-long.954。⚠️ Crossref 仅记 1 位作者（Jiachen Qian），疑作者消歧不全 |
| B-36 | M³Att: Knowledge Poisoning Attacks on Medical Multi-Modal RAG | ACL | 2026 | A | 原表（Table 1, Fig. 2/3） | **T01** | 1 | T01 | ACL 2026 Long；DOI 10.18653/v1/2026.acl-long.892 |
| B-37 | LogicPoison: Logical Attacks on Graph Retrieval-Augmented Generation | ACL | 2026 | A | 原表（Table 2/3, Fig. 3/4） | **T01** | 1 | T01 | ACL 2026 Long；DOI 10.18653/v1/2026.acl-long.252。攻图谱**拓扑完整性** |
| B-38 | MM-PoisonRAG: Disrupting Multimodal RAG with Local and Global Knowledge Poisoning Attacks | ACL | 2026 | A | 原表（Table 1/2/3） | **T01** | 1 | T01 | ACL 2026 Long；DOI 10.18653/v1/2026.acl-long.1558 |
| B-39 | AdversarialCoT: Single-Document Retrieval Poisoning for LLM Reasoning | ACM SIGIR | 2026 | A | 原表（Table 2/3） | **T01** | 1 | T01 | SIGIR '26；DOI 10.1145/3805712.3809838 |
| B-40 | Unsupervised Corpus Poisoning Attacks in Continuous Space for Dense Retrieval | ACM SIGIR | 2025 | A | 原表（Table 2/3/4/5） | **T01** | 1 | T01 | SIGIR '25（48th）；DOI 10.1145/3726302.3730110。连续嵌入空间优化，非离散词替换 |
| B-41 | CorruptRAG: Practical Poisoning Attacks against RAG | ACM SACMAT | 2026 | A | 原表（Table 2–9） | **T01** | 1 | T01 | SACMAT '26；DOI 10.1145/3750555.3811900。⚠️ 与 B-42 **同一团队**（7 位共同作者，Baolei Zhang 组），攻/防两篇，勿混计 |
| B-42 | Who Taught the Lie? Responsibility Attribution for Poisoned Knowledge in RAG（方法名 **RAGOrigin**） | IEEE S&P | 2026 | S | 原表 | —— | **0** | T01 | DOI 10.1109/sp63933.2026.00053；arXiv **2509.13772**。⚠️ **防御/归因框架，非攻击方法**，按 C6 不计方法；收录供 T01 判据层与归因对照使用 |
| B-43 | CatPoison: Category-Oriented Knowledge Poisoning Attacks in RAG Systems | IEEE TrustCom | 2025 | A | 原表 | **T01** | 1 | T01 | pp.2181-2189；DOI 10.1109/trustcom66490.2025.00254；arXiv 2509.13772 **非本篇**（该号实为 B-42） |
| B-44 | RefineRAG: Word-Level Poisoning Attacks via Retriever-Guided Text Refinement | LNCS / Pattern Recognition（会议录） | 2026 | B | 原表 | **T01** | 1 | T01 | DOI 10.1007/978-3-032-31583-0_35；arXiv **2604.07403**。⚠️ **出版形态是 book-chapter（会议录），不是 SCI 期刊**——检索时极易误判为期刊 |

> **`类别` 列带 `?` 者为待定**——需由对应类别会话在作业时确认。

---

## 2. 待处理事项（**须在开 8 个会话前解决**）

| # | 事项 | 影响 |
|---|---|---|
| 1 | **B-15 / B-16 / B-17 是否算"攻击方法"** | 三者更接近评测基准 / 能力演示，与 B-18 的分类学条目有类似问题；若剔除，容量再减 3 |
| 2 | **B-24 的四档监控者能力算不算四个方法** | 四档是防御方能力，不是攻击方 |
| 3 | **B-02 / B-13 的多档切分是否成立** | 决定"可切"列的可信度 |
| 4 | **B-04 / B-05 的双类归属**（T06 与 T08 都是"读"） | 主类判定依赖 `category-taxonomy.md` §5.3 的谓词 |
| 5 | **B-11 与 B-10 的合并**（同工作两版本） | 影响计数 |
| 6 | **所有 `?` 类别的确认** | 每类可用方法数 |

---

---


> 本类的收录理由、判为不计的文献、以及待收录项，逐条见 **`docs/domain-and-literature.md`**（本表只放池内行）。
> `等级` 依据**原文自述**的 venue 陈述（arXiv `comment`/`journal_ref`）定级；
> **第 4 轮 DBLP 独立核验本轮未取得**（见 `ROADMAP.md` F-2），凡"待核"在备注列写明。

| bib_id | 论文 | venue | 年 | 等级 | 数字 | 类别 | 可切 | 收录方 | 备注 |
|---|---|---|---|---|---|---|---|---|---|
| B-65 | Jailbreaking LLM-Controlled Robots（方法名 **RoboPAIR**） | 论文未声明；项目页自述 ICRA 2025 | 2024 | A | **原表** | **T04** | 1–3 | T04 | arXiv **2410.13691**。⚠️ **题名更正**：旧记 "RoboPAIR" 非论文自称（与 B-05 "SpillBeans" 同类处置）。Table 1 = Dolphins 白盒 7 动作 × 5 方法 × 5 次独立试验（RoboPAIR 35/35，Direct 5/35）；Jackal 灰盒 / Go2 黑盒两张结果表被 HTML 截断（TRUNCATED） |
| B-66 | BadVLA: Towards Backdoor Attacks on Vision-Language-Action Models via Objective-Decoupled Optimization | 论文未声明；二手称 NeurIPS 2025（**未核**） | 2025 | S（待核） | **原表** | **T04** | 1 | T04 | arXiv **2505.16640**。Table 1（OpenVLA × LIBERO 四套件 × 三种触发器）**含 Data-Poisoned / Model-Poisoned 对照臂**，二者四套件全 0.0；Ours AVE 98.3 / 97.8 |
| B-67 | BadRobot: Jailbreaking Embodied LLM Agents in the Physical World | **ICLR 2025**（comment + journal-ref 自述） | 2024 | S | **摘要** | **T04** | 1 | T04 | arXiv **2407.20242**。基于**语音**的用户-系统交互；实验表号未取到 ⇒ 按 C11 暂不能算 |
| B-68 | AttackLLM: LLM-based Attack Pattern Generation for an Industrial Control System | 论文未声明（HTML 为未替换的 ACM 模板占位符） | 2025 | 未分级 | **原表** | **T04** | 1 | T04 | arXiv **2504.04187**。Table 1（11 条控制不变量）/ Table 2（7 中 4 通过）/ Listing 1；**159 条生成 / 120 条经验证 vs 人类专家 36 条**。⚠️ 产出物是攻击模式与数据集，非已执行的 agent 控制动作 |
| B-69 | Jailbreaking Embodied LLMs via Action-level Manipulation | **ACM SenSys 2026**（comment 自述） | 2026 | A | **摘要** | **T04** | 1 | T04 | arXiv **2603.01414**。机制 = **Adversarial Proxy Planning**（被控本地替身 LLM 把恶意意图翻译成一串各自良性的原子动作）+ 掩护动作噪声 |
| B-70 | CHAI: Command Hijacking against embodied AI | **IEEE SaTML**（comment 自述） | 2025 | A | **摘要** | **T04** | 1 | T04 | arXiv **2510.00181**。机制 = **物理环境间接注入**：把欺骗性自然语言指令（误导性标牌）嵌入**视觉输入**，搜 token 空间 + 提示字典。摘要无数值 |
| B-71 | Propagating Unsafe Actions in LLM Controlled Multi-Robot Collaboration via Single Robot Compromise | **IJCAI 2026**（comment 自述） | 2026 | A | **摘要** | **T04** | 1 | T04 | arXiv **2605.15641**。机制 = **单点妥协 → 机器人间通信传播**。摘要：obedience **1.00** / infectiousness **0.90** / **3.0 轮** / stealthiness **0.81** |
| B-72 | Breaking Planner Integrity Boundary: Enviroment State-Text Injection Attack on LLM-Driven Embodied Agents | 未声明（comment 仅 "Embodied Agents"） | 2026 | 未分级 | **摘要** | **T04** | 1 | T04 | arXiv **2608.16806**。机制 = **ESTI**：把对抗目标改写为**假状态证据**注入环境状态文本，不改指令/权重/执行器。摘要：planning ASR **+89.32%** / execution ASR **+43.69%**。⚠️ 题名拼写为原文的 "Enviroment"（缺 n），照录不改 |
| B-73 | TrapVLA: Trapping Vision-Language-Action Models in Configured Failure Modes | 待核 | 2026 | 未分级 | **原表** | **T04** | 1 | T04 | arXiv **2608.26578**。**Table 1** verbatim：*"Trap-LIBERO results with OpenVLA-OFT. Success Rate (SR) is measured under clean instructions; Close, Grasp, Open, and Release report C-ASR for the four configured failure modes."* 实机为 **ROKAE 6-DoF 臂**，每任务 50 条演示、每条件 30 次试验 |
| B-74 | MCP-ITP: An Automated Framework for Implicit Tool Poisoning in MCP | 待核 | 2026 | 未分级 | **摘要** | **T04** | 1 | T04 | arXiv **2601.07395**。机制 = 毒化工具描述使 agent **忽略**该工具、转而调用**合法高权限**工具（Fig. 1 caption：`write_file` 改写 SSH 私钥等敏感资产）。摘要：ASR ≤ **84.2%** / MDR ≥ **0.3%** |
| B-75 | A2M: Trace-Optimized Agent Hijacking in the MCP Ecosystem | **AACL-IJCNLP 2026**（comment 自述） | 2026 | A | **摘要** | **T04** | 1（仅 EIC 子机制） | T04 | arXiv **2609.26761**。§3.3 **Environment Integrity Compromise**：诱使 agent 执行未授权写操作（改 `config.json`、装持久化后门）。⚠️ 该文 4 场景中仅此 1 个是 ACTION 终点；摘要 MTIR **93.6%** / mean ASR **74.4%** |

| B-76 | TrojanRobot / Robot Collapse: Supply Chain Backdoor Attacks Against VLM-based Robotic Manipulation | 论文未声明 | 2024/2026 | 未分级 | **原表** | **T04** | 1 | T04 | arXiv **2411.11683**。⚠️ **一篇 4 个题名**：v1 2024-11-18「…Backdoor Attacks Against Robotic Manipulation…」· **v2 2024-12-08「TrojanRobot: Backdoor Attacks Against LLM-based Embodied Robots in the Physical World」（与共享池记录逐字相符）** · v3–v6 改名「…Physical-world Backdoor Attacks Against VLM-based Robotic Manipulation」· **v7 2026-04-02 完全改名「Robot Collapse: Supply Chain Backdoor Attacks Against VLM-based Robotic Manipulation」**。引用须标版本。v7 Table 1 为 CA/ASR 双栏（**averaged from three runs with standard deviations**），仿真 4 策略 + 物理 **UR3e** 4 VLM；Fig. 1 为 myCobot 280-Pi 演示。机制 = 供应链模块投毒（外部后门 VLM 改写 LLM→VLM 物体文本） |
| B-77 | Adversarial Attacks on Robotic Vision Language Action Models（GCG 式文本后缀） | 论文未声明 | 2025 | 未分级 | **原表** | **T04** | 1 | T04 | arXiv **2506.03350**。Table 1「Single step attacks」逐维 + 总体 ASR（**256×7=1792 个 one-hot 目标/模型**）；Table 2 真实世界图像（HYDRA 61.2 / SIMPLER 38.0）；Table 3 防御臂（**LLM-Only PF 与 Smoothing 均 0.0**）；Fig. 2 持久化攻击，对照 = **50 次未攻击 rollout**。⚠️ **无真机致动**——『真实世界』是真实图像数据集，rollout 在仿真执行 |
| B-78 | Hidden in Plain Sight: Diffusion-Based Unrestricted Robotic Attacks on Vision-Language-Action Models（方法名 **DURA**） | 论文未声明 | 2026 | 未分级 | **原表** | **T04** | 1 | T04 | arXiv **2608.10393**。Table 1/2（OpenVLA-7B 与 π0-FAST）；对照臂 **Benign 无贴片 23.5% / Clean patch 39.5%**；黑盒 Ours 模拟贴片 86.0 / 物理贴片 79.3。**Fig. 3 = 真机 Franka 7-DoF**：放入打印贴片→偏离、取出→恢复、再放入→再次触发（原文「controllable and repeatable on real hardware」）。**n = over 100 trials per suite (10 tasks × 10 rollouts)** |
| B-79 | BadRobot: Jailbreaking Embodied LLM Agents in the Physical World | **ICLR 2025** | 2024 | S | **原表** | **T04** | 1 | T04 | arXiv **2407.20242**（v5 2026-06-09）。**补表号（推翻本池旧记的『摘要级』）**：Table 1「Comparison Studies」与 5 个越狱族对照（B_cj 0.83 / B_sm 0.66 / B_cd 0.65 vs Vanilla 0.25）；Table 2「Effectiveness Evaluation」逐 LLM × 危害类别；Table 3「Mitigations」。⚠️ **头条指标是 MSR（Manipulate Success Rate），不是 ASR** —— §4.4 里的 ASR 指 **Automatic Speech Recognition**（语音识别模块）。真机 **UR3e + myCobot 280-Pi**；§4.4 原文「our method achieved an average MSR of 68.57%, meaning the robotic arm successfully executed actions corresponding to malicious commands」；**基准 n = 277 条恶意查询**，真机臂 n = 35 次/攻击（7 类 × 5 样本）。⚠️ 作者 GitHub README 称基准「320+」，与论文 277 冲突 ⇒ **引 277** |
| B-80 | Jailbreaking LLM-Controlled Robots（**黑盒档**：Unitree Go2，仅语音查询） | 论文未声明；项目页自述 ICRA 2025 | 2024 | A（待核） | **摘要** | **T04** | 1 | T04 | arXiv **2410.13691** = **B-65** 的**黑盒能力档**。B-65 摘要原文「our results on the Unitree Go2 represent the first successful jailbreak of a deployed commercial robotic system」；§4 给出三种威胁模型（白盒 Dolphins / 灰盒 Jackal / **黑盒 Go2**）。⚠️ 本条目与 B-65 是**同一篇论文**，单列是因为该文**把能力档当作独立构造**（见 `docs/`）。**若该提案未获批，本条在 C4 五轴上与 B-65 全等 ⇒ 须并为 `variant_of`** |
| B-81 | Jailbreaking LLM-Controlled Robots（**灰盒档**：Clearpath Jackal + GPT-4o 规划器） | 论文未声明；项目页自述 ICRA 2025 | 2024 | A（待核） | **摘要** | **T04** | 1 | T04 | arXiv **2410.13691** = **B-65** 的**灰盒能力档**。Fig. 9 说明 Jackal 的 GPT-4o 规划器在学术实验场景下一般拒绝识别炸弹投放目标。同上：**取决于 C4 第 6 轴提案是否获批** |
| B-82 | AttackLLM: LLM-based Attack Pattern Generation for an Industrial Control System | 论文未声明（HTML 为未替换的 ACM 模板占位符） | 2025 | 未分级 | **原表** | **T04** | 1 | T04 | arXiv **2504.04187**。Table 1（Stage1 的 11 条控制不变量）· Table 2（校验：7 中 4 通过）· Listing 1（控制逻辑 29 行，阈值 250/500/800/1000/1200）· §3 正文：**159 条生成 / 120 条经验证 vs 人类专家 36 条**；复现人类设计攻击 10 条中的 9 条。⚠️ **产出物是攻击模式与数据集**，不是已执行的 agent 控制动作（原文自陈） |
| B-83 | ControlLoc: Physical-World Hijacking Attack on Camera-based Perception in Autonomous Driving | **ACM CCS 2025**, pp.738–752（出版方元数据；论文自身未声明） | 2025 | S | **原表** | **T04** | 1 | T04 | DOI `10.1145/3719027.3744842`。⚠️ arXiv 预印本 `2406.05810`（唯一版本）题名为「…on **Visual** Perception…」且**数字不同** ⇒ 须**并列双值 + 版本标签**。**Table 1**（四 OD × 四 MOT，末行 Average ASR **98.1**、Average Frame# **2.8**）· **Table 3**（物理世界：实车 **79%** ASR，**基线 [25] 在每一格为 0%**，72 场景 = 3 光照 × 4 角度 × 6 背景，averaged over 5 videos）· **Fig. 9**（系统级：Baidu Apollo + LGSVL 仿真，**10 runs/场景**）。⚠️ **CCS 摘要的 72.5% / 96.3% 在正文其余部分不再出现**，而 §6.5 正文写的是 **77.5%** ⇒ 按 E5 并列登记，**卡上 `numeric_evidence` 只能记 `body_text`**（规则 47：指不出表号不得记 `original_table`）。**实车仅验证到感知层，物理后果来自仿真** |
| B-T04-01 | Jailbreaking Embodied LLMs via Action-level Manipulation（方法名 **Blindfold**） | **ACM SenSys 2026**（comment 自述） | 2026 | A | **原表** | **T04** | 3 | T04 | arXiv **2603.01414**。**三个独立机制**：代理分解 / 掩护动作混淆 / FSM 校验细化（本类用 LIT-B-T04-01A/B/C 区分）。Table 1 消融（Raw GPT-4o ASR 27.4%/TSR 26.4%；**无 verifier** 88.4%/41.9% 与 95.9%/19.3%；**无 obfuscator** 59.8%/80.1% 与 61.0%/49.2%；**完整 Blindfold 93.2%/77.6% 与 98.1%/46.9%**）；Table 2 逐条 20 个恶意指令；Table 3 迁移防御（Llama-Guard 86.1%、SafeDecoding 88.7%、VeriSafe 76.5%）。**真机 UFactory xArm 6：20 条中 18 条成功、12 条在真机上实际执行**（§7.6）。 |
| B-T04-02 | Propagating Unsafe Actions in LLM Controlled Multi-Robot Collaboration via Single Robot Compromise（方法名 **InfectBot**） | **IJCAI 2026**（comment 自述） | 2026 | A | **原表** | **T04** | 1 | T04 | arXiv **2605.15641**（v2）。Table 1 逐任务 × 模型：**obedience 1.00 / stealth 0.81 / 3.0 轮** 同属 Formation Escort·Kimi-K2 行；infectiousness 0.90 属 Warehouse Patrol·Gemini-2.5-Flash。Table 2：832 次不安全事件，**61.5% 由转发消息诱导**（仅 38.5% 由 Robot 0 直接触发）；44.2% 达 ≥3 跳、10.3% 达 ≥5 跳。终点 ACTION（Isaac Sim + ROS 2 Humble 派发 Move/Camera/HandleCargo）；**伦理声明 no physical deployment**。⚠️ **每格 n 未声明**（仅写 deterministic decoding, temperature 0）。 |
| B-T04-03 | Breaking Planner Integrity Boundary: Enviroment State-Text Injection Attack on LLM-Driven Embodied Agents（方法名 **ESTI**） | 未声明（v3 comment 仅「Embodied Agents」；v1/v2 为 submitted to USENIX Security 2027） | 2026 | 未分级 | **原表** | **T04** | 1 | T04 | arXiv **2608.16806**（v3）。机制 = 改写 **planner 可见的环境状态文本**（§3.1.2 verbatim）。Table 1/3/4 逐 planner 的 P-ASR/E-ASR（如 Qwen-3.6-Plus·AI2-THOR「ESTI 69.33% 100.00% 50.49%」vs「BADROBOT-conceptual deception 68.00% 10.68% 6.80%」）；**Table 5 消融**：w/o Runtime Re-grounding 98.08/44.23、w/o Native-Carrier Matching 12.50/6.73、w/o Representation Consistency 37.50/25.00、**Full ESTI 100.00/48.08**。三点结构对照 **clean / control（等长同风格良性状态文本）/ attack** ⇒ 本类最规范的对照设计。⚠️ **头条的 +89.32% / +43.69% 只在摘要**（任何表或 caption 都没有）⇒ `numeric_evidence` 记 `abstract`。⚠️ n 未声明（仅「Each condition is repeated three times」）。 |
| B-T04-04 | FreezeVLA: Action-Freezing Attacks against Vision-Language-Action Models | 未声明 | 2025 | 未分级 | **原表** | **T04** | 1 | T04 | arXiv **2509.19870**。机制 = **min–max 双层优化**：先由 o3 生成参考提示集 P，内层以 M=10 次同义词贪心替换构造「抗冻结」硬提示，外层以 T=100 次在 ε=4/255 下优化**对抗图像**，使 VLA 输出 `<freeze>` token（SpatialVLA/π0 的 `<eos>`；OpenVLA 的 do-nothing token）⇒ 数字心智与物理动作解耦。Table 1 逐模型 × 逐套件（OpenVLA：PGD 17.0 → Multi-Prompt 92.0；FreezeVLA+GPT 95.4 平均；SpatialVLA 73.3；π0 59.8）；Table 2 方法对照；Fig. 3/4/5 消融。⚠️ **每格 n 未声明**；⚠️ **仅仿真**（§5 Limitation 自陈 limited to simulation benchmarks）。 |
| B-T04-05 | SilentDrift: Exploiting Action Chunking for Stealthy Backdoor Attacks on Vision-Language-Action Models | **ACL Findings 2026**（comment 自述） | 2026 | B | **原表** | **T04** | 1 | T04 | arXiv **2601.14323**（v2）。机制 = **Smootherstep 调制的 C² 连续漂移**（五阶、边界速度与加速度为零、幅值 0.3 m）注入 **delta-pose 动作分块**，仅在末端接近目标物体（<0.15 m）时激活；视觉触发器为红色圆形贴片（r=5 px、α=1.0）；投毒率 2%。Table 1（VLA-Adapter **CTSR 95.3 / ASR 93.2**；pi-0 CTSR 92.4 / ASR 92.7；Baseline SR 96.6 / 93.2）；Table 2 触发器变体敏感性；Fig. 6 四因素消融。⚠️ **评测回合数未声明**（投毒率 2% = 每任务 1 条毒样本已给）。⚠️ 仅仿真（LIBERO，两架构）。 |
| B-T04-06 | Systems-Level Attack Surface of Edge Agent Deployments on IoT | **EuroMLSys '26**（comment 自述；与 EuroSys 2026 合办） | 2026 | B | **原表** | **T04** | 3 | T04 | arXiv **2602.22525**。机制 = **流氓 MQTT 客户端向 agent 收件箱/安全主题发布伪造或重放的信封**，绕过监督层。**Table 4 四类攻击全部被 broker 接受**：Missing sender → Untraceable command；Spoofed sender → Rogue agent frames others；Replayed → Command re-executed；Direct safety publish → Agent logic bypassed。Table 2/3（致动-审计延迟：50 B 均值 23.6 ms、P95 26.9 ms；NUC 路径 64.3–64.5 ms；**N=150/50**）。Table 5/6/7（数据外流、主权边界、重连 9.3 ms）。⚠️ **物理致动未明确报告**（论文自陈失效窗口「可被用于未授权致动」）⇒ 终点在控制面而非致动面。三个可切面：provenance forgery / 静默云回退 / 故障切换盲窗。 |
| B-T04-07 | From Prompt to Physical Action: Structured Backdoor Attacks on LLM-Mediated Robotic Control Systems | 未声明 | 2026 | 未分级 | **无**（全文无数据表） | **T04** | 1 | T04 | arXiv **2604.03890**（v1，唯一版本）。机制 = **后门 LoRA 适配器输出恶意 JSON 速度指令**，经 **ROS 2** 解析后发布到 `/cmd_vel`；在**实体 Yahboom MicroROS 机器人小车**上验证。数字（**全部为正文级**，83% ASR / CPA >93% / 延迟 <1.0 s / 有防御臂 20% ASR 与 8–9 s）—— 该文**全文没有任何数据表**，Fig. 5 的 caption 也不含数字 ⇒ 按规则 47 `numeric_evidence` 记 **`body_text`**。对照臂齐全：推理层投毒 vs **结构化输出投毒**；有防御 vs 无防御。 |
| B-T04-08 | RIPA: Sensory-Vector Prompt Injection Attacks on LLM-Controlled ROS 2 Robots | 未声明（comment 仅篇幅） | 2026 | B | **原表（10 张）** | **T04** | 2 | T04 | arXiv **2606.28649**。**两个可切机制**（本类用 LIT-B-T04-08A/B 区分）：**视觉（OCR）通道**（TABLE VII）与 **LiDAR 状态伪造通道**（TABLE X）。TABLE IV「MULTI-MODEL BASELINE ASR」副题注明 **n = 100 per variant**；正文 *"three base injection variants; each was tested in **100 independent runs per model (300 attack runs per model)**"*，总 **570 trials**；TABLE VIII（音频，DeepSeek-V4-Flash，**N = 30**）与 TABLE X（LiDAR，temperature = 0，**N = 30 PER VARIANT**）。TABLE II 给出到 ROS 2 **/cmd_vel** 的 TwistStamped 命令映射；TABLE V 为防火墙防御臂（聚合指标）。**反单调发现**：Llama-3.3-70B-Instruct-Turbo 全变体 100% ASR，Llama-3-8B 与 Qwen2.5-7B 对 direct-override 0%，最小模型 Gemma-3n-E4B（约 4B）与 70B 同档 ⇒ 稳健性与规模无关。⚠️ 原文自陈 *"payloads are **deterministic**, so we report per-payload bypass counts rather than claim exact reproducibility"* ⇒ 引用时须带此限定 |
| B-T04-09 | Adversarial Vulnerabilities of Learned Telesurgery Policies | 未声明 | 2026 | B | **原表（4 张）** | **T04** | 1 | T04 | arXiv **2606.11535**。自陈**首个**学习型手术机器人策略对抗脆弱性研究。白色盒设定、向**视频流**注入扰动；两模式：**disruptive**（不被术者察觉地打断执行）与 **steering**（把动作导向攻击者指定方向）。**TABLE I** 清创性能（caption 原文：*"Debridement performance after **UAP** (Offline Dataset Attack), **PGD** (Online Inference Attack), and **TPA** (Temporal Photometric Attack). Bold indicates the best performance…The Clean row reports…"*）；**TABLE II** 缝合性能；**TABLE III** 人类检测时延与工作空间偏差（**人也要被量化**）；**TABLE IV** 三种光度变换与最小二乘参数估计（白盒）。**n 明确**：*"**80 trials** of debridement and **100 trials** of suturing"*、*"evaluated over **10 trials**"*、*"**10 trials per condition**"*。覆盖 **ACT / Diffusion Policy** 等三个端到端策略架构；在**体模**上完成。⚠️ 该文**未使用 LLM/agent 诱导**，攻击者直接扰动视频流 ⇒ 按本类谓词属**边界条目**（终点确为执行动作，但通道非语言模型） |
| B-T04-11 | NRT-Bench: Benchmarking Multi-Turn Red-Teaming of LLM Operator Agents in Safety-Critical Control Rooms | 未声明 | 2026 | B | **原表（10 张）** | **T04** | 0 | T04 | arXiv **2606.20408**（与 KAERI 合作）。五角色 LLM 操作员班组运行一个受**六项关键安全功能（CSF）**约束的**仿真核电厂控制室**；对手经**四个通道**在有界多轮会话中注入、**每轮带反馈**。**TABLE 2** 八格消融网格的 per-cell ASR_CSF（*"The gpt and claude columns aggregate **72 replayed sessions per cell**"*）；**TABLE 4/6** 基于 **149-session paired test split**；TABLE 11 定义六项 CSF。⚠️ **本类计 0 个方法**：它是**基准**，不产新攻击构造。但它是本类**判据层的最强外部对照**——其 harm 定义 *"an objective signal rather than LLM-judged text: a run terminates the moment any CSF is lost"*，与 `docs/judgment-discipline.md` **E1**（模型自述不可作为证据）及本类卡的 `evidence_layer: behavior` **同型且相互独立**。⚠️ 该文摘要出现 **MSR 68.57%**，即**本项目 BadRobot 卡（T04.B-79）的指标值** ⇒ 它**引用了 BadRobot 作对照基线**；两处含 MSR 的文献**不是同一工作**，引用须写明出处 |
## 3. 追加规则（**8 个类别会话按此追加**）

```
每收录一篇新文献，追加一行：
bib_id        B-<最大序号+1>
类别          填 primary_asset（T01–T08）；多类用逗号，主类在前
可切          填"该文献可切出的方法数"，不是条目数
收录方        填当前实现的 T0X
备注          版本冲突 / 数字口径 / 与其他条目的重复关系，一律并列陈述，不推断
```

**强制**：
- **不得删除已有行**；勘误只改「备注」列并保留原值；
- **不得修改他方已填的行**，只能在「备注」列追加；
- 追加后须同步 `docs/method-coverage.md` 的归类表。