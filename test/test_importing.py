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
        def _file_ext_grammars(grammar_name, *exts):
            return [parse_grammar_string("""
                #JSGF V1.0;
                grammar {};
                public <rule> = test {};
            """.format(grammar_name, ext)) for ext in exts]

        class Grammars(object):
            test1 = parse_grammar_string("""
                #JSGF V1.0;
                grammar grammars.test1;
                <X> = x;
                <Y> = y;
                public <Z> = <X>|<Y>;
            """)

            test2jsgf, test2jgram, test2jgrammar = _file_ext_grammars(
                "grammars.test2", "jsgf", "jgram", "jgrammar")
            test3jsgf, test3jgram, test3jgrammar = _file_ext_grammars(
                "grammars.test3", "jsgf", "jgram", "jgrammar")

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

    def test_resolve_sub_directory_import(self):
        """ Import.resolve() parses grammar files from sub-directories. """
        memo = {}
        Import("grammars.test1.Z").resolve(memo)
        self.assertEqual(memo["grammars.test1"], self.grammars.test1)

    def test_resolve_working_directory_import(self):
        """ Import.resolve() parses grammar files from the working directory. """
        memo = {}
        Import("grammars.test2.rule").resolve(memo)
        self.assertEqual(memo["grammars.test2"], self.grammars.test2jsgf)

    def test_resolve_file_exts_non_existant(self):
        """ Import.resolve() only parses grammar files with matching file extensions.
        """
        # test1 is defined in a .jsgf file, so excluding that extension when
        # resolving an import statement for it should raise an error.
        self.assertRaises(JSGFImportError, Import("grammars.test1.Z").resolve,
                          file_exts=[".jgram"])

        # test2 is effectively defined in 3 separate files. Specifying no extensions
        # when resolving an import statement for it should raise an error.
        self.assertRaises(JSGFImportError, Import("grammars.test2.rule").resolve,
                          file_exts=[])

    def test_resolve_file_exts_ordering(self):
        """ Import.resolve() checks against given file extensions in order.
        """
        exts_grammars = {(".jsgf", ".jgram", ".jgrammar"): self.grammars.test3jsgf,
                         (".jgram", ".jgrammar"): self.grammars.test3jgram,
                         (".jgrammar",): self.grammars.test3jgrammar}
        memo = {}
        for exts, grammar in exts_grammars.items():
            Import("grammars.test3.rule").resolve(memo, exts)
            self.assertEqual(memo["grammars.test3"], grammar)
            memo.clear()

    def test_resolve_file_exts_without_dots(self):
        """ File extensions passed to Import.resolve() are given leading dots.
        """
        memo = {}
        Import("grammars.test3.rule").resolve(memo, ["jgrammar"])
        self.assertEqual(memo["grammars.test3"], self.grammars.test3jgrammar)

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
