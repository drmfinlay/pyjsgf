import unittest
import random

from jsgf import *


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
        random.seed(123)
        hello, hi = map(Literal, ["hello", "hi"])
        e = AlternativeSet(hello, hi)
        self.assertEqual(e.generate(), "hello")
        self.assertEqual(e.generate(), "hi")
    
    def test_rule_ref(self):
        e1 = Sequence("bob")
        person = HiddenRule("person", e1)
        e2 = Sequence("hi", RuleRef(person))
        self.assertEqual(e2.generate(), "hi bob")
        
    def test_optional(self):
        random.seed(123)
        e = Sequence("hello", OptionalGrouping("there"))
        self.assertEqual(e.generate(), "hello there")
        self.assertEqual(e.generate(), "hello")

    def test_repeat(self):
        random.seed(123)
        e = Repeat("hello")
        self.assertEqual(e.generate(), "hello hello hello hello hello")
        self.assertEqual(e.generate(), "hello hello hello hello")
        self.assertEqual(e.generate(), "hello hello")
        
    def test_kleene_star(self):
        random.seed(123)
        e = KleeneStar("hello")
        self.assertEqual(e.generate(), "hello hello hello hello")
        self.assertEqual(e.generate(), "hello hello hello")
        self.assertEqual(e.generate(), "hello")
        self.assertEqual(e.generate(), "hello hello hello")
        self.assertEqual(e.generate(), "")
