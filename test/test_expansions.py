import unittest
from jsgf import AlternativeSet, Sequence, Literal, OptionalGrouping, RequiredGrouping, Rule, RuleRef


class ParentCase(unittest.TestCase):
    def setUp(self):
        alt_set1 = AlternativeSet("hello", "hi", "hey")
        alt_set2 = AlternativeSet("alice", "bob", "eve")
        self.expansions = [Sequence(alt_set1, alt_set2), alt_set1, alt_set2]

    def test_parent_is_none(self):
        self.assertIsNone(self.expansions[0].parent)

    def check_descendants(self, expansion):
        for child in expansion.children:
            self.assertEqual(expansion, child.parent)
            self.check_descendants(child)

    def test_parent_is_set(self):
        # Recursively test the descendants of the Sequence expansion
        self.check_descendants(self.expansions[0])


class Comparisons(unittest.TestCase):
    def test_literals(self):
        self.assertEqual(Literal("hello"), Literal("hello"))
        self.assertNotEqual(Literal("hey"), Literal("hello"))

    def test_alt_sets(self):
        self.assertEqual(AlternativeSet("hello"), AlternativeSet("hello"))
        self.assertNotEqual(AlternativeSet("hey"), AlternativeSet("hello"))

    def test_optional(self):
        self.assertEqual(OptionalGrouping("hello"), OptionalGrouping("hello"))
        self.assertNotEqual(OptionalGrouping("hello"), OptionalGrouping("hey"))
        self.assertNotEqual(OptionalGrouping("hello"), AlternativeSet("hello"))

    def test_required_grouping(self):
        self.assertEqual(RequiredGrouping("hello"), RequiredGrouping("hello"))
        self.assertNotEqual(RequiredGrouping("hello"), RequiredGrouping("hey"))
        self.assertNotEqual(RequiredGrouping("hello"), AlternativeSet("hello"))
        self.assertNotEqual(RequiredGrouping("hello"), AlternativeSet("hello"))

    def test_rule_ref(self):
        rule1 = Rule("test", True, "test")
        rule2 = Rule("test", True, "testing")
        self.assertEqual(RuleRef(rule1), RuleRef(rule1))
        self.assertNotEqual(RuleRef(rule1), RuleRef(rule2))


if __name__ == '__main__':
    unittest.main()
