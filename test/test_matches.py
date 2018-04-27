import unittest

from jsgf import *
from jsgf.expansions import matches_overlap


class MatchesOverlap(unittest.TestCase):
    def setUp(self):
        self.p1 = Literal("hey").matching_regex_pattern
        self.p2 = Literal("hello").matching_regex_pattern
        self.p3 = Literal("hello world").matching_regex_pattern

    def test_no_overlap(self):
        m1 = self.p1.match("hey")
        m2 = self.p2.match("hey")
        self.assertFalse(matches_overlap(m1, m2))

        m1 = self.p1.match("hello")
        m2 = self.p2.match("hello")
        self.assertFalse(matches_overlap(m1, m2))

        m1 = self.p1.match("hey hello")
        m2 = self.p2.match("hey hello")
        self.assertFalse(matches_overlap(m1, m2))

    def test_commutative(self):
        m1 = self.p1.match("hey")
        m2 = self.p2.match("hey")
        msg = "matches_overlap should be commutative (order does not matter)"
        self.assertFalse(matches_overlap(m1, m2))
        self.assertEqual(matches_overlap(m1, m2), matches_overlap(m2, m1), msg)

        m1 = self.p1.match("hey hello")
        m2 = self.p2.match("hey hello")
        self.assertFalse(matches_overlap(m1, m2))
        self.assertEqual(matches_overlap(m1, m2), matches_overlap(m2, m1), msg)

        m1 = self.p2.match("hello world")
        m2 = self.p3.match("hello world")
        self.assertTrue(matches_overlap(m1, m2))
        self.assertEqual(matches_overlap(m1, m2), matches_overlap(m2, m1), msg)

    def test_same_match(self):
        p1 = Literal("hello").matching_regex_pattern
        m1 = p1.match("hello")
        self.assertTrue(matches_overlap(m1, m1))
        self.assertFalse(matches_overlap(None, None))

    def test_overlap(self):
        p1 = Literal("hello").matching_regex_pattern
        p2 = Literal("hello world").matching_regex_pattern

        m1 = p1.match("hello world")
        m2 = p2.match("hello world")
        self.assertTrue(matches_overlap(m1, m2))
        self.assertTrue(matches_overlap(m2, m1))


class CurrentMatchCase(unittest.TestCase):
    def test_current_match_correction(self):
        """
        Test whether current_match gets set to None if the expansion isn't optional
        and "" if it is.
        """
        e1 = Literal("hello")
        e1.current_match = ""
        self.assertEqual(e1.current_match, None)
        e1.current_match = None
        self.assertEqual(e1.current_match, None)
        e1.current_match = "hello"
        self.assertEqual(e1.current_match, "hello")

        e2 = KleeneStar("hello")
        e2.current_match = None
        self.assertEqual(e2.current_match, "")
        e2.current_match = ""
        self.assertEqual(e2.current_match, "")
        e1.current_match = "hello hello"
        self.assertEqual(e1.current_match, "hello hello")

    def test_literal(self):
        e = Literal("hello")
        r = PublicRule("test", e)
        self.assertTrue(r.matches("hello"))
        self.assertEqual(e.current_match, "hello")

    def test_literal_no_match(self):
        e = Literal("hello world")
        r = PublicRule("test", e)
        self.assertFalse(r.matches("hello"))
        self.assertEqual(e.current_match, None)

    def test_sequence(self):
        e = Sequence("hello", "world")
        r = PublicRule("test", e)
        self.assertTrue(r.matches("hello world"))
        self.assertEqual(e.children[0].current_match, "hello")
        self.assertEqual(e.children[1].current_match, "world")

    def test_sequence_no_match(self):
        e = Sequence("hello", "world")
        r = PublicRule("test", e)
        self.assertFalse(r.matches("hello"))
        self.assertEqual(e.children[0].current_match, None,
                         "current_match should be None if the whole rule didn't "
                         "match")
        self.assertEqual(e.children[1].current_match, None)

    def test_alt_set_simple(self):
        e = AlternativeSet("hello", "hi")
        r = PublicRule("test", e)
        self.assertTrue(r.matches("hello"))
        self.assertEqual(e.current_match, "hello")
        self.assertEqual(e.children[0].current_match, "hello")
        self.assertEqual(e.children[1].current_match, None)

        self.assertTrue(r.matches("hi"))
        self.assertEqual(e.current_match, "hi")
        self.assertEqual(e.children[1].current_match, "hi")
        self.assertEqual(e.children[0].current_match, None)

        self.assertFalse(r.matches("hey"))
        map_expansion(e, lambda x: self.assertIsNone(x.current_match))

    def test_alt_set_complex(self):
        e = Sequence(
            AlternativeSet("hello", "hi"),
            AlternativeSet("there", "my friend"))
        r = PublicRule("test", e)
        self.assertFalse(r.matches("hey"))
        self.assertEqual(e.current_match, None)
        self.assertEqual(e.children[0].current_match, None)
        self.assertEqual(e.children[1].current_match, None)

        self.assertTrue(r.matches("hi there"))
        self.assertEqual(e.current_match, "hi there")
        self.assertEqual(e.children[0].current_match, "hi")
        self.assertEqual(e.children[0].children[0].current_match, None)
        self.assertEqual(e.children[0].children[1].current_match, "hi")
        self.assertEqual(e.children[1].current_match, "there")
        self.assertEqual(e.children[1].children[0].current_match, "there")
        self.assertEqual(e.children[1].children[1].current_match, None)

        # If a speech string doesn't match, then no match values should be set.
        self.assertFalse(r.matches("hi"))
        map_expansion(e, lambda x: self.assertIsNone(x.current_match))

    def test_skip_mutually_exclusive(self):
        """
        Test whether literals that are mutually exclusive get skipped in the
        matching process.
        """
        e1 = AlternativeSet(Sequence("a", "b", OptionalGrouping("c")),
                            Sequence("a", "b"))
        r1 = PublicRule("test", e1)
        seq1, seq2 = e1.children[0], e1.children[1]
        a1, b1 = seq1.children[0], seq1.children[1]
        c = seq1.children[2]
        a2, b2 = seq2.children[0], seq2.children[1]

        self.assertTrue(r1.matches("a b"))
        self.assertEqual(a2.current_match, None)
        self.assertEqual(a1.current_match, "a")
        self.assertEqual(b2.current_match, None)
        self.assertEqual(b1.current_match, "b")

        self.assertFalse(r1.matches("a b a b"))
        self.assertFalse(r1.matches("a b a b c"))

        self.assertTrue(r1.matches("a b c"))
        self.assertEqual(a1.current_match, "a")
        self.assertEqual(a2.current_match, None)
        self.assertEqual(b1.current_match, "b")
        self.assertEqual(b2.current_match, None)
        self.assertEqual(c.current_match, "c")

    def test_rule_ref(self):
        e1 = AlternativeSet("bob", "leo")
        person = HiddenRule("person", e1)
        e2 = Sequence("hi", RuleRef(person))
        r = PublicRule("test", e2)
        self.assertTrue(r.matches("hi leo"))
        self.assertEqual(e2.current_match, "hi leo")
        self.assertEqual(e2.children[0].current_match, "hi")

        self.assertEqual(e2.children[1].current_match,
                         person.expansion.current_match,
                         "RuleRef should have the same current_match value as the "
                         "rule it references")
        self.assertEqual(e1.current_match, "leo")
        self.assertEqual(e1.children[0].current_match, None)
        self.assertEqual(e1.children[1].current_match, "leo")

        self.assertTrue(r.matches("hi bob"))
        self.assertEqual(e2.current_match, "hi bob")
        self.assertEqual(e2.children[0].current_match, "hi")
        self.assertEqual(e2.children[1].current_match, "bob")
        self.assertEqual(e1.current_match, "bob")

        # Test with a partial match. No match values should be set.
        # This will also test e1's expansions.
        self.assertFalse(r.matches("hi there"))
        map_expansion(e2, lambda x: self.assertIsNone(x.current_match))

    def test_multiple_rule_refs(self):
        numbers = ["one", "two", "three", "four"]
        r1 = Rule("numbers", False, AlternativeSet(*numbers))
        r2 = PublicRule("commands", AlternativeSet(
            Sequence("backspace", RuleRef(r1)),
            Sequence("delete", OptionalGrouping(RuleRef(r1)))
        ))

        # Check that r3 matches delete without a number
        self.assertTrue(r2.matches("delete"))

        for n in numbers:
            self.assertTrue(r1.matches(n))
            self.assertTrue(r2.matches("backspace %s" % n),
                            "matching 'backspace %s' failed" % n)
            self.assertTrue(r2.matches("delete %s" % n),
                            "matching 'delete %s' failed" % n)

    def test_rule_ref_ambiguous(self):
        e1 = Literal("hello")
        r1 = HiddenRule("test1", e1)
        e2 = Sequence(
            OptionalGrouping(RuleRef(r1)), "hello")
        r2 = PublicRule("test2", e2)

        self.assertTrue(r2.matches("hello"))
        self.assertEqual(e2.current_match, "hello")
        self.assertEqual(e2.children[0].current_match, "")
        self.assertEqual(e2.children[1].current_match, "hello")
        self.assertEqual(e1.current_match, "")

        self.assertFalse(r2.matches("hello hello hello"))
        self.assertEqual(e2.current_match, None)
        self.assertEqual(e2.children[0].current_match, "hello")
        self.assertEqual(e1.current_match, "hello")
        self.assertEqual(e2.children[1].current_match, "hello")

    def test_optional_simple(self):
        e = Sequence("hello", OptionalGrouping("there"))
        r = PublicRule("test", e)
        self.assertTrue(r.matches("hello"))
        self.assertEqual(e.current_match, "hello")
        self.assertEqual(e.children[0].current_match, "hello")
        self.assertEqual(e.children[1].current_match, "")

        self.assertFalse(r.matches("there"))
        self.assertEqual(e.current_match, None)
        self.assertEqual(e.children[0].current_match, None)
        self.assertEqual(e.children[1].current_match, '')

    def test_optional_complex(self):
        root = Sequence(
            "a", OptionalGrouping("b"),
            Sequence("c", OptionalGrouping("d"))
        )
        a = root.children[0]
        opt1 = root.children[1]
        b = opt1.child
        seq2 = root.children[2]
        c = seq2.children[0]
        opt2 = seq2.children[1]
        d = opt2.child

        r = PublicRule("test", root)

        self.assertTrue(r.matches("a b c d"))
        self.assertEqual(root.current_match, "a b c d")
        self.assertEqual(a.current_match, "a")
        self.assertEqual(opt1.current_match, "b")
        self.assertEqual(b.current_match, "b")
        self.assertEqual(seq2.current_match, "c d")
        self.assertEqual(c.current_match, "c")
        self.assertEqual(opt2.current_match, "d")
        self.assertEqual(d.current_match, "d")

        self.assertTrue(r.matches("a c d"))
        self.assertEqual(root.current_match, "a c d")
        self.assertEqual(a.current_match, "a")
        self.assertEqual(opt1.current_match, "")
        self.assertEqual(b.current_match, "")
        self.assertEqual(seq2.current_match, "c d")
        self.assertEqual(c.current_match, "c")
        self.assertEqual(opt2.current_match, "d")
        self.assertEqual(d.current_match, "d")

        self.assertTrue(r.matches("a c"))
        self.assertEqual(root.current_match, "a c")
        self.assertEqual(a.current_match, "a")
        self.assertEqual(opt1.current_match, "")
        self.assertEqual(b.current_match, "")
        self.assertEqual(seq2.current_match, "c")
        self.assertEqual(c.current_match, "c")
        self.assertEqual(opt2.current_match, "")
        self.assertEqual(d.current_match, "")

    def test_optional_ambiguous(self):
        e1 = Sequence("a", OptionalGrouping("a"))
        r1 = PublicRule("test", e1)
        self.assertTrue(r1.matches("a"))
        self.assertEqual(e1.current_match, "a")
        self.assertEqual(e1.children[0].current_match, "a")
        self.assertEqual(e1.children[1].current_match, "")

        self.assertTrue(r1.matches("a a"))
        self.assertEqual(e1.current_match, "a a")
        self.assertEqual(e1.children[0].current_match, "a")
        self.assertEqual(e1.children[1].current_match, "a")

        e2 = Sequence(OptionalGrouping("a"), "a")
        r2 = PublicRule("test", e2)
        self.assertTrue(r2.matches("a"))
        self.assertEqual(e2.current_match, "a")
        self.assertEqual(e2.children[0].current_match, "")
        self.assertEqual(e2.children[1].current_match, "a")

        self.assertTrue(r2.matches("a a"))
        self.assertEqual(e2.current_match, "a a")
        self.assertEqual(e2.children[0].current_match, "a")
        self.assertEqual(e2.children[1].current_match, "a")

    def test_multiple_optional_ambiguous(self):
        e1 = Sequence("a", OptionalGrouping("a"), OptionalGrouping("a"))
        r1 = PublicRule("test", e1)
        self.assertTrue(r1.matches("a"))
        self.assertEqual(e1.current_match, "a")
        self.assertEqual(e1.children[0].current_match, "a")
        self.assertEqual(e1.children[1].current_match, "")
        self.assertEqual(e1.children[2].current_match, "")

        self.assertTrue(r1.matches("a a"))
        self.assertEqual(e1.current_match, "a a")
        self.assertEqual(e1.children[0].current_match, "a")
        self.assertEqual(e1.children[1].current_match, "a")
        self.assertEqual(e1.children[2].current_match, "")

        self.assertTrue(r1.matches("a a a"))
        self.assertEqual(e1.current_match, "a a a")
        self.assertEqual(e1.children[0].current_match, "a")
        self.assertEqual(e1.children[1].current_match, "a")
        self.assertEqual(e1.children[2].current_match, "a")

        e2 = Sequence(OptionalGrouping("a"), OptionalGrouping("a"), "a")
        r2 = PublicRule("test", e2)
        self.assertTrue(r2.matches("a"))
        self.assertEqual(e2.current_match, "a")
        self.assertEqual(e2.children[0].current_match, "")
        self.assertEqual(e2.children[1].current_match, "")
        self.assertEqual(e2.children[2].current_match, "a")

        self.assertTrue(r2.matches("a a"))
        self.assertEqual(e2.current_match, "a a")
        self.assertEqual(e2.children[0].current_match, "a")
        self.assertEqual(e2.children[1].current_match, "")
        self.assertEqual(e2.children[2].current_match, "a")

        self.assertTrue(r2.matches("a a a"))
        self.assertEqual(e2.current_match, "a a a")
        self.assertEqual(e2.children[0].current_match, "a")
        self.assertEqual(e2.children[1].current_match, "a")
        self.assertEqual(e2.children[2].current_match, "a")

    def test_optional_ambiguous_complex(self):
        root = Sequence("a", OptionalGrouping("a"),
                        Sequence("a", OptionalGrouping("a")))
        a1 = root.children[0]
        opt1 = root.children[1]
        a2 = opt1.child
        seq2 = root.children[2]
        a3 = seq2.children[0]
        opt2 = seq2.children[1]
        a4 = opt2.child

        r = PublicRule("test", root)

        self.assertTrue(r.matches("a a a a"))
        self.assertEqual(root.current_match, "a a a a")
        self.assertEqual(a1.current_match, "a")
        self.assertEqual(opt1.current_match, "a")
        self.assertEqual(a2.current_match, "a")
        self.assertEqual(seq2.current_match, "a a")
        self.assertEqual(a3.current_match, "a")
        self.assertEqual(opt2.current_match, "a")
        self.assertEqual(a4.current_match, "a")

        self.assertTrue(r.matches("a a a"))
        self.assertEqual(root.current_match, "a a a")
        self.assertEqual(a1.current_match, "a")
        self.assertEqual(opt1.current_match, "a")
        self.assertEqual(a2.current_match, "a")
        self.assertEqual(seq2.current_match, "a")
        self.assertEqual(a3.current_match, "a")
        self.assertEqual(opt2.current_match, "")
        self.assertEqual(a4.current_match, "")

        self.assertTrue(r.matches("a a"))
        self.assertEqual(root.current_match, "a a")
        self.assertEqual(a1.current_match, "a")
        self.assertEqual(opt1.current_match, "")
        self.assertEqual(a2.current_match, "")
        self.assertEqual(seq2.current_match, "a")
        self.assertEqual(a3.current_match, "a")
        self.assertEqual(opt2.current_match, "")
        self.assertEqual(a4.current_match, "")

    def test_optional_forward_search_complex(self):
        seq1 = Sequence(
            OptionalGrouping(Sequence("a", "b c")),
            "a b c"
        )
        opt = seq1.children[0]
        seq2 = opt.child
        a = seq2.children[0]
        bc = seq2.children[1]
        abc = seq1.children[1]
        r = PublicRule("test", seq1)

        self.assertTrue(r.matches("a b c"))
        self.assertEqual(seq1.current_match, "a b c")
        self.assertEqual(abc.current_match, "a b c")
        self.assertEqual(opt.current_match, "")
        self.assertEqual(seq2.current_match, "")
        self.assertEqual(a.current_match, "")
        self.assertEqual(bc.current_match, "")

    def test_repeat_simple(self):
        e = Repeat("hello")
        r = PublicRule("test", e)
        self.assertTrue(r.matches("hello"))
        self.assertEqual(e.current_match, "hello")
        self.assertEqual(e.children[0].current_match, "hello")

        self.assertTrue(r.matches("hello hello"))
        self.assertEqual(e.current_match, "hello hello")
        self.assertEqual(e.children[0].current_match, "hello")

    def test_repeat_complex(self):
        e = Sequence(Repeat("please"), "don't crash")
        r = PublicRule("test", e)
        self.assertTrue(r.matches("please don't crash"))
        self.assertEqual(e.current_match, "please don't crash")
        self.assertEqual(e.children[0].current_match, "please")
        self.assertEqual(e.children[0].child.current_match, "please")
        self.assertEqual(e.children[1].current_match, "don't crash")

        self.assertTrue(r.matches("please please don't crash"))
        self.assertEqual(e.current_match, "please please don't crash")
        self.assertEqual(e.children[0].current_match, "please please")
        self.assertEqual(e.children[0].child.current_match, "please")
        self.assertEqual(e.children[1].current_match, "don't crash")

    def test_successive_repeats(self):
        e = Sequence(Repeat("please"), Repeat("don't crash"))
        r = PublicRule("test", e)
        self.assertTrue(r.matches("please don't crash"))
        self.assertEqual(e.current_match, "please don't crash")
        self.assertEqual(e.children[0].current_match, "please")
        self.assertEqual(e.children[0].child.current_match, "please")
        self.assertEqual(e.children[1].current_match, "don't crash")

        self.assertTrue(r.matches("please please don't crash don't crash"))
        self.assertEqual(e.current_match, "please please don't crash don't crash")
        self.assertEqual(e.children[0].current_match, "please please")
        self.assertEqual(e.children[0].child.current_match, "please")
        self.assertEqual(e.children[1].current_match, "don't crash don't crash")
        self.assertEqual(e.children[1].child.current_match, "don't crash")

    def test_kleene_star(self):
        e = Sequence(KleeneStar("please"), "don't crash")
        r = PublicRule("test", e)

        # No pleases
        self.assertTrue(r.matches("don't crash"))
        self.assertEqual(e.current_match, "don't crash")
        self.assertEqual(e.children[0].current_match, "")
        self.assertEqual(e.children[0].child.current_match, "")
        self.assertEqual(e.children[1].current_match, "don't crash")

        # One please
        self.assertTrue(r.matches("please don't crash"))
        self.assertEqual(e.current_match, "please don't crash")
        self.assertEqual(e.children[0].current_match, "please")
        self.assertEqual(e.children[0].child.current_match, "please")
        self.assertEqual(e.children[1].current_match, "don't crash")

        # Two pleases
        self.assertTrue(r.matches("please please don't crash"))
        self.assertEqual(e.current_match, "please please don't crash")
        self.assertEqual(e.children[0].current_match, "please please")
        self.assertEqual(e.children[0].child.current_match, "please")
        self.assertEqual(e.children[1].current_match, "don't crash")

    def test_successive_kleene_stars(self):
        e1 = Sequence(KleeneStar("please"), KleeneStar("don't crash"))
        r1 = PublicRule("test", e1)
        self.assertTrue(r1.matches("don't crash"))
        self.assertEqual(e1.current_match, "don't crash")
        self.assertEqual(e1.children[0].current_match, "")
        self.assertEqual(e1.children[0].child.current_match, "")
        self.assertEqual(e1.children[1].current_match, "don't crash")

        self.assertTrue(r1.matches("please don't crash"))
        self.assertEqual(e1.current_match, "please don't crash")
        self.assertEqual(e1.children[0].current_match, "please")
        self.assertEqual(e1.children[0].child.current_match, "please")
        self.assertEqual(e1.children[1].current_match, "don't crash")

        self.assertTrue(r1.matches("please please don't crash don't crash"))
        self.assertEqual(e1.current_match, "please please don't crash don't crash")
        self.assertEqual(e1.children[0].current_match, "please please")
        self.assertEqual(e1.children[0].child.current_match, "please")
        self.assertEqual(e1.children[1].current_match, "don't crash don't crash")
        self.assertEqual(e1.children[1].child.current_match, "don't crash")

    def test_repeats_in_repeat(self):
        e1 = Repeat(Repeat("a"))
        r = PublicRule("test", e1)

        self.assertFalse(r.matches(""))
        self.assertEqual(e1.child.current_match, None)
        self.assertEqual(e1.child.child.current_match, None)
        self.assertEqual(e1.current_match, None)

        self.assertTrue(r.matches("a"))
        self.assertEqual(e1.child.current_match, "a")
        self.assertEqual(e1.child.child.current_match, "a")
        self.assertEqual(e1.current_match, "a")

        self.assertTrue(r.matches("a a"))
        self.assertEqual(e1.child.current_match, "a a")
        self.assertEqual(e1.child.child.current_match, "a")
        self.assertEqual(e1.current_match, "a a")

        e2 = KleeneStar(Repeat("a"))
        r2 = PublicRule("test", e2)

        self.assertTrue(r2.matches(""))
        self.assertEqual(e2.child.current_match, "")
        self.assertEqual(e2.child.child.current_match, "")
        self.assertEqual(e2.current_match, "")

        self.assertTrue(r2.matches("a"))
        self.assertEqual(e2.child.current_match, "a")
        self.assertEqual(e2.child.child.current_match, "a")
        self.assertEqual(e2.current_match, "a")

        self.assertTrue(r2.matches("a a"))
        self.assertEqual(e2.child.current_match, "a a")
        self.assertEqual(e2.child.child.current_match, "a")
        self.assertEqual(e2.current_match, "a a")

    def test_multiple_repeats(self):
        e1 = Sequence(Repeat("a"), "b", Repeat("c"), "d")
        r1 = PublicRule("test", e1)
        self.assertTrue(r1.matches("a b c d"))
        self.assertTrue(r1.matches("a a b c d"))
        self.assertTrue(r1.matches("a b c c d"))
        self.assertTrue(r1.matches("a a b c c d"))

        e2 = Sequence(KleeneStar("a"), "b", KleeneStar("c"), "d")
        r2 = PublicRule("test", e2)
        self.assertTrue(r2.matches("b d"))
        self.assertTrue(r2.matches("a b d"))
        self.assertTrue(r2.matches("b c d"))
        self.assertTrue(r2.matches("a b c d"))
        self.assertTrue(r2.matches("a a b c d"))
        self.assertTrue(r2.matches("a b c c d"))
        self.assertTrue(r2.matches("a a b c c d"))

    def test_kleene_star_ambiguous(self):
        e = Sequence(KleeneStar("a"), KleeneStar("a"), "a")
        r = PublicRule("test", e)

        self.assertTrue(r.matches("a"))
        self.assertEqual(e.children[0].current_match, "")
        self.assertEqual(e.children[0].child.current_match, "")
        self.assertEqual(e.children[1].current_match, "")
        self.assertEqual(e.children[1].child.current_match, "")
        self.assertEqual(e.children[2].current_match, "a")
        self.assertEqual(e.current_match, "a")

        # For the moment, an error should be raised for ambiguous repetition
        self.assertRaises(MatchError, r.matches, "a a")
        self.assertRaises(MatchError, r.matches, "a a a")

    def test_repeat_ambiguous(self):
        e1 = Sequence(Repeat("a"), Repeat("a"), "a")
        r1 = PublicRule("test", e1)

        self.assertFalse(r1.matches("a"))
        self.assertEqual(e1.children[0].current_match, None)
        self.assertEqual(e1.children[0].child.current_match, None)
        self.assertEqual(e1.children[1].current_match, None)
        self.assertEqual(e1.children[1].child.current_match, None)
        self.assertEqual(e1.children[2].current_match, None)
        self.assertEqual(e1.current_match, None)

        # For the moment, an error should be raised for ambiguous repetition
        self.assertRaises(MatchError, r1.matches, "a a")
        self.assertRaises(MatchError, r1.matches, "a a a")

        r2 = PublicRule("test", Sequence(Repeat("a"), Repeat("a")))
        self.assertRaises(MatchError, r2.matches, "a a a")
        self.assertRaises(MatchError, r2.matches, "a a a")

        r3 = PublicRule("test", Sequence(Repeat("a"), KleeneStar("a")))
        self.assertRaises(MatchError, r3.matches, "a a")
        self.assertRaises(MatchError, r3.matches, "a a a")

    def test_forward_searching_complex(self):
        e = Sequence("a", Sequence(
            OptionalGrouping("b"), OptionalGrouping("c"),
            "a"
        ))
        r = PublicRule("test", e)

        self.assertTrue(r.matches("a b c a"))
        self.assertEqual(e.current_match, "a b c a")
        self.assertEqual(e.children[0].current_match, "a")
        self.assertEqual(e.children[1].current_match, "b c a")


if __name__ == '__main__':
    unittest.main()
