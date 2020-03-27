"""
This sub-package contains extensions to JSGF, notably the ``Dictation``,
``SequenceRule`` and ``DictationGrammar`` classes.
"""

from .expansions import Dictation
from .expansions import dictation_in_expansion
from .expansions import only_dictation_in_expansion
from .expansions import no_dictation_in_expansion
from .expansions import dictation_and_literals_in_expansion

from .rules import SequenceRule
from .rules import PublicSequenceRule
from .rules import PrivateSequenceRule

from .grammars import DictationGrammar

# Things kept in for backwards compatibility.
from .rules import HiddenSequenceRule
