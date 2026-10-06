# -*- coding: utf-8 -*-
"""目标能力对齐表的可执行防线（`score/targets.py` + `targets/capability-aliases.yaml`）。

它存在的理由：`required_actions` 有 **152 个自造动作名**，与 AgentDojo 的工具名**只有 3 个**
逐字相同 ⇒ 纯字符串口径下"适用性"取决于巧合（`targets/README.md` §3.1）。

所以这张表**最危险的地方不是漏，是滥**：只要往里多写几行，覆盖率就会好看，
而那等于把"目标其实没有这个面"洗成"适用"。故本测试集的**主线是负向不变量**：

1. **排除项必须真的被排除** —— `knowledge_retrieve` / `authz_decide` / `memory_write`
   等目标不具备的动作，**不得**出现在展开结果里。
2. **每条别名都必须有据** —— `source` 与 `reason` 非空，且 `id` 唯一。
3. **展开结果可分解** —— 报告要能看出覆盖率里有多少来自别名（口径差异必须可见）。
4. **别名不得悄悄扩大 `not_applicable`** —— 前置条件那一关不受别名影响。

运行：`python -m pytest tests/test_targets.py -q`
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from score import prior as P        # noqa: E402
from score import targets as T      # noqa: E402

TARGET = "agentdojo-workspace"


def profile():
    return T.load_profile(TARGET)


def cards():
    return [yaml.safe_load(p.read_text(encoding="utf-8"))
            for p in sorted((ROOT / "methods").glob("T0*/cards/*.yaml"))]


class TestAliasFileIntegrity(unittest.TestCase):
    def setUp(self):
        self.a = T.load_aliases()
        self.tgt = (self.a.get("targets") or {}).get(TARGET) or {}

    def test_version_present(self):
        # v2（2026-10-03，G-42）：补齐 `agentdojo-banking` / `agentdojo-travel` 两段
        # 通用能力别名（它们是**已接线的可跑靶标**，此前在表里连一段都没有）。
        self.assertEqual(self.a.get("version"), "capability-aliases-v2")

    def test_pipeline_level_agentdojo_capabilities_are_declared_for_every_wired_suite(self):
        """**G-42 的回归断言**：三份 AgentDojo 画像共用同一基类 ⇒ 通用能力必须都声明。

        为什么这条要写成测试：这三段曾出现"workspace 有、banking/travel 没有"的**静默不一致**
        —— 而后者是**已接线的可跑靶标**（`harness/cli.py` 的 `_ADAPTERS`）。
        缺一段不会报错，只会让适用性悄悄变少 ⇒ 必须由断言钉住。

        ⚠️ **只断言"通用能力"**（管线级：用户轮 / 助手回复 / 工具调用…）。
        各 suite **专有**的能力（workspace 的 `state_changing_tools` 等）不在本条范围内。
        """
        common = {"user_turn", "assistant_response", "instruction_following",
                  "tool_invocation", "tool_schema_exposure", "tool_output_ingestion",
                  "system_prompt_in_context"}
        targets = self.a.get("targets") or {}
        for tid in ("agentdojo-workspace", "agentdojo-banking", "agentdojo-travel"):
            self.assertIn(tid, targets, "已接线的 AgentDojo 套件缺别名段：%s" % tid)
            ids = {c["id"] for c in targets[tid].get("capabilities") or []}
            self.assertTrue(common <= ids, "%s 缺通用能力：%s" % (tid, sorted(common - ids)))

    def test_every_alias_has_source_and_reason(self):
        for cap in self.tgt.get("capabilities") or []:
            self.assertTrue(cap.get("id"), cap)
            self.assertTrue(str(cap.get("source") or "").strip(), cap["id"])
            self.assertTrue(str(cap.get("reason") or "").strip(), cap["id"])
            self.assertTrue(cap.get("actions"), cap["id"])

    def test_capability_ids_are_unique(self):
        ids = [c["id"] for c in self.tgt.get("capabilities") or []]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_exclusion_has_a_reason(self):
        for row in self.tgt.get("excluded") or []:
            self.assertTrue(row.get("family"))
            self.assertTrue(str(row.get("reason") or "").strip(), row.get("family"))
            self.assertTrue(row.get("actions"), row.get("family"))

    def test_alias_file_is_not_a_json_profile(self):
        """`cardcheck` 用 `targets/**/*.json` 收画像；本文件不是画像，故不得是 .json。"""
        p = ROOT / "targets" / "capability-aliases.yaml"
        self.assertTrue(p.exists())
        self.assertFalse((ROOT / "targets" / "capability-aliases.json").exists())


class TestExclusionsAreReal(unittest.TestCase):
    """**本测试集存在的主要理由**：排除项不许被别名偷偷放行。"""

    def setUp(self):
        self.have, self.det = T.expand_tools(profile(), TARGET)

    def test_excluded_actions_are_not_in_the_expanded_set(self):
        for act, why in (self.det["excluded"] or {}).items():
            self.assertNotIn(act, self.have, "被排除的动作却出现在可用集合里：%s（%s）" % (act, why))

    def test_the_headline_gaps_stay_gaps(self):
        """头部缺口是**目标真的没有**的面，别名不许把它们补上。"""
        for act in ("knowledge_retrieve", "authz_decide", "memory_write", "memory_retrieve",
                    "register_tool", "server_log_readback", "execute_manipulation",
                    "load_model", "agent_message"):
            self.assertNotIn(act, self.have, act)

    def test_exclusion_map_is_not_empty(self):
        self.assertGreaterEqual(len(self.det["excluded"] or {}), 10)


class TestExpansionIsDecomposable(unittest.TestCase):
    def test_direct_and_aliased_are_reported_separately(self):
        _have, det = T.expand_tools(profile(), TARGET)
        self.assertEqual(det["raw_tools"], len(profile()["tools"]))
        self.assertGreater(det["aliased_count"], 0)
        # 别名集合与逐字命中集合不相交
        self.assertEqual(set(det["direct"]) & set(det["aliased"]), set())

    def test_every_aliased_action_has_a_capability(self):
        amap = T.alias_map(TARGET)
        _have, det = T.expand_tools(profile(), TARGET)
        for act in det["aliased"]:
            self.assertIn(act, amap)
            self.assertTrue(amap[act]["source"], act)


class TestCoverageDeltaIsPinned(unittest.TestCase):
    """别名的效果要**被测试记住**：净增多少张、增在哪几类。数字变了必须有人过目。"""

    EMPTY = {"version": None, "targets": {}}

    def _applicable(self, aliases):
        out = set()
        for c in cards():
            ok, _st, _why = P.applicable(c, profile(), aliases)
            if ok:
                out.add(c["method_id"])
        return out

    def test_alias_delta_is_eleven_cards(self):
        """别名带来的适用增量 = **11** 张（原为 8，2026-10-03 因 **G-43** 变 11）。

        为什么变：G-43 把「观测落点名字」从 10 张 T08 卡的 `required_actions` 迁出
        （`server_log_readback` / `intent_reconstruction` / `verbatim_disclosure` /
        `user_solicitation`）⇒ 其中 **3 张**在 workspace 上从 `untested` 变 `scored`。
 依据见 `results/README.md` §4.1 与 2026-10-03 批准。
        """
        off, on = self._applicable(self.EMPTY), self._applicable(None)
        self.assertEqual(len(off), 13, "纯字符串口径的适用数变了")
        # 2026-10-04：展开口径 24 -> 25、增量 11 -> 12（新增 T05.LIT-B-85B.SELECTION_HIJACK）。
        # 它只声明 read_tool_metadata / select_tool / invoke_tool ⇒ 纯字符串口径下不适用，
        # 别名展开后才落进集合 —— 与那 11 张同一类增量。
        # 2026-10-04：24 -> 25（新增 T05.LIT-B-85B.SELECTION_HIJACK，它在展开口径下适用）
        self.assertEqual(len(on), 25, "展开口径的适用数变了")
        self.assertEqual(len(on - off), 12)

    def test_new_cards_come_from_t02_t05_t07_t08(self):
        """增量的类构成：T02/T05/T07（别名）+ **T08**（G-43 迁出观测侧名字）。"""
        off, on = self._applicable(self.EMPTY), self._applicable(None)
        by_case = {c["method_id"]: c["case_id"] for c in cards()}
        self.assertEqual(sorted({by_case[m] for m in (on - off)}),
                         ["T02", "T05", "T07", "T08"])

    def test_aliases_do_not_change_the_precondition_gate(self):
        """别名只作用于"动作"那一问；前置条件不满足的卡不该因为别名而变成适用。"""
        for c in cards():
            ok_off, st_off, _ = P.applicable(c, profile(), self.EMPTY)
            ok_on, st_on, why_on = P.applicable(c, profile(), None)
            if not ok_off and st_off == P.NOT_APPLICABLE:
                # 关别名时因前置条件不适用 ⇒ 开别名后仍不得变成适用
                self.assertFalse(ok_on, "%s 因前置条件不适用，开别名后却适用来" % c["method_id"])
            if ok_on and not ok_off:
                self.assertNotIn("前置条件", why_on)


class TestBothCalibersAgreeWhereTheyShould(unittest.TestCase):
    """先验与 runner 必须同口径（都用展开），否则两处会漂移。"""

    def test_prior_and_runner_agree_with_aliases_on(self):
        from harness import runner as R
        prof = profile()

        class StubTarget:
            target_id = TARGET

            def tools(self):
                return list(prof["tools"])

            def design_dimensions(self):
                return dict(prof["design_dimensions"])

        stub, diff = StubTarget(), []
        for c in cards():
            ok_p, st_p, _ = P.applicable(c, prof)
            ok_r, st_r, _ = R.applicability(c, stub)
            norm_p = (ok_p, st_p if not ok_p else None)
            norm_r = (ok_r, st_r if not ok_r else None)
            if norm_p != norm_r:
                diff.append((c["method_id"], norm_p, norm_r))
        self.assertEqual(diff, [], "两处口径不一致：%s" % diff[:3])

    def test_runner_prose_still_falls_back_if_aliases_are_broken(self):
        """对齐表坏掉时 runner 应退回原始工具清单，而不是让测量跑不动。"""
        src = (ROOT / "harness" / "runner.py").read_text(encoding="utf-8")
        self.assertIn("except Exception", src)


class TestEveryProfileConformsToSchema(unittest.TestCase):
    """守住画像的形状。**这条是被一次真实失败逼出来的**：

    InjecAgent 的真实工具名是 CamelCase（`AmazonAddToCart`），而
    `spec/target-profile.schema.json` 要求 `tools` 匹配 `^[a-z][a-z0-9_]*$`
    ⇒ 首次提交时 `cardcheck` 报了 **330 条 ERROR**。
    补救不是改 schema，而是**机械**归一化（`to_snake`）并把该变换记录在画像里。
    """

    REQUIRED = ["target_id", "display_name", "design_dimensions", "tools",
                "receipt_supported", "cleanup_supported", "model", "deployment",
                "provenance", "reproducibility_note"]
    DIMS = ["input_trust", "access_sensitivity", "workflow", "action", "memory",
            "tool", "user_interface"]

    def profiles(self):
        return sorted((ROOT / "targets").glob("*.json"))

    def test_every_profile_has_the_required_keys(self):
        for p in self.profiles():
            d = json.loads(p.read_text(encoding="utf-8"))
            for k in self.REQUIRED:
                self.assertIn(k, d, "%s 缺 %s" % (p.name, k))

    def test_tools_match_the_schema_pattern(self):
        import re
        pat = re.compile(r"^[a-z][a-z0-9_]*$")
        for p in self.profiles():
            d = json.loads(p.read_text(encoding="utf-8"))
            bad = [t for t in d["tools"] if not pat.match(t)]
            self.assertEqual(bad[:3], [], "%s 的工具名不符合 ^[a-z][a-z0-9_]*$" % p.name)
            self.assertEqual(len(d["tools"]), len(set(d["tools"])), "%s 工具有重复" % p.name)

    def test_design_dimensions_are_complete_and_in_range(self):
        for p in self.profiles():
            d = json.loads(p.read_text(encoding="utf-8"))
            dims = d["design_dimensions"]
            self.assertEqual(sorted(dims), sorted(self.DIMS), p.name)
            for k, v in dims.items():
                self.assertIn(v, (1, 2, 3), "%s.%s=%r" % (p.name, k, v))


class TestInjecAgentProfile(unittest.TestCase):
    """第二份画像：InjecAgent 的工具集。**工具清单是导出物，不是手抄的。**"""

    TID = "injecagent-toolkits"

    def setUp(self):
        self.prof = T.load_profile(self.TID)

    def test_tool_count_and_recorded_hash_agree(self):
        """画像自报的 sha256 必须与它自己的工具清单对得上（防手改）。"""
        import hashlib
        names = self.prof["tools"]
        digest = hashlib.sha256("\n".join(names).encode("utf-8")).hexdigest()[:16]
        self.assertIn(digest, self.prof["reproducibility_note"],
                      "画像里记的哈希与工具清单不符 ⇒ 有人改了清单却没重建")
        self.assertEqual(len(names), 330)

    def test_toolkit_prefix_is_preserved(self):
        """工具名带 toolkit 前缀（其 sed 规则是 kit+tool），归一化后仍能看出归属。"""
        for t in ("amazon_place_order", "terminal_execute", "web_browser_navigate_to",
                  "august_smart_lock_unlock_door", "epic_fhir_search_patients"):
            self.assertIn(t, self.prof["tools"], t)

    def test_dimensions_have_evidence_in_the_note(self):
        for dim in ("input_trust", "access_sensitivity", "workflow", "action",
                    "memory", "tool", "user_interface"):
            self.assertIn(dim, self.prof["reproducibility_note"], dim)

    def test_not_runnable_here_is_stated(self):
        note = self.prof["reproducibility_note"]
        self.assertIn("先验分", note)
        self.assertFalse(self.prof["receipt_supported"])
        self.assertFalse(self.prof["cleanup_supported"])

    def test_alias_delta_is_pinned(self):
        """钉住适用数：数字变了必须有人过目。

        **2026-10-03（G-43）由 25 变 28**：把「观测落点名字」从 10 张 T08 卡的
        `required_actions` 迁出后，其中 3 张在 injecagent 的展开口径下也变适用
        （`tool_call` / `tool_list` 本就在 injecagent 的别名覆盖里）。
        ⚠️ 但这 **3 张是"纸面适用性"**：`injecagent-toolkits` 仍是 `PAPER_ONLY`（无适配器、未实测）
        ⇒ 不得计入任何"已覆盖"的表述。
        """
        cards = [yaml.safe_load(p.read_text(encoding="utf-8"))
                 for p in sorted((ROOT / "methods").glob("T0*/cards/*.yaml"))]
        ok = [c for c in cards if P.applicable(c, self.prof, None)[0]]
        # 2026-10-04：28 -> 29（新增 T05.LIT-B-85B.SELECTION_HIJACK）
        # 2026-10-04：29 -> 30（新增 T04.EXT-T04-CARRIER，它在 injecagent 的展开口径下适用）
        self.assertEqual(len(ok), 30)
        # 2026-10-04：加 T04（新增的承载式卡在该画像的展开口径下适用）
        self.assertEqual(sorted({c["case_id"] for c in ok}),
                         ["T02", "T04", "T05", "T06", "T07", "T08"])

    def test_the_knowledge_corpus_judgment_is_not_made_for_us(self):
        """`knowledge_retrieve` 是**一处判断**（网页检索算不算语料面），本轮从严排除。

        若哪天有人把它加进别名，这条会先炸——**因为那会一次性改变约 20 张卡的适用性**，
 须由拍板（见 D22 的"危险方向是滥不是漏"）。
        """
        have, det = T.expand_tools(self.prof, self.TID)
        for act in ("knowledge_retrieve", "retrieve_document", "rag_query"):
            self.assertNotIn(act, have, act)
        self.assertTrue(any("检索语料" in v for v in det["excluded"].values()))

    def test_two_calibers_differ_and_both_are_real(self):
        """纯字符串口径下这份画像覆盖 **0** 张；展开口径下 25 张。两个数都要报。"""
        raw = {str(x) for x in self.prof["tools"]}
        cards = [yaml.safe_load(p.read_text(encoding="utf-8"))
                 for p in sorted((ROOT / "methods").glob("T0*/cards/*.yaml"))]
        direct = [c for c in cards
                  if set((c.get("trigger_path") or {}).get("required_actions") or []) <= raw]
        self.assertEqual(len(direct), 0, "纯字符串口径不再为 0 ⇒ 口径说明要更新")


class TestRagPipelineProfile(unittest.TestCase):
    """第三份画像：PoisonedRAG 的 RAG 评测管线。

    它的用途是**把 D23 的判断变成事实**：D23 问"网页检索算不算可投毒的语料面"（判断），
    而这份画像**真的有语料与检索器** ⇒ 在它上面 `knowledge_retrieve` 是事实。
    """

    TID = "poisonedrag-rag-pipeline"

    def setUp(self):
        self.prof = T.load_profile(self.TID)

    def test_tools_are_source_symbols_not_card_vocabulary(self):
        """工具名必须取**代码自己的符号名**，不得直接把卡的动作名写进画像（那是套答案）。"""
        self.assertEqual(sorted(self.prof["tools"]),
                         ["encode_corpus", "encode_queries", "query", "wrap_prompt"])

    def test_every_tool_cites_file_and_line(self):
        note = self.prof["reproducibility_note"]
        for sym in ("beir_utils.py:85", "beir_utils.py:46", "prompts.py:8", "GPT.py:14"):
            self.assertIn(sym, note, sym)

    def test_contamination_risk_is_stated(self):
        """PoisonedRAG 是 T01 两张卡的**机制来源**；用它当靶标 = 方法针对该目标调过。

        本画像只用于先验。这条断言保证那句话不会被后来的人删掉。
        """
        note = self.prof["reproducibility_note"]
        self.assertIn("污染风险", note)
        self.assertIn("实测", note)

    def test_knowledge_retrieve_is_a_fact_here_not_a_judgment(self):
        have, det = T.expand_tools(self.prof, self.TID)
        self.assertIn("knowledge_retrieve", have)
        self.assertNotIn("knowledge_retrieve", det["excluded"])

    def test_it_is_not_an_agent_so_tool_calling_is_excluded(self):
        """这是 RAG 管线不是 agent：无 tool-calling ⇒ 工具调用一族必须排除。"""
        have, det = T.expand_tools(self.prof, self.TID)
        for act in ("tool_call", "tool_invoke", "select_tool", "read_tool_metadata"):
            self.assertNotIn(act, have, act)
            self.assertIn(act, det["excluded"], act)

    def test_coverage_is_pinned(self):
        cards = [yaml.safe_load(p.read_text(encoding="utf-8"))
                 for p in sorted((ROOT / "methods").glob("T0*/cards/*.yaml"))]
        ok = [c for c in cards if P.applicable(c, self.prof, None)[0]]
        self.assertEqual(len(ok), 32)
        self.assertEqual(sorted({c["case_id"] for c in ok}), ["T01", "T06", "T07"])

    def test_union_across_all_profiles_is_pinned(self):
        """全部画像合计覆盖的不同方法数。数字变了必须有人过目。

        **2026-10-03 的两次变更（逐个可重算，不得静默改）**：

        | 变更 | 画像数 | union |
        |---|---|---|
        | 原值（3 份） | 3 | 40 |
        | + `agentdojo-banking` · `agentdojo-travel`（T08 会话） | 5 | **40**（贡献 0：同族
          suite 的适用卡已被 `agentdojo-workspace` 覆盖） |
        | + `mcp-local`（T05 会话，见 `targets/mcp-local.json`） | **6** | **54**（贡献 14） |
        | **+ G-43（观测侧名字从 10 张 T08 卡迁出，2026-10-03）** | 6 | **59**（贡献 5） |
        | **+ T03 授权判定闸门（`mcp-local` 加 `authz_decide`，2026-10-03）** | 6 | **64**（贡献 5） |
        | **+ T04 具身面（`mcp-local` 加 15 个控制动作工具，2026-10-03）** | 6 | **68**（贡献 4） |

        **T04 那 4 张的来源**（`mcp-local` 的展开口径 43 → 62）：
        15 个具身工具名**逐字取自 T04 卡上的 `allowed_tools`**（不发明别名）
        ⇒ 原先 24 张卡"46 个动作名一个都不存在"，现在 **6 张一张都不缺**
        （另 18 张仍缺 32 个更专门的动作名：`transcribe_voice_input` 2 张、
        `ingest_video_stream` / `decode_surgical_action` / `execute_instrument_motion` 等各 1 张）。
        ⚠️ **具身面是进程内的运动学占位器**，不接真机也不接 MuJoCo，**不声称物理后果**；
        判据自己也只到 `behavior` 层。

        **G-43 那 5 张的来源**：`B-T08-03` · `B-T08-04` · `B-T08-09` · `LIT-B-163` · `LIT-B-163B`
        （`required_actions` 里原先那个「观测落点名字」被迁出，剩下的 `tool_call` / `tool_list`
        本就在各画像的展开集里）。⚠️ **其中在纸面画像（`injecagent` / `poisonedrag`）上的部分是纸面适用性**，
        一格未实测；只有 4 个可跑靶标上的那部分才可能变成实测。

        **T03 那 5 张的来源**（`mcp-local` 的展开口径 35 → 43）：
        `B-47` · `B-55` · `B-58` · `B-T03-01` · `B-T03-03`。
        ⚠️ 授权闸门落地**前**测算的是 6 张，落地**后**实测是 **5 张** —— 差在
        `B-52.delegation_scope_expansion`：它的**前置条件要 `workflow>=3`**，而 `mcp-local` 的
        `workflow=2` ⇒ 记 `not_applicable`（**不是缺动作**）。
        ⇒ **「只差一个名字就能翻」不等于「翻了就出分」**，前置条件是第二道闸门。
        ⚠️ 另：`B-58` 结构上适用，但判据是 `ground_truth_contradiction`，而该判据的双 reader
        **没有任何靶标提供** ⇒ 运行期会记 `inconclusive`。

        ⚠️ `mcp-local` 的展开口径在其上适用 **43 张卡**（T05 10 · T06 18 · T07 4 · T02 3 · T08 3 · T03 5）
        —— 跨类那一部分是**结构上可行**（它确有用户轮、响应、工具调用与工具元数据面），
        **不是**当前实现的测量结论。两个口径（纯字符串 / 展开）在同一次交付里并列报告。
        """
        cards = [yaml.safe_load(p.read_text(encoding="utf-8"))
                 for p in sorted((ROOT / "methods").glob("T0*/cards/*.yaml"))]
        union = set()
        for tp in sorted((ROOT / "targets").glob("*.json")):
            prof = json.loads(tp.read_text(encoding="utf-8"))
            for c in cards:
                if P.applicable(c, prof, None)[0]:
                    union.add(c["method_id"])
        # 2026-10-04：68 -> 69（新增 T05.LIT-B-85B.SELECTION_HIJACK；它只要求在
        # mcp-local 上存在的 select_tool/invoke_tool/read_tool_metadata ⇒ 贡献 1）
        # 2026-10-04：69 -> 70（新增 T04.EXT-T04-CARRIER，贡献 1）
        # 2026-10-05：70 -> 74（**T02 审计器件落地**：`mcp-local` 新增两个审计面工具
        #   `log_interpret` / `trace_cleanup`，见
        #   `results/README.md` §4 步骤 5）。
        #   逐条点名（当前实现离线复算，`expand_tools` + `prior.applicable` 两条口径都过）：
        #     + T02.AUD-TRACE-DELETE.trace_self_delete      （`trace_cleanup`）
        #     + T02.AUD-TRACE-EDIT.trace_record_edit         （`trace_cleanup`）
        #     + T02.AUD-TRACE-FORGE.forged_event_insertion   （`trace_cleanup`）
        #     + T02.AUD-NODE-SUBSTITUTE.provenance_node_substitution（`log_interpret`）
        #   ⚠️ 另外 4 张卡（COVER-ACCESS / INTERP-EVASION / LOGSUBSTRATE-s2 /
        #   MODEL-BACKDOOR）**只过了动作闸门**，仍被前置条件挡住（都要求 `workflow>=3`，
        #   本靶标是 2）⇒ 不进这个并集（"只差一个名字就能翻"≠"翻了就出分"）。
        self.assertEqual(len(union), 74)
        self.assertEqual(len(list((ROOT / "targets").glob("*.json"))), 6)


if __name__ == "__main__":
    unittest.main()
