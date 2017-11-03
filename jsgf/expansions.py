"""
Classes for compiling JSpeech Grammar Format expansions
"""
import re


def map_expansion(e, func):
    """
    Traverse an expansion tree and call func on each expansion returning a tuple
    structure with the results.
    :type e: Expansion
    :type func: callable
    :return: tuple
    """
    if isinstance(e, RuleRef):
        e_result = map_expansion(e.rule.expansion, func)
    else:
        e_result = func(e)
    children_result = tuple([map_expansion(child, func) for child in e.children])
    return e_result, children_result


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


class ExpansionError(Exception):
    pass


class MatchError(Exception):
    pass


class Expansion(object):
    """
    Expansion base class
    """
    def __init__(self, children):
        self._tag = None
        self._parent = None
        self._is_optional = False
        if not isinstance(children, (tuple, list)):
            raise TypeError("'children' must be a list or tuple")

        # Validate each child expansion
        self._children = map(lambda e: self.validate(e), children)

        # Set each child's parent as this expansion
        for child in self._children:
            child.parent = self

        self._current_match = None

    def __add__(self, other):
        return self + other

    @property
    def children(self):
        return self._children

    def compile(self, ignore_tags=False):
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

            # Check if value is an optional expansion
            parent = value
            while parent:
                if parent.is_optional:
                    def func(x):
                        x._is_optional = True

                    # Set is_optional for self and all descendants
                    map_expansion(self, func)
                    break
                parent = parent.parent

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
        # Escape '{', '}' and '\' so that tags will be processed
        # properly if they have those characters.
        # This is suggested in the JSGF specification.
        assert isinstance(value, str)
        escaped = value.replace("{", "\\{") \
            .replace("}", "\\}") \
            .replace("\\", "\\\\")
        self._tag = "{ %s }" % escaped

    @staticmethod
    def validate(e):
        """
        Validate an Expansion object and return it.
        :param e:
        :return: Expansion
        """
        if isinstance(e, str):
            return Literal(e)
        elif isinstance(e, Expansion):
            return e
        else:
            raise TypeError("can only take strings or Expansions")

    @property
    def current_match(self):
        """
        Current speech match.
        """
        return self._current_match

    @current_match.setter
    def current_match(self, value):
        # Ensure that string values have only one space between words
        if isinstance(value, str):
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

    def __eq__(self, other):
        return type(self) == type(other) and self.children == other.children

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def is_optional(self):
        """
        Whether or not this expansion has an OptionalGrouping or KleeneStar
        ancestor.
        """
        return self._is_optional

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
            if not e.children:
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


class SingleChildExpansion(Expansion):
    def __init__(self, expansion):
        super(SingleChildExpansion, self).__init__([expansion])

    @property
    def child(self):
        return self.children[0]


class VariableChildExpansion(Expansion):
    def __init__(self, *expansions):
        super(VariableChildExpansion, self).__init__(expansions)


class Sequence(VariableChildExpansion):
    def compile(self, ignore_tags=False):
        seq = " ".join([
            e.compile(ignore_tags) for e in self.children
        ])

        # Return the sequence and the tag if there is one
        if self.tag and not ignore_tags:
            return "%s%s" % (seq, self.tag)
        else:
            return seq


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

    def compile(self, ignore_tags=False):
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
            leaves_after = self.leaves_after
            for leaf in leaves_after:
                if (leaf.is_optional and not leaf.repetition_ancestor
                        or self.mutually_exclusive_of(leaf)):
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


class RuleRef(Expansion):
    def __init__(self, rule):
        """
        Class for referencing another rule from a rule.
        :param rule:
        """
        self.rule = rule
        super(RuleRef, self).__init__([])

        self.rule.reference_count += 1

    def compile(self, ignore_tags=False):
        if self.tag and not ignore_tags:
            return "<%s>%s" % (self.rule.name, self.tag)
        else:
            return "<%s>" % self.rule.name

    def __str__(self):
        return "%s('%s')" % (self.__class__.__name__, self.rule.name)

    def _matches_internal(self, speech):
        # Temporarily set the parent of the referenced rule's root expansion to
        # this expansion. This is required when it is necessary to view this
        # expansion's tree and the referencing rule's expansion tree as one larger
        # tree. E.g. when determining mutual exclusivity of 2 expansions, if an
        # expansion is optional, if a literal is used for repetition, etc.
        self.rule.expansion.parent = self

        result = self.rule.expansion.matches(speech)
        self.current_match = self.rule.expansion.current_match

        # Reset parent
        self.rule.expansion.parent = None

        return result

    def decrement_ref_count(self):
        if self.rule.reference_count > 0:
            self.rule.reference_count -= 1

    def __del__(self):
        self.decrement_ref_count()

    def __eq__(self, other):
        return super(RuleRef, self).__eq__(other) and self.rule == other.rule


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
        compiled = self.child.compile(ignore_tags)
        if self.tag and not ignore_tags:
            return "(%s)+%s" % (compiled, self.tag)
        else:
            return "(%s)+" % compiled

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
            intermediate_result = self.child.matches(intermediate_result)
            child_match = self.child.current_match

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
        compiled = self.child.compile(ignore_tags)
        if self.tag and not ignore_tags:
            return "(%s)*%s" % (compiled, self.tag)
        else:
            return "(%s)*" % compiled

    @property
    def is_optional(self):
        return True


class OptionalGrouping(SingleChildExpansion):
    """
    Expansion that can be spoken in a rule, but doesn't have to be.
    """
    def compile(self, ignore_tags=False):
        compiled = self.child.compile(ignore_tags)
        if self.tag and not ignore_tags:
            return "[%s]%s" % (compiled, self.tag)
        else:
            return "[%s]" % compiled

    @property
    def is_optional(self):
        return True


class RequiredGrouping(VariableChildExpansion):
    def compile(self, ignore_tags=False):
        grouping = " ".join([
            e.compile(ignore_tags) for e in self.children
        ])

        if self.tag and not ignore_tags:
            return "(%s%s)" % (grouping, self.tag)
        else:
            return "(%s)" % grouping


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

    def compile(self, ignore_tags=False):
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

    @property
    def is_alternative(self):
        return True
