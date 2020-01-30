"""
This module contains extension grammar classes.
"""
import re

from six import string_types

from .expansions import dictation_in_expansion, expand_dictation_expansion
from .rules import SequenceRule
from jsgf import GrammarError, Grammar, Rule


class DictationGrammar(Grammar):
    """
    Grammar subclass that processes rules using ``Dictation`` expansions so they can
    be compiled, matched and used with normal JSGF rules with utterance breaks.
    """
    def __init__(self, rules=None, name="default", case_sensitive=False):
        """
        :param rules: list
        :param name: str
        :param case_sensitive: bool
        """
        super(DictationGrammar, self).__init__(name, case_sensitive=case_sensitive)
        self._dictation_rules = []
        self._original_rule_map = {}
        self._init_jsgf_only_grammar()

        if rules:
            self.add_rules(*rules)

    def _init_jsgf_only_grammar(self):
        """
        Method that initialises the grammar to use for rules not containing
        Dictation expansions.

        Override this to use a different grammar class.
        """
        self._jsgf_only_grammar = Grammar(name=self.name,
                                          case_sensitive=self.case_sensitive)

    @property
    def rules(self):
        """
        The rules in this grammar.

        This includes internal generated rules as well as original rules.

        :returns: list
        """
        return list(set(
                self._dictation_rules + self._jsgf_only_grammar.match_rules +
                list(self._original_rule_map.values())
        ))

    @property
    def match_rules(self):
        """
        The rules that the ``find_matching_rules`` method will match against.

        :returns: list
        """
        result = []
        result.extend([x for x in self._dictation_rules if x.visible])
        result.extend(self._jsgf_only_grammar.match_rules)
        return result

    def add_rule(self, rule):
        if not isinstance(rule, Rule):
            raise TypeError("object '%s' was not a JSGF Rule object" % rule)

        # Check if the same rule is already in the grammar.
        if rule.name in self.rule_names:
            if rule in self.rules:
                # Silently return if the rule is comparable to another in the
                # grammar.
                return
            else:
                # This is not strictly true for DictationGrammar, but still holds
                # for match_rules and output from the compile methods.
                raise GrammarError("JSGF grammars cannot have multiple rules with "
                                   "the same name")

        # If the rule is not a dictation rule, add it to the JSGF only grammar and
        # the original rule map.
        if not dictation_in_expansion(rule.expansion):
            self._jsgf_only_grammar.add_rule(rule)
            self._original_rule_map[rule] = rule
            return

        # Check if the rule is a SequenceRule already and do a few things with it.
        if isinstance(rule, SequenceRule):
            if not rule.current_is_dictation_only:
                # The sequence starts with a JSGF only rule and can be
                # spoken like a normal rule
                self._jsgf_only_grammar.add_rule(rule)
            else:
                self._dictation_rules.append(rule)
            self._original_rule_map[rule] = rule
            return

        # Expand the rule's expansion into a list of 1 or more expansions.
        expanded = expand_dictation_expansion(rule.expansion)

        # Otherwise create new rules from the resulting expansions and add each to
        # either dictation_rules or _jsgf_only_grammar
        for i, x in enumerate(expanded):
            if len(expanded) == 1:
                # No need to use different names in this case
                new_name = rule.name
            else:
                new_name = "%s_%d" % (rule.name, i)
            if not dictation_in_expansion(x):
                r = Rule(new_name, rule.visible, x)

                # Add this rule to the JSGF only grammar
                self._jsgf_only_grammar.add_rule(r)

                # Keep track of the relationship between the original rule and its
                # expanded rules
                self._original_rule_map[r] = rule
            else:
                seq_rule = SequenceRule(new_name, rule.visible, x)
                self._original_rule_map[seq_rule] = rule

                if not seq_rule.current_is_dictation_only:
                    # The sequence starts with a JSGF only rule and can be
                    # spoken like a normal rule
                    self._jsgf_only_grammar.add_rule(seq_rule)
                else:
                    self._dictation_rules.append(seq_rule)

    def get_original_rule(self, rule):
        """
        Get the original rule from a generated rule.

        :param rule: Rule
        :returns: Rule
        """
        return self._original_rule_map[rule]

    def get_generated_rules(self, rule):
        """
        Get the rules generated from a rule added to this grammar.

        :param rule: Rule
        :returns: generator
        """
        for k, v in list(self._original_rule_map.items()):
            if v is rule:
                yield k

    def remove_rule(self, rule, ignore_dependent=False):
        # Find the rules generated from this rule and remove them wherever they are
        # as well as the original rule
        if isinstance(rule, string_types):
            rule_name = rule
        else:
            rule_name = rule.name

        for k, v in list(self._original_rule_map.items()):
            if v.name == rule_name:
                self._original_rule_map.pop(k)

                if k in self._dictation_rules:
                    self._dictation_rules.remove(k)

                elif k in self._jsgf_only_grammar.match_rules:
                    self._jsgf_only_grammar.remove_rule(k, ignore_dependent)

    def _compile(self, compile_as_root_grammar):
        """
        Internal method to compile the grammar.

        :param compile_as_root_grammar: bool
        :returns: str
        """
        self.rearrange_rules()

        try:
            # Compile the grammar
            if compile_as_root_grammar:
                result = self._jsgf_only_grammar.compile_as_root_grammar()
            else:
                result = self._jsgf_only_grammar.compile()

            # Check for compiled rules
            rule_pattern = re.compile("(public )?<.+> = .+;")

            # If there are none, set result to "".
            if not rule_pattern.search(result):
                result = ""
        except GrammarError as e:
            if len(self._dictation_rules) > 0:
                return ""
            else:
                raise GrammarError("no Dictation rules and JSGF only grammar "
                                   "failed to compile with error: '%s'" %
                                   e)
        return result

    def compile(self):
        return self._compile(False)

    def compile_as_root_grammar(self):
        return self._compile(True)

    def rearrange_rules(self):
        """
        Move each ``SequenceRule`` in this grammar between the dictation rules list
        and the internal grammar used for JSGF only rules depending on whether a
        ``SequenceRule``'s current expansion is dictation-only or not.
        """
        for rule in tuple(self._jsgf_only_grammar.match_rules):
            if not isinstance(rule, SequenceRule):
                continue
            if rule.current_is_dictation_only:
                self._jsgf_only_grammar.remove_rule(rule)
                self._dictation_rules.append(rule)

        for rule in tuple(self._dictation_rules):
            if not rule.current_is_dictation_only:
                self._jsgf_only_grammar.add_rule(rule)
                self._dictation_rules.remove(rule)

    def reset_sequence_rules(self):
        """
        Reset each ``SequenceRule`` in this grammar so that they can accept matches
        again.
        """
        for r in self._jsgf_only_grammar.match_rules + self._dictation_rules:
            if isinstance(r, SequenceRule):
                r.restart_sequence()

        self.rearrange_rules()

    def find_matching_rules(self, speech, advance_sequence_rules=True):
        """
        Find each visible rule passed to the grammar that matches the `speech`
        string. Also set matches for the original rule.

        :param speech: str
        :param advance_sequence_rules: whether to call ``set_next()`` for successful
            sequence rule matches.
        :returns: list
        """
        # Match against each match rule and remove any rules that didn't match
        result = self.match_rules
        for rule in tuple(result):
            if not rule.matches(speech):
                result.remove(rule)

        # Get the original rule for each rule in the result and ensure that their
        # current_match values reflect the generated rules' values.
        for rule in result:
            original = self.get_original_rule(rule)
            if isinstance(rule, SequenceRule):
                SequenceRule.graft_sequence_matches(rule, original.expansion)

                # Progress to the next expansion if required
                if rule.has_next_expansion and advance_sequence_rules:
                    rule.set_next()

            else:
                original.matches(rule.expansion.current_match)

        # Move SequenceRules between _dictation_rules and _jsgf_only_grammar as
        # required
        self.rearrange_rules()

        return result
