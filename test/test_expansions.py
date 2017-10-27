import unittest
from jsgf import *


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


class AncestorProperties(unittest.TestCase):
    """
    Test the ancestor properties of the Expansion class and its subclasses.
    """
    def test_is_optional(self):
        e1 = OptionalGrouping("hello")
        self.assertTrue(e1.is_optional)

        e2 = Literal("hello")
        self.assertFalse(e2.is_optional)

        e3 = Sequence(Literal("hello"))
        self.assertFalse(e3.is_optional)

        e4 = Sequence(Literal("hello"), OptionalGrouping("there"))
        self.assertFalse(e4.is_optional)
        self.assertTrue(e4.children[1].is_optional)
        self.assertTrue(e4.children[1].child.is_optional)

        e5 = Sequence(
            "a", OptionalGrouping("b"),
            Sequence("c", OptionalGrouping("d"))
        )

        a = e5.children[0]
        opt1 = e5.children[1]
        b = opt1.child
        seq2 = e5.children[2]
        c = seq2.children[0]
        opt2 = seq2.children[1]
        d = opt2.child
        self.assertFalse(e5.is_optional)
        self.assertFalse(a.is_optional)
        self.assertTrue(opt1.is_optional)
        self.assertTrue(opt2.is_optional)
        self.assertTrue(b.is_optional)
        self.assertTrue(opt2.is_optional)
        self.assertTrue(d.is_optional)
        self.assertFalse(c.is_optional)

    def test_is_alternative(self):
        e1 = AlternativeSet("hello")
        self.assertTrue(e1.is_alternative)

        e2 = Literal("hello")
        self.assertFalse(e2.is_alternative)

        e3 = Sequence(Literal("hello"))
        self.assertFalse(e3.is_alternative)

        e4 = AlternativeSet(Literal("hello"), Literal("hi"), Literal("hey"))
        for child in e4.children:
            self.assertTrue(child.is_alternative)

        e5 = Sequence(e4)
        self.assertFalse(e5.is_alternative)

        e6 = AlternativeSet(Literal("hello"), AlternativeSet("hi there",
                                                             "hello there"),
                            Literal("hey"))
        for leaf in e6.leaves:
            self.assertTrue(leaf.is_alternative)


class MapExpansionCase(unittest.TestCase):
    """
    Test the map_expansion function.
    """
    def setUp(self):
        self.map_to_string = lambda x: "%s" % x
        self.map_to_current_match = lambda x: x.current_match

    def test_base(self):
        e = Literal("hello")
        mapped = map_expansion(e, self.map_to_string)
        self.assertEqual(mapped[0], "%s" % e)

    def test_simple(self):
        e = Sequence("hello", "world")
        mapped = map_expansion(e, self.map_to_string)
        self.assertEqual(mapped, (
            "Sequence(Literal('hello'), Literal('world'))", (
                ("Literal('hello')", ()),
                ("Literal('world')", ())
            )))

    def test_with_matches(self):
        e = Sequence("hello", "world")
        e.matches("hello world")  # assuming matches tests pass
        mapped = map_expansion(e, self.map_to_current_match)
        self.assertEqual(mapped, (
            "hello world", (
                ("hello", ()),
                ("world", ())
            )))


class LeavesProperty(unittest.TestCase):
    """
    Test the leaves property of the Expansion classes.
    """
    def test_base(self):
        e = Literal("hello")
        self.assertListEqual(e.leaves, [Literal("hello")])

    def test_new_leaf_type(self):
        class TestLeaf(Expansion):
            def __init__(self):
                super(TestLeaf, self).__init__([])

        e = TestLeaf()
        self.assertListEqual(e.leaves, [TestLeaf()])

    def test_multiple(self):
        e = Sequence(Literal("hello"), AlternativeSet("there", "friend"))
        self.assertListEqual(e.leaves, [Literal("hello"), Literal("there"),
                                        Literal("friend")],
                             "leaves should be in sequence from left to right.")


if __name__ == '__main__':
    unittest.main()
