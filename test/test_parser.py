import unittest

from jsgf import *


class ValidGrammarTests(unittest.TestCase):
    """
    Tests for valid_grammar function.
    """
    def assert_valid(self, s):
        self.assertTrue(valid_grammar(s, False))

    def assert_invalid(self, s):
        self.assertFalse(valid_grammar(s, False))

    def test_no_rules(self):
        """Grammar strings with no rule definitions are invalid."""
        self.assert_invalid("grammar test;")

    def test_no_newlines(self):
        """Grammar strings delimited only by semicolons are valid."""
        self.assert_valid("grammar test;public <rule> = hello;")

    def test_only_newlines(self):
        """Grammar strings using newlines and no semicolons are valid."""
        self.assert_valid("grammar test\n"
                          "public <rule> = hello\n")

    def test_no_line_delimiters(self):
        """Grammars with insufficient/no line endings are invalid."""
        self.assert_invalid("grammar test public <rule> = hello;")
        self.assert_invalid("grammar test; public <rule> = hello <x> <x> = world")

    def test_empty_lines(self):
        """Valid grammars with excess empty lines are still valid."""
        # With excess semicolons
        self.assert_valid(";;;grammar test;;public <rule> = hello;;;")

        # With excess newlines
        self.assert_valid("#JSGF V1.0 UTF-8 en\n\n"
                          "\ngrammar test\n\n"
                          "public <rule> = hello\n")

    def test_using_both(self):
        """Grammars using both newlines and semicolons as line endings are valid."""
        self.assert_valid("grammar test;\n"
                          "public <rule> = hello;\n")

        # Test with inconsistency
        self.assert_valid("#JSGF V1.0 UTF-8 en;"
                          "grammar test;;\n"
                          "public <rule> = hello;\n")


class ExpansionParserTests(unittest.TestCase):
    """Test the parse_expansion_string method"""
    pass


class GrammarParserTests(unittest.TestCase):
    def test_parse_one(self):
        # Test the header using non-default values
        header = '#JSGF V2.0 UTF-16 english;grammar test;public <test> = hello\n'
        expected = Grammar("test")
        expected.jsgf_version = "2.0"
        expected.charset_name = "UTF-16"
        expected.language_name = "english"

        grammar_list = parse_grammar_string(header)
        self.assertEqual(
            len(grammar_list), 1, "only one Grammar should be returned"
        )
        grammar = grammar_list[0]
        self.assertEqual(grammar.jsgf_version, "2.0")
        self.assertEqual(grammar.charset_name, "UTF-16")
        self.assertEqual(grammar.language_name, "english")

        # Test that the 'test' rule is in the grammar
        self.assertIn(PublicRule("test", "hello"), grammar.rules)

    def test_out_of_scope_import(self):
        """Parsing grammars importing non-existent rules raises GrammarErrors."""
        self.assertRaises(GrammarError, parse_grammar_string,
                          "#JSGF V1.0 UTF-8 en;"
                          "grammar test;"
                          "import <existentialCrisis>;"
                          "public <rule> = test;")

        self.assertRaises(GrammarError, parse_grammar_string,
                          "#JSGF V1.0 UTF-8 en;"
                          "grammar test;"
                          "import <existentialCrisis.singleRule>;"
                          "public <rule> = test;")

        self.assertRaises(GrammarError, parse_grammar_string,
                          "#JSGF V1.0 UTF-8 en;"
                          "grammar test;"
                          "import <existentialCrisis.*>;"
                          "public <rule> = test;")

    def test_importing(self):
        """Test that importing works"""
        # Define a simple grammar to import
        g1 = Grammar("greetings")
        name = HiddenRule("name", AlternativeSet("alice", "bob", "mallory"))
        greet = PublicRule("greet", Sequence("hello", RuleRef(name)))
        g1.add_rules(greet, name)

        # Parse a grammar string using the 'greetings' grammar
        grammar_list = parse_grammar_string(
            "#JSGF V1.0 UTF-8 en;"
            "grammar test;"
            "import <greetings.*>;"
            "public <rule> = <greetings.greet>|hello there",
            imports=[g1]
        )

        expected_grammar = Grammar()
        expected_grammar.add_rule(PublicRule("rule", RuleRef(greet)))
        expected_grammar.add_import(Import("greetings"))

        self.assertListEqual(grammar_list, [
            g1
        ])
        expected_rules = []
        expected_rules.extend(g1.rules)
        # TODO Change Rule classes to store a reference to their grammars
        # TODO Change RuleRef to use <grammar_name>.<rule_name> if rules cross-reference between grammars
        expected_rules.append(PublicRule("rule", RuleRef(name)))
        self.assertListEqual(grammar_list[0].rules,
                             expected_rules)


if __name__ == '__main__':
    unittest.main()
