"""
This module contains classes for compiling, importing from and matching JSpeech
Grammar Format grammars.
"""

import os

from six import string_types

from . import references
from .rules import Rule
from .errors import GrammarError, JSGFImportError


class Import(references.BaseRef):
    """
    Import objects used in grammar compilation and import resolution.

    Import names must be fully qualified. This means they must be in the reverse
    domain name format that Java packages use. Wildcards may be used to import all
    public rules in a grammar.

    The following are valid rule import names:

    * com.example.grammar.rule_name
    * grammar.rule_name
    * com.example.grammar.*
    * grammar.*

    There are two reserved rule names: *NULL* and *VOID*. These reserved names
    cannot be used as import names. You can however change the case to 'null'
    or 'void' to use them, as names are case-sensitive.
    """

    #: Default file extensions to consider during import resolution.
    grammar_file_exts = (".jsgf", ".jgram")

    def __init__(self, name):
        super(Import, self).__init__(name)

    def compile(self):
        return "import <%s>;" % self.name

    @property
    def grammar_name(self):
        """
        The full name of the grammar to import from.

        :returns: grammar name
        :rtype: str
        """
        return ".".join(self.name.split(".")[:-1])

    @property
    def wildcard_import(self):
        """
        Whether this import statement imports every grammar rule.

        :returns: bool
        :rtype: bool
        """
        return self.name.endswith(".*")

    @property
    def rule_name(self):
        """
        The name of the rule to import from the grammar.

        :returns: rule name
        :rtype: str
        """
        return self.name.split(".")[-1]

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__, self.name)

    def _get_import_grammar(self, memo, file_exts):
        """ Internal method to get the grammar from a file if necessary. """
        grammar_name = self.grammar_name
        if grammar_name in memo:
            return memo[grammar_name]

        # Import the parser function locally to avoid import cycles; this module is
        # used by the parser.
        from jsgf.parser import parse_grammar_file

        # Look for the file in the current working directory and in a
        # sub-directory based on the grammar's full name.
        result = None
        for file_ext in file_exts:
            # Add a leading dot to the file extension if necessary.
            if not file_ext.startswith("."):
                file_ext = "." + file_ext

            grammar_path1 = grammar_name + file_ext
            grammar_path2 = os.path.join(*grammar_name.split(".")) + file_ext
            if os.path.isfile(grammar_path1):
                result = parse_grammar_file(grammar_path1)
                break

            # Look for the file in sub-directories based on the grammar's full
            # name.
            elif os.path.isfile(grammar_path2):
                result = parse_grammar_file(grammar_path2)
                break

        # The grammar file doesn't exist, so raise an error.
        if result is None:
            raise JSGFImportError("The grammar file for grammar %r could not be "
                                  "found" % grammar_name)

        memo[grammar_name] = result
        return result

    def resolve(self, memo=None, file_exts=None):
        """
        Resolve this import statement and return the imported :class:`Rule`
        object(s).

        This method attempts to parse grammar files in the working directory and its
        sub-directories. If a dictionary was passed for the *memo* argument, then
        that dictionary will be updated with the parsed grammar and rules.

        Errors will be raised if the grammar could not be found and parsed, or if the
        import statement could not be resolved.

        :param memo: dictionary of import names to grammar rules
        :type memo: dict
        :param file_exts: list of grammar file extensions to check against (default:
            ``(".jsgf", ".jgram")``)
        :type file_exts: list | tuple
        :returns: imported Rule or list of Rules
        :rtype: Rule | list
        :raises: GrammarError | JSGFImportError
        """
        if memo is None:
            memo = {}

        if file_exts is None:
            file_exts = self.grammar_file_exts

        # Check if this import statement has already been resolved.
        import_name = self.name
        if import_name in memo:
            return memo[import_name]

        # Parse the grammar from its file, if it exists.
        grammar = self._get_import_grammar(memo, file_exts)

        # Add the grammar to the dictionary.
        # TODO Decide whether it is worth allowing different file and grammar names.
        grammar_name = self.grammar_name
        import_rule_name = self.rule_name
        wildcard_import = self.wildcard_import
        memo[grammar_name] = grammar
        memo[grammar.name] = grammar

        # The resolved value for wildcard import statements is a list of the
        # grammar's public rules.
        visible_rules = grammar.visible_rules
        if wildcard_import:
            memo[import_name] = visible_rules

        # If this is not a wildcard import and the grammar doesn't contain the
        # expected public rule, then raise an error.
        elif import_rule_name not in [r.name for r in visible_rules]:
            raise JSGFImportError("no public rule with name %r was found in grammar "
                                  "%r" % (import_rule_name, grammar_name))

        # Add any appropriate rules.
        for rule in visible_rules:
            if wildcard_import or rule.name == import_rule_name:
                memo[rule.fully_qualified_name] = rule
                memo["%s.%s" % (grammar_name, rule.name)] = rule

        # Return the imported rule(s).
        return memo[import_name]

    @staticmethod
    def valid(name):
        return references.import_name.matches(name)


class Grammar(references.BaseRef):
    """
    Base class for JSGF grammars.

    Grammar names can be either a qualified name with dots or a single name.
    A name is defined as a single word containing one or more alphanumeric Unicode
    characters and/or any of the following special characters: +-:;,=|/\()[]@#%!^&~$

    For example, the following are valid grammar names:
    com.example.grammar
    grammar

    There are two reserved rule names: *NULL* and *VOID*. These reserved names
    cannot be used as grammar names. You can however change the case to 'null'
    or 'void' to use them, as names are case-sensitive.
    """
    default_header_values = (
        "1.0",
        "",
        ""
    )

    def __init__(self, name="default", case_sensitive=False):
        super(Grammar, self).__init__(name)
        self._rules = []
        self._imports = []
        self._import_env = {}
        self.jsgf_version, self.charset_name, self.language_name =\
            self.default_header_values
        self._case_sensitive = case_sensitive

    @property
    def jsgf_header(self):
        """
        The JSGF header string for this grammar. By default this is::

            #JSGF V1.0;

        :returns: str
        """
        header = "#JSGF V%s" % self.jsgf_version

        # Add the character set and language name only if they are specified.
        if self.charset_name:
            header += " %s" % self.charset_name
        if self.language_name:
            header += " %s" % self.language_name

        return header + ";\n"

    @staticmethod
    def valid(name):
        return references.grammar_name.matches(name)

    @property
    def case_sensitive(self):
        """
        Case sensitivity used when matching and compiling :class:`Literal` rule
        expansions.

        Setting this property will override the ``case_sensitive`` values for each
        :class:`Rule` and :class:`Literal` expansion in the grammar or in any newly
        added grammar rules.

        :rtype: bool
        :returns: case sensitivity
        """
        return self._case_sensitive

    @case_sensitive.setter
    def case_sensitive(self, value):
        value = bool(value)
        self._case_sensitive = value
        for rule in self.rules:
            rule.case_sensitive = value

    def compile(self):
        """
        Compile this grammar's header, imports and rules into a string that can be
        recognised by a JSGF parser.

        :returns: str
        """
        result = self.jsgf_header
        result += "grammar %s;\n" % self.name

        for i in self._imports:
            result += "%s\n" % i.compile()

        for r in self._rules:
            compiled = r.compile()
            if compiled and r.active:
                result += "%s\n" % compiled

        return result

    def compile_to_file(self, file_path, compile_as_root_grammar=False):
        """
        Compile this grammar by calling ``compile`` and write the result to the
        specified file.

        :param file_path: str
        :param compile_as_root_grammar: bool
        """
        if compile_as_root_grammar:
            compiled_lines = self.compile_as_root_grammar()
        else:
            compiled_lines = self.compile()
        with open(file_path, "w+") as f:
            f.write(compiled_lines)

    def compile_grammar(self, charset_name="UTF-8", language_name="en",
                        jsgf_version="1.0"):
        """
        Compile this grammar's header, imports and rules into a string that can be
        recognised by a JSGF parser.

        This method is **deprecated**, use ``compile`` instead.

        :param charset_name:
        :param language_name:
        :param jsgf_version:
        :returns: str
        """
        self.charset_name = charset_name
        self.language_name = language_name
        self.jsgf_version = jsgf_version
        return self.compile()

    def compile_as_root_grammar(self):
        """
        Compile this grammar with one public "root" rule containing rule references
        in an alternative set to every other rule as such::

            public <root> = (<rule1>|<rule2>|..|<ruleN>);
            <rule1> = ...;
            <rule2> = ...;
            .
            .
            .
            <ruleN> = ...;

        This is useful if you are using JSGF grammars with CMU Pocket Sphinx.

        :returns: str
        """
        result = self.jsgf_header
        result += "grammar %s;\n" % self.name

        # Add imports
        for i in self._imports:
            result += "%s\n" % i.compile()

        # Get rules in the grammar that are visible and active
        visible_rules = list(filter(lambda x: x.active, self.visible_rules))

        # Return the result if there are no rules that are visible and active
        if not visible_rules:
            return result

        # Temporarily set each visible rule to not visible
        for rule in visible_rules:
            rule.visible = False

        # Compile each rule and add its name to the names list if it compiled to
        # something. Rules can compile to the empty string if they are disabled.
        names = []
        compiled_rules = ""
        for rule in self.rules:
            compiled = rule.compile()
            if compiled:
                compiled_rules += "%s\n" % compiled
            if rule in visible_rules and compiled:
                names.append(rule.name)

        # If there are names, then build the root rule and add it and the compiled
        # rules to the result.
        if names:
            refs = ["<%s>" % name for name in names]
            alt_set = "(%s)" % "|".join(refs)
            root_rule = "public <root> = %s;\n" % alt_set
            result += root_rule
            result += compiled_rules

        # Set rule visibility back to normal
        for rule in visible_rules:
            rule.visible = True

        return result

    @property
    def imports(self):
        """
        Get the imports for this grammar.

        :returns: list
        """
        return list(self._imports)

    @property
    def rules(self):
        """
        Get the rules added to this grammar.

        :returns: list
        """
        return list(self._rules)

    visible_rules = property(
        lambda self: [rule for rule in self.rules if rule.visible],
        doc="""
        The rules in this grammar which have the visible attribute set to True.

        :returns: list
        """
    )

    rule_names = property(
        lambda self: [rule.name for rule in self.rules],
        doc="""
        The rule names of each rule in this grammar.

        :returns: list
        """
    )

    import_names = property(
        lambda self: [import_.name for import_ in self._imports],
        doc="""
        The import names associated with this grammar.

        :returns: list
        """
    )

    @property
    def match_rules(self):
        """
        The rules that the ``find_matching_rules`` method will match against.

        :returns: list
        """
        return self.visible_rules

    def __str__(self):
        charset = self.charset_name if self.charset_name else "<auto>"
        language = self.language_name if self.language_name else "<auto>"
        return "Grammar(version=%s, charset=%s, language=%s, name=%s)" % (
            self.jsgf_version, charset, language, self.name
        )

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return (self.name == other.name and self.jsgf_header == other.jsgf_header
                and self.rules == other.rules and self.imports == other.imports
                and self.case_sensitive == other.case_sensitive)

    def __ne__(self, other):
        return not self.__eq__(other)

    def add_rules(self, *rules):
        """
        Add multiple rules to the grammar.

        This method will override each new rule's :py:attr:`~Rule.case_sensitive`
        value with the grammar's :py:attr:`~case_sensitive` value.

        :param rules: rules
        :raises: GrammarError
        """
        for r in rules:
            self.add_rule(r)

    def add_imports(self, *imports):
        """
        Add multiple imports to the grammar.

        :param imports: imports
        """
        for i in imports:
            self.add_import(i)

    def add_rule(self, rule):
        """
        Add a rule to the grammar.

        This method will override the new rule's :py:attr:`~Rule.case_sensitive`
        value with the grammar's :py:attr:`~case_sensitive` value.

        :param rule: Rule
        :raises: GrammarError
        """
        if not isinstance(rule, Rule):
            raise TypeError("object '%s' was not a JSGF Rule object" % rule)

        # Check if the same rule is already in the grammar.
        if rule.name in self.rule_names:
            if rule in self.rules:
                # Silently return if the rule is comparable to another in the
                # grammar.
                return
            else:
                raise GrammarError("JSGF grammars cannot have multiple rules with "
                                   "the same name")

        # Set case sensitivity.
        rule.case_sensitive = self.case_sensitive

        self._rules.append(rule)
        rule.grammar = self

    def add_import(self, _import):
        """
        Add an import statement to the grammar.

        :param _import: Import
        """
        if not isinstance(_import, Import):
            raise TypeError("object '%s' is not a JSGF Import object" % _import)

        if _import not in self._imports:
            self._imports.append(_import)

    def find_matching_rules(self, speech):
        """
        Find each visible rule in this grammar that matches the `speech` string.

        :param speech: str
        :returns: list
        """
        return [r for r in self.match_rules if r.visible and r.matches(speech)]

    def find_tagged_rules(self, tag, include_hidden=False):
        """
        Find each rule in this grammar that has the specified JSGF tag.

        :param tag: str
        :param include_hidden: whether to include hidden rules (default False).
        :returns: list
        """
        if include_hidden:
            return [r for r in self.rules if r.has_tag(tag)]
        else:
            return [r for r in self.match_rules if r.has_tag(tag)]

    @property
    def import_environment(self):
        """
        A dictionary of imported rules and their grammars that functions as the
        import environment of this grammar.

        The import environment dictionary is updated internally by the
        :meth:`resolve_imports` method.

        :rtype: dict
        :returns: dictionary of import names to grammar rules
        """
        return self._import_env

    def resolve_imports(self, memo=None, file_exts=None):
        """
        Resolve each import statement in the grammar and make the imported
        :class:`Rule` object(s) available for referencing and matching.

        This method attempts to parse grammar files in the working directory and its
        sub-directories. If a dictionary was passed for the *memo* argument, then
        that dictionary will be updated with the parsed grammars and rules.

        Errors will be raised if a grammar could not be found and parsed, or if an
        import statement could not be resolved.

        :param memo: dictionary of import names to grammar rules
        :type memo: dict
        :param file_exts: list of grammar file extensions to check against (default:
            ``(".jsgf", ".jgram")``)
        :type file_exts: list | tuple
        :returns: dictionary of import names to grammar rules
        :rtype: dict
        :raises: GrammarError | JSGFImportError
        """
        if memo is None:
            memo = self._import_env.copy()

        if file_exts is None:
            file_exts = Import.grammar_file_exts

        # Add this grammar's name to the dictionary to avoid other grammars
        # re-resolving this one unnecessarily.
        memo[self._name] = self

        # Resolve each import statement. Import.resolve() will update the memo
        # dictionary.
        for import_ in self._imports:
            import_.resolve(memo, file_exts)

        # Update the import environments of this and other grammars in the memo
        # dictionary.
        for value in memo.values():
            if isinstance(value, Grammar):
                value.import_environment.update(memo)

        return memo

    def get_rule_from_name(self, name):
        """
        Get a rule object with the specified name if one exists in the grammar or its
        imported rules.

        If ``name`` is a fully-qualified rule name, then this method will attempt to
        import it.

        :param name: str
        :returns: Rule
        :raises: GrammarError | TypeError | JSGFImportError
        """
        if not isinstance(name, string_types):
            raise TypeError("string expected, got %r instead" % name)

        if not references.optionally_qualified_name.matches(name):
            raise GrammarError("%r is not a valid JSGF reference name" % name)

        for rule in self.rules:
            if rule.name == name:
                return rule

        # No local rules matched, so resolve import statements.
        self.resolve_imports()
        import_names = self.import_names
        imported_rules = []
        for (key, value) in self.import_environment.items():
            if key not in import_names:
                continue

            # Handle single rule imports.
            if isinstance(value, Rule):
                imported_rules.append(value)

            # Handle wildcard rule imports.
            elif isinstance(value, list):
                imported_rules.extend(value)

        # Check against imported rules.
        matching_rules = []
        qualified_name = ".".join(name.split(".")[-2:])  # get only the last part
        for rule in imported_rules:
            if name == rule.name or qualified_name == rule.qualified_name:
                matching_rules.append(rule)

        # Return the matching imported rule if there is only one.
        if len(matching_rules) == 1:
            return matching_rules[0]

        # Raise an error if there are multiple matches and the name is not fully
        # qualified.
        if len(matching_rules) > 1 and name.count(".") <= 1:
            raise GrammarError("name %r is ambiguous; multiple imported rules match."
                               " Use a qualified or fully-qualified name instead."
                               % name)

        # If the name is a fully-qualified rule name, then try to resolve it.
        if name.count(".") > 0:
            import_ = Import(name)
            return import_.resolve(self._import_env)

        # No local or imported rule matched. This is an error.
        raise GrammarError("%r is not a local or imported rule in Grammar %r"
                           % (name, self.name))

    #: Alias of :meth:`get_rule_from_name`.
    get_rule = get_rule_from_name

    def get_rules_from_names(self, *names):
        """
        Get rule objects with the specified names, if they exist in the grammar.

        :param names: str
        :returns: list
        :raises: GrammarError
        """
        return [self.get_rule_from_name(name) for name in names]

    #: Alias of :meth:`get_rules_from_names`.
    get_rules = get_rules_from_names

    def remove_rule(self, rule, ignore_dependent=False):
        """
        Remove a rule from this grammar.

        :param rule: Rule object or the name of a rule in this grammar
        :param ignore_dependent: whether to check if the rule has dependent rules
        :raises: GrammarError
        """
        if not isinstance(rule, Rule):
            # Assume 'rule' is the name of a rule
            # Get the rule object with the name
            rule = self.get_rule_from_name(rule)
        elif rule not in self.rules:
            raise GrammarError("'%s' is not a rule in Grammar '%s'" % (rule, self))

        # Check if rule with name 'rule_name' is a dependency of another rule
        # in this grammar.
        if not ignore_dependent and rule.dependent_rules:
            raise GrammarError("Cannot remove rule '%s' as it is referenced by "
                               "another rule." % rule)

        self._rules.remove(rule)
        rule.grammar = None

    def enable_rule(self, rule):
        """
        Enable a rule in this grammar, allowing it to appear in the compile method
        output and to be matched with the find_matching_rules method.

        Rules are enabled by default.

        :param rule: Rule object or the name of a rule in this grammar
        :raises: GrammarError
        """
        # Handle the rule parameter
        if isinstance(rule, string_types):
            rule_name = rule
        else:
            rule_name = rule.name
            rule.enable()

        if rule_name not in self.rule_names:
            raise GrammarError("'%s' is not a rule in Grammar '%s'" % (rule, self))

        # Enable the rule
        self.get_rule_from_name(rule_name).enable()

    def disable_rule(self, rule):
        """
        Disable a rule in this grammar, preventing it from appearing in the compile
        method output or being matched with the find_matching_rules method.

        :param rule: Rule object or the name of a rule in this grammar
        :raises: GrammarError
        """
        # Handle the rule parameter
        if isinstance(rule, string_types):
            rule_name = rule
        else:
            rule_name = rule.name
            rule.disable()

        if rule_name not in self.rule_names:
            raise GrammarError("'%s' is not a rule in Grammar '%s'" % (rule, self))

        # Disable the rule
        self.get_rule_from_name(rule_name).disable()

    def remove_import(self, _import):
        """
        Remove an Import from the grammar.

        :param _import: Import
        """
        if _import in self._imports:
            self._imports.remove(_import)
        elif isinstance(_import, Import):
            raise GrammarError("%r is not an import statement in Grammar '%r'"
                               % (_import, self.name))
        else:
            raise TypeError("object '%s' is not a JSGF Import object" % _import)

    def remove_imports(self, *imports):
        """
        Remove multiple imports from the grammar.

        :param imports: imports
        """
        for i in imports:
            self.remove_import(i)


class RootGrammar(Grammar):
    """
    A grammar with one public "root" rule containing rule references in an
    alternative set to every other rule as such::

        public <root> = (<rule1>|<rule2>|..|<ruleN>);
        <rule1> = ...;
        <rule2> = ...;
        .
        .
        .
        <ruleN> = ...;

    This is useful if you are using JSGF grammars with CMU Pocket Sphinx.
    """
    def __init__(self, rules=None, name="root", case_sensitive=False):
        super(RootGrammar, self).__init__(name, case_sensitive)
        if rules:
            self.add_rules(*rules)

    def compile(self):
        """
        Compile this grammar's header, imports and rules into a string that can be
        recognised by a JSGF parser.

        This method will compile the grammar using ``compile_as_root_grammar``.

        :returns: str
        """
        return self.compile_as_root_grammar()

    def add_rule(self, rule):
        if rule.name == "root":
            raise GrammarError("cannot add rule with name 'root' to RootGrammar")

        super(RootGrammar, self).add_rule(rule)

    def compile_to_file(self, file_path, compile_as_root_grammar=True):
        super(RootGrammar, self).compile_to_file(file_path, compile_as_root_grammar)
