# -*- coding: utf-8 -*-
"""方法卡契约的可执行保证。

三件事：
  1. 校验器自身正确（最小 JSON Schema 子集的每个 keyword 都有正反用例）；
  2. **校验器不会静默失效**——schema 里出现未实现的 keyword 必须报错；
  3. 门禁的反向自测——把文档/schema 改坏，`card_contract_sync` 必须失败。
"""
from __future__ import annotations

import copy
import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import cardcheck as CC      # noqa: E402
from tools import gates                # noqa: E402

REPO = pathlib.Path(gates.ROOT)


class TestMiniValidator(unittest.TestCase):
    """最小 JSON Schema 子集校验器的正反用例。"""

    def test_type(self):
        self.assertEqual(CC.validate("x", {"type": "string"}), [])
        self.assertTrue(CC.validate(1, {"type": "string"}))
        self.assertTrue(CC.validate("x", {"type": "integer"}))
        # bool 是 int 的子类，必须单独判定——否则 true 会被当成合法整数
        self.assertTrue(CC.validate(True, {"type": "integer"}))
        self.assertEqual(CC.validate(True, {"type": "boolean"}), [])

    def test_type_union(self):
        s = {"type": ["object", "null"]}
        self.assertEqual(CC.validate(None, s), [])
        self.assertEqual(CC.validate({}, s), [])
        self.assertTrue(CC.validate("x", s))

    def test_enum_and_const(self):
        s = {"enum": ["a", "b"]}
        self.assertEqual(CC.validate("a", s), [])
        self.assertTrue(CC.validate("c", s))
        self.assertEqual(CC.validate(1, {"const": 1}), [])
        self.assertTrue(CC.validate(2, {"const": 1}))
        # bool/int 混淆：True 不得被判为等于 1
        self.assertTrue(CC.validate(True, {"const": 1}))

    def test_string_keywords(self):
        self.assertTrue(CC.validate("ab", {"minLength": 3}))
        self.assertTrue(CC.validate("abcd", {"maxLength": 3}))
        self.assertEqual(CC.validate("abc", {"pattern": "^a.c$"}), [])
        self.assertTrue(CC.validate("xbc", {"pattern": "^a.c$"}))

    def test_number_keywords(self):
        self.assertTrue(CC.validate(0, {"minimum": 1}))
        self.assertTrue(CC.validate(4, {"maximum": 3}))
        # bool 是 int 的子类，但**不是** number：数值关键字对它不适用……
        self.assertEqual(CC.validate(True, {"minimum": 1}), [])
        # ……而一旦同时声明 type，它就会被类型检查挡住。
        self.assertTrue(CC.validate(True, {"type": "number", "minimum": 1}))

    def test_array_keywords(self):
        self.assertTrue(CC.validate([], {"minItems": 1}))
        self.assertTrue(CC.validate([1, 2], {"maxItems": 1}))
        self.assertTrue(CC.validate([1, 1], {"uniqueItems": True}))
        self.assertEqual(CC.validate([1, 2], {"uniqueItems": True}), [])
        self.assertTrue(CC.validate(["a"], {"items": {"type": "integer"}}))

    def test_object_keywords(self):
        s = {"type": "object", "required": ["a"], "additionalProperties": False,
             "properties": {"a": {"type": "integer"}}}
        self.assertEqual(CC.validate({"a": 1}, s), [])
        self.assertTrue(CC.validate({}, s))
        self.assertTrue(CC.validate({"a": 1, "b": 2}, s))
        self.assertTrue(CC.validate({"a": 1, "b": 2}, {"minProperties": 3}))
        # additionalProperties 为 schema 时，未列出的键要按该 schema 校验
        s2 = {"properties": {}, "additionalProperties": {"type": "string"}}
        self.assertEqual(CC.validate({"k": "v"}, s2), [])
        self.assertTrue(CC.validate({"k": 1}, s2))

    def test_one_of(self):
        s = {"oneOf": [{"type": "string"}, {"type": "integer"}]}
        self.assertEqual(CC.validate("a", s), [])
        self.assertTrue(CC.validate(1.5, s))
        # 恰好匹配 0 个或多个都要失败
        self.assertTrue(CC.validate("a", {"oneOf": [{"type": "string"}, {"minLength": 1}]}))


class TestKeywordSelfGuard(unittest.TestCase):
    """schema 用了校验器不认识的 keyword ⇒ 必须报错，不能静默忽略。"""

    SCHEMAS = ["method-card.schema.json", "scenario-manifest.schema.json",
               "target-profile.schema.json", "judge-registry.schema.json"]

    def test_all_shipped_schemas_are_supported(self):
        for name in self.SCHEMAS:
            with self.subTest(schema=name):
                sch = json.loads((REPO / "spec" / name).read_text(encoding="utf-8"))
                errs = CC.assert_keywords_supported(sch, name)
                self.assertEqual(errs, [], "未实现的 keyword：\n" + "\n".join(errs))

    def test_guard_actually_fires(self):
        errs = CC.assert_keywords_supported({"type": "object", "if": {"type": "string"}}, "t")
        self.assertTrue(any("if" in e for e in errs), "self-guard 没抓住未实现的 keyword")


class TestFixtures(unittest.TestCase):
    """1 套合法 + 19 套违规，每套只破坏一处。"""

    def test_all_fixtures_behave_as_expected(self):
        r = CC.run_fixtures()
        self.assertTrue(r["ok"], "\n".join(r["failures"]))
        self.assertGreaterEqual(r["cases"], 12, "违规样本数必须 >= 12（设计规格 F6 DoD）")

    def test_at_least_12_rejection_samples(self):
        exp = json.loads((REPO / "tests" / "fixtures" / "cards" / "expectations.json")
                         .read_text(encoding="utf-8"))
        bad = [c for c in exp["cases"] if c["expect_error"]]
        self.assertGreaterEqual(len(bad), 12)
        self.assertEqual(len({c["dir"] for c in exp["cases"]}), len(exp["cases"]), "夹具目录名重复")

    def test_valid_fixture_really_valid(self):
        ctx = CC.Ctx(REPO, methods_dir=REPO / "tests" / "fixtures" / "cards" / "valid")
        res = CC.run(ctx)
        self.assertTrue(res["ok"], "合法夹具被拒：\n" + "\n".join(
            "r%s %s %s" % (e["rule"], e["path"], e["message"]) for e in res["errors"]))


class TestRuleCoverage(unittest.TestCase):
    def test_every_declared_rule_is_mapped(self):
        ctx = CC.Ctx(REPO)
        cov = CC.coverage(ctx)
        self.assertEqual(cov["missing"], [], "schema 里的规则没有执行器")
        self.assertEqual(cov["extra"], [], "规则表超出了 schema 声明的条数")

    def test_deferred_rules_are_documented(self):
        ctx = CC.Ctx(REPO)
        text = (REPO / "docs" / "ci-coverage.md").read_text(encoding="utf-8")
        for i in sorted(CC.RULES):
            rid, _fn, status, why = CC.RULES[i]
            if status == "deferred":
                self.assertIn("`%s`" % rid, text, "缺口 %s 未登记" % rid)
                self.assertTrue(why, "缺口 %s 没有写原因" % rid)

    def test_ci_coverage_sync_passes(self):
        r = gates.check_ci_coverage_sync()
        self.assertEqual(r.status, "pass", "\n".join(f.message for f in r.errors))


class TestCardContractSyncGate(unittest.TestCase):
    def test_repo_in_sync(self):
        r = gates.check_card_contract_sync()
        self.assertEqual(r.status, "pass",
                         "\n".join("%s %s" % (f.path, f.message) for f in r.errors))

    def _drift(self, old: str, new: str, target: str = "docs/technical-design.md"):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            (td / "docs").mkdir()
            (td / "spec").mkdir()
            doc = (REPO / target).read_text(encoding="utf-8")
            self.assertIn(old, doc, "锚点不存在：%r" % old)
            (td / target).write_text(doc.replace(old, new), encoding="utf-8", newline="\n")
            for name in ("method-card.schema.json", "judge-registry.schema.json",
                         "target-profile.schema.json"):
                shutil.copy(REPO / "spec" / name, td / "spec" / name)
            orig = gates.ROOT
            gates.ROOT = td
            try:
                return gates.check_card_contract_sync()
            finally:
                gates.ROOT = orig

    def test_detects_doc_field_without_schema(self):
        """回归：这正是本项目真实发生过的事故——文档里写了 schema 里没有的字段。"""
        r = self._drift("| `judge` | object | 必填 | 见 §2.4 |",
                        "| `judge` | object | 必填 | 见 §2.4 |\n| `totally_new_field` | string | 必填 | 文档自造 |")
        self.assertEqual(r.status, "fail", "文档引入 schema 没有的字段却没被发现")
        self.assertTrue(any("totally_new_field" in f.message for f in r.errors))

    def test_detects_missing_schema_file(self):
        r = self._drift("<!-- schema-authority: spec/method-card.schema.json -->",
                        "<!-- schema-authority: spec/nope.schema.json -->")
        self.assertEqual(r.status, "fail")


class TestGate1Wiring(unittest.TestCase):
    def test_gate1_has_executables(self):
        for item in gates.GATE1_CHECKS:
            self.assertTrue(callable(item[1]), "Gate 1 项 %s 仍是占位" % item[0])

    def test_gate1_is_executable_not_placeholder(self):
        """Gate 1 的每一项都必须有执行器——**不能是 [TODO] 占位**。

        注意断言的是「可执行」，不是「全绿」。Gate 1 里的 `method_card_schema`
        会随 `methods/` 的真实状态变红（例如卡缺必填字段时），**那是它该做的事**。
        一条永远为绿的检查等于没有检查。
        """
        res = gates.run("1")
        bad = [(r.name, r.status, r.summary) for r in res if r.status == "not_implemented"]
        self.assertEqual(bad, [], "Gate 1 仍有占位项：%s" % bad)
        names = {r.name for r in res}
        self.assertIn("card_fixtures", names)
        fx = [r for r in res if r.name == "card_fixtures"][0]
        self.assertEqual(fx.status, "pass", fx.summary)


if __name__ == "__main__":
    unittest.main(verbosity=2)