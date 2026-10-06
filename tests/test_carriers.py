# -*- coding: utf-8 -*-
"""载体库（`harness/payloads.py` 的 `CARRIERS`）的可执行防线。

守四件事：

1. **T06 回归**：`text_only` + 对话框架这条路**逐字不变**——已存档的两个批次
   （`batch-3b57e93c6f15` / `batch-39958d9a7688`）的可比性全押在这一条上。
2. **对话框架不越界**：artifact 类载体（文档/配置/工具返回/记录/任务）里
   **不得出现** `lead`/`tail`。拆之前 `kb_doc` 会产出
   *"Reference note\\n\\nFirst, a quick question: …"*——一句用户指令贴了页眉页脚。
3. **载体隐含投放面**：`kb_doc` 遇上不支持检索面的靶标必须 `NotDeliverable`，
   不得悄悄以用户输入的形态投出去（否则测的不是那个方法）。
4. **值域取自语料**：六个载体名必须与 186 张卡的 `carrier` 字段值域**逐字一致**。
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(ROOT))

from harness import payloads as P  # noqa: E402

ALL_SURFACES = {"entry_surfaces": ["用户输入", "检索文档", "工具返回", "系统提示词",
                                   "记忆写入", "智能体间消息", "user_turn", "user_turn_multi"]}
USER_ONLY = {"entry_surfaces": ["用户输入", "user_turn"]}
SPEC = {"frame": "sandwich",
        "tokens": {"request": "verbatim_restate", "artifact": "instructions"}}


def _render(carrier, arm="adversarial", caps=ALL_SURFACES):
    d = dict(SPEC)
    d["carrier"] = carrier
    return P.synthesize(P.from_dict(d), arm=arm, caps=caps)


class TestVocabularyComesFromCorpus(unittest.TestCase):
    """值域必须与卡上 `carrier` 字段一致——不得自己发明第七个。"""

    def test_six_carriers_exactly(self):
        self.assertEqual(sorted(P.carrier_ids()),
                         ["chat_log", "config_fragment", "descriptor_wording", "kb_doc",
                          "task_context", "text_only", "tool_return"])

    def test_corpus_uses_only_these_values(self):
        import yaml
        seen = set()
        for p in sorted((ROOT / "methods").glob("T0*/cards/*.yaml")):
            seen.add(yaml.safe_load(p.read_text(encoding="utf-8")).get("carrier"))
        self.assertTrue(seen <= set(P.carrier_ids()),
                        "卡上出现了载体库没有的取值：%s" % (seen - set(P.carrier_ids())))
        self.assertEqual(seen - {None}, set(P.carrier_ids()),
                         "载体库里有语料从未出现的取值（不许凑数）")

    def test_unknown_carrier_is_rejected(self):
        with self.assertRaises(KeyError):
            P.from_dict({"frame": "sandwich", "carrier": "email"})
        with self.assertRaises(ValueError):
            P.apply_carrier("email", ["x"])


class TestTextOnlyIsBitIdentical(unittest.TestCase):
    """回归：T06 现有 8 条规格走的就是这条路。"""

    def test_default_carrier_is_text_only(self):
        s = P.from_dict(SPEC)
        self.assertEqual(s.carrier, "text_only")
        self.assertTrue(P.is_conversational("text_only"))

    def test_text_only_rendering_is_the_raw_frame_output(self):
        spec = P.from_dict(SPEC)
        raw = P.FRAMES["sandwich"]["render"](P.resolve(spec, arm="adversarial"))
        self.assertEqual(_render("text_only"), raw)

    def test_explicit_text_only_equals_implicit(self):
        a = P.from_dict(dict(SPEC, carrier="text_only"))
        b = P.from_dict(SPEC)
        self.assertEqual(P.render(a, arm="adversarial"), P.render(b, arm="adversarial"))


class TestConversationalBookendsDoNotLeak(unittest.TestCase):
    """artifact 类载体**不是对话**，不得带 `lead`/`tail`。"""

    def test_artifact_carriers_have_no_lead_or_tail(self):
        for c in P.carrier_ids():
            if c == "text_only":
                continue
            text = _render(c)[0]
            self.assertNotIn(P.BENIGN_LEAD, text, "%s 里出现了对话开场白" % c)
            self.assertNotIn(P.BENIGN_TAIL, text, "%s 里出现了对话收尾" % c)

    def test_text_only_does_have_them(self):
        text = _render("text_only")[0]
        self.assertIn(P.BENIGN_LEAD, text)
        self.assertIn(P.BENIGN_TAIL, text)

    def test_every_frame_has_a_core_renderer(self):
        """新增 frame 时若忘写 `render_core`，artifact 载体就会静默回落到 `render`。"""
        for fid, fr in P.FRAMES.items():
            self.assertIn("render_core", fr, "frame %s 缺 render_core" % fid)


class TestCarrierShape(unittest.TestCase):
    """每个载体的产出必须**认得出是那种东西**。"""

    def test_kb_doc_looks_like_a_document(self):
        t = _render("kb_doc")[0]
        self.assertTrue(t.startswith("Reference note"))
        self.assertIn("— end of note —", t)

    def test_tool_return_is_valid_json(self):
        t = _render("tool_return")[0]
        obj = json.loads(t)
        self.assertEqual(obj["status"], "ok")
        self.assertIsInstance(obj["content"], str)

    def test_tool_return_survives_quotes_in_body(self):
        """正文里有引号时不得产生非法 JSON。"""
        d = dict(SPEC, carrier="tool_return")
        d["tokens"] = {"request": "verbatim_restate", "artifact": "config"}
        s = P.from_dict(d)
        out = P.synthesize(s, arm="adversarial", caps=ALL_SURFACES)[0]
        json.loads(out)                       # 不抛即通过

    def test_chat_log_marks_the_speaker(self):
        self.assertIn("User:", _render("chat_log")[0])

    def test_config_fragment_uses_config_syntax(self):
        t = _render("config_fragment")[0]
        self.assertTrue(t.startswith("#"))
        self.assertIn("# end of configuration", t)

    def test_task_context_prefixes(self):
        self.assertTrue(_render("task_context")[0].startswith("Task context:"))


class TestCarrierImpliesEntrySurface(unittest.TestCase):
    """载体隐含的投放面必须进闸门——否则会以错误的形态投出去。"""

    def test_effective_requires_unions_both_sources(self):
        s = P.from_dict(dict(SPEC, carrier="kb_doc", requires=("user_turn",)))
        self.assertEqual(set(s.effective_requires()), {"user_turn", "检索文档"})

    def test_kb_doc_on_a_target_without_retrieval_is_not_deliverable(self):
        with self.assertRaises(P.NotDeliverable):
            _render("kb_doc", caps=USER_ONLY)

    def test_text_only_still_delivers_on_a_user_turn_target(self):
        self.assertTrue(_render("text_only", caps=USER_ONLY))

    def test_multi_turn_surface_still_implied(self):
        s = P.from_dict(dict(SPEC, turns=3))
        self.assertIn(P.MULTI_TURN_SURFACE, s.effective_requires())


class TestMetaRecordsCarrier(unittest.TestCase):
    def test_meta_carries_carrier_and_its_requires(self):
        m = P.meta_of(P.from_dict(dict(SPEC, carrier="tool_return")))
        self.assertEqual(m["carrier"], "tool_return")
        self.assertEqual(m["carrier_requires"], ["工具返回"])


if __name__ == "__main__":
    unittest.main()
