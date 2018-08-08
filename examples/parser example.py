"""
Example use of the pyjsgf parse_grammar_string function.

The parse_grammar_file, parse_rule_string and parse_expansion_string functions
are also available and work in a similar way.
"""

from jsgf import parse_grammar_string

# Parse a grammar string with parse_grammar_string and get a Grammar object back.
grammar = parse_grammar_string(
    "#JSGF V1.0 UTF-8 en;"
    "grammar example;"
    "public <greet> = hello world {tag};"
)

# Print it.
print(grammar)

# Get the rule that matches "hello world".
rule = grammar.find_matching_rules("hello world")[0]
print("Matching rule: %s" % rule)

# Tags are also parsed and will work as expected.
print("Matched tags: %s" % rule.matched_tags)
