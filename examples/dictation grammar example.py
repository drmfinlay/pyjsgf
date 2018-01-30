"""
Example showing use of the jsgf.ext DictationGrammar class for matching and
compiling rules that use regular JSGF expansions like Literal and Sequence as
well as Dictation expansions.
"""

from jsgf import PublicRule, Sequence
from jsgf.ext import Dictation, DictationGrammar


def main():
    # Create a simple rule using a Dictation expansion.
    rule = PublicRule("Hello_X", Sequence("hello", Dictation()))

    # Create a new DictationGrammar using the simple rule.
    grammar = DictationGrammar([rule])

    # Print the compiled grammar
    print(grammar.compile())

    # Match against some speech strings.
    # find_matching_rules has an optional second parameter for advancing to
    # the next part of the rule, which is set to False here.
    matching = grammar.find_matching_rules("hello", False)
    print("Matching rule: %s" % matching[0])  # first part of rule

    # Go to the next part of the rule.
    matching[0].set_next()

    # Match the dictation part. This can be anything.
    matching = grammar.find_matching_rules("world")
    print("Matching rule: %s" % matching[0])

    # The entire match and the original rule's current_match value will both be
    'hello world'
    print(matching[0].entire_match)
    print(rule.expansion.current_match)


if __name__ == '__main__':
    main()
