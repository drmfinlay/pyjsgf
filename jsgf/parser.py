# encoding=utf-8
"""
This module contains functions that parse strings into ``Grammar``, ``Import``,
``Rule`` and ``Expansion`` objects.

=======================
Supported functionality
=======================
The parser functions support the following:

* Alternative sets, e.g. ``a|b|c``.
* Alternative set weights (e.g. ``/10/ a | /20/ b | /30/ c``).
* C++ style single/in-line and multi-line comments (``// ...`` and ``/* ... */``
  respectively).
* Import statements.
* Optional groupings, e.g. ``[this is optional]``.
* Public and private/hidden rules.
* Required groupings, e.g. ``(a b c) | (e f g)``.
* Rule references, e.g. ``<command>``.
* Sequences, e.g. ``run <command> [now] [please]``.
* Single or multiple JSGF tags, e.g. ``text {tag1} {tag2} {tag3}``.
* Special JSGF rules ``<NULL>`` and ``<VOID>``.
* Unary kleene star and repeat operators (``*`` and ``+``).
* Using Unicode alphanumeric characters for names, references and literals.
* Using semicolons or newlines interchangeably as line delimiters.


===========
Limitations
===========

This parser will fail to parse long alternative sets due to recursion depth limits.
The simplest workaround for this limitation is to split long alternatives into
groups. For example::

    // Raises an error.
    <n> = (0|...|100);

    // Will not raise an error.
    // As a side note, this will be parsed to '(0|...|100)'.
    <n> = (0|...|50)|(51|...|100);

This workaround could be done automatically in a future release.

This limitation also applies to long sequences, but it is much more difficult to
reach the limit.


=========================
Extended Backus–Naur form
=========================
`Extended Backus–Naur form
<https://en.wikipedia.org/wiki/Extended_Backus%E2%80%93Naur_form>`_ (EBNF) is a
notation for defining context-free grammars. The following is the EBNF used by
pyjsgf's parsers::

    alphanumeric = ? any alphanumeric Unicode character ? ;
    weight = '/' , ? any non-negative number ? , '/' ;
    atom = [ weight ] , ( literal | '<' , reference name , '>' |
           '(' , exp , ')' | '[' , exp , ']' ) ;
    exp = atom , [ { tag | '+' | '*' | exp | '|' , [ weight ] , exp } ] ;
    grammar = grammar header , grammar declaration ,
              [ { import statement } ] , { rule definition } ;
    grammar declaration = 'grammar' , reference name , line end ;
    grammar header = '#JSGF', ( 'v' | 'V' ) , version , word ,
                     word , line end ;
    identifier = { alphanumeric | special } ;
    import name = qualified name , [ '.*' ] | identifier , '.*' ;
    import statement = 'import' , '<' , import name  , '>' , line end ;
    line end = ';' | '\\n' ;
    literal = { word } ;
    qualified name = identifier , { '.' , identifier }  ;
    version = ? an integer or floating-point number ? ;
    reference name = identifier | qualified name ;
    rule definition = [ 'public' ] , '<' , reference name , '>' , '=' ,
                      exp , line end ;
    special = '+' | '-' | ':' | ';' | ',' | '=' | '|' | '/' | '$' |
              '(' | ')' | '[' | ']' | '@' | '#' | '%' | '!' | '^' |
              '&' | '~' | '\\' ;
    tag = '{' , { tag literal } , '}' ;
    tag literal = { word character | '\\{' | '\\}' } ;
    word = { word character } ;
    word character = alphanumeric | "'" | '-' ;


I've not included comments for simplicity; they can be used pretty much anywhere.
`pyparsing <https://github.com/pyparsing/pyparsing>`_ handles that for us.

"""

import re

from pyparsing import (Literal as PPLiteral, Suppress, OneOrMore, pyparsing_common,
                       White, Regex, Optional, cppStyleComment, ZeroOrMore, Forward,
                       ParseException, CaselessKeyword, CaselessLiteral, Word)
from six import string_types, integer_types

from .errors import GrammarError
from .expansions import (AlternativeSet, KleeneStar, Literal, NamedRuleRef, NullRef,
                         OptionalGrouping, RequiredGrouping, Repeat, Sequence,
                         VoidRef, SingleChildExpansion)
from .grammars import Grammar, Import
from .references import (optionally_qualified_name, import_name, grammar_name,
                         word, words)
from .rules import Rule


# Define angled brackets that don't appear in the output.
langle, rangle = map(Suppress, "<>")

# Define line endings as either ; or \n. This will also gobble empty lines.
line_delimiter = Suppress(OneOrMore(
    (PPLiteral(";") | White("\n")).setName("line end")
))


class WrapperExpansion(SingleChildExpansion):
    """ Wrapper expansion class used during the parser's post-processing stage. """


class WeightedExpansion(SingleChildExpansion):
    """
    Internal class used during parsing of alternative sets with weights.
    """

    def __init__(self, expansion, weight):
        super(WeightedExpansion, self).__init__(expansion)
        self.weight = weight
        self._child = expansion

    def __str__(self):
        return "%s(child=%s, weight=%s)" % (self.__class__.__name__,
                                            self.child, self.weight)

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        # Raise an error if the parent is invalid.
        if value and not isinstance(value, (AlternativeSet, WrapperExpansion)):
            raise GrammarError("weights cannot be used outside of alternative sets")
        self._parent = value

    @property
    def tag(self):
        return ""

    @tag.setter
    def tag(self, value):
        self.child.tag = value


class ParsedAlternativeSet(AlternativeSet):
    """
    AlternativeSet sub-class used by the parser to set alternative weights
    properly.

    This class handles unravelling nested alternative sets.
    """

    def __init__(self, *expansions):
        children = []
        weights = []
        last_weight = None
        for e in expansions:
            # Unravel any alternative set without a tag.
            if isinstance(e, AlternativeSet) and not e.tag:
                # Add each child and preserve the weights.
                if last_weight is not None:
                    weights.append((e.children[0], last_weight))
                    last_weight = None

                children.extend(e.children)
                weights.extend(list(e.weights.items()))
            elif isinstance(e, WeightedExpansion):
                children.append(e.child)
                weights.append((e.child, e.weight))
                e.child.parent = None
            elif isinstance(e, (float, integer_types)):
                last_weight = e
            else:
                if last_weight is not None:
                    weights.append((e, last_weight))
                    last_weight = None

                children.append(e)
        super(ParsedAlternativeSet, self).__init__(*children)
        self.weights = weights


def _post_process(tokens):
    """Do post-processing on the expansion tree produced by the parser."""
    def flatten_seq_chain(lst):
        children = []
        for x in lst:
            if isinstance(x, Sequence) and not x.tag:
                children.extend(flatten_seq_chain(x.children))
            else:
                children.append(x)
        return children

    def post_process(e):
        for child in list(e.children):
            post_process(child)

        # Remove redundant alternative sets, sequences and required groupings with
        # only one child. Do not remove such expansions if they have a tag or weight.
        should_remove_redundant = (
            len(e.children) == 1 and not e.tag and
            isinstance(e, (AlternativeSet, Sequence)) and
            not isinstance(e, RequiredGrouping) and

            # Check that the parent (if any) has no weight for e.
            not(e.parent and getattr(e.parent, "weights", False) and
                e in e.parent.weights)
        )
        if should_remove_redundant:
            child = e.children[0]
            children = e.parent.children
            children[children.index(e)] = child
            e.parent = None

        # Flatten any sequence chains.
        if len(e.children) > 1 and isinstance(e, Sequence) and \
                isinstance(e.children[1], Sequence):
            e.children = flatten_seq_chain(e.children)

    def transform(e):
        # Wrap e in a new expansion in case it is a redundant expansion.
        w = WrapperExpansion(e)

        # Do the post processing.
        post_process(w)
        if isinstance(w.child, WeightedExpansion):
            raise GrammarError("weights cannot be used outside of alternative sets")

        result = w.child
        result.parent = None
        return result

    return list(map(transform, tokens))


def _transform_tokens(tokens):
    lst = tokens.asList()

    # Handle tags.
    while "{" in lst:
        # Remove braces and tag text from the left and assign the text to the
        # expansion on the left.
        i = lst.index("{")

        # Raise an error if '*' or '+' is found; repeats cannot be tagged like that.
        previous = lst[i-1]
        if isinstance(previous, string_types):
            if previous in "*+":
                raise GrammarError("cannot tag repeats without using parenthesises")
            else:
                # I don't think this should happen...
                raise GrammarError("tag cannot be attached to string %s" % previous)

        if previous.tag:
            # Support tagging syntax like 'text {tag1} {tag2} {tag3}' by wrapping
            # the expansion on the left in required groupings.
            previous = RequiredGrouping(previous)
            previous.tag = lst.pop(i+1)
            lst[i-1] = previous
        else:
            previous.tag = lst.pop(i+1)

        # Remove both braces from the list.
        lst.pop(i)
        lst.pop(i)

    # Handle repeats by wrapping the preceding item in either a Repeat or
    # KleeneStar expansion.
    if "+" in lst or "*" in lst:
        cls = Repeat if lst.pop(1) == "+" else KleeneStar

        # Handle weighted expansions by weighting the repeat expansion.
        if isinstance(lst[0], WeightedExpansion):
            child = lst[0].children.pop()
            weight = lst[0].weight
            lst[0] = WeightedExpansion(cls(child), weight)
        else:
            lst[0] = cls(lst[0])

    # Handle atoms by returning the only token.
    if len(lst) == 1:
        return lst[0]

    # Handle alternative sets.
    elif "|" in lst:
        lst.remove("|")
        return ParsedAlternativeSet(*lst)

    # Handle sequences.
    elif len(lst) == 2:
        # If the second expansion is an alternative set, place the first expansion
        # inside a sequence with the first child of the alternative set.
        # Do not do this if the first expansion is a required grouping.
        # This handles rule expansions like "up <n> | left <n>".
        RG, AS = RequiredGrouping, AlternativeSet
        if not isinstance(lst[0], RG) and isinstance(lst[1], AS):
            child1 = lst[1].children.pop(0)
            seq = Sequence(lst[0], child1)
            lst[1].children.insert(0, seq)
            return lst[1]

        # Otherwise return a sequence.
        else:
            return Sequence(*lst)

    raise TypeError("unhandled tokens %s" % lst)


def _ref_action(tokens):
    if tokens[0] == "NULL":
        return NullRef()
    elif tokens[0] == "VOID":
        return VoidRef()
    else:
        return NamedRuleRef(tokens[0])


def _atom_action(tokens):
    if len(tokens) == 2:
        weight = tokens.pop(0)
        alt = tokens.pop(0)
        return WeightedExpansion(alt, weight)
    else:
        return tokens[0]


def get_exp_parser():
    """
    Get a pyparsing ParserElement for parsing JSGF rule expansions.

    The following operator precedence rules (highest to lowest) from JSGF Spec
    section 4.7 are enforced:
    1. Rule name in angle brackets, and a quoted or unquoted token.
    2. `()' parentheses for grouping and `[]' for optional grouping.
    3. Unary operators (`+', `*', and tag attachment) apply to the tightest immediate
       preceding rule expansion. (To apply them to a sequence or to alternatives,
       use `()' or `[]' grouping.)
    4. Sequence of rule expansions.
    5. `|' separated set of alternative rule expansions.

    :returns: Forward
    """
    # Make a forward declaration for defining an expansion. This is necessary for
    # recursive grammars.
    exp = Forward().setName("expansion")

    # Define some characters that don't appear in the output.
    lpar, rpar, lbrac, rbrac, slash = map(Suppress, "()[]/")

    # Define some other characters that do appear in the output.
    star, plus, pipe, lcurl, rcurl = map(PPLiteral, "*+|{}")

    # Define literals.
    literal = words.copy()\
        .setParseAction(lambda tokens: Literal(" ".join(tokens)))

    # Define rule references.
    rule_ref = (langle + optionally_qualified_name + rangle)\
        .setName("rule reference").setParseAction(_ref_action)

    # Define JSGF weights.
    weight = Optional(slash + pyparsing_common.number + slash)\
        .setName("alternative weight")

    # Define expansions inside parenthesises, optionals, literals and
    # rule references as atomic.
    req = (lpar + exp + rpar).setName("required grouping")\
        .setParseAction(lambda tokens: RequiredGrouping(tokens[0]))
    opt = (lbrac + exp + rbrac).setName("optional")\
        .setParseAction(lambda tokens: OptionalGrouping(tokens[0]))
    atom = (weight + (literal | rule_ref | req | opt))\
        .setParseAction(_atom_action)

    # Define tag text to one or more words defined by a regular expression.
    # Escaped brace characters ('\{' or '\}') are allowed in tag text.
    tag_text = OneOrMore(
        Regex(r"([\w\-\\']|\\{|\\})+", re.UNICODE).setName("tag text")
    )
    tag = lcurl + tag_text + rcurl

    # Define the root expansion as an atom plus additional alternatives, repeat or
    # kleene star operators, tags or expansions (for sequence definitions).
    root = (atom + ZeroOrMore(
        tag | plus | star | exp | pipe + weight + exp
    )).setParseAction(_transform_tokens)

    # Assign the expansion definition.
    exp <<= root

    # Set the parse action for exp and return it.
    exp.setParseAction(_post_process)
    return exp


def get_rule_parser():
    equals = Suppress("=")
    public = CaselessKeyword("public")

    def _make_rule(tokens):
        # Make a Rule object from three tokens.
        visible, name, e = tokens
        return Rule(name, visible, e)

    # Make a parser element for the <rule>.visible attribute.
    visibility = Optional(public).setParseAction(lambda tokens: bool(tokens))

    # Define the rule parser and set its parse action. Also ignore any C++ style
    # comments around it.
    parser = (visibility + langle + optionally_qualified_name + rangle +
              equals + expansion_parser + line_delimiter)\
        .setName("rule definition")
    parser.setParseAction(_make_rule).ignore(cppStyleComment)
    return parser


def get_grammar_parser():
    # Define keywords and literals.
    import_ = Suppress(CaselessKeyword("import"))
    grammar_ = Suppress("grammar")

    def _make_grammar(tokens):
        # Create a new Grammar object.
        result = Grammar()

        # Get the attributes in the header as well as the name.
        version, charset, language, name = tokens[0:4]

        # Use charset as the language instead if it is 2 characters long and no
        # language was specified.
        if not language and len(charset) == 2:
            language = charset
            charset = ""

        # Set the header attributes and grammar name.
        result.jsgf_version = version[1:]
        result.charset_name = charset
        result.language_name = language
        result.name = name

        # Add the remaining imports/rules to the grammar.
        for token in tokens[4:]:
            if isinstance(token, Import):
                result.add_import(token)
            else:
                result.add_rule(token)

        # Return the new grammar object.
        return result

    # Define parser elements for the grammar header.
    version_no = Regex(r"(v|V)(\d+\.\d+|\d+\.|\.\d+)") \
        .setName("version number")

    def optional_header_action(tokens):
        return tokens if tokens else [""]

    charset_name = Optional(word.copy()).setName("character set") \
        .setParseAction(optional_header_action)
    language_name = Optional(word.copy()).setName("language name") \
        .setParseAction(optional_header_action)

    header_line = (Suppress(CaselessLiteral("#JSGF")) + version_no + charset_name +
                   language_name + line_delimiter).setName("grammar header")

    # Define the grammar name line, import statements and rule lines. All lines
    # should support C++ style comments (/* comment */ or // comment).
    name_line = (grammar_ + grammar_name + line_delimiter) \
        .setName("grammar declaration").ignore(cppStyleComment)
    import_statement = (import_ + langle + import_name + rangle + line_delimiter) \
        .setParseAction(lambda tokens: Import(tokens[0])).ignore(cppStyleComment)

    # Define the grammar parser element, then set its name and parse action.
    parser = (header_line + name_line + ZeroOrMore(import_statement) +
              OneOrMore(rule_parser))
    parser.setName("grammar").setParseAction(_make_grammar)
    return parser


# Initialise each of the main parsers.
expansion_parser = get_exp_parser()
rule_parser = get_rule_parser()
grammar_parser = get_grammar_parser()


def parse_expansion_string(s):
    """
    Parse a string containing a JSGF expansion and return an ``Expansion`` object.

    :param s: str
    :returns: Expansion
    :raises: ParseException, GrammarError
    """
    # Parse the string and return the first (and only) expansion object that was
    # generated. Pass True as the second argument to catch trailing invalid tokens.
    return expansion_parser.parseString(s, True).asList()[0]


def parse_rule_string(s):
    """
    Parse a string containing a JSGF rule definition and return a ``Rule`` object.

    :param s: str
    :returns: Rule
    :raises: ParseException, GrammarError
    """
    return rule_parser.parseString(s, True).asList()[0]


def parse_grammar_string(s):
    """
    Parse a JSGF grammar string and return a ``Grammar`` object with the defined
    attributes, name, imports and rules.

    :param s: str
    :returns: Grammar
    :raises: ParseException, GrammarError
    """
    return grammar_parser.parseString(s, True).asList()[0]


def valid_grammar(s):
    """
    Whether a string is a valid JSGF grammar string.

    Note that this method will not return False for grammars that are otherwise
    valid, but have out-of-scope imports.

    :param s: str
    :returns: bool
    """
    try:
        parse_grammar_string(s)
        return True
    except (ParseException, GrammarError):
        # print(e)
        return False


def parse_grammar_file(path):
    """
    Parse a JSGF grammar file and a return a ``Grammar`` object with the defined
    attributes, name, imports and rules.

    This method will not attempt to import rules or grammars defined in other files,
    that should be done by an import resolver, not a parser.

    :param path: str
    :returns: Grammar
    :raises: ParseException, GrammarError
    """
    # Read all lines from the file, join them and call parse_grammar_string.
    # Note that lines should retain any newline characters or semicolons.
    with open(path, "r") as f:
        lines = f.readlines()

    content = "".join(lines)

    return parse_grammar_string(content)
