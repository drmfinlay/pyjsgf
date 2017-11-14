from .expansions import *


class SequenceRule(Rule):
    """
    Class representing a list of expansions that must be spoken in a sequence.
    """
    def __init__(self, name, visible, expansion):
        """
        :type name: str
        :type visible: bool
        :param expansion:
        """
        super(SequenceRule, self).__init__(name, visible, expansion)

        # Check if expansion contains unexpanded AlternativeSets or Optionals
        # with Dictation descendants
        if expand_dictation_expansion(self.expansion) != [self.expansion]:
            raise GrammarError("SequenceRule cannot accept expansions which "
                               "have not been expanded with the "
                               "expand_dictation_expansion function.")

        self._sequence = tuple(calculate_expansion_sequence(self.expansion))
        self._current_index = 0
        self._original_expansion = self.expansion
        self._set_expansion_to_current()

    def compile(self, ignore_tags=False):
        if self.current_is_dictation_only:
            # This rule cannot be fully compiled to JSGF as it only has dictation
            # expansions
            return ""
        else:
            return super(SequenceRule, self).compile(ignore_tags)

    @property
    def has_next_expansion(self):
        """
        Whether the current sequence expansion is the last one.
        :return: bool
        """
        return self._current_index + 1 < len(self._sequence)

    @property
    def current_is_dictation_only(self):
        """
        Whether the current expansion in the sequence contains only dictation
        literals.
        :return: bool
        """
        return only_dictation_in_expansion(self._sequence[self._current_index])

    def _set_expansion_to_current(self):
        self.expansion = self._sequence[self._current_index]

    def set_next(self):
        """
        Moves to the next expansion in the sequence if there is one.
        """
        if self.has_next_expansion:
            self._current_index += 1
            self._set_expansion_to_current()

    @property
    def entire_match(self):
        """
        If the entire sequence is matched by successive calls to the matches
        method, this returns all strings that matched joined together by spaces.
        :return: str
        """
        matches = map(lambda x: x.current_match, self._sequence)
        if all(map(lambda m: m is not None, matches)):
            return " ".join(matches)

    def restart_sequence(self):
        """
        Resets the current sequence expansion to the first one in the sequence and
        clears the match data of each sequence expansion.
        """
        self._current_index = 0
        self._set_expansion_to_current()
        for expansion in self._sequence:
            expansion.reset_match_data()

    def matches(self, speech):
        """
        Return whether or not speech matches the current expansion in the sequence.
        Also sets matches for the original expansion used to create this rule.
        :type speech: str
        :return: bool
        """
        result = super(SequenceRule, self).matches(speech)

        # Graft the matches in the sequence onto the original expansion used to
        # create this SequenceRule.
        SequenceRule.graft_sequence_matches(self, self._original_expansion)

        return result

    @property
    def original_expansion(self):
        return self._original_expansion

    @staticmethod
    def graft_sequence_matches(sequence_rule, expansion):
        """
        Take a SequenceRule and an expansion and attempt to graft the matches of
        all expansions in the sequence onto the given expansion in-place.

        Not all expansions in the sequence need to have been matched.

        :type sequence_rule: SequenceRule
        :type expansion: Expansion
        """
        def is_dictation(x):
            return isinstance(x, Dictation)

        # Collect Dictation in expansion and in all expansions in the
        # sequence
        dictation_in_seq = []
        dictation_in_exp = filter_expansion(expansion, is_dictation,
                                            TraversalOrder.PostOrder)
        for e in sequence_rule._sequence:
            dictation_in_seq.extend(filter_expansion(
                e, is_dictation, TraversalOrder.PostOrder))

        # Set current_match of Dictation expansions in the given expansion to
        # current_match values of their respective counterparts in the sequence.
        for e1, e2 in zip(dictation_in_seq, dictation_in_exp):
            assert isinstance(e1, Dictation) and isinstance(e2, Dictation)
            # Stop the matches(speech) method from changing current_match
            e2.refuse_matches = True
            e2.current_match = e1.current_match

        # Then collect expansions with current_match set.
        matching = []
        for e in sequence_rule._sequence:
            if e.current_match is None:
                # e and nothing after e match
                break
            else:
                matching.append(e)

        # Now match on expansion using the matches for the sequence.
        expansion.matches(" ".join([e.current_match for e in matching]))


class PublicSequenceRule(SequenceRule):
    def __init__(self, name, expansion):
        super(PublicSequenceRule, self).__init__(name, True, expansion)


class HiddenSequenceRule(SequenceRule):
    def __init__(self, name, expansion):
        super(HiddenSequenceRule, self).__init__(name, False, expansion)
