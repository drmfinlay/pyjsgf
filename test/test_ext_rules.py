import unittest

from jsgf import *
from jsgf.ext import *

# Create shorthand aliases for some expansions as they're used here A LOT
Seq = Sequence
Opt = OptionalGrouping
Dict = Dictation
AS = AlternativeSet
Rep = Repeat


def generate_rule(e):
    return PublicSequenceRule("test", e)


class SequenceRulePropertiesCase(unittest.TestCase):
    def test_dictation_only_one_expansion(self):
        r1 = generate_rule(Dict())
        r2 = generate_rule(Literal("test"))

        self.assertTrue(r1.current_is_dictation_only)
        self.assertFalse(r2.current_is_dictation_only)

    def test_dictation_and_literal(self):
        rule = SequenceRule("test", True, Seq("hello", Dict()))
        self.assertFalse(rule.current_is_dictation_only)

        # Move to the next expansion in the sequence
        self.assertTrue(rule.matches("hello"))
        rule.set_next()
        self.assertTrue(rule.current_is_dictation_only)

    def test_dictation_only_complex(self):
        e1 = Seq(Dict(), Dict())
        r1 = generate_rule(e1)
        self.assertTrue(r1.current_is_dictation_only)
        self.assertTrue(r1.matches("hello"))

        # Go to the next expansion
        r1.set_next()
        self.assertTrue(r1.current_is_dictation_only)

    def test_next_in_sequence_methods(self):
        r1 = generate_rule(Seq("hello", Dict()))
        self.assertTrue(r1.has_next_expansion)
        r1.set_next()
        self.assertFalse(r1.has_next_expansion)
        r1.set_next()
        self.assertFalse(r1.has_next_expansion)

    def test_repeating_sequence(self):
        """
        Test that if SequenceRule is given an expansion tree with Repeat and
        Dictation expansions, that the expansion sequence is correct and that
        can_repeat is correct.
        """
        r1 = generate_rule(Rep(Seq("hello", Dict())))
        self.assertTrue(r1.can_repeat)
        self.assertEqual(r1.expansion, Seq("hello"))
        r1.set_next()
        self.assertEqual(r1.expansion, Seq(Dict()))

        # Test with non-root Repeat expansions
        r2 = generate_rule(Seq(Rep("hello")))
        self.assertTrue(r2.can_repeat)
        self.assertEqual(r2.expansion, Seq("hello"))

        r3 = generate_rule(AS(Seq(Rep(Dict()))))
        self.assertTrue(r3.can_repeat)
        self.assertEqual(r3.expansion, AS(Seq(Dict())))

        r4 = generate_rule(Seq(Rep(Seq("hello", Dict()))))
        self.assertTrue(r4.can_repeat)
        self.assertEqual(r4.expansion, Seq(Seq("hello")))
        r4.set_next()
        self.assertEqual(r4.expansion, Seq(Seq(Dict())))

    def test_non_repeating_sequence(self):
        """
        Test that if SequenceRule is given an expansion tree with Repeat and
        Dictation expansions, that the expansion sequence is correct and that
        can_repeat is correct.
        """
        r1 = generate_rule(Dict())
        self.assertFalse(r1.can_repeat)

        # Test with Repeat expansions that aren't ancestors of all leaves
        r2 = generate_rule(Seq(Rep(Dict()), "world"))
        self.assertFalse(r2.can_repeat)
        self.assertEqual(r2.expansion, Seq(Rep(Dict())))
        r2.set_next()
        self.assertEqual(r2.expansion, Seq("world"))

        r3 = generate_rule(Seq("world", Rep(Dict())))
        self.assertFalse(r3.can_repeat)
        self.assertEqual(r3.expansion, Seq("world"))
        r3.set_next()
        self.assertEqual(r3.expansion, Seq(Rep(Dict())))

    def test_original_expansion(self):
        """
        Test to check whether the original_expansion property yields the same
        expansion passed to the SequenceRule's init method.
        """
        e1 = Seq("hello", Dict())
        r1 = generate_rule(e1)
        self.assertIs(r1.original_expansion, e1)

        # Test with Repeats which require special handling.
        e2 = Seq(Rep("hello"))
        r2 = generate_rule(e2)
        self.assertIs(r2.original_expansion, e2)

        e3 = Rep(Seq("hello", Dict()))
        r3 = generate_rule(e3)
        self.assertIs(r3.original_expansion, e3)


class SequenceRuleGraftMatchMethods(unittest.TestCase):
    def test_simple(self):
        r1 = PublicRule("test", Dict())
        r2 = generate_rule(r1.expansion)
        r2.matches("hello world")
        self.assertEqual(r1.expansion.current_match, "hello world")

        r3 = PublicRule("test", Seq("hello", Dict()))
        r4 = generate_rule(r3.expansion)
        r4.matches("hello")
        r4.set_next()
        r4.matches("there")
        self.assertEqual(r3.expansion.current_match, "hello there")

    def test_repeating_dictation(self):
        r1 = PublicRule("test", Rep(Dict()))
        r2 = generate_rule(r1.expansion)
        r2.matches("hello")
        r2.refuse_matches = False
        r2.matches("hello")

        # r1 should have had r2's current_match values grafted onto it
        self.assertEqual(r1.expansion.current_match, "hello")
        self.assertEqual(r1.expansion.child.current_match, "hello")

        # Check that a rule with a Literal also works fine
        r3 = PublicRule("test", Rep(Seq(Dict(), "world")))
        r4 = generate_rule(r3.expansion)
        r4.matches("hello")
        r4.refuse_matches = False
        r4.matches("hello")
        r4.set_next()
        r4.matches("world")

        # r3 should have had r4's current_match values grafted onto it
        self.assertEqual(r3.expansion.current_match, "hello world")
        self.assertEqual(r3.expansion.children[0].current_match, "hello world")
        self.assertEqual(r3.expansion.children[0].children[0].current_match, "hello")
        self.assertEqual(r3.expansion.children[0].children[1].current_match, "world")

        # Check that a rule with a Repeat around a Dictation works fine
        r5 = PublicRule("test", Seq(Rep(Dict()), "world"))
        r6 = generate_rule(r5.expansion)
        r6.matches("hello")
        r6.set_next()
        r6.matches("world")
        self.assertEqual(r5.expansion.current_match, "hello world")
        self.assertEqual(r5.expansion.children[0].current_match, "hello")
        self.assertEqual(r5.expansion.children[0].child.current_match, "hello")
        self.assertEqual(r5.expansion.children[1].current_match, "world")

    def test_two_dictation(self):
        r1 = PublicRule("test", Seq(Dict(), Dict()))
        r2 = generate_rule(r1.expansion)
        r2.matches("hello")
        r2.set_next()
        r2.matches("there")
        self.assertEqual(r1.expansion.current_match, "hello there")
        self.assertEqual(r1.expansion.children[0].current_match, "hello")
        self.assertEqual(r1.expansion.children[1].current_match, "there")

    def test_complex(self):
        r1 = PublicRule("test", Seq(
            "test with", AS("lots of", "many"), Dict(), "and JSGF",
            "expansions", Dict(), Dict()))
        r2 = generate_rule(r1.expansion)
        seq = r1.expansion
        l1, alt_set, d1, l2, l3, d2, d3 = seq.children
        r2.matches("test with lots of")
        r2.set_next()
        r2.matches("dictation")
        r2.set_next()
        r2.matches("and JSGF expansions")
        r2.set_next()
        r2.matches("hopefully")
        r2.set_next()
        r2.matches("maybe")
        self.assertEqual(l1.current_match, "test with")
        self.assertEqual(alt_set.current_match, "lots of")
        self.assertEqual(d1.current_match, "dictation")
        self.assertEqual(l2.current_match, "and JSGF")
        self.assertEqual(l3.current_match, "expansions")
        self.assertEqual(d2.current_match, "hopefully")
        self.assertEqual(d3.current_match, "maybe")
        self.assertEqual(seq.current_match, "test with lots of dictation and JSGF "
                                            "expansions hopefully maybe")

    def test_graft_matches_onto_unrelated(self):
        """
        Test graft_sequence_matches using a different expansion than the original
        passed to SequenceRule's init method.
        """
        # Test using only Dictation
        r1 = generate_rule(Dict())
        r1.matches("hello world")
        e1 = Dict()
        SequenceRule.graft_sequence_matches(r1, e1)
        self.assertEqual(e1.current_match, "hello world")

        # Test using a Literal and a Dictation
        r2 = generate_rule(Seq("hello", Dict()))
        r2.matches("hello")
        r2.set_next()
        r2.matches("there")
        e2 = Seq("hello", Dict())
        SequenceRule.graft_sequence_matches(r2, e2)
        self.assertEqual(e2.current_match, "hello there")
        self.assertEqual(e2.children[0].current_match, "hello")
        self.assertEqual(e2.children[1].current_match, "there")

        # Test on an expansion that won't match
        r3 = generate_rule(Seq("hello", Dict()))
        r3.matches("hello")
        r3.set_next()
        r3.matches("there")
        e3 = Seq("hello", "world")
        SequenceRule.graft_sequence_matches(r3, e3)
        self.assertEqual(e3.current_match, None)
        self.assertEqual(e3.children[0].current_match, None)
        self.assertEqual(e3.children[1].current_match, None)


class SequenceRuleEntireMatchProperty(unittest.TestCase):
    def assert_no_entire_match(self, rule):
        self.assertEqual(
            rule.entire_match, None,
            "entire_match should be None unless all expansions match")

    def test_one_seq_expansion(self):
        r1 = generate_rule("hello world")
        self.assert_no_entire_match(r1)
        self.assertTrue(r1.matches("hello world"))
        self.assertEqual(r1.entire_match, "hello world")

        r1.restart_sequence()
        self.assertFalse(r1.matches(""))
        self.assert_no_entire_match(r1)

    def test_multiple_seq_expansions(self):
        r1 = generate_rule(Seq("hello", Dict()))
        self.assert_no_entire_match(r1)
        self.assertTrue(r1.matches("hello"))
        r1.set_next()
        self.assertTrue(r1.matches("world"))
        self.assertEqual(r1.entire_match, "hello world")

        r1.restart_sequence()
        self.assertFalse(r1.matches(""))
        self.assert_no_entire_match(r1)

    def test_restart_sequence(self):
        r1 = PublicSequenceRule("test1", Seq("hello", Dict()))
        self.assert_no_entire_match(r1)
        self.assertTrue(r1.matches("hello"))
        r1.set_next()
        self.assertTrue(r1.matches("world"))
        self.assertEqual(r1.entire_match, "hello world")
        r1.restart_sequence()
        self.assert_no_entire_match(r1)

    def test_with_normal_rule(self):
        r1 = PublicSequenceRule("test1", "hello")
        r2 = PublicRule("test2", "hello")
        self.assert_no_entire_match(r1)
        self.assertTrue(r1.matches("hello"))
        self.assertEqual(r1.entire_match, "hello")
        self.assertTrue(r2.matches(r1.entire_match))

        r3 = PublicSequenceRule("test3", Seq("hello", Dict()))
        r4 = PublicRule("test4", Seq("hello", Dict()))
        self.assert_no_entire_match(r3)
        self.assertTrue(r3.matches("hello"))
        r3.set_next()
        self.assertTrue(r3.matches("world"))
        self.assertEqual(r3.entire_match, "hello world")
        self.assertTrue(r4.matches(r3.entire_match))

    def test_with_normal_rule_complex(self):
        r1 = PublicSequenceRule(
            "test", Seq(AlternativeSet("hi", "hello"), Dict()))
        r2 = PublicRule(
            "test", Seq(AlternativeSet("hi", "hello"), Dict()))
        self.assert_no_entire_match(r1)
        self.assertTrue(r1.matches("hello"))
        r1.set_next()
        self.assertTrue(r1.matches("world"))
        self.assertEqual(r1.entire_match, "hello world")
        self.assertTrue(r2.matches(r1.entire_match))
        r1.restart_sequence()
        self.assert_no_entire_match(r1)
        self.assertTrue(r1.matches("hi"))
        r1.set_next()
        self.assertTrue(r1.matches("world"))
        self.assertEqual(r1.entire_match, "hi world")
        self.assertTrue(r2.matches(r1.entire_match))


class SequenceRuleMatchCase(unittest.TestCase):
    """
    Test the match functionality of the SequenceRule class using expansions
    containing dictation.
    """

    def assert_rule_matches_speech(self, expansion, speech_list):
        r = SequenceRule("test", True, expansion)
        i = 0
        while r.has_next_expansion:
            self.assertTrue(r.matches(speech_list[i]))
            r.set_next()  # go to the next expansion
            i += 1

    def assert_rule_does_not_match_speech(self, expansion, speech_list):
        r = SequenceRule("test", True, expansion)
        i = 0
        final_result = r.matches(speech_list[i])
        while r.has_next_expansion:
            final_result = final_result and r.matches(speech_list[i])
            if not final_result:
                break
            i += 1

        self.assertFalse(final_result)

    def test_only_dictation_match(self):
        self.assert_rule_matches_speech(Dict(), ["hello"])

    def test_no_dictation_match(self):
        self.assert_rule_does_not_match_speech(Literal("hi"), ["hello"])

    def test_dictation_in_sequence(self):
        # Dictation first
        self.assert_rule_matches_speech(Seq(Dict(), "test", "testing"),
                                        ("hello", "test testing"))

        # Dictation second
        self.assert_rule_matches_speech(Seq("test", Dict(), "testing"),
                                        ("test", "hello", "testing"))

        # Dictation last
        self.assert_rule_matches_speech(Seq("test", "testing", Dict()),
                                        ("test testing", "hello"))

    def test_multiple_dictation_in_sequence(self):
        e1 = Seq(Dict(), "test", "testing", Dict())
        self.assert_rule_matches_speech(e1,
                                        ("hello", "test testing",
                                         "world"))

        e2 = Seq("test", Dict(), "testing", Dict())
        self.assert_rule_matches_speech(e2,
                                        ("test", "hello", "testing",
                                         "world"))

        e3 = Seq("test", "testing", Dict(),
                 "more", "testing", Dict())
        self.assert_rule_matches_speech(e3,
                                        ("test testing", "hello",
                                         "more testing", "world"))

    def test_with_rule_references(self):
        r = PrivateRule("test", "test")
        e1 = Seq(Dict(), RuleRef(r))
        self.assert_rule_matches_speech(e1, (
            "hello world", "test"
        ))


class SequenceRuleRefuseMatches(unittest.TestCase):
    def setUp(self):
        self.r1 = generate_rule("test")
        self.r2 = generate_rule(Dict())
        self.r3 = generate_rule(Seq("test", Dict()))
        self.rules = [self.r1, self.r2, self.r3]

    def test_initial_values(self):
        for r in self.rules:
            self.assertFalse(
                r.refuse_matches, "refuse_matches should initially be False")

            # Test initial compile() results
            if r.current_is_dictation_only:
                expected = ""
            else:
                expected = "public <%s> = %s;" % (r.name, r.expansion.compile())

            self.assertEqual(r.compile(), expected)

    def test_restart_sequence(self):
        for r in self.rules:
            r.refuse_matches = True
            self.assertTrue(r.refuse_matches)
            r.restart_sequence()
            self.assertFalse(
                r.refuse_matches,
                "refuse_matches should now be False even if the matches method was "
                "not called"
            )

    def test_one_expansion(self):
        r1, r2 = self.r1, self.r2

        # Keep a copy of the compiled rule
        r1_compiled = "public <%s> = %s;" % (r1.name, r1.expansion.compile())

        # Test matching
        self.assertTrue(r1.matches("test"))
        self.assertTrue(r2.matches("hello"))

        msg = "refuse_matches should be True after a successful match"
        self.assertTrue(r1.refuse_matches, msg)
        self.assertTrue(r2.refuse_matches, msg)

        # Test compile()
        msg = "result from compile() should be '' after a successful match"
        self.assertEqual(r1.compile(), "", msg)
        self.assertEqual(r2.compile(), "", msg)

        msg = "matches() should not match if refuse_matches is True"
        self.assertFalse(r1.matches("test"), msg)
        self.assertFalse(r2.matches("test"), msg)

        # Test manually setting refuse_matches
        r1.refuse_matches = False
        r2.refuse_matches = False
        self.assertFalse(r1.refuse_matches)
        self.assertFalse(r2.refuse_matches)

        # Test compile()
        msg = "result from compile() should be the compiled rule if " \
              "refuse_matches is False"
        self.assertEqual(r1.compile(), r1_compiled, msg)

        # Then matches()
        msg = "matches() should match if refuse_matches is False"
        self.assertTrue(r1.matches("test"), msg)
        self.assertTrue(r2.matches("hello"), msg)

        # Test the effect of set_next()
        msg = "refuse_matches should still be True after set_next()"
        r1.set_next()  # this has no effect as r1 only has one sequence expansion
        r2.set_next()
        self.assertTrue(r1.refuse_matches, msg)
        self.assertTrue(r2.refuse_matches, msg)

        # Test restarting the sequences
        r1.restart_sequence()
        r2.restart_sequence()
        msg = "refuse_matches should be False after restart_sequence()"
        self.assertFalse(r1.refuse_matches, msg)
        self.assertFalse(r2.refuse_matches, msg)

        # Test no matches
        self.assertFalse(r1.matches("hello"))
        self.assertFalse(r2.matches(""))
        msg = "refuse_matches should be True after a failed match"
        self.assertTrue(r1.refuse_matches, msg)
        self.assertTrue(r2.refuse_matches, msg)

    def test_multiple_expansions(self):
        r3 = self.r3

        # Keep a copy of the compiled rule
        r3_compiled = "public <%s> = %s;" % (r3.name, r3.expansion.compile())

        # Test matching
        self.assertTrue(r3.matches("test"))
        self.assertTrue(r3.refuse_matches,
                        "refuse_matches should be True after a successful match")

        self.assertEqual(r3.compile(), "",
                         "compile() should be '' if refuse_matches is True")

        self.assertFalse(r3.matches("test"),
                         "matches() should not match if refuse_matches is True")

        # Test compile() output after manually setting refuse_matches
        r3.refuse_matches = False
        self.assertEqual(r3.compile(), r3_compiled,
                         "result from compile() should be the compiled rule if "
                         "refuse_matches is False")

        # Test no match on first sequence expansion
        self.assertFalse(r3.matches("hello"))
        self.assertTrue(r3.refuse_matches,
                        "refuse_matches should be True after a failed match")
        self.assertEqual(r3.compile(), "",
                         "compile() should be '' after a failed match")

        # Test the effect of set_next()
        r3.set_next()
        self.assertFalse(r3.refuse_matches,
                         "refuse_matches should be False after set_next()")
        self.assertTrue(r3.matches("hello"),
                        "matches() should match if refuse_matches is False")
        self.assertTrue(r3.refuse_matches,
                        "refuse_matches should be True after successful match")
        self.assertFalse(r3.matches("hello"),
                         "matches() should not match if called while "
                         "refuse_matches is True")

        # Test manually setting refuse_matches
        r3.refuse_matches = False
        self.assertFalse(r3.refuse_matches)
        self.assertTrue(r3.matches("hello"),
                        "matches() should match if refuse_matches is False")

        # Test restarting the sequence
        r3.restart_sequence()
        self.assertFalse(r3.refuse_matches,
                         "refuse_matches should be False after restart_sequence()")

        # Test no match on second sequence expansion
        self.assertFalse(r3.matches("hello"))
        self.assertTrue(r3.refuse_matches,
                        "refuse_matches should be True after a failed match")
        self.assertEqual(r3.compile(), "",
                         "compile() should be '' after a failed match")


class SequenceRuleCompileCase(unittest.TestCase):
    def assert_compiled_rules_equal(self, expansion, expected):
        rule = HiddenSequenceRule("test", expansion)
        compiled_rules = [rule.compile()]
        while rule.has_next_expansion:
            rule.set_next()
            compiled_rules.append(rule.compile())

        self.assertListEqual(compiled_rules, list(expected))

    def test_only_dictation_compile(self):
        self.assert_compiled_rules_equal(Dict(), [""])
        self.assert_compiled_rules_equal(Rep(Dict()), [""])
        self.assert_compiled_rules_equal(Seq(Dict()), [""])

        self.assertRaises(GrammarError,
                          SequenceRule, "test", True, Opt(Dict()))
        self.assertRaises(GrammarError,
                          SequenceRule, "test", True, AS("hi", Dict()))
        self.assertRaises(GrammarError,
                          SequenceRule, "test", True, KleeneStar(Dict()))

    def test_no_dictation_compile(self):
        self.assert_compiled_rules_equal(Literal("hi"), ["<test> = hi;"])

    def test_dictation_in_sequence(self):
        # Dictation first
        self.assert_compiled_rules_equal(Seq(Dict(), "test", "testing"), (
            "",
            "<test> = test testing;"
        ))

        # Dictation second
        self.assert_compiled_rules_equal(Seq("test", Dict(), "testing"), (
            "<test> = test;",
            "",
            "<test> = testing;"
        ))

        # Dictation last
        self.assert_compiled_rules_equal(Seq("test", "testing", Dict()), (
            "<test> = test testing;",
            ""
        ))

    def test_multiple_dictation_in_sequence(self):
        e1 = Seq(Dict(), "test", "testing", Dict())
        self.assert_compiled_rules_equal(e1, (
            "",
            "<test> = test testing;",
            ""
        ))

        e2 = Seq("test", Dict(), "testing", Dict())
        self.assert_compiled_rules_equal(e2, (
            "<test> = test;",
            "",
            "<test> = testing;",
            ""
        ))

        e3 = Seq("test", "testing", Dict(),
                 "more", "testing", Dict())
        self.assert_compiled_rules_equal(e3, (
            "<test> = test testing;",
            "",
            "<test> = more testing;",
            ""
        ))

    def test_dictation_in_alternative_set(self):
        e1 = Seq(AS(Dict(), "test", "testing"), "end")
        self.assertRaises(GrammarError, generate_rule, e1)

        e2 = Seq(AS("test", Dict(), "testing"), "end")
        self.assertRaises(GrammarError, generate_rule, e2)

        e3 = Seq(AS("test", "testing", Dict()), "end")
        self.assertRaises(GrammarError, generate_rule, e3)


class ComparisonTests(unittest.TestCase):
    def test_hashing(self):
        h = hash
        e = Seq(Dict())
        f = Seq("a", Dict())

        # Rules that are the same should generate the same hash
        self.assertEqual(h(PublicSequenceRule("a", e)),
                         h(PublicSequenceRule("a", e.copy())))

        # The same hash value should be generated regardless of the expansion
        # in the sequence.
        r = PublicSequenceRule("b", f)
        value = h(r)
        r.set_next()
        self.assertEqual(value, h(r))

        # Rules with only a different type should generate the same hash value
        self.assertEqual(h(PublicSequenceRule("a", e.copy())),
                         h(SequenceRule("a", True, e.copy())))

        # Rules that are different should generate different values
        self.assertNotEqual(h(PublicSequenceRule("a", e.copy())),
                            h(HiddenSequenceRule("a", e.copy())))
        self.assertNotEqual(h(PublicSequenceRule("a", e.copy())),
                            h(SequenceRule("a", False, e.copy())))
        self.assertNotEqual(h(PublicSequenceRule("a", e.copy())),
                            h(PublicSequenceRule("b", e.copy())))
        self.assertNotEqual(h(PublicSequenceRule("a", e.copy())),
                            h(PublicSequenceRule("a", f.copy())))
        self.assertNotEqual(h(PublicSequenceRule("a", e.copy())),
                            h(PublicSequenceRule("b", f.copy())))

        # Test that a normal Rule with the same expansion generates the same
        # hash as a SequenceRule.
        self.assertEqual(h(PublicRule("b", f.copy())),
                         h(PublicSequenceRule("b", f.copy())))


if __name__ == '__main__':
    unittest.main()
