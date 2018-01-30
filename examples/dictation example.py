"""
Example showing use of the jsgf.ext Dictation expansion.
"""

from jsgf import PublicRule, Sequence, map_expansion
from jsgf.ext import Dictation


def main():
    # Create a simple rule using a Dictation expansion.
    dictation = Dictation()
    dictation.tag = "dictation"  # add a tag to the expansion
    rule = PublicRule("dictation", Sequence("hello", dictation))

    # Print the compiled rule
    print("Compiled rule: %s" % rule.compile())

    # Match a speech string against the rule.
    speech = "hello world"
    print("Rule matches '%s': %s." % (speech, rule.matches(speech)))

    # Print the rule's current_match values using map_expansion.
    def print_match(x):
        print("Match for %s: %s" % (x, x.current_match))

    map_expansion(rule.expansion, print_match)


if __name__ == '__main__':
    main()
