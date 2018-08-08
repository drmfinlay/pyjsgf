import re
from jsgf import *


class Dictation(Literal):
    """
    Class representing dictation input matching any spoken words.
    This expansion uses the default compile() implementation because JSGF
    does not handle dictation.
    This is largely based on the functionality provided by using Dragon
    NaturallySpeaking and the dragonfly Python library together.
    """
    def __init__(self):
        # Pass the empty string to the Literal constructor so that calling compile
        # yields "" or "" + the tag
        super(Dictation, self).__init__("")
        self._use_current_match = False

    def __str__(self):
        return "%s()" % self.__class__.__name__

    def __copy__(self):
        e = type(self)()
        e.tag = self.tag
        return e

    def __deepcopy__(self, memo=None):
        return self.__copy__()

    def validate_compilable(self):
        pass

    @property
    def use_current_match(self):
        """
        Consume the value of current_match in _matches_internal rather than
        matching on any string of words.
        This is used by the SequenceRule.graft_sequence_matches method.

        :return: bool
        """
        return self._use_current_match

    @use_current_match.setter
    def use_current_match(self, value):
        self._use_current_match = value

    def _matches_internal(self, speech):
        result = speech

        if self.use_current_match:
            # If current_match is set and speech starts with it, then pretend
            # that part of speech was consumed normally and return the rest.
            if self.current_match and result.startswith(self.current_match):
                result = result[len(self.current_match):].strip()
            return result

        match = None
        for leaf in self.matchable_leaves_after:
            # Handle successive dictation
            if isinstance(leaf, Dictation):
                if self.is_optional and not leaf.is_optional:
                    # Let the next dictation expansion use the speech.
                    return "%s %s".strip() % (
                        super(Dictation, self)._matches_internal(" "), result)
                elif not self.is_optional and not leaf.is_optional:
                    # This is an error because we can't detect the end of one
                    # expansion's match and the start of the other.
                    raise ExpansionError("cannot match on two successive "
                                         "non-optional Dictation expansions")
                else:
                    break

            pattern = leaf.matching_regex_pattern
            match = pattern.search(result)  # get the first match

            # Break on the first leaf that matches or if a required leaf doesn't
            # match (no point continuing)
            if not match and not leaf.is_optional or match:
                break

        # Let speech to be matched start with a single space in order to match
        # n words easily
        if match:
            result = "%s %s" % (
                super(Dictation, self)._matches_internal(
                    " " + result[0:match.start()]),
                result[match.start():])
        else:
            result = super(Dictation, self)._matches_internal(" " + result)

        # Strip whitespace before returning so that the rule doesn't fail to match
        return result.strip()

    @property
    def matching_regex_pattern(self):
        """
        A regex pattern for matching this expansion.
        """
        if not self._pattern:
            # Match one or more words or digits separated by whitespace
            word = "[\w\d?,\.\-_!;:']+"
            regex = "(\s+%s)+" % word
            self._pattern = re.compile(regex)
        return self._pattern


def dictation_in_expansion(e, no_literals=False):
    dictation_expansions = []
    others = []

    for leaf in e.leaves:
        if isinstance(leaf, Dictation):
            dictation_expansions.append(leaf)
        else:
            others.append(leaf)

    if no_literals:
        return len(dictation_expansions) > 0 and len(others) == 0
    else:
        return len(dictation_expansions) > 0


def only_dictation_in_expansion(e):
    return dictation_in_expansion(e, no_literals=True)


def no_dictation_in_expansion(e):
    return not bool(find_expansion(
        e, lambda x: isinstance(x, Dictation), TraversalOrder.PostOrder
    ))


def dictation_and_literals_in_expansion(e):
    return dictation_in_expansion(e, False)


def expand_dictation_expansion(expansion):
    """
    Take an expansion and expand any AlternativeSet with alternatives containing
    Dictation expansions. This function returns a list of all expanded expansions.
    :type expansion: Expansion
    :return: list
    """
    def is_unprocessed(e):
        if isinstance(e, AlternativeSet):
            jsgf_only_alt = False

            # Not necessarily dictation only, that scenario is handled by
            # expansion sequence and SequenceRule.
            dictation_alts = 0
            for c in e.children:
                if dictation_in_expansion(c):
                    dictation_alts += 1
                else:
                    jsgf_only_alt = True

                if jsgf_only_alt and dictation_alts:
                    return True
                elif dictation_alts > 1:
                    # An AlternativeSet that has two or more dictation expansions
                    # needs further processing
                    return True
        elif isinstance(e, (OptionalGrouping, KleeneStar)):
            if dictation_in_expansion(e):
                return True
            else:
                # Handle the special case of dictation-free optionals in a sequence
                # that has a dictation expansion.

                # Check if there's a sequence ancestor
                p = e
                while p.parent:
                    if isinstance(p, Sequence):
                        break
                    p = p.parent

                if not p or no_dictation_in_expansion(p):
                    # There was no sequence ancestor or there wasn't dictation
                    # anywhere in the sequence
                    return False
                else:  # e requires processing
                    return True
        return False

    def first_unprocessed_expansion(e):
        """
        Find the first expansion in an expansion tree for which is_unprocessed
        returns True.
        :type e: Expansion
        :return: Expansion | None
        """
        if isinstance(e, NamedRuleRef):
            return first_unprocessed_expansion(e.referenced_rule.expansion)
        else:
            # Traverse in post order, i.e. children first, then e.
            for child in e.children:
                result = first_unprocessed_expansion(child)
                if result:
                    return result
            if is_unprocessed(e):
                return e

    def find_goal(e, goal):
        return find_expansion(e, lambda x: x == goal)

    def process(e):
        """
        Process an expansion recursively and return a list of expanded expansions.
        :type e: Expansion
        :return: list
        """
        result = []
        current = first_unprocessed_expansion(e)

        # Handle cases where no processing is required
        if not current:
            return [e]

        copies = []
        if isinstance(current, AlternativeSet):
            # Create a replacements list with copies of the relevant children of
            # the AlternativeSet currently being processed.
            dictation_children = []  # again, not necessarily only dictation.
            jsgf_only_children = []
            for child in current.children:
                # Add a deep copy of each child to one of the above lists.
                if dictation_in_expansion(child):
                    dictation_children.append(child.copy())
                else:
                    jsgf_only_children.append(child.copy())

            if len(jsgf_only_children) == 1:
                replacements = jsgf_only_children
            elif len(jsgf_only_children) > 1:
                replacements = [AlternativeSet(*jsgf_only_children)]
            else:  # no JSGF children
                replacements = []
            replacements.extend(dictation_children)

        elif isinstance(current, (OptionalGrouping, KleeneStar)):
            # Handle not required - remove from a copy
            copy = current.root_expansion.copy()
            copy_x = find_goal(copy, current)
            copy_parent = copy_x.parent
            ancestor = copy_parent

            # Traverse up the parent tree and remove copy_x or one of its ancestors
            # where there is another child
            while ancestor:
                if len(ancestor.children) > 1:
                    ancestor.children.remove(copy_x)
                    break

                copy_x = ancestor
                ancestor = ancestor.parent

            # copy_x or one of its ancestors was removed from the tree correctly
            # If this isn't true, the expansion is an empty tree and shouldn't be
            # added.
            if ancestor:
                copies.append(copy)

            # Let replacement loop handle required
            if isinstance(current, OptionalGrouping):
                replacements = [current.child.copy()]
            else:
                replacements = [Repeat(current.child.copy())]
        else:
            replacements = []

        for replacement in replacements:
            # Find the copy of the current expansion being processed
            copy = current.root_expansion.copy()
            copy_x = find_goal(copy, current)
            copy_parent = copy_x.parent
            if copy_parent:
                index = copy_parent.children.index(copy_x)
                copy_parent.children.remove(copy_x)
                copy_parent.children.insert(index, replacement)
            else:
                # copy is the root expansion.
                copy = replacement
            copies.append(copy)

        for copy in copies:
            next_unprocessed = first_unprocessed_expansion(copy)
            if not next_unprocessed and copy not in result:
                result.append(copy)
            else:
                # Process the next unprocessed expansion and add the results.
                # There are duplicates sometimes, so don't add them.
                for r in process(next_unprocessed):
                    if r not in result:
                        result.append(r)

        return result

    return process(expansion)


def calculate_expansion_sequence(expansion, should_deepcopy=True):
    """
    Split an expansion into 2n expansions where n is the number of Dictation
    expansions in the expansion.

    If there aren't any Dictation expansions, the result will be the original
    expansion.
    :type expansion: Expansion
    :param should_deepcopy: whether to deepcopy the expansion before using it
    :rtype: list
    """
    def generate_expansion_from_children(e, children):
        assert isinstance(e, Expansion)
        assert isinstance(children, (list, tuple))
        if len(children) == 1:
            result = type(e)(children[0])
        elif len(children) > 1:
            result = type(e)(*children)
        else:
            result = None

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
                e = type(parent)(e)

                # Go up to the next parent
                parent = parent.parent

            result.append(e)

        elif len(e.children) == 0:
            if (isinstance(e, NamedRuleRef) and
                    dictation_in_expansion(e.referenced_rule.expansion)):
                result.extend(calculate_sequence(e.referenced_rule.expansion))
            else:
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

    # Only deepcopy the expansion if required
    if should_deepcopy:
        return calculate_sequence(expansion.copy())
    else:
        return calculate_sequence(expansion)
