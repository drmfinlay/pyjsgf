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

        # Parse test file grammars.
        class Grammars(object):
            test1 = parse_grammar_string("""
                #JSGF V1.0;
                grammar grammars.test1;
                <X> = x;
                <Y> = y;
                public <Z> = <X>|<Y>;
            """)

        cls.grammars = Grammars

    @classmethod
    def tearDownClass(cls):
        # CD back to the previous directory. This may do nothing.
        os.chdir(cls.cwd)


class ImportClassCase(ImportResolutionCase):
    """ Import class tests. """

    def test_resolve_single(self):
        """ Import.resolve() correctly handles importing single rules. """
        # Check that import.resolve() returns the 'Z' rule and updates the memo
        # dictionary.
        expected_grammar = self.grammars.test1
        Z, = expected_grammar.get_rules("Z")
        memo = {}
        self.assertEqual(Import("grammars.test1.Z").resolve(memo), Z)
        self.assertDictEqual(memo, {
            "grammars.test1": expected_grammar,
            "grammars.test1.Z": Z
        })

    def test_resolve_wildcard(self):
        """ Import.resolve() correctly handles wildcard import statements. """
        expected_grammar = self.grammars.test1
        Z, = expected_grammar.get_rules("Z")
        memo = {}
        self.assertEqual(Import("grammars.test1.*").resolve(memo), [Z])
        self.assertDictEqual(memo, {
            "grammars.test1": expected_grammar,
            "grammars.test1.Z": Z,
            "grammars.test1.*": [Z]
        })

    def test_resolve_memo_dictionary_reused(self):
        """ Import.resolve() reuses objects in the memo dictionary. """
        memo = {}
        Import("grammars.test1.Z").resolve(memo)
        import1_grammar = memo["grammars.test1"]
        import1_z = memo["grammars.test1.Z"]
        self.assertIs(Import("grammars.test1.Z").resolve(memo),
                      import1_z)
        self.assertIs(memo["grammars.test1"], import1_grammar)

    def test_resolve_non_existant_grammars(self):
        """ Resolving import statements for non-existent grammars raises errors. """
        self.assertRaises(JSGFImportError, Import("grammars.test0.*").resolve)
        self.assertRaises(JSGFImportError, Import("grammars.test0.X").resolve)

    def test_resolve_non_existant_rule(self):
        """ Resolving import statements for non-existent grammar rules raises errors.
        """
        self.assertRaises(JSGFImportError, Import("grammars.test1.A").resolve)

    def test_resolve_private_rules(self):
        """ Resolving import statements for private grammar rules raises errors. """
        self.assertRaises(JSGFImportError, Import("grammars.test1.X").resolve)

    def test_hash_cmp(self):
        """ Import objects with the same name are equivalent. """
        name1 = "grammars.test1.Z"
        name2 = "grammars.test1.*"
        self.assertEqual(Import(name1), Import(name1))
        self.assertEqual(hash(Import(name1)), hash(Import(name1)))
        self.assertNotEqual(Import(name1), Import(name2))
        self.assertNotEqual(hash(Import(name1)), hash(Import(name2)))
