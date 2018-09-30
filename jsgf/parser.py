# encoding=utf-8
"""
This module contains functions that parse strings into ``Grammar``, ``Import``,
``Rule`` and ``Expansion`` objects.

=======================
Supported functionality
=======================
The parser functions support the following:

* Public and private/hidden rules.
* Import statements.
* Alternative sets, e.g. ``a|b|c``.
* Expansion sequences.
* Required groupings, e.g. ``(a b c) | (e f g)``.
* Optionals, e.g. ``[this is optional]``.
* Single or multiple JSGF tags, e.g. ``text {tag1} {tag2} {tag3}``.
* Unary kleene star and repeat operators (``*`` and ``+``).
* Rule references, e.g. ``<command>``.
* Special rules ``<NULL>`` and ``<VOID>``.
* C++ style single/in-line and multi-line comments (``// ...`` and ``/* ... */``
  respectively).
* Using semicolons or newlines interchangeably as line delimiters.
* Using Unicode alphanumerics for names, references and literals.


===========
Limitations
===========
There are a few limitations with this parser:

* It will fail to parse long sequences and alternative sets. A workaround for this
  is to split the alternatives/sequences into shorter rules and use references. This
  could be probably be done automatically somehow in a future release.
* Alternative set weights (e.g. ``/10/ a | /20/ b | /30/ c``) are not yet
  implemented, so they won't be parsed correctly.


=========================
Extended Backus–Naur form
=========================
`Extended Backus–Naur form
<https://en.wikipedia.org/wiki/Extended_Backus%E2%80%93Naur_form>`_ (EBNF) is a
notation for defining context-free grammars. The following is the EBNF used by
pyjsgf's parsers::

    alphanumeric = ? any alphanumeric Unicode character ? ;
    atom = literal | '<' , reference name , '>' | '(' , exp , ')' |
           '[' , exp , ']' ;
    exp = atom , [ { tag | '+' | '*' | exp | '|' , exp } ] ;
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

from pyparsing import *
from pyparsing import Literal as PPLiteral

from .rules import Rule
from .grammars import Grammar, Import
from .expansions import *
from .references import optionally_qualified_name, import_name, grammar_name,\
    word, words

from six import string_types

# Define angled brackets that don't appear in the output.
langle, rangle = map(Suppress, "<>")

# Define line endings as either ; or \n. This will also gobble empty lines.
line_delimiter = Suppress(OneOrMore(
    (PPLiteral(";") | White("\n")).setName("line end")
))


def _post_process(tokens):
    """Do post-processing on the expansion tree produced by the parser."""
    def flatten_chain(lst, inst):
        children = []
        for x in lst:
            if isinstance(x, inst):
                children.extend(flatten_chain(x.children, inst))
            else:
                children.append(x)
        return children

    def replace_expansion(x, y):
        if x.parent:
            children = x.parent.children
            children[children.index(x)] = y

    def transform(e):
        result = e
        for child in e.children:
            transform(child)

        # Remove redundant alternative sets, sequences and required groupings with
        # only one child. Do not remove such expansions if they have a tag.
        if (len(e.children) == 1 and isinstance(e, (AlternativeSet, Sequence))
                and not e.tag):
            replace_expansion(e, e.children[0])
            result = e.children[0]

        # Flatten any alternative set or sequence chains.
        if len(e.children) >= 1 and isinstance(e, AlternativeSet) and \
                isinstance(e.children[1], AlternativeSet):
            e.children = flatten_chain(e.children, AlternativeSet)
        elif len(e.children) > 1 and isinstance(e, Sequence) and \
                isinstance(e.children[1], Sequence):
            e.children = flatten_chain(e.children, Sequence)

        return result

    return list(map(transform, tokens))


def _unwrap_tokens(tokens):
    """
    Take parse tokens or a list and return a list that has no wrapping lists.
    E.g. [[[Literal("text")]]] -> [Literal("text")]

    :param tokens: ParseResults
    :returns: list
    """
    if isinstance(tokens, ParseResults):
        l = tokens.asList()
    elif isinstance(tokens, list):
        l = tokens
    else:
        raise TypeError("_unwrap_tokens can only take ParseResults or lists")

    while len(l) == 1 and isinstance(l[0], list):
        l = l[0]

    return l


def _transform_tokens(t, tokens):
    """
    Function for transforming ParsingResults / lists into expansions of type t.
    """
    lst = _unwrap_tokens(tokens)

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

    # Handle the root case for alternatives, repeats, kleene stars, tags and
    # sequences.
    repeat = "+" in lst or "*" in lst
    if t is Expansion:
        # Handle atoms by returning the only token.
        if len(lst) == 1:
            return lst[0]

        # Handle sequences.
        elif len(lst) == 2 and not repeat:
            return Sequence(*lst)

        # Handle repeats by returning an expansion of the appropriate type.
        elif len(lst) >= 2 and repeat:
            cls = Repeat if lst.pop(1) == "+" else KleeneStar
            lst[0] = cls(lst[0])

            # Return a Sequence if there are two or more tokens left, otherwise
            # return the Repeat/KleeneStar expansion.
            if len(lst) >= 2:
                return Sequence(*lst)
            else:
                return lst[0]

        elif len(lst) == 3 and lst[1] == "|":
            # Handle tokens of form [e, '|', [x, ...]] as alternatives
            # Alt. sets are parsed as a nested list structure. E.g:
            # a|b|c -> [Literal("a"), [Literal("b"), [Literal("c")]]]
            lst.pop(1)
            return AlternativeSet(*lst)

    elif t is Literal:
        # Join the token list into one string.
        return t(" ".join(lst))

    # Handle rule references.
    elif t is NamedRuleRef:
        if lst[0] == "NULL":
            return NullRef()
        elif lst[0] == "VOID":
            return VoidRef()
        else:
            return NamedRuleRef(lst[0])

    elif t in (OptionalGrouping, RequiredGrouping):
        # Create an expansion of type t using the token list.
        return t(*lst)

    # If t is an unhandled expansion type, raise an error.
    raise TypeError("unhandled expansion type %s" % t.__name__)


def _get_type_action(t):
    # Return a function to make an expansion object of type t from ParsingResults
    # objects (tokens) or lists.
    return lambda tokens: _transform_tokens(t, tokens)


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
    lpar, rpar, lbrac, rbrac = map(Suppress, "()[]")

    # Define some other characters that do appear in the output.
    star, plus, pipe, lcurl, rcurl = map(PPLiteral, "*+|{}")

    # Define literals.
    literal = words.copy()\
        .setParseAction(_get_type_action(Literal))

    # Define rule references.
    rule_ref = Group(langle + optionally_qualified_name + rangle)\
        .setName("rule reference").setParseAction(_get_type_action(NamedRuleRef))

    # Define expansions inside parenthesises, optionals, literals and
    # rule references as atomic.
    req = Group(lpar + exp + rpar).setName("required grouping")\
        .setParseAction(_get_type_action(RequiredGrouping))
    opt = Group(lbrac + exp + rbrac).setName("optional")\
        .setParseAction(_get_type_action(OptionalGrouping))
    atom = literal | rule_ref | req | opt

    # Define tag text to one or more words defined by a regular expression.
    # Escaped brace characters ('\{' or '\}') are allowed in tag text.
    tag_text = OneOrMore(
        Regex(r"([\w\-\\']|\\{|\\})+", re.UNICODE).setName("tag text")
    )
    tag = lcurl + tag_text + rcurl

    # Define the root expansion as an atom plus additional alternatives, repeat or
    # kleene star operators, tags or expansions (for sequence definitions).
    root = Group(atom + ZeroOrMore(
        (tag | plus | star | exp | pipe + exp)
    )).setParseAction(_get_type_action(Expansion))

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

    # Define a parser element for the grammar header.
    version_no = Regex(r"(v|V)(\d+\.\d+|\d+\.|\.\d+)") \
        .setName("version number")
    language_name = word.copy().setName("language name")
    charset_name = word.copy().setName("character set name")
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
