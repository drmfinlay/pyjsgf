import unittest

from jsgf.ext import Dictation

from jsgf import *
from jsgf import CompilationError


class MemberTests(unittest.TestCase):
    """
    Test some methods and properties of the Rule class.
    """
    def test_dependencies_simple(self):
        rule2 = HiddenRule("greetWord", AlternativeSet("hello", "hi"))
        rule3 = HiddenRule("name", AlternativeSet("peter", "john", "mary", "anna"))
        rule1 = PublicRule("greet", RequiredGrouping(RuleRef(rule2), RuleRef(rule3)))
        self.assertSetEqual(rule1.dependencies, {rule2, rule3})

    def test_dependencies_complex(self):
        rule2 = HiddenRule("greetWord", AlternativeSet("hello", "hi"))
        rule3 = HiddenRule("firstName", AlternativeSet("peter", "john", "mary", "anna"))
        rule4 = HiddenRule("lastName", AlternativeSet("smith", "ryan", "king", "turner"))
        rule5 = HiddenRule("name", RequiredGrouping(RuleRef(rule3),
                                                    OptionalGrouping(RuleRef(rule4))))
        rule1 = PublicRule("greet", RequiredGrouping(RuleRef(rule2), RuleRef(rule5)))

        # Test dependencies for each rule.
        self.assertSetEqual(rule1.dependencies, {rule2, rule3, rule4, rule5})
        self.assertSetEqual(rule5.dependencies, {rule3, rule4})
        self.assertSetEqual(rule2.dependencies, set())
        self.assertSetEqual(rule3.dependencies, set())
        self.assertSetEqual(rule4.dependencies, set())

    def test_dependencies_named_rule_ref(self):
        rule2 = HiddenRule("greetWord", AlternativeSet("hello", "hi"))
        rule3 = HiddenRule("firstName", AlternativeSet("peter", "john", "mary", "anna"))
        rule4 = HiddenRule("lastName", AlternativeSet("smith", "ryan", "king", "turner"))
        rule5 = HiddenRule("name", RequiredGrouping(
            NamedRuleRef("firstName"), OptionalGrouping(NamedRuleRef("lastName"))
        ))
        rule1 = PublicRule("greet", RequiredGrouping(NamedRuleRef("greetWord"),
                                                     NamedRuleRef("name")))

        # Add all rules to a grammar so that NamedRuleRefs can be matched and so
        # that testing <Rule>.dependent_rules works.
        grammar = Grammar()
        grammar.add_rules(rule1, rule2, rule3, rule4, rule5)

        # Test dependencies.
        self.assertSetEqual(rule1.dependencies, {rule2, rule3, rule4, rule5})
        self.assertSetEqual(rule5.dependencies, {rule3, rule4})
        self.assertSetEqual(rule2.dependencies, set())
        self.assertSetEqual(rule3.dependencies, set())
        self.assertSetEqual(rule4.dependencies, set())

        # Test dependent rules.
        self.assertSetEqual(rule2.dependent_rules, {rule1})
        self.assertSetEqual(rule3.dependent_rules, {rule1, rule5})
        self.assertSetEqual(rule4.dependent_rules, {rule1, rule5})
        self.assertSetEqual(rule5.dependent_rules, {rule1})

    def test_dependent_rules(self):
        r1 = PublicRule("r1", "hi")
        r2 = PublicRule("r2", RuleRef(r1))
        self.assertEqual(r1.dependent_rules, set(),
                         "r1 has no dependent rules if it isn't in a grammar")
        g = Grammar()
        g.add_rule(r1)
        self.assertEqual(r1.dependent_rules, set(),
                         "r1 has no dependent rules in its grammar")
        g.add_rule(r2)
        self.assertEqual(r1.dependent_rules, {r2}, "r1 has dependent rule r2")

    def test_was_matched(self):
        """
        Test the was_matched property of the Rule class.
        """
        r = PublicRule("test", Sequence("hello", OptionalGrouping("hello")))
        self.assertFalse(r.was_matched, "was_matched should initially be False")
        self.assertTrue(r.matches("hello hello"))
        self.assertTrue(r.was_matched, "was_matched should be True if matches() "
                                       "returned True")
        self.assertFalse(r.matches("hello hello world"))
        self.assertFalse(r.was_matched, "was_matched should be False if matches() "
                                        "returned True")

    def test_enable_disable(self):
        r1 = PublicRule("test", "hello")
        self.assertTrue(r1.active, "should initially be True")
        self.assertTrue(r1.matches("hello"))
        self.assertTrue(r1.was_matched)
        self.assertEqual(r1.compile(), "public <test> = hello;")
        r1.disable()
        self.assertFalse(r1.active)
        self.assertTrue(r1.was_matched, "was_matched should still be True")
        self.assertFalse(r1.matches("hello"))
        self.assertEqual(r1.compile(), "")
        r1.enable()
        self.assertTrue(r1.active)
        self.assertTrue(r1.matches("hello"))
        self.assertTrue(r1.was_matched)
        self.assertEqual(r1.compile(), "public <test> = hello;")

    def test_find_matching_part(self):
        r1 = PublicRule("test", "hello world")

        # Test with matches.
        m = "hello world"
        self.assertEqual(r1.find_matching_part("test hello world"), m)
        self.assertEqual(r1.find_matching_part("hello world test"), m)
        self.assertEqual(r1.find_matching_part("test hello world test"), m)
        self.assertEqual(r1.find_matching_part("test abc hello world"), m)
        self.assertEqual(r1.find_matching_part("test test hello world"), m)
        self.assertEqual(r1.find_matching_part("hello world abc test"), m)
        self.assertEqual(r1.find_matching_part("hello world test test"), m)
        self.assertEqual(
            r1.find_matching_part("test abc hello world test abc"), m
        )
        self.assertEqual(
            r1.find_matching_part("test test hello world test test"), m
        )

        # Test with no matches.
        self.assertIsNone(r1.find_matching_part(""))
        self.assertIsNone(r1.find_matching_part("test hello"))
        self.assertIsNone(r1.find_matching_part("abc hello def world"))
        self.assertIsNone(r1.find_matching_part("hello abc def world"))

        # Test disabled rule.
        r1.disable()
        self.assertIsNone(r1.find_matching_part(""))
        self.assertIsNone(r1.find_matching_part("hello world"))
        self.assertIsNone(r1.find_matching_part("test"))


class InvalidRules(unittest.TestCase):
    def test_invalid_rules(self):
        # Literals with text == "" raise CompilationErrors
        self.assertRaises(CompilationError, PublicRule("test", "").compile)
        self.assertRaises(CompilationError, PublicRule("test", Literal("")).compile)

        # Dictation doesn't raise errors on compilation.
        self.assertEqual(PublicRule("test", Dictation()).compile(), "")


class ComparisonTests(unittest.TestCase):
    def test_same_type(self):
        self.assertEqual(PublicRule("test", "test"), PublicRule("test", "test"),
                         "identical rules were not equal")

        self.assertNotEqual(
            PublicRule("test1", "test"), PublicRule("test2", "test"),
            "rules with only different names were equal")

        self.assertNotEqual(
            Rule("test", False, "test"), Rule("test", True, "test"),
            "rules with only different visibility were equal")

        self.assertNotEqual(
            PublicRule("test", "test"), PublicRule("test", "testing"),
            "rules with only different expansions were equal")

        self.assertNotEqual(
            PublicRule("test1", "test"), PublicRule("test2", "testing"),
            "rules with different expansions and names were equal")

        self.assertNotEqual(
            Rule("test", True, "test"), Rule("test", False, "testing"),
            "rules with different expansions and visibility were equal")

        self.assertNotEqual(
            Rule("test1", True, "test"), Rule("test2", False, "test"),
            "rules with different names and visibility were equal")

    def test_complex_expansions(self):
        self.assertEqual(PublicRule("test", Sequence("a", "b", "c")),
                         PublicRule("test", Sequence("a", "b", "c")),
                         "identical rules were not equal")

        self.assertNotEqual(PublicRule("test", Sequence("a", "b")),
                            PublicRule("test", Sequence("a", "b", "c")),
                            "rules with different expansions were equal")

        self.assertNotEqual(PublicRule("test", Sequence("a", "b", "c")),
                            PublicRule("test",
                                       Sequence("a", "b", OptionalGrouping("c"))),
                            "rules with different expansions were equal")

    def test_different_types(self):
        self.assertNotEqual(
            HiddenRule("test", "test"), PublicRule("test", "test"),
            "rules with only different visibility were equal")

        self.assertEqual(
            HiddenRule("test", "test"), Rule("test", False, "test"),
            "rules with only different types were not equal")

        self.assertEqual(
            PublicRule("test", "test"), Rule("test", True, "test"),
            "rules with only different types were not equal")

    def test_hashing(self):
        h = hash
        # Rules that are the same should generate the same hash
        self.assertEqual(h(PublicRule("a", "a")),
                         h(PublicRule("a", "a")))

        # Rules with only a different type should generate the same hash value
        self.assertEqual(h(PublicRule("a", "a")),
                         h(Rule("a", True, "a")))

        # Rules that are different should generate different values
        self.assertNotEqual(h(PublicRule("a", "a")),
                            h(HiddenRule("a", "a")))
        self.assertNotEqual(h(PublicRule("a", "a")),
                            h(Rule("a", False, "a")))
        self.assertNotEqual(h(PublicRule("a", "a")),
                            h(PublicRule("b", "a")))
        self.assertNotEqual(h(PublicRule("a", "a")),
                            h(PublicRule("a", "b")))
        self.assertNotEqual(h(PublicRule("a", "a")),
                            h(PublicRule("b", "b")))


class TagTests(unittest.TestCase):
    def test_simple(self):
        r = PublicRule("hello", "hello world")
        r.expansion.tag = "greet"
        self.assertTrue(r.has_tag("greet"))

    def test_no_tag(self):
        # Empty or whitespace-only strings are not valid JSGF tags.
        r = PublicRule("hello", "hello world")
        r.expansion.tag = ""
        self.assertFalse(r.has_tag(""))
        r.expansion.tag = "  "
        self.assertFalse(r.has_tag("  "))

    def test_referenced(self):
        n = Rule("n", False, AlternativeSet("one", "two", "three"))
        n.expansion.tag = "number"
        r = PublicRule("numbers", Repeat(RuleRef(n)))
        self.assertTrue(n.has_tag("number"))
        self.assertTrue(r.has_tag("number"))

    def test_whitespace(self):
        # Any leading or trailing whitespace should be trimmed by the Expansion.tag
        # setter and the Rule.has_tag method.
        r = PublicRule("hello", "hello world")
        r.expansion.tag = "  greet     "
        self.assertEqual(r.expansion.tag, "greet")
        self.assertTrue(r.has_tag("greet"))
        self.assertTrue(r.has_tag("  greet     "))

    def test_tag_properties(self):
        a, b, one = map(Literal, ["a", "b", "one"])
        a.tag = "letter"
        b.tag = "letter"
        one.tag = "number"
        e = AlternativeSet(a, b, one)
        e.tag = "alt_set"
        r = PublicRule("r", Repeat(e))

        # Tags should be in the order in which they would be compiled left-to-right
        # and the list should not be distinct in case someone wants to use tags like
        # that for some reason.
        self.assertListEqual(r.tags, ["letter", "letter", "number", "alt_set"])

        # Test matched_tags property
        self.assertListEqual(r.matched_tags, [])  # nothing matched yet
        r.matches("a")
        self.assertListEqual(r.matched_tags, ["letter", "alt_set"])
        r.matches("one")
        self.assertListEqual(r.matched_tags, ["number", "alt_set"])

        # Test that returned tags are not de-duplicated (this also tests Repeat)
        r.matches("a b")
        self.assertListEqual(r.matched_tags, ["letter", "letter", "alt_set"])

    def test_get_tags_matching(self):
        # Test with a simple rule
        e = AlternativeSet("open", "close")
        e.children[0].tag = "OPEN"
        e.children[1].tag = "CLOSE"
        cmd = PublicRule("command", Sequence(e, "the file"))
        self.assertListEqual(cmd.get_tags_matching("open the file"), ["OPEN"])

        # Test that a referenced rule also works
        op = Rule("operation", False, e.copy())
        cmd = PublicRule("command", Sequence(RuleRef(op), "the file"))
        self.assertListEqual(cmd.get_tags_matching("open the file"), ["OPEN"])


if __name__ == '__main__':
    unittest.main()
