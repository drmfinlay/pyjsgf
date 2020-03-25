"""
This module contains classes for compiling and matching JSpeech Grammar Format rule
expansions.
"""

import functools
import math
import random
import re
from copy import deepcopy

import pyparsing
from six import string_types, integer_types

from .errors import CompilationError, GrammarError
from . import references


class TraversalOrder(object):
    PreOrder, PostOrder = list(range(2))


def map_expansion(e, func=lambda x: x, order=TraversalOrder.PreOrder,
                  shallow=False):
    """
    Traverse an expansion tree and call func on each expansion returning a tuple
    structure with the results.

    :param e: Expansion
    :param func: callable (default: the identity function, f(x)->x)
    :param order: int
    :param shallow: whether to not process trees of referenced rules (default False)
    :returns: tuple
    """
    def map_children(x):
        if isinstance(x, NamedRuleRef) and not shallow:  # map the referenced rule
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
    the other top-level functions in this module.

    :param e: Expansion
    :param func: callable (default: the identity function, f(x)->x)
    :param order: int
    :param shallow: whether to not process trees of referenced rules (default False)
    :returns: Expansion | None
    """
    def find_in_children(x):
        # Find in the referenced rule's tree
        if isinstance(x, NamedRuleRef) and not shallow:
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

    :param e: Expansion
    :param func: callable (default: the identity function, f(x)->x)
    :param order: int
    :param shallow: whether to not process trees of referenced rules (default False)
    :returns: list
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

    :param e: Expansion
    :param func: callable (default: the identity function, f(x)->x)
    :param order: int
    :param shallow: whether to not process trees of referenced rules (default False)
    :returns: list
    """
    result = []

    def filter_(x):
        if func(x):
            result.append(x)

    map_expansion(e, filter_, order, shallow)

    return result


def save_current_matches(e):
    """
    Traverse an expansion tree and return a dictionary populated with each
    descendant ``Expansion`` and its match data.

    This will also include ``e``.

    :param e: Expansion
    :returns: dict
    """
    values = {}

    def save(x):
        values[x] = {
            "current_match": x.current_match,
            "matching_slice": x.matching_slice,
        }
    map_expansion(e, save)
    return values


def restore_current_matches(e, values, override_none=True):
    """
    Traverse an expansion tree and restore matched data using the values dictionary.

    :param e: Expansion
    :param values: dict
    :param override_none: bool
    """
    def restore(x):
        match_data = values.get(x, None)
        if match_data:
            if not override_none and match_data["current_match"] is not None:
                x.current_match = match_data["current_match"]
            if not override_none and match_data["matching_slice"] is not None:
                x.matching_slice = match_data["matching_slice"]

    map_expansion(e, restore)


def matches_overlap(m1, m2):
    """
    Check whether two regex matches overlap.

    :returns: bool
    """
    if not m1 or not m2 or m1.string != m2.string:
        return False
    x1, y1 = m1.span()
    x2, y2 = m2.span()
    return x1 < x2 <= y1 or x2 < x1 <= y2 or x1 == x2


class JointTreeContext(object):
    """
    Class that temporarily joins an expansion tree with the expansion trees of all
    referenced rules by setting the parent relationships.

    This is useful when it is necessary to view an expansion tree and the expansion
    trees of referenced rules as one larger tree. E.g. when determining mutual
    exclusivity of two expansions, if an expansion is optional or used for
    repetition in the context of other trees, etc.

    **Note**: this class will reduce the matching performance if used, but will only
    be noticeable with larger grammars.

    On ``__exit__``, the trees will be detached recursively.

    This class can be used with Python's ``with`` statement.
    """

    def __init__(self, root_expansion):
        self._root = root_expansion

    @staticmethod
    def join_tree(x):
        """
        If x is a NamedRuleRef, join its referenced rule's expansion to this tree.

        :param x: Expansion
        """
        if isinstance(x, NamedRuleRef):
            # Set the parent of the referenced rule's root expansion to this
            # expansion.
            x.referenced_rule.expansion.parent = x

    @staticmethod
    def detach_tree(x):
        """
        If x is a NamedRuleRef, detach its referenced rule's expansion from this
        tree.

        :param x: Expansion
        """
        if isinstance(x, NamedRuleRef):
            # Reset parent
            x.referenced_rule.expansion.parent = None

    def __enter__(self):
        map_expansion(self._root, self.join_tree, TraversalOrder.PostOrder)

    def __exit__(self, exc_type, exc_val, exc_tb):
        map_expansion(self._root, self.detach_tree, TraversalOrder.PostOrder)


@functools.total_ordering
class ChildList(object):
    """
    List wrapper class for expansion child lists.

    The ``parent`` attribute of each child will be set appropriately when they
    added or removed from lists.
    """

    def __init__(self, expansion, seq=()):
        # Ensure that 'expansion' is an expansion.
        self._expansion = Expansion.make_expansion(expansion)

        # If seq is specified, map each element in the sequence to an Expansion
        # (if possible) and set each expanion's parent to self._expansion.
        if seq:
            def f(x):
                x = Expansion.make_expansion(x)
                x.parent = self._expansion
                return x

            seq = map(f, seq)

        # Use an internal list rather than sub-classing to avoid pickling issues.
        self._list = list(seq)

    def __repr__(self):
        return repr(self._list)

    def __lt__(self, other):
        return self._list < other

    def __eq__(self, other):
        return self._list == other

    def __len__(self):
        return len(self._list)

    def __not__(self):
        return not(self._list)

    def __add__(self, other):
        return self._list + other

    def __iadd__(self, other):
        self._list += other

    def append(self, e):
        e = Expansion.make_expansion(e)
        self._list.append(e)
        e.parent = self._expansion

    def __iter__(self):
        return iter(self._list)

    def clear(self):
        """
        Remove all expansions from this list and unset their parent attributes.
        """
        # Clear the list using remove().
        for c in tuple(self._list):
            self.remove(c)

    def orphan_children(self):
        """
        Set each child's parent to None.
        """
        for c in self:
            c.parent = None

    def extend(self, iterable):
        # Make each item in the iterable into an Expansion.
        iterable = [Expansion.make_expansion(e) for e in iterable]

        # Set the parent of each to self._expansion.
        for e in iterable:
            e.parent = self._expansion

        # Call the super method to extend the list.
        self._list.extend(iterable)

    def index(self, value, start=0, end=None):
        if end is None:
            end = len(self._list)
        return self._list.index(value, start, end)

    def insert(self, index, e):
        # Make e an Expansion, call the super method and set e's parent.
        e = Expansion.make_expansion(e)
        self._list.insert(index, e)
        e.parent = self._expansion

    def pop(self, index=-1):
        # Pop item at the specified index (default -1), set its parent to None
        # and return it.
        e = self._list.pop(index)
        e.parent = None
        return e

    def remove(self, value):
        # Set the parent before removing the expansion.
        # 'value' is not necessarily in the list, so we can't use that.
        self._list[self._list.index(value)].parent = None
        self._list.remove(value)

    def __setslice__(self, i, j, sequence):
        """
        Method for setting a list slice compatible with Python 2 and 3.

        :param i: int
        :param j: int
        :param sequence: iterable
        """
        # Convert the sequence to a sequence of Expansions if it isn't one.
        sequence = [Expansion.make_expansion(e) for e in sequence]

        # Orphan the old children :-(
        def orphan(x):
            x.parent = None

        [orphan(c) for c in self._list[i:j]]

        # Set the slice.
        self._list[slice(i, j)] = sequence

        # Adopt the new children :-)
        def adopt(x):
            x.parent = self._expansion

        [adopt(c) for c in sequence]

    def __getitem__(self, key):
        return self._list[key]

    def __setitem__(self, i, value):
        # Handle setting slices separately for my sanity.
        if isinstance(i, slice):
            self.__setslice__(i.start, i.stop, value)
            return

        # Convert value to Expansion appropriately.
        value = Expansion.make_expansion(value)

        # Orphan the old child :-(
        self._list[i].parent = None

        # Set the Expansion in the internal list.
        self._list[i] = value

        # Adopt the new child :-)
        self._list[i].parent = self._expansion


class Expansion(object):
    """
    Expansion base class.
    """

    _NO_CALCULATION = object()

    def __init__(self, children):
        self._tag = ""
        self._parent = None

        # Internal member for the parser element used during matching.
        self._matcher_element = None

        # Set children, letting the setter handle validation.
        self._children = None
        self.children = children

        self._current_match = None
        self._matching_slice = None
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
        :returns: Expansion
        """
        if shallow:
            return self.__copy__()
        else:
            return self.__deepcopy__({})

    @property
    def children(self):
        """
        List of children.

        :returns: ChildList
        """
        return self._children

    @children.setter
    def children(self, value):
        if not isinstance(value, (tuple, list, ChildList)):
            raise TypeError("'children' must be a list or tuple")

        # Orphan current children if applicable.
        if self._children:
            self._children.orphan_children()

        # Set a new ChildList. This will handle setting the parent attributes.
        self._children = ChildList(self, value)

    def compile(self, ignore_tags=False):
        self.validate_compilable()
        if self.tag and not ignore_tags:
            return self.compiled_tag
        else:
            return ""
        
    def generate(self):
        """Generate a string matching this expansion."""
        return ""

    @property
    def parent(self):
        """
        This expansion's parent, if it has one.

        Setting the parent will call ``Expansion.invalidate_matcher`` as necessary
        on the new and old parents.

        :returns: Expansion | None
        """
        return self._parent

    @parent.setter
    def parent(self, value):
        if isinstance(value, Expansion) or value is None:
            # Invalidate the old parent if necessary.
            if self._parent:
                self._parent.invalidate_matcher()

            # Set the parent and invalidate the matcher element for this expansion.
            self._parent = value
            self.invalidate_matcher()

            # Also invalidate the new parent as necessary. This is a quick operation
            # if nothing has been matched yet.
            if self._parent:
                self._parent.invalidate_matcher()
        else:
            raise TypeError("'parent' must be an Expansion or None")

    @property
    def tag(self):
        """
        JSGF tag for this expansion.

        :returns: str
        """
        return self._tag

    @tag.setter
    def tag(self, value):
        """
        Sets the tag for the expansion.

        :param value: str
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

        :returns: str
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

        :param e: str | Expansion
        :returns: Expansion
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
        raise a ``CompilationError``.

        :raises: CompilationError
        """
        pass

    @property
    def current_match(self):
        """
        Currently matched speech value for this expansion.

        If the expansion hasn't been matched, this will be None (if required) or
        '' (if optional).

        :returns: str | None
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

    @property
    def matching_slice(self):
        """
        Slice of the last speech string matched. This will be ``None`` initially.

        :rtype: slice
        """
        return self._matching_slice

    @matching_slice.setter
    def matching_slice(self, value):
        if not isinstance(value, slice) and value is not None:
            raise TypeError("matching_slice must be a slice or None")

        self._matching_slice = value

    def reset_for_new_match(self):
        """
        Call ``reset_match_data`` for this expansion and all of its descendants.
        """
        map_expansion(self, lambda x: x.reset_match_data())

    def reset_match_data(self):
        """
        Reset any members or properties this expansion uses for matching speech,
        i.e. ``current_match`` values.

        This does **not** invalidate ``matcher_element``.
        """
        self.current_match = None
        self.matching_slice = None

    def matches(self, speech):
        """
        Match speech with this expansion, set ``current_match`` to the first matched
        substring and return the remainder of the string.

        Matching ambiguous rule expansions is **not supported** because it not worth
        the performance hit. Ambiguous rule expansions are defined as some optional
        literal x followed by a required literal x. For example, successfully
        matching ``'test'`` for the following rule is not supported::

            <rule> = [test] test;

        :param speech: str
        :returns: str
        """
        # Match the string using this expansion's parser element.
        speech = speech.strip()
        try:
            result = " ".join(
                self.matcher_element.parseString(speech).asList()
            )
        except pyparsing.ParseException:
            result = ""

        # Return the difference between the result and speech. The result can be
        # shorter than speech, which means the match wasn't complete.
        remaining = speech[len(result):].strip()

        # Do a second pass of the expansion tree for post-processing.
        def process(x):
            # Remove partial matches.
            if (x.parent and not isinstance(x, NamedRuleRef) and not
                    x.parent.current_match):
                x.current_match = None
                x.matching_slice = None

        map_expansion(self, process)
        return remaining

    def invalidate_matcher(self):
        """
        Method to invalidate the parser element used for matching this expansion.
        This is method is called automatically when a parent is set or a ChildList
        is modified. The parser element will be recreated again when required.

        This only needs to be called manually if modifying an expansion tree *after*
        matching with a Dictation expansion.
        """
        # Return early if _matcher_element hasn't been set.
        if not self._matcher_element:
            return

        # Set _matcher_element to None for this expansion and each ancestor, but not
        # any other subtrees (they are unaffected).
        self._matcher_element = None
        if self.parent:
            self.parent.invalidate_matcher()

        # If at the root expansion, call invalidate_matcher for any RuleRefs or
        # NamedRuleRefs that reference this rule. To make things simple, this is
        # is only done if this expansion belongs to a rule in a grammar.
        elif self.rule and self.rule.grammar:
            def process(x):
                if isinstance(x, NamedRuleRef) and x.name == self.rule.name:
                    x.invalidate_matcher()

            # Invalidate each reference to this rule. Use shallow=True because every
            # rule in the grammar will be processed, no need to process rules twice.
            for r in self.rule.grammar.rules:
                map_expansion(r.expansion, process, shallow=True)

    @property
    def matcher_element(self):
        """
        Lazily initialised `pyparsing` ``ParserElement`` used to match speech to
        expansions. It will also set ``current_match`` values.

        :returns: pyparsing.ParserElement
        """
        if not self._matcher_element:
            element = self._make_matcher_element()
            self._matcher_element = element
        else:
            element = self._matcher_element
        return element

    def _parse_action(self, tokens):
        self.current_match = " ".join(tokens.asList())
        return tokens

    def _make_matcher_element(self):
        """
        Method used by the matcher_element property to create ParserElements.

        Subclasses should implement this method for speech matching functionality.
        """
        raise NotImplementedError()

    def _set_matcher_element_attributes(self, element):
        # Set the ParserElement's action.
        element.setParseAction(self._parse_action)

        # Save the element's original postParse function.
        closure = element.postParse

        # Set a new function and use the original function for returning values.
        def postParse(instring, loc, tokenlist):
            if isinstance(tokenlist, pyparsing.ParseResults):
                s = " ".join(tokenlist.asList())
            elif isinstance(tokenlist, list):
                s = "".join(tokenlist)
            elif isinstance(tokenlist, string_types):
                s = tokenlist
            else:
                raise TypeError("postParse received invalid tokenlist %s"
                                % tokenlist)
            self.matching_slice = slice(loc - len(s), loc)
            return closure(instring, loc, tokenlist)

        element.postParse = postParse

        # Return the element.
        return element

    @property
    def had_match(self):
        """
        Whether this expansion has a ``current_match`` value that is not '' or None.
        This will also check if this expansion was part of a complete repetition if
        it has a Repeat or KleeneStar ancestor.

        :returns: bool
        """
        if self.current_match:
            return True

        rep = self.repetition_ancestor
        if rep and any(rep.get_expansion_matches(self)):
            return True
        else:
            return False

    def _init_lookup(self):
        # Initialises the lookup dictionary for the root expansion.
        # If it is already initialised, this does nothing.
        if not self._lookup_dict:
            self._lookup_dict = {
                "is_descendant_of": {},
                "mutually_exclusive_of": {}
            }

    def _store_calculation(self, name, key, value):
        # Put a calculation into a named lookup dictionary.
        # This method will always store calculation data in the root expansion.

        # :param name: str
        # :param key: object used to store the calculation result (e.g. a tuple)
        # :param value: calculation result | Expansion._NO_CALCULATION

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
        # Check if a calculation has already been made and return it. If no
        # calculation has been made, Expansion._NO_CALCULATION will be returned.
        # This method will always check for calculations using the root expansion.

        # :param name: str
        # :param key: object used to store the calculation result (e.g. a tuple)
        # :returns: calculation result | Expansion._NO_CALCULATION

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
        expansion. This only effects ``mutually_exclusive_of`` and
        ``is_descendant_of``, neither of which are used in compiling or matching
        rules.

        This should be called if a child is added to an expansion or if an
        expansion's parent is changed outside of what ``JointTreeContext`` does.

        Some changes may also require invalidating descendants, the
        ``map_expansion`` function can be used with this method to accomplish that::

            map_expansion(self, Expansion.invalidate_calculations)
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

    def __getstate__(self):
        state = self.__dict__.copy()
        state['_matcher_element'] = None
        return state

    @property
    def is_optional(self):
        """
        Whether or not this expansion has an optional ancestor.

        :returns: bool
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

        :returns: bool
        """
        result = False
        if self.parent:
            result = self.parent.is_alternative
        return result

    @property
    def repetition_ancestor(self):
        """
        This expansion's closest Repeat or KleeneStar ancestor, if it has one.

        :returns: Expansion
        """
        parent = self.parent
        if parent and hasattr(parent, "repetitions_matched"):
            return parent
        elif parent:
            return self.parent.repetition_ancestor
        else:
            return None

    def collect_leaves(self, order=TraversalOrder.PreOrder, shallow=False):
        """
        Collect all descendants of an expansion that have no children.
        This can include self if it has no children. RuleRefs are also counted as
        leaves.

        :param order: tree traversal order (default 0: pre-order)
        :param shallow: whether to not collect leaves from trees of referenced rules
        :returns: list
        """
        return filter_expansion(
            self, lambda x: not x.children, order=order, shallow=shallow
        )

    leaves = property(collect_leaves)

    @property
    def leaves_after(self):
        """
        Generator function for leaves after this one (if any).

        :returns: generator
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

        :returns: generator
        """
        for leaf in self.leaves_after:
            if not self.mutually_exclusive_of(leaf):
                yield leaf

    @property
    def root_expansion(self):
        """
        Traverse to the root expansion r and return it.

        :returns: Expansion
        """
        r = self
        while r.parent:
            r = r.parent

        return r

    def is_descendant_of(self, other):
        """
        Whether this expansion is a descendant of another expansion.

        :param other: Expansion
        :returns: bool
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

        :param other: Expansion
        :returns: bool
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


class BaseExpansionRef(references.BaseRef, Expansion):
    """
    Base class which RuleRef, NamedRuleRef, NullRef and VoidRef inherit from.
    """
    def __init__(self, name):
        # Call both super constructors
        references.BaseRef.__init__(self, name)
        Expansion.__init__(self, [])

    @staticmethod
    def valid(name):
        return references.optionally_qualified_name.matches(name)

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
        return (Expansion.__eq__(self, other) and
                references.BaseRef.__eq__(self, other))

    def __copy__(self):
        e = type(self)(self.name)
        e.tag = self.tag
        return e

    def __deepcopy__(self, memo):
        return self.__copy__()


class NamedRuleRef(BaseExpansionRef):
    """
    Class used to reference rules by name.
    """
    @property
    def referenced_rule(self):
        """
        Find and return the rule this expansion references in the grammar.

        This raises an error if the referenced rule cannot be found using
        ``self.rule.grammar`` or if there is no link to a grammar.

        :raises: GrammarError
        :returns: Rule
        """
        if self.rule and self.rule.grammar:
            return self.rule.grammar.get_rule_from_name(self.name)
        else:
            raise GrammarError("cannot get referenced Rule object from Grammar")
    
    def generate(self):
        """
        Generate a string matching the referenced rule's expansion.

        :rtype: str
        """
        return self.referenced_rule.generate()

    def _make_matcher_element(self):
        # Wrap the parser element for the referenced rule's root expansion so that
        # the current match value for the NamedRuleRef is also set.
        return self._set_matcher_element_attributes(pyparsing.And([
            self.referenced_rule.expansion.matcher_element
        ]))

    def __hash__(self):
        return super(NamedRuleRef, self).__hash__()


class NullRef(BaseExpansionRef):
    """
    Reference expansion for the special *NULL* rule.

    The *NULL* rule always matches speech. If this reference is used by
    a rule, that part of the rule expansion requires no speech substring to match.
    """
    def __init__(self):
        super(NullRef, self).__init__("NULL")

    def _make_matcher_element(self):
        return self._set_matcher_element_attributes(pyparsing.Empty())

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


class VoidRef(BaseExpansionRef):
    """
    Reference expansion for the special *VOID* rule.

    The *VOID* rule can never be spoken. If this reference is used by a rule, then
    it will not match unless the reference it is optional.
    """
    def __init__(self):
        super(VoidRef, self).__init__("VOID")

    def _make_matcher_element(self):
        return self._set_matcher_element_attributes(pyparsing.NoMatch())

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
        # Add a reference to the built-in NULL rule to produce a valid JSGF rule
        # expansion: "<NULL>" instead of "()";
        if not self.children:
            self.children.append(NullRef())


class SingleChildExpansion(ExpansionWithChildren):
    def __init__(self, expansion):
        super(SingleChildExpansion, self).__init__([expansion])

    @property
    def child(self):
        if not self.children:
            return None  # the child has been removed
        else:
            return self.children[0]
        
    def generate(self):
        return self.child.generate()

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
        
    def generate(self):
        return " ".join([c for c in [e.generate() for e in self.children] if c])

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
    """
    Class for expansions to be spoken in sequence.
    """
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

    def _make_matcher_element(self):
        # Return an And element using each child's matcher element.
        return self._set_matcher_element_attributes(pyparsing.And([
            child.matcher_element for child in self.children
        ]))

    def __hash__(self):
        return super(Sequence, self).__hash__()


class Literal(Expansion):
    """
    Expansion class for literals.
    """
    def __init__(self, text, case_sensitive=False):
        # Set _text and use the text setter to validate the input.
        self._text = ""
        self.text = text
        self._case_sensitive = bool(case_sensitive)
        super(Literal, self).__init__([])

    def __str__(self):
        return "%s('%s')" % (self.__class__.__name__, self.text)

    def __hash__(self):
        return hash("%s" % self)

    @property
    def case_sensitive(self):
        """
        Case sensitivity used when matching and compiling :class:`Literal` rule
        expansions.

        This property can be ``True`` or ``False``. Matching and compilation will
        be *case-sensitive* if ``True`` and *case-insensitive* if ``False``. The
        default value is ``False``.

        :rtype: bool
        :returns: literal case sensitivity
        """
        return self._case_sensitive

    @case_sensitive.setter
    def case_sensitive(self, value):
        self._case_sensitive = bool(value)
        self.invalidate_matcher()

    @property
    def text(self):
        """
        Text to match/compile.

        This will return lowercase text if :py:attr:`~case_sensitive` is not
        ``True``.

        :rtype: str
        :returns: text
        """
        text = self._text
        if not self.case_sensitive:
            text = text.lower()
        return text

    @text.setter
    def text(self, value):
        if not isinstance(value, string_types):
            raise TypeError("expected string, got %s instead" % value)

        self._text = value

    def generate(self):
        """
        Generate a string matching this expansion's text.

        This will just return the value of ``text``.

        :rtype: str
        """
        return self.text

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

        This property has been left in for backwards compatibility.
        The ``Expansion.matches`` method now uses the ``matcher_element`` property
        instead.

        :returns: regex pattern object
        """
        # Selectively escape certain characters because this text will
        # be used in a regular expression pattern string.
        escaped = self.text.replace(".", r"\.")

        # Create a list of words from text.
        words = escaped.split()

        # Return a regex pattern to use.
        return re.compile(r"\s+".join(words))

    def _make_matcher_element(self):
        # Return a case-sensitive or case-insensitive pyparsing Literal element.
        text = self._text
        if self.case_sensitive:
            matcher_cls = pyparsing.Literal
        else:
            matcher_cls = pyparsing.CaselessLiteral
        return self._set_matcher_element_attributes(matcher_cls(text))

    def __eq__(self, other):
        return (super(Literal, self).__eq__(other) and self.text == other.text and
                self.case_sensitive == other.case_sensitive)


class RuleRef(NamedRuleRef):
    """
    Subclass of ``NamedRuleRef`` for referencing another rule with a Rule object.
    """
    def __init__(self, referenced_rule):
        """
        :param referenced_rule:
        """
        super(RuleRef, self).__init__(referenced_rule.name)
        self._referenced_rule = referenced_rule

    @property
    def referenced_rule(self):
        return self._referenced_rule

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

    For example::

        <repeat> = (please)+ don't crash;
    """
    def __init__(self, expansion):
        super(Repeat, self).__init__(expansion)
        self._repetitions_matched = []

    def compile(self, ignore_tags=False):
        super(Repeat, self).compile()
        compiled = self.child.compile(ignore_tags)
        if self.tag and not ignore_tags:
            return "(%s)+%s" % (compiled, self.compiled_tag)
        else:
            return "(%s)+" % compiled
        
    def generate(self):
        """
        Generate a string matching this expansion.

        This method can generate one or more repetitions of the child expansion.

        :rtype: str
        """
        c = int(math.log(random.random() / 2, 0.5))
        return " ".join([self.child.generate() for _ in range(c)])

    def __hash__(self):
        return super(Repeat, self).__hash__()

    @property
    def repetitions_matched(self):
        """
        The number of repetitions last matched.

        :returns: int
        """
        return len(self._repetitions_matched)

    def get_expansion_matches(self, e):
        """
        Get a list of an expansion's ``current_match`` values for each repetition.

        :returns: list
        """
        if e.is_descendant_of(self):
            return [values[e]["current_match"] for values in
                    self._repetitions_matched]
        else:
            return []

    def get_expansion_slices(self, e):
        """
        Get a list of an expansion's ``matching_slice`` values for each repetition.

        :returns: list
        """
        if e.is_descendant_of(self):
            return [values[e]["matching_slice"] for values in
                    self._repetitions_matched]
        else:
            return []

    def _parse_action(self, tokens):
        # Call the super method to set current_match.
        super(Repeat, self)._parse_action(tokens)

        # Note: this method is called after the child's parse actions.
        if self._repetitions_matched:
            # Restore the last repetition's match values.
            last = self._repetitions_matched[len(self._repetitions_matched) - 1]
            restore_current_matches(self.child, last, False)
        return tokens

    def _make_matcher_element(self):
        # Define an extra parse action for the child's matcher element.
        def f(tokens):
            if tokens.asList():
                # Add current match values to the _repetitions_matched list.
                self._repetitions_matched.append(save_current_matches(self.child))

                # Wipe current match values for the next repetition (if any).
                self.child.reset_for_new_match()
            return tokens

        # Get the child's matcher element and add the extra parse action.
        child_element = self.child.matcher_element.addParseAction(f)

        # Determine the parser element type to use.
        type_ = pyparsing.ZeroOrMore if self.is_optional else pyparsing.OneOrMore

        # Handle the special case of a repetition ancestor, e.g. ((a b)+)+
        rep = self.repetition_ancestor
        if rep:
            # Check if there are no other branches.
            c = rep.child
            only_branch = True
            while c is not self:
                if len(c.children) > 1:
                    only_branch = False
                    break
                else:
                    c = c.children[0]

            # Use an And element instead if self is the only branch because
            # it makes no sense to repeat a repeat like this!
            if only_branch:
                type_ = pyparsing.And
                child_element = [child_element]

        return self._set_matcher_element_attributes(type_(child_element))

    def reset_match_data(self):
        super(Repeat, self).reset_match_data()
        self._repetitions_matched = []


class KleeneStar(Repeat):
    """
    JSGF Kleene star operator for allowing zero or more repeats of an expansion.

    For example::

        <kleene> = (please)* don't crash;
    """
    def compile(self, ignore_tags=False):
        super(KleeneStar, self).compile()
        compiled = self.child.compile(ignore_tags)
        if self.tag and not ignore_tags:
            return "(%s)*%s" % (compiled, self.compiled_tag)
        else:
            return "(%s)*" % compiled
        
    def generate(self):
        """
        Generate a string matching this expansion.

        This method can generate zero or more repetitions of the child expansion,
        zero repetitions meaning the empty string (`""`) will be returned.

        :rtype: str
        """
        c = int(math.log(random.random() / 2, 0.5)) - 1
        return " ".join([self.child.generate() for _ in range(c)])

    @property
    def is_optional(self):
        return True

    def __hash__(self):
        return super(KleeneStar, self).__hash__()


class OptionalGrouping(SingleChildExpansion):
    """
    Class for expansions that can be optionally spoken in a rule.
    """
    def compile(self, ignore_tags=False):
        super(OptionalGrouping, self).compile()
        compiled = self.child.compile(ignore_tags)
        if self.tag and not ignore_tags:
            return "[%s]%s" % (compiled, self.compiled_tag)
        else:
            return "[%s]" % compiled
        
    def generate(self):
        return random.choice([self.child.generate(), ""])

    def _make_matcher_element(self):
        return self._set_matcher_element_attributes(
            pyparsing.Optional(self.child.matcher_element)
        )

    @property
    def is_optional(self):
        return True

    def __hash__(self):
        return super(OptionalGrouping, self).__hash__()


class RequiredGrouping(Sequence):
    """
    Subclass of ``Sequence`` for wrapping multiple expansions in parenthesises.
    """
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
    """
    Class for a set of expansions, one of which can be spoken.
    """
    def __init__(self, *expansions):
        self._weights = {}
        super(AlternativeSet, self).__init__(*expansions)

    @property
    def weights(self):
        """
        The dictionary of alternatives to their weights.

        :rtype: dict
        """
        return self._weights

    @weights.setter
    def weights(self, value):
        value = dict(value)

        # Set weights for each child using set_weight().
        for k, v in value.items():
            self.set_weight(k, v)

    def set_weight(self, child, weight):
        """
        Set the weight of a child.

        The weight determines how likely it is that an alternative was spoken.

        Higher values are more likely, lower values are less likely. A value
        of 0 means that the alternative will never be matched. Negative
        weights are not allowed.

        *Note*: weights are compiled as floating-point numbers accurate to 4
        decimal places, e.g. 5.0001.

        :param child: child/list index/compiled child to set the weight for.
        :type child: Expansion|int|str
        :param weight: weight value - must be >= 0
        :type weight: float|int
        """
        # Check that weight is a non-negative number.
        weight = float(weight)
        if weight < 0:
            raise TypeError("weight value '%s' is a negative number" % weight)

        # Use the alternative as the key for _weights.
        if isinstance(child, integer_types):
            child = self.children[child]
        elif isinstance(child, string_types):
            compiled_child = child
            for c in self.children:
                if c.compile() == compiled_child:
                    child = c

        self._weights[child] = weight

        # Invalidate this expansion. This is a quick procedure if the matcher
        # element hasn't been initialised.
        self.invalidate_matcher()

    def __hash__(self):
        # The hash of an Alt.Set is a combination of the class name, tag and
        # hashes of children, similar to expansion string representations.
        # Hashes of children are sorted so that the same value is returned
        # regardless of child order. Weights are also included.
        child_hashes = sorted([
            (e.compile(), float(self.weights.get(e, 1)))
            for e in self.children
        ])
        return hash(
            "%s(%s)%s" % (self.__class__.__name__, child_hashes, self.tag)
        )

    def __copy__(self):
        result = super(AlternativeSet, self).__copy__()
        result.weights = dict(self.weights)
        return result

    def __deepcopy__(self, memo):
        result = super(AlternativeSet, self).__deepcopy__(memo)
        result.weights = dict(self.weights)
        return result

    def _validate_weights(self):
        # Check that all alternatives have a weight. The rule for weights is
        # all or nothing.
        for e in self.children:
            if e not in self._weights:
                raise GrammarError("alternative %s does not have a weight "
                                   "value" % e)

    def compile(self, ignore_tags=False):
        super(AlternativeSet, self).compile()
        if self._weights:
            self._validate_weights()

            # Create a string with w=weight and e=compiled expansion
            # such that:
            # /<w 0>/ <e 0> | ... | /<w n-1>/ <e n-1>
            alt_set = "|".join([
                "/%.4f/ %s" % (float(self._weights[e]), e.compile(ignore_tags))
                for e in self.children
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
        
    def generate(self):
        """
        Generate a matching string for this alternative set.

        Each alternative has an equal chance of being chosen for string generation.

        If weights are set, then the probability of an alternative is its weight over
        the sum of all weights::

            p = w / sum(weights)

        """
        if self._weights:
            self._validate_weights()
            # use weights if they are set
            # each alternative gets the probability weight / sum_of_all_weights
            w_sum = sum(self._weights.values())
            rand = random.random()
            # print("rand = %s" % rand)
            help_sum = 0
            for child, weight in self._weights.items():
                help_sum += (weight / w_sum)
                # print(help_sum)
                if rand < help_sum:
                    return child.generate()
        return random.choice(self.children).generate()

    def _make_matcher_element(self):
        # Return an element that can match the alternatives.
        if self._weights:
            self._validate_weights()

            # Exclude alternatives that have a weight value of 0.
            children = []
            for e, w in self._weights.items():
                if w > 0:
                    children.append((e, w))

            # Sort the list by weight (highest to lowest).
            children = [e for e, _ in sorted(children, key=lambda x: x[1])]
            children.reverse()
        else:
            children = self.children

        return self._set_matcher_element_attributes(pyparsing.Or([
            e.matcher_element for e in children
        ]))

    def __eq__(self, other):
        return (
            isinstance(other, AlternativeSet) and
            len(self.children) == len(other.children) and

            # Check that the children lists have the same contents, but the
            # ordering can be different. Also check the weights dictionaries.
            set(self.children) == set(other.children) and
            self.weights == other.weights
        )

    @property
    def is_alternative(self):
        return True
