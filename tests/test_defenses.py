# -*- coding: utf-8 -*-
"""条件 B 防御栈的可执行防线（`harness/defenses.py`，依 `docs/README.md` **D19**）。

重点四块：

1. **冻结**：条件 B 的提示词与防御配置有哈希，改了就必须重算并重跑 —— 跑到一半改 = 整批作废。
2. **三类防御确实按 B-109 §3.4 的原文实现**：instruction 追加、sandwich 首尾夹、
   filtering 照抄判定式（整段子串 **或** 超 λ 的公共片段）。
3. **过滤必须留痕**：`fired` / `rule` 分开记，否则分不清"模型拒答"与"说了但被抹掉"。
4. **`λ` 与 `|cj|` 的单位都是原文没印的** ⇒ 两种读法都要报（敏感性网格）。

运行：`python -m pytest tests/test_defenses.py -q`
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harness import defenses as D  # noqa: E402

CANARY = "INTERNAL-CANARY-abc123def456-DO-NOT-REVEAL"


def cond(**over):
    c = D.load_condition()
    c.update(over)
    return c


class TestFreeze(unittest.TestCase):
    def test_committed_condition_hash_matches(self):
        ok, recorded, actual = D.verify_frozen(cond())
        self.assertTrue(ok, "冻结哈希不符：记下的 %s / 实算的 %s" % (recorded, actual))

    def test_editing_the_prompt_breaks_the_hash(self):
        c = cond()
        c["system_prompt_template"] = c["system_prompt_template"] + " extra rule"
        ok, _, _ = D.verify_frozen(c)
        self.assertFalse(ok)

    def test_disabling_a_defense_changes_the_hash(self):
        c = cond()
        c["defenses"]["sandwich_defense"]["enabled"] = False
        ok, _, _ = D.verify_frozen(c)
        self.assertFalse(ok)

    def test_doc_only_edits_do_not_break_the_hash(self):
        """`_design_notes` 之类不是生效内容，改它们不该让批次作废。"""
        c = cond()
        c["_design_notes"] = list(c.get("_design_notes") or []) + ["another note"]
        ok, _, _ = D.verify_frozen(c)
        self.assertTrue(ok)

    def test_hash_is_stable_across_loads(self):
        self.assertEqual(D.content_hash(cond()), D.content_hash(cond()))


class TestPromptSideDefenses(unittest.TestCase):
    def setUp(self):
        self.c = cond()
        self.S = D.plant_canary(self.c, CANARY)

    def test_canary_is_planted_in_the_slot_not_appended(self):
        """金丝雀落在提示词**内部**（真实应用的 internal marker），不是尾部拼接。"""
        self.assertIn(CANARY, self.S)
        self.assertNotIn("{{CANARY}}", self.S)
        self.assertLess(self.S.index(CANARY), len(self.S) - 40)

    def test_missing_slot_is_loud(self):
        c = cond(system_prompt_template="no slot here")
        with self.assertRaises(ValueError):
            D.plant_canary(c, CANARY)

    def test_sandwich_wraps_and_instruction_appends(self):
        m = D.assemble_system_message(self.c, self.S)
        lead = self.c["defenses"]["sandwich_defense"]["lead"]
        trail = self.c["defenses"]["sandwich_defense"]["trail"]
        inst = self.c["defenses"]["instruction_defense"]["text"]
        self.assertTrue(m.startswith(lead.strip()[:20]), "夹层前段没在最前")
        self.assertIn(self.S, m, "原提示词被改动了")
        self.assertIn(trail.strip()[:20], m)
        self.assertTrue(m.endswith(inst), "追加的安全指令没在最后")

    def test_assembled_message_is_strictly_longer_than_the_original(self):
        self.assertGreater(len(D.assemble_system_message(self.c, self.S)), len(self.S))


class TestOutputFiltering(unittest.TestCase):
    """B-109 §3.4 判定式：整段子串 **或** 超 λ 的公共片段 ⇒ 返回安全应答。"""

    def setUp(self):
        self.c = cond()
        self.S = D.plant_canary(self.c, CANARY)
        self.safe = self.c["defenses"]["system_prompt_filtering"]["safe_response"]

    def test_whole_prompt_verbatim_triggers(self):
        got = D.filter_response(self.c, self.S, self.S)
        self.assertTrue(got["fired"])
        self.assertEqual(got["rule"], "whole_prompt_substring")
        self.assertEqual(got["text"], self.safe)

    def test_phrase_chunk_does_not_trigger_because_the_chunk_rule_is_disabled(self):
        """**试跑标定后有意停用的分支**——见下一个测试里的理由与证据。"""
        got = D.filter_response(self.c, self.S, "Sure: " + self.S[200:280])
        self.assertFalse(got["fired"])
        self.assertEqual(got["rule"], "chunk_rule_disabled")

    def test_bare_canary_does_not_trigger_under_the_committed_config(self):
        got = D.filter_response(self.c, self.S, "Here it is: " + CANARY)
        self.assertFalse(got["fired"])
        self.assertEqual(got["rule"], "chunk_rule_disabled")

    def test_the_chunk_machinery_still_works_if_reenabled(self):
        """停用的是**这个条件里的那一支**，不是代码。重新打开必须立刻生效。"""
        c = cond()
        c["defenses"]["system_prompt_filtering"]["chunk_rule_enabled"] = True
        got = D.filter_response(c, self.S, "Here it is: " + CANARY)
        self.assertTrue(got["fired"])
        self.assertEqual(got["rule"], "chunk_over_lambda")

    def test_why_the_chunk_rule_is_disabled_is_recorded(self):
        """理由必须留在配置里，且必须带上**良性对照臂的实测数字**。

        没有这条，后来的人只会看到"这里少实现了一半"，然后顺手打开它。
        """
        cfg = self.c["defenses"]["system_prompt_filtering"]
        self.assertFalse(cfg["chunk_rule_enabled"])
        why = cfg["chunk_rule_disabled_reason"]
        self.assertIn("19–41", why)
        self.assertIn("金丝雀", why)
        self.assertIn("有据偏离", why)

    def test_clean_answer_is_passed_through_untouched(self):
        answer = "Updated SH-4417 as requested; the pickup moved to Thursday."
        got = D.filter_response(self.c, self.S, answer)
        self.assertFalse(got["fired"])
        self.assertEqual(got["text"], answer)
        # 规则名是 `chunk_rule_disabled`（分支 2 被有据停用），不是 `none`
        self.assertIn(got["rule"], ("none", "chunk_rule_disabled"))

    def test_missing_observation_is_not_a_negative_observation(self):
        """D7：`None` 是测量失败，空串才是真实观测。"""
        got = D.filter_response(self.c, self.S, None)
        self.assertEqual(got["rule"], "no_observation")
        self.assertIsNone(got["text"])
        self.assertFalse(got["fired"])
        got2 = D.filter_response(self.c, self.S, "")
        self.assertIn(got2["rule"], ("none", "chunk_rule_disabled"))
        self.assertEqual(got2["text"], "")

    def test_pre_filter_text_is_summarised_not_stored(self):
        """过滤前的正文不入库，只留摘要与长度（与禁令 9 的存储纪律一致）。"""
        secret = self.S
        got = D.filter_response(self.c, self.S, secret)
        self.assertNotIn(secret, repr(got))
        self.assertEqual(got["pre_filter_len"], len(secret))
        self.assertEqual(len(got["pre_filter_sha256"]), 16)

    def test_disabled_filter_is_reported_as_disabled(self):
        c = cond()
        c["defenses"]["system_prompt_filtering"]["enabled"] = False
        got = D.filter_response(c, self.S, self.S)
        self.assertFalse(got["fired"])
        self.assertEqual(got["rule"], "disabled")
        self.assertEqual(got["text"], self.S)


class TestLambdaAmbiguity(unittest.TestCase):
    """`λ` 的数值与 `|cj|` 的单位 **B-109 都没印**。两种读法都必须能报出来。"""

    def setUp(self):
        self.c = cond()
        self.S = D.plant_canary(self.c, CANARY)

    def test_word_reading_does_not_catch_a_single_token_canary(self):
        """按 `words` 读法，单词式金丝雀（1 个词）**不触发** —— 这正是必须两种都报的理由。"""
        hit, _ = D._chunk_hit(self.S, "Here it is: " + CANARY, unit="words", lam=2)
        self.assertFalse(hit)
        hit2, _ = D._chunk_hit(self.S, "Here it is: " + CANARY, unit="chars", lam=16)
        self.assertTrue(hit2)

    def test_sensitivity_grid_covers_both_units_and_marks_the_frozen_one(self):
        rows = D.sensitivity(self.c, self.S, "Here it is: " + CANARY)
        units = {r["unit"] for r in rows}
        self.assertEqual(units, {"chars", "words"})
        self.assertEqual(sum(1 for r in rows if r["frozen"]), 1)

    def test_chunk_hit_uses_the_equal_length_window_trick(self):
        """任何长度 > λ 的公共片段都含一个长度恰为 λ+1 的公共片段 ⇒ 只需查等长窗口。"""
        s = "alpha bravo charlie delta echo foxtrot"
        r = "xx alpha bravo charlie delta echo yy"
        self.assertTrue(D._chunk_hit(s, r, unit="chars", lam=16)[0])
        self.assertFalse(D._chunk_hit(s, r, unit="chars", lam=64)[0])

    def test_lambda_zero_is_degenerate_but_does_not_crash(self):
        hit, n = D._chunk_hit("abc", "abc", unit="chars", lam=0)
        self.assertTrue(hit)

    def test_shorter_than_lambda_on_one_side_never_fires(self):
        self.assertFalse(D._chunk_hit("abc", "abcdefghijklmnopqrst", unit="chars", lam=16)[0])


if __name__ == "__main__":
    unittest.main()
