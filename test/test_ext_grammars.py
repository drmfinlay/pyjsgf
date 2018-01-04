import unittest
from jsgf import *
from jsgf.ext import *


class DictationGrammarCase(unittest.TestCase):
    def test_compile_dictation_only(self):
        grammar = DictationGrammar([PublicRule("test", Dictation())])
        self.assertEqual(grammar.compile_grammar(
            charset_name="UTF-8", language_name="en", jsgf_version="1.0"),
            "", "grammar with only Dictation rules should compile to the "
                "empty string")

    def test_compile_dictation_and_others(self):
        grammar = DictationGrammar(rules=[
            PublicRule("a", Dictation()),
            PublicRule("b", "hello world")
        ])

        expected = "#JSGF V1.0 UTF-8 en;\n" \
                   "grammar root;\n" \
                   "public <root> = (<b_0>);\n" \
                   "<b_0> = hello world;\n"

        self.assertEqual(grammar.compile_grammar(
            charset_name="UTF-8", language_name="en", jsgf_version="1.0"),
            expected)

    def test_matching_dictation_and_others(self):
        grammar = DictationGrammar()
        e1 = Sequence("hello", Dictation())
        r1 = PublicRule("test", e1)
        seq_rule = SequenceRule("test_0", True, e1)
        grammar.add_rule(r1)

        matching = grammar.find_matching_rules("hello", False)
        seq_rule.matches("hello")
        self.assertListEqual(matching, [seq_rule])

        matching[0].set_next()
        seq_rule.set_next()
        matching = grammar.find_matching_rules("world")
        seq_rule.matches("world")
        self.assertListEqual(matching, [seq_rule])

    def test_add_rules_with_taken_names(self):
        r1 = PublicRule("test", Sequence("hello", Dictation()))
        grammar = DictationGrammar([r1])
        self.assertRaises(GrammarError, grammar.add_rule,
                          PublicRule("test", "hello"))

        self.assertRaises(GrammarError, grammar.add_rule,
                          HiddenRule("test", Dictation()))

        rules_to_add = [
            PublicRule("test", "hello"),
            HiddenRule("test", Dictation()),
            PublicRule("test", Sequence("hello", Dictation()))
        ]
        self.assertRaises(GrammarError, grammar.add_rules,
                          *rules_to_add)

    def test_create_grammar_with_rule_name_conflicts(self):
        # Try with duplicate rules
        self.assertRaises(GrammarError, RootGrammar,
                          [PublicRule("test", Sequence("test", Dictation())),
                           PublicRule("test", Sequence("test", Dictation()))])

        # Try with different rules
        self.assertRaises(GrammarError, RootGrammar,
                          [PublicRule("test", Sequence("testing", Dictation())),
                           PublicRule("test", Sequence("test", Dictation()))])
        self.assertRaises(GrammarError, RootGrammar,
                          [PublicRule("test", Sequence("test", Dictation())),
                           HiddenRule("test", Sequence("test", Dictation()))])
        self.assertRaises(GrammarError, RootGrammar,
                          [PublicRule("test", Sequence("testing", Dictation())),
                           HiddenRule("test", Sequence("test", Dictation()))])

    def test_add_remove_rules(self):
        grammar = DictationGrammar()
        r1 = PublicRule("test1", Dictation())
        r2 = PublicRule("test2", Sequence("test", Dictation()))
        grammar.add_rule(r1)
        grammar.add_rule(r2)
        self.assertIn(r1, grammar.rules)
        self.assertIn(r2, grammar.rules)

        # Test removing rules using names
        grammar.remove_rule("test1")
        self.assertNotIn(r1, grammar.rules)
        grammar.remove_rule("test2")
        self.assertNotIn(r2, grammar.rules)

        # Test that using add_rules has the same effect
        grammar.add_rules(r1, r2)
        self.assertIn(r1, grammar.rules)
        self.assertIn(r2, grammar.rules)

        # Test removing rules using the original rule objects
        grammar.remove_rule(r1)
        self.assertNotIn(r1, grammar.rules)
        grammar.remove_rule(r2)
        self.assertNotIn(r2, grammar.rules)

    def rearrange_rules(self):
        grammar = DictationGrammar()
        r1 = PublicRule("test1", Sequence("test", Dictation()))
        r2 = PublicRule("test2", Sequence("testing", Dictation()))
        grammar.add_rules(r1, r2)

        expected1 = "#JSGF V1.0 UTF-8 en;\n" \
                    "grammar root;\n" \
                    "public <root> = (<test1_0>|<test2_0>);\n" \
                    "<test1_0> = test;\n" \
                    "<test2_0> = testing;\n"

        self.assertEqual(grammar.compile_grammar(
            charset_name="UTF-8", language_name="en", jsgf_version="1.0"),
            expected1)

        grammar.rearrange_rules()

        self.assertEqual(grammar.compile_grammar(
            charset_name="UTF-8", language_name="en", jsgf_version="1.0"),
            expected1, "rearrange_rules() should have had no effect")

        # Note that find_matching_rules calls rearrange_rules
        grammar.find_matching_rules("test", True)

        self.assertEqual(grammar.compile_grammar(
            charset_name="UTF-8", language_name="en", jsgf_version="1.0"),
            "#JSGF V1.0 UTF-8 en;\n"
            "grammar root;\n"
            "public <root> = (<test2_0>);\n"
            "<test2_0> = testing;\n")

        grammar.find_matching_rules("testing", True)
        self.assertEqual(grammar.compile_grammar(
            charset_name="UTF-8", language_name="en", jsgf_version="1.0"),
            "")

        # Add some more rules
        r3 = PublicRule("test3", Sequence(Dictation(), "testing"))
        r4 = PublicRule("test4", Sequence(Dictation(), Dictation()))
        grammar.add_rules(r3, r4)
        self.assertEqual(grammar.compile_grammar(
            charset_name="UTF-8", language_name="en", jsgf_version="1.0"),
            "")

        grammar.find_matching_rules("hello")
        self.assertEqual(grammar.compile_grammar(
            charset_name="UTF-8", language_name="en", jsgf_version="1.0"),
            "#JSGF V1.0 UTF-8 en;\n"
            "grammar root;\n"
            "public <root> = (<test3_0>);\n"
            "<test3_0> = testing;\n")

    def test_find_matching_rules(self):
        grammar = DictationGrammar()
        grammar.add_rules(
            PublicRule("test1", Sequence("hello", Dictation())),
            PublicRule("test2", Sequence("hello", Dictation(), "world"))
        )

        self.assertEqual(
            grammar.compile_grammar(),
            "#JSGF V1.0 UTF-8 en;\ngrammar root;\n"
            "public <root> = (<test1_0>|<test2_0>);\n"
            "<test1_0> = hello;\n"
            "<test2_0> = hello;\n"
        )

        self.assertTrue(len(grammar.find_matching_rules("hello")) == 2)
        self.assertEqual(
            grammar.compile_grammar(),
            ""
        )


class DictationGrammarOriginalRule(unittest.TestCase):
    """
    Test the get_original_rule DictationGrammar method.
    """
    def test_simple(self):
        grammar = DictationGrammar()
        r1 = PublicRule("test", Dictation())
        grammar.add_rule(r1)
        matching = grammar.find_matching_rules("hello")
        self.assertTrue(len(matching) == 1)
        original = grammar.get_original_rule(matching[0])
        self.assertIs(original, r1)
        self.assertEqual(r1.expansion.current_match, "hello",
                         "original rule doesn't have the correct current_match "
                         "value")

    def test_with_two_dictation(self):
        grammar = DictationGrammar()
        r1 = PublicRule("test", Sequence(Dictation(), Dictation()))
        grammar.add_rule(r1)
        matching = grammar.find_matching_rules("hello", advance_sequence_rules=True)
        self.assertTrue(len(matching) == 1)
        original = grammar.get_original_rule(matching[0])
        self.assertIs(original, r1)
        matching = grammar.find_matching_rules("there", advance_sequence_rules=True)
        original = grammar.get_original_rule(matching[0])
        self.assertIs(original, r1)
        self.assertEqual(r1.expansion.current_match, "hello there",
                         "original rule doesn't have the correct current_match "
                         "value")


if __name__ == '__main__':
    unittest.main()
