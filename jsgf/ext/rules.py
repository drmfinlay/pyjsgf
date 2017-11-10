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
        self._original_name = self.name
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
        self.name = "%s_%d" % (self._original_name, self._current_index)

    def set_next(self):
        """
        Moves to the next expansion in the sequence if there is one.
        """
        if self.has_next_expansion:
            self._current_index += 1
            self._set_expansion_to_current()

    def restart_sequence(self):
        """
        Resets the current sequence expansion to the first one in the sequence.
        """
        self._current_index = 0
        self._set_expansion_to_current()

    def matches(self, speech):
        """
        Return whether or not speech matches the current expansion in the sequence.
        :type speech: str
        :return: bool
        """
        return super(SequenceRule, self).matches(speech)


class PublicSequenceRule(SequenceRule):
    def __init__(self, name, expansion):
        super(PublicSequenceRule, self).__init__(name, True, expansion)


class HiddenSequenceRule(SequenceRule):
    def __init__(self, name, expansion):
        super(HiddenSequenceRule, self).__init__(name, False, expansion)
