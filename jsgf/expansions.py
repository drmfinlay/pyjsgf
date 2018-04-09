"""
Classes for compiling JSpeech Grammar Format expansions
"""
import re
from copy import deepcopy

from .references import BaseRef
from .errors import *


class TraversalOrder(object):
    PreOrder, PostOrder = list(range(2))


def map_expansion(e, func=lambda x: x, order=TraversalOrder.PreOrder):
    """
    Traverse an expansion tree and call func on each expansion returning a tuple
    structure with the results.
    :type e: Expansion
    :param func: callable (default: the identity function, f(x)->x)
    :type order: int
    :return: tuple
    """
    def map_children(x):
        if isinstance(x, RuleRef):  # map the referenced rule
            return map_expansion(x.referenced_rule.expansion, func, order)
        else:
            return tuple([map_expansion(child, func, order)
                          for child in x.children])

    if order == TraversalOrder.PreOrder:
        return func(e), map_children(e)
    elif order == TraversalOrder.PostOrder:
        return map_children(e), func(e)
    else:
        raise ValueError("order should be either %d for pre-order or %d for "
                         "post-order" % (TraversalOrder.PreOrder,
                                         TraversalOrder.PostOrder))


def flat_map_expansion(e, func=lambda x: x, order=TraversalOrder.PreOrder):
    """
    Call map_expansion with the arguments and return a single flat list.
    :type e: Expansion
    :param func: callable (default: the identity function, f(x)->x)
    :type order: int
    :return: list
    """
    result = []

    def flatten(x):
        result.append(func(x))

    map_expansion(e, flatten, order)

    return result


def filter_expansion(e, func=lambda x: x, order=TraversalOrder.PreOrder):
    """
    Find all expansions in an expansion tree for which func(x) == True.
    :type e: Expansion
    :param func: callable (default: the identity function, f(x)->x)
    :type order: int
    :return: list
    """
    result = []

    def filter_(x):
        if func(x):
            result.append(x)

    map_expansion(e, filter_, order)

    return result


def save_current_matches(e):
    """
    Traverse an expansion tree and return a dictionary with all current_matches
    saved.

    :type e: Expansion
    :return: dict
    """
    values = {}

    def save(x):
        values[x] = x.current_match
    map_expansion(e, save)
    return values


def restore_current_matches(e, values, override_none=True):
    """
    Traverse an expansion tree and set e.current_match to its value in the
    dictionary or None:
    e.current_match = values[e, None]

    :type e: Expansion
    :type values: dict
    :param override_none:
    """
    def restore(x):
        if not override_none and values.get(x, None) is not None:
            x.current_match = values.get(x, None)
    map_expansion(e, restore)


def matches_overlap(m1, m2):
    """
    Check whether two regex matches overlap.
    :return: bool
    """
    if not m1 or not m2 or m1.string != m2.string:
        return False
    x1, y1 = m1.span()
    x2, y2 = m2.span()
    return x1 < x2 <= y1 or x2 < x1 <= y2 or x1 == x2


class JointTreeContext(object):
    """
    Class used during matching to temporarily join an expansion tree with the
    expansion trees of all referenced rules.

    This is required when it is necessary to view an expansion tree and the
    expansion trees of referenced rules as one larger tree. E.g. when determining
    mutual exclusivity of two expansions, if an expansion is optional or used for
    repetition in the context of other trees, etc.

    On __exit__, the trees will be detached recursively.

    This class can be used with Python's 'with' statement:
    with JointTreeContext(expansion):
        pass
    """

    def __init__(self, root_expansion):
        self._root = root_expansion

    @staticmethod
    def join_tree(x):
        """
        If x is a RuleRef, join its referenced rule's expansion to this tree.
        :type x: Expansion
        """
        if isinstance(x, RuleRef):
            # Set the parent of the referenced rule's root expansion to this
            # expansion.
            x.referenced_rule.expansion.parent = x

    @staticmethod
    def detach_tree(x):
        """
        If x is a RuleRef, detach its referenced rule's expansion from this tree.
        :type x: Expansion
        """
        if isinstance(x, RuleRef):
            # Reset parent
            x.referenced_rule.expansion.parent = None

    def __enter__(self):
        map_expansion(self._root, self.join_tree)

    def __exit__(self, exc_type, exc_val, exc_tb):
        map_expansion(self._root, self.detach_tree)


class Expansion(object):
    """
    Expansion base class
    """
    def __init__(self, children):
        self._tag = None
        self._parent = None
        if not isinstance(children, (tuple, list)):
            raise TypeError("'children' must be a list or tuple")

        # Transform any non-expansion children into expansions
        self._children = [self.make_expansion(e) for e in children]

        # Set each child's parent as this expansion
        for child in self._children:
            child.parent = self

        self._current_match = None
        self.rule = None

    def __add__(self, other):
        return self + other

    def __hash__(self):
        return self.__str__().__hash__()

    def __copy__(self):
        if not self.children:
            e = type(self)([])
        else:
            e = type(self)(*self.children)
        e.tag = self.tag
        return e

    def __deepcopy__(self, memo):
        if not self.children:
            e = type(self)([])
        else:
            children = [deepcopy(child, memo) for child in self.children]
            e = type(self)(*children)
        e.tag = self.tag
        return e

    def copy(self, shallow=False):
        """
        Make a copy of this expansion. This returns a deep copy by default.
        Neither referenced rules or their expansions will be deep copied.
        :param shallow: whether to create a shallow copy (default: False)
        :rtype: Expansion
        """
        if shallow:
            return self.__copy__()
        else:
            return self.__deepcopy__({})

    @property
    def children(self):
        return self._children

    def compile(self, ignore_tags=False):
        self.validate_compilable()
        if self.tag and not ignore_tags:
            return self.tag
        else:
            return ""

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        if isinstance(value, Expansion) or value is None:
            self._parent = value
        else:
            raise AttributeError("'parent' must be an Expansion or None")

    @property
    def tag(self):
        # If the tag is set, return it with a space before it
        # Otherwise return the empty string
        if self._tag:
            return " " + self._tag
        else:
            return ""

    @tag.setter
    def tag(self, value):
        """
        Sets the tag for the expansion.
        :type value: str
        """
        if not value:
            self._tag = ""
        else:
            # Escape '{', '}' and '\' so that tags will be processed
            # properly if they have those characters.
            # This is suggested in the JSGF specification.
            escaped = value.replace("{", "\\{") \
                .replace("}", "\\}") \
                .replace("\\", "\\\\")
            self._tag = "{ %s }" % escaped

    @staticmethod
    def make_expansion(e):
        """
        Take an object, turn it into an Expansion if it isn't one and return it.
        :param e:
        :return: Expansion
        """
        if isinstance(e, Expansion):
            return e
        else:
            # Assume e is a string
            return Literal(e)

    def validate_compilable(self):
        """
        Check that the expansion is compilable. If it isn't, this method should
        raise a CompilationError.
        """
        pass

    @property
    def current_match(self):
        """
        Current speech match.
        """
        return self._current_match

    @current_match.setter
    def current_match(self, value):
        self._set_current_match(value)

    def _set_current_match(self, value):
        # Ensure that string values have only one space between words
        if value:
            value = " ".join([x.strip() for x in value.split()])

        if not value:
            if self.is_optional:
                value = ""
            else:
                value = None

        self._current_match = value

    def reset_for_new_match(self):
        """
        Call reset_match_data for this expansion and all of its descendants.
        """
        map_expansion(self, lambda x: x.reset_match_data())

    def reset_match_data(self):
        """
        Reset any members or properties this expansion uses for matching speech.
        """
        self.current_match = None

    def matches(self, speech):
        """
        Match speech with this expansion, set current_match to the first matched
        substring and return the remainder of the string.

        :type speech: str
        :return: str
        """
        result = speech.lstrip()
        return self._matches_internal(result).strip()

    def _matches_internal(self, speech):
        result = speech
        for child in self.children:
            # Consume speech
            result = child.matches(result)

        # Check if any children returned None as the match
        child_matches = [child.current_match for child in self.children]
        if None in child_matches:
            self.current_match = None
            return speech
        else:
            self.current_match = " ".join(child_matches)
            return result

    def __str__(self):
        descendants = ", ".join(["%s" % c for c in self.children])
        if self.tag:
            return "%s(%s) with tag '%s'" % (self.__class__.__name__,
                                             descendants,
                                             self.tag)
        else:
            return "%s(%s)" % (self.__class__.__name__,
                               descendants)

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return type(self) == type(other) and self.children == other.children

    def __ne__(self, other):
        return not self.__eq__(other)

    def __contains__(self, item):
        return item in flat_map_expansion(self)

    @property
    def is_optional(self):
        """
        Whether or not this expansion has an optional ancestor.
        """
        result = False
        if self.parent:
            result = self.parent.is_optional
        return result

    @property
    def is_alternative(self):
        """
        Whether or not this expansion has an AlternativeSet ancestor with more
        than one child.
        """
        parent = self.parent
        while parent:
            if isinstance(parent, AlternativeSet) and len(parent.children) > 1:
                return True
            parent = parent.parent
        return False

    @property
    def leaves(self):
        leaves = []

        def add_leaf(e):
            if not (e.children or isinstance(e, RuleRef)):
                leaves.append(e)

        map_expansion(self, add_leaf)

        return leaves

    @property
    def root_expansion(self):
        """
        Traverse to the root expansion r and return it.
        :return: Expansion
        """
        r = self
        while r.parent:
            r = r.parent

        return r

    def mutually_exclusive_of(self, other):
        """
        Whether this expansion cannot be spoken with another expansion together.
        :type other: Expansion
        :return: bool
        """
        parent1 = self.parent
        parent2 = other.parent
        e1, e2 = self, other
        s1, s2 = set(), set()
        d1, d2 = {}, {}

        # Add each ancestor of self and other to 2 sets and store which child of
        # parent1/parent2 is [an ancestor of] self/e in 2 dictionaries
        while parent1 or parent2:
            if parent1:
                if isinstance(parent1, AlternativeSet):
                    s1.add(parent1)
                    d1[parent1] = e1
                e1 = parent1
                parent1 = parent1.parent

            if parent2:
                if isinstance(parent2, AlternativeSet):
                    s2.add(parent2)
                    d2[parent2] = e2
                e2 = parent2
                parent2 = parent2.parent

        s3 = s1.intersection(s2)
        if len(s3) == 0:
            # self and other are not mutually exclusive if there is no intersection
            return False
        else:
            for alt_set in s3:
                if d1[alt_set] is not d2[alt_set]:
                    return True
        return False


class NamedRuleRef(BaseRef, Expansion):
    """
    Class used to reference rules by name.
    """
    def __init__(self, name):
        # Call both super constructors
        BaseRef.__init__(self, name)
        Expansion.__init__(self, [])

    def compile(self, ignore_tags=False):
        self.validate_compilable()
        if self.tag and not ignore_tags:
            return "<%s>%s" % (self.name, self.tag)
        else:
            return "<%s>" % self.name

    def __str__(self):
        return "%s('%s')" % (self.__class__.__name__, self.name)

    def __hash__(self):
        return Expansion.__hash__(self)

    def __copy__(self):
        e = type(self)(self.name)
        e.tag = self.tag
        return e

    def __deepcopy__(self, memo):
        return self.__copy__()


class NullRef(NamedRuleRef):
    """
    The NULL rule is a rule that is automatically matched without the user speaking.
    """
    def __init__(self):
        super(NullRef, self).__init__("NULL")

    def _matches_internal(self, speech):
        return ""

    def _set_current_match(self, value):
        self._current_match = ""

    @staticmethod
    def valid(name):
        return name == "NULL"

    def __copy__(self):
        e = type(self)()
        e.tag = self.tag
        return e

    def __hash__(self):
        return super(NullRef, self).__hash__()


class VoidRef(NamedRuleRef):
    """
    The VOID rule is a rule that can never be spoken. As such, if this is used in
    an expansion, it will not match, even if the expansion is optional.
    """
    def __init__(self):
        super(VoidRef, self).__init__("VOID")

    def _matches_internal(self, speech):
        return speech

    def _set_current_match(self, value):
        self._current_match = None

    @staticmethod
    def valid(name):
        return name == "VOID"

    def __copy__(self):
        e = type(self)()
        e.tag = self.tag
        return e

    def __hash__(self):
        return super(VoidRef, self).__hash__()


class ExpansionWithChildren(Expansion):
    def compile(self, ignore_tags=False):
        # Add a reference to the built-in VOID rule to produce a valid JSGF
        # expansion that compiles, but cannot be matched.
        if not self.children:
            self.children.append(VoidRef())


class SingleChildExpansion(ExpansionWithChildren):
    def __init__(self, expansion):
        super(SingleChildExpansion, self).__init__([expansion])

    @property
    def child(self):
        if not self.children:
            return None  # the child has been removed
        else:
            return self.children[0]

    def __hash__(self):
        return super(SingleChildExpansion, self).__hash__()


class VariableChildExpansion(ExpansionWithChildren):
    def __init__(self, *expansions):
        super(VariableChildExpansion, self).__init__(expansions)

    def __hash__(self):
        return super(VariableChildExpansion, self).__hash__()


class Sequence(VariableChildExpansion):
    def compile(self, ignore_tags=False):
        super(Sequence, self).compile()
        seq = " ".join([
            e.compile(ignore_tags) for e in self.children
        ])

        # Return the sequence and the tag if there is one
        if self.tag and not ignore_tags:
            return "%s%s" % (seq, self.tag)
        else:
            return seq

    def __hash__(self):
        return super(Sequence, self).__hash__()


class Literal(Expansion):
    def __init__(self, text):
        # CMU Sphinx recognizers use dictionaries with lower case words only
        # So use lower() to fix errors similar to:
        # "The word 'HELLO' is missing in the dictionary"
        self.text = text.lower()
        self._pattern = None
        super(Literal, self).__init__([])

    def __str__(self):
        return "%s('%s')" % (self.__class__.__name__, self.text)

    def __hash__(self):
        return super(Literal, self).__hash__()

    def __copy__(self):
        e = type(self)(self.text)
        e.tag = self.tag
        return e

    def __deepcopy__(self, memo):
        return self.__copy__()

    def validate_compilable(self):
        if not self.text:
            raise CompilationError("%s expansion cannot be compiled with a text "
                                   "value of '%s'"
                                   % (self.__class__.__name__, self.text))

    def compile(self, ignore_tags=False):
        super(Literal, self).compile()
        if self.tag and not ignore_tags:
            return "%s%s" % (self.text, self.tag)
        else:
            return self.text

    @property
    def matching_regex_pattern(self):
        """
        A regex pattern for matching this expansion.
        """
        if not self._pattern:
            # Selectively escape certain characters because this text will
            # be used in a regular expression pattern string.
            #
            escaped = self.text.replace(".", r"\.")

            # Also make everything lowercase and allow matching 1 or more
            # whitespace characters between words and before the first word.
            words = escaped.lower().split()

            # Create and set a regex pattern to use
            regex = "%s" % "\s+".join(words)
            self._pattern = re.compile(regex)
        return self._pattern

    @property
    def leaves_after(self):
        """
        Generator function for leaves after this one (if any).
        :return: generator
        """
        self_reached = False
        leaves = self.root_expansion.leaves
        for leaf in leaves:
            if leaf is self:
                self_reached = True
                continue
            elif self_reached:
                yield leaf

    @property
    def matchable_leaves_after(self):
        """
        Generator function yielding all leaves after self that are not mutually
        exclusive of it.
        :return: generator
        """
        for leaf in self.leaves_after:
            if not self.mutually_exclusive_of(leaf):
                yield leaf

    def _matches_internal(self, speech):
        result = speech
        match = self.matching_regex_pattern.match(result)

        if not match:
            self.current_match = None
            return result

        repetition_ancestor = self.repetition_ancestor
        use_match = True
        if self.is_optional or repetition_ancestor:
            # Check if there are non-optional unprocessed leaves with only one
            # match that overlaps with this expansion's match
            leaves_after = list(self.matchable_leaves_after)
            for leaf in leaves_after:
                if leaf.is_optional and not leaf.repetition_ancestor:
                    continue

                leaf_pattern = leaf.matching_regex_pattern
                leaf_matches = [_ for _ in leaf_pattern.finditer(result)]

                overlapping_matches = []
                for m in leaf_matches:
                    if matches_overlap(match, m):
                        overlapping_matches.append(m)

                if len(overlapping_matches) == 0 and len(leaf_matches) > 0:
                    use_match = True
                else:
                    use_match = len(leaf_matches) > len(overlapping_matches)

                if repetition_ancestor and use_match:
                    def pattern_matches_self(l):
                        return (l.matching_regex_pattern.pattern ==
                                self.matching_regex_pattern.pattern)

                    message = "self and leaf are ambiguous literals used by " \
                              "one or more repetition expansions"
                    if pattern_matches_self(leaf) and leaf.repetition_ancestor:
                        raise MatchError(message)
                    else:
                        for x in leaves_after:
                            if pattern_matches_self(x):
                                raise MatchError(message)
                            else:
                                break
                break
        if use_match:
            self.current_match = match.group()
            result = result[match.end():]
        else:
            self.current_match = None

        return result

    def __eq__(self, other):
        return super(Literal, self).__eq__(other) and self.text == other.text

    @property
    def repetition_ancestor(self):
        """
        This expansion's closest Repeat or KleeneStar ancestor, if it has one.
        :return: Expansion
        """
        parent = self.parent
        result = None
        while parent:
            if isinstance(parent, Repeat):
                result = parent
                break
            parent = parent.parent

        return result


class RuleRef(NamedRuleRef):
    def __init__(self, referenced_rule):
        """
        Class for referencing another rule by Rule object.
        :param referenced_rule:
        """
        super(RuleRef, self).__init__(referenced_rule.name)
        self.referenced_rule = referenced_rule

    def _matches_internal(self, speech):
        result = self.referenced_rule.expansion.matches(speech)
        self.current_match = self.referenced_rule.expansion.current_match
        return result

    def __eq__(self, other):
        return (super(RuleRef, self).__eq__(other) and
                self.referenced_rule == other.referenced_rule)

    def __copy__(self):
        e = type(self)(self.referenced_rule)
        e.tag = self.tag
        return e

    def __deepcopy__(self, memo):
        # Note that this implementation won't copy the referenced rule
        return self.__copy__()

    def __hash__(self):
        return super(RuleRef, self).__hash__()


class Repeat(SingleChildExpansion):
    """
    JSGF plus operator for allowing one or more repeats of an expansion.
    For example:
    <repeat> = (please)+ don't crash;
    """
    def __init__(self, expansion):
        super(Repeat, self).__init__(expansion)
        self._repetition_limit = None
        self._repetitions_matched = None

    def compile(self, ignore_tags=False):
        super(Repeat, self).compile()
        compiled = self.child.compile(ignore_tags)
        if self.tag and not ignore_tags:
            return "(%s)+%s" % (compiled, self.tag)
        else:
            return "(%s)+" % compiled

    def __hash__(self):
        return super(Repeat, self).__hash__()

    @property
    def repetitions_matched(self):
        """
        :The number of repetitions last matched.
        :return:
        """
        return self._repetitions_matched

    def _matches_internal(self, speech):
        """
        Specialisation of matches method for repetition expansions.
        A match here is whether every child's current_match value is not None at
        least once.
        :type speech: str
        :return: str
        """
        result = speech
        # Save the state of the expansion tree here
        values = save_current_matches(self)

        # Accept N complete repetitions
        matches = []
        self._repetitions_matched = 0

        # Use a copy of result for repetitions
        intermediate_result = result
        while True:
            # Consume speech
            last_intermediate_result = intermediate_result
            intermediate_result = self.child.matches(intermediate_result)
            child_match = self.child.current_match

            # If the child consumed nothing and still matches, then there is a
            # descendant that is probably a Dictation expansion. So break out of
            # the loop.
            if child_match and intermediate_result == last_intermediate_result:
                break

            if not child_match:
                # Restore current_match state for incomplete repetition tree
                # without overriding current_match strings with None
                restore_current_matches(self, values, override_none=False)
                break
            else:
                matches.append(child_match)
                self._repetitions_matched += 1

                # Save current_match state for complete repetition and update
                # repetitions_matched
                values = save_current_matches(self)

        self.current_match = " ".join(matches)
        return intermediate_result

    def reset_match_data(self):
        super(Repeat, self).reset_match_data()
        self._repetitions_matched = None


class KleeneStar(Repeat):
    """
    JSGF Kleene star operator for allowing zero or more repeats of an expansion.
    For example:
    <kleene> = (please)* don't crash;
    """
    def compile(self, ignore_tags=False):
        super(KleeneStar, self).compile()
        compiled = self.child.compile(ignore_tags)
        if self.tag and not ignore_tags:
            return "(%s)*%s" % (compiled, self.tag)
        else:
            return "(%s)*" % compiled

    @property
    def is_optional(self):
        return True

    def __hash__(self):
        return super(KleeneStar, self).__hash__()


class OptionalGrouping(SingleChildExpansion):
    """
    Expansion that can be spoken in a rule, but doesn't have to be.
    """
    def compile(self, ignore_tags=False):
        super(OptionalGrouping, self).compile()
        compiled = self.child.compile(ignore_tags)
        if self.tag and not ignore_tags:
            return "[%s]%s" % (compiled, self.tag)
        else:
            return "[%s]" % compiled

    @property
    def is_optional(self):
        return True

    def __hash__(self):
        return super(OptionalGrouping, self).__hash__()


class RequiredGrouping(Sequence):
    def compile(self, ignore_tags=False):
        super(RequiredGrouping, self).compile()
        grouping = " ".join([
            e.compile(ignore_tags) for e in self.children
        ])

        if self.tag and not ignore_tags:
            return "(%s%s)" % (grouping, self.tag)
        else:
            return "(%s)" % grouping

    def __hash__(self):
        return super(RequiredGrouping, self).__hash__()


class AlternativeSet(VariableChildExpansion):
    def __init__(self, *expansions):
        self._weights = None
        super(AlternativeSet, self).__init__(*expansions)

    @property
    def weights(self):
        return self._weights

    def __hash__(self):
        return super(AlternativeSet, self).__hash__()

    @weights.setter
    def weights(self, value):
        self._weights = value

    def compile(self, ignore_tags=False):
        super(AlternativeSet, self).compile()
        if self.weights:
            # Create a string with w=weight and e=compiled expansion
            # such that:
            # /<w 0>/ <e 0> | ... | /<w n-1>/ <e n-1>
            alt_set = "|".join([
                "/%f/ %s" % (self.weights[i],
                             e.compile(ignore_tags))
                for i, e in enumerate(self.children)
            ])
        else:
            # Or do the same thing without the weights
            alt_set = "|".join([
                e.compile(ignore_tags) for e in self.children
            ])

        if self.tag and not ignore_tags:
            return "(%s%s)" % (alt_set, self.tag)
        else:
            return "(%s)" % alt_set

    def _matches_internal(self, speech):
        result = speech
        self.current_match = None
        for child in self.children:
            # Consume speech
            result = child.matches(result)
            child_match = child.current_match
            if child_match:
                self.current_match = child_match
                break

        if self.current_match is None:
            result = speech

        return result

    def __eq__(self, other):
        if type(self) != type(other) or len(self.children) != len(other.children):
            return False
        else:
            # Check that the children lists have the same contents, but the
            # ordering can be different.
            for child in self.children:
                if child not in other.children:
                    return False
            return True

    @property
    def is_alternative(self):
        return True
