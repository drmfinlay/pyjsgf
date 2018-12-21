import unittest

from jsgf import PublicRule, Rule

from jsgf.expansions import *
from jsgf.ext import Dictation

from jsgf.ext.rules import calculate_expansion_sequence, expand_dictation_expansion

# Create shorthand aliases for some expansions as they're used here A LOT
Seq = Sequence
Opt = OptionalGrouping
Dict = Dictation
AS = AlternativeSet
Rep = Repeat


class DictationMatchesCase(unittest.TestCase):
    def test_matches_with_literals(self):
        e1 = Seq("hello", Dict())
        r1 = PublicRule("test", e1)
        self.assertTrue(r1.matches("hello world"))
        self.assertTrue(r1.matches("hello world"))
        self.assertEqual(e1.current_match, "hello world")
        self.assertEqual(e1.children[0].current_match, "hello")
        self.assertEqual(e1.children[1].current_match, "world")

        e2 = Seq("a", Dict(), "c")
        r2 = PublicRule("test", e2)
        self.assertTrue(r2.matches("a b c"))
        self.assertEqual(e2.children[0].current_match, "a")
        self.assertEqual(e2.children[1].current_match, "b")
        self.assertEqual(e2.children[2].current_match, "c")
        self.assertEqual(e2.current_match, "a b c")

        # Test with strings that don't match for e1 and e2
        self.assertFalse(r1.matches("test testing"))
        map_expansion(e1, lambda x: self.assertIsNone(x.current_match))
        self.assertFalse(r2.matches("test testing"))
        map_expansion(e2, lambda x: self.assertIsNone(x.current_match))

    def test_matches_as_optional(self):
        e1 = Seq("hello", Opt(Dict()))
        r1 = PublicRule("test", e1)
        self.assertTrue(r1.matches("hello"))
        self.assertEqual(e1.current_match, "hello")
        self.assertEqual(e1.children[0].current_match, "hello")
        self.assertEqual(e1.children[1].current_match, "")

        # Test no match
        self.assertFalse(r1.matches("test testing"))
        map_expansion(
            e1, lambda x: self.assertTrue(x.current_match in [None, ""])
        )

    def test_successive_dictation(self):
        e1 = Seq(Dict(), Dict())
        self.assertEqual(e1.matches("testing testing testing"), "")
        self.assertEqual(e1.current_match, "testing testing testing")
        self.assertEqual(e1.children[0].current_match, "testing",
                         "first dictation should get the first word")
        self.assertEqual(e1.children[1].current_match, "testing testing",
                         "second dictation should get the remainder")

        e3 = Seq(Dict(), Opt(Dict()))
        self.assertEqual(e3.matches("hello"), "")
        self.assertEqual(e3.current_match, "hello")
        self.assertEqual(e3.children[0].current_match, "hello",
                         "required Dictation should get to consume the speech "
                         "string")
        self.assertEqual(e3.children[1].current_match, "")

    def test_forward_tracking(self):
        e = Seq(Opt(Dict()), "hello")
        self.assertEqual(e.matches("hello"), "")
        self.assertEqual(e.current_match, "hello")
        self.assertEqual(e.children[0].current_match, "")
        self.assertEqual(e.children[1].current_match, "hello")

        e = Seq(Dict(), "hello")
        self.assertEqual(e.matches("hey hello"), "")
        self.assertEqual(e.current_match, "hey hello")
        self.assertEqual(e.children[0].current_match, "hey")
        self.assertEqual(e.children[1].current_match, "hello")

        e = Seq("say", Dict(), Opt("end"))
        # Without the optional 'end'.
        self.assertEqual(e.matches("say hello world"), "")
        self.assertEqual(e.current_match, "say hello world")
        self.assertEqual(e.children[0].current_match, "say")
        self.assertEqual(e.children[1].current_match, "hello world")
        self.assertEqual(e.children[2].current_match, "")

        # With the optional 'end'.
        self.assertEqual(e.matches("say hello world end"), "")
        self.assertEqual(e.current_match, "say hello world end")
        self.assertEqual(e.children[0].current_match, "say")
        self.assertEqual(e.children[1].current_match, "hello world")
        self.assertEqual(e.children[2].current_match, "end")

    def test_forward_tracking_multiple(self):
        # Test that matching works with multiple next literals.
        e = Seq(Dict(), Opt(AS("a", "b")))

        # Test with a.
        self.assertEqual(e.matches("test testing a"), "")
        self.assertEqual(e.current_match, "test testing a")
        self.assertEqual(e.children[0].current_match, "test testing")
        self.assertEqual(e.children[1].current_match, "a")

        # Test with b.
        self.assertEqual(e.matches("test testing b"), "")
        self.assertEqual(e.current_match, "test testing b")
        self.assertEqual(e.children[0].current_match, "test testing")
        self.assertEqual(e.children[1].current_match, "b")

        # Test with neither next literal as they are optional in this case.
        self.assertEqual(e.matches("test testing"), "")
        self.assertEqual(e.current_match, "test testing")
        self.assertEqual(e.children[0].current_match, "test testing")
        self.assertEqual(e.children[1].current_match, "")

    def test_back_tracking(self):
        dict1, dict2 = Dict(), Dict()
        seq1 = Seq("lower", dict1)
        seq2 = Seq("camel", dict2)
        e = Rep(AS(seq1, seq2))

        # Match only one time.
        self.assertEqual(e.matches("lower lorem ipsum"), "")
        self.assertEqual(e.current_match, "lower lorem ipsum")
        self.assertEqual(e.get_expansion_matches(seq1), ["lower lorem ipsum"])
        self.assertEqual(e.get_expansion_matches(dict1), ["lorem ipsum"])
        self.assertEqual(e.get_expansion_matches(seq2), [None])
        self.assertEqual(e.get_expansion_matches(dict2), [None])

        # Reset match data for a new match. This is normally done by the expansion's
        # rule.
        e.reset_for_new_match()

        # Test two of the same repetitions.
        self.assertEqual(e.matches("lower lorem ipsum lower lorem ipsum"), "")
        self.assertEqual(e.current_match, "lower lorem ipsum lower lorem ipsum")
        self.assertEqual(e.get_expansion_matches(seq1), ["lower lorem ipsum"] * 2)
        self.assertEqual(e.get_expansion_matches(dict1), ["lorem ipsum"] * 2)
        self.assertEqual(e.get_expansion_matches(seq2), [None] * 2)
        self.assertEqual(e.get_expansion_matches(dict2), [None] * 2)

        # Reset match data again.
        e.reset_for_new_match()

        # Test matching two different repetitions.
        self.assertEqual(e.matches(
            "lower consectetur adipiscing camel dolor sit"),
            ""
        )
        self.assertEqual(
            e.current_match, "lower consectetur adipiscing camel dolor sit"
        )

        # Use e.get_expansion_matches to check the match values.
        self.assertEqual(e.get_expansion_matches(e.child), [
            "lower consectetur adipiscing", "camel dolor sit"
        ])
        self.assertEqual(e.get_expansion_matches(seq1), [
            "lower consectetur adipiscing", None
        ])
        self.assertEqual(e.get_expansion_matches(dict1), [
            "consectetur adipiscing", None
        ])
        self.assertEqual(e.get_expansion_matches(seq2), [None, "camel dolor sit"])
        self.assertEqual(e.get_expansion_matches(dict2), [None, "dolor sit"])

    def test_back_and_forward_tracking(self):
        # Test with a required literal after a repeat.
        dict_ = Dict()
        seq = Seq("lower", dict_)
        rep = Rep(seq)
        e = Seq(rep, "end")

        # Test matching once.
        self.assertEqual(e.matches("lower lorem ipsum end"), "")
        self.assertEqual(e.current_match, "lower lorem ipsum end")
        self.assertEqual(e.children[1].current_match, "end")
        self.assertEqual(rep.get_expansion_matches(seq), ["lower lorem ipsum"])
        self.assertEqual(rep.get_expansion_matches(dict_), ["lorem ipsum"])

        # Reset match data for another match.
        e.reset_for_new_match()

        # Test matching twice.
        self.assertEqual(e.matches("lower lorem ipsum lower lorem ipsum end"), "")
        self.assertEqual(e.current_match, "lower lorem ipsum lower lorem ipsum end")
        self.assertEqual(e.children[1].current_match, "end")
        self.assertEqual(rep.get_expansion_matches(seq), ["lower lorem ipsum"] * 2)
        self.assertEqual(rep.get_expansion_matches(dict_), ["lorem ipsum"] * 2)


class DictationMembersCase(unittest.TestCase):
    """
    Test case for Dictation methods, members and properties.
    """
    def test_compile(self):
        d = Dict()
        d.tag = "dictation"
        self.assertEqual(d.compile(ignore_tags=True), "<DICTATION>")
        self.assertEqual(d.compile(ignore_tags=False), "<DICTATION> { dictation }")

    def test_hash(self):
        # Test that dictation expansions with the same parents have the same hashes.
        dict1, dict2 = Dict(), Dict()
        e1 = Seq("test", dict1)
        e2 = Seq("test", dict2)
        self.assertEqual(hash(e1), hash(e2))

        # Test that dictation expansions with different parents have different
        # hashes.
        dict1, dict2 = Dict(), Dict()
        e1 = Seq("a", dict1)
        e2 = Seq("b", dict2)
        self.assertNotEqual(hash(e1), hash(e2))
        self.assertNotEqual(hash(e1), hash(Dict()))
        self.assertNotEqual(hash(e2), hash(Dict()))


class ExpansionSequenceCase(unittest.TestCase):
    """
    Test cases for expansion sequences used for integrating arbitrary spoken text
    with JSGF grammars, possibly by using a separate decoder.
    This case may be just *slightly* over tested...
    """
    def assert_expansion_sequence_equal(self, expected, expansion):
        """
        Takes a list of expected expansions and an expansion to be tested.
        :type expected: list
        :type expansion: Expansion
        """
        actual_expansions = calculate_expansion_sequence(expansion)
        self.assertListEqual(expected, actual_expansions)

    def test_only_dictation(self):
        self.assert_expansion_sequence_equal([(Dict())], Dict())

    def test_no_dictation(self):
        seq = calculate_expansion_sequence(Literal("hello"))
        self.assertListEqual(seq, [Literal("hello")])

    def test_dictation_in_sequence(self):
        # Dictation first
        e1 = Seq(Dict(), "test", "testing")
        self.assert_expansion_sequence_equal([
            Seq(Dict()),
            Seq("test", "testing")
        ], e1)

        # Dictation second
        e2 = Seq("test", Dict(), "testing")
        self.assert_expansion_sequence_equal([
            Seq("test"),
            Seq(Dict()),
            Seq("testing")
        ], e2)

        # Dictation last
        e3 = Seq("test", "testing", Dict())
        self.assert_expansion_sequence_equal([
            Seq("test", "testing"),
            Seq(Dict())
        ], e3)

    def test_multiple_dictation_in_sequence(self):
        e1 = Seq(Dict(), "test", "testing", Dict())
        self.assert_expansion_sequence_equal([
            Seq(Dict()),
            Seq("test", "testing"),
            Seq(Dict())
        ], e1)

        e2 = Seq("test", Dict(), "testing", Dict())
        self.assert_expansion_sequence_equal([
            Seq("test"),
            Seq(Dict()),
            Seq("testing"),
            Seq(Dict()),
        ], e2)

        e3 = Seq("test", "testing", Dict(),
                 "more", "testing", Dict())
        self.assert_expansion_sequence_equal([
            Seq("test", "testing"),
            Seq(Dict()),
            Seq("more", "testing"),
            Seq(Dict())
        ], e3)

    def test_dictation_in_alternative_set(self):
        # Dictation first
        e1 = AS(Dict(), "test", "testing")
        self.assert_expansion_sequence_equal([
            AS(Dict()),
            AS("test", "testing")
        ], e1)

        # Dictation second
        e2 = AS("test", Dict(), "testing")
        self.assert_expansion_sequence_equal([
            AS("test"),
            AS(Dict()),
            AS("testing")
        ], e2)

        # Dictation last
        e3 = AS("test", "testing", Dict())
        self.assert_expansion_sequence_equal([
            AS("test", "testing"),
            AS(Dict())
        ], e3)

    def test_multiple_dictation_in_alternative_set(self):
        e1 = AS(Dict(), "test", "testing", Dict())
        self.assert_expansion_sequence_equal([
            AS(Dict()),
            AS("test", "testing"),
            AS(Dict())
        ], e1)

        e2 = AS("test", Dict(), "testing", Dict())
        self.assert_expansion_sequence_equal([
            AS("test"),
            AS(Dict()),
            AS("testing"),
            AS(Dict())
        ], e2)

        e3 = AS("test 1", "test 2", Dict(),
                "test 3", "test 4", Dict())
        self.assert_expansion_sequence_equal([
            AS("test 1", "test 2"),
            AS(Dict()),
            AS("test 3", "test 4"),
            AS(Dict())
        ], e3)

    def test_successive_dictation_alt_sets(self):
        e1 = Seq(AS("test", Dict()), AS("testing", Dict()))
        self.assert_expansion_sequence_equal([
            Seq(AS("test")),
            Seq(AS(Dict())),
            Seq(AS("testing")),
            Seq(AS(Dict())),
        ], e1)

    def test_optional_dictation(self):
        # Optional dictation first
        e1 = Seq(Opt(Dict()), "test")
        self.assert_expansion_sequence_equal([
            Seq(Opt(Dict())),
            Seq("test")
        ], e1)

        # Optional dictation second
        e2 = Seq("test", Opt(Dict()), "testing")
        self.assert_expansion_sequence_equal([
            Seq("test"), Seq(Opt(Dict())),
            Seq("testing")
        ], e2)

        # Optional dictation last
        e3 = Seq("test", Opt(Dict()))
        self.assert_expansion_sequence_equal([
            Seq("test"), Seq(Opt(Dict()))
        ], e3)

    def test_optional_dictation_sequence(self):
        e1 = Seq("test", Opt(Seq("testing", Dict())))
        self.assert_expansion_sequence_equal([
            Seq("test", Opt(Seq("testing"))),
            Seq(Opt(Seq(Dict())))
        ], e1)

    def test_dictation_using_all(self):
        e1 = Seq(Seq("test this", Opt("messy")), Dict(),
                 AS("end", "stop", Dict()), Opt(Dict()))
        self.assert_expansion_sequence_equal([
            Seq(Seq("test this", Opt("messy"))),
            Seq(Dict()),
            Seq(AS("end", "stop")),
            Seq(AS(Dict())),
            Seq(Opt(Dict()))
        ], e1)

    def test_optional_dictation_alt_set(self):
        e1 = Seq("test", Opt(
            AS("testing", Dict())
        ))
        self.assert_expansion_sequence_equal([
            Seq("test", Opt(AS("testing"))),
            Seq(Opt(AS(Dict())))
        ], e1)

    def test_repeated_dictation(self):
        e1 = Rep(Dict())
        self.assert_expansion_sequence_equal([
            Rep(Dict())
        ], e1)

    def test_repeated_dictation_with_literals(self):
        e1 = Rep(Seq("lower", Dict()))
        self.assert_expansion_sequence_equal([
            Rep(Seq("lower")),
            Rep(Seq(Dict()))
        ], e1)

        e2 = Rep(Seq(Dict(), "lower"))
        self.assert_expansion_sequence_equal([
            Rep(Seq(Dict())),
            Rep(Seq("lower"))
        ], e2)

    def test_repeated_dictation_and_alt_set(self):
        e1 = Rep(Seq(AS("lower", "upper"), Dict()))
        self.assert_expansion_sequence_equal([
            Rep(Seq(AS("lower", "upper"))),
            Rep(Seq(Dict()))
        ], e1)

        e2 = Rep(Seq(Dict(), AS("lower", "upper")))
        self.assert_expansion_sequence_equal([
            Rep(Seq(Dict())),
            Rep(Seq(AS("lower", "upper")))
        ], e2)

    def test_with_rule_ref(self):
        r1 = PublicRule("test", "test")
        e1 = Seq(RuleRef(r1), Dict())
        self.assert_expansion_sequence_equal([
            Seq(RuleRef(r1)),
            Seq(Dict())
        ], e1)

        r2 = PublicRule("test", Dict())
        e2 = Seq(RuleRef(r2), Dict())
        self.assert_expansion_sequence_equal([
            Dict(),
            Seq(Dict())
        ], e2)


class ExpandedDictationExpansion(unittest.TestCase):
    """
    Test whether the functionality of expand_dictation_expansion works correctly.
    """
    def test_no_alt_sets(self):
        e2 = Seq("hi", "hello")
        self.assertListEqual(expand_dictation_expansion(e2), [e2])

        e1 = Seq("hi", "hello", Dict())
        self.assertListEqual(expand_dictation_expansion(e1), [e1])

    def test_no_dictation(self):
        e1 = AS("hi", "hello")
        self.assertListEqual(expand_dictation_expansion(e1), [e1],
                             "Dictation-free expansions should remain untouched")

        e2 = Seq(AS("hi", "hello"), "there")
        self.assertListEqual(expand_dictation_expansion(e2), [e2])

    def test_one_dictation(self):
        e1 = AS("hi", "hello", Dict())
        self.assertListEqual(expand_dictation_expansion(e1), [
            AS("hi", "hello"),
            Dict()
        ])

        e2 = AS("hi", "hello", Seq("hey", Dict()))
        self.assertListEqual(expand_dictation_expansion(e2), [
            AS("hi", "hello"),
            Seq("hey", Dict())
        ])

        e3 = Seq(AS("hi", "hello", Dict()), "there")
        self.assertListEqual(expand_dictation_expansion(e3), [
            Seq(AS("hi", "hello"), "there"),
            Seq(Dict(), "there")
        ])

    def test_one_jsgf_only_alternative(self):
        e1 = AS("a", Dict())
        self.assertListEqual(expand_dictation_expansion(e1), [
            Literal("a"),
            Dict()
        ])

        e2 = AS("a")
        self.assertListEqual(expand_dictation_expansion(e2), [
            AS("a")
        ], "Dictation free AlternativeSets should remain untouched")

    def test_multiple_dictation(self):
        e1 = AS("hi", "hello", Seq("hey", Dict()), Dict())
        self.assertListEqual(expand_dictation_expansion(e1), [
            AS("hi", "hello"),
            Seq("hey", Dict()),
            Dict()
        ])

        e2 = Seq(AS("hi", "hello", Seq("hey", Dict())), Dict())
        self.assertListEqual(expand_dictation_expansion(e2), [
            Seq(AS("hi", "hello"), Dict()),
            Seq(Seq("hey", Dict()), Dict())
        ])

    def test_multiple_dictation_alt_sets(self):
        e1 = Seq(AS("a", "b", Dict()), "c", AS("d", Dict()))
        self.assertListEqual(expand_dictation_expansion(e1), [
            Seq(AS("a", "b"), "c", "d"),
            Seq(AS("a", "b"), "c", Dict()),
            Seq(Dict(), "c", "d"),
            Seq(Dict(), "c", Dict())
        ])

        e2 = Seq(AS("a", "b", Dict()), "c", AS("d", Dict()), "e")
        self.assertListEqual(expand_dictation_expansion(e2), [
            Seq(AS("a", "b"), "c", "d", "e"),
            Seq(AS("a", "b"), "c", Dict(), "e"),
            Seq(Dict(), "c", "d", "e"),
            Seq(Dict(), "c", Dict(), "e")
        ])

    def test_mutually_exclusive_dictation(self):
        e1 = AS(Seq("a", Dict()), Seq(Dict(), "b"))
        self.assertListEqual(expand_dictation_expansion(e1), [
            Seq("a", Dict()),
            Seq(Dict(), "b")
        ])

        e2 = AS(Seq("a", Dict()), Seq("b", Dict()))
        self.assertListEqual(expand_dictation_expansion(e2), [
            Seq("a", Dict()),
            Seq("b", Dict())
        ])

        e3 = AS(Seq(Dict(), "a"), Seq(Dict(), "b"))
        self.assertListEqual(expand_dictation_expansion(e3), [
            Seq(Dict(), "a"),
            Seq(Dict(), "b")
        ])

        # Also test with a JSGF only alternative
        e4 = AS(Seq("a", Dict()), Seq("b", Dict()), "c")
        self.assertListEqual(expand_dictation_expansion(e4), [
            Literal("c"),  # JSGF alternatives just happen to be processed first
            Seq("a", Dict()),
            Seq("b", Dict())
        ])

    def test_optional(self):
        e1 = Seq("hey", Opt(Dict()))
        self.assertListEqual(expand_dictation_expansion(e1), [
            Seq("hey"),
            Seq("hey", Dict())
        ])

        e2 = Seq("the", Opt(Dict()), "thing")
        self.assertListEqual(expand_dictation_expansion(e2), [
            Seq("the", "thing"),
            Seq("the", Dict(), "thing")
        ])

        e3 = Seq("the", KleeneStar(Dict()), "thing")
        self.assertListEqual(expand_dictation_expansion(e3), [
            Seq("the", "thing"),
            Seq("the", Rep(Dict()), "thing")
        ])

        e4 = Seq(Opt("hey"), Dict())
        self.assertListEqual(expand_dictation_expansion(e4), [
            Seq(Dict()),
            Seq("hey", Dict())
        ])

        e5 = Seq(Opt("hey"), Dict(), Opt("hey"))
        self.assertListEqual(expand_dictation_expansion(e5), [
            Seq(Dict()),
            Seq(Dict(), "hey"),
            Seq("hey", Dict()),
            Seq("hey", Dict(), "hey")
        ])

    def test_optional_with_alt_set(self):
        e1 = AS("a", "b", Seq("c", Opt(Seq("d", Dict()))))
        self.assertListEqual(expand_dictation_expansion(e1), [
            AS("a", "b", Seq("c")),
            AS("a", "b"),
            Seq("c", Seq("d", Dict()))
        ])

        e2 = AS("a", "b", Seq("c", KleeneStar(Seq("d", Dict()))))
        self.assertListEqual(expand_dictation_expansion(e2), [
            AS("a", "b", Seq("c")),
            AS("a", "b"),
            Seq("c", Rep(Seq("d", Dict())))
        ])

        e3 = AS("a", "b", Seq(Opt("c"), Seq("d", Dict())))
        self.assertListEqual(expand_dictation_expansion(e3), [
            AS("a", "b"),
            Seq(Seq("d", Dict())),
            Seq("c", Seq("d", Dict()))
        ])

        e4 = AS("a", "b", Seq(KleeneStar("c"), Seq("d", Dict())))
        self.assertListEqual(expand_dictation_expansion(e4), [
            AS("a", "b"),
            Seq(Seq("d", Dict())),
            Seq(Rep("c"), Seq("d", Dict()))
        ])

    def test_copying(self):
        """Original expansions are not used in output expansions"""
        # Note that JSGF only expansions are not expected to pass this test;
        # expand_dictation_expansion(e) returns exactly e.

        def assert_no_identical_expansions(original_e, expanded_list):
            """
            Recursively check if any expanded expansion is identical to one in the
            original expansion tree.
            Only the immediate tree is checked (shallow traversals).
            :type original_e: Expansion
            :type expanded_list: list
            """
            original_expansions = flat_map_expansion(original_e, shallow=True)

            def f(x):
                for o in original_expansions:
                    self.assertIsNot(x, o)

            for expanded in expanded_list:
                map_expansion(expanded, f, shallow=True)

        # Test with a relatively simple expansion
        e = AS("a", "b", Seq("c", Dict()))
        result = expand_dictation_expansion(e)
        self.assertListEqual(result, [
            AS("a", "b"),
            Seq("c", Dict())
        ])
        assert_no_identical_expansions(e, result)

        # Test with an expansion using RuleRefs
        n = Rule("n", False, AS("one", "two", "three"))
        e = AS(Seq("backward", RuleRef(n)), "forward", Seq(Dict(), RuleRef(n)))
        result = expand_dictation_expansion(e)
        self.assertListEqual(result, [
            AS(Seq("backward", RuleRef(n)), "forward"),
            Seq(Dict(), RuleRef(n))
        ])
        assert_no_identical_expansions(e, result)

        # Test with an expansion using optionals
        e = AS("a", "b", Seq("c", Opt(Dict())))
        result = expand_dictation_expansion(e)
        self.assertListEqual(result, [
            AS("a", "b", Seq("c")),
            AS("a", "b"),
            Seq("c", Dict())
        ])
        assert_no_identical_expansions(e, result)

        # And again instead using KleeneStar
        e = AS("a", "b", Seq("c", KleeneStar(Dict())))
        result = expand_dictation_expansion(e)
        self.assertListEqual(result, [
            AS("a", "b", Seq("c")),
            AS("a", "b"),
            Seq("c", Repeat(Dict()))
        ])
        assert_no_identical_expansions(e, result)


if __name__ == '__main__':
    unittest.main()
