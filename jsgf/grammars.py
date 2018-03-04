"""
Classes for compiling and importing JSpeech Grammar Format grammars
"""

from .rules import Rule
from .errors import GrammarError


class Import(object):
    def __init__(self, name):
        self.name = name

    def compile(self):
        return "import <%s>;" % self.name

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__, self.name)


class Grammar(object):
    def __init__(self, name="default"):
        self.name = name
        self._rules = []
        self._imports = []
        self.charset_name = "UTF-8"
        self.language_name = "en"
        self.jsgf_version = "1.0"

    def _get_jsgf_header(self):
        return "#JSGF V%s %s %s;\n" % (self.jsgf_version,
                                       self.charset_name,
                                       self.language_name)

    def compile(self):
        """
        Compile this grammar's imports and rules into a string that can be
        recognised by a JSGF parser.
        :rtype: str
        """
        result = self._get_jsgf_header()
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
        Compile this grammar by calling compile and write the result to the
        specified file.
        :type file_path: str
        :type compile_as_root_grammar: bool
        """
        if compile_as_root_grammar:
            compiled_lines = self.compile_as_root_grammar().splitlines()
        else:
            compiled_lines = self.compile().splitlines()
        with open(file_path, "w+") as f:
            f.writelines(compiled_lines)

    def compile_grammar(self, charset_name="UTF-8", language_name="en",
                        jsgf_version="1.0"):
        """
        This method is *deprecated*, use `compile` instead.
        Compile this grammar's imports and rules into a string that can be
        recognised by a JSGF parser.
        :param charset_name:
        :param language_name:
        :param jsgf_version:
        :rtype: str
        """
        self.charset_name = charset_name
        self.language_name = language_name
        self.jsgf_version = jsgf_version
        return self.compile()

    def compile_as_root_grammar(self):
        """
        Compile this grammar with one public "root" rule containing rule references
        in an alternative set to every other rule as such:
        public <root> = (<rule1>|<rule2>|..|<ruleN>);
        <rule1> = ...;
        <rule2> = ...;
        .
        .
        .
        <ruleN> = ...;
        :rtype: str
        """
        result = self._get_jsgf_header()
        result += "grammar %s;\n" % self.name

        # Add imports
        for i in self._imports:
            result += "%s\n" % i.compile()

        # Get rules in the grammar that are visible and active
        visible_rules = list(filter(lambda x: x.active, self.visible_rules))

        # Return the result if there are no rules that are visible and active
        if not visible_rules:
            return result

        # Build the root rule and add it to the result
        names = [r.name for r in visible_rules if r.visible]
        refs = ["<%s>" % name for name in names]
        alt_set = "(%s)" % "|".join(refs)
        result += "public <root> = %s;\n" % alt_set

        # Temporarily set each visible rule to not visible
        for rule in visible_rules:
            rule.visible = False

        # Compile each rule
        for rule in self.rules:
            compiled = rule.compile()
            if compiled and rule.active:
                result += "%s\n" % compiled

        # Set rule visibility back to normal
        for rule in visible_rules:
            rule.visible = True

        return result

    @property
    def rules(self):
        """
        Get the rules added to this grammar.
        :rtype: list
        """
        return self._rules

    visible_rules = property(
        lambda self: [rule for rule in self.rules if rule.visible],
        doc="""
        The rules in this grammar which have the visible attribute set to True.
        :rtype: list
        """
    )

    rule_names = property(
        lambda self: [rule.name for rule in self.rules],
        doc="""
        The rule names of each rule in this grammar.
        :rtype: list
        """
    )

    @property
    def match_rules(self):
        """
        The rules that the find_matching_rules method will match against.
        :return: iterable
        """
        return self.visible_rules

    def __str__(self):
        rules = ", ".join(["%s" % rule for rule in self.rules])
        return "Grammar(%s) with rules: %s" % (self.name, rules)

    def add_rules(self, *rules):
        for r in rules:
            self.add_rule(r)

    def add_imports(self, *imports):
        for i in imports:
            self.add_import(i)

    def add_rule(self, rule):
        if not isinstance(rule, Rule):
            raise TypeError("object '%s' was not a JSGF Rule object" % rule)

        if rule.name in self.rule_names:
            raise GrammarError("JSGF grammar cannot have rules with the same name")
        self._rules.append(rule)

    def add_import(self, _import):
        """
        Add an import for another JSGF grammar file.
        :type _import: Import
        """
        if not isinstance(_import, Import):
            raise TypeError("object '%s' was not a JSGF Import object" % _import)
        self._rules.append(_import)

    def find_matching_rules(self, speech):
        """
        Find each visible rule in this grammar that matches the 'speech' string.
        :type speech: str
        :return: iterable
        """
        return [r for r in self.match_rules if r.visible and r.matches(speech)]

    def _get_rule_from_name(self, name):
        if name not in self.rule_names:
            raise GrammarError("'%s' is not a rule in Grammar '%s'" % (name, self))

        return self.rules[self.rule_names.index(name)]

    def remove_rule(self, rule, ignore_dependent=False):
        """
        Remove a rule from this grammar.
        :param rule: Rule object or the name of a rule in this grammar
        :param ignore_dependent: whether to check if the rule has dependent rules
        """
        if not isinstance(rule, Rule):
            # Assume 'rule' is the name of a rule
            # Get the rule object with the name
            rule = self._get_rule_from_name(rule)
        elif rule not in self.rules:
            raise GrammarError("'%s' is not a rule in Grammar '%s'" % (rule, self))

        # Check if rule with name 'rule_name' is a dependency of another rule
        # in this grammar.
        if rule.reference_count > 0 and not ignore_dependent:
            raise GrammarError("Cannot remove rule '%s' as it is referenced by "
                               "a RuleRef object in another rule." % rule)

        self.rules.remove(rule)

    def enable_rule(self, rule):
        """
        Enable a rule in this grammar, allowing it to appear in the compile method
        output and to be matched with the find_matching_rules method.

        Rules are enabled by default.

        :param rule: Rule object or the name of a rule in this grammar
        """
        # Handle the rule parameter
        if not isinstance(rule, Rule):
            rule_name = rule  # assume rule is a name string
        else:
            rule_name = rule.name
            rule.enable()

        if rule_name not in self.rule_names:
            raise GrammarError("'%s' is not a rule in Grammar '%s'" % (rule, self))

        # Enable any rules in the grammar which have the given name
        for r in [x for x in self.rules if x.name == rule_name]:
            r.enable()

    def disable_rule(self, rule):
        """
        Disable a rule in this grammar, preventing it from appearing in the compile
        method output or being matched with the find_matching_rules method.
        :param rule: Rule object or the name of a rule in this grammar
        """
        # Handle the rule parameter
        if not isinstance(rule, Rule):
            rule_name = rule  # assume rule is a name string
        else:
            rule_name = rule.name
            rule.disable()

        if rule_name not in self.rule_names:
            raise GrammarError("'%s' is not a rule in Grammar '%s'" % (rule, self))

        # Disable any rules in the grammar which have the given name
        for r in [x for x in self.rules if x.name == rule_name]:
            r.disable()


class RootGrammar(Grammar):
    """
    A grammar with one public "root" rule containing rule references in an
    alternative set to every other rule as such:
    public <root> = (<rule1>|<rule2>|..|<ruleN>);
    <rule1> = ...;
    <rule2> = ...;
    .
    .
    .
    <ruleN> = ...;
    """
    def __init__(self, rules=None, name="root"):
        super(RootGrammar, self).__init__(name)
        if rules:
            self.add_rules(*rules)

    def compile(self):
        return self.compile_as_root_grammar()

    def add_rule(self, rule):
        if rule.name == "root":
            raise GrammarError("cannot add rule with name 'root' to RootGrammar")

        super(RootGrammar, self).add_rule(rule)

    def compile_to_file(self, file_path, compile_as_root_grammar=True):
        super(RootGrammar, self).compile_to_file(file_path, compile_as_root_grammar)
