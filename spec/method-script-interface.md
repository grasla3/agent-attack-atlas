# 方法脚本接口（`spec/method-script-interface.md`）

| 项 | 值 |
|---|---|
| 状态 | **已冻结**（2026-09-29） |
| 冻结依据 | **三份独立实现已自然收敛**——T01（28 方法）/ T03（1）/ T06（20）由三个互不可见的会话各自写成，**必需面完全一致**（对照见 §6） |

| 下游 | 全部 `methods/<CASE>/<CASE>.py` 与 `methods/<CASE>/scripts/*.py` |

---

## 1. 这一层为什么存在

交付形态是 `method library + evaluation specification`：**脚本是交付物本身**。
脚本分两层（`docs/delivery-form.md` §1）：

```
methods/<CASE>/
├── cards/        每方法一张 .yaml   ← 源：声明 + 出处 + 判据 + 前置条件
├── scripts/      每方法一份 .py     ← 派生：由本类模块 + 该卡参数生成
└── <CASE>.py     本类共用的执行逻辑  ← 手写，每类一份（本文件规定的就是它）
```

**手写的是类模块，派生出的是方法脚本。** 240 份手写脚本就是 240 份要单独审计的代码；
8 份类模块 + 参数，通用逻辑只改一处。

---

## 2. 必需面（**每类都必须有**）

### 2.1 五个常量

| 常量 | 类型 | 语义 |
|---|---|---|
| `CASE_ID` | `str` | 本类编号，如 `"T01"`。必须等于所在目录名 |
| `CARD_DIR` | `Path` | `Path(__file__).resolve().parent / "cards"`。**不得硬编码绝对路径** |
| `ENTRY_TOOL` | `Dict[str, str]` | **投放入口映射**：卡上 `provenance_components.vector` 的取值 → 目标侧需具备的工具名。回答"往哪写、调哪个工具" |
| `EVIDENCE_LAYER` | `str` | 本类声明的证据层，取 `text` / `behavior` / `authorization` / `state` / `causal` 之一。**须与卡的 `judge.evidence_layer` 相容**，并受 manifest 的 `allow_text_fallback` 约束 |
| `NON_PARAMETRIC` | `Dict[str, str]` | **无法参数化的方法**：`method_id -> 理由`。判据是"该构造要求运行期反馈回路或独立优化器"，**不是"看起来复杂"**。这些方法对应 `execution.mode: script_hook` |

### 2.2 两个数据类

| 类 | 语义 |
|---|---|
| `MethodSpec` | 一个方法的**可执行规格**：由卡推出，含通道、参数、维度档位、判定信息 |
| 载荷规格类（名字由本类定，如 `InjectionSpec` / `DeliverySpec` / `ProbeSpec`） | 本类的**载荷构造规格**。**只放结构性参数，不放载荷正文**（禁令 9） |

### 2.3 五个函数

| 函数 | 签名 | 语义 |
|---|---|---|
| `spec_from_card` | `(method_id: str) -> MethodSpec` | 由**卡**推出规格。这是"源 → 派生"的入口，**卡是唯一真相源** |
| `build_plan` | `(spec: MethodSpec, dry_run: bool = True) -> Dict[str, Any]` | 产出一份**执行计划**（结构化 dict）。`dry_run=True` 时不得产生副作用 |
| `plan_grid` | `(spec: MethodSpec) -> List[Dict[str, Any]]` | 按 `dimensions` 的档位组合展开成网格。**这是"可组合"（S3）的执行器** |
| `validate` | `(spec: MethodSpec) -> List[str]` | 自查，返回问题清单（空列表 = 通过） |
| `main` | `(argv: Optional[List[str]] = None) -> int` | CLI 入口。须支持 `list`（列出本类方法与通道）与 `plan <method_id> [--dry-run]`；**输出结构化 JSON 到 stdout**（tech-design §3.5 E8） |

---

## 3. 允许的扩展（**每类按需加，不算违约**）

三份实现各自的扩展，可作为先例：

| 类 | 扩展 | 用途 |
|---|---|---|
| T03 | `EVIDENCE_LAYER_ALTERNATIVES = {...}` | 本类部分方法的判据只能落在别的证据层，逐方法如实登记 |
| T06 | `SIDE_CHANNEL_METHODS = {...}` + `CACHE_SHARING_OBSERVABLE` + `status_of(observables, spec)` | 本类有依赖目标属性的分支，需要显式状态函数（见 §3.1） |
| T01 | `load_card` / `custom_builder` / `_all_cards` | 卡加载与 `script_hook` 方法的分派 |

**约束**：扩展只**增**，不得改必需面的签名与语义。若某个扩展在两类以上出现且语义相同，应提议并入本文件（见 §7）。

### 3.1 `status_of`：类模块与 runner 的状态判定接口（`script-interface-v1.1` 刷新）

有些方法"该不该测"只有**类自己**知道——它依赖目标侧有没有某种**观测装置**
（T06 的侧信道一族要缓存/批处理共享）。这一问既不是"目标有没有这个工具"，
也不是"前置条件满不满足"，故单列一个可选扩展：

```python
def status_of(observables, spec) -> str:
    # observables: 靶标声明的观测装置清单（TargetAdapter.caps()["observables"]），原样递入
    # 返回 "" 或 "applicable" ⇒ 继续测；返回六态之一 ⇒ 整格按该态记，不投放、不调判据
```

**为什么传清单而不是传布尔**：runner **不得知道任何类别的词汇**。
若签名是 `status_of(target_has_cache_sharing, spec)`，那么"缓存共享"这个名字就
硬编码进了 runner——而它是 T06 的词。传清单则 runner 保持通用，判断留在类里。

**状态语义**（R3/R4）：装置不具备 ⇒ `not_applicable`（本就不该测，**不拉低覆盖率**）；
本目标连这条路都没有 ⇒ `untested`。**两者都不是 `fail`。**

> 本子节为 v1.1 新增：v1 冻结时 T06 的实现签名是
> `status_of(target_has_cache_sharing, spec)`，但**当时无人调用它**——
> runner 直到 2026-10-02 才接上这条线。接线时发现原签名会把类词汇漏进 runner，故刷新为传清单。
> **必需面（§2 的五个常量 + 两个数据类 + 五个函数）一字未改。**

---

## 4. 卡与脚本的接线

| 卡上 | 指向 |
|---|---|
| `execution.mode` | `declarative`（逻辑在类模块，本卡只给参数）/ `script_hook`（独立逻辑） |
| `execution.script` | **两种模式都必填**：本方法可执行形态的路径（declarative → `scripts/` 下的派生脚本；script_hook → 手写脚本）。须存在（规则 9） |
| `execution.args` | 传给类模块或脚本的**结构性参数**。**不得含载荷正文**（禁令 9，规则 45 扫） |

---

## 5. 脚本的合格标准（`docs/delivery-form.md` §1，因不要求跑而**不是**"能运行"）

| # | 标准 |
|---|---|
| **S1** | **自足**——一个懂行的人照着脚本能实现，不需要再回去查文献 |
| **S2** | **有出处**——脚本里每一处关键构造都能对回卡上的 `provenance_components` |
| **S3** | **可组合**——维度档位是参数，不是硬编码（由 `plan_grid` 保证） |
| **S5** | **接口统一**——实现本节 §2 的必需面 |

**其它工程要求**：只依赖 Python 标准库 + `harness/` 已提取模块；**无网络调用**（NF2）；

---

## 6. 一致性证据（三份独立实现对照）

| 项 | T01 | T03 | T06 |
|---|---|---|---|
| `CASE_ID` / `CARD_DIR` / `ENTRY_TOOL` / `EVIDENCE_LAYER` / `NON_PARAMETRIC` | ✅ | ✅ | ✅ |
| `MethodSpec` / `spec_from_card` / `build_plan` / `plan_grid` / `main` | ✅ | ✅ | ✅ |
| 载荷规格类名（自定） | `InjectionSpec` | `DeliverySpec` | `ProbeSpec` |
| `validate` | ✅ | ✅ | 未单列 |
| `load_card` / `custom_builder` / `_all_cards` | ✅ | ✅ | 未单列 |
| 接口答复文档的章节 | Q1–Q4 + 五 | Q1–Q4 + 五 | Q1–Q4 + 五 |

**结论**：必需面由三份互不可见的实现自然收敛，**故冻结**。§2.3 中 T06 未单列的三项
（`validate` / `load_card` / `custom_builder`）不是必需面的一部分，属建议实现。

---

## 7. 冻结后怎么改

1. **必需面的任何改动**都必须走变更提案（照 `docs/` 的规格），
   并同步全部八份类模块；
2. **扩展**可自由增加，但若在两类以上重复出现且语义相同，应提议并入 §3；
3. 本文件的哈希进报告头；改它 = 发布新版本。

---

## 8. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| `script-interface-v1.1` | 2026-10-02 | **必需面未改**。新增 §3.1：`status_of` 的接线约定与状态语义；§3 表格中 T06 扩展的签名由 `status_of(target_has_cache_sharing, spec)` 刷新为 `status_of(observables, spec)`（理由：原签名会把类别词汇漏进通用 runner）。触发原因：runner 首次真正调用该扩展（`harness/runner.py` 的 `class_status`） |
| `script-interface-v1` | 2026-09-29 | 初版并冻结。依据 T01/T03/T06 三份独立实现的一致性；规定五个常量 + 两个数据类 + 五个函数为必需面；列出允许的扩展与「只增不改」约束 |