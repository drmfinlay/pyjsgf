"""
This module contains the base class for referencing rules and grammars by name.
"""

import re

from pyparsing import Regex, Optional, OneOrMore, Combine
from pyparsing import Literal as PPLiteral  # to differentiate from jsgf.Literal

from .errors import GrammarError

# Define words as Unicode alphanumerics and/or one of "-\'"
word = Regex(r"[\w\-\']+", re.UNICODE).setName("word")
words = OneOrMore(word).setName("literal")

# Define a parser for reserved names.
reserved_names = Combine(PPLiteral("NULL") ^ PPLiteral("VOID"))

# This will match one or more alphanumeric Unicode characters and/or any of the
# following special characters: +-:;,=|/\()[]@#%!^&~$
base_name = Regex(r"[\w\+\-;:\|/\\\(\)\[\]@#%!\^&~\$]+", re.UNICODE)\
    .setName("base name")

# A qualified name is a base name plus one or more base names joined by dots,
# i.e. Java package syntax.
qualified_name = Combine(base_name + OneOrMore("." + base_name))\
    .setName("qualified name")

# An optionally qualified name is either a base name or a qualified name. This is
# used for rule references.
optionally_qualified_name = Combine(base_name ^ qualified_name)

# Import names are similar, except that they can have wildcards on the end for
# importing all public rules in a grammar
import_name = Combine((qualified_name + Optional(".*")) ^ (base_name + ".*"))

# Grammar names cannot include semicolons because the declared grammar name parser
# will gobble any semicolon after the name that isn't separated by whitespace,
# leading to a parser error.
_grammar_base_name = Regex(r"[\w\+\-:\|/\\\(\)\[\]@#%!\^&~\$]+", re.UNICODE)\
    .setName("base name")
grammar_name = Combine(_grammar_base_name ^ Combine(
    _grammar_base_name + OneOrMore("." + _grammar_base_name)))\
    .setName("grammar name")


class BaseRef(object):
    """
    Base class for JSGF rule and grammar references.
    """
    def __init__(self, name):
        # Set the _name attribute and use the setter to validate the input
        # name.
        self._name = None
        self.name = name

    def __eq__(self, other):
        return type(self) == type(other) and self.name == other.name

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__, self.name)

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        return hash(self.name)

    @property
    def name(self):
        """
        The referenced name.

        :returns: str
        """
        return self._name

    @name.setter
    def name(self, value):
        # Validate the format of name
        if not self.valid(value):
            raise GrammarError("'%s' is not a valid %s name"
                               % (value, self.__class__.__name__))
        self._name = value

    @staticmethod
    def valid(name):
        """
        Static method for checking if a reference name is valid.

        This should be overwritten appropriately in subclasses.

        :param name: str
        :returns: bool
        """
        return base_name.matches(name) and not reserved_names.matches(name)
