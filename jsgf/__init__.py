"""
This package contains classes and functions for compiling, matching and parsing JSGF
grammars using rules, imports and rule expansions, such as sequences, repeats,
optional and required groupings.
"""
from .errors import CompilationError
from .errors import ExpansionError
from .errors import GrammarError
from .errors import JSGFImportError
from .errors import MatchError

from .expansions import AlternativeSet
from .expansions import Expansion
from .expansions import filter_expansion
from .expansions import find_expansion
from .expansions import flat_map_expansion
from .expansions import JointTreeContext
from .expansions import KleeneStar
from .expansions import Literal
from .expansions import map_expansion
from .expansions import OptionalGrouping
from .expansions import restore_current_matches
from .expansions import Repeat
from .expansions import RequiredGrouping
from .expansions import RuleRef
from .expansions import save_current_matches
from .expansions import Sequence
from .expansions import SingleChildExpansion
from .expansions import TraversalOrder
from .expansions import VariableChildExpansion
from .expansions import NamedRuleRef, NullRef, VoidRef

from .grammars import Grammar
from .grammars import Import
from .grammars import RootGrammar

from .parser import parse_grammar_string, parse_grammar_file, valid_grammar
from .parser import parse_expansion_string, parse_rule_string

from .references import BaseRef

from .rules import PrivateRule
from .rules import PublicRule
from .rules import Rule

# Things kept in for backwards compatibility.
from .rules import HiddenRule
