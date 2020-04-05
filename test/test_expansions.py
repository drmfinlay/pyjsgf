import unittest
from copy import deepcopy

from six import text_type

from jsgf import *
from jsgf.expansions import ExpansionWithChildren, SingleChildExpansion, \
    VariableChildExpansion, BaseExpansionRef, ChildList
from jsgf.ext import Dictation


class Compilation(unittest.TestCase):
    def test_alt_set(self):
        e1 = AlternativeSet("a")
        e1.tag = "t"
        self.assertEqual(e1.compile(ignore_tags=True), "(a)")
        self.assertEqual(e1.compile(ignore_tags=False), "(a) { t }")

        e2 = AlternativeSet("a b")
        e2.tag = "t"
        self.assertEqual(e2.compile(ignore_tags=True), "(a b)")
        self.assertEqual(e2.compile(ignore_tags=False), "(a b) { t }")

        e3 = AlternativeSet("a", "b")
        e3.children[0].tag = "t1"
        e3.children[1].tag = "t2"
        self.assertEqual(e3.compile(ignore_tags=True), "(a|b)")
        self.assertEqual(e3.compile(ignore_tags=False), "(a { t1 }|b { t2 })")

    def test_kleene_star(self):
        e1 = KleeneStar("a")
        e1.tag = "t"
        self.assertEqual(e1.compile(ignore_tags=True), "(a)*")
        self.assertEqual(e1.compile(ignore_tags=False), "(a)* { t }")

        e2 = KleeneStar("a b")
        e2.tag = "t"
        self.assertEqual(e2.compile(ignore_tags=True), "(a b)*")
        self.assertEqual(e2.compile(ignore_tags=False), "(a b)* { t }")

        e3 = KleeneStar(Sequence("a", "b"))
        e3.tag = "t"
        self.assertEqual(e3.compile(ignore_tags=True), "(a b)*")
        self.assertEqual(e3.compile(ignore_tags=False), "(a b)* { t }")

    def test_literal(self):
        e1 = Literal("a")
        self.assertEqual(e1.compile(ignore_tags=True), "a")

        e2 = Literal("a b")
        self.assertEqual(e2.compile(ignore_tags=True), "a b")

        e3 = Literal("a b")
        e3.tag = "t"
        self.assertEqual(e3.compile(ignore_tags=False), "a b { t }")

    def test_optional_grouping(self):
        e1 = OptionalGrouping("a")
        self.assertEqual(e1.compile(ignore_tags=True), "[a]")

        e2 = OptionalGrouping("a b")
        e2.tag = "t"
        self.assertEqual(e2.compile(ignore_tags=True), "[a b]")
        self.assertEqual(e2.compile(ignore_tags=False), "[a b] { t }")

    def test_required_grouping(self):
        e1 = RequiredGrouping("a")
        e1.tag = "blah"
        self.assertEqual(e1.compile(ignore_tags=True), "(a)")
        self.assertEqual(e1.compile(ignore_tags=False), "(a) { blah }")

        e2 = RequiredGrouping("a b")
        e2.tag = "t"
        self.assertEqual(e2.compile(ignore_tags=True), "(a b)")
        self.assertEqual(e2.compile(ignore_tags=False), "(a b) { t }")

        e3 = RequiredGrouping("a", "b")
        e3.children[0].tag = "t1"
        e3.children[1].tag = "t2"
        self.assertEqual(e3.compile(ignore_tags=True), "(a b)")
        self.assertEqual(e3.compile(ignore_tags=False), "(a { t1 } b { t2 })")

    def test_repeat(self):
        e1 = Repeat("a")
        e1.tag = "t"
        self.assertEqual(e1.compile(ignore_tags=True), "(a)+")
        self.assertEqual(e1.compile(ignore_tags=False), "(a)+ { t }")

        e2 = Repeat("a b")
        e2.tag = "t"
        self.assertEqual(e2.compile(ignore_tags=True), "(a b)+")
        self.assertEqual(e2.compile(ignore_tags=False), "(a b)+ { t }")

        e3 = Repeat(Sequence("a", "b"))
        e3.tag = "t"
        self.assertEqual(e3.compile(ignore_tags=True), "(a b)+")
        self.assertEqual(e3.compile(ignore_tags=False), "(a b)+ { t }")

    def test_rule_ref(self):
        r = PublicRule("test", "a")
        rule_ref = RuleRef(r)
        rule_ref.tag = "ref"
        self.assertEqual(rule_ref.compile(ignore_tags=True), "<test>")
        self.assertEqual(rule_ref.compile(ignore_tags=False), "<test> { ref }")

    def test_sequence(self):
        e1 = Sequence("a")
        self.assertEqual(e1.compile(ignore_tags=True), "a")

        e2 = Sequence("a b")
        e2.tag = "t"
        self.assertEqual(e2.compile(ignore_tags=True), "a b")
        self.assertEqual(e2.compile(ignore_tags=False), "a b { t }")

        e3 = Sequence("a", "b")
        self.assertEqual(e3.compile(ignore_tags=True), "a b")

        e4 = Sequence("a", "b", "c")
        e4.children[1].tag = "t"
        self.assertEqual(e4.compile(ignore_tags=True), "a b c")
        self.assertEqual(e4.compile(ignore_tags=False), "a b { t } c")


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


class ChildListCase(unittest.TestCase):
    """
    Tests for the ChildList class.

    Most test methods in this class do not use ChildList directly because it
    requires an Expansion parameter.
    """
    def setUp(self):
        self.e = Sequence("a", "b", "c")

    def test_setter(self):
        """Expansion classes always use ChildrenLists."""
        e = Sequence()
        self.assertIsInstance(e.children, ChildList)
        e.children = ChildList(e, ["a", "b", "c"])
        self.assertIsInstance(e.children, ChildList)
        self.assertSequenceEqual(e.children, [Literal("a"), Literal("b"), Literal("c")])

        # Check that replacing a ChildList modifies the old list appropriately.
        old_list = e.children
        e.children = ChildList(e, ["x", "y", "z"])
        self.assertIsNone(old_list[0].parent)
        self.assertIsNone(old_list[1].parent)
        self.assertIsNone(old_list[2].parent)

    def test_orphan_children(self):
        """ChildList.orphan_children() sets each child's parent to None."""
        e = self.e
        e.children.orphan_children()
        self.assertIsNone(e.children[0].parent)
        self.assertIsNone(e.children[1].parent)
        self.assertIsNone(e.children[2].parent)

    def test_equal(self):
        """Equivalent lists and ChildLists should be equal."""
        e = self.e
        self.assertSequenceEqual(e.children, [Literal(s) for s in ("a", "b", "c")])
        e = Literal("a")
        self.assertSequenceEqual(e.children, [])

    def test_unequal(self):
        """Different lists and ChildLists should still be unequal."""
        e = self.e
        self.assertNotEqual(e.children, [Literal(s) for s in ("a", "b")])

    def test_string_to_literal(self):
        """Strings added to a ChildList are turned into Literals."""
        # Test append()
        e = Sequence("a")
        e.children.append("b")
        expected = Sequence("a", "b")
        self.assertSequenceEqual(e.children, expected.children)

        # Test insert()
        e = Sequence("a")
        e.children.insert(1, "b")
        self.assertSequenceEqual(e.children, expected.children)

        # Test set item
        e = Sequence("a")
        e.children[0] = "b"
        self.assertSequenceEqual(e.children, Sequence("b").children)

    def test_append(self):
        """Appended children are added and have their parent attributes set."""
        # Test with an expansion and string.
        e = self.e
        e.children.append("d")
        e.children.append(OptionalGrouping("e"))
        expected = Sequence("a", "b", "c", "d", OptionalGrouping("e"))
        self.assertSequenceEqual(e.children, expected.children)
        self.assertEqual(e.children[3].parent, e)
        self.assertEqual(e.children[4].parent, e)

    def test_clear(self):
        """Each child has no parent after clear() is called."""
        e = self.e
        a, b, c = e.children
        e.children.clear()
        self.assertIsNone(a.parent)
        self.assertIsNone(b.parent)
        self.assertIsNone(c.parent)

    def test_extend(self):
        """extend() appends each element in an iterable and sets each parent."""
        e = Sequence("a")
        e.children.extend(["b", OptionalGrouping("c")])
        expected = Sequence("a", "b", OptionalGrouping("c"))
        self.assertSequenceEqual(e.children, expected.children)
        self.assertEqual(e.children[1].parent, e)
        self.assertEqual(e.children[2].parent, e)

    def test_insert(self):
        """Inserted children are added and have their parent attributes set."""
        e = self.e
        e.children.insert(0, "a")
        e.children.insert(4, OptionalGrouping("e"))
        expected = Sequence("a", "a", "b", "c", OptionalGrouping("e"))
        self.assertSequenceEqual(e.children, expected.children)
        self.assertEqual(e.children[0].parent, e)
        self.assertEqual(e.children[4].parent, e)

    def test_pop(self):
        """Expansions removed using pop() have parent set to None."""
        e = self.e
        c = e.children.pop()
        self.assertEqual(c, Literal("c"))
        self.assertIsNone(c.parent)

        # Test with an explicit index.
        a = e.children.pop(0)
        self.assertEqual(a, Literal("a"))
        self.assertIsNone(a.parent)

    def test_remove(self):
        """Expansions removed using remove() have parent set to None."""
        e = self.e
        a = e.children[0]
        e.children.remove(a)
        self.assertIsNone(a.parent)

    def test_set_slice(self):
        """Setting list slices works as expected."""
        e = self.e
        a, b, c = e.children
        expected = Sequence("x", "y", "z")
        e.children[0:3] = "x", "y", "z"
        self.assertSequenceEqual(e.children, expected.children)

        # Check that the old children no longer have e as their parent.
        self.assertIsNone(a.parent)
        self.assertIsNone(b.parent)
        self.assertIsNone(c.parent)

    def test_set_item(self):
        """Setting items changes the parents of new and old expansions."""
        e = self.e
        a = e.children[0]
        expected = Sequence("x", "b", "c")
        e.children[0] = "x"
        self.assertSequenceEqual(e.children, expected.children)

        # Check that the old child no longer has e as its parent.
        self.assertIsNone(a.parent)


class Comparisons(unittest.TestCase):
    def test_literals(self):
        self.assertEqual(Literal("hello"), Literal("hello"))
        self.assertNotEqual(Literal("hey"), Literal("hello"))
        self.assertNotEqual(Literal("hey"), Sequence(Literal("hello")))

        # Check case-sensitive vs case-insensitive literals.
        self.assertEqual(Literal("HELLO", False), Literal("HELLO", False))
        self.assertEqual(Literal("HELLO", True), Literal("HELLO", True))
        self.assertEqual(Literal("hello", False), Literal("HELLO", False))
        self.assertNotEqual(Literal("hello", False), Literal("HELLO", True))
        self.assertNotEqual(Literal("HELLO", False), Literal("HELLO", True))

    def test_alt_sets(self):
        self.assertEqual(AlternativeSet("hello", "hi"),
                         AlternativeSet("hello", "hi"))
        self.assertNotEqual(AlternativeSet("hello", "hi"), AlternativeSet("hello"))
        self.assertNotEqual(AlternativeSet("hello", "hi"), AlternativeSet("hello"))
        self.assertNotEqual(AlternativeSet("hello", "hi"), Literal("hello"))

        # Test that child ordering doesn't matter
        self.assertEqual(AlternativeSet("hello", "hi"),
                         AlternativeSet("hi", "hello"))

        # Test that weights are compared.
        e1 = AlternativeSet("a", "b")
        e1.weights = {e1.children[0]: 1, e1.children[1]: 2}
        e2 = AlternativeSet("a", "b")
        self.assertNotEqual(e1, e2)

        e2.weights = {e2.children[0]: 1, e2.children[1]: 2}
        self.assertEqual(e1, e2)

        e1.set_weight(e1.children[1], 1)
        self.assertNotEqual(e1, e2)

    def test_optional(self):
        self.assertEqual(OptionalGrouping("hello"), OptionalGrouping("hello"))
        self.assertNotEqual(OptionalGrouping("hello"), OptionalGrouping("hey"))
        self.assertNotEqual(OptionalGrouping("hello"), AlternativeSet("hello"))

    def test_required_grouping(self):
        self.assertEqual(RequiredGrouping("hello"), RequiredGrouping("hello"))
        self.assertNotEqual(RequiredGrouping("hello"), RequiredGrouping("hey"))
        self.assertNotEqual(RequiredGrouping("hello"), AlternativeSet("hello"))
        self.assertNotEqual(RequiredGrouping("hello"), AlternativeSet("hello"))

    def test_sequence(self):
        self.assertEqual(Sequence("hello"), Sequence("hello"))
        self.assertNotEqual(Sequence("hello"), Sequence("hey"))
        self.assertNotEqual(Sequence("hello"), AlternativeSet("hello"))
        self.assertNotEqual(Sequence("hello"), Literal("hello"))

    def test_repeat(self):
        self.assertEqual(Repeat("hello"), Repeat("hello"))
        self.assertNotEqual(Repeat("hello"), Repeat("hey"))
        self.assertNotEqual(Repeat("hello"), Literal("hello"))
        self.assertNotEqual(Repeat("hello"), Sequence(Literal("hello")))

    def test_kleene_star(self):
        self.assertEqual(KleeneStar("hello"), KleeneStar("hello"))
        self.assertNotEqual(KleeneStar("hello"), KleeneStar("hey"))
        self.assertNotEqual(KleeneStar("hello"), Literal("hello"))
        self.assertNotEqual(KleeneStar("hello"), Sequence(Literal("hello")))

    def test_rule_ref(self):
        rule1 = Rule("test", True, "test")
        rule2 = Rule("test", True, "testing")
        self.assertEqual(RuleRef(rule1), RuleRef(rule1))
        self.assertEqual(RuleRef(rule1), RuleRef(deepcopy(rule1)))
        self.assertNotEqual(RuleRef(rule1), RuleRef(rule2))

    def test_set_equality(self):
        # Test with only literals
        self.assertSetEqual({Literal("a"), Literal("z"), Literal("b")},
                            {Literal("a"), Literal("b"), Literal("z")})

        # Test with other items
        self.assertSetEqual({"a", Literal("z"), Literal("a"), "b"},
                            {"a", "b", Literal("a"), Literal("z")})

        # Test with child expansions
        self.assertSetEqual(
            {Sequence("a", "b"), Literal("c"), OptionalGrouping("d")},
            {Literal("c"), Sequence("a", "b"), OptionalGrouping("d")})
        self.assertSetEqual({AlternativeSet("a", "b")}, {AlternativeSet("b", "a")})


class Hashing(unittest.TestCase):
    def test_alt_set(self):
        # Test that ordering doesn't matter for hashing.
        self.assertEqual(hash(AlternativeSet("hello", "hi")),
                         hash(AlternativeSet("hi", "hello")))

        # Test more complex expansions
        self.assertEqual(hash(Sequence(AlternativeSet("a", "b"), "c")),
                         hash(Sequence(AlternativeSet("b", "a"), "c")))
        self.assertEqual(hash(Sequence(AlternativeSet("a", Dictation(), "b"), "c")),
                         hash(Sequence(AlternativeSet("b", "a", Dictation()), "c")))

        # Test that different sets produce different hashes
        self.assertNotEqual(hash(AlternativeSet("a", "b")),
                            hash(AlternativeSet("a", "b", "c")))

        # Test weights.
        e1 = AlternativeSet("hello", "hi")
        e1.weights = {"hello": 1, "hi": 2}
        self.assertNotEqual(hash(e1), hash(AlternativeSet("hi", "hello")))
        e2 = AlternativeSet("hello", "hi")
        e2.weights = {"hello": 2, "hi": 3}
        self.assertNotEqual(hash(e1), hash(e2))
        e2.weights = {"hi": 2, "hello": 1}
        self.assertEqual(hash(e1), hash(e2))

    def test_hashable(self):
        # Test that all expansion types are hashable
        def assert_hashable(x):
            # Check that a copy of x generates the same hash value.
            # hash(x) will raise a TypeError if x cannot be hashed, making the test
            # fail.
            self.assertEqual(hash(x), hash(x.copy()))

        # Test single child types
        for T in [SingleChildExpansion, OptionalGrouping, Repeat, KleeneStar]:
            assert_hashable(T("a"))

        # Test variable child types
        for T in [VariableChildExpansion, AlternativeSet, Sequence,
                  RequiredGrouping]:
            assert_hashable(T("a", "b", "c"))

        # Test childless types
        for T in [VoidRef, NullRef, Dictation]:
            assert_hashable(T())

        # Test special classes
        assert_hashable(Expansion([]))
        assert_hashable(ExpansionWithChildren(["a"]))
        assert_hashable(Literal("abc"))
        assert_hashable(BaseExpansionRef("name"))
        assert_hashable(NamedRuleRef("name"))
        assert_hashable(RuleRef(Rule("test", False, "abc")))

    def test_sequence(self):
        # Test that the same sequences produce the same hashes
        self.assertEqual(hash(Sequence("a", "b")),
                         hash(Sequence("a", "b")))

        # Test that ordering does matter for hashing sequences.
        self.assertNotEqual(hash(Sequence("a", "b")),
                            hash(Sequence("b", "a")))

        # Test more complex expansions
        self.assertNotEqual(
            hash(AlternativeSet(Sequence("a", "b"), "c")),
            hash(AlternativeSet(Sequence("b", "a"), "c")))
        self.assertEqual(
            hash(AlternativeSet(Sequence("a", "b"), "c")),
            hash(AlternativeSet("c", Sequence("a", "b"))))

    def test_rule_ref(self):
        self.assertEqual(RuleRef(Rule("test", True, "test")),
                         RuleRef(Rule("test", True, "test")))
        self.assertNotEqual(RuleRef(Rule("test", False, "test")),
                            RuleRef(Rule("test", True, "test")))
        self.assertNotEqual(RuleRef(Rule("test", True, "testing")),
                            RuleRef(Rule("test", True, "test")))
        self.assertNotEqual(RuleRef(Rule("testing", True, "test")),
                            RuleRef(Rule("test", True, "test")))


class Copying(unittest.TestCase):
    def assert_copy_works(self, e):
        """Copy an expansion e and do some checks."""
        # Try first with deepcopy (default)
        e2 = e.copy()
        self.assertIsNot(e, e2)
        self.assertEqual(e, e2)

        # Then with shallow copying
        e3 = e.copy(shallow=True)
        self.assertIsNot(e, e3)
        self.assertEqual(e, e3)

        for c1, c2 in zip(e.children, e3.children):
            # Children of e and e3 should all be the same objects
            self.assertIs(c1, c2)

    def test_base(self):
        self.assert_copy_works(Expansion([]))
        self.assert_copy_works(Expansion(["a"]))

    def test_named_references(self):
        self.assert_copy_works(NamedRuleRef("test"))
        self.assert_copy_works(NullRef())
        self.assert_copy_works(VoidRef())

    def test_literals(self):
        self.assert_copy_works(Literal("test"))
        self.assert_copy_works(Dictation())

    def test_sequences(self):
        self.assert_copy_works(Sequence("test", "testing"))
        self.assert_copy_works(RequiredGrouping("test", "testing"))

    def test_alt_set(self):
        # Test with and without weights.
        self.assert_copy_works(AlternativeSet("test", "testing"))
        e = AlternativeSet("test", "testing")
        e.weights = {"test": 2, "testing": 4}
        self.assert_copy_works(e)

    def test_rule_ref(self):
        r1 = PublicRule("r1", "test")
        ref = RuleRef(r1)
        self.assert_copy_works(ref)

        # Check that a copy of a RuleRef references r1, not a copy of it.
        self.assertIs(ref.referenced_rule, ref.copy().referenced_rule)

        # Check that the same is true for a deep copied rule referencing r1
        self.assertIs(deepcopy(PublicRule("r2", ref)).expansion.referenced_rule, r1)

    def test_repeat(self):
        self.assert_copy_works(Repeat("testing"))
        self.assert_copy_works(KleeneStar("testing"))


class LiteralProperties(unittest.TestCase):
    """
    Tests for the Literal class properties.
    """
    def test_set_text(self):
        e = Literal("a")
        e.text = "b"
        self.assertEqual(e.text, "b")

    def test_text_casing(self):
        """Literal.text property can return lowered or unchanged strings."""
        e = Literal("A")
        self.assertEqual(e.text, "a")
        e.case_sensitive = True
        self.assertEqual(e.text, "A")
        e.text = "a"
        self.assertEqual(e.text, "a")

    def test_set_text_valid_type(self):
        """Literal.text accepts string types."""
        l = Literal("")
        l.text = text_type("a")
        self.assertEqual(l.text, "a")
        l.text = str("b")
        self.assertEqual(l.text, "b")

    def test_set_text_invalid_types(self):
        l = Literal("")

        # Make a local function for testing assignments.
        def test_assignment(x):
            l.text = x

        self.assertRaises(TypeError, test_assignment, object())
        self.assertRaises(TypeError, test_assignment, 1)
        self.assertRaises(TypeError, test_assignment, None)


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

    def test_is_descendant_of(self):
        e1 = Sequence("hello")
        self.assertTrue(e1.children[0].is_descendant_of(e1))
        self.assertFalse(e1.is_descendant_of(e1))
        self.assertFalse(e1.is_descendant_of(e1.children[0]))

        r = Rule("n", False, AlternativeSet("one", "two", "three"))
        e2 = RuleRef(r)
        self.assertFalse(e2.is_descendant_of(e2))

        # Expansions part of the 'n' rule are descendants of e2
        def assert_descendant(x):
            self.assertTrue(x.is_descendant_of(e2))

        map_expansion(r.expansion, assert_descendant)


class LiteralRepetitionAncestor(unittest.TestCase):
    def setUp(self):
        self.seq = Sequence("hello", "world")

    def test_no_repetition(self):
        self.assertIsNone(Literal("hello").repetition_ancestor)
        self.assertFalse(self.seq.children[0].repetition_ancestor)
        self.assertFalse(self.seq.children[1].repetition_ancestor)

    def test_with_repeat(self):
        rep1 = Repeat("hello")
        rep2 = Repeat(self.seq)
        self.assertEqual(rep1.child.repetition_ancestor, rep1)
        self.assertEqual(rep2.child.children[0].repetition_ancestor, rep2)

    def test_with_kleene_star(self):
        k1 = KleeneStar("hello")
        k2 = KleeneStar(self.seq)
        self.assertEqual(k1.child.repetition_ancestor, k1)
        self.assertEqual(k2.child.children[1].repetition_ancestor, k2)


class MutuallyExclusiveOfCase(unittest.TestCase):
    def test_no_alternative_sets(self):
        e1 = Literal("hi")
        e2 = Literal("hello")
        self.assertFalse(e1.mutually_exclusive_of(e2))

    def test_one_alternative_set(self):
        e1 = AlternativeSet("hi", "hello")
        self.assertTrue(e1.children[0].mutually_exclusive_of(e1.children[1]))

        e2 = AlternativeSet(Sequence("hi", "there"), "hello")
        self.assertTrue(e2.children[0]
                        .mutually_exclusive_of(e2.children[1]))
        self.assertTrue(e2.children[0].children[0]
                        .mutually_exclusive_of(e2.children[1]))
        self.assertTrue(e2.children[0].children[1]
                        .mutually_exclusive_of(e2.children[1]))

    def test_two_alternative_sets(self):
        e1 = Sequence(AlternativeSet(Sequence("a", "b"), "c"),
                      AlternativeSet("d", "e"))
        as1, as2 = e1.children[0], e1.children[1]
        seq2 = as1.children[0]
        a, b, c = seq2.children[0], seq2.children[1], as1.children[1]
        d, e = as2.children[0], as2.children[1]

        self.assertFalse(as1.mutually_exclusive_of(as2))
        self.assertTrue(a.mutually_exclusive_of(c))
        self.assertTrue(b.mutually_exclusive_of(c))
        self.assertFalse(a.mutually_exclusive_of(b))

        self.assertEqual(d.mutually_exclusive_of(e), e.mutually_exclusive_of(d),
                         "mutual_exclusive_of should be a commutative operation "
                         "(order does not matter)")
        self.assertTrue(d.mutually_exclusive_of(e))
        self.assertFalse(a.mutually_exclusive_of(d))
        self.assertFalse(a.mutually_exclusive_of(e))


class ExpansionTreeConstructs(unittest.TestCase):
    """
    Tests for functions and classes that operate on expansion trees, such as
    map_expansion, flat_map_expansion, filter_expansion and JointTreeContext.
    """
    def setUp(self):
        self.map_to_string = lambda x: "%s" % x
        self.map_to_current_match = lambda x: x.current_match
        self.find_letter = lambda x, l: hasattr(x, "text") and x.text == l
        self.find_a = lambda x: self.find_letter(x, "a")
        self.find_b = lambda x: self.find_letter(x, "b")
        self.find_seq = lambda x: isinstance(x, Sequence)

    def test_default_arguments(self):
        e = Sequence("hello")
        self.assertEqual(map_expansion(e), (
            e, ((Literal("hello"), ()),)
        ))
        self.assertEqual(flat_map_expansion(e), [e, Literal("hello")])
        self.assertEqual(filter_expansion(e), [e, Literal("hello")])

    def test_base_map(self):
        e = Literal("hello")
        mapped1 = map_expansion(e, self.map_to_string, TraversalOrder.PreOrder)
        self.assertEqual(mapped1[0], "%s" % e)

        mapped2 = map_expansion(e, self.map_to_string, TraversalOrder.PostOrder)
        self.assertEqual(mapped2[1], "%s" % e)

    def test_simple_map(self):
        e = Sequence("hello", "world")
        mapped1 = map_expansion(e, self.map_to_string, TraversalOrder.PreOrder)
        self.assertEqual(mapped1, (
            "Sequence(Literal('hello'), Literal('world'))", (
                ("Literal('hello')", ()),
                ("Literal('world')", ())
            )))

        mapped2 = map_expansion(e, self.map_to_string, TraversalOrder.PostOrder)
        self.assertEqual(mapped2, (
            (((), "Literal('hello')"), ((), "Literal('world')")),
            "Sequence(Literal('hello'), Literal('world'))"
        ))

    def test_using_rule_ref(self):
        """
        Test map_expansion using a RuleRef.
        """
        r = PrivateRule("name", AlternativeSet("alice", "bob"))
        e = RuleRef(r)
        self.assertEqual(map_expansion(e), (
            RuleRef(r), (
                (AlternativeSet("alice", "bob"), (
                    (Literal("alice"), ()),
                    (Literal("bob"), ())
                ))
            )
        ))

    def test_using_named_rule_ref(self):
        """
        Test map_expansion using a NamedRuleRef.
        """
        # NamedRuleRefs require rules to be in grammars for mapping to work.
        r1 = PrivateRule("name", AlternativeSet("alice", "bob"))
        r2 = PublicRule("test", NamedRuleRef("name"))
        g = Grammar()
        g.add_rules(r1, r2)
        self.assertEqual(map_expansion(r2.expansion), (
            r2.expansion, (
                (AlternativeSet("alice", "bob"), (
                    (Literal("alice"), ()),
                    (Literal("bob"), ())
                ))
            )
        ))

    def test_map_with_matches(self):
        e = Sequence("hello", "world")
        e.matches("hello world")  # assuming matches tests pass
        mapped = map_expansion(e, self.map_to_current_match)
        self.assertEqual(mapped, (
            "hello world", (
                ("hello", ()),
                ("world", ())
            )))

    def test_filter_base(self):
        e = Literal("hello")
        self.assertEqual(
            filter_expansion(e, lambda x: x.text == "hello",
                             TraversalOrder.PreOrder),
            [Literal("hello")])

        self.assertEqual(
            filter_expansion(e, lambda x: x.text == "hello",
                             TraversalOrder.PostOrder),
            [Literal("hello")])

    def test_filter_simple(self):
        e = Sequence("a", "b", "c")
        literals = e.children
        self.assertEqual(
            filter_expansion(e, lambda x: isinstance(x, Literal),
                             TraversalOrder.PreOrder),
            literals)

        self.assertEqual(
            filter_expansion(e, lambda x: isinstance(x, Literal),
                             TraversalOrder.PostOrder),
            literals)

    def test_filter_with_matches(self):
        e1 = Sequence("a", "b", "c")
        a, b, c = e1.children
        e1.matches("a b c")
        self.assertEqual(
            filter_expansion(e1, lambda x: x.current_match is not None,
                             TraversalOrder.PreOrder),
            [e1, a, b, c])

        self.assertEqual(
            filter_expansion(e1, lambda x: x.current_match is not None,
                             TraversalOrder.PostOrder),
            [a, b, c, e1])

        e2 = Sequence("d", OptionalGrouping("e"), "f")
        d, opt, f = e2.children
        e = opt.child
        e2.matches("d f")
        self.assertEqual(
            filter_expansion(e2, lambda x: x.current_match is not None,
                             TraversalOrder.PreOrder),
            [e2, d, opt, e, f])

        self.assertEqual(
            filter_expansion(e2, lambda x: x.current_match is not None,
                             TraversalOrder.PostOrder),
            [d, e, opt, f, e2])

    def test_flat_map_base(self):
        e = Literal("hello")
        self.assertEqual(
            flat_map_expansion(e, order=TraversalOrder.PreOrder),
            [e])

        self.assertEqual(
            flat_map_expansion(e, order=TraversalOrder.PostOrder),
            [e])

    def test_flat_map_simple(self):
        e = Sequence("a", AlternativeSet("b", "c"), "d")
        a, alt_set, d = e.children
        b, c = alt_set.children
        self.assertEqual(
            flat_map_expansion(e, order=TraversalOrder.PreOrder),
            [e, a, alt_set, b, c, d])

        self.assertEqual(
            flat_map_expansion(e, order=TraversalOrder.PostOrder),
            [a, b, c, alt_set, d, e])

    def test_joint_tree_context(self):
        """JointTreeContext joins and detaches trees correctly"""
        r1 = PublicRule("r1", "hi")
        ref = RuleRef(r1)
        e = AlternativeSet(ref, "hello")
        self.assertIsNone(r1.expansion.parent)
        self.assertFalse(r1.expansion.mutually_exclusive_of(e.children[1]),
                         "'hi' shouldn't be mutually exclusive of 'hello' "
                         "alternative yet")
        with JointTreeContext(e):
            self.assertEqual(r1.expansion.parent, ref,
                             "parent of r1.expansion changes to ref")
            self.assertTrue(r1.expansion.mutually_exclusive_of(e.children[1]),
                            "'hi' should be mutually exclusive of 'hello' within a "
                            "JointTreeContext")
        self.assertIsNone(r1.expansion.parent)
        self.assertFalse(r1.expansion.mutually_exclusive_of(e.children[1]))

    def test_find_expansion(self):
        e = Sequence("a", "a", "b")
        self.assertIs(find_expansion(e, self.find_a, TraversalOrder.PreOrder),
                      e.children[0])
        self.assertIs(find_expansion(e, self.find_a, TraversalOrder.PostOrder),
                      e.children[0])
        self.assertIs(find_expansion(e, self.find_b, TraversalOrder.PreOrder),
                      e.children[2])
        self.assertIs(find_expansion(e, self.find_b, TraversalOrder.PostOrder),
                      e.children[2])

    def test_find_expansion_rule_ref(self):
        """find_expansion correctly traverses through referenced rules"""
        r = Rule("n", False, AlternativeSet("a", "b", "c"))
        e1 = RuleRef(r)
        e2 = OptionalGrouping(RuleRef(r))
        self.assertIs(find_expansion(e1, self.find_a, TraversalOrder.PreOrder),
                      r.expansion.children[0])
        self.assertIs(find_expansion(e1, self.find_a, TraversalOrder.PreOrder),
                      r.expansion.children[0])
        self.assertIs(find_expansion(e2, self.find_b, TraversalOrder.PreOrder),
                      r.expansion.children[1])
        self.assertIs(find_expansion(e2, self.find_b, TraversalOrder.PreOrder),
                      r.expansion.children[1])

    def test_find_expansion_order(self):
        inner_seq = Sequence("a", "b")
        e = Sequence(AlternativeSet(inner_seq, "c"))
        self.assertIs(find_expansion(e, self.find_seq, TraversalOrder.PreOrder), e)
        self.assertIs(find_expansion(e, self.find_seq, TraversalOrder.PostOrder),
                      inner_seq)

    def test_find_expansion_optimisation(self):
        """find_expansion only searches until a match is found"""
        visited = []
        e = Sequence("a", "a", "b")

        def find_a(x):
            visited.append(x)
            return self.find_a(x)

        self.assertIs(find_expansion(e, find_a, TraversalOrder.PreOrder),
                      e.children[0])
        self.assertSequenceEqual(visited, [e, e.children[0]])

        # Reset the visited list and test with a post order traversal
        visited = []
        self.assertIs(find_expansion(e, find_a, TraversalOrder.PostOrder),
                      e.children[0])
        self.assertSequenceEqual(visited, [e.children[0]])

        # Test again finding 'b' instead
        visited = []

        def find_b(x):
            visited.append(x)
            return self.find_b(x)

        self.assertIs(find_expansion(e, find_b, TraversalOrder.PreOrder),
                      e.children[2])
        self.assertSequenceEqual(visited, [e] + list(e.children))

        # Reset the visited list and test with a post order traversal
        visited = []
        self.assertIs(find_expansion(e, find_b, TraversalOrder.PostOrder),
                      e.children[2])
        self.assertSequenceEqual(visited, e.children)


class LeafProperties(unittest.TestCase):
    """
    Test the leaf properties and methods of the Expansion classes.
    """
    def test_leaves_base(self):
        e = Literal("hello")
        self.assertSequenceEqual(e.leaves, [Literal("hello")])

    def test_new_leaf_type(self):
        # Make a new Expansion that has no children.
        class TestLeaf(Expansion):
            def __init__(self):
                super(TestLeaf, self).__init__([])

        e = TestLeaf()
        self.assertSequenceEqual(e.leaves, [TestLeaf()])

    def test_leaves_multiple(self):
        e = Sequence(Literal("hello"), AlternativeSet("there", "friend"))
        self.assertSequenceEqual(e.leaves, [Literal("hello"), Literal("there"),
                                        Literal("friend")],
                             "leaves should be in sequence from left to right.")

    def test_leaves_with_rule_ref(self):
        r = PublicRule("test", Literal("hi"))
        e = RuleRef(r)
        self.assertSequenceEqual(e.leaves, [e, Literal("hi")])

    def test_leaves_after_base(self):
        e = Literal("a")
        self.assertSequenceEqual(list(e.leaves_after), [])

    def test_leaves_after_multiple(self):
        e = Sequence("a", "b")
        self.assertSequenceEqual(list(e.children[0].leaves_after), [e.children[1]])
        self.assertSequenceEqual(list(e.children[1].leaves_after), [])

    def test_leaves_after_complex(self):
        x = Sequence(
            AlternativeSet(Sequence("a", "b"), Sequence("c", "d")),
            "e", OptionalGrouping("f")
        )
        a = x.children[0].children[0].children[0]
        b = x.children[0].children[0].children[1]
        c = x.children[0].children[1].children[0]
        d = x.children[0].children[1].children[1]
        e = x.children[1]
        f = x.children[2].child

        self.assertSequenceEqual(list(a.leaves_after), [b, c, d, e, f])
        self.assertSequenceEqual(list(b.leaves_after), [c, d, e, f])
        self.assertSequenceEqual(list(c.leaves_after), [d, e, f])
        self.assertSequenceEqual(list(d.leaves_after), [e, f])
        self.assertSequenceEqual(list(e.leaves_after), [f])
        self.assertSequenceEqual(list(f.leaves_after), [])

    def test_collect_leaves(self):
        n = Rule("n", False, AlternativeSet("one", "two", "three"))
        e = Sequence("test", RuleRef(n))

        # Test with default parameters
        self.assertSequenceEqual(
            e.collect_leaves(order=TraversalOrder.PreOrder, shallow=False),
            #    test         RuleRef(n)       one, two, three
            [e.children[0], e.children[1]] + list(n.expansion.children)
        )

        # Test with PostOrder traversal
        self.assertSequenceEqual(
            e.collect_leaves(order=TraversalOrder.PostOrder, shallow=False),
            #     test          one, two, three        RuleRef(n)
            [e.children[0]] + list(n.expansion.children) + [e.children[1]]
        )

        # Test with shallow=True (order is irrelevant in this case)
        self.assertSequenceEqual(
            e.collect_leaves(shallow=True),
            #     test        RuleRef(n)
            [e.children[0], e.children[1]]
        )


class RootExpansionProperty(unittest.TestCase):
    def test_base(self):
        e = Literal("hello")
        self.assertEqual(e.root_expansion, e)

    def test_multiple(self):
        e = Sequence(Literal("hello"), AlternativeSet("there", "friend"))
        hello = e.children[0]
        alt_set = e.children[1]
        there = e.children[1].children[0]
        friend = e.children[1].children[1]
        self.assertEqual(e.root_expansion, e)
        self.assertEqual(alt_set.root_expansion, e)
        self.assertEqual(hello.root_expansion, e)
        self.assertEqual(there.root_expansion, e)
        self.assertEqual(friend.root_expansion, e)


class AlternativeWeightTests(unittest.TestCase):
    def test_set_weight(self):
        a, b, c = map(Literal, ["a", "b", "c"])
        e = AlternativeSet(a, b, c)

        # Test that errors are raised for invalid weights.
        self.assertRaises(TypeError, e.set_weight, a, -1)
        self.assertRaises(TypeError, e.set_weight, a, None)
        self.assertRaises(ValueError, e.set_weight, a, "")
        self.assertRaises(ValueError, e.set_weight, a, "x")

        # Set the weight for "a" and test that errors are raised because "b"
        # and "c" don't have weights. The rule is that all weights or no
        # weights must be set.
        e.set_weight(a, 1)
        self.assertRaises(GrammarError, e.compile)
        self.assertRaises(GrammarError, e.matches, "a")

        # Test again with "b".
        e.set_weight(b, 5.5)
        self.assertRaises(GrammarError, e.compile)
        self.assertRaises(GrammarError, e.matches, "b")

        # Set the weight for "c" and check again.
        e.set_weight(c, 10)
        self.assertEqual(e.compile(), "(/1.0000/ a|/5.5000/ b|/10.0000/ c)")
        for s in ["a", "b", "c"]:
            self.assertEqual(e.matches(s), "")

        # Check that the weights property returns the expected dictionary.
        self.assertDictEqual(e.weights, {a: 1, b: 5.5, c: 10})

        # Check that strings can be used for weight values.
        e.set_weight(a, "2")
        self.assertDictEqual(e.weights, {a: 2, b: 5.5, c: 10})

    def test_weights(self):
        # Test the weights property.
        a, b, c = map(Literal, ["a", "b", "c"])
        e = AlternativeSet(a, b, c)

        # weights should be an empty dictionary at first.
        self.assertDictEqual(e.weights, {})

        # Set each weight and test again.
        e.weights = {a: 0, b: 1, c: 2.5}
        self.assertDictEqual(e.weights, {a: 0, b: 1, c: 2.5})

        # Check that strings can be used for weight values.
        e.weights.update({a: "2"})
        self.assertEqual(e.compile(), "(/2.0000/ a|/1.0000/ b|/2.5000/ c)")


if __name__ == '__main__':
    unittest.main()
