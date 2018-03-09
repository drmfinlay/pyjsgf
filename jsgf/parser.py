"""
JSGF parser functions

The main functions of interest in this module are parse_grammar_string,
parse_grammar_file, parse_rule_string, parse_expansion_string and valid_grammar.

Note: this parser does not strictly use ';' as the line ending character.
Newline characters and/or semicolons may be used interchangeably. For example:

#JSGF V1.0 UTF-8 en
grammar test
public <rule> = hello

is equivalent to:

#JSGF V1.0 UTF-8 en;
grammar test;
public <rule> = hello;

as well as:

#JSGF V1.0 UTF-8 en; grammar test; public <rule> = hello
"""

from pyparsing import *
from pyparsing import CaselessLiteral as Caseless
from .rules import Rule
from .grammars import Grammar, Import
from .references import QUALIFIED_NAME, OPTIONALLY_QUALIFIED_NAME, IMPORT_NAME
from .expansions import *

# Define some special characters as parsing tokens ignored in parse output.
LPAR, RPAR, LANGLE, RANGLE, LBRAC, RBRAC, EQUALS = map(Suppress, "()<>[]=")
STAR, PLUS, PIPE = map(Suppress, "*+|")

# Define a word as one or more alphanumeric Unicode characters plus a few special
# characters: -'
WORD = Regex(r"[\w\-\']+", re.UNICODE)

# Expansion definition
EXPANSION = Forward().setName("expansion")

# Parser elements for Expansion classes
LITERAL = OneOrMore(WORD).setName("Literal")
RULE_REF = (LANGLE + OPTIONALLY_QUALIFIED_NAME + RANGLE).setName("RuleRef")
OPTIONAL = (LBRAC + EXPANSION + RBRAC).setName("OptionalGrouping")
REPEAT = (EXPANSION + PLUS).setName("Repeat")
KLEENE = (EXPANSION + STAR).setName("KleeneStar")
ALT_SET = (EXPANSION + PIPE + EXPANSION).setName("AlternativeSet")
SEQUENCE = (EXPANSION + EXPANSION).setName("Sequence")

# Note that RequiredGrouping will only ever get one child.
REQ_GROUP = (LPAR + EXPANSION + RPAR).setName("RequiredGrouping")

# Set parse actions for each Expansion class to yield equivalent Expansion objects
# instead of strings.
LITERAL.setParseAction(lambda tokens: Literal(tokens[0]))
RULE_REF.setParseAction(lambda tokens: NamedRuleRef(tokens[0]))
OPTIONAL.setParseAction(lambda tokens: OptionalGrouping(tokens[0]))
REPEAT.setParseAction(lambda tokens: Repeat(tokens[0]))
KLEENE.setParseAction(lambda tokens: KleeneStar(tokens[0]))
ALT_SET.setParseAction(lambda tokens: AlternativeSet(*tokens))
REQ_GROUP.setParseAction(lambda tokens: RequiredGrouping(*tokens))
SEQUENCE.setParseAction(lambda tokens: Sequence(*tokens))


# TODO Allow definition of right recursive rules by transforming them using a parse
# action:
# '<do> = do | <do>' -> '<do> = do+;'
# and '<command> = <action> | (<action> and <command>);


# TODO Enforce operator precedence (highest to lowest) from JSGF Spec 4.7 Precedence
# 1. Rule name in angle brackets, and a quoted or unquoted token.
# 2. `()' parentheses for grouping and `[]' for optional grouping.
# 3. Unary operators (`+', `*', and tag attachment) apply to the tightest immediate
#    preceding rule expansion. (To apply them to a sequence or to alternatives,
#    use `()' or `[]' grouping.)
# 4. Sequence of rule expansions.
# 5. `|' separated set of alternative rule expansions.

# TODO Make recursive parsing work properly
EXPANSION <<= (
    Group(LITERAL) |
    RULE_REF |
    OPTIONAL |
    REPEAT |
    KLEENE |
    ALT_SET |
    REQ_GROUP |
    SEQUENCE
)

# Example header: #JSGF V1.0 UTF-8 en;
FLOAT = Regex(r"\d+\.\d+|\d+\.|\.\d+")  # this will do for version numbers
JSGF_VERSION = Suppress(Caseless("V")) + FLOAT
HEADER = Suppress(Caseless("#JSGF")) + JSGF_VERSION + WORD + WORD

# Import statements
IMPORT_STATEMENT = (Suppress(Caseless("import")) + LANGLE + IMPORT_NAME +
                    RANGLE).setParseAction(lambda tokens: Import(tokens[0]))

# Parser element for the <rule>.visible attribute
PUBLIC = Optional(Caseless("public"))\
    .setParseAction(lambda tokens: True if tokens[0] else False)


def _make_rule(tokens):
    """Make a Rule object from three tokens"""
    visible, name, e = tokens
    return Rule(name, visible, e.asList()[0])


# Rule and grammar definitions with parsing actions yielding Rule and Grammar
# objects respectively
RULE = (PUBLIC + QUALIFIED_NAME + EQUALS + EXPANSION)\
    .setName("Rule").setParseAction(_make_rule)
GRAMMAR_START = (Suppress(Caseless("grammar")) + OPTIONALLY_QUALIFIED_NAME)\
    .setParseAction(lambda tokens: Grammar(name=tokens[0]))


def parse_expansion_string(s):
    """
    Parse a string containing a JSGF expansion and return an Expansion object.
    :type s: str
    :rtype: Expansion
    """
    return EXPANSION.parseString(s).asList()[0]


def parse_rule_string(s):
    """
    Parse a string containing a JSGF rule definition and return a Rule object.
    :type s: str
    :rtype: Rule
    """
    return RULE.parseString(s).asList()[0]


def valid_grammar(s, require_header):
    """
    Whether a string is a valid JSGF grammar string.
    A grammar string can contain multiple grammar definitions.
    Note that this method will not return False for grammars that are otherwise
    valid, but have out-of-scope imports.
    :type s: str
    :param require_header: whether the string must have a valid JSGF header
    :rtype: bool
    """
    try:
        parse_grammar_string(s, require_header=require_header)
        return True
    except (ParseException, GrammarError) as e:
        print(e)
        return False


def get_grammar_lines(s):
    """
    Get a list of non-empty grammar lines from a grammar string.
    Grammar lines must end with a semicolon or a newline or both.
    Empty lines will be removed.
    :type s: str
    :rtype: list
    """
    # Split on either \n or ';'
    # Strip whitespace from resulting strings and drop empty ones.
    # Note: re is imported by pyparsing
    return [l.strip() for l in re.split(r"[\n;]", s) if l.strip()]


def parse_grammar_string(s, imports=None, require_header=True):
    """
    Parse a JSGF grammar string and return a list of Grammar objects with the
    defined rules.
    :type s: str
    :param imports: imported grammars or rules used in the grammar to parse
    :param require_header: whether the string must have a valid JSGF header
    :rtype: list
    """
    if not imports:
        imports = []

    # Collect imports names
    import_dict = {}

    def collect_names(x):
        assert x.name not in import_dict
        import_dict[x.name] = x
        if isinstance(x, Grammar):
            # Also add the rule names: <grammar_name>.<rule_name>
            for r in x.rules:
                import_dict["%s.%s" % (x.name, r.name)] = r

    for i in imports:
        collect_names(i)

    # Get non-empty grammar lines delimited by semicolons and/or newlines.
    lines = get_grammar_lines(s)

    if not lines:
        raise GrammarError("invalid grammar string %s" % s)

    # The first line should be the header. E.g. #JSGF V1.0 UTF-8 en;
    version, charset, language = Grammar.default_header_values
    if not require_header:
        if HEADER.matches(lines[0]):  # there is a header, use its values
            version, charset, language = HEADER.parseString(lines[0])
            lines = lines[1:]  # consume the first line
    else:
        version, charset, language = HEADER.parseString(lines[0])
        lines = lines[1:]

    # Find each grammar defined in the string (there can be more than one).
    result = []
    rule_defined = False
    for l in lines:
        if GRAMMAR_START.matches(l):  # New grammar definition has started
            # Add a new grammar to the result list.
            grammar = GRAMMAR_START.parseString(l).asList()[0]
            grammar.jsgf_version = version
            grammar.charset_name = charset
            grammar.language_name = language
            result.append(grammar)
        elif not result:
            # No grammar has been defined yet. This is an error.
            raise GrammarError("expected grammar declaration, got '%s' instead" % l)
        elif IMPORT_STATEMENT.matches(l):
            import_ = IMPORT_STATEMENT.parseString(l)[0]

            # Check if this is a wildcard import and that the grammar is in scope
            if import_.name.endswith(".*"):
                imported_grammar = import_.name[:-2]
                if (imported_grammar in import_dict and
                        not isinstance(import_dict[imported_grammar], Grammar)
                        or imported_grammar not in import_dict):
                    raise GrammarError("cannot import rules from out of scope "
                                       "grammar %s" % imported_grammar)

            elif import_.name not in import_dict:
                raise GrammarError("cannot import out of scope rule/grammar '%s'"
                                   % import_.name)

            # Add new Import objects to the current grammar
            current_grammar = result[len(result) - 1]
            current_grammar.add_import(import_)

            # TODO Add the import either to the current grammar if it's a rule
            # or to the result list
            pass

        elif RULE.matches(l):
            rule_defined = True

            # This should be a rule line.
            pass

    def replace(x, y):
        """Replace expansion x with expansion y."""
        if x.parent:
            children = x.parent.children
            children[children.index(x)] = y
        else:
            x.rule.expansion = y

    # Resolve all NamedRuleRef expansions now that all grammars, imports and rules
    # have been collected
    for grammar in result:
        rule_refs = []
        for rule in grammar.rules:
            rule_refs.extend(filter_expansion(
                rule.expansion, lambda x: isinstance(x, NamedRuleRef)
            ))

        for ref in rule_refs:
            # First check if the reference is for a rule in the current grammar.
            if ref.name in grammar.rule_names:
                replace(ref, RuleRef(grammar.get_rule_from_name(ref.name)))

            # Otherwise check if ref is referencing an imported rule
            elif (ref.name in import_dict.keys() and
                    isinstance(import_dict[ref.name], Rule)):
                replace(ref, RuleRef(ref.rule))

    # If no rules have been defined, then this is not a valid grammar string.
    if not rule_defined:
        raise GrammarError("no rules defined in grammar string: %s" % s)

    return result


def parse_grammar_file(path):
    """
    Parse a JSGF grammar file and return a list of populated Grammar objects
    defined in it.

    This method will also attempt to import grammars and rules defined in
    other files as specified.
    :type path: str
    :rtype: list
    """
    # Read all lines from the file, join them and call parse_grammar_string.
    # Note that lines should retain any newline characters.
    with open(path, "r") as f:
        lines = f.readlines()

    content = "".join(lines)

    # TODO Handle importing/parsing other files if there are any import lines
    # TODO Check working directory name and import assuming a Java package hierarchy
    # TODO If imports have non-hierarchical names, use the current working directory
    # TODO Use os.walk (upwards) to find grammar files to import if using hierarchy
    # Collect import statements
    import_statements = IMPORT_STATEMENT.searchString(content).asList()

    return parse_grammar_string(content)
