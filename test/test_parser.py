# encoding=utf-8

import os
import unittest
import tempfile

from pyparsing import ParseException

from jsgf import *
from jsgf.parser import parse_expansion_string, parse_rule_string


class ValidGrammarTests(unittest.TestCase):
    """
    Tests for valid_grammar function.
    """
    def assert_valid(self, s):
        self.assertTrue(valid_grammar(s))

    def assert_invalid(self, s):
        self.assertFalse(valid_grammar(s))

    def test_no_header(self):
        """Grammar strings with no header are invalid."""
        self.assert_invalid("grammar test;"
                            "public <test> = test;")

    def test_no_rules(self):
        """Grammar strings with no rule definitions are invalid."""
        self.assert_invalid("#JSGF V1.0 UTF-8 en;"
                            "grammar test;")

    def test_no_newlines(self):
        """Grammar strings delimited only by semicolons are valid."""
        self.assert_valid("#JSGF V1.0 UTF-8 en;grammar test;public <rule> = hello;")

    def test_only_newlines(self):
        """Grammar strings using newlines and no semicolons are valid."""
        self.assert_valid("#JSGF V1.0 UTF-8 en\n"
                          "grammar test\n"
                          "public <rule> = hello\n")

    def test_no_line_delimiters(self):
        """Grammars with insufficient/no line endings are invalid."""
        self.assert_invalid("#JSGF V1.0 UTF-8"
                            "en grammar test public <rule> = hello;")
        self.assert_invalid("#JSGF V1.0 UTF-8 en"
                            "grammar test; public <rule> = hello <x> <x> = world")

    def test_empty_lines(self):
        """Valid grammars with excess empty lines are still valid."""
        # With excess semicolons
        self.assert_valid("#JSGF V1.0 UTF-8 en;"
                          ";;grammar test;;public <rule> = hello;;;")

        # With excess newlines
        self.assert_valid("#JSGF V1.0 UTF-8 en\n\n"
                          "\ngrammar test\n\n"
                          "public <rule> = hello\n")

    def test_using_both(self):
        """Grammars using both newlines and semicolons as line endings are valid."""
        self.assert_valid("#JSGF V1.0 UTF-8 en;"
                          "grammar test;\n"
                          "public <rule> = hello;\n")

        # Test with inconsistency
        self.assert_valid("#JSGF V1.0 UTF-8 en;"
                          "grammar test;;\n"
                          "public <rule> = hello;\n")


class ExpansionParserTests(unittest.TestCase):
    """Test the parse_expansion_string function."""

    def test_literal_ascii(self):
        self.assertEqual(parse_expansion_string("command"), Literal("command"))
        self.assertEqual(parse_expansion_string("a literal"), Literal("a literal"))

    def test_literal_unicode(self):
        self.assertEqual(parse_expansion_string(u"комманде"), Literal(u"комманде"))

    def test_alt_set(self):
        self.assertEqual(parse_expansion_string("a|b"), AlternativeSet("a", "b"))
        self.assertEqual(parse_expansion_string("a|b|c"),
                         AlternativeSet("a", "b", "c"))

        # Also test invalid alt. sets
        self.assertRaises(ParseException, parse_expansion_string, "a|b|")

    def test_alternative_weights(self):
        # Test with three weighted alternatives are parsed correctly.
        expected = AlternativeSet("a", "b", "c")
        expected.weights = {"a": 10, "b": 5.5, "c": 20}
        self.assertEqual(parse_expansion_string("/10/ a | /5.5/ b | /20/ c"),
                         expected)

        # Test that groupings, references and sequences can also be weighted.
        alt1, alt2, alt3, alt4 = (OptionalGrouping("a"), RequiredGrouping("b"),
                                  RequiredGrouping("c d"), NamedRuleRef("test"))
        expected = AlternativeSet(alt1, alt2, alt3, alt4)
        expected.weights = {alt1: 10, alt2: 5.5, alt3: 20, alt4: 2.5}
        self.assertEqual(parse_expansion_string(
            "/10/ [a] | /5.5/ (b) | /20/ (c d) | /2.5/ <test>"
        ), expected)

    def test_invalid_alternative_weights(self):
        # Test that errors are raised if weights aren't used correctly in an
        # alt. set.
        self.assertRaises(TypeError, parse_expansion_string, "/-1/ a | /5/ b")
        self.assertRaises(ParseException, parse_expansion_string, "// a | /5/ b")
        self.assertRaises(ParseException, parse_expansion_string,
                          "/1/ a | /2/ b | // c")
        invalid_uses = [
            "[/2/ a] | /6/ b",
            "/2/ a | [/6/ b]",
            "(/2/ a) | /6/ b",
            "/2/ a | /6/ b | (/12/ c)",
            "/2/ a | (/6/ b)",
            "/2/ test",
        ]
        for s in invalid_uses:
            self.assertRaises(GrammarError, parse_expansion_string, s)

    def test_alt_set_within_sequence(self):
        self.assertEqual(
            parse_expansion_string("i (go | run) to school"),
            Sequence("i", AlternativeSet("go", "run"), "to school")
        )

    def test_alt_set_weights_and_tags(self):
        a, b = map(Literal, "ab")
        expected = AlternativeSet(a, b)
        expected.weights = {a: 10, b: 5.5}
        expected.children[0].tag = "1"
        expected.children[1].tag = "2"
        self.assertEqual(parse_expansion_string("/10/ a {1} | /5.5/ b {2}"),
                         expected)

    def test_unary_alternatives(self):
        for cls, op in [(Repeat, "+"), (KleeneStar, "*")]:
            # Test unweighted.
            expected = AlternativeSet(
                cls("a"), cls(RequiredGrouping("b c")),
                cls(RequiredGrouping(Sequence("d", OptionalGrouping("e"))))
            )
            exp_str = "a{op} | (b c){op} | (d [e]){op}".format(op=op)
            self.assertEqual(parse_expansion_string(exp_str),
                             expected)

            # Test weighted.
            alt1, alt2 = cls("a"), cls(RequiredGrouping("b c"))
            alt3 = cls(RequiredGrouping(Sequence("d", OptionalGrouping("e"))))
            expected = AlternativeSet(alt1, alt2, alt3)
            expected.weights = {alt1: 10, alt2: 5, alt3: 2}
            exp_str = "/10/ a{op} | /5/ (b c){op} | /2/ (d [e]){op}".format(op=op)
            self.assertEqual(parse_expansion_string(exp_str), expected)

    def test_optional(self):
        self.assertEqual(parse_expansion_string("[a]"), OptionalGrouping("a"))
        self.assertEqual(parse_expansion_string("([a])"),
                         RequiredGrouping(OptionalGrouping("a")))

    def test_required_grouping(self):
        self.assertEqual(parse_expansion_string("(a)"),
                         RequiredGrouping(Literal("a")))

    def test_rule_ref(self):
        self.assertEqual(parse_expansion_string("<rule>"), NamedRuleRef("rule"))

    def test_null_void_refs(self):
        self.assertEqual(parse_expansion_string("<NULL>"), NullRef())
        self.assertEqual(parse_expansion_string("<VOID>"), VoidRef())

    def test_tags(self):
        # Test with one literal.
        e = parse_expansion_string("a {tag}")
        self.assertEqual(e, Literal("a"))
        self.assertEqual(e.tag, "tag")

        # Test with two literals.
        e = parse_expansion_string("a {1} b {2}")
        self.assertEqual(e, Sequence("a", "b"))
        self.assertEqual(e.children[0].tag, "1")
        self.assertEqual(e.children[1].tag, "2")

        # Test with an alternative set.
        e = parse_expansion_string("a {1} | b {2} | c {3}")
        self.assertEqual(e, AlternativeSet("a", "b", "c"))
        self.assertEqual(e.children[0].tag, "1")
        self.assertEqual(e.children[1].tag, "2")
        self.assertEqual(e.children[2].tag, "3")

        # Test with a required grouping.
        e = parse_expansion_string("(a b) {tag}")
        self.assertEqual(e, RequiredGrouping(Literal("a b")))
        self.assertEqual(e.tag, "tag")

        # Test with an optional.
        e = parse_expansion_string("[a] {tag}")
        self.assertEqual(e, OptionalGrouping(Literal("a")))
        self.assertEqual(e.tag, "tag")

        # Test with a sequence.
        e = parse_expansion_string("(a [b]) {tag}")
        self.assertEqual(e, RequiredGrouping(Sequence("a", OptionalGrouping("b"))))
        self.assertEqual(e.tag, "tag")

        # Test with references.
        e = parse_expansion_string("<action> {tag}")
        self.assertEqual(e, NamedRuleRef("action"))
        self.assertEqual(e.tag, "tag")

    def test_invalid_tags(self):
        # Test that errors are raised when trying to tag a repeat or kleene star
        # without using parenthesises.
        self.assertRaises(GrammarError, parse_expansion_string, "test+ {tag}")
        self.assertRaises(GrammarError, parse_expansion_string, "test* {tag}")

    def test_multiple_tags(self):
        # Test that required groupings are added if using the multiple tag syntax.
        expected = RequiredGrouping(RequiredGrouping("text"))
        e = parse_expansion_string("text {tag1} {tag2} {tag3}")
        self.assertEqual(e, expected)
        self.assertEqual(e.tag, "tag3")
        self.assertEqual(e.children[0].tag, "tag2")
        self.assertEqual(e.children[0].children[0].tag, "tag1")

    def test_sequence(self):
        # A sequence with optional and required literals.
        self.assertEqual(parse_expansion_string("[please] work"),
                         Sequence(OptionalGrouping("please"), "work"))

        # A sequence with two alternative sets.
        self.assertEqual(parse_expansion_string("(a|b|c) (one|two|three)"),
                         Sequence(AlternativeSet("a", "b", "c"),
                                  AlternativeSet("one", "two", "three")))

        # A sequence with tags.
        expected = Sequence("this", RequiredGrouping("is"), "a",
                            RequiredGrouping("test"))
        result = parse_expansion_string("this (is){tag1} a (test){tag2}")
        self.assertEqual(result, expected)
        self.assertEqual(result.children[1].tag, "tag1")
        self.assertEqual(result.children[3].tag, "tag2")

        # Sequences within an alternative set.
        expected = AlternativeSet(Sequence("up", NamedRuleRef("n")),
                                  Sequence("left", NamedRuleRef("n")))
        self.assertEqual(expected, parse_expansion_string("up <n>|left <n>"))

    def test_repeat(self):
        # Test one literal
        self.assertEqual(parse_expansion_string("test+"), Repeat("test"))

        # Test a sequence of two literals, one repeating.
        self.assertEqual(parse_expansion_string("(please)+ work"),
                         Sequence(Repeat(RequiredGrouping("please")), "work"))

        # Test a sequence of three literals, one repeating.
        self.assertEqual(parse_expansion_string("a+ b [c]"),
                         Sequence(Repeat("a"), "b", OptionalGrouping("c")))

        # Sequences within a repeated alternative set.
        expected = Repeat(RequiredGrouping(AlternativeSet(
            Sequence("up", NamedRuleRef("n")),
            Sequence("left", NamedRuleRef("n")))))
        self.assertEqual(expected, parse_expansion_string("(up <n>|left <n>)+"))

    def test_kleene(self):
        # Test one literal
        self.assertEqual(parse_expansion_string("test*"), KleeneStar("test"))

        # Test a sequence of two literals, one repeating.
        self.assertEqual(parse_expansion_string("(please)* work"),
                         Sequence(KleeneStar(RequiredGrouping("please")), "work"))

        # Test a sequence of three literals, one repeating.
        self.assertEqual(parse_expansion_string("a* b [c]"),
                         Sequence(KleeneStar("a"), "b", OptionalGrouping("c")))


class GrammarParserTests(unittest.TestCase):
    def test_grammar(self):
        """ Test that a grammar is parsed correctly. """
        # Test a grammar using non-default header values, an import statement and
        # public and private rules.
        s = "#JSGF V2.0 utf-8 fr;" \
            "grammar test;" \
            "import <com.example.grammar.greet>;" \
            "public <test> = hello;" \
            "<test2> = hi;"

        expected = Grammar("test")
        expected.jsgf_version = "2.0"
        expected.charset_name = "utf-8"
        expected.language_name = "fr"
        expected.add_import(Import("com.example.grammar.greet"))
        expected.add_rules(PublicRule("test", "hello"), Rule("test2", False, "hi"))
        self.assertEqual(expected, parse_grammar_string(s))

    def test_optional_header_values(self):
        """ Grammars with and without optional header values are parsed correctly.
        """
        grammar_body = "grammar test;" \
            "import <com.example.grammar.greet>;" \
            "public <test> = <com.example.grammar.greet>;"

        expected = Grammar("test")
        expected.add_import(Import("com.example.grammar.greet"))
        expected.add_rule(
            PublicRule("test", NamedRuleRef("com.example.grammar.greet"))
        )

        self.assertEqual(
            expected, parse_grammar_string("#JSGF V1.0;" + grammar_body)
        )
        expected.language_name = None
        expected.charset_name = "utf-8"
        self.assertEqual(
            expected, parse_grammar_string("#JSGF V1.0 utf-8;" + grammar_body)
        )
        expected.charset_name = None
        expected.language_name = "en"
        self.assertEqual(
            expected, parse_grammar_string("#JSGF V1.0 en;" + grammar_body)
        )

    def test_rule_visibility(self):
        """Rule visibility is parsed correctly."""
        self.assertEqual(parse_rule_string("public <rule> = hello;"),
                         Rule("rule", True, "hello"))
        self.assertEqual(parse_rule_string("<rule> = hello;"),
                         Rule("rule", False, "hello"))

    def test_comments(self):
        """C-style comments are allowed in grammar strings."""
        # Test with an overly commented grammar string with multiple lines.
        grammar = parse_grammar_string(
            "#JSGF V1.0;\n"
            "\n"
            "// test comment.\n"
            "grammar test; /* in-line comment */\n"
            "\n"
            "import <com.example.grammar.greet>; // another in-line comment.\n"
            "/*\n"
            " * Rules are defined below "
            " * this multi-line comment.\n"
            " */\n"
            "public <rule> = hello; // one more in-line comment.\n"
            "//comment after the rule definitions.\n"
        )

        expected_grammar = Grammar("test")
        expected_grammar.add_rule(PublicRule("rule", "hello"))
        expected_grammar.add_import(Import("com.example.grammar.greet"))
        self.assertEqual(expected_grammar, grammar)

    def test_file_parsing(self):
        """Grammar files are read in and parsed correctly."""
        s = "#JSGF V2.0 UTF-16 english;" \
            "grammar test;" \
            "import <com.example.grammar.greet>;" \
            "public <test> = hello;" \
            "<test2> = hi;"

        expected = Grammar("test")
        expected.jsgf_version = "2.0"
        expected.charset_name = "UTF-16"
        expected.language_name = "english"
        expected.add_rules(PublicRule("test", "hello"), Rule("test2", False, "hi"))
        expected.add_import(Import("com.example.grammar.greet"))

        # Write the above grammar string to a temporary file.
        tf = tempfile.NamedTemporaryFile(mode="a", delete=False)
        with tf:
            tf.write(s)

        # Parse the grammar file and remove the temp file.
        grammar = parse_grammar_file(tf.name)
        os.remove(tf.name)

        # Check if the resulting grammar is correct.
        self.assertEqual(expected, grammar)


if __name__ == '__main__':
    unittest.main()
