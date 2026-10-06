# -*- coding: utf-8 -*-
"""`harness/` 的两个协议与注册表。**runner 只认这里的契约，不认任何具体类别或靶标。**

设计依据：`docs/runner-design.md` §2（四个契约）与 §4（七阶段）。

为什么用 `Protocol` 而不是基类：类模块与适配器是**两拨人写的**，
用结构化协议可以让"没继承任何东西"的实现也通过检查，避免为了继承而继承。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

# ───────────────────────── 靶标 ─────────────────────────

@dataclass
class InjectionReceipt:
    """一次投放的回执。**只记事实，不记结论**。"""

    vector: str
    turn: int
    placed: bool
    detail: str = ""


@dataclass
class Observations:
    """判据的**全部**输入。判据不得从别处取数（D9：自证字段旁路）。"""

    response_text: Optional[str] = None      # None = 没取到观测（≠ 空串，见 D7）
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    state_before: Dict[str, Any] = field(default_factory=dict)
    state_after: Dict[str, Any] = field(default_factory=dict)
    receipts: List[Dict[str, Any]] = field(default_factory=list)
    canary_in_target: Optional[bool] = None  # 由**独立 reader** 回读，三态
    error: Optional[str] = None              # 调度/测量失败的原因（产生 inconclusive）

    #: **目标侧的真值文本**（本靶标种进去的那份定义本身，如系统提示词）。
    #: 供**副观测**比对复原保真度用（`harness/observers.py`）。
    #: `None` = 本靶标提供不了 ⇒ 副观测记 `reference_unavailable`，**不给数**（R2）。
    #:
    #: ⚠️ 它不是判据的输入：判据只认 `response_text` 与 `canary_in_target`（D9）。
    #: 条件 B 下它是**原始系统提示词 S**（不含夹层/追加的安全指令）——攻击者想要的是那份。
    reference_definition: Optional[str] = None

    #: **防御介入的事实**（条件 B 的输出侧过滤）。`{}` = 本靶标无输出侧防御。
    #: 取值域见 `harness/defenses.py` 的 `filter_response()`：
    #: `{"fired": bool, "rule": str, "matched_words": int, "pre_filter_sha256": str, ...}`。
    #:
    #: 为什么必须记：过滤会**改变判据看到的东西**，不记就分不清
    #: "模型拒答了" 与 "模型说了但被抹掉了"（`docs/README.md` D19 明文要求）。
    defense: Dict[str, Any] = field(default_factory=dict)

    # —— 以下四项由本批（C 项接线）新增，**全部可选、缺省即"本靶标给不出"** ——
    #: 授权判定记录（`scenario_contract` 要）。`[]` = 本靶标没有这道闸门。
    authorization_decisions: List[Dict[str, Any]] = field(default_factory=list)

    #: 目标**真实**工具面（`scenario_contract` 要）。`[]` = 未声明。
    #: ⚠️ 与 `caps()["observables"]` 是两个问题：这是"目标有哪些动作"，
    #: 那个是"我们能看见什么"（**D11**）。
    target_tools: List[str] = field(default_factory=list)

    #: **「选择」通道**（T05 的 `tool_selection` 判据要；2026-10-04 加）。`{}` = 本靶标给不出。
    #:
    #: 为什么单列一项：T05 卡上的机制是「模型在**功能重叠的工具**之间选了哪一个」
    #: （`methods/T05/cards/T05_LIT-B-85_*.yaml` 的 assumptions 逐字："目标在多个功能重叠的
    #: 工具间做选择，选择依据包含工具描述文本"），而卡上 `judge.params` 一直声明的是
    #: `(mcp_tool_registry, description)` —— **判据读的量与攻击的作用点不是同一个量**。
    #: 这一通道把作用点本身（选了哪个、带了什么参数）摆到判据面前。
    #:
    #: 取值（由靶标填，**只记模型实际发出过的调用**）：`first_candidate_call` /
    #: `candidates` / `per_tool_calls` / `observations[{tool, arguments}]` / `target_tools`。
    selection_channel: Dict[str, Any] = field(default_factory=dict)

    #: **出站侧**原始取证文本（`sensitive_data` 的 `outbound_texts`）。`[]` = 没有出站面。
    outbound_texts: List[str] = field(default_factory=list)

    #: 金丝雀的**归属三态**（`sensitive_data` 要）：
    #:   · `canary_field` 这枚金丝雀标记的是哪个字段；
    #:   · `canary_scope` 它所属的范围标识；
    #:   · `canary_in_authorized_scope` 它是否落在发起方主体的授权范围内（三态：`None` = 没验）。
    #: 三项都**必须由独立来源**填，判据不得自己推断（D2）。
    canary_field: Optional[str] = None
    canary_scope: Optional[str] = None
    canary_in_authorized_scope: Optional[bool] = None

    #: `cross_session` 要的两个通道：写会话是否确认写入（三态）、这份回复取自哪个会话。
    #: 本靶标是单会话形态 ⇒ 两者都缺省 `None`，判据据此记 `inconclusive`（**如实**）。
    canary_in_write_session: Optional[bool] = None
    response_session: Optional[str] = None
    #: 读会话的真实动作记录（`cross_session` 的 `read_session_actions`）。
    read_session_actions: Optional[List[Dict[str, Any]]] = None

    #: **审计流水**（T02 / `harness/observers_audit_journal.py`）。`None` = 本靶标给不出。
    #:
    #: 它是**独立 reader 的读回面**：`harness/obs_kwargs.py` 的 `audit_readback()` 从这里
    #: 取出 `audit_integrity` 要的那批权威读回（`entry_present_*` / `entry_locator_*` /
    #: `entry_sha256_*` / `entry_fields(_read)` / `entry_text_*` / `absence_basis`）。
    #: 观测→形参的翻译**只在 `harness/obs_kwargs.py` 一处**发生。
    #:
    #: ⚠️ **判据不得直接读它**（D9）：判据只认形参，而形参由翻译层从读回值填。
    #: ⚠️ 它回答的是"**能不能读回**"，**不是**"目标有没有审计记录"——后者由靶标
    #: `caps()['audit_entry_types']` 如实声明（本靶标为**空表** ⇒ 一个 `entry_*` 值都给不出）。
    audit_journal: Any = None

    #: 攻击**被拦在第几个防御层**。取值域是 `score/core.py` 的 `LAYER_ORDER`
    #: （9 个防御层名）或 `"real_effect"` / `"no_observation"`；
    #: **`None` 表示本靶标拿不到这一项**（防御栈不可配置），此时 `depth` 分量算不出来。
    #:
    #: ⚠️ **不要把它和证据层混起来。** 本项目里有两套都叫 "layer" 的词汇表：
    #:   · 证据层 `text/behavior/authorization/state/causal` —— 进 `impact()`
    #:   · 防御层 9 个名字 —— 进 `depth_from_layer()`
    #: 实测踩过一次：把证据层喂给 `depth_from_layer()` 会抛「未知防护层」（2026-10-01）。
    deepest_defense_layer: Optional[str] = None


@runtime_checkable
class TargetAdapter(Protocol):
    """靶标适配器。**八类的差异不在这里**，这里只有"目标能做什么"。"""

    target_id: str

    def tools(self) -> List[str]:
        """本目标暴露的工具/动作名清单。对应 TargetProfile.tools。"""

    def design_dimensions(self) -> Dict[str, int]:
        """Kim 7 维档位。对应 TargetProfile.design_dimensions。"""

    def caps(self) -> Dict[str, Any]:
        """本目标**如实**声明自己能做什么。取值**全部可选**，缺省即"未声明"。

        | 键 | 类型 | 语义 |
        |---|---|---|
        | `cleanup_supported` | `bool` | 有幂等 restore + 独立 cleanup reader |
        | `receipt_supported` | `bool` | 有请求绑定回执 |
        | `entry_surfaces` | `List[str]` | 本靶标**真正实现了**的投放面（取值域同 `inject()` 的 `vector`） |
        | `observables` | `List[str]` | 本靶标**真正能观测**的装置名（如 `response_timing` / `cache_sharing`） |

        ⚠️ `entry_surfaces` 与 `observables` 是**两个问题**，不得混用（**D11**）：
        前者问"载荷写不写得进去"，后者问"测量看不看得见"。

        ⚠️ `entry_surfaces` **只作声明与报告用，不作判定闸门**——判"投得进去没有"
        以 `inject()` 的 `InjectionReceipt.placed` 为**唯一权威**（那是一次真实尝试的回执，
        而声明是一句话）。理由详见 `docs/README.md` §3。
        """

    def reset(self) -> None:
        """复位到初始态。**清不了必须抛异常**，由 runner 记 inconclusive。"""

    def inject(self, *, vector: str, payload: str, turn: int) -> InjectionReceipt:
        """按 `vector` 把 payload 放到目标的可达面上。"""

    def run_task(self, *, max_turns: int) -> None:
        """让目标跑起来。"""

    def observe(self) -> Observations:
        """取观测。**这是判据的唯一输入来源。**"""

    def cleanup(self) -> None:
        """清场。不支持时是 no-op，但 `caps()` 必须如实报 false。"""


# ───────────────────────── 判据 ─────────────────────────

@runtime_checkable
class Judge(Protocol):
    """判据。实现见 `judges/`。"""

    judge_id: str

    def __call__(self, *, params: Dict[str, Any], **obs: Any) -> Any:
        """返回带 `.verdict` 的对象。取值只允许 pass/fail/inconclusive/not_applicable。"""

    def params_for(self, card: Dict[str, Any]) -> Dict[str, Any]:
        """**可选**。返回判据**实际会被调用时**使用的参数（模板里的占位须在此解析）。

        为什么要有这一条：卡的 `judge.params` 里 `expected_verbatim` 是**模板**
        （如 `T06CANARY-<random32>`），真实金丝雀由靶标在运行期生成。若证据只记模板，
        则 trial 文件**复算不出它自己记的判定**——那正是 D1"文件为真相源"的反面。

        实现方不提供本方法时，runner 记 `judge_params_source = "card_declared"`
        并在证据里如实标注 **不可复算参数**，不假装可复算。
        """


# ───────────────────────── 副观测 ─────────────────────────

@runtime_checkable
class Observer(Protocol):
    """**副观测**：额外的测量，**不进六态、不进评分路径**。

    为什么单列一个协议而不是塞进 `Judge`：判据产出"成没成"（六态），
    副观测产出"成得怎么样"（连续的诊断量）。两者混在一个契约里，
    迟早会有人把诊断量喂进评分（R9：两把尺子不混排）。

    实现见 `harness/observers.py`。runner 不认任何具体观测器，
    只按 `observers=` 传进来的清单逐个调用。
    """

    observer_id: str

    #: **可选**。声明"把哪个键当率来聚合"：结果里的该键若可转成数，
    #: runner 会在对抗臂上求均值，写进 `CellResult.observer_rates[observer_id]`。
    #: 例如防御介入观测器声明 `rate_key = "fired"`（0/1）⇒ 格级得到**介入率**。
    #: 不声明则只逐 trial 记录、不做格级聚合（runner 不猜哪个键是率）。
    rate_key: Optional[str] = None

    def __call__(self, *, card: Dict[str, Any], observations: Any,
                 request_text: str = "", payload_text: str = "") -> Optional[Dict[str, Any]]:
        """返回一个 JSON 可序列化的 dict；给不出就返回 `None` 或带 `reason` 的 dict。"""


# ───────────────────────── 注册表 ─────────────────────────

_ADAPTERS: Dict[str, Any] = {}
_JUDGES: Dict[str, Any] = {}


def register_adapter(target_id: str, factory) -> None:
    if target_id in _ADAPTERS:
        raise ValueError("适配器重复注册：%s" % target_id)
    _ADAPTERS[target_id] = factory


def get_adapter(target_id: str, **kwargs) -> TargetAdapter:
    if target_id not in _ADAPTERS:
        raise KeyError("未注册的靶标 %r；已注册：%s"
                       % (target_id, ", ".join(sorted(_ADAPTERS)) or "（无）"))
    return _ADAPTERS[target_id](**kwargs)


def register_judge(judge_id: str, fn) -> None:
    _JUDGES[judge_id] = fn


def get_judge(judge_id: str) -> Judge:
    if judge_id not in _JUDGES:
        raise KeyError("未注册的判据 %r；已注册：%s"
                       % (judge_id, ", ".join(sorted(_JUDGES)) or "（无）"))
    return _JUDGES[judge_id]


def available() -> Dict[str, List[str]]:
    return {"adapters": sorted(_ADAPTERS), "judges": sorted(_JUDGES)}