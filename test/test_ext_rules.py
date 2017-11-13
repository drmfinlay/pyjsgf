import unittest

from jsgf.ext.rules import *

# Create shorthand aliases for some expansions as they're used here A LOT
Seq = Sequence
Opt = OptionalGrouping
Dict = Dictation
AS = AlternativeSet
Rep = Repeat


class SequenceRulePropertiesCase(unittest.TestCase):
    def test_one_expansion(self):
        r1 = PublicSequenceRule("test", Dict())
        r2 = PublicSequenceRule("test", Literal("test"))

        self.assertTrue(r1.current_is_dictation_only)
        self.assertFalse(r2.current_is_dictation_only)

    def test_dictation_and_literal(self):
        rule = SequenceRule("test", True, Seq("hello", Dict()))
        self.assertFalse(rule.current_is_dictation_only)

        # Move to the next expansion in the sequence
        self.assertTrue(rule.matches("hello"))
        rule.set_next()
        self.assertTrue(rule.current_is_dictation_only)

    def test_complex(self):
        e1 = Seq(Dict(), Dict())
        r1 = PublicSequenceRule("test", e1)
        self.assertTrue(r1.current_is_dictation_only)
        self.assertTrue(r1.matches("hello"))

        # Go to the next expansion
        r1.set_next()
        self.assertTrue(r1.current_is_dictation_only)

    def test_next_in_sequence_methods(self):
        r1 = PublicSequenceRule("test", Seq("hello", Dict()))
        self.assertTrue(r1.has_next_expansion)
        r1.set_next()
        self.assertFalse(r1.has_next_expansion)
        r1.set_next()
        self.assertFalse(r1.has_next_expansion)

        # Check that set_next raises an IndexError if called too much
        self.assertRaises(IndexError, r1.set_next())


class SequenceRuleGraftMatchMethods(unittest.TestCase):
    def test_simple(self):
        r1 = PublicRule("test", Dict())
        r2 = PublicSequenceRule("test", r1.expansion)
        r2.matches("hello world")
        SequenceRule.graft_sequence_matches(r2, r1.expansion)
        self.assertEqual(r1.expansion.current_match, "hello world")

        r3 = PublicRule("test", Seq("hello", Dict()))
        r4 = PublicSequenceRule("test", r3.expansion)
        r4.matches("hello")
        r4.set_next()
        r4.matches("there")
        SequenceRule.graft_sequence_matches(r4, r3.expansion)
        self.assertEqual(r3.expansion.current_match, "hello there")

    def test_two_dictation(self):
        r1 = PublicRule("test", Seq(Dict(), Dict()))
        r2 = PublicSequenceRule("test", r1.expansion)
        r2.matches("hello")
        r2.set_next()
        r2.matches("there")
        SequenceRule.graft_sequence_matches(r2, r1.expansion)
        self.assertEqual(r1.expansion.current_match, "hello there")
        self.assertEqual(r1.expansion.children[0].current_match, "hello")
        self.assertEqual(r1.expansion.children[1].current_match, "there")

    def test_complex(self):
        r1 = PublicRule("test", Seq(
            "test with", AS("lots of", "many"), Dict(), "and JSGF",
            "expansions", Dict(), Dict()))
        r2 = PublicSequenceRule("test", r1.expansion)
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
        SequenceRule.graft_sequence_matches(r2, r1.expansion)
        self.assertEqual(l1.current_match, "test with")
        self.assertEqual(alt_set.current_match, "lots of")
        self.assertEqual(d1.current_match, "dictation")
        self.assertEqual(l2.current_match, "and jsgf")
        self.assertEqual(l3.current_match, "expansions")
        self.assertEqual(d2.current_match, "hopefully")
        self.assertEqual(d3.current_match, "maybe")
        self.assertEqual(seq.current_match, "test with lots of dictation and jsgf "
                                            "expansions hopefully maybe")


class SequenceRuleEntireMatchProperty(unittest.TestCase):
    def assert_no_entire_match(self, rule):
        self.assertEqual(
            rule.entire_match, None,
            "entire_match should be None unless all expansions match")

    def test_one_seq_expansion(self):
        r1 = PublicSequenceRule("test", "hello world")
        self.assert_no_entire_match(r1)
        self.assertTrue(r1.matches("hello world"))
        self.assertEqual(r1.entire_match, "hello world")

        self.assertFalse(r1.matches(""))
        self.assert_no_entire_match(r1)

    def test_multiple_seq_expansions(self):
        r1 = PublicSequenceRule("test", Seq("hello", Dict()))
        self.assert_no_entire_match(r1)
        self.assertTrue(r1.matches("hello"))
        r1.set_next()
        self.assertTrue(r1.matches("world"))
        self.assertEqual(r1.entire_match, "hello world")

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
        r = HiddenRule("test", "test")
        e1 = Seq(Dict(), RuleRef(r))
        self.assert_rule_matches_speech(e1, (
            "hello world", "test"
        ))


class SequenceRuleCompileCase(unittest.TestCase):
    def assert_compiled_rules_equal(self, expansion, expected):
        rule = HiddenSequenceRule("test", expansion)
        compiled_rules = [rule.compile()]
        while rule.has_next_expansion:
            rule.set_next()
            compiled_rules.append(rule.compile())

        self.assertItemsEqual(compiled_rules, expected)

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
        self.assert_compiled_rules_equal(Literal("hi"), ["<test_0> = hi;"])

    def test_dictation_in_sequence(self):
        # Dictation first
        self.assert_compiled_rules_equal(Seq(Dict(), "test", "testing"), (
            "",
            "<test_1> = test testing;"
        ))

        # Dictation second
        self.assert_compiled_rules_equal(Seq("test", Dict(), "testing"), (
            "<test_0> = test;",
            "",
            "<test_2> = testing;"
        ))

        # Dictation last
        self.assert_compiled_rules_equal(Seq("test", "testing", Dict()), (
            "<test_0> = test testing;",
            ""
        ))

    def test_multiple_dictation_in_sequence(self):
        e1 = Seq(Dict(), "test", "testing", Dict())
        self.assert_compiled_rules_equal(e1, (
            "",
            "<test_1> = test testing;",
            ""
        ))

        e2 = Seq("test", Dict(), "testing", Dict())
        self.assert_compiled_rules_equal(e2, (
            "<test_0> = test;",
            "",
            "<test_2> = testing;",
            ""
        ))

        e3 = Seq("test", "testing", Dict(),
                 "more", "testing", Dict())
        self.assert_compiled_rules_equal(e3, (
            "<test_0> = test testing;",
            "",
            "<test_2> = more testing;",
            ""
        ))

    def test_dictation_in_alternative_set(self):
        e1 = Seq(AS(Dict(), "test", "testing"), "end")
        self.assertRaises(GrammarError, SequenceRule, "test", True, e1)

        e2 = Seq(AS("test", Dict(), "testing"), "end")
        self.assertRaises(GrammarError, SequenceRule, "test", True, e2)

        e3 = Seq(AS("test", "testing", Dict()), "end")
        self.assertRaises(GrammarError, SequenceRule, "test", True, e3)


if __name__ == '__main__':
    unittest.main()
