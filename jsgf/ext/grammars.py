"""
JSGF extension grammar classes
"""
from .expansions import dictation_in_expansion, expand_dictation_expansion
from .rules import SequenceRule
from jsgf import GrammarError, Grammar, Rule, RootGrammar


class DictationGrammar(Grammar):
    """
    Grammar subclass that processes rules that use Dictation expansions so they can
    be compiled, matched and used with normal JSGF rules.
    """
    def __init__(self, rules=None, name="default"):
        """
        :type rules: list
        :type name: str
        """
        super(DictationGrammar, self).__init__(name)
        self._dictation_rules = []
        self._original_rule_map = {}
        self._init_jsgf_only_grammar()

        if not rules:
            rules = []

        for rule in rules:
            self.add_rule(rule)

    def _init_jsgf_only_grammar(self):
        """
        Method that initialises the grammar to use for rules not containing
        Dictation expansions.

        Override this to use a different grammar class.
        """
        self._jsgf_only_grammar = RootGrammar()

    @property
    def rules(self):
        """
        The rules in this grammar.
        This includes internal generated rules as well as original rules.
        :return: iterable
        """
        return (self._dictation_rules + self._jsgf_only_grammar.match_rules +
                self._original_rule_map.values())

    @property
    def match_rules(self):
        """
        The rules that the find_matching_rules method will match against.
        :return: iterable
        """
        result = []
        result.extend(filter(lambda x: x.visible, self._dictation_rules))
        result.extend(self._jsgf_only_grammar.match_rules)
        return result

    def add_rule(self, rule):
        if rule.name in self.rule_names:
            raise GrammarError("JSGF grammar cannot have rules with the same name")

        # Expand rule's expansion into a list of expansions using
        # expand_dictation_expansion, create new rules from the resulting
        # expansions and add each to either dictation_rules or _jsgf_only_grammar
        for i, x in enumerate(expand_dictation_expansion(rule.expansion)):
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
        Get the original rule used to generate a rule from find_matching_rules.
        :type rule: Rule
        :return: Rule
        """
        return self._original_rule_map[rule]

    def get_generated_rules(self, rule):
        """
        Get a generator yielding the rules generated from a rule added to this
        grammar.
        :type rule: Rule
        """
        for k, v in self._original_rule_map.items():
            if v is rule:
                yield k

    def remove_rule(self, rule, ignore_dependent=False):
        # Find the rules generated from this rule and remove them wherever they are
        # as well as the original rule
        if isinstance(rule, str):
            rule_name = rule
        else:
            rule_name = rule.name

        for k, v in self._original_rule_map.items():
            if v.name == rule_name:
                self._original_rule_map.pop(k)

                if k in self._dictation_rules:
                    self._dictation_rules.remove(k)

                elif k in self._jsgf_only_grammar.match_rules:
                    self._jsgf_only_grammar.remove_rule(k, ignore_dependent)

    def compile_grammar(self, charset_name="UTF-8", language_name="en",
                        jsgf_version="1.0"):
        self.rearrange_rules()
        try:
            result = self._jsgf_only_grammar.compile_grammar(
                charset_name, language_name, jsgf_version)
        except GrammarError, e:
            if len(self._dictation_rules) > 0:
                result = ""
            else:
                raise GrammarError("no Dictation rules and JSGF only grammar "
                                   "failed to compile with error: '%s'" %
                                   e.message)
        return result

    def rearrange_rules(self):
        """
        Move SequenceRules in this grammar between the dictation rules list and
        the internal grammar used for JSGF only rules depending on whether a
        SequenceRule's current expansion is dictation only or not.
        """
        for rule in self._jsgf_only_grammar.match_rules:
            if not isinstance(rule, SequenceRule):
                continue
            if rule.current_is_dictation_only or rule.refuse_matches:
                self._jsgf_only_grammar.remove_rule(rule)
                self._dictation_rules.append(rule)

        for rule in self._dictation_rules:
            if not rule.current_is_dictation_only:
                self._jsgf_only_grammar.add_rule(rule)
                self._dictation_rules.remove(rule)

    def reset_sequence_rules(self):
        """
        Reset each SequenceRule in this grammar so that they can accept matches
        again.
        """
        for r in self._jsgf_only_grammar.match_rules + self._dictation_rules:
            if isinstance(r, SequenceRule):
                r.restart_sequence()

        self.rearrange_rules()

    def find_matching_rules(self, speech, advance_sequence_rules=True):
        """
        Find each visible rule passed to the grammar that matches the 'speech'
        string. Also set matches for the original rule.
        :type speech: str
        :param advance_sequence_rules: whether to call set_next() for successful
        sequence rule matches.
        :return: iterable
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
