import unittest
from jsgf import *


class BasicGrammarCase(unittest.TestCase):
    def setUp(self):
        rule2 = HiddenRule("greetWord", AlternativeSet("hello", "hi"))
        rule3 = HiddenRule("name", AlternativeSet("peter", "john", "mary",
                                                  "anna"))
        rule1 = PublicRule("greet", RequiredGrouping(RuleRef(rule2),
                                                     RuleRef(rule3)))
        self.grammar = Grammar("test")
        self.grammar.add_rules(rule1, rule2, rule3)
        self.rule1 = rule1
        self.rule2 = rule2
        self.rule3 = rule3

    def test_basic_grammar_compile(self):
        expected = "#JSGF V1.0 UTF-8 en;\n" \
                   "grammar test;\n" \
                   "public <greet> = (<greetWord> <name>);\n" \
                   "<greetWord> = (hello|hi);\n" \
                   "<name> = (peter|john|mary|anna);\n"

        compiled = self.grammar.compile_grammar(charset_name="UTF-8",
                                                language_name="en",
                                                jsgf_version="1.0")
        self.assertEqual(expected, compiled)

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

    def test_add_rules_with_taken_names(self):
        self.assertRaises(GrammarError, self.grammar.add_rule,
                          PublicRule("name", "bob"))

        self.assertRaises(GrammarError, self.grammar.add_rule,
                          HiddenRule("name", "bob"))

        rules_to_add = [HiddenRule("name", "bob"),
                        PublicRule("name", "bob")]
        self.assertRaises(GrammarError, self.grammar.add_rules,
                          *rules_to_add)


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


class RootGrammarCase(BasicGrammarCase):
    def setUp(self):
        super(RootGrammarCase, self).setUp()
        self.rule5 = HiddenRule("greetWord", AlternativeSet("hello", "hi"))
        self.rule4 = PublicRule("greet", Sequence(RuleRef(self.rule5), "there"))
        self.rule6 = PublicRule("partingPhrase", AlternativeSet("goodbye", "see you"))

    def test_compile(self):
        root = RootGrammar(rules=self.grammar.rules, name="root")

        expected = "#JSGF V1.0 UTF-8 en;\n" \
                   "grammar root;\n" \
                   "public <root> = (<greet>);\n" \
                   "<greet> = (<greetWord> <name>);\n" \
                   "<greetWord> = (hello|hi);\n" \
                   "<name> = (peter|john|mary|anna);\n"

        self.assertEqual(root.compile_grammar(charset_name="UTF-8", language_name="en",
                                              jsgf_version="1.0"), expected)

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

        self.assertEqual(root.compile_grammar(
            charset_name="UTF-8", language_name="en", jsgf_version="1.0"),
            expected_without)

        root.add_rule(self.rule6)

        self.assertEqual(root.compile_grammar(
            charset_name="UTF-8", language_name="en", jsgf_version="1.0"),
            expected_with)

        # Test removing the partingPhrase rule using the name
        root.remove_rule("partingPhrase")
        self.assertEqual(root.compile_grammar(
            charset_name="UTF-8", language_name="en", jsgf_version="1.0"),
            expected_without)

        # Add the rule and test removing it using the rule object
        root.add_rule(self.rule6)
        self.assertEqual(root.compile_grammar(
            charset_name="UTF-8", language_name="en", jsgf_version="1.0"),
            expected_with)

        root.remove_rule(self.rule6)
        self.assertEqual(root.compile_grammar(
            charset_name="UTF-8", language_name="en", jsgf_version="1.0"),
            expected_without)

    def test_match(self):
        # Only rule1 should match
        root = RootGrammar(rules=self.grammar.rules, name="root")
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

    def test_no_public_rules(self):
        root = RootGrammar([self.rule5, self.rule4])
        root.remove_rule("greet")
        self.assertNotIn("greet", root.rule_names)
        self.assertRaises(GrammarError, root.compile_grammar)
        self.assertFalse(root.find_matching_rules("hello"))

        root = RootGrammar([self.rule5, self.rule4])
        root.remove_rule(self.rule4)
        self.assertNotIn(self.rule4, root.rules)
        self.assertRaises(GrammarError, root.compile_grammar)
        self.assertFalse(root.find_matching_rules("hello"))

    def test_erroneous_remove_rule(self):
        root = RootGrammar(rules=[self.rule5, self.rule4], name="root")

        # Try to remove the root rule using the name and the rule object
        self.assertRaises(GrammarError, root.remove_rule, "root")
        i = root.rule_names.index("root")
        self.assertRaises(GrammarError, root.remove_rule, root.rules[i])

    def test_add_rules_with_taken_names(self):
        root = RootGrammar(rules=self.grammar.rules)
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
        # Try with duplicate rules
        self.assertRaises(GrammarError, RootGrammar,
                          [PublicRule("test", "test"),
                           PublicRule("test", "test")])

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


if __name__ == '__main__':
    unittest.main()
