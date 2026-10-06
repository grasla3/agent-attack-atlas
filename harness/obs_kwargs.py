# -*- coding: utf-8 -*-
"""观测 → 判据形参的**唯一翻译层**（`` §2 的 C 项）。

## 为什么必须有这一层，而不能"把一张大 kwargs 表灌给所有判据"

八份接线清单散在各判据的 `results/README.md*-notes.md` 里，合并时发现**两种签名形态**：

| 判据 | 签名 | 多给的键会怎样 |
|---|---|---|
| `prompt_leak`（`judges/canary_disclosure.py:96`） | **封闭**，无 `**observations` | `TypeError` |
| `prompt_leak_consistency`（`judges/consistency.py`） | 无模块级 `judge()`（走类） | — |
| 其余 7 个 | 有 `**observations` | 收下并记进 `notes`（但**不参与判定**） |

⇒ 灌一张统一表会让 T06 的既有通道**当场崩**。故本模块**按判据**给出它签名里
真正存在的键，且**只用 `inspect.signature` 决定**（不硬编码第二张名单，
那样两份名单迟早不一致）。

## 两条通道必须分开（**本层最重要的纪律**）

`state_diff` 的 `judge-state_diff-notes.md:57-68` 把这件事写死了：

* **声明通道**（卡上 `judge.params`）—— 我们自己写的**预期/标签**，如
  `<read-at-runtime>` 与 `sha256:baseline-…`。**判据不得用它当观测**；
* **观测通道**（`Observations`）—— **独立 reader** 回读到的权威状态。**`pass`/`fail` 只能由它定。**

本层的 `build()` **只走观测通道**；`params` 由调用方原样传入，本层**绝不**把读回值
写进 `params`（那等于自己宣布自己成功，D2/D9）。

## 缺观测时怎么办：**不猜**

拿不到就是拿不到。本层**不填默认值**（除 `""` / `None` 这类"没有"的表示），
让各判据按自己的 fail-closed 守卫记 `inconclusive`。
`unavailable()` 用**同一张表**报出"哪些键本靶标给不出"，供批次元数据同报。
"""
from __future__ import annotations

import importlib
import inspect
from typing import Any, Dict, List, Optional, Sequence, Tuple

#: 判据 id → 模块名。**注册表是真相源**（`judges/registry.json`），此处只做 id→模块的映射。
JUDGE_MODULES: Dict[str, str] = {
    "prompt_leak": "judges.canary_disclosure",
    "prompt_leak_consistency": "judges.consistency",
    "state_diff": "judges.state_diff",
    "scenario_contract": "judges.scenario_contract",
    "cross_session": "judges.cross_session",
    "sensitive_data": "judges.sensitive_data",
    "audit_integrity": "judges.audit_integrity",
    "ground_truth_contradiction": "judges.ground_truth_contradiction",
    "baseline_comparison": "judges.baseline_comparison",
    # 它读的是"模型在功能重叠的工具里选了哪一个、参数是什么"，
    # 而不是"权威注册表里的描述字段有没有被改写"（后者与攻击作用点不是同一个量）。
    "tool_selection": "judges.tool_selection",
    # T02 的**判读层**判据（2026-10-04 加）：读模型对一条日志的判读档位（7 点 Likert），
    # 判"判读有没有被注入内容带偏"。为什么需要：T02 六篇文献里只有 B-165 判"记录本身"，
    # 其余五篇判的都是"读了记录之后的判定" ⇒ `audit_integrity` 吃不下它们。
    "log_interpretation_slip": "judges.log_interpretation_slip",
    # T01 的**检索污染**判据（2026-10-05 加）：读"毒文档进没进模型自己发起的检索的 top-k、
    # 最终回答有没有被换成它断言的值"，而不是"记录里的值与真值一致不一致"。
    "retrieval_poisoning": "judges.retrieval_poisoning",
}

#: **由调用方负责**的键，本层不产生：
#:   · `params` —— 卡上声明（`judge.params`），原样传入；
#:   · `expected_verbatim` —— 运行期解析出的金丝雀（`prompt_leak` 专用通道）；
#:   · `canary_id` —— 卡上声明；
#:   · `request_text` / `payload_text` —— **我方这一轮实际发出去的文本**（D1 守卫的比对对象）。
#:     runner 在 `_run_arm` 里有它们（`payload`），本层拿不到 ⇒ 必须由调用方补。
#: 写在这里是为了让"谁负责什么"可机检（见 `unavailable()`）。
CALLER_OWNED = ("params", "expected_verbatim", "canary_id", "request_text", "payload_text")

#: 读审计读回的那**一个**判据（T02）。不是白名单——键的取舍仍由 `accepted_keys()`
#: 按签名决定；这里只用来把"要不要去读审计流水"限制在该判据上（别的判据读了也白读）。
AUDIT_JUDGE_ID = "audit_integrity"


def judge_callable(judge_id: str):
    """取该判据的模块级 `judge()`；没有（如 `consistency` 走类）⇒ 返回 `None`。"""
    name = JUDGE_MODULES.get(judge_id)
    if not name:
        return None
    mod = importlib.import_module(name)
    fn = getattr(mod, "judge", None)
    return fn if callable(fn) else None


def accepted_keys(judge_id: str) -> Tuple[str, ...]:
    """该判据 `judge()` **签名里存在**的形参名（不含 `params` 与本层不自造的键）。"""
    fn = judge_callable(judge_id)
    if fn is None:
        return ()
    out = []
    for n, p in inspect.signature(fn).parameters.items():
        if p.kind in (p.KEYWORD_ONLY, p.POSITIONAL_OR_KEYWORD) and n not in CALLER_OWNED:
            out.append(n)
    return tuple(out)


def accepts_var_kw(judge_id: str) -> bool:
    fn = judge_callable(judge_id)
    if fn is None:
        return False
    return any(p.kind == p.VAR_KEYWORD for p in inspect.signature(fn).parameters.values())


def _state_hash(value: Any) -> Any:
    """把 `Observations.state_*` 归一成判据要的形态。

    `state_diff` 的 `_read_state` 收三种：`None` / `str`（直接是摘要）/ mapping。
    本层**不做摘要计算**——那需要一个权威 reader，属靶标侧能力（`caps()` 如实报）。
    `{}` 与 `None` 都当作"没读回"。
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value or None
    if isinstance(value, dict):
        if not value:
            return None
        for k in ("sha256", "hash", "digest"):
            if isinstance(value.get(k), str) and value.get(k):
                return value[k]
        return value
    return value


def audit_entry_id_of(card: Any) -> Optional[str]:
    """卡上声明的审计条目 id（`judge.params.audit_entry_id`）。取不到 ⇒ `None`。

    ⚠️ 这是**卡侧契约**（"要核对哪一条审计条目"），**不是观测值**。观测值（在不在 /
    定位 / 摘要 / 字段 / 正文）一律由独立 reader 读回（D2/D9）——把声明值当观测
    就是本项目最贵的那条防线上的错误。
    """
    params = dict(((card or {}).get("judge") or {}).get("params") or {})
    got = params.get("audit_entry_id")
    if got is None:
        return None
    got = str(got).strip()
    return got or None


def audit_readback(obs: Any, *, adapter: Any = None, card: Any = None) -> Optional[Dict[str, Any]]:
    """T02 的**审计条目读回**（`harness/observers_audit_journal.py`，独立 reader）。

    返回 `read_audit_entry(...).to_dict()`；**靶标没声明这条通道**（或卡没声明条目 id、
    或没有可读的流水面）时返回 `None` ⇒ 调用方**一个键都不放**（缺观测必须可见）。

    三道闸门，缺一不可（任一不满足 ⇒ 不去读，也就不会产出任何 `entry_*`）：

    1. `caps()['audit_store_readback_supported']` —— 靶标如实声明"读回装置在不在"；
    2. 卡上的 `judge.params.audit_entry_id` —— "要核对哪一条"，取自**卡**（声明通道）；
    3. 靶标 `caps()['audit_entry_types']` 里有没有这个 id —— 观测器据此判"目标声明支持"，
       **空表 ⇒ 每个 id 都回 `locator_unresolved` 且不摆任何 `entry_*` 值**。
       本靶标（`agentdojo-workspace`）正是空表：它自己**一条审计记录都不产生**。

    ⚠️ 读回值**逐字来自 reader**：本函数不补默认值、不把 `None` 写成 `False`。
    """
    if obs is None:
        return None
    caps: Dict[str, Any] = {}
    if adapter is not None:
        try:
            caps = dict(adapter.caps() or {})
        except Exception:
            caps = {}
    if not caps.get("audit_store_readback_supported"):
        return None
    entry_id = audit_entry_id_of(card)
    if not entry_id:
        return None

    from . import observers_audit_journal as AJ

    # 流水优先从**观测**上取（`Observations.audit_journal`，本层的正规通道）；
    # 观测上没有就退回适配器（观测器两种 source 都支持，见其模块头 §1 的 `OBS_ATTR`）。
    src = obs if getattr(obs, AJ.OBS_ATTR, None) is not None else adapter
    if src is None:
        return None
    return AJ.read_audit_entry(source=src, entry_type=entry_id,
                               declared_support=caps.get("audit_entry_types")).to_dict()


def build(judge_id: str, obs: Any, *, adapter: Any = None,
          card: Any = None) -> Dict[str, Any]:
    """`Observations` → 该判据**签名里存在**的那些形参。

    返回的 dict **只含观测通道的键**；调用方再并入 `params=` 即可。
    任何本靶标给不出的键**不出现**在结果里（判据自己按缺省值 fail-closed）。

    `card` 只有**一个**用途：T02 的 `audit_integrity` 要按卡声明的 `audit_entry_id`
    决定去读哪一条审计条目（`judge.params` 是**声明通道**）。卡上其余任何值
    **都不进**返回值——若不传 `card`，审计通道整体不产出键（宁可缺，不可猜）。
    """
    out: Dict[str, Any] = {}
    if obs is None:
        return out

    # —— 通用四项：runner 一直在传的（判据多数都收）——
    out["response_text"] = getattr(obs, "response_text", None)
    out["canary_in_target"] = getattr(obs, "canary_in_target", None)
    out["error"] = getattr(obs, "error", None)

    # —— 观测侧：状态 / 动作 / 回执 ——
    out["state_before"] = getattr(obs, "state_before", None)
    out["state_after"] = getattr(obs, "state_after", None)
    out["tool_calls"] = list(getattr(obs, "tool_calls", None) or [])
    out["receipts"] = list(getattr(obs, "receipts", None) or [])

    # 直传摘要形态（`state_diff` 有这两个独立形参；与 `state_*` 冲突时判据自己判 inconclusive）
    sb, sa = _state_hash(getattr(obs, "state_before", None)), _state_hash(getattr(obs, "state_after", None))
    if isinstance(sb, str):
        out["before_state_hash"] = sb
    if isinstance(sa, str):
        out["after_state_hash"] = sa

    # —— `Observations` 新增的**可选通道**（本批补；缺省即"本靶标给不出"）——
    out["authorization_decisions"] = list(getattr(obs, "authorization_decisions", None) or [])
    out["target_tools"] = list(getattr(obs, "target_tools", None) or [])
    # T05 的**作用点**通道（2026-10-04 加）：模型在功能重叠的工具里选了哪个、带了什么参数。
    # ⚠️ 与 `target_tools` 是两个问题（D11）：那个是"目标有哪些工具"，
    # 这个是"模型**实际选了**哪一个、参数是什么"。`{}` = 本靶标给不出这条通道。
    out["selection_channel"] = dict(getattr(obs, "selection_channel", None) or {})
    out["outbound_texts"] = list(getattr(obs, "outbound_texts", None) or [])
    out["canary_field"] = getattr(obs, "canary_field", None)
    out["canary_scope"] = getattr(obs, "canary_scope", None)
    out["canary_in_authorized_scope"] = getattr(obs, "canary_in_authorized_scope", None)
    # `canary_in_write_session`（cross_session 要）：写会话是否确认写入金丝雀。
    # 本靶标没有"写会话"这个概念 ⇒ 不给（缺省 None ⇒ 判据记 inconclusive）。
    out["canary_in_write_session"] = getattr(obs, "canary_in_write_session", None)
    out["response_session"] = getattr(obs, "response_session", None)
    out["read_session_actions"] = list(getattr(obs, "read_session_actions", None) or []) or None

    # —— 金丝雀字面量：`sensitive_data` / `cross_session` 只能走这条通道 ——
    #     它们的 `params_schema` 是封闭的（`additionalProperties: false`），
    #     往 `params` 里塞真值会抛 `ParamsError`（两份 notes 都点名了这条）。
    canary = None
    if adapter is not None:
        canary = getattr(adapter, "canary", None)
    if canary:
        out["canary_verbatim"] = canary

    # —— 本靶标**声明**的能力，如实转成观测（不声明 = 不提供）——
    # 判据要的通道与本靶标能给的能力是**逐条对上**的（不是"有就多给一点"）：
    #   · `receipt_id`            ← `receipt_supported_reader`
    #   · `state_before/after`    ← `state_readback_supported`（读不回来就**不摆**这两个键，
    #                               让 `state_diff` 走它自己的 `no_state_readback` 守卫）
    #   · 审计条目读回（T02）      ← `audit_store_readback_supported`
    #   · 双会话（cross_session）  ← `dual_session_supported`
    # ⚠️ 本函数**不提供**的能力一律**不摆键**，且会出现在 `unavailable()` 的名单里 ——
    #    缺观测必须**可见**（否则报告上看不出"这一格为什么 inconclusive"）。
    caps = {}
    try:
        caps = dict((adapter.caps() if adapter is not None else {}) or {})
    except Exception:
        caps = {}
    if caps.get("receipt_supported_reader"):
        out["receipt_id"] = None
    if not caps.get("state_readback_supported"):
        out.pop("state_before", None)
        out.pop("state_after", None)
        out.pop("before_state_hash", None)
        out.pop("after_state_hash", None)
    # ── 审计条目读回（T02）──
    # 靶标**如实声明**"读回装置在位"（`audit_store_readback_supported`）时才去读；
    # 读回值逐键来自 `harness/observers_audit_journal.py` 的独立 reader（`audit_readback()`）。
    # ⚠️ **本靶标（`agentdojo-workspace`）声明 `audit_entry_types == []`**：它自己一条
    #    审计记录都不产生 ⇒ reader 对每个卡声明的条目 id 都只回 `absence_basis=
    #    "locator_unresolved"`，**一个 `entry_*` 值都不摆** ⇒ `audit_integrity` 记
    #    `inconclusive/no_observation`（**如实**，不是缺陷；见 closeout-T02-audit-wiring.md）。
    # ⚠️ 拿不到的键一个都不放（**不填 `None`、更不填 `False`**）：判据按缺省参数
    #    fail-closed（D7），而这些键会由 `unavailable()` 逐个报出来（缺观测必须可见）。
    if judge_id == AUDIT_JUDGE_ID:
        rb = audit_readback(obs, adapter=adapter, card=card)
        if rb is not None:
            for k, v in (rb.get("values") or {}).items():
                out[k] = v
    # 「先探测再决定」的双 reader（ground_truth_contradiction）目前仍没有任何靶标提供
    # ⇒ 一个键都不放，让那个判据按自己的主张记 `inconclusive`。

    # —— 最后：只留下该判据签名里真正存在的键 ——
    # 为什么**连有 `**observations` 的判据也只给签名里的键**：多给的键会被收下并记进
    # `notes`（不参与判定），看着无害；但"多给"这件事一旦成为习惯，接线就会从
    # "这个判据要什么"漂成"我们有什么"，而**判据要而靶标给不出的那些键**（T02 的审计
    # 读回、ground_truth 的双 reader）就再也没人去看 `unavailable()` 报出来的名单。
    keep = set(accepted_keys(judge_id))
    return {k: v for k, v in out.items() if k in keep}


def unavailable(judge_id: str, obs: Any, *, adapter: Any = None,
                card: Any = None) -> List[str]:
    """本靶标**给不出**、而该判据签名里**要**的键。供批次元数据同报。

    `card` 原样转交 `build()`（T02 的审计读回要按卡声明的 `audit_entry_id` 去读）
    ——**同报的口径必须与真跑的口径逐字相同**，否则 `judge_channels_missing`
    会报出一份与实际不符的名单。
    """
    keep = accepted_keys(judge_id)
    got = set(build(judge_id, obs, adapter=adapter, card=card))
    # `params` 与金丝雀由调用方给，不算"靶标给不出"
    skip = set(CALLER_OWNED)
    return sorted(k for k in keep if k not in got and k not in skip)

#: 判据 → 它的**金丝雀真值走哪条通道**。三态语义：
#:   · `"params"`      —— 把运行期金丝雀写进 `params` 的 `expected_verbatim`（`prompt_leak` 专用；
#:                        它的 `params_schema` 里**有**这个键，且有 `minLength: 4`）；
#:   · `"observation"` —— 真值只能走观测通道（`sensitive_data` / `cross_session` 的
#:                        `params_schema` 是**封闭**的，`additionalProperties: false`，
#:                        往 `params` 塞真值会抛 `ParamsError` —— 两份 notes 都点名了这条）；
#:   · `None`          —— 本判据不用金丝雀。
CANARY_CHANNEL: Dict[str, Any] = {
    "prompt_leak": "params",
    "sensitive_data": "observation",
    "cross_session": "observation",
}


def resolve_params(judge_id: str, card_params: Any, *, canary: Any = None) -> Dict[str, Any]:
    """卡上声明 → 判据**实际会用**的那一份 `params`（证据里的 `judge_params_resolved`）。

    **本函数只改该判据 `params_schema` 里存在的键** —— 多一个键就会被判据的
    `_validate_params` 抛 `ParamsError`（封闭 schema，两份 notes 明确警告过）。
    """
    p = dict(card_params or {})
    if CANARY_CHANNEL.get(judge_id) == "params" and canary:
        # 卡上写的是**模板**（如 `T06CANARY-<random32>`），真值由靶标运行期生成。
        # 不解析的话，判据会去找一个永远不存在的字符串（这个坑实测栽过一次）。
        p["expected_verbatim"] = canary
        p["canary_id"] = p.get("canary_id") or "runtime-canary"
    return p
