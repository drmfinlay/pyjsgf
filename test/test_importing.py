import os
import unittest

from jsgf import *


class ImportResolutionCase(unittest.TestCase):
    """ Base JSGF import resolution TestCase class. """

    @classmethod
    def setUpClass(cls):
        # Save the current working directory.
        cls.cwd = os.getcwd()

        # Check which directory we're in. CD into the 'test' directory if necessary
        # so the test grammars are importable.
        if os.path.isdir("jsgf") and os.path.isdir(os.path.join("test", "grammars")):
            os.chdir("test")
        elif not (cls.cwd.endswith("test") or os.path.isdir("grammars")):
            assert False, "tests are running from an unusual working directory"

        # Define expected file grammars here.
        class Grammars(object):
            # grammars.test1.jsgf
            test1 = Grammar("grammars.test1")
            test1.add_rules(
                Rule("X", False, "x"),
                Rule("Y", False, "y"),
                PublicRule("Z", AlternativeSet(NamedRuleRef("X"), NamedRuleRef("Y")))
            )

        cls.grammars = Grammars

    @classmethod
    def tearDownClass(cls):
        # CD back to the previous directory. This may do nothing.
        os.chdir(cls.cwd)


class ImportClassCase(ImportResolutionCase):
    """ Import class tests. """

    def test_resolve(self):
        """ Test that the Import.resolve() method works correctly. """
        import1 = Import("grammars.test1.Z")
        expected_grammar = self.grammars.test1
        Z, = expected_grammar.get_rules("Z")

        # Check that import.resolve() returns the 'Z' rule and updates the memo
        # dictionary.
        memo = {}
        self.assertEqual(import1.resolve(memo), Z)
        self.assertDictEqual(memo, {
            "grammars.test1": expected_grammar,
            "grammars.test1.Z": Z
        })

        # Test that wild card imports work correctly.
        import2 = Import("grammars.test1.*")

        # Check that import.resolve() returns all grammar rules and re-uses the
        # objects in the memo dictionary.
        grammar_parsed_by_import1 = memo["grammars.test1"]
        self.assertEqual(import2.resolve(memo), [Z])
        self.assertIs(memo["grammars.test1"], grammar_parsed_by_import1)
        self.assertDictEqual(memo, {
            "grammars.test1": expected_grammar,
            "grammars.test1.Z": Z,
            "grammars.test1.*": [Z]
        })

    def test_resolve_non_existant_grammars(self):
        """
        Test that errors are raised when resolving import statements for
        non-existent grammars.
        """
        self.assertRaises(JSGFImportError, Import("grammars.test0.*").resolve)
        self.assertRaises(JSGFImportError, Import("grammars.test0.X").resolve)

    def test_resolve_non_existant_rule(self):
        """
        Test that an error is raised when resolving an import statement for a rule
        that doesn't exist in a grammar.
        """
        self.assertRaises(JSGFImportError, Import("grammars.test1.A").resolve)

    def test_resolve_private_rules(self):
        """
        Test that an error is raised when resolving an import statement for a rule
        that exists in a grammar, but is private (visible=False).
        """
        self.assertRaises(JSGFImportError, Import("grammars.test1.X").resolve)

    def test_hash_cmp(self):
        """ Import objects with the same name are equivalent. """
        name1 = "grammars.test1.Z"
        name2 = "grammars.test1.*"
        self.assertEqual(Import(name1), Import(name1))
        self.assertEqual(hash(Import(name1)), hash(Import(name1)))
        self.assertNotEqual(Import(name1), Import(name2))
        self.assertNotEqual(hash(Import(name1)), hash(Import(name2)))
