import unittest

from jsgf import *
from jsgf.rules import CompilationError


class RuleDependenciesCase(unittest.TestCase):
    """
    Test the 'dependencies' property of the Rule class.
    """
    def test_simple(self):
        rule2 = HiddenRule("greetWord", AlternativeSet("hello", "hi"))
        rule3 = HiddenRule("name", AlternativeSet("peter", "john", "mary", "anna"))
        rule1 = PublicRule("greet", RequiredGrouping(RuleRef(rule2), RuleRef(rule3)))
        self.assertSetEqual(rule1.dependencies, {rule2, rule3})

    def test_complex(self):
        rule2 = HiddenRule("greetWord", AlternativeSet("hello", "hi"))
        rule3 = HiddenRule("firstName", AlternativeSet("peter", "john", "mary", "anna"))
        rule4 = HiddenRule("lastName", AlternativeSet("smith", "ryan", "king", "turner"))
        rule5 = HiddenRule("name", RequiredGrouping(RuleRef(rule3),
                                                    OptionalGrouping(RuleRef(rule4))))
        rule1 = PublicRule("greet", RequiredGrouping(RuleRef(rule2), RuleRef(rule5)))
        self.assertSetEqual(rule1.dependencies, {rule2, rule3, rule4, rule5})


class RuleRefCount(unittest.TestCase):
    """
    Test the 'reference_count' property of the Rule class.
    """
    def setUp(self):
        self.rule = HiddenRule("greet", "hello")

    def test_simple(self):
        rule_refs = [RuleRef(self.rule)]
        self.assertEqual(1, self.rule.reference_count)
        rule_refs.pop()
        self.assertEqual(0, self.rule.reference_count)

    def test_with_grammar(self):
        grammar = Grammar()
        grammar.add_rule(self.rule)
        self.assertEqual(0, self.rule.reference_count, "rule '%s' is not independent.")
        grammar.add_rule(PublicRule("test", RuleRef(self.rule)))
        self.assertEqual(1, self.rule.reference_count, "rule '%s' is independent.")


class OptionalOnlyRule(unittest.TestCase):
    def test_optional_only_rule(self):
        rule = PublicRule("test", OptionalGrouping("hello"))

        # Rules that only have optional literals are not valid
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
            "rules with only different types were equal")

        self.assertNotEqual(
            HiddenRule("test", "test"), Rule("test", False, "test"),
            "rules with only different types were equal")

        self.assertNotEqual(
            PublicRule("test", "test"), Rule("test", True, "test"),
            "rules with only different types were equal")


if __name__ == '__main__':
    unittest.main()
