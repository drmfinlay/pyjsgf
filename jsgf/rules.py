# This Python file uses the following encoding: utf-8

"""
This module contains classes for compiling and matching JSpeech Grammar Format
rules.
"""

from .errors import GrammarError
from . import references
from .expansions import Expansion, Literal, NamedRuleRef, filter_expansion, \
    map_expansion, TraversalOrder


class Rule(references.BaseRef):
    """
    Base class for JSGF rules.

    Rule names can be a single word containing one or more alphanumeric Unicode
    characters and/or any of the following special characters: +-:;,=|/\()[]@#%!^&~$

    For example, the following are valid rule names:

    * hello
    * Zürich
    * user_test
    * $100
    * 1+2=3

    There are two reserved rule names: NULL and VOID. These reserved names cannot be
    used as rule names. You can however change the case to 'null' or 'void' to use
    them, as names are case-sensitive.
    """
    def __init__(self, name, visible, expansion, case_sensitive=False):
        """
        :param name: str
        :param visible: bool
        :param expansion: a string or Expansion object
        :param case_sensitive: whether rule literals should be case sensitive
            (default False).
        """
        super(Rule, self).__init__(name)
        self.visible = visible
        self._expansion = None
        self.expansion = expansion
        self._active = True
        self.grammar = None

        # Set case sensitivity (backing attribute and property).
        self._case_sensitive = case_sensitive
        self.case_sensitive = case_sensitive

    @property
    def expansion(self):
        """
        This rule's expansion.

        :returns: Expansion
        """
        return self._expansion

    @expansion.setter
    def expansion(self, value):
        self._set_expansion(value)

    @property
    def qualified_name(self):
        """
        This rule's qualified name.

        Qualified rule names are the last part of the grammar name plus the rule
        name. For example, if ``"com.example.grammar"`` is the full grammar name and
        ``"rule"`` is the rule name, then ``"grammar.rule"`` is the qualified name.
        """
        if self.grammar is not None:
            grammar_part = self.grammar.name.split(".")[-1]
            return "%s.%s" % (grammar_part, self._name)
        else:
            return self._name

    @property
    def fully_qualified_name(self):
        """
        This rule's fully qualified name.

        Fully-qualified rule names are the grammar name plus the rule name.
        For example, if ``"com.example.grammar"`` is the grammar name and ``"rule"``
        is the rule name, then ``"com.example.grammar.rule"`` is the fully-qualified
        name.
        """
        if self.grammar is not None:
            return "%s.%s" % (self.grammar.name, self._name)
        else:
            return self._name

    def _set_expansion(self, value):
        # Reset expansion.rule if there was a previous expansion
        if self._expansion:
            self._expansion.rule = None

        # Handle the object passed in as an expansion
        self._expansion = Expansion.make_expansion(value)

        # Set the rule attribute for the rule's expansions
        def set_rule(x):
            x.rule = self

        map_expansion(self._expansion, set_rule, shallow=True)

    def compile(self, ignore_tags=False):
        """
        Compile this rule's expansion tree and return the result.
        Set ignore_tags to True to not include expansion tags in the result.

        :param ignore_tags: bool
        :returns: str
        """
        if not self._active:
            return ""

        expansion = self.expansion.compile(ignore_tags)
        if not expansion:  # the compiled expansion is None or ""
            return ""

        result = "<%s> = %s;" % (self.name, expansion)

        if self.visible:
            return "public %s" % result
        else:
            return result
        
    def generate(self):
        """
        Generate a string matching this rule.

        :rtype: str
        """
        if not self._active:
            return ""
        
        result = self.expansion.generate()
        return result

    def __str__(self):
        return "%s(name='%s', visible=%s, expansion=%s)" %\
               (self.__class__.__name__,
                self.name, self.visible, self.expansion)

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        # The hash of a rule is the hash of its name, visibility and expansion
        # hashes combined.
        return hash("%s%s%s" % (hash(self.name),
                                hash(self.visible), hash(self.expansion)))

    @property
    def case_sensitive(self):
        """
        Case sensitivity used when matching and compiling :class:`Literal` rule
        expansions.

        This property can be ``True`` or ``False``. Matching and compilation will
        be *case-sensitive* if ``True`` and *case-insensitive* if ``False``. The
        default value is ``False``.

        Setting this property will override the ``case_sensitive`` value for each
        :class:`Literal` in the rule and in referenced rules.

        :rtype: bool
        :returns: literal case sensitivity
        """
        return self._case_sensitive

    @case_sensitive.setter
    def case_sensitive(self, value):
        value = bool(value)
        self._case_sensitive = value

        # Define a function for setting case_sensitive for all Literal rule
        # expansions.
        def func(e):
            if isinstance(e, Literal):
                e.case_sensitive = value
            elif isinstance(e, NamedRuleRef):
                # Set case_sensitive for referenced rules. Ignore references that
                # don't resolve to actual Rule objects.
                try:
                    e.referenced_rule.case_sensitive = value
                except GrammarError:
                    pass

        # Recursively operate on the rule expansion tree. Do *not* operate on
        # referenced rules directly.
        map_expansion(self.expansion, func, shallow=True)

    def enable(self):
        """
        Allow this rule to produce compile output and to match speech strings.
        """
        self._active = True

    def disable(self):
        """
        Stop this rule from producing compile output or from matching speech strings.
        """
        self._active = False

    @property
    def active(self):
        """
        Whether this rule is enabled or not. If it is, the rule can be matched and
        compiled, otherwise the ``compile`` and ``matches`` methods will return ""
        and False respectively.

        :returns: bool
        """
        return self._active

    @property
    def was_matched(self):
        """
        Whether this rule matched last time the ``matches`` method was called.

        :returns: bool
        """
        return self.expansion.current_match is not None

    def matches(self, speech):
        """
        Whether speech matches this rule.

        Matching ambiguous rule expansions is **not supported** because it not worth
        the performance hit. Ambiguous rule expansions are defined as some optional
        literal x followed by a required literal x. For example, successfully
        matching ``'test'`` for the following rule is not supported::

            <rule> = [test] test;

        :param speech: str
        :returns: bool
        """
        if not self._active:
            return False

        # Strip whitespace at the start of 'speech' and lower it to match regex
        # properly.
        speech = speech.lstrip()

        # Reset match data for this rule and referenced rules.
        self.expansion.reset_for_new_match()

        # Match the expansion and use the remainder substring to check if the rule
        # matched completely.
        remainder = self.expansion.matches(speech)
        if remainder != "":
            self.expansion.current_match = None

        return self.expansion.current_match is not None

    def find_matching_part(self, speech):
        """
        Searches for a part of speech that matches this rule and returns it.

        If no part matches or the rule is disabled, return None.

        :param speech: str
        :returns: str | None
        """
        if not self._active:
            return None

        # Strip whitespace at the start of 'speech' and lower it to match regex
        # properly.
        speech = speech.lstrip().lower()

        # Reset match data for this rule and referenced rules.
        self.expansion.reset_for_new_match()

        # Use the first match (if any) and break. The loop is required because
        # scanString returns a generator.
        result = None
        for match in self.expansion.matcher_element.scanString(speech):
            _, start, end = match
            result = speech[start:end]
            break

        return result

    @property
    def tags(self):
        """
        A list of JSGF tags used by this rule and any referenced rules. The returned
        list will be in the order in which tags appear in the compiled rule.

        :returns: list
        """
        # Get tagged expansions
        tagged_expansions = filter_expansion(
            self.expansion, lambda e: e.tag, TraversalOrder.PostOrder
        )

        # Return a list containing the tags of each expansion.
        return list(map(lambda e: e.tag, tagged_expansions))

    @property
    def matched_tags(self):
        """
        A list of JSGF tags whose expansions have been matched. The returned list
        will be in the order in which tags appear in the compiled rule.

        This includes matching tags in referenced rules.

        :returns: list
        """
        # Get tagged and matching expansions in this rule and referenced rules.
        tagged_expansions = filter_expansion(
            self.expansion, lambda e: e.tag and e.had_match,
            TraversalOrder.PostOrder
        )

        # Return a list containing the tags of each expansion.
        return list(map(lambda e: e.tag, tagged_expansions))

    def has_tag(self, tag):
        """
        Check whether there are expansions in this rule or referenced rules that use
        a given JSGF tag.

        :param tag: str
        :returns: bool
        """
        # Empty or whitespace-only strings are not valid tags.
        tag = tag.strip()
        if not tag:
            return False

        # Return whether the specified tag is used in this rule or referenced rules.
        return tag in self.tags

    def get_tags_matching(self, speech):
        """
        Match a speech string and return a list of any matching tags in this rule
        and in any referenced rules.

        :param speech: str
        :returns: list
        """
        self.matches(speech)
        return self.matched_tags

    @property
    def dependencies(self):
        """
        The set of rules which this rule directly and indirectly references.

        :returns: set
        """
        # Return the set of all rules referenced by a RuleRef
        return set(map(
            lambda x: x.referenced_rule,
            filter_expansion(self.expansion,
                             lambda x: isinstance(x, NamedRuleRef))
        ))

    @property
    def dependent_rules(self):
        """
        The set of rules in this rule's grammar that reference this rule.
        Returns an empty set if this rule is not in a grammar.

        :returns: set
        """
        if not self.grammar:
            return set()

        # Find any rule in the grammar that references this rule by checking if
        # this rule is in the dependencies set.
        return set(filter(
            lambda x: self in x.dependencies,
            self.grammar.rules
        ))

    @property
    def reference_count(self):
        """
        The number of dependent rules.

        :returns: int
        """
        return len(self.dependent_rules)

    def __eq__(self, other):
        return (self.name == other.name and
                self.expansion == other.expansion and
                self.visible == other.visible and
                self.case_sensitive == other.case_sensitive)

    def __ne__(self, other):
        return not self.__eq__(other)


class PublicRule(Rule):
    """
    Rule subclass with ``visible`` set to True.
    """
    def __init__(self, name, expansion, case_sensitive=False):
        super(PublicRule, self).__init__(name, True, expansion, case_sensitive)

    def __hash__(self):
        return super(PublicRule, self).__hash__()

    def __str__(self):
        return "%s(name='%s', expansion=%s)" %\
               (self.__class__.__name__, self.name, self.expansion)


class PrivateRule(Rule):
    """
    Rule subclass with ``visible`` set to False.
    """
    def __init__(self, name, expansion, case_sensitive=False):
        super(PrivateRule, self).__init__(name, False, expansion, case_sensitive)

    def __hash__(self):
        return super(PrivateRule, self).__hash__()

    def __str__(self):
        return "%s(name='%s', expansion=%s)" %\
               (self.__class__.__name__, self.name, self.expansion)


#: Alias of :class:`PrivateRule` kept in for backwards compatibility.
HiddenRule = PrivateRule
