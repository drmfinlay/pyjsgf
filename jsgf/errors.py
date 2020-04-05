"""
This module contains pyjsgf's exception classes.
"""


class GrammarError(Exception):
    """
    Error raised when invalid grammar operations occur.

    This error is raised under the following circumstances:

    * When matching or resolving referenced rules that are out-of-scope.
    * Attempting to enable, disable or retrieve a rule that isn't in a grammar.
    * Attempting to remove rules referenced by other rules in the grammar.
    * Attempting to add a rule to a grammar using an already taken name.
    * Using an invalid name (such as *NULL* or *VOID*) for a grammar name, rule
      name or rule reference.
    * Passing a grammar string with an illegal expansion to a parser function, such
      as a tagged repeat (e.g. ``blah+ {tag}``).
    """


class JSGFImportError(Exception):
    """
    Error raised when a JSGF import statement could not be resolved.

    This error is raised under the following circumstances:

    * When a grammar file could not be found and read from successfully during import
      resolution.
    * When an imported grammar does not define the specified rule.
    * When an imported grammar does define the specified rule, but it is private.
    """


class ExpansionError(Exception):
    """
    This error class has been **deprecated** and is no longer used.
    """


class MatchError(Exception):
    """
    This error class has been **deprecated** and is no longer used.
    """


class CompilationError(Exception):
    """
    Error raised when compiling an invalid grammar.

    This error is currently only raised if a ``Literal`` expansion is compiled with
    the empty string (``''``) as its ``text`` value.
    """
