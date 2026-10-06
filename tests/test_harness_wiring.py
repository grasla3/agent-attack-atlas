# -*- coding: utf-8 -*-
"""C 项：接线（`` §2 的 C；七份接线清单见
`results/README.md`）。

本文件钉的是**两种静默失效**（本项目各栽过一次的同一形状）：

1. **把读回值写进 `params`** ⇒ 判据拿自己供给的"预期"当观测 ⇒ 63 张 `state_diff` 卡零成本全 `pass`；
2. **多给一个键不报错**（有 `**observations` 的判据会收下并记进 notes）⇒ 接线从
   "这个判据要什么"漂成"我们有什么"，而**判据要、靶标给不出**的通道再没人看。

运行：`python -m unittest tests.test_harness_wiring -v`
"""
from __future__ import annotations

import glob
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from harness import cli, evidence, obs_kwargs as K, protocol  # noqa: E402

CASES = ["T0%d" % i for i in range(1, 9)]


class FakeAdapter:
    """最小靶标：**如实声明自己什么都读不回来**（与 `agentdojo-workspace` 同形）。"""

    target_id = "fake-workspace"
    canary = "INTERNAL-CANARY-abc123-DO-NOT-REVEAL"

    def caps(self):
        return {"cleanup_supported": False, "receipt_supported": False,
                "entry_surfaces": ["用户输入", "user_turn"], "observables": [],
                "state_readback_supported": False, "audit_store_readback_supported": False,
                "receipt_supported_reader": False, "dual_session_supported": False}


def all_cards():
    out = []
    for p in sorted(glob.glob(str(ROOT / "methods" / "T0*" / "cards" / "*.yaml"))):
        with open(p, encoding="utf-8") as f:
            out.append(yaml.safe_load(f))
    return out


class TestTranslationLayerIsPerJudge(unittest.TestCase):
    """观测→形参的翻译**逐判据**做，且只给它签名里存在的键。"""

    def test_closed_signature_judges_get_no_extra_keys(self):
        """`prompt_leak` 与 `cross_session` 的签名封闭（无 `**observations`）⇒ 多给即 TypeError。"""
        for jid in ("prompt_leak", "cross_session"):
            self.assertFalse(K.accepts_var_kw(jid), jid)
            got = K.build(jid, protocol.Observations(response_text="r"), adapter=FakeAdapter())
            self.assertTrue(set(got) <= set(K.accepted_keys(jid)), (jid, got))

    def test_every_registered_judge_can_be_called_with_what_we_build(self):
        """**八判据 × 空观测**一律不得抛异常，且必须给四态之一（多数应是 `inconclusive`）。"""
        import importlib
        obs = protocol.Observations()
        for jid, modname in sorted(K.JUDGE_MODULES.items()):
            fn = K.judge_callable(jid)
            if fn is None:
                continue  # consistency 走类，见 TestConsistencyIsNotWiredAsAJudge
            kw = K.build(jid, obs, adapter=FakeAdapter())
            kw["request_text"], kw["payload_text"] = "", ""
            params = K.resolve_params(jid, {}, canary=FakeAdapter.canary)
            v = fn(params=params, **kw)          # 不得抛
            self.assertIn(getattr(v, "verdict", None),
                          ("pass", "fail", "inconclusive", "not_applicable"),
                          "%s 给了非法四态" % jid)

    def test_unavailable_is_reported_for_channels_no_target_provides(self):
        """判据要、靶标给不出 ⇒ 必须出现在 `unavailable()` 里（缺口必须**可见**）。"""
        obs = protocol.Observations(response_text="r")
        miss = K.unavailable("audit_integrity", obs, adapter=FakeAdapter())
        self.assertIn("entry_sha256_after", miss)
        self.assertIn("absence_basis", miss)
        miss2 = K.unavailable("ground_truth_contradiction", obs, adapter=FakeAdapter())
        self.assertIn("authoritative_value_from_source", miss2)

    def test_state_readback_absent_is_not_faked(self):
        """靶标声明读不回状态 ⇒ 翻译层**不摆** `state_before/after`（不填假值）。"""
        obs = protocol.Observations(response_text="r",
                                    state_before={"a": 1}, state_after={"a": 2})
        got = K.build("state_diff", obs, adapter=FakeAdapter())
        self.assertNotIn("state_before", got)
        self.assertNotIn("state_after", got)
        self.assertNotIn("before_state_hash", got)


class TestParamsChannelIsDeclarationOnly(unittest.TestCase):
    """**声明通道与观测通道严格分开**（`judge-state_diff-notes.md:57-68`）。"""

    def test_self_supplied_hashes_still_inconclusive(self):
        """把一对"看起来很真"的自供哈希喂进去 ⇒ 必须仍 `inconclusive`。

        这是本项目最贵的一条防线：`params` 里的哈希是**标签**，若判据拿它当观测，
        63 张卡会零成本全 `pass`（那不是判据，是自我实现）。
        """
        from judges import state_diff as J
        params = {"entity_id": "svc_thin",
                  "before_state_hash": "sha256:baseline-svc_thin",
                  "after_state_hash": "sha256:attacked-svc_thin"}
        v = J.judge(params=params)                     # 没有**任何**读回
        self.assertEqual(v.verdict, "inconclusive")
        self.assertIn("no_state_readback", v.reason)

    def test_resolve_params_never_injects_readback_values(self):
        """`resolve_params` 只解析金丝雀模板，**不碰**任何读回类键。"""
        card_params = {"entity_id": "e", "before_state_hash": "<read-at-runtime>",
                       "after_state_hash": "<read-at-runtime>"}
        got = K.resolve_params("state_diff", card_params, canary="CANARY-x")
        self.assertEqual(got, card_params)

    def test_canary_goes_to_the_right_channel_per_judge(self):
        """三态：`prompt_leak` 走 `params`；`sensitive_data` / `cross_session` 走**观测**。"""
        c = "INTERNAL-CANARY-abc123"
        p1 = K.resolve_params("prompt_leak", {"canary_id": "x", "expected_verbatim": "T06CANARY-<random32>"}, canary=c)
        self.assertEqual(p1["expected_verbatim"], c)
        for jid in ("sensitive_data", "cross_session"):
            p2 = K.resolve_params(jid, {"canary_id": "x"}, canary=c)
            self.assertNotIn("expected_verbatim", p2, jid)   # 封闭 schema，塞了就抛 ParamsError
            self.assertNotIn("canary_verbatim", p2, jid)
            got = K.build(jid, protocol.Observations(), adapter=FakeAdapter())
            # 观测通道里的真值来自**靶标**（`adapter.canary`），不是上面那个局部变量 c ——
            # 写错这一处正是"数字对、构念错"的最小样本，故把来源写进断言里。
            self.assertEqual(got.get("canary_verbatim"), FakeAdapter.canary, jid)

    def test_resolve_params_adds_no_key_outside_the_schema(self):
        """对**全部 186 张真卡**：解析后的键集必须仍落在该判据 `params_schema` 允许的键内。"""
        import json
        reg = json.loads((ROOT / "judges" / "registry.json").read_text(encoding="utf-8"))
        judges = reg["judges"] if isinstance(reg, dict) and "judges" in reg else reg
        if not isinstance(judges, dict):
            judges = {j.get("judge_id"): j for j in judges}
        bad = []
        for c in all_cards():
            j = c.get("judge") or {}
            vid = j.get("verifier")
            entry = judges.get(vid) or {}
            allowed = set((entry.get("params_schema") or {}).get("properties") or {})
            got = K.resolve_params(vid, j.get("params"), canary="CANARY-zzz")
            extra = set(got) - allowed
            if extra:
                bad.append((c["method_id"], vid, sorted(extra)))
        self.assertEqual(bad, [], "解析后多出 schema 外的键 ⇒ 判据会抛 ParamsError：%s" % bad[:5])


class TestDispatchCoversEveryCard(unittest.TestCase):
    """`judge_for_factory` 必须能按 `card.judge.verifier` 分派**库里每一个**判据。"""

    def test_factory_builds_a_judge_for_every_card_verifier(self):
        factory = cli.judge_for_factory(FakeAdapter())
        seen = set()
        for c in all_cards():
            vid = (c.get("judge") or {}).get("verifier")
            bound = factory(c)
            self.assertEqual(bound.judge_id, vid)
            seen.add(vid)
        # 库里出现的判据都要分派得动（2026-10-05：T01 的 14 张「答案替换」卡从
        # `ground_truth_contradiction` 换成 `retrieval_poisoning` ⇒ 这张名单多一个。
        # 名单是**状态**不是上限，故按新事实重述；断言强度未降——仍要求
        # 「卡库用到的每一个 verifier 都恰好在这张名单里」。
        self.assertEqual(seen, {"state_diff", "scenario_contract", "ground_truth_contradiction",
                                "prompt_leak", "sensitive_data", "audit_integrity",
                                "cross_session", "baseline_comparison", "tool_selection",
                                "retrieval_poisoning"})

    def test_unimplemented_verifier_is_loud(self):
        """未注册的 verifier **必须报错**，不得静默回落成某个默认判据。"""
        factory = cli.judge_for_factory(FakeAdapter())
        with self.assertRaises(SystemExit):
            factory({"method_id": "X", "judge": {"verifier": "nope_not_a_judge"}})

    def test_bound_params_for_writes_the_resolved_canary(self):
        """证据里的 `judge_params_resolved` 必须是**真值**，不是卡上模板（G-8）。"""
        factory = cli.judge_for_factory(FakeAdapter())
        card = next(c for c in all_cards() if (c.get("judge") or {}).get("verifier") == "prompt_leak")
        got = factory(card).params_for(card)
        self.assertEqual(got["expected_verbatim"], FakeAdapter.canary)
        self.assertNotIn("<random32>", got["expected_verbatim"])


class TestEvidenceCarriesWhatJudgesNeed(unittest.TestCase):
    """C⑦：判据的输入不进证据束 ⇒ trial 文件复算不出它自己记的 `verdict`。"""

    def test_evidence_has_the_observation_fields(self):
        ev = evidence.TrialEvidence(batch_id="b", method_id="m", target_id="t")
        for name in ("receipts", "state_before", "state_after", "tool_calls",
                     "judge_channels_missing", "judge_params_resolved", "judge_params_source"):
            self.assertTrue(hasattr(ev, name), name)

    def test_evidence_serialises_with_defaults(self):
        ev = evidence.TrialEvidence(batch_id="b", method_id="m", target_id="t")
        import json
        d = json.loads(ev.to_json())          # 不得抛
        self.assertIn("state_after", d)
        self.assertIn("judge_channels_missing", d)


class TestConsistencyIsNotWiredAsAJudge(unittest.TestCase):
    """`prompt_leak_consistency` 是**第二判据通道**，不是 `judge.verifier` 的可选值。"""

    def test_no_card_declares_it_as_verifier(self):
        used = {(c.get("judge") or {}).get("verifier") for c in all_cards()}
        self.assertNotIn("prompt_leak_consistency", used)

    def test_it_has_no_module_level_judge(self):
        self.assertIsNone(K.judge_callable("prompt_leak_consistency"))
        self.assertEqual(K.accepted_keys("prompt_leak_consistency"), ())


if __name__ == "__main__":
    unittest.main()
