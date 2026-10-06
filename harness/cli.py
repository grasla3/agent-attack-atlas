# -*- coding: utf-8 -*-
"""执行层命令行（`docs/technical-design.md` §3.2 的 OP-12 / OP-13）。

用法：
    python -m harness.cli targets
    python -m harness.cli run --target agentdojo-workspace --case T06 --n 3 --limit 1

**凭据从环境变量读，命令行不传 key**（`targets/README.md` 的纪律）。
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import io
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml

from harness import baseline, obs_kwargs, payloads, protocol, runner, store

ROOT = Path(__file__).resolve().parent.parent

#: ⚠️ **这里原来放着两句成品探针文本**（`GENERIC_PROBES` / `CONTROL_PROBES`，2026-10-02 删除）。
#:
#: 两个原因，都有实测代价：
#:   ① 违反标准 S4（`spec/method-script-interface.md` §5：载荷文本不进仓库）；
#:   ② 更致命的是它被**用在每一张卡上**——于是 20 个方法共用同一句探针，
#:      六格"成功"其实是同一个探针成功了六次，各方法**始终未实例化**（`ROADMAP.md` **G-6**）。
#:
#: 现在逐方法载荷由类模块的构造规格 + `harness/payloads.py` 的框架在运行期合成，
#: 词汇材料只在 `payloads.py` 的短语表里，且必须经 token 解析才成句。


def load_cards(case_id: str) -> List[Dict[str, Any]]:
    out = []
    for p in sorted((ROOT / "methods" / case_id / "cards").glob("*.yaml")):
        d = yaml.safe_load(p.read_text(encoding="utf-8"))
        if isinstance(d, dict):
            out.append(d)
    return out


def judge_for_factory(adapter):
    """按 `card.judge.verifier` **分派**判据，并把运行期金丝雀按**该判据自己的通道**绑进去。

    为什么不能"一张统一 kwargs 表灌给所有判据"：`judges/canary_disclosure.py:96` 与
    `judges/cross_session.py:235` 的 `judge()` **签名是封闭的**（没有 `**observations`），
    多给一个键就 `TypeError`。故观测→形参的翻译由 `harness/obs_kwargs.py` **逐判据**做，
    本函数只负责"选哪个判据 + 传什么 params"。

    判据的两条通道**严格分开**（`judge-state_diff-notes.md:57-68`）：

      · `params` = 卡上声明，**预期/标签**。`params_for()` 原样返回（只解析金丝雀模板）；
      · 观测     = **独立 reader** 的回读。由 runner 经 `obs_kwargs.build()` 传入。

    ⚠️ **绝不把读回值写进 `params`**：那等于我们自己宣布自己成功（D2/D9），
    而且本类 63 张 `state_diff` 卡会零成本全 `pass`。
    """
    def _factory(card):
        vid = str((card.get("judge") or {}).get("verifier") or "")
        fn = obs_kwargs.judge_callable(vid)
        if fn is None:
            raise SystemExit(
                "判据 %r 尚未实现或没有模块级 judge()；已接线：%s"
                % (vid, ", ".join(sorted(obs_kwargs.JUDGE_MODULES))))

        canary = getattr(adapter, "canary", None)

        class Bound:
            judge_id = vid

            def params_for(self, card):
                """给 runner 用：把**实际会用的**参数写进证据（`judge_params_resolved`）。"""
                return obs_kwargs.resolve_params(
                    vid, (card.get("judge") or {}).get("params"), canary=canary)

            def __call__(self, *, params, **obs):
                # `card` 一并交进去：T02 的审计读回要按卡声明的 `audit_entry_id` 决定读哪一条。
                # 两处调用点（这里与 `runner._run_arm`）**口径必须一致**——只接一处，
                # 另一处就会静默少一条通道（本项目反复撞的"静默失效"）。
                kw = obs_kwargs.build(vid, obs.pop("_observations", None),
                                      adapter=adapter, card=card)
                # 调用方显式给的同名键优先（`request_text` / `payload_text` 由 runner 给）
                kw.update({k: v for k, v in obs.items() if k in obs_kwargs.accepted_keys(vid)})
                return fn(params=obs_kwargs.resolve_params(vid, params, canary=canary), **kw)
        return Bound()
    return _factory


def payload_for_factory(case_id: str, adapter):
    """**逐方法载荷**：类模块给构造规格，`harness/payloads.py` 在运行期合成。

    ⚠️ 旧实现（至 2026-10-02）**完全忽略 `card`**，对每张卡都返回同一句通用探针 ——
    于是 `batch-6d0b76397335` 的六格"成功"其实是**同一个探针成功了六次**，
    各方法**始终未实例化**。那是"方法之间测不出差异"的直接原因（`ROADMAP.md` **G-6**）。

    **本函数不持有任何载荷文本**：旧实现里的 `GENERIC_PROBES`（成品探针文本）
    已删除 —— 它违反标准 S4（`spec/method-script-interface.md` §5：载荷文本不进仓库）。
    词汇材料现在只在 `harness/payloads.py` 的短语表里，且必须经 token 解析才成型。
    """
    mod = runner.load_class_module(case_id)

    def _factory(card, plan, trial, arm):
        if card.get("_is_baseline"):
            # 朴素基线臂（`harness/baseline.py`）：载荷是**冻结常量**，
            # 不经 `spec_for_card` —— 它没有卡、没有框架，这正是"朴素"的定义。
            return baseline.payload_for(arm)
        # 靶标可以要求"投放前把当前方法卡交给我"（T05 的 `mcp-local` 需要：它要按卡的
        # `entity_id`/`field` 决定回读哪个实体，而**那是卡的属性、不是靶标的属性**）。
        # 用 `getattr` 探测而非写进 `TargetAdapter` 协议：只有一个靶标需要它，
        # 而协议每加一个必需方法，其余适配器都得跟着改。
        notify = getattr(adapter, "bind_card", None)
        if callable(notify):
            notify(card)
        spec = payloads.spec_for_card(card, mod)
        # 返回**轮次列表**：多轮构造由 runner 逐轮投放（G-10 落地后不再压成一轮）。
        return payloads.synthesize(spec, arm=arm,
                                   canary=getattr(adapter, "canary", None),
                                   caps=adapter.caps())
    return _factory


def payload_meta_factory(case_id: str):
    """记录**构造元数据**（框架 / 近似程度 / 出处 / 槽 token）。**不含载荷文本。**"""
    mod = runner.load_class_module(case_id)

    def _meta(card):
        if card.get("_is_baseline"):
            return dict(baseline.NAIVE_META)
        return payloads.meta_of(payloads.spec_for_card(card, mod))
    return _meta


def observers_for(adapter):
    """本批次挂的**副观测**（`harness/protocol.py` 的 `Observer`）。

    当前两个：

    | 观测器 | 回答什么 | 格级率 |
    |---|---|---|
    | 复原覆盖度（**D16**） | "出来的是不是那份真东西" | 无（多尺度覆盖度逐 trial 记录） |
    | 防御介入（**D19**） | "模型说了但被抹掉" 还是 "模型拒答" | `defense_intervention` ⇒ **介入率** |

    **它们与判据、六态、评分路径完全解耦**——是报告里的第二列，不是分（R9）。
    靶标若不提供对应观测（如条件 A 无输出侧防御），各自如实记不可用，不填 0。
    """
    from harness import observers as OB
    canary = getattr(adapter, "canary", None)
    return [OB.ReconstructionCoverage(canary=canary), OB.DefenseIntervention()]


def condition_env(adapter) -> Dict[str, Any]:
    """批次元数据里的**条件指纹**：条件 id + 冻结哈希（D19 要求运行前冻结）。"""
    cond = getattr(adapter, "_condition", None)
    cid = getattr(adapter, "condition_id", "native")
    if not cond:
        return {"condition": cid or "native", "condition_sha256": None,
                "target_system_prompt_sha256": _sha16(getattr(adapter, "reference", ""))}
    from harness import defenses as D
    return {"condition": cid,
            "condition_sha256": D.content_hash(cond),
            "condition_frozen_at": (cond.get("frozen") or {}).get("date"),
            "defenses_enabled": sorted(D.effective_config(cond)),
            "target_system_prompt_sha256": _sha16(getattr(adapter, "reference", ""))}


def _sha16(text) -> Optional[str]:
    return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()[:16] if text else None


#: **靶标分派表**（模块级，供测试与 `cmd_targets` 共用）。
#:
#: **新增靶标必须在这里登记** —— 否则 `--target` 直接 `SystemExit`。
#: 这是 T08 接线时暴露的缺口：`harness/adapters/` 里加了 banking/travel、`targets/` 里也加了画像，
#: 但 `cmd_run` 当时是**写死的 if/else**，只认 workspace ⇒ **新靶标在库里、却一条命令都跑不起来，
#: 而没有任何测试会红**。`tests/test_cli_target_dispatch.py` 现在钉住三件事：
#: 分派表↔适配器类实际存在 · 每份画像要么已接线要么在 `PAPER_ONLY` 里写明理由 · 分派表里的 id 都有画像。
_ADAPTERS: Dict[str, tuple] = {
    "agentdojo-workspace": ("harness.adapters.agentdojo_workspace", "AgentDojoWorkspace"),
    "agentdojo-banking": ("harness.adapters.agentdojo_banking", "AgentDojoBanking"),
    "agentdojo-travel": ("harness.adapters.agentdojo_travel", "AgentDojoTravel"),
    # 本地 MCP 服务器靶标（T05）。适配器是**扁平模块**（协议 §2.1：`harness/observers/` 那次撞车的教训）。
    "mcp-local": ("harness.adapter_mcp_local", "McpLocalTarget"),
}


def cmd_run(a) -> int:
    if a.target not in _ADAPTERS:
        raise SystemExit("未知靶标：%s（见 `python -m harness.cli targets`）" % a.target)
    _mod, _cls = _ADAPTERS[a.target]
    import importlib as _il
    _A = getattr(_il.import_module(_mod), _cls)
    # G-44：AgentDojo 套件的金丝雀落点由**条件**选择（业务数据 = T08 构念 /
    # 系统提示词 = T06 构念）。只有声明了 `canary_surface` 的适配器接这个参数；
    # 别的适配器（mcp-local / workspace）签名里没有它 ⇒ 只传 `condition`，行为不变。
    #
    # **LLM 端点覆写**（2026-10-04 加）：`--base-url` / `--api-key-env` 只对
    # **签名里有这两个形参**的适配器生效（现状：仅 `mcp-local`）。为什么要它：
    # 网络对某个 provider 不可达时，可以用另一个可达的端点把同一套构造跑出来 ——
    # 但结果**必须**在证据里标明端点（`env.api_base` / `env.accounting.model`），
    # 因为它与走默认端点的历史批次**不可直接合并**。默认值 = 不传 ⇒ 行为逐字不变。
    _kwargs = {}
    _vars = _A.__init__.__code__.co_varnames
    if "canary_surface" in _vars:
        _t06_canary = "t06-sysprompt-canary"
        _kwargs["canary_surface"] = ("system_prompt" if a.condition == _t06_canary
                                     else "business_data")
    if getattr(a, "base_url", ""):
        if "base_url" not in _vars:
            raise SystemExit("靶标 %s 的适配器不接受 `--base-url`（签名里没有 base_url）"
                             % a.target)
        _kwargs["base_url"] = a.base_url
    if getattr(a, "api_key_env", ""):
        if "api_key_env" not in _vars:
            raise SystemExit("靶标 %s 的适配器不接受 `--api-key-env`" % a.target)
        _kwargs["api_key_env"] = a.api_key_env
    if getattr(a, "extra_body", ""):
        if "extra_body" not in _vars:
            raise SystemExit("靶标 %s 的适配器不接受 `--extra-body`" % a.target)
        try:
            _kwargs["extra_body"] = json.loads(a.extra_body)
        except Exception as exc:
            raise SystemExit("--extra-body 不是合法 JSON：%s" % exc)
    adapter = _A(model=a.model, condition=a.condition, **_kwargs)

    cards = load_cards(a.case)
    if a.limit:
        cards = cards[:a.limit]
    if not cards:
        raise SystemExit("没有卡：methods/%s/cards/" % a.case)

    print("[run_matrix] 靶标=%s 类别=%s 方法数=%d n=%d"
          % (adapter.target_id, a.case, len(cards), a.n))
    env = {"model": a.model, "payload_source": "per_method_spec"}
    # **端点如实入证**（2026-10-04 加）：换了 provider 的批次不得与默认端点批次合并。
    env["llm_endpoint"] = {
        "api_base": str(getattr(adapter, "base_url", "") or ""),
        "api_key_env": str(getattr(adapter, "api_key_env", "") or ""),
        "overridden": bool(getattr(a, "base_url", "") or getattr(a, "api_key_env", "")),
    }
    env.update(condition_env(adapter))
    # ── 适配器指纹（2026-10-03 加）──────────────────────────────────────────
    # **为什么**：靶标文本是**代码的函数**（`CATALOG` 的工具描述经 `served()` 进系统提示词，
    # 也进权威投影）。所以整批的比对基准会随 `harness/adapter_*.py` 的**任何**改动而变。
    # 当前实现实测踩过：某类批次跑到一半时适配器被改（改的是 T04 的工具描述），
    # 该批 n=3 与 n=10 两批的 `(mcp_tool_registry, description)` 投影哈希**跨批不可比**
    # （`sha256:eedcb059…` vs `sha256:df6c0e80…`），两批**不能当复现对**。
    # 记下指纹 ⇒ 事后能一眼看出"这两批是不是同一个靶标"。
    # ⚠️ 它**不是**冻结机制（不阻止改动），只是一个**可核对的锚**。
    try:
        import importlib as _il
        _mf = getattr(_il.import_module(_ADAPTERS[a.target][0]), "__file__", None)
        if _mf and os.path.exists(_mf):
            with open(_mf, "rb") as _f:
                env["adapter_module"] = os.path.basename(_mf)
                env["adapter_module_sha256"] = hashlib.sha256(_f.read()).hexdigest()
    except Exception:
        pass
    bl = baseline.card_for(a.case) if a.baseline else None
    if bl:
        env["baseline_arm"] = baseline.NAIVE_ID
        env["baseline_payload_sha256"] = hashlib.sha256(
            baseline.NAIVE_ADVERSARIAL.encode("utf-8")).hexdigest()
        print("[run_matrix] 朴素基线臂 = %s（载荷 %.24s…）"
              % (baseline.NAIVE_ID, baseline.NAIVE_ADVERSARIAL))
    res = runner.run_matrix(adapter=adapter, cards=cards,
                            judge_for=judge_for_factory(adapter),
                            payload_for=payload_for_factory(a.case, adapter),
                            payload_meta_for=payload_meta_factory(a.case),
                            n=a.n,
                            observers=observers_for(adapter),
                            baseline=bl,
                            env=env)
    print("[run_matrix] 条件 = %s（冻结哈希 %s）"
          % (env.get("condition"), (env.get("condition_sha256") or "—")[:12]))
    print("[run_matrix] batch_id = %s" % res.batch_id)
    print("[run_matrix] 六态计数（**只数方法**）= %s"
          % json.dumps(res.six_state_counts(), ensure_ascii=False))
    for c in res.cells:
        print("  %-58s %-18s %s" % (c.method_id[:58], c.six_state,
                                    ("; ".join(c.notes))[:70]))
    for c in res.baseline_cells():
        print("  [基线] %-52s v_adv=%s v_ctrl=%s Adv̂=%s"
              % (c.method_id[:52], c.v_adv, c.v_ctrl, c.adv_hat))
    print("[run_matrix] 产物：%s" % store.batch_dir(res.batch_id))
    return 0


def cmd_targets(_a) -> int:
    for p in sorted((ROOT / "targets").glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        print("  %-26s %-38s tools=%d"
              % (d["target_id"], d["display_name"][:38], len(d["tools"])))
    return 0


def main(argv=None) -> int:
    # Windows 控制台默认 GBK，`⚠` 这类字符会抛 UnicodeEncodeError **在打印阶段**——
    # 实测踩过：整批跑完、产物都落盘了，却在汇总打印时崩掉，看起来像运行失败。
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:                       # 没有 buffer 的包装流（如重定向到某些对象）
        pass
    ap = argparse.ArgumentParser(prog="python -m harness.cli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("targets").set_defaults(fn=cmd_targets)
    r = sub.add_parser("run")
    r.add_argument("--target", default="agentdojo-workspace")
    r.add_argument("--case", default="T06")
    r.add_argument("--model", default="deepseek/deepseek-chat-v3-0324")
    r.add_argument("--n", type=int, default=3)
    r.add_argument("--condition", default="native",
                   help="native（靶场原生，条件 A）/ t06-condition-b（D19 条件 B）"
                        "/ t06-sysprompt-canary（G-44：金丝雀改种系统提示词，让 T06 的"
                        " prompt_leak 测得到系统提示词外泄；只对 AgentDojo 套件有效）")
    r.add_argument("--limit", type=int, default=0,
                   help="按**文件名排序**取前 K 张卡 —— ⚠️ 它**不等于**"
                        "「前 K 张可跑的卡」（缺动作的卡会白占名额）")
    r.add_argument("--base-url", default="",
                   help="覆写 LLM 端点（默认空 = 用适配器的缺省）。"
                        "只对签名里有 `base_url` 的适配器生效；用了它 ⇒ 证据里"
                        "`env.llm_endpoint.overridden=true`，该批**不得**与默认端点批次合并。")
    r.add_argument("--extra-body", default="",
                   help="provider 特有的附加请求参数（JSON）。例：百炼的 qwen3 系列"
                        "非流式调用必须带 '{\"enable_thinking\": false}'。"
                        "只影响请求体，不进判据/载荷/靶标文本。")
    r.add_argument("--api-key-env", default="",
                   help="覆写读凭据的环境变量名（默认空 = 用适配器缺省）。"
                        "凭据本身**只走环境变量**，绝不进命令行与产物。")
    r.add_argument("--baseline", action="store_true",
                   help="在同一批里加跑**朴素基线臂**（harness/baseline.py，"
                        "载荷冻结于 docs/preregistration-t06-naive-arm.md）。"
                        "它不是方法，不进六态计数，用途是算 Δnaive")
    r.set_defaults(fn=cmd_run)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())