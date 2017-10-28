import unittest

from jsgf import *


class CurrentMatchCase(unittest.TestCase):
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
        self.assertEqual(e.children[0].current_match, "hello",
                         "current_match should still be set even if the whole "
                         "rule didn't match")
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

        self.assertFalse(r.matches("hi"))
        self.assertEqual(e.current_match, None)
        self.assertEqual(e.children[0].current_match, "hi")
        self.assertEqual(e.children[0].children[0].current_match, None)
        self.assertEqual(e.children[0].children[1].current_match, "hi")
        self.assertEqual(e.children[1].current_match, None)
        self.assertEqual(e.children[1].children[0].current_match, None)
        self.assertEqual(e.children[1].children[1].current_match, None)

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

    def test_rule_ref_back_tracing(self):
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
        self.assertEqual(e2.current_match, "hello hello")
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
        self.assertEqual(e.children[1].current_match, "there")
        self.assertEqual(e.children[0].current_match, None)

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

    def test_optional_backtrack_complex(self):
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

        self.assertTrue(r.matches("a a"))
        self.assertEqual(e.children[0].current_match, "a")
        self.assertEqual(e.children[0].child.current_match, "a")
        self.assertEqual(e.children[1].current_match, "")
        self.assertEqual(e.children[1].child.current_match, "")
        self.assertEqual(e.children[2].current_match, "a")
        self.assertEqual(e.current_match, "a a")

    def test_backtracking_complex(self):
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
