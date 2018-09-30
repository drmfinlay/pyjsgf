# This Python file uses the following encoding: utf-8
# The above line is required for the MultiLingualTests class

import copy
import tempfile
import unittest

from jsgf import *
from jsgf.ext import Dictation


class BasicGrammarCase(unittest.TestCase):
    def setUp(self):
        rule2 = HiddenRule("greetWord", AlternativeSet("hello", "hi"))
        rule3 = HiddenRule("name", AlternativeSet(
            "peter", "john", "mary", "anna"))
        rule1 = PublicRule("greet", RequiredGrouping(
            RuleRef(rule2), RuleRef(rule3)))
        self.grammar = Grammar("test")
        self.grammar.add_rules(rule1, rule2, rule3)
        self.rule1 = rule1
        self.rule2 = rule2
        self.rule3 = rule3

    def test_compile(self):
        expected = "#JSGF V1.0 UTF-8 en;\n" \
                   "grammar test;\n" \
                   "public <greet> = (<greetWord> <name>);\n" \
                   "<greetWord> = (hello|hi);\n" \
                   "<name> = (peter|john|mary|anna);\n"

        compiled = self.grammar.compile()
        self.assertEqual(expected, compiled)

    def test_compile_to_file(self):
        expected = "#JSGF V1.0 UTF-8 en;\n" \
                   "grammar test;\n" \
                   "public <greet> = (<greetWord> <name>);\n" \
                   "<greetWord> = (hello|hi);\n" \
                   "<name> = (peter|john|mary|anna);\n"

        # Create a temporary testing file.
        tf = tempfile.NamedTemporaryFile()
        self.grammar.compile_to_file(tf.name)

        # Check the file contents after writing to it.
        with open(tf.name) as f:
            content = f.read()

        try:
            self.assertEqual(expected, content)
        finally:
            # Always close and remove the temp file, even if the assertion fails.
            tf.close()

    def test_remove_dependent_rule(self):
        self.assertRaises(GrammarError, self.grammar.remove_rule, "greetWord")
        self.assertRaises(GrammarError, self.grammar.remove_rule, "name")

        # Test again with the actual rule objects
        self.assertRaises(GrammarError, self.grammar.remove_rule, self.rule2)
        self.assertRaises(GrammarError, self.grammar.remove_rule, self.rule3)

        self.grammar.remove_rule("greet")
        self.assertListEqual([self.rule2, self.rule3], self.grammar.rules)

        # Add it again to test removing the rule using the object
        self.grammar.add_rule(self.rule1)
        self.assertListEqual([self.rule2, self.rule3, self.rule1],
                             self.grammar.rules)
        self.grammar.remove_rule(self.rule1)
        self.assertListEqual([self.rule2, self.rule3], self.grammar.rules)

        # Test that removing rule2 works using ignore_dependent=True
        self.grammar.add_rule(self.rule1)  # add rule1 again
        self.assertIsNone(self.grammar.remove_rule(self.rule2,
                                                   ignore_dependent=True))

    def test_add_rules_with_taken_names(self):
        self.assertRaises(GrammarError, self.grammar.add_rule,
                          PublicRule("name", "bob"))

        self.assertRaises(GrammarError, self.grammar.add_rule,
                          HiddenRule("name", "bob"))

        rules_to_add = [HiddenRule("name", "bob"),
                        PublicRule("name", "bob")]
        self.assertRaises(GrammarError, self.grammar.add_rules, *rules_to_add)

    def test_enable_disable_rule(self):
        self.grammar.disable_rule(self.rule1)
        self.assertFalse(self.rule1.active)

        self.grammar.enable_rule(self.rule1)
        self.assertTrue(self.rule1.active)

    def test_enable_disable_using_name(self):
        self.grammar.disable_rule("greetWord")
        self.assertFalse(self.rule2.active)

        self.grammar.enable_rule("greetWord")
        self.assertTrue(self.rule1.active)

    def test_enable_disable_non_existent(self):
        self.assertRaises(GrammarError, self.grammar.disable_rule, "hello")
        self.assertRaises(GrammarError, self.grammar.enable_rule, "hello")

        r = PublicRule("test", "hello")
        self.assertRaises(GrammarError, self.grammar.disable_rule, r)
        self.assertRaises(GrammarError, self.grammar.enable_rule, r)

    def test_enable_disable_using_dup_rule(self):
        """
        Test that a copy of a rule in the grammar can be used to disable or enable
        the equivalent rule in the grammar as well as the rule object passed.
        """
        r = HiddenRule("greetWord", AlternativeSet("hello", "hi"))
        self.grammar.disable_rule(r)
        self.assertFalse(r.active, "duplicate rule should be disabled")
        self.assertFalse(self.rule2.active, "rule in grammar should be disabled")

        # Test enabling it again
        self.grammar.enable_rule(r)
        self.assertTrue(r.active, "duplicate rule should be enabled again")
        self.assertTrue(self.rule2.active, "rule in grammar should be enabled")

    def test_enable_disable_compile_output(self):
        enabled_output = "#JSGF V1.0 UTF-8 en;\n" \
                         "grammar test;\n" \
                         "public <greet> = (<greetWord> <name>);\n" \
                         "<greetWord> = (hello|hi);\n" \
                         "<name> = (peter|john|mary|anna);\n"

        self.assertEqual(self.grammar.compile(), enabled_output)

        self.grammar.disable_rule(self.rule1)
        self.assertFalse(self.rule1.active)

        self.assertEqual(
            self.grammar.compile(),
            "#JSGF V1.0 UTF-8 en;\n"
            "grammar test;\n"
            "<greetWord> = (hello|hi);\n"
            "<name> = (peter|john|mary|anna);\n",
            "disabled output shouldn't have the public 'greet' rule"
        )

        self.grammar.enable_rule(self.rule1)
        self.assertTrue(self.rule1.active)
        self.assertEqual(self.grammar.compile(), enabled_output)

    def test_comparisons(self):
        self.assertEqual(Grammar(), Grammar())
        self.assertNotEqual(Grammar(name="test"), Grammar(name="test2"),
                            "grammars with different names should not be equal")
        g1 = Grammar(name="test")
        g1.add_import(Import("test2.*"))
        self.assertNotEqual(g1, Grammar(name="test"),
                            "grammars with different imports should not be equal")
        g2 = Grammar()
        g2.add_rule(PublicRule("r1", "hello"))
        g3 = Grammar()
        self.assertNotEqual(g1, g2,
                            "grammars with different names, rules and imports "
                            "should not be equal")

        self.assertEqual(g2, g2, "the same grammar should be equal with itself")
        self.assertEqual(g2, copy.copy(g2),
                         "grammars with the same rules should be equal")

        self.assertNotEqual(g2, g3, "grammars with only different rules should not "
                                    "be equal")

        # Assert that any difference in the JSGF header makes Grammar objects not
        # equal
        default = Grammar()

        def check():
            self.assertNotEqual(g3, default, "grammars with only different JSGF "
                                             "headers should not be equal")
        g3.language_name = "ru"
        check()
        g3.jsgf_version = "2.0"
        check()
        g3.charset_name = "utf-16"
        check()

        self.assertEqual(RootGrammar(name="test"), Grammar(name="test"),
                         "grammars with only different types should be equal")

    def test_links(self):
        """Expansion.rule and Rule.grammar attributes work correctly."""
        hello = Literal("hello")
        self.assertIsNone(hello.rule, "no rule will use the expansion yet")
        r = PublicRule("test", hello)
        self.assertEqual(hello.rule, r, "rule 'test' should use the expansion")
        r.expansion = "hi"
        self.assertIsNone(hello.rule, "setting r.expansion should reset "
                                      "hello.rule")

        # Test Rule.grammar
        g = Grammar(name="g")
        self.assertIsNone(r.grammar, "no grammar will be using the rule yet")

        g.add_rule(r)
        self.assertEqual(r.grammar, g, "adding r to a grammar should set r.grammar")

        g.remove_rule(r)
        self.assertIsNone(r.grammar, "remove r from its grammar should reset "
                                     "r.grammar")


class TagTests(unittest.TestCase):
    """
    Test the Grammar.find_tagged_rules method.
    """
    def test_simple(self):
        g = Grammar()
        r = Rule("r", True, "test")
        r.expansion.tag = "tag"
        g.add_rule(r)
        self.assertListEqual(g.find_tagged_rules("tag"), [r])

    def test_hidden_rule(self):
        g = Grammar()
        r = Rule("r", False, "test")
        r.expansion.tag = "tag"
        g.add_rule(r)
        self.assertListEqual(g.find_tagged_rules("tag"), [])
        self.assertListEqual(g.find_tagged_rules("tag", include_hidden=True), [r])

    def test_no_tag(self):
        g = Grammar()
        r = PublicRule("hello", "hello world")
        self.assertListEqual(g.find_tagged_rules(""), [])
        r.expansion.tag = ""
        self.assertListEqual(g.find_tagged_rules(""), [])
        self.assertListEqual(g.find_tagged_rules(" "), [])
        r.expansion.tag = " "
        self.assertListEqual(g.find_tagged_rules(" "), [])

    def test_whitespace(self):
        # Leading or trailing whitespace should be ignored by find_tagged_rules.
        g = Grammar()
        r = PublicRule("r", "test")
        r.expansion.tag = " tag  "
        g.add_rule(r)
        self.assertEqual(r.expansion.tag, "tag")
        self.assertListEqual(g.find_tagged_rules("tag"), [r])
        self.assertListEqual(g.find_tagged_rules("  tag "), [r])


class SpeechMatchCase(unittest.TestCase):
    def assert_matches(self, speech, rule):
        self.assertTrue(rule.matches(speech))

    def assert_no_match(self, speech, rule):
        self.assertFalse(rule.matches(speech))

    def test_single_rule_match(self):
        grammar = Grammar("test")
        rule = HiddenRule("greet", Sequence(
            AlternativeSet("hello", "hi"), "world"
        ))
        grammar.add_rules(rule)
        self.assert_matches("hello world", rule)
        self.assert_matches("hello world".swapcase(), rule)
        self.assert_matches("hi world", rule)
        self.assert_no_match("hey world", rule)
        self.assert_no_match("hello", rule)
        self.assert_no_match("world", rule)
        self.assert_no_match("", rule)

    def test_multi_rule_match(self):
        grammar = Grammar("test")
        rule2 = HiddenRule("greetWord", AlternativeSet("hello", "hi"))
        rule3 = HiddenRule("name", AlternativeSet("peter", "john",
                                                  "mary", "anna"))
        rule1 = PublicRule("greet",
                           RequiredGrouping(
                               RuleRef(rule2),
                               RuleRef(rule3))
                           )
        grammar.add_rules(rule1, rule2, rule3)

        # Rule 1
        self.assert_matches("hello john", rule1)
        self.assert_matches("hello john".swapcase(), rule1)
        self.assert_no_match("hello", rule1)
        self.assert_no_match("john", rule1)
        self.assert_no_match("", rule1)

        # Rule 2
        self.assert_matches("hello", rule2)
        self.assert_matches("HELLO", rule2)
        self.assert_matches("hi", rule2)
        self.assert_matches("HI", rule2)
        self.assert_no_match("", rule2)

        # Rule 3
        self.assert_matches("john", rule3)
        self.assert_no_match("", rule3)


class MultiLingualTests(unittest.TestCase):
    """
    Test that Unicode characters can be used in rule, import and grammar names
    as well as in literals and that the text can be matched.

    Cyrillic characters are used to test this functionality. There are various
    Unicode character sets, each containing an enormous number of characters, so
    it is hardly feasible to test everything. Plus, this library simply uses
    Python's Unicode support.
    """
    def test_names(self):
        """Unicode strings can be used in names and literals and can be matched."""
        grammar = Grammar(name=u"грамматика")
        self.assertEqual(grammar.name, u"грамматика")
        rule = PublicRule(u"русский", AlternativeSet(
            u"привет", u"здравствуйте", u"пожалуйста"))
        import_ = Import(u"грамматика2.*")
        self.assertEqual(import_.name, u"грамматика2.*")

        # Test matching the rule
        self.assertTrue(rule.matches(u"здравствуйте"))

        # Test matching using the grammar
        grammar.add_rule(rule)
        self.assertListEqual(grammar.find_matching_rules(u"пожалуйста"), [rule])

    def test_dictation(self):
        """Dictation Expansions match Unicode strings."""
        self.assertTrue(PublicRule(u"всё", Dictation().matches(u"это кофе")))


class VisibleRulesCase(unittest.TestCase):
    """
    Test the 'visible_rules' property of the Grammar class.
    """
    def setUp(self):
        grammar1 = Grammar("test")
        self.rule1 = HiddenRule("rule1", "Hello")
        self.rule2 = HiddenRule("rule2", "Hey")
        self.rule3 = HiddenRule("rule3", "Hi")
        grammar1.add_rules(self.rule1, self.rule2, self.rule3)
        self.grammar1 = grammar1

        grammar2 = Grammar("test2")
        self.rule4 = PublicRule("rule4", "Hello")
        self.rule5 = PublicRule("rule5", "Hey")
        self.rule6 = HiddenRule("rule6", "Hi")
        grammar2.add_rules(self.rule4, self.rule5, self.rule6)
        self.grammar2 = grammar2

    def test_none(self):
        self.assertListEqual(self.grammar1.visible_rules, [])

    def test_many(self):
        self.assertListEqual(self.grammar2.visible_rules, [self.rule4, self.rule5])


class RootGrammarCase(unittest.TestCase):
    def setUp(self):
        self.grammar = RootGrammar(name="root")
        self.rule2 = HiddenRule("greetWord", AlternativeSet("hello", "hi"))
        self.rule3 = HiddenRule("name", AlternativeSet(
            "peter", "john", "mary", "anna"))
        self.rule1 = PublicRule("greet", RequiredGrouping(
            RuleRef(self.rule2), RuleRef(self.rule3)))
        self.grammar.add_rules(self.rule1, self.rule2, self.rule3)

        self.rule5 = HiddenRule("greetWord", AlternativeSet("hello", "hi"))
        self.rule4 = PublicRule("greet", Sequence(RuleRef(self.rule5), "there"))
        self.rule6 = PublicRule("partingPhrase", AlternativeSet(
            "goodbye", "see you"))

    def test_compile(self):
        root = self.grammar
        expected = "#JSGF V1.0 UTF-8 en;\n" \
                   "grammar root;\n" \
                   "public <root> = (<greet>);\n" \
                   "<greet> = (<greetWord> <name>);\n" \
                   "<greetWord> = (hello|hi);\n" \
                   "<name> = (peter|john|mary|anna);\n"

        self.assertEqual(root.compile(), expected)

    def test_compile_to_file(self):
        root = self.grammar
        expected = "#JSGF V1.0 UTF-8 en;\n" \
                   "grammar root;\n" \
                   "public <root> = (<greet>);\n" \
                   "<greet> = (<greetWord> <name>);\n" \
                   "<greetWord> = (hello|hi);\n" \
                   "<name> = (peter|john|mary|anna);\n"

        # Create a temporary testing file.
        tf = tempfile.NamedTemporaryFile()
        root.compile_to_file(tf.name)

        # Check the file contents after writing to it.
        with open(tf.name) as f:
            content = f.read()

        try:
            self.assertEqual(expected, content)
        finally:
            # Always close and remove the temp file, even if the assertion fails.
            tf.close()

    def test_compile_add_remove_rule(self):
        root = RootGrammar(rules=[self.rule5, self.rule4], name="root")

        expected_without = "#JSGF V1.0 UTF-8 en;\n" \
                           "grammar root;\n" \
                           "public <root> = (<greet>);\n" \
                           "<greetWord> = (hello|hi);\n" \
                           "<greet> = <greetWord> there;\n"

        expected_with = "#JSGF V1.0 UTF-8 en;\n" \
                        "grammar root;\n" \
                        "public <root> = (<greet>|<partingPhrase>);\n" \
                        "<greetWord> = (hello|hi);\n" \
                        "<greet> = <greetWord> there;\n" \
                        "<partingPhrase> = (goodbye|see you);\n"

        self.assertEqual(root.compile(), expected_without)

        root.add_rule(self.rule6)
        self.assertEqual(root.compile(), expected_with)

        # Test removing the partingPhrase rule using the name
        root.remove_rule("partingPhrase")
        self.assertEqual(root.compile(), expected_without)

        # Add the rule and test removing it using the rule object
        root.add_rule(self.rule6)
        self.assertEqual(root.compile(), expected_with)

        root.remove_rule(self.rule6)
        self.assertEqual(root.compile(), expected_without)

    def test_match(self):
        # Only rule1 should match
        root = self.grammar
        self.assertListEqual(root.find_matching_rules("Hello John"), [self.rule1])
        self.assertListEqual(root.find_matching_rules("HELLO mary"), [self.rule1])
        self.assertListEqual(root.find_matching_rules("hello ANNA"), [self.rule1])

    def test_match_add_remove(self):
        root = RootGrammar(rules=[self.rule5, self.rule4], name="root")
        self.assertListEqual(root.find_matching_rules("Hello there"), [self.rule4])
        self.assertListEqual(root.find_matching_rules("Hi there"), [self.rule4])

        # Add a rule
        root.add_rule(self.rule6)
        self.assertListEqual(root.find_matching_rules("Goodbye"), [self.rule6])
        self.assertListEqual(root.find_matching_rules("See you"), [self.rule6])

        # Remove it and test again
        root.remove_rule("partingPhrase")
        self.assertListEqual(root.find_matching_rules("Goodbye"), [])
        self.assertListEqual(root.find_matching_rules("See you"), [])

        # Test again using the remove_rule(rule object) instead
        root.add_rule(self.rule6)
        self.assertListEqual(root.find_matching_rules("Goodbye"), [self.rule6])
        self.assertListEqual(root.find_matching_rules("See you"), [self.rule6])
        root.remove_rule(self.rule6)
        self.assertListEqual(root.find_matching_rules("Goodbye"), [])
        self.assertListEqual(root.find_matching_rules("See you"), [])

    def test_add_rules_with_taken_names(self):
        root = self.grammar
        self.assertRaises(GrammarError, root.add_rule,
                          PublicRule("name", "bob"))

        self.assertRaises(GrammarError, root.add_rule,
                          HiddenRule("name", "bob"))

        rules_to_add = [HiddenRule("name", "bob"),
                        PublicRule("name", "bob")]
        self.assertRaises(GrammarError, root.add_rules,
                          *rules_to_add)

        # Test if adding a rule with the name 'root' raises an error
        self.assertRaises(GrammarError, root.add_rule, PublicRule("root", "test"))

    def test_create_grammar_with_rule_name_conflicts(self):
        # Try with duplicate rules (should fail silently)
        g = RootGrammar()
        r = PublicRule("test", "test")
        g.add_rule(r)
        self.assertListEqual(g.rules, [r])
        g.add_rule(PublicRule("test", "test"))
        self.assertListEqual(g.rules, [r])

        # Try with slightly different rules
        self.assertRaises(GrammarError, RootGrammar,
                          [PublicRule("test", "testing"),
                           PublicRule("test", "test")])
        self.assertRaises(GrammarError, RootGrammar,
                          [PublicRule("test", "test"),
                           HiddenRule("test", "test")])
        self.assertRaises(GrammarError, RootGrammar,
                          [PublicRule("test", "testing"),
                           HiddenRule("test", "test")])

    def test_enable_disable_rule(self):
        self.grammar.disable_rule(self.rule1)
        self.assertFalse(self.rule1.active)

        self.grammar.enable_rule(self.rule1)
        self.assertTrue(self.rule1.active)

    def test_enable_disable_using_name(self):
        self.grammar.disable_rule("greetWord")
        self.assertFalse(self.rule2.active)

        self.grammar.enable_rule("greetWord")
        self.assertTrue(self.rule2.active)

    def test_enable_disable_non_existent(self):
        self.assertRaises(GrammarError, self.grammar.disable_rule, "hello")
        self.assertRaises(GrammarError, self.grammar.enable_rule, "hello")

        r = PublicRule("test", "hello")
        self.assertRaises(GrammarError, self.grammar.disable_rule, r)
        self.assertRaises(GrammarError, self.grammar.enable_rule, r)

    def test_enable_disable_using_dup_rule(self):
        """
        Test that a copy of a rule in the grammar can be used to disable or enable
        the equivalent rule in the grammar as well as the rule object passed.
        """
        r = HiddenRule("greetWord", AlternativeSet("hello", "hi"))
        self.assertTrue(self.rule2.active)
        self.grammar.disable_rule(r)
        self.assertFalse(r.active, "duplicate rule should be disabled")
        self.assertFalse(self.rule2.active, "original rule should be disabled")

        # Test enabling it again
        self.grammar.enable_rule(r)
        self.assertTrue(r.active, "duplicate rule should be enabled again")
        self.assertTrue(self.rule2.active, "original rule should be enabled")

    def test_enable_disable_compile_output(self):
        enabled_output = "#JSGF V1.0 UTF-8 en;\n" \
                         "grammar root;\n" \
                         "public <root> = (<greet>);\n" \
                         "<greet> = (<greetWord> <name>);\n" \
                         "<greetWord> = (hello|hi);\n" \
                         "<name> = (peter|john|mary|anna);\n"

        self.assertEqual(self.grammar.compile(), enabled_output)

        self.grammar.disable_rule(self.rule1)
        self.assertFalse(self.rule1.active)

        self.assertEqual(
            self.grammar.compile(),
            "#JSGF V1.0 UTF-8 en;\n"
            "grammar root;\n",
            "disabled output shouldn't have the originally public 'greet' rule"
        )

        self.grammar.enable_rule(self.rule1)
        self.assertTrue(self.rule1.active)
        self.assertEqual(self.grammar.compile(), enabled_output)

        # Add another public rule and test again
        self.grammar.add_rule(PublicRule("test", "testing"))
        self.grammar.disable_rule(self.rule1)
        self.assertFalse(self.rule1.active)
        self.assertEqual(
            self.grammar.compile(),
            "#JSGF V1.0 UTF-8 en;\n"
            "grammar root;\n"
            "public <root> = (<test>);\n"
            "<greetWord> = (hello|hi);\n"
            "<name> = (peter|john|mary|anna);\n"
            "<test> = testing;\n",
            "disabled output should have the originally public 'test' rule"
        )


if __name__ == '__main__':
    unittest.main()
