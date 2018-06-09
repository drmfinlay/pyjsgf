"""
Classes for compiling JSpeech Grammar Format expansions
"""
import re

from copy import deepcopy
from six import string_types

from .references import BaseRef
from .errors import *


class TraversalOrder(object):
    PreOrder, PostOrder = list(range(2))


def map_expansion(e, func=lambda x: x, order=TraversalOrder.PreOrder,
                  shallow=False):
    """
    Traverse an expansion tree and call func on each expansion returning a tuple
    structure with the results.
    :type e: Expansion
    :param func: callable (default: the identity function, f(x)->x)
    :type order: int
    :param shallow: whether to not process trees of referenced rules (default False)
    :return: tuple
    """
    def map_children(x):
        if isinstance(x, RuleRef) and not shallow:  # map the referenced rule
            return map_expansion(x.referenced_rule.expansion, func, order, shallow)
        else:
            return tuple([map_expansion(child, func, order, shallow)
                          for child in x.children])

    if order == TraversalOrder.PreOrder:
        return func(e), map_children(e)
    elif order == TraversalOrder.PostOrder:
        return map_children(e), func(e)
    else:
        raise ValueError("order should be either %d for pre-order or %d for "
                         "post-order" % (TraversalOrder.PreOrder,
                                         TraversalOrder.PostOrder))


def find_expansion(e, func=lambda x: x, order=TraversalOrder.PreOrder,
                   shallow=False):
    """
    Find the first expansion in an expansion tree for which func(x) is True
    and return it. Otherwise return None.

    This function will stop searching once a matching expansion is found, unlike
    filter_expansion.

    :type e: Expansion
    :param func: callable (default: the identity function, f(x)->x)
    :type order: int
    :param shallow: whether to not process trees of referenced rules (default False)
    :return: Expansion | None
    """
    def find_in_children(x):
        # Find in the referenced rule's tree
        if isinstance(x, RuleRef) and not shallow:
            return find_expansion(x.referenced_rule.expansion, func, order, shallow)
        else:
            for child in x.children:
                child_result = find_expansion(child, func, order, shallow)
                if child_result:
                    return child_result

    if order == TraversalOrder.PreOrder:
        # Check e first, then the children if func(e) is None.
        if func(e):
            return e
        else:
            return find_in_children(e)
    elif order == TraversalOrder.PostOrder:
        # Check children first, then e if find_in_children returns None.
        result = find_in_children(e)
        if result:
            return result
        elif func(e):
            return e
    else:
        raise ValueError("order should be either %d for pre-order or %d for "
                         "post-order" % (TraversalOrder.PreOrder,
                                         TraversalOrder.PostOrder))


def flat_map_expansion(e, func=lambda x: x, order=TraversalOrder.PreOrder,
                       shallow=False):
    """
    Call map_expansion with the arguments and return a single flat list.
    :type e: Expansion
    :param func: callable (default: the identity function, f(x)->x)
    :type order: int
    :param shallow: whether to not process trees of referenced rules (default False)
    :return: list
    """
    result = []

    def flatten(x):
        result.append(func(x))

    map_expansion(e, flatten, order, shallow)

    return result


def filter_expansion(e, func=lambda x: x, order=TraversalOrder.PreOrder,
                     shallow=False):
    """
    Find all expansions in an expansion tree for which func(x) == True.
    :type e: Expansion
    :param func: callable (default: the identity function, f(x)->x)
    :type order: int
    :param shallow: whether to not process trees of referenced rules (default False)
    :return: list
    """
    result = []

    def filter_(x):
        if func(x):
            result.append(x)

    map_expansion(e, filter_, order, shallow)

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
        map_expansion(self._root, self.join_tree, TraversalOrder.PostOrder)

    def __exit__(self, exc_type, exc_val, exc_tb):
        map_expansion(self._root, self.detach_tree, TraversalOrder.PostOrder)


class Expansion(object):
    """
    Expansion base class
    """

    _NO_CALCULATION = object()

    def __init__(self, children):
        self._tag = ""
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

        # Internal member used for caching calculations. Initially None as this
        # member is only used on root expansions, no sense in creating lots of
        # unused dictionaries.
        self._lookup_dict = None

    def __add__(self, other):
        return self + other

    def __hash__(self):
        # The hash of an expansion is a combination of the class name, tag and
        # hashes of children, similar to expansion string representations.
        child_hashes = [hash(c) for c in self.children]
        return hash(
            "%s(%s)%s" % (self.__class__.__name__, child_hashes, self.tag)
        )

    def __copy__(self):
        if not self.children:
            e = type(self)([])
        else:
            e = type(self)(self.children)
        e.tag = self.tag
        return e

    def __deepcopy__(self, memo):
        if not self.children:
            e = type(self)([])
        else:
            children = [deepcopy(child, memo) for child in self.children]
            e = type(self)(children)
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
            return self.compiled_tag
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
        """
        JSGF tag for this expansion.
        :rtype: str
        """
        return self._tag

    @tag.setter
    def tag(self, value):
        """
        Sets the tag for the expansion.
        :type value: str
        """
        if not value:
            self._tag = ""
        elif isinstance(value, string_types):
            self._tag = value.strip()
        else:
            raise TypeError("expected JSGF tag string, got %s instead" % value)

    @property
    def compiled_tag(self):
        """
        Get the compiled tag for this expansion if it has one. The empty string is
        returned if there is no tag set.
        :rtype: str
        """
        if not self.tag:
            return ""
        else:
            # Escape '{', '}' and '\' so that tags will be processed
            # properly if they have those characters.
            # This is suggested in the JSGF specification.
            escaped = self.tag.replace("{", "\\{") \
                .replace("}", "\\}") \
                .replace("\\", "\\\\")
            return " { %s }" % escaped

    @staticmethod
    def make_expansion(e):
        """
        Take an object, turn it into an Expansion if it isn't one and return it.
        :param e:
        :return: Expansion
        """
        if isinstance(e, Expansion):
            return e
        elif isinstance(e, string_types):
            return Literal(e)
        else:
            raise TypeError("expected a string or Expansion, got %s instead"
                            % e)

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
        if isinstance(value, string_types):
            # Ensure that string values have only one space between words
            value = " ".join([x.strip() for x in value.split()])
        elif value is not None:
            raise TypeError("current_match must be a string or None")

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

        If the required descendants of an expansion don't match, the match data for
        the expansion and all of its descendants will be reset and the original
        speech string will be returned.

        :type speech: str
        :return: consumed / unconsumed speech string
        """
        result = speech.lstrip()
        return self._matches_internal(result).strip()

    def _matches_internal(self, speech):
        """
        Expansion subclasses should override this internal method to set the
        current_match values for self and for any children.
        :type speech: str
        :return: consumed / unconsumed speech string
        """
        # Don't consume speech strings by default.
        return speech

    def _init_lookup(self):
        """
        Initialises the lookup dictionary for the root expansion.
        If the lookup is already initialised, this does nothing.
        """
        if not self._lookup_dict:
            self._lookup_dict = {
                "is_descendant_of": {},
                "mutually_exclusive_of": {}
            }

    def _store_calculation(self, name, key, value):
        """
        Put a calculation into a named lookup dictionary.
        This method will always store calculation data in the root expansion.
        :type name: str
        :param key: object used to store the calculation result (e.g. a tuple)
        :param value: calculation result | Expansion._NO_CALCULATION
        """
        # Get the root expansion.
        root = self.root_expansion

        # Initialise the lookup dictionary as required.
        root._init_lookup()

        # Always use IDs for the key instead. This way calculations are stored for
        # exact expansions, rather than for any other comparable expansions.
        if isinstance(key, (tuple, list)):
            # Map each object x in 'key' to id(x)
            id_key = tuple(map(lambda x: id(x), key))
        else:
            id_key = id(key)

        if value is self._NO_CALCULATION:
            # Drop the stored value, if there is one.
            root._lookup_dict[name].pop(id_key, None)
        else:
            # Otherwise store 'value' under the 'name' dictionary using 'id_key'.
            root._lookup_dict[name][id_key] = value

    def _lookup_calculation(self, name, key):
        """
        Check if a calculation has already been made and return it. If no
        calculation has been made, Expansion._NO_CALCULATION will be returned.
        This method will always check for calculations using the root expansion.
        :type name: str
        :param key: object used to store the calculation result (e.g. a tuple)
        :returns: calculation result | Expansion._NO_CALCULATION
        """
        # Get the root expansion.
        root = self.root_expansion

        # Initialise the lookup dictionary as required.
        root._init_lookup()

        # Always use IDs for the key instead. This way calculations are stored for
        # exact expansions, rather than for any other comparable expansions.
        if isinstance(key, (tuple, list)):
            # Map each object x in 'key' to id(x)
            id_key = tuple(map(lambda x: id(x), key))
        else:
            id_key = id(key)

        # Return the value from the relevant dictionary or _NO_CALCULATION if it
        # hasn't been calculated yet.
        return root._lookup_dict[name].get(id_key, self._NO_CALCULATION)

    def invalidate_calculations(self):
        """
        Invalidate calculations stored in the lookup tables that involve this
        expansion. This currently only effects `mutually_exclusive_of` and
        `is_descendant_of`.

        This should be called if a child is added to an expansion or if the
        an expansion's parent is changed outside of what `JointTreeContext` does.

        Some changes may also require invalidating descendants, the `map_expansion`
        function can be used with this method to accomplish that:
        `map_expansion(self, Expansion.invalidate_calculations)`
        """
        root = self.root_expansion
        if not root._lookup_dict:
            return  # nothing to invalidate

        for d in root._lookup_dict.values():
            for k, v in d.items():
                # Assume k is either an expansion or an iterable of expansions
                if self is k or isinstance(k, (tuple, list)) and self in k:
                    assert isinstance(d, dict)
                    d.pop(k)
                # Do something similar for values
                elif self is v or isinstance(v, (tuple, list)) and self in k:
                    d.pop(k)

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

    def collect_leaves(self, order=TraversalOrder.PreOrder, shallow=False):
        """
        Collect all descendants of an expansion that have no children.
        This can include self if it has no children. RuleRefs are also counted as
        leaves.
        :param order: tree traversal order (default 0: pre-order)
        :param shallow: whether to not collect leaves from trees of referenced rules
        :return: list
        """
        return filter_expansion(
            self, lambda x: not x.children, order=order, shallow=shallow
        )

    leaves = property(collect_leaves)

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

    def is_descendant_of(self, other):
        """
        Whether this expansion is a descendant of another expansion.
        :type other: Expansion
        :rtype: bool
        """
        if self is other:
            return False

        calc_name = "is_descendant_of"
        calc = self._lookup_calculation(calc_name, (self, other))
        if calc is not self._NO_CALCULATION:
            return calc

        # Return whether self is in other's expansion tree.
        result = bool(find_expansion(other, lambda x: x is self))
        self._store_calculation(calc_name, (self, other), result)
        return result

    def mutually_exclusive_of(self, other):
        """
        Whether this expansion cannot be spoken with another expansion.
        :type other: Expansion
        :return: bool
        """
        root = self.root_expansion
        # Trees are not joined, so we cannot guarantee mutual exclusivity.
        if root is not other.root_expansion:
            return False

        calc_name = "mutually_exclusive_of"

        # Check if this has been calculated before. Check (other, self) too; mutual
        # exclusivity is commutative.
        calc = self._lookup_calculation(calc_name, (self, other))
        if calc is self._NO_CALCULATION:
            calc = self._lookup_calculation(calc_name, (other, self))

        if calc is not self._NO_CALCULATION:
            return calc

        def add_leaf(x):
            if not x.children:
                self._store_calculation(calc_name, (x, self), True)
                self._store_calculation(calc_name, (x, other), True)

        def valid_alt_set(x):
            if isinstance(x, AlternativeSet) and len(x.children) > 1:
                e1, e2 = None, None
                for child in x.children:
                    # If they haven't been found, check if child is self or self's
                    # ancestor, or if child is other or other's ancestor.
                    if not e1 and (self.is_descendant_of(child) or self is child):
                        e1 = child

                    if not e2 and (other.is_descendant_of(child) or other is child):
                        e2 = child

                    if e1 and e2:
                        break
                # This is the expansion we're looking for if self and other descend
                # from it and if they are not both [descended from] the same child
                # of x.
                valid = e1 and e2 and e1 is not e2

                if valid:
                    # Add siblings / their leaf expansions in the expansion tree as
                    # mutually exclusive to self and other
                    for child in filter(lambda c: c is not e1 and c is not e2,
                                        x.children):
                        map_expansion(child, add_leaf, shallow=True)

                return valid

        # Calculate mutually exclusivity, cache the calculation in root._lookup_dict
        # and return the result.
        result = bool(find_expansion(root, valid_alt_set))
        root._store_calculation(calc_name, (self, other), result)
        return result


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
            return "<%s>%s" % (self.name, self.compiled_tag)
        else:
            return "<%s>" % self.name

    def __str__(self):
        return "%s('%s')" % (self.__class__.__name__, self.name)

    def __hash__(self):
        return hash("%s" % self)

    def __eq__(self, other):
        return Expansion.__eq__(self, other) and BaseRef.__eq__(self, other)

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

    def __copy__(self):
        # This should raise an error if self.child is None.
        e = type(self)(self.child)
        e.tag = self.tag
        return e

    def __deepcopy__(self, memo):
        e = type(self)(deepcopy(self.child, memo))
        e.tag = self.tag
        return e


class VariableChildExpansion(ExpansionWithChildren):
    def __init__(self, *expansions):
        super(VariableChildExpansion, self).__init__(expansions)

    def __hash__(self):
        return super(VariableChildExpansion, self).__hash__()

    def __copy__(self):
        if not self.children:
            e = type(self)()
        else:
            e = type(self)(*self.children)
        e.tag = self.tag
        return e

    def __deepcopy__(self, memo):
        if not self.children:
            e = type(self)()
        else:
            children = [deepcopy(child, memo) for child in self.children]
            e = type(self)(*children)
        e.tag = self.tag
        return e


class Sequence(VariableChildExpansion):
    def compile(self, ignore_tags=False):
        super(Sequence, self).compile()
        seq = " ".join([
            e.compile(ignore_tags) for e in self.children
        ])

        # Return the sequence and the tag if there is one
        if self.tag and not ignore_tags:
            return "%s%s" % (seq, self.compiled_tag)
        else:
            return seq

    def _matches_internal(self, speech):
        result = speech
        for child in self.children:
            # Consume speech
            result = child.matches(result)

            # Child was non-optional and did not match, so break.
            if child.current_match is None:
                break

        # Check if any children returned None as the match
        child_matches = [child.current_match for child in self.children]
        if None in child_matches:
            # Reset match data for this subtree and return the original speech
            # string; this was an incomplete match.
            self.reset_for_new_match()
            return speech
        else:
            self.current_match = " ".join(child_matches)
            return result

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
        return hash("%s" % self)

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
            return "%s%s" % (self.text, self.compiled_tag)
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
                # Also skip any NamedRuleRefs (or sub class instances)
                if isinstance(leaf, NamedRuleRef) or\
                        (leaf.is_optional and not leaf.repetition_ancestor):
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

                    message = "%s and %s are ambiguous literals used by " \
                              "one or more repetition expansions" % (self, leaf)
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
        return hash("%s%s" % (self.__class__.__name__,
                              hash(self.referenced_rule)))


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
            return "(%s)+%s" % (compiled, self.compiled_tag)
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
            return "(%s)*%s" % (compiled, self.compiled_tag)
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
            return "[%s]%s" % (compiled, self.compiled_tag)
        else:
            return "[%s]" % compiled

    def _matches_internal(self, speech):
        # Consume speech
        result = self.child.matches(speech)

        # Check if child has None or '' as the match
        if not self.child.current_match:
            # Reset match data for this subtree and return the original speech
            # string; this was an incomplete match.
            self.reset_for_new_match()
            return speech
        else:
            self.current_match = self.child.current_match
            return result

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
            return "(%s)%s" % (grouping, self.compiled_tag)
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

    @weights.setter
    def weights(self, value):
        self._weights = value

    def __hash__(self):
        # The hash of an Alt.Set is a combination of the class name, tag and
        # hashes of children, similar to expansion string representations.
        # Hashes of children are sorted so that the same value is returned
        # regardless of child order.
        child_hashes = sorted([hash(c) for c in self.children])
        return hash(
            "%s(%s)%s" % (self.__class__.__name__, child_hashes, self.tag)
        )

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
            return "(%s)%s" % (alt_set, self.compiled_tag)
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
            else:
                # This alternative didn't match, so set the match values of
                # descendants to None or ''.
                child.reset_for_new_match()

        # No children matched.
        if not self.current_match:
            result = speech

        return result

    def __eq__(self, other):
        if type(self) != type(other) or len(self.children) != len(other.children):
            return False
        else:
            # Check that the children lists have the same contents, but the
            # ordering can be different.
            return set(self.children) == set(other.children)

    @property
    def is_alternative(self):
        return True
