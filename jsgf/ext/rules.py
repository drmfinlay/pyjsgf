from jsgf import Expansion
from .expansions import *


class SequenceRule(Rule):
    """
    Class representing a list of expansions that must be spoken in a sequence.
    """
    def __init__(self, name, visible, expansion):
        """
        :type name: str
        :type visible: bool
        :type expansion: Expansion
        """
        super(SequenceRule, self).__init__(name, visible, expansion)

        # Check if expansion contains unexpanded AlternativeSets or Optionals
        # with Dictation descendants
        if expand_dictation_expansion(self.expansion) != [self.expansion]:
            raise GrammarError("SequenceRule cannot accept expansions which "
                               "have not been expanded with the "
                               "expand_dictation_expansion function.")

        self._sequence = tuple(calculate_expansion_sequence(self.expansion))
        self._next_index = 0
        self._original_name = self.name
        self._original_expansion = self.expansion

    def compile(self, ignore_tags=False):
        self.expansion = self._sequence[self._next_index]

        if self.next_is_dictation_only:
            # This rule cannot be fully compiled to JSGF as it only has dictation
            # expansions
            return ""
        else:
            self.name = "%s_%d" % (self._original_name, self._next_index)
            return super(SequenceRule, self).compile(ignore_tags)

    @property
    def has_next_expansion(self):
        """
        Whether the current sequence expansion is the last one.
        :return: bool
        """
        return self._next_index < len(self._sequence)

    @property
    def next_is_dictation_only(self):
        """
        Whether the next expansion in the sequence contains only dictation
        literals.
        :return: bool
        """
        if self.has_next_expansion:
            return only_dictation_in_expansion(self._sequence[self._next_index])
        else:
            return False

    def set_next(self):
        """
        Moves to the next expansion in the sequence if there is one.
        """
        self._next_index += 1

    def restart_sequence(self):
        """
        Set the current sequence expansion index to the first expansion.
        """
        self._next_index = 0
        self.expansion = self._sequence[self._next_index]

    def matches(self, speech):
        """
        Return whether or not speech matches the next expansion in the sequence.
        :type speech: str
        :return: bool
        """
        self.expansion = self._sequence[self._next_index]
        return super(SequenceRule, self).matches(speech)


class PublicSequenceRule(SequenceRule):
    def __init__(self, name, expansion):
        super(PublicSequenceRule, self).__init__(name, True, expansion)


class HiddenSequenceRule(SequenceRule):
    def __init__(self, name, expansion):
        super(HiddenSequenceRule, self).__init__(name, False, expansion)
