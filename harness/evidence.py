# -*- coding: utf-8 -*-
"""证据束：一次 trial 的**全部**可复算材料。

为什么单独立一个模块：`docs/README.md` **D1** 定的是"文件为真相源"，
而真相源要能被**独立复算**。若只存汇总（"pass / R_m=3.2"），复算不可能——
这一条是本模块存在的全部理由。

设计约束（都来自已发生的事故）：
  · 判据的输入**只能**来自 `Observations`（`harness/protocol.py`），
    不得从证据束里另取"verified"字段（**D9**：自证字段旁路）。
  · **载荷正文不入库**（禁令 9 / `spec/method-script-interface.md` S4）。
    证据束只存 `payload_sha256` 与 `payload_len`，正文由运行期生成、不入盘。
  · `response_text` 的 `None` 与 `""` 必须分开存（**D7**：测量失败 ≠ 阴性观测）。
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional

#: 模板占位符的形态。**这一条是"证据能不能复算"的最后一道守卫**，故宁可从严：
#:   · `<...>`（如 `<read-at-runtime>` / `T06CANARY-<random32>`）
#:   · `[待校准]`（禁令 10 的既有约定）
#:   · `sha256:baseline-…` / `sha256:attacked-…` —— 卡上 29 张 `state_diff` 用的**标签**，
#:     不是真摘要（`judges/state_diff.py` 的 `_is_hex_hash()` 判否）
_PLACEHOLDER = re.compile(r"<[^>]*>|\[待校准\]|sha256:(?:baseline|attacked)-")


def has_unresolved_placeholder(params: Any) -> bool:
    """`params` 里还有没有**未解析的模板占位符**。有 ⇒ 这份证据复算不出它自己。"""
    if isinstance(params, str):
        return bool(_PLACEHOLDER.search(params))
    if isinstance(params, Mapping):
        return any(has_unresolved_placeholder(v) for v in params.values())
    if isinstance(params, (list, tuple)):
        return any(has_unresolved_placeholder(v) for v in params)
    return False


SCHEMA = "trial_evidence_v1"


@dataclass
class TrialEvidence:
    """一个 (方法, 靶标, 第 i 次) 格子的全部材料。"""

    schema: str = SCHEMA
    batch_id: str = ""
    method_id: str = ""
    target_id: str = ""
    trial_index: int = 0

    # —— 输入侧（可复算所需）——
    case_id: str = ""
    judge_id: str = ""
    #: 卡上**声明**的判据参数。取自卡，未解析——它回答"这张卡要求判据拿到什么"。
    judge_params: Dict[str, Any] = field(default_factory=dict)
    #: 判据**实际被调用时**使用的参数（含运行期解析后的金丝雀）。
    #: 它回答"这一次判定到底拿什么去比"。**没有它，本文件复算不出自己的 `verdict`。**
    judge_params_resolved: Dict[str, Any] = field(default_factory=dict)
    #: `judge_params_resolved` 从哪来：`runtime`（由 `Judge.params_for` 解析）
    #: 或 `card_declared`（无人解析 ⇒ 如实标注为不可复算，不假装）。
    judge_params_source: str = ""
    required_actions: List[str] = field(default_factory=list)

    # —— 投放（只记事实）——
    arm: str = "adversarial"     # "adversarial" | "control"（配对良性对照）
    vector: str = ""
    turns: int = 0
    payload_sha256: str = ""
    payload_len: int = 0
    #: 载荷的**构造元数据**（框架 / 近似程度 / 出处 / 轮数 / 槽 token）——**不含载荷文本**。
    #: 它回答"这一格测的到底是不是这个方法"：`scope="generic"` 表示用的是兜底探针，
    #: **不得**当作该方法的效果（`ROADMAP.md` G-6 的病根就是这一栏以前不存在）。
    payload_meta: Dict[str, Any] = field(default_factory=dict)

    # —— 观测 ——
    response_text: Optional[str] = None
    response_captured: bool = False          # False ⇒ 测量失败，非阴性
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    # 以下四栏由 **C⑦** 落地（2026-10-03）：不落它们，`state_diff` / `scenario_contract`
    # 的结论就复算不出来 —— 判据的输入不进证据束，trial 文件复算不出它自己记的 `verdict`
    # （D1「文件为真相源」的反面）。
    receipts: List[Dict[str, Any]] = field(default_factory=list)
    state_before: Any = None
    state_after: Any = None
    #: **授权判定台账**（T03 的 `authorization_decisions[]`，2026-10-03 补）。
    #: 与上面三栏同规（C⑦）：判据的输入必须进证据束。此前它没落盘 ⇒
    #: `trial-*.json` 里复算不出 `scenario_contract` 为什么报 `authz_baseline_missing`
    #: —— 当前实现实测踩过：`observe()` 明明给了（本地直跑可打出基线 `deny` 与服务器那条），
    #: 落盘时被丢掉 ⇒ 判据拿到空表 ⇒ T03 的 5 张可跑卡恒 `inconclusive`。
    authorization_decisions: List[Dict[str, Any]] = field(default_factory=list)
    canary_in_target: Optional[bool] = None
    error: Optional[str] = None
    #: **本靶标给不出、而该判据签名里要**的观测通道（`harness/obs_kwargs.unavailable()`）。
    #: 它是"这一格为什么 inconclusive"的机器可读答案；不记就只能靠人读 notes。
    judge_channels_missing: List[str] = field(default_factory=list)

    # —— 判定与评分 ——
    verdict: str = ""
    verdict_reason: str = ""
    match_kind: Optional[str] = None
    six_state: str = ""                      # runner 判定的六态
    r_measured: Optional[Dict[str, Any]] = None
    source: str = "measured"

    #: **副观测**结果，按 `observer_id` 归档（`harness/observers.py`）。
    #: 与 `verdict` / `six_state` / `r_measured` **完全无关**——它不进六态、不进评分路径。
    #: 只入证据、只进报告的"第二列"（R9：两把尺子不混排）。
    observations_extra: Dict[str, Any] = field(default_factory=dict)

    # —— 环境（复现所需）——
    env: Dict[str, Any] = field(default_factory=dict)
    started_at: str = ""
    finished_at: str = ""

    def compute_payload_hash(self, payload: str) -> None:
        """只记哈希与长度，**不记正文**（禁令 9）。"""
        b = payload.encode("utf-8")
        self.payload_sha256 = hashlib.sha256(b).hexdigest()
        self.payload_len = len(b)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2, sort_keys=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")