"""
Classes and ParserElements for referencing rules and grammars as well as validating
reference names.
"""

from .errors import GrammarError
from pyparsing import Regex, Optional, OneOrMore, Combine, NotAny
from pyparsing import Literal as PPLiteral  # to differentiate from jsgf.Literal
import re


RESERVED_NAMES = Combine(PPLiteral("NULL") ^ PPLiteral("VOID"))

# This will match one or more alphanumeric Unicode characters and/or any of the
# following special characters: +-:;,=|/\()[]@#%!^&~$
# It will not match any reserved name.
BASE_NAME = Regex(r"[\w\+\-;:\|/\\\(\)\[\]@#%!\^&~\$]+", re.UNICODE) +\
            NotAny(RESERVED_NAMES).setName("base name")

# Qualified name is the base name plus one or more base names joined by dots
# i.e. Java package syntax
QUALIFIED_NAME = Combine(BASE_NAME + OneOrMore("." + BASE_NAME))

# A grammar name or a rule reference expansion is either a base name or a qualified
# name.
OPTIONALLY_QUALIFIED_NAME = Combine(BASE_NAME ^ QUALIFIED_NAME)

# Import names are similar, except that they can have wildcards on the end for
# importing all public rules in a grammar
IMPORT_NAME = Combine((QUALIFIED_NAME + Optional(".*")) ^ (BASE_NAME + ".*"))


class BaseRef(object):
    """
    Base class for JSGF rule and grammar references.
    """
    def __init__(self, name):
        # Validate the format of name
        if not self.valid(name):
            raise GrammarError("'%s' is not a valid %s name"
                               % (name, self.__class__.__name__))
        self._name = name

    def __eq__(self, other):
        return type(self) == type(other) and self.name == other.name

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def name(self):
        """
        The referenced name.
        :rtype: str
        """
        return self._name

    @staticmethod
    def valid(name):
        """
        Static method for checking if a reference name is valid.
        :type name: str
        :rtype: bool
        """
        return BASE_NAME.matches(name)
