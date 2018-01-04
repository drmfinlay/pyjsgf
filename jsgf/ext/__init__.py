"""
This package contains extensions that aren't part of the JSGF specification.
"""

from .expansions import Dictation
from .expansions import dictation_in_expansion
from .expansions import only_dictation_in_expansion
from .expansions import no_dictation_in_expansion
from .expansions import dictation_and_literals_in_expansion

from .rules import SequenceRule
from .rules import PublicSequenceRule
from .rules import HiddenSequenceRule

from .grammars import DictationGrammar
