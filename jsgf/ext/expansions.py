"""
This module contains extension rule expansion classes and functions.
"""

import re

import pyparsing

from ..expansions import (
    AlternativeSet,
    Expansion,
    KleeneStar,
    Literal,
    NamedRuleRef,
    OptionalGrouping,
    Repeat,
    Sequence,
    TraversalOrder,
    find_expansion,
)

# Define the regular expression used for dictation words.
_word_regex_str = r"[\w\d?,\.\-_!;:']+"


def _collect_from_leaves(e, backtrack):
    result = []
    look_further = True
    for leaf in e.leaves:
        if isinstance(leaf, Dictation):
            # Add regex for a single dictation word.
            result.append(_word_regex_str)
        elif isinstance(leaf, Literal):
            # Add first word of literal.
            result.append(leaf.text.split()[0])
        else:
            # Skip references.
            continue

        # Break out of the loop if the leaf is required.
        if not leaf.is_optional:
            if not backtrack:
                look_further = False
            break
    return result, look_further


def _collect_next_literals(stack, i, look_further, backtrack):
    """
    Build a list of each next literal using a stack of expansions and their parents
    as well as an index for which stack frame to use.

    The stack has the following structure:
    [(e, e.parent), (e.parent, e.parent.parent), ... (root.children[x], root)]
    :param stack: list
    :param i: int
    :param look_further: bool
    :param backtrack: bool
    :returns: tuple of literals list and flags value
    """
    # Handle stop looking for literals or i being an invalid index.
    if not look_further or i < 0 or i >= len(stack):
        return [], look_further

    # Get the current child and parent from the stack.
    p1, p2 = stack[i]
    result = []

    if isinstance(p2, Sequence):
        # Get the index of p1 in p2.children using 'is'.
        j = 0
        for j, c in enumerate(p2.children):
            if c is p1:
                break

        # Collect the first word of each literal until a required one is found.
        # This won't collect the same repeating dictation from backtracking.
        child_slice = p2.children[:j] if backtrack else p2.children[j + 1:]
        for c in child_slice:
            leaves, look_further = _collect_from_leaves(c, backtrack)
            result.extend(leaves)

            # Stop if a required literal has been collected.
            if not look_further:
                break

    elif isinstance(p2, Repeat):
        # If we get to a repeat, it means that there were no required literals below
        # it *after* the dictation expansion. Backtrack to search before it instead.
        next_stack_result = _collect_next_literals(stack, i - 1, look_further, True)
        result.extend(next_stack_result[0])
        look_further = look_further or next_stack_result[1]

    elif isinstance(p2, AlternativeSet) and backtrack:
        # Handle backtracking through repeating alternatives. Non-repeating
        # alternative sets in the stack won't have next literals.
        for c in p2.children:
            # Collect the next literals from each alternative; any of them could be
            # matched after dictation.
            leaves, look_further = _collect_from_leaves(c, backtrack)
            result.extend(leaves)

    # Go to the next logical stack frame.
    if backtrack:
        next_stack_result = _collect_next_literals(stack, i - 1, look_further,
                                                   backtrack)
    else:
        next_stack_result = _collect_next_literals(stack, i + 1, look_further,
                                                   backtrack)

    result.extend(next_stack_result[0])
    look_further = look_further or next_stack_result[1]
    return result, look_further


class Dictation(Literal):
    """
    Class representing dictation input matching any spoken words.

    This is largely based on the ``Dictation`` element class in the dragonfly Python
    library.

    ``Dictation`` expansions compile to a special reference (``<DICTATION>``),
    similar to :class:`NullRef` and :class:`VoidRef`. See the
    :class:`DictationGrammar` class if you want to use this expansion type with CMU
    Pocket Sphinx.

    The matching implementation for ``Dictation`` expansions will look ahead for
    possible next literals to avoid matching them and making the rule fail to
    match. It will also look backwards for literals in possible future repetitions.

    It will **not** however look at referencing rules for next possible
    literals. If you have match failures because of this, only use ``Dictation``
    expansions in public rules *or* use the ``JointTreeContext`` class before
    matching if you don't mind reducing the matching performance.
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

    def __hash__(self):
        # A Dictation hash is a hash of the class name and each ancestor's string
        # representation.
        ancestors = []
        p = self.parent
        while p:
            ancestors.append("%s" % p)
            p = p.parent
        return hash("%s: %s" % (self.__class__.__name__,
                                ",".join(ancestors)))

    def validate_compilable(self):
        pass

    def compile(self, ignore_tags=False):
        super(Dictation, self).compile()
        output = "<DICTATION>"
        if self.tag and not ignore_tags:
            return "%s%s" % (output, self.compiled_tag)
        else:
            return output

    @property
    def use_current_match(self):
        """
        Whether to match the ``current_match`` value next time rather than matching
        one or more words.

        This is used by the ``SequenceRule.graft_sequence_matches`` method.

        :returns: bool
        """
        return self._use_current_match

    @use_current_match.setter
    def use_current_match(self, value):
        self._use_current_match = value

        # Invalidate the matcher.
        self.invalidate_matcher()

    def _make_matcher_element(self):
        # Handle the case where use_current_match is True.
        if self.use_current_match is True:
            current_match = self.current_match
            if current_match is None:
                result = pyparsing.NoMatch()
            elif current_match == "":
                result = pyparsing.Empty()
            else:
                result = pyparsing.Literal(self.current_match)

            # Set the parse action and return the element.
            return result.setParseAction(self._parse_action)

        # Otherwise build a list of next possible literals. Make the required stack
        # of child-parent pairs.
        stack = []
        p1, p2 = self, self.parent
        while p1 and p2:
            stack.append((p1, p2))

            # Move both pivots further up the tree.
            p1 = p1.parent
            p2 = p2.parent

        # Build a list of next literals using the stack.
        next_literals, _ = _collect_next_literals(stack, 0, True, False)

        # De-duplicate the list.
        next_literals = set(next_literals)

        word = pyparsing.Regex(_word_regex_str, re.UNICODE)
        if next_literals:
            # Check if there is a next dictation literal. If there is, only match
            # one word for this expansion.
            if _word_regex_str in next_literals:
                result = word

            # Otherwise build an element to match one or more words stopping on
            # any of the next literals so that they aren't matched as dictation.
            else:
                next_literals = list(map(pyparsing.Literal, next_literals))
                result = pyparsing.OneOrMore(
                    word, stopOn=pyparsing.Or(next_literals)
                )
        else:
            # Handle the case of no literals ahead by allowing one or more Unicode
            # words without restrictions.
            result = pyparsing.OneOrMore(word)

        return self._set_matcher_element_attributes(result)

    @property
    def matching_regex_pattern(self):
        """
        A regex pattern for matching this expansion.

        This property has been left in for backwards compatibility.
        The ``Expansion.matches`` method now uses the ``matcher_element`` property
        instead.

        :returns: regex pattern object
        """
        # Match one or more words or digits separated by whitespace
        regex = "%s(\s+%s)*" % (_word_regex_str, _word_regex_str)
        return re.compile(regex, re.UNICODE)


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
    Take an expansion and expand any ``AlternativeSet`` with alternatives containing
    ``Dictation`` expansions. This function returns a list of all expanded
    expansions.

    :param expansion: Expansion
    :returns: list
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
        :param e: Expansion
        :returns: Expansion | None
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

        :param e: Expansion
        :returns: list
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
    Split an expansion into `2*n` expansions where `n` is the number of
    ``Dictation`` expansions in the expansion tree.

    If there aren't any ``Dictation`` expansions, the result will be the original
    expansion.

    :param expansion: Expansion
    :param should_deepcopy: whether to deepcopy the expansion before using it
    :returns: list
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

        :param e: Expansion
        :returns: list
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

            # Remove and process each child from left to right.
            while len(e.children) > 0:
                # Keep the parent relationship, as it is used above.
                c = e.children.pop(0)
                c.parent = e
                child_result = calculate_sequence(c)

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
