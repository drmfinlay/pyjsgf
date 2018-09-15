"""
This module contains classes for compiling, importing from and matching JSpeech
Grammar Format grammars.
"""

from six import string_types

from .references import BaseRef, import_name, grammar_name
from .rules import Rule
from .errors import GrammarError


class Import(BaseRef):
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
    def __init__(self, name):
        super(Import, self).__init__(name)

    def compile(self):
        return "import <%s>;" % self.name

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__, self.name)

    @staticmethod
    def valid(name):
        return import_name.matches(name)


class Grammar(BaseRef):
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
        "UTF-8",
        "en"
    )

    def __init__(self, name="default"):
        super(Grammar, self).__init__(name)
        self._rules = []
        self._imports = []
        self.jsgf_version, self.charset_name, self.language_name =\
            self.default_header_values

    @property
    def jsgf_header(self):
        """
        The JSGF header string for this grammar. By default this is::

            #JSGF V1.0 UTF-8 en;

        :returns: str
        """
        return "#JSGF V%s %s %s;\n" % (self.jsgf_version,
                                       self.charset_name,
                                       self.language_name)

    @staticmethod
    def valid(name):
        return grammar_name.matches(name)

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

    @property
    def match_rules(self):
        """
        The rules that the ``find_matching_rules`` method will match against.

        :returns: list
        """
        return self.visible_rules

    def __str__(self):
        rules = ", ".join(["%s" % rule for rule in self.rules])
        return "Grammar(%s) with rules: %s" % (self.name, rules)

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return (self.name == other.name and self.jsgf_header == other.jsgf_header
                and self.rules == other.rules and self.imports == other.imports)

    def __ne__(self, other):
        return not self.__eq__(other)

    def add_rules(self, *rules):
        """
        Add multiple rules to the grammar.

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

        self._rules.append(rule)
        rule.grammar = self

    def add_import(self, _import):
        """
        Add an import statement to the grammar.

        :param _import: Import
        """
        if not isinstance(_import, Import):
            raise TypeError("object '%s' was not a JSGF Import object" % _import)
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

    def get_rule_from_name(self, name):
        """
        Get a rule object with the specified name, if one exists in the grammar.

        :param name: str
        :returns: Rule
        :raises: GrammarError
        """
        if name not in self.rule_names:
            raise GrammarError("'%s' is not a rule in Grammar '%s'" % (name, self))

        return self.rules[self.rule_names.index(name)]

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
    def __init__(self, rules=None, name="root"):
        super(RootGrammar, self).__init__(name)
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
