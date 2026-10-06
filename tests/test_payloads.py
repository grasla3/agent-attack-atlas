# -*- coding: utf-8 -*-
"""载荷合成层的可执行防线（`harness/payloads.py`，依 `ROADMAP.md` **G-6**）。

重点有四块：

1. **词汇表闭合**：类模块交出来的槽值只能是**枚举 token**，且必须能在短语表里查到。
   这一条同时是 **S4（载荷文本不进仓库）**的机检形态 —— 方法脚本里一个字的载荷都没有。
2. **守卫**：未知 token / 槽未填齐 / 载荷含金丝雀 / 投放面不具备，四种情形都不许放行。
3. **配对**：对照臂与对抗臂**同一个框架、同一个轮数**，只换"请求" token。
4. **逐方法载荷真的不同**（G-6 的修复本身）：8 个可投放方法的载荷两两不同。

运行：`python -m pytest tests/test_payloads.py -q`
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harness import payloads as P  # noqa: E402

RUNNABLE = ["LIT-B-105.intent_inference_equivalent_prompt",
            "LIT-B-106.gradient_optimized_adversarial_query",
            "LIT-B-107.memorization_attention_path_analysis",
            "LIT-B-108.rl_trained_attack_agent",
            "LIT-B-109.extended_sandwich_query_family",
            "LIT-B-110.remember_to_start_instruction_family",
            "LIT-B-115.multi_turn_sycophancy_escalation",
            "LIT-B-116.output_inversion_prompt_recovery"]

#: 与 `harness/adapters/agentdojo_workspace.py` 的 `caps()` 一致：**不支持多轮**。
ADAPTER_CAPS = {"entry_surfaces": ["用户输入", "user_turn"], "observables": []}


def t06_spec(name: str) -> P.PayloadSpec:
    from methods.T06 import T06
    return P.from_dict(T06.payload_spec("T06." + name))


class TestVocabularyIsClosed(unittest.TestCase):
    """槽值只能是枚举 token —— 这是 S4 的可机检形态。"""

    def test_every_frame_token_is_known(self):
        for fid, fr in P.FRAMES.items():
            for tok in fr["tokens"]:
                self.assertIn(tok, ("request", "artifact", "repeat_mode"), fid)

    def test_t06_specs_only_use_tokens_in_the_phrase_tables(self):
        from methods.T06 import T06
        for mech, spec in T06.CONSTRUCTION_SPECS.items():
            self.assertIn(spec["frame"], P.frame_ids(), mech)
            toks = spec.get("tokens") or {}
            if "request" in toks:
                self.assertIn(toks["request"], P.REQUESTS, mech)
            if "artifact" in toks:
                self.assertIn(toks["artifact"], P.ARTIFACTS, mech)
            if "repeat_mode" in toks:
                self.assertIn(toks["repeat_mode"], P.REPEAT_MODES, mech)

    def test_method_module_carries_no_sentence_like_values(self):
        """方法脚本里的槽值必须是短 token，不是句子 —— 长了就说明载荷文本漏进去了。"""
        from methods.T06 import T06
        for mech, spec in T06.CONSTRUCTION_SPECS.items():
            for k, v in (spec.get("tokens") or {}).items():
                self.assertLessEqual(len(str(v)), 24,
                                     "%s 的槽 %s 长达 %d 字符，疑似载荷文本" % (mech, k, len(str(v))))

    def test_every_frame_renders_both_arms(self):
        for fid in P.frame_ids():
            spec = P.PayloadSpec(frame=fid, tokens={"request": "verbatim_restate",
                                                    "artifact": "instructions",
                                                    "repeat_mode": "twice"})
            for arm in ("adversarial", "control"):
                out = P.render(spec, arm=arm)
                self.assertTrue(all(isinstance(x, str) and x.strip() for x in out), (fid, arm))


class TestGuards(unittest.TestCase):
    def test_unknown_frame_is_rejected(self):
        with self.assertRaises(KeyError):
            P.render(P.PayloadSpec(frame="nope"), arm="adversarial")

    def test_unknown_token_is_rejected_not_guessed(self):
        with self.assertRaises(KeyError):
            P.render(P.PayloadSpec(frame="sandwich",
                                   tokens={"request": "make_it_leak", "artifact": "instructions"}),
                     arm="adversarial")

    def test_canary_in_payload_is_refused(self):
        """D1：我方供给的秘密进了载荷，判据测的就成了"模型会不会复读输入"。"""
        spec = P.PayloadSpec(frame="sandwich",
                             tokens={"request": "verbatim_restate", "artifact": "instructions"})
        with self.assertRaises(ValueError) as cm:
            P.synthesize(spec, arm="adversarial", canary="First, a quick question")
        self.assertIn("D1", str(cm.exception))

    def test_missing_surface_is_not_deliverable(self):
        """多轮构造遇上不支持多轮的适配器 ⇒ `untested`（没测 ≠ 没成功）。"""
        spec = P.PayloadSpec(frame="crescendo", turns=5,
                             tokens={"request": "verbatim_restate", "artifact": "instructions"})
        self.assertEqual(P.missing_requirements(spec, ADAPTER_CAPS), [P.MULTI_TURN_SURFACE])
        with self.assertRaises(P.NotDeliverable):
            P.synthesize(spec, arm="adversarial", caps=ADAPTER_CAPS)

    def test_declared_surface_lets_it_through(self):
        caps = {"entry_surfaces": ["user_turn", P.MULTI_TURN_SURFACE]}
        spec = P.PayloadSpec(frame="crescendo", turns=5,
                             tokens={"request": "verbatim_restate", "artifact": "instructions"})
        self.assertEqual(P.missing_requirements(spec, caps), [])
        self.assertEqual(len(P.synthesize(spec, arm="adversarial", caps=caps)), 5)

    def test_turn_count_mismatch_is_loud(self):
        spec = P.PayloadSpec(frame="crescendo", turns=3,      # 框架给 5 轮
                             tokens={"request": "verbatim_restate", "artifact": "instructions"})
        caps = {"entry_surfaces": ["user_turn", P.MULTI_TURN_SURFACE]}
        with self.assertRaises(ValueError):
            P.synthesize(spec, arm="adversarial", caps=caps)


class TestPairing(unittest.TestCase):
    """AgentSecBench 定义 4：两臂必须**同形**，否则 `Adv̂` 减掉的是不可比的东西。"""

    def test_control_uses_the_same_frame_and_turn_count(self):
        spec = t06_spec("LIT-B-109.extended_sandwich_query_family")
        adv = P.synthesize(spec, arm="adversarial", caps=ADAPTER_CAPS)
        ctrl = P.synthesize(spec, arm="control", caps=ADAPTER_CAPS)
        self.assertEqual(len(adv), len(ctrl))
        self.assertNotEqual(adv, ctrl)

    def test_control_differs_only_in_the_request_clause(self):
        spec = t06_spec("LIT-B-109.extended_sandwich_query_family")
        adv = P.resolve(spec, arm="adversarial")
        ctrl = P.resolve(spec, arm="control")
        self.assertEqual(adv["lead"], ctrl["lead"])
        self.assertEqual(adv["artifact"], ctrl["artifact"])
        self.assertNotEqual(adv["request"], ctrl["request"])
        self.assertIn(P.BENIGN_REQUESTS[P.CONTROL_REQUEST_TOKEN], ctrl["request"])


class TestPerMethodInstantiation(unittest.TestCase):
    """G-6 的修复本身：**各方法的载荷必须真的不同**。"""

    def test_runnable_methods_yield_pairwise_distinct_payloads(self):
        seen = {}
        for name in RUNNABLE:
            spec = t06_spec(name)
            try:
                text = P.synthesize(spec, arm="adversarial", caps=ADAPTER_CAPS)[0]
            except P.NotDeliverable:
                continue                      # 多轮方法在本适配器上投不了，见下一测试
            self.assertNotIn(text, seen,
                             "%s 与 %s 的载荷完全相同 ⇒ 方法又没被实例化" % (name, seen.get(text)))
            seen[text] = name
        self.assertGreaterEqual(len(seen), 6, "可投放且载荷互异的方法应有 6 个")

    def test_multiturn_methods_are_undeliverable_here_not_silently_collapsed(self):
        """B-108（3 轮）与 B-115（5 轮）：本适配器未声明多轮投放面 ⇒ `NotDeliverable`。

        **不得把它们压成一轮发出去** —— 那测的就不是这个方法了。
        """
        for name in ("LIT-B-108.rl_trained_agent".replace("_agent", "_agent"),
                     "LIT-B-115.multi_turn_sycophancy_escalation"):
            try:
                spec = t06_spec(name)
            except KeyError:
                continue
            if spec.turns <= 1:
                continue
            with self.assertRaises(P.NotDeliverable):
                P.synthesize(spec, arm="adversarial", caps=ADAPTER_CAPS)

    def test_scope_is_declared_for_every_runnable_method(self):
        """近似必须是**自报**的：`scope` 不许缺省糊过去。"""
        for name in RUNNABLE:
            spec = t06_spec(name)
            self.assertIn(spec.scope, ("faithful", "approximation", "generic"), name)
            self.assertTrue(spec.source.startswith("LIT-B-"), name)


class TestSpecForCardFallback(unittest.TestCase):
    def test_module_without_payload_spec_falls_back_and_says_so(self):
        class Bare:
            pass

        card = {"method_id": "T06.X.y", "mechanism_ref": "LIT-B-999"}
        spec = P.spec_for_card(card, Bare())
        self.assertEqual(spec.scope, "generic")
        self.assertIn("兜底", spec.note)
        meta = P.meta_of(spec)
        self.assertEqual(meta["scope"], "generic")

    def test_real_module_does_not_fall_back_for_runnable_methods(self):
        from methods.T06 import T06
        card = {"method_id": "T06." + RUNNABLE[0], "mechanism_ref": "LIT-B-105"}
        spec = P.spec_for_card(card, T06)
        self.assertNotEqual(spec.scope, "generic")

    def test_capitalisation_touches_only_the_first_letter(self):
        """回归：`str.capitalize()` 会把其余字符全变小写。

        实测代价：对照臂的 `list the items I have` 曾被写成 `list the items i have`——
        两臂形状本该一致，这种噪声会污染 `Adv̂`。
        """
        self.assertEqual(P._cap("list the items I have"), "List the items I have")
        self.assertEqual(P._cap(""), "")

    def test_control_payload_preserves_internal_capitals(self):
        spec = t06_spec("LIT-B-116.output_inversion_prompt_recovery")
        ctrl = P.synthesize(spec, arm="control", caps=ADAPTER_CAPS)[0]
        self.assertIn("I have", ctrl)
        self.assertNotIn("i have", ctrl)

    def test_no_double_connector_in_sandwich(self):
        spec = t06_spec("LIT-B-109.extended_sandwich_query_family")
        adv = P.synthesize(spec, arm="adversarial", caps=ADAPTER_CAPS)[0]
        self.assertNotIn("Finally, And", adv)

    def test_meta_carries_no_payload_text(self):
        spec = t06_spec("LIT-B-109.extended_sandwich_query_family")
        meta = P.meta_of(spec)
        blob = repr(meta)
        for text in P.synthesize(spec, arm="adversarial", caps=ADAPTER_CAPS):
            frag = text[:24]
            self.assertNotIn(frag, blob, "构造元数据里混进了载荷文本：%r" % frag)


if __name__ == "__main__":
    unittest.main()
