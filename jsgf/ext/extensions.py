from copy import deepcopy

from jsgf.expansions import Literal, Expansion
from jsgf.rules import Rule


class Dictation(Expansion):
    """
    Class representing dictation input matching any spoken words.
    This expansion uses the default compile() implementation because JSGF
    does not handle dictation.
    This is largely based on the functionality provided by using Dragon
    NaturallySpeaking and the dragonfly Python library together.
    """
    def __init__(self):
        super(Dictation, self).__init__([])

    def matching_regex(self):
        # Match one or more words separated by whitespace as well as any
        # whitespace preceding the words.
        word = "[a-zA-Z0-9?,\.\-_!;:']+"
        words = "(\s+%s)+" % word
        return words


def dictation_in_expansion(e, no_literals=False):
    if isinstance(e, Dictation):
        return True
    elif no_literals:
        if isinstance(e, Literal):
            return False
        else:
            result = True
            for child in e.children:
                result = result and dictation_in_expansion(child,
                                                           no_literals)
            return result
    else:
        for child in e.children:
            if dictation_in_expansion(child, no_literals):
                return True
        return False


only_dictation_in_expansion = lambda e: dictation_in_expansion(e, True)
no_dictation_in_expansion = lambda e: not dictation_in_expansion(e, False)
dictation_and_literals_in_expansion = lambda e: dictation_in_expansion(e, False)


class SequenceRule(Rule):
    """
    Class representing rules that must be spoken in a sequence.
    """
    def __init__(self, name, visible, expansion, expansion_groups):
        """
        :type name: str
        :type visible: bool
        :type expansion: Expansion
        :type expansion_groups: tuple
        """
        if not isinstance(expansion_groups, tuple):
            raise TypeError("expansion_groups must be a tuple")
        self._expansion_groups = expansion_groups
        print("Printing expansion groups")
        for x, group in enumerate(expansion_groups):
            for e in group:
                print("%d: %s" % (x, e))

        print("--------------\n")

        super(SequenceRule, self).__init__(name, visible, expansion)

    def compile(self, ignore_tags=False, empty_result=False):
        # This rule cannot be fully compiled to JSGF as it only has dictation
        # expansions
        if only_dictation_in_expansion(self.expansion):
            return ""
        else:
            return super(SequenceRule, self).compile(ignore_tags)

    @property
    def dictation_only_rule(self):
        """
        Whether this rule contains dictation expansions and no Literal expansions.
        :return: bool
        """
        return only_dictation_in_expansion(self.expansion)

    @property
    def dictation_rule(self):
        """
        Whether or not this rule's contains a dictation expansion.
        :return: bool
        """
        return dictation_in_expansion(self.expansion)

    @property
    def expansion_groups(self):
        return self._expansion_groups


class ExtensionRule(Rule):
    def __init__(self, name, visible, expansion):
        self._rule_sequence = None
        self._current_sequence_rule = None
        super(ExtensionRule, self).__init__(name, visible, expansion)

    def _set_expansion(self, value):
        super(ExtensionRule, self)._set_expansion(value)

        # Construct the rule sequence of this rule so that if it's a dictation
        # rule, it can be recognised properly in sequence.
        self.calculate_rule_sequence()

    @property
    def rule_sequence(self):
        """
        List of rules that must be spoken in a sequence.
        These rules can contain extension Dictation expansions that can use
        JSGF-only rules in conjunction with arbitrary speech from, for example,
        large vocabulary speech decoders.
        """
        if not self._rule_sequence:
            self.calculate_rule_sequence()

        return self._rule_sequence

    @property
    def current_sequence_rule(self):
        if not self._current_sequence_rule:
            self._current_sequence_rule = self.rule_sequence[0]
        else:
            return self._current_sequence_rule

    @property
    def dictation_only_rule(self):
        """
        Whether this rule contains dictation expansions and no Literal expansions.
        :return: bool
        """
        return only_dictation_in_expansion(self.expansion)

    @property
    def dictation_rule(self):
        """
        Whether or not this rule's contains a dictation expansion.
        :return: bool
        """
        return dictation_in_expansion(self.expansion)

    def compile(self, ignore_tags=False, empty_result=False):
        if not self.rule_sequence:
            return super(ExtensionRule, self).compile(ignore_tags)
        else:
            return self.current_sequence_rule.compile(ignore_tags)

    def matches(self, speech):
        result = self.current_sequence_rule.matches(speech)
        if result:
            index = self.rule_sequence.index(self.current_sequence_rule)
            next = self.rule_sequence[index + 1]
        else:
            # The whole sequence must match and this SequenceRule didn't.
            self._current_sequence_rule = None

        return result

    def calculate_rule_sequence(self):
        """
        Set the rule_sequence property to a list of rules to recognise in sequence.
        """

        # Create a deep copy of the expansion tree because there will be
        # modification of the child/parent relationships
        expansion = deepcopy(self.expansion)

        # Populate a dictionary with an id for each expansion to distinguish between
        # groups of expansions without ambiguity when matching a rule.
        # This is necessary because dictation expansions are wrapped in a copy of
        # each of their ancestors as they occur.
        ids = {}

        def id_expansion_tree(e, id_):
            for child in e.children:
                id_ = id_expansion_tree(child, id_)

            ids[e] = id_
            id_ += 1
            return id_

        id_expansion_tree(expansion, 0)

        def generate_expansion_from_children(e, children):
            assert isinstance(e, Expansion)
            assert isinstance(children, (list, tuple))
            if len(children) == 1:
                result = type(e)(children[0])
            elif len(children) > 1:
                result = type(e)(*children)
            else:
                result = None

            if result and e in ids:
                ids[result] = ids[e]

            return result

        def calculate_sequence(e):
            """
            Calculate the sequence of an expansion containing dictation that is in
            one of the following forms with DF meaning dictation free expansion and
            DO meaning dictation only expansion:
            [DF] - e has no dictation expansions
            [DO]
            [DO, DF, ...]
            [DF, DO, ... ]
            :type e: Expansion
            :rtype: list
            """
            result = []
            if isinstance(e, Dictation):
                # Manipulate the result by turning this expansion into its entire
                # parent chain so that it becomes a top level expansion in the sequence
                # with all relevant information denoted by the expansions wrapping it
                parent = e.parent
                while parent:
                    # Add e's replacement to the ids dictionary using the parent's
                    # value
                    e = type(parent)(e)
                    ids[e] = ids[parent]

                    # Go up to the next parent
                    parent = parent.parent

                result.append(e)

            elif len(e.children) == 0:
                result.append(e)

            else:
                # Partition the children of the expansion so that dictation
                # expansions are placed after groups of normal expansions
                child_group = []

                # Remove and process each child from left to right
                while len(e.children) > 0:
                    child_result = calculate_sequence(e.children.pop(0))

                    # Process the child_result list
                    for r in child_result:
                        # Add child_group, the expansion r, and this expansion with
                        # its remaining children to the result list appropriately
                        if only_dictation_in_expansion(r):  # fully processed
                            # Add child_group to the result list appropriately
                            new_expansion = generate_expansion_from_children(
                                e, child_group
                            )

                            if new_expansion:
                                result.append(new_expansion)

                            # Reset child_group for the next partition
                            child_group = []
                            result.append(r)
                        elif no_dictation_in_expansion(r):  # no processing required
                            child_group.append(r)

                        elif dictation_and_literals_in_expansion(r):
                            # Add child_group to the result list appropriately
                            new_expansion = generate_expansion_from_children(
                                e, child_group
                            )

                            if new_expansion:
                                result.append(new_expansion)

                            # Reset child_group for the next partition
                            child_group = []

                            # Append this expansion for further processing if it
                            # still has children
                            if len(e.children) >= 1:
                                result.append(e)

                # If there are still children left in child_group, they must be
                # appended to the result appropriately
                if len(child_group) >= 1:
                    new_expansion = generate_expansion_from_children(
                        e, child_group
                    )
                    if new_expansion:
                        result.append(new_expansion)

            return result

        # Create expansion groups from the split and id'd expansion trees
        groups_by_id = {}
        for k, v in ids.items():
            if v not in groups_by_id:
                groups_by_id[v] = []
            groups_by_id[v].append(k)

        def expansion_groups(e):
            """
            Get the expansion groups used in an expansion tree.
            :type e: Expansion
            :return: set
            """
            result = set()
            if e in ids:
                result.add(tuple(groups_by_id[ids[e]]))
            for child in e.children:
                result = result.union(expansion_groups(child))
            return result

        sequence = [
            SequenceRule("%s_%s" % (self.name, i), True, x,
                         tuple(expansion_groups(x)))
            for i, x in enumerate(calculate_sequence(expansion))
        ]

        print("Sequence: %s" % " "
              .join(["%s" % _ for _ in sequence]))

        self._rule_sequence = sequence
