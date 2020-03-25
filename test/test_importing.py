import os
import unittest

from jsgf import *


class ImportResolutionCase(unittest.TestCase):
    """ Tests related to JSGF import resolution. """

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

    def test_import_resolve(self):
        """ Test that the Import.resolve() method works correctly. """
        import1 = Import("grammars.test1.X")
        expected_grammar = self.grammars.test1
        X, Y, Z = expected_grammar.get_rules("X", "Y", "Z")

        # Check that import.resolve() returns the 'X' rule and updates the memo
        # dictionary.
        memo = {}
        self.assertEqual(import1.resolve(memo), X)
        self.assertDictEqual(memo, {
            "grammars.test1": expected_grammar,
            "grammars.test1.X": X
        })

        # Test that wild card imports work correctly.
        import2 = Import("grammars.test1.*")

        # Check that import.resolve() returns all grammar rules and re-uses the
        # objects in the memo dictionary.
        grammar_parsed_by_import1 = memo["grammars.test1"]
        self.assertIs(import2.resolve(memo), grammar_parsed_by_import1)
        self.assertDictEqual(memo, {
            "grammars.test1": expected_grammar,
            "grammars.test1.X": X,
            "grammars.test1.Y": Y,
            "grammars.test1.Z": Z,
            "grammars.test1.*": expected_grammar
        })

    def test_import_resolve_non_existant_grammars(self):
        """
        Test that errors are raised when resolving import statements for
        non-existent grammars.
        """
        self.assertRaises(JSGFImportError, Import("grammars.test0.*").resolve)
        self.assertRaises(JSGFImportError, Import("grammars.test0.X").resolve)

    def test_import_resolve_non_existant_rules(self):
        """
        Test that an error is raised when an resolving import statement for a
        rule that doesn't exist in a grammar.
        """
        self.assertRaises(JSGFImportError, Import("grammars.test1.A").resolve)
