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


class MatchesCase(unittest.TestCase):
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
        self.assertEqual(e.matching_slice, slice(0, 5))

    def test_matching_tags(self):
        e = Literal("hello")
        e.tag = "greet"
        r = PublicRule("test", e)
        self.assertTrue(r.matches("hello"))
        self.assertEqual(e.current_match, "hello")
        self.assertEqual(e.matching_slice, slice(0, 5))
        self.assertEqual(r.matched_tags, ["greet"])

        # Test that rule.matches() erases previous tags.
        self.assertFalse(r.matches(""))
        self.assertEqual(r.matched_tags, [])

    def test_literal_no_match(self):
        e = Literal("hello world")
        r = PublicRule("test", e)
        self.assertFalse(r.matches("hello"))
        self.assertEqual(e.current_match, None)
        self.assertEqual(e.matching_slice, None)

    def test_sequence(self):
        e = Sequence("hello", "world")
        r = PublicRule("test", e)
        self.assertTrue(r.matches("hello world"))
        self.assertEqual(e.children[0].current_match, "hello")
        self.assertEqual(e.children[0].matching_slice, slice(0, 5))
        self.assertEqual(e.children[1].current_match, "world")
        self.assertEqual(e.children[1].matching_slice, slice(6, 11))

    def test_sequence_no_match(self):
        e = Sequence("hello", "world")
        r = PublicRule("test", e)
        self.assertFalse(r.matches("hello"))
        self.assertEqual(e.children[0].current_match, None,
                         "current_match should be None if the whole rule didn't "
                         "match")
        self.assertEqual(e.children[0].matching_slice, None)
        self.assertEqual(e.children[1].current_match, None)
        self.assertEqual(e.children[1].matching_slice, None)

    def test_alt_set_simple(self):
        hello, hi = map(Literal, ["hello", "hi"])
        e = AlternativeSet(hello, hi)
        r = PublicRule("test", e)
        self.assertTrue(r.matches("hello"))
        self.assertEqual(e.current_match, "hello")
        self.assertEqual(hello.current_match, "hello")
        self.assertEqual(hi.current_match, None)
        self.assertEqual(hello.matching_slice, slice(0, 5))
        self.assertEqual(hi.matching_slice, None)

        self.assertTrue(r.matches("hi"))
        self.assertEqual(e.current_match, "hi")
        self.assertEqual(hi.current_match, "hi")
        self.assertEqual(hello.current_match, None)
        self.assertEqual(hi.matching_slice, slice(0, 2))
        self.assertEqual(hello.matching_slice, None)

        self.assertFalse(r.matches("hey"))
        def make_assertion(x):
            self.assertIsNone(x.current_match)
            self.assertIsNone(x.matching_slice)

        map_expansion(e, make_assertion)

    def test_alt_set_complex(self):
        a1 = AlternativeSet("hello", "hi")
        a2 = AlternativeSet("there", "my friend")
        e = Sequence(a1, a2)
        r = PublicRule("test", e)
        self.assertFalse(r.matches("hey"))
        self.assertEqual(e.current_match, None)
        self.assertEqual(e.children[0].current_match, None)
        self.assertEqual(e.children[1].current_match, None)

        self.assertTrue(r.matches("hi there"))
        # Check current_match
        self.assertEqual(e.current_match, "hi there")
        self.assertEqual(a1.current_match, "hi")
        self.assertEqual(a1.children[0].current_match, None)
        self.assertEqual(a1.children[1].current_match, "hi")
        self.assertEqual(a2.current_match, "there")
        self.assertEqual(a2.children[0].current_match, "there")
        self.assertEqual(a2.children[1].current_match, None)

        # Check matching_slice
        self.assertEqual(e.matching_slice, slice(0, 8))
        self.assertEqual(a1.matching_slice, slice(0, 2))
        self.assertEqual(a1.children[0].matching_slice, None)
        self.assertEqual(a1.children[1].matching_slice, slice(0, 2))
        self.assertEqual(a2.matching_slice, slice(3, 8))
        self.assertEqual(a2.children[0].matching_slice, slice(3, 8))
        self.assertEqual(a2.children[1].matching_slice, None)

        # If a speech string doesn't match, then no match values should be set.
        self.assertFalse(r.matches("hi"))
        def make_assertion(x):
            self.assertIsNone(x.current_match)
            self.assertIsNone(x.matching_slice)

        map_expansion(e, make_assertion)

    def test_repeating_alt_set(self):
        g = Grammar()
        n = Rule(
            "n", False, AlternativeSet(
                "one", "two", "three", "four", "five" "six",
                "seven", "eight", "nine", "ten"))
        r = Rule("test", True, Repeat(AlternativeSet(
            Sequence("up", OptionalGrouping(NamedRuleRef("n"))),
            Sequence("down", OptionalGrouping(NamedRuleRef("n"))),
            Sequence("left", OptionalGrouping(NamedRuleRef("n"))),
            Sequence("right", OptionalGrouping(NamedRuleRef("n")))
        )))
        g.add_rules(n, r)
        self.assertTrue(r.matches("up"))
        self.assertTrue(r.matches("down"))
        self.assertTrue(r.matches("left"))
        self.assertTrue(r.matches("right"))
        self.assertTrue(r.matches("up down left right"))
        self.assertTrue(r.matches("up one down left two right three"))
        self.assertTrue(r.matches("down right three up two left ten"))

    def test_alt_set_weights(self):
        # Test that AlternativeSet weights effects the matching process.
        one, two, three = map(Literal, ["one", "two", "three"])
        e = AlternativeSet(one, two, three)
        e.weights = {one: 1, two: 2, three: 3}

        # Test the order in which child expansions are matched.
        self.assertEqual(repr(e.matcher_element),
                         '{"three" ^ "two" ^ "one"}'.replace('"', "'"))

        # Each alternative should be matchable with non-zero weights.
        r = Rule("test", True, e)
        self.assertTrue(r.matches("one"))
        self.assertTrue(r.matches("two"))
        self.assertTrue(r.matches("three"))

        # Test that a weight of 0 for "a" makes the alternative unmatchable.
        e.set_weight(one, 0)
        self.assertFalse(r.matches("one"))
        self.assertTrue(r.matches("two"))
        self.assertTrue(r.matches("three"))

        # Test the order in which child expansions are matched.
        self.assertEqual(repr(e.matcher_element),
                         '{"three" ^ "two"}'.replace('"', "'"))

        # Test that no alternatives can match if all weights are 0.
        e.weights = {one: 0, two: 0, three: 0}
        self.assertFalse(r.matches("one"))
        self.assertFalse(r.matches("two"))
        self.assertFalse(r.matches("three"))

    def test_alt_set_and_optionals(self):
        # Test for Matching issue with alternatives and OptionalGrouping (iss. #12)
        e = Sequence("this is a ", OptionalGrouping("big"),
                     AlternativeSet("sentence", "file"))
        r = PublicRule("test", e)
        self.assertTrue(r.matches("this is a sentence"))
        self.assertTrue(r.matches("this is a big sentence"))
        self.assertTrue(r.matches("this is a file"))
        self.assertTrue(r.matches("this is a big file"))

        e = Sequence("this is a ", KleeneStar("big"),
                     AlternativeSet("sentence", "file"))
        r = PublicRule("test", e)
        self.assertTrue(r.matches("this is a sentence"))
        self.assertTrue(r.matches("this is a big sentence"))
        self.assertTrue(r.matches("this is a big big sentence"))
        self.assertTrue(r.matches("this is a file"))
        self.assertTrue(r.matches("this is a big file"))
        self.assertTrue(r.matches("this is a big big big file"))

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
        person = PrivateRule("person", e1)
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

        # Check that r2 matches delete without a number
        self.assertTrue(r2.matches("delete"))
        for n in numbers:
            self.assertTrue(r1.matches(n))
            self.assertTrue(r2.matches("backspace %s" % n),
                            "matching 'backspace %s' failed" % n)
            self.assertTrue(r2.matches("delete %s" % n),
                            "matching 'delete %s' failed" % n)

    def test_named_rule_ref(self):
        g = Grammar()
        test = Rule("test", False, "b")
        r = Rule("r", True, Sequence("a", NamedRuleRef("test")))

        # An error should be raised if a NamedRuleRef cannot be resolved
        self.assertRaises(GrammarError, r.expansion.matches, "a")
        self.assertRaises(GrammarError, r.expansion.matches, "a b")
        self.assertRaises(GrammarError, r.matches, "a b")
        self.assertRaises(GrammarError, r.matches, "a b")

        # Test that 'r' being part of a Grammar still raises an error if
        # the 'test' rule doesn't exist in it.
        g.add_rule(r)
        self.assertRaises(GrammarError, r.matches, "a b")
        self.assertRaises(GrammarError, r.expansion.matches, "a b")

        # Add the 'test' rule to the grammar and test again
        g.add_rule(test)
        self.assertTrue(r.matches("a b"))
        self.assertEqual(r.expansion.matches("a b"), "")

    def test_multiple_named_rule_refs(self):
        # Note: this test is predicated on the parser working correctly.
        grammar_string = """
        #JSGF V1.0 UTF-8 en;
        grammar default;
        public <root> = (<repeating_cmd>);
        <repeating_cmd> = <nav>+;
        <n> = one|two|three|four|five|six|seven|eight|nine|ten;
        <nav> = (up [<n>])|(down [<n>]);
        """
        g = parse_grammar_string(grammar_string)

        # Check that r2 matches 'up down' without numbers.
        self.assertEqual(g.find_matching_rules("up down"), g.match_rules)

        # Check that r2 matches with and without numbers.
        self.assertListEqual(
            g.find_matching_rules("up two down five down ten up three"),
            g.match_rules
        )


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
        self.assertEqual(e1.child.current_match, "a")
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
        self.assertEqual(e2.child.current_match, "a")
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

    def test_repetition_match_methods(self):
        """
        Test the Expansion.had_match, Repeat.get_expansion_matches and
        Repeat.methods.
        """
        a, b, c = map(Literal, "abc")
        e = Repeat(AlternativeSet(a, b, c))

        # Match a string using all three alternatives
        self.assertEqual(e.matches("a b c"), "")

        # Test expansions a, b and c
        # All three expansions should have had a match and get_expansions_matches
        # should return a list of length 3 for each; there were 3 repetitions of
        # the alternative set.
        # Also test the return values for get_expansion_slices().
        self.assertTrue(a.had_match)
        self.assertListEqual(
            e.get_expansion_matches(a),
            ["a", None, None]
        )
        self.assertListEqual(
            e.get_expansion_slices(a),
            [slice(0, 1), None, None]
        )
        self.assertTrue(b.had_match)
        self.assertListEqual(
            e.get_expansion_matches(b),
            [None, "b", None]
        )
        self.assertListEqual(
            e.get_expansion_slices(b),
            [None, slice(2, 3), None]
        )
        self.assertTrue(c.had_match)
        self.assertListEqual(
            e.get_expansion_matches(c),
            [None, None, "c"]
        )
        self.assertListEqual(
            e.get_expansion_slices(c),
            [None, None, slice(4, 5)]
        )

        # Reset the match data.
        e.reset_for_new_match()

        # Test with multiple matches for each alternative
        self.assertEqual(e.matches("a b c a b c a b c"), "")
        self.assertTrue(a.had_match)
        self.assertListEqual(
            e.get_expansion_matches(a),
            ["a", None, None, "a", None, None, "a", None, None]
        )
        self.assertListEqual(
            e.get_expansion_slices(a),
            [slice(0, 1), None, None, slice(6, 7), None, None,
             slice(12, 13), None, None]
        )
        self.assertTrue(b.had_match)
        self.assertListEqual(
            e.get_expansion_matches(b),
            [None, "b", None, None, "b", None, None, "b", None]
        )
        self.assertListEqual(
            e.get_expansion_slices(b),
            [None, slice(2, 3), None, None, slice(8, 9), None,
             None, slice(14, 15), None]
        )
        self.assertTrue(c.had_match)
        self.assertListEqual(
            e.get_expansion_matches(c),
            [None, None, "c", None, None, "c", None, None, "c"]
        )
        self.assertListEqual(
            e.get_expansion_slices(c),
            [None, None, slice(4, 5), None, None, slice(10, 11),
             None, None, slice(16, 17)]
        )

        # Test with get_expansion_matches an expansion that isn't a descendant
        self.assertListEqual(e.get_expansion_matches(Literal("d")), [])

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

    def test_forward_searching_special(self):
        # Test that special NullRef and VoidRef expansions are handled properly
        e = Sequence(OptionalGrouping("a"), NullRef(), OptionalGrouping("a"))
        r = Rule("r", True, e)
        self.assertTrue(r.matches("a a"))
        self.assertEqual(e.current_match, "a a")
        self.assertEqual(e.children[0].child.current_match, "a")
        self.assertEqual(e.children[1].current_match, "")
        self.assertEqual(e.children[2].current_match, "a")
        self.assertTrue(r.matches("a a"))
        self.assertEqual(e.current_match, "a a")
        self.assertEqual(e.children[0].child.current_match, "a")
        self.assertEqual(e.children[1].current_match, "")
        self.assertEqual(e.children[2].current_match, "a")

        e = Sequence(OptionalGrouping("a"), VoidRef())
        r = Rule("r", True, e)
        self.assertFalse(r.matches("a a"))
        self.assertEqual(e.current_match, None)
        self.assertEqual(e.children[0].child.current_match, "")
        self.assertEqual(e.children[1].current_match, None)
        self.assertFalse(r.matches("a a a"))
        self.assertEqual(e.current_match, None)
        self.assertEqual(e.children[0].child.current_match, "")
        self.assertEqual(e.children[1].current_match, None)

    def test_invalidation(self):
        # Test that an expansion matches properly after changing a parent or
        # ChildList.
        e = AlternativeSet("a", "b")
        r = PublicRule("test", e)

        self.assertTrue(r.matches("b"))
        self.assertEqual(e.current_match, "b")

        # Pop the "b" literal.
        e.children.pop(1)

        # Matching "b" again should fail.
        self.assertFalse(r.matches("b"))
        self.assertEqual(e.current_match, None)

    def test_invalidation_of_references(self):
        # Test invalidation of references.
        n = Rule("n", False, AlternativeSet("once", "twice", "thrice"))

        # Create rules using NamedRuleRefs and RuleRefs to reference the 'n' rule.
        r1 = PublicRule("test1", Sequence("do this", NamedRuleRef("n")))
        r2 = PublicRule("test2", Sequence("do this", RuleRef(n)))

        # Add all three rules to a grammar.
        g = Grammar()
        g.add_rules(n, r1, r2)

        # Both should match using 'once', 'twice' and 'thrice' initially.
        self.assertListEqual(g.find_matching_rules("do this once"), [r1, r2])
        self.assertListEqual(g.find_matching_rules("do this twice"), [r1, r2])
        self.assertListEqual(g.find_matching_rules("do this thrice"), [r1, r2])

        # Add 'four times' to n's alternative set.
        n.expansion.children.append("four times")

        # Check that both rules also match 'four times'. If they don't match, then
        # the references haven't been invalidated.
        self.assertListEqual(g.find_matching_rules("do this once"), [r1, r2])
        self.assertListEqual(g.find_matching_rules("do this twice"), [r1, r2])
        self.assertListEqual(g.find_matching_rules("do this thrice"), [r1, r2])
        self.assertListEqual(g.find_matching_rules("do this four times"), [r1, r2])


if __name__ == '__main__':
    unittest.main()
