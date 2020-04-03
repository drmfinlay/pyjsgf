import os
import unittest

from jsgf import (parse_grammar_string, Import, JSGFImportError, Grammar, Rule,
                  GrammarError, NamedRuleRef)


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
                public <W> = w;
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
        Z, W = expected_grammar.get_rules("Z", "W")
        memo = {}
        self.assertEqual(Import("grammars.test1.*").resolve(memo), [Z, W])
        self.assertDictEqual(memo, {
            "grammars.test1": expected_grammar,
            "grammars.test1.Z": Z,
            "grammars.test1.W": W,
            "grammars.test1.*": [Z, W]
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


class GrammarImportCase(ImportResolutionCase):
    """ Grammar class import resolution tests. """

    def test_resolve_imports_same_dictionary(self):
        """ Grammar.resolve_imports() returns the same dictionary passed to it. """
        memo = {}
        grammar = Grammar()
        result = grammar.resolve_imports(memo)
        self.assertIs(result, memo)

    def test_resolve_imports_self_added(self):
        """ Grammar.resolve_imports() adds the current grammar to the dictionary. """
        grammar = Grammar("test")
        self.assertDictEqual(grammar.resolve_imports(), {
            "test": grammar,
        })

    def test_resolve_imports_single(self):
        """ Grammar.resolve_imports() correctly handles importing a single rule. """
        memo = {}
        grammar = Grammar("test")
        grammar.add_import(Import("grammars.test1.Z"))
        grammar.resolve_imports(memo)
        expected_grammar = self.grammars.test1
        Z, = expected_grammar.get_rules("Z")
        self.assertDictEqual(memo, {
            "test": grammar,
            "grammars.test1": expected_grammar,
            "grammars.test1.Z": Z
        })

    def test_resolve_imports_wildcard(self):
        """ Grammar.resolve_imports() correctly handles wildcard import statements.
        """
        memo = {}
        grammar = Grammar("test")
        grammar.add_import(Import("grammars.test1.*"))
        grammar.resolve_imports(memo)
        expected_grammar = self.grammars.test1
        Z, W = expected_grammar.get_rules("Z", "W")
        self.assertDictEqual(memo, {
            "test": grammar,
            "grammars.test1": expected_grammar,
            "grammars.test1.Z": Z,
            "grammars.test1.W": W,
            "grammars.test1.*": [Z, W]
        })

    def test_resolve_imports_multiple_grammars(self):
        """ Similar import statements in multiple grammars are handled efficiently.
        """
        memo = {}
        grammar = Grammar("test")
        grammar.add_import(Import("grammars.test4.BackspaceRule"))
        grammar.add_import(Import("grammars.test5.DeleteRule"))
        grammar.resolve_imports(memo)
        self.assertIn("grammars.test4", memo)
        self.assertIn("grammars.test5", memo)
        test4 = memo["grammars.test4"]
        test5 = memo["grammars.test5"]

        # The import environments of 'test', 'test4', 'test5' and 'numbers' should be
        # the same. resolve_imports() should update the import environment of every
        # grammar present in the memo dictionary.
        test4.resolve_imports(memo)
        test5.resolve_imports(memo)
        self.assertIn("grammars.numbers", memo)
        numbers = memo["grammars.numbers"]
        expected_environment = {
            "test": grammar,
            "grammars.test4": test4,
            "grammars.test4.BackspaceRule": test4.get_rule("BackspaceRule"),
            "grammars.test5": test5,
            "grammars.test5.DeleteRule": test5.get_rule("DeleteRule"),
            "grammars.numbers": numbers,
            "grammars.numbers.1to39": numbers.get_rule("1to39"),
        }
        for grammar_ in (grammar, test4, test5, numbers):
            self.assertDictEqual(grammar_.import_environment, expected_environment)

        # The 'numbers' grammar should have only be parsed once, even though it is
        # used by two separate grammars.
        for grammar_ in (test4, test5):
            self.assertIs(grammar_.import_environment["grammars.numbers"], numbers)

    def test_resolve_imports_cycles(self):
        """ Grammars that import from one another are resolved correctly.
        """
        memo = {}
        grammar = Grammar("test")
        grammar.add_import(Import("grammars.cycle-test1.rule1"))
        grammar.add_import(Import("grammars.cycle-test2.rule2"))
        grammar.resolve_imports(memo)
        self.assertIn("grammars.cycle-test1", memo)
        self.assertIn("grammars.cycle-test2", memo)
        cycle_test1 = memo["grammars.cycle-test1"]
        cycle_test2 = memo["grammars.cycle-test2"]
        cycle_test1.resolve_imports()
        cycle_test2.resolve_imports()
        expected_environment = {
            "test": grammar,
            "grammars.cycle-test1": cycle_test1,
            "grammars.cycle-test1.rule1": cycle_test1.get_rule("rule1"),
            "grammars.cycle-test1.Y": cycle_test1.get_rule("Y"),
            "grammars.cycle-test2": cycle_test2,
            "grammars.cycle-test2.rule2": cycle_test2.get_rule("rule2"),
            "grammars.cycle-test2.X": cycle_test2.get_rule("X"),
        }
        self.assertIs(cycle_test1.import_environment["grammars.cycle-test2"],
                      cycle_test2)
        self.assertIs(cycle_test2.import_environment["grammars.cycle-test1"],
                      cycle_test1)
        for grammar_ in (cycle_test1, cycle_test2):
            self.assertDictEqual(grammar_.import_environment, expected_environment)

    def test_same_local_and_imported_rule_names(self):
        """ Local rules with the same name have precedence over imported rules. """
        grammar = Grammar("test")
        local_z = Rule("Z", True, "z")
        grammar.add_rule(local_z)
        grammar.add_import(Import("grammars.test1.Z"))
        self.assertEqual(grammar.get_rule("Z"), local_z)

    def test_ambiguous_imported_rules(self):
        """ Imported rules with the same name cannot be referenced locally. """
        grammar = Grammar("test")
        grammar.add_import(Import("grammars.test2.rule"))
        grammar.add_import(Import("grammars.test3.rule"))
        self.assertRaises(GrammarError, grammar.get_rule, "rule")

    def test_ambiguous_qualified_names(self):
        """ Imported rules with the same qualified name must be fully referenced. """
        grammar = Grammar("test")
        grammar.add_import(Import("grammars.test6.rule"))
        grammar.add_import(Import("grammars2.test6.rule"))
        self.assertRaises(GrammarError, grammar.get_rule, "rule")
        self.assertRaises(GrammarError, grammar.get_rule, "test6.rule")

        expected1 = parse_grammar_string("""
            #JSGF V1.0;
            grammar grammars.test6;
            public <rule> = test grammars one;
        """)
        expected2 = parse_grammar_string("""
            #JSGF V1.0;
            grammar grammars2.test6;
            public <rule> = test grammars two;
        """)
        self.assertEqual(grammar.get_rule("grammars.test6.rule"),
                         expected1.get_rule("rule"))
        self.assertEqual(grammar.get_rule("grammars2.test6.rule"),
                         expected2.get_rule("rule"))

    def test_fully_qualified_rule_reference(self):
        """ Fully-qualified rule references do not require import statements. """
        grammar = Grammar("test")
        fully_qualified_ref = "grammars.test1.W"
        named_ref = NamedRuleRef(fully_qualified_ref)
        rule = Rule("rule", True, named_ref)
        grammar.add_rule(rule)
        expected_rule = self.grammars.test1.get_rule("W")
        for x in range(2):
            self.assertEqual(named_ref.referenced_rule, expected_rule)
            self.assertEqual(grammar.get_rule(fully_qualified_ref), expected_rule)
            self.assertEqual(grammar.find_matching_rules("w"), [rule])

            # Check that the import statement is allowed.
            grammar.add_import(Import(fully_qualified_ref))
