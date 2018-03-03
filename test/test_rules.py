import unittest

from jsgf import *
from jsgf import CompilationError


class PropertiesTests(unittest.TestCase):
    """
    Test some properties of the Rule class.
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
        self.assertSetEqual(rule1.dependencies, {rule2, rule3, rule4, rule5})

    def test_reference_count_simple(self):
        r = HiddenRule("greet", "hello")
        rule_refs = [RuleRef(r)]
        self.assertEqual(1, r.reference_count)
        rule_refs.pop()
        self.assertEqual(0, r.reference_count)

    def test_reference_count_with_grammar(self):
        grammar = Grammar()
        r = HiddenRule("greet", "hello")
        grammar.add_rule(r)
        self.assertEqual(0, r.reference_count, "rule '%s' is not independent.")
        grammar.add_rule(PublicRule("test", RuleRef(r)))
        self.assertEqual(1, r.reference_count, "rule '%s' is independent.")

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


class InvalidRules(unittest.TestCase):
    def test_invalid_rules(self):
        invalid_rules = [
            PublicRule("test", OptionalGrouping("hello")),
            PublicRule("test", KleeneStar("hello")),
            PublicRule("test", AlternativeSet(OptionalGrouping("hello"))),
            PublicRule("test", Sequence(OptionalGrouping("hello"))),
            PublicRule("test", Sequence()),
            PublicRule("test", AlternativeSet()),
            PublicRule("test", VariableChildExpansion()),
            PublicRule("test", "")
        ]

        r = PublicRule("test", SingleChildExpansion("hello"))
        r.expansion.children.remove(Literal("hello"))
        invalid_rules.append(r)

        # Rules that only have optional literals are not valid
        for rule in invalid_rules:
            self.assertRaises(CompilationError, rule.compile)


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


if __name__ == '__main__':
    unittest.main()
