import unittest

from jsgf import *
from mock import patch


class RuleGenerators(unittest.TestCase):
    
    def test_rule(self):
        e = Sequence("don't", "crash")
        r = PublicRule("test", e)
        self.assertEqual(r.generate(), "don't crash")


class ExpansionGenerators(unittest.TestCase):
    
    def test_literal(self):
        e = Literal("hello")
        self.assertEqual(e.generate(), "hello")
        
    def test_sequence(self):
        e = Sequence("hello", "world")
        self.assertEqual(e.generate(), "hello world")
        
    def test_alt_set(self):
        i = 0
        
        def choice(lst):
            return lst[i]
        
        hello, hi = map(Literal, ["hello", "hi"])
        e = AlternativeSet(hello, hi)
        with patch("random.choice", choice):
            self.assertEqual(e.generate(), "hello")
            i += 1
            self.assertEqual(e.generate(), "hi")
    
    def test_rule_ref(self):
        e1 = Sequence("bob")
        person = PrivateRule("person", e1)
        e2 = Sequence("hi", RuleRef(person))
        self.assertEqual(e2.generate(), "hi bob")
        
    def test_optional(self):
        i = 0
    
        def choice(lst):
            return lst[i]
    
        e = Sequence("hello", OptionalGrouping("there"))
        with patch("random.choice", choice):
            self.assertEqual(e.generate(), "hello there")
            i += 1
            self.assertEqual(e.generate(), "hello")

    def test_repeat(self):
        e = Repeat("hello")
        with patch("random.random", return_value=0) as mocked_random:
            mocked_random.return_value = .5
            self.assertEqual(e.generate(), "hello hello")
            mocked_random.return_value = .12345
            self.assertEqual(e.generate(), "hello hello hello hello")

        indices = [1, 0, 1, 0, 1]  # for five choices
        
        def choice(lst):
            i = indices.pop(0)
            return lst[i]

        e = Repeat(AlternativeSet("hello", "hi"))
        with patch("random.random", return_value=0) as mocked_random:
            with patch("random.choice", choice):
                mocked_random.return_value = .5
                self.assertEqual(e.generate(), "hi hello")
                mocked_random.return_value = .25
                self.assertEqual(e.generate(), "hi hello hi")

    def test_kleene_star(self):
        e = KleeneStar("hello")
        with patch("random.random", return_value=0) as mocked_random:
            mocked_random.return_value = .5
            self.assertEqual(e.generate(), "hello")
            mocked_random.return_value = .12345
            self.assertEqual(e.generate(), "hello hello hello")
            mocked_random.return_value = .786
            self.assertEqual(e.generate(), "")

        indices = [1, 0, 1]  # for three choices

        def choice(lst):
            i = indices.pop(0)
            return lst[i]

        e = KleeneStar(AlternativeSet("hello", "hi"))
        with patch("random.random", return_value=0) as mocked_random:
            with patch("random.choice", choice):
                mocked_random.return_value = .5
                self.assertEqual(e.generate(), "hi")
                mocked_random.return_value = .25
                self.assertEqual(e.generate(), "hello hi")
