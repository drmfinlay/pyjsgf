"""
Classes for compiling JSpeech Grammar Format expansions
"""


class ExpansionError(Exception):
    pass


class Expansion(object):
    """
    Expansion base class
    """
    def __init__(self, children):
        self._tag = None
        self._parent = None
        if not isinstance(children, (tuple, list)):
            raise TypeError("'children' must be a list or tuple")

        # Validate each child expansion
        self._children = map(lambda e: self.validate(e), children)

        # Set each child's parent as this expansion
        for child in self._children:
            child.parent = self

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

    def matching_regex(self):
        """
        A regex string for matching this expansion.
        :return: str
        """
        return ""

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
        Whether or not this expansion has an OptionalGrouping ancestor
        """
        parent = self.parent
        while parent:
            if isinstance(parent, OptionalGrouping):
                return True
            parent = parent.parent
        return False

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
        def _collect_leaves(e):
            """
            Recursively collect all expansions with no children.
            :type e: Expansion
            :rtype: list
            """
            if not e.children:
                result = [e]
            else:
                result = []
                for child in e.children:
                    result.extend(_collect_leaves(child))
            return result
        return _collect_leaves(self)


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

    def matching_regex(self):
        """
        A regex string for matching this expansion.
        :return: str
        """
        return "".join([
            e.matching_regex() for e in self.children
        ])


class Literal(Expansion):
    def __init__(self, text):
        # CMU Sphinx recognizers use dictionaries with lower case words only
        # So use lower() to fix errors similar to:
        # "The word 'HELLO' is missing in the dictionary"
        self.text = text.lower()
        super(Literal, self).__init__([])

    def __str__(self):
        return "%s('%s')" % (self.__class__.__name__, self.text)

    def compile(self, ignore_tags=False):
        if self.tag and not ignore_tags:
            return "%s%s" % (self.text, self.tag)
        else:
            return self.text

    def matching_regex(self):
        """
        A regex string for matching this expansion.
        :return: str
        """
        # Selectively escape certain characters because this text will
        # be used in a regular expression pattern string.
        #
        escaped = self.text.replace(".", r"\.")

        # Also make everything lowercase and allow matching 1 or more
        # whitespace characters between words and before the first word.
        words = escaped.lower().split()
        return "\s+%s" % "\s+".join(words)

    def __eq__(self, other):
        return super(Literal, self).__eq__(other) and self.text == other.text


class RuleRef(Expansion):
    def __init__(self, rule):
        """
        Class for referencing another rule from a rule.
        :param rule:
        """
        super(RuleRef, self).__init__([])

        self.rule = rule
        self.rule.reference_count += 1

    def compile(self, ignore_tags=False):
        if self.tag and not ignore_tags:
            return "<%s>%s" % (self.rule.name, self.tag)
        else:
            return "<%s>" % self.rule.name

    def __str__(self):
        return "%s('%s')" % (self.__class__.__name__, self.rule.name)

    def matching_regex(self):
        return self.rule.expansion.matching_regex()

    def decrement_ref_count(self):
        if self.rule.reference_count > 0:
            self.rule.reference_count -= 1

    def __del__(self):
        self.decrement_ref_count()

    def __eq__(self, other):
        return super(RuleRef, self).__eq__(other) and self.rule == other.rule


class KleeneStar(SingleChildExpansion):
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

    def matching_regex(self):
        """
        A regex string for matching this expansion.
        :return: str
        """
        return "(%s)*" % self.child.matching_regex()


class Repeat(SingleChildExpansion):
    """
    JSGF plus operator for allowing one or more repeats of an expansion.
    For example:
    <kleene> = (please)+ don't crash;
    """
    def compile(self, ignore_tags=False):
        compiled = self.child.compile(ignore_tags)
        if self.tag and not ignore_tags:
            return "(%s)+%s" % (compiled, self.tag)
        else:
            return "(%s)+" % compiled

    def matching_regex(self):
        """
        A regex string for matching this expansion.
        :return: str
        """
        return "(%s)+" % self.child.matching_regex()


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

    def matching_regex(self):
        """
        A regex string for matching this expansion.
        :return: str
        """
        return "(%s)?" % self.child.matching_regex()

    @property
    def is_optional(self):
        return True


class RequiredGrouping(VariableChildExpansion):
    def compile(self, ignore_tags=False):
        grouping = "".join([
            e.compile(ignore_tags) for e in self.children
        ])

        if self.tag and not ignore_tags:
            return "(%s%s)" % (grouping, self.tag)
        else:
            return "(%s)" % grouping

    def matching_regex(self):
        """
        A regex string for matching this expansion.
        :return: str
        """
        grouping = "".join([
            e.matching_regex() for e in self.children
        ])
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

    def matching_regex(self):
        """
        A regex string for matching this expansion.
        :return: str
        """
        alt_set = "|".join([
            "(%s)" % e.matching_regex() for e in self.children
        ])
        return "(%s)" % alt_set

    @property
    def is_alternative(self):
        return True
