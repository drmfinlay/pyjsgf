# This Python file uses the following encoding: utf-8

"""
Classes for compiling JSpeech Grammar Format rules
"""

from .references import BaseRef
from .expansions import Expansion, RuleRef, filter_expansion, JointTreeContext
from .errors import CompilationError


class Rule(BaseRef):
    """
    Base class for JSGF rules.

    Rule names can be a single word containing one or more alphanumeric Unicode
    characters and/or any of the following special characters: +-:;,=|/\()[]@#%!^&~$

    For example, the following are valid rule names:
    hello
    Zürich
    user_test
    $100
    1+2=3

    There are two reserved rule names: NULL and VOID. These reserved names cannot be
    used as rule names. You can however change the case to 'null' or 'void' to use
    them, as names are case-sensitive.
    """
    def __init__(self, name, visible, expansion):
        """
        :type name: str
        :type visible: bool
        :param expansion: a string or Expansion object
        """
        super(Rule, self).__init__(name)
        self.visible = visible
        self._expansion = None
        self.expansion = expansion
        self._active = True
        self.grammar = None

    @property
    def expansion(self):
        return self._expansion

    @expansion.setter
    def expansion(self, value):
        self._set_expansion(value)

    def _set_expansion(self, value):
        # Reset expansion.rule if there was a previous expansion
        if self._expansion:
            self._expansion.rule = None

        # Handle the object passed in as an expansion
        self._expansion = Expansion.make_expansion(value)

        # Set expansion's rule attribute to this rule
        self._expansion.rule = self

    def compile(self, ignore_tags=False):
        """
        Compile this rule's expansion tree and return the result.
        Set ignore_tags to True to not include expansion tags in the result.
        :type ignore_tags: bool
        :rtype: str
        """
        if not self._active:
            return ""

        expansion = self.expansion.compile(ignore_tags)
        if not expansion:  # the compiled expansion is None or ""
            return ""

        # Raise a CompilationError if there are no non-optional leaves in the
        # expansion tree
        leaves = self.expansion.leaves

        if self.expansion.is_optional or all([l.is_optional for l in leaves]):
            raise CompilationError("nothing in the expansion tree is required to "
                                   "be spoken.")

        result = "<%s> = %s;" % (self.name, expansion)

        if self.visible:
            return "public %s" % result
        else:
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
        compiled, otherwise the compile and matches methods will return "" and
        False respectively.
        :return: bool
        """
        return self._active

    @property
    def was_matched(self):
        """
        Whether this rule matched last time the matches method was called.
        :return: bool
        """
        return self.expansion.current_match is not None

    def matches(self, speech):
        """
        Whether speech matches this rule.
        :type speech: str
        """
        if not self._active:
            return False

        # Strip whitespace at the start of 'speech' and lower it to match regex
        # properly.
        speech = speech.lstrip().lower()

        # Reset match data for this rule and referenced rules.
        self.expansion.reset_for_new_match()

        # Use a JointTreeContext so that this rule's expansion tree and the
        # expansion trees of referenced rules are joint during matching.
        with JointTreeContext(self.expansion):
            result = self.expansion.matches(speech)

        # Check if the rule matched completely
        if result != "":
            self.expansion.current_match = None

        return self.expansion.current_match is not None

    @property
    def tags(self):
        """
        The set of JSGF tags in this rule's expansion.
        This does not include tags in referenced rules.
        :rtype: set
        """
        # Get tagged expansions
        tagged_expansions = filter_expansion(
            self.expansion, lambda e: e.tag, shallow=True
        )

        # Return a set containing the tags of each tagged expansion.
        return set(map(lambda e: e.tag, tagged_expansions))

    def has_tag(self, tag):
        """
        Check whether there are expansions in this rule that use a given JSGF tag.
        :type tag: str
        :rtype: bool
        """
        # Empty or whitespace-only strings are not valid tags.
        tag = tag.strip()
        if not tag:
            return False

        # Return whether the specified is used in this rule.
        return tag in self.tags

    @property
    def dependencies(self):
        """
        The set of rules which this rule directly and indirectly references.
        :rtype: set
        """
        # Return the set of all rules referenced by a RuleRef
        return set(map(
            lambda x: x.referenced_rule,
            filter_expansion(self.expansion, lambda x: isinstance(x, RuleRef))
        ))

    @property
    def dependent_rules(self):
        """
        The set of rules in this rule's grammar that reference this rule.
        Returns an empty set if this rule is not in a grammar.
        :rtype: set
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
        :rtype: int
        """
        return len(self.dependent_rules)

    def __eq__(self, other):
        return (self.name == other.name and
                self.expansion == other.expansion and
                self.visible == other.visible)

    def __ne__(self, other):
        return not self.__eq__(other)


class PublicRule(Rule):
    def __init__(self, name, expansion):
        super(PublicRule, self).__init__(name, True, expansion)

    def __hash__(self):
        return super(PublicRule, self).__hash__()

    def __str__(self):
        return "%s(name='%s', expansion=%s)" %\
               (self.__class__.__name__, self.name, self.expansion)


class HiddenRule(Rule):
    def __init__(self, name, expansion):
        super(HiddenRule, self).__init__(name, False, expansion)

    def __hash__(self):
        return super(HiddenRule, self).__hash__()

    def __str__(self):
        return "%s(name='%s', expansion=%s)" %\
               (self.__class__.__name__, self.name, self.expansion)
