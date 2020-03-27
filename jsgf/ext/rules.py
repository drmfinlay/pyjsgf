"""
This module contains extension rule classes.
"""

from ..errors import GrammarError
from ..expansions import Repeat, TraversalOrder, filter_expansion
from ..rules import Rule

from .expansions import (expand_dictation_expansion, calculate_expansion_sequence,
                         Dictation, only_dictation_in_expansion)


class SequenceRule(Rule):
    """
    Class representing a list of regular expansions and ``Dictation`` expansions
    that must be spoken in a sequence.
    """
    def __init__(self, name, visible, expansion, case_sensitive=False):
        super(SequenceRule, self).__init__(name, visible, expansion, case_sensitive)

        # Keep the original expansion and use a copy of it for the sequence
        self._original_expansion = self.expansion
        self.expansion = self.expansion.copy()

        # Check if the entire rule can be repeated
        rep = self._find_root_repeat(self.expansion)
        if rep:
            # If it can, modify the tree so that rep is skipped over
            parent = rep.parent
            child = rep.children.pop(0)
            child.parent = parent
            if parent:
                parent.children.remove(rep)
                parent.children.append(child)
                rep.parent = None
            else:
                # If rep had no parent, set self.expansion to rep's child
                self.expansion = child
            self._can_repeat = True
        else:
            self._can_repeat = False

        # Check if expansion contains unexpanded AlternativeSets or Optionals
        # with Dictation descendants
        if expand_dictation_expansion(self.expansion) != [self.expansion]:
            raise GrammarError("SequenceRule cannot accept expansions which "
                               "have not been expanded with the "
                               "expand_dictation_expansion function.")

        # Calculate the expansion sequence without deep copying again
        self._sequence = tuple(calculate_expansion_sequence(self.expansion, False))
        self._current_index = 0
        self._refuse_matches = False
        self._set_expansion_to_current()

    def __str__(self):
        return "%s(name='%s', visible=%s, expansion=%s)" %\
               (self.__class__.__name__,
                self.name, self.visible, self.original_expansion)

    def __hash__(self):
        # The hash of a rule is the hash of its name, visibility and original
        # expansion hashes combined.
        return hash("%s%s%s" % (hash(self.name), hash(self.visible),
                                hash(self.original_expansion)))

    @property
    def expansion_sequence(self):
        """
        The expansion sequence used by the rule.

        :returns: tuple
        """
        return self._sequence

    @property
    def can_repeat(self):
        """
        Whether the entire SequenceRule can be repeated multiple times.

        Note that if the rule can be repeated, data from a repetition of the rule,
        such as ``current_match`` values of each sequence expansion, should be
        stored before ``restart_sequence`` is called for a further repetition.
        """
        return self._can_repeat

    @staticmethod
    def _find_root_repeat(e):
        """
        Recursive method to find a Repeat expansion that is an ancestor of all
        leaves in an expansion tree. If there isn't one, return None.

        :param e: Expansion
        :returns: Repeat | None
        """
        if isinstance(e, Repeat) and not e.is_optional:  # don't use optionals
            # Check if this Repeat has any ancestors with other children
            result = e
            p = e.parent
            while p:
                if len(p.children) > 1:
                    result = None
                    break
                p = p.parent
            if result:
                return e

        for child in e.children:
            result = SequenceRule._find_root_repeat(child)
            if result:
                return result

    def compile(self, ignore_tags=False):
        result = ""
        if not self.refuse_matches and not self.current_is_dictation_only:
            # This rule can be compiled as it doesn't have any Dictation expansions
            # and refuse_matches is not True.
            result = super(SequenceRule, self).compile(ignore_tags)

        return result

    @property
    def has_next_expansion(self):
        """
        Whether there is another sequence expansion after the current one.

        :returns: bool
        """
        return self._current_index + 1 < len(self._sequence)

    @property
    def current_is_dictation_only(self):
        """
        Whether the current expansion in the sequence contains only ``Dictation``
        expansions.

        :returns: bool
        """
        return only_dictation_in_expansion(self._sequence[self._current_index])

    @property
    def refuse_matches(self):
        """
        Whether or not matches on this rule can succeed.

        This is set to False if ``set_next`` is called and there is a next expansion
        or if ``restart_sequence`` is called.

        This can also be manually set with the setter for problematic situations
        where, for example, the current expansion is a ``Repeat`` expansion with a
        ``Dictation`` descendant.

        :returns: bool
        """
        return self._refuse_matches

    @refuse_matches.setter
    def refuse_matches(self, value):
        self._refuse_matches = value

    def _set_expansion_to_current(self):
        self.expansion = self._sequence[self._current_index]

        # Stop refusing matches
        self.refuse_matches = False

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

        :returns: str
        """
        matches = [x.current_match for x in self._sequence]
        if all([m is not None for m in matches]):
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

        This also sets ``current_match`` values for the original expansion used to
        create this rule.

        This method will only match once and return False on calls afterward until
        ``refuse_matches`` is False.

        :param speech: str
        :returns: bool
        """
        result = False
        if not self.refuse_matches:
            result = super(SequenceRule, self).matches(speech)

            # Graft the matches in the sequence onto the original expansion used to
            # create this SequenceRule.
            SequenceRule.graft_sequence_matches(self, self._original_expansion)

            # By default, don't let the current expansion be matched more than once
            self.refuse_matches = True

        return result

    @property
    def tags(self):
        """
        The set of JSGF tags in this rule's expansion.
        This does not include tags in referenced rules.

        :returns: set
        """
        # Get tagged expansions
        tagged_expansions = filter_expansion(
            self.original_expansion, lambda e: e.tag, shallow=True
        )

        # Return a set containing the tags of each tagged expansion.
        return set(map(lambda e: e.tag, tagged_expansions))

    @property
    def original_expansion(self):
        return self._original_expansion

    @staticmethod
    def graft_sequence_matches(sequence_rule, expansion):
        """
        Take a ``SequenceRule`` and an expansion and attempt to graft the matches of
        all expansions in the sequence onto the given expansion in-place.

        Not all expansions in the sequence need to have been matched.

        :param sequence_rule: SequenceRule
        :param expansion: Expansion
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
            e2.use_current_match = True
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
    """
    SequenceRule subclass with ``visible`` set to True.
    """
    def __init__(self, name, expansion, case_sensitive=False):
        super(PublicSequenceRule, self).__init__(name, True, expansion,
                                                 case_sensitive)

    def __hash__(self):
        return super(PublicSequenceRule, self).__hash__()

    def __str__(self):
        return "%s(name='%s', expansion=%s)" %\
               (self.__class__.__name__, self.name, self.original_expansion)


class PrivateSequenceRule(SequenceRule):
    """
    SequenceRule subclass with ``visible`` set to False.
    """
    def __init__(self, name, expansion, case_sensitive=False):
        super(PrivateSequenceRule, self).__init__(name, False, expansion,
                                                 case_sensitive)

    def __hash__(self):
        return super(PrivateSequenceRule, self).__hash__()

    def __str__(self):
        return "%s(name='%s', expansion=%s)" %\
               (self.__class__.__name__, self.name, self.original_expansion)


#: Alias of :class:`PrivateSequenceRule` kept in for backwards compatibility.
HiddenSequenceRule = PrivateSequenceRule
