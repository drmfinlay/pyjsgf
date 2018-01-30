"""
Example showing use of some recursive expansion functions.
"""
from jsgf import *


def main():
    # Create a new public rule using speech alternatives.
    rule = PublicRule("greet", Sequence(AlternativeSet("hello", "hey"), "there"))

    # Define a function to get the rule's current_match values using
    # flat_map_expansion.
    def get_values():
        return flat_map_expansion(rule.expansion, lambda x: x.current_match)

    # All values will initially be set to None.
    print("current_match values before matching: %s" % get_values())

    # Match a speech string and print the values again.
    rule.matches("hello there")
    print("current_match values after matching: %s" % get_values())

    # Use filter_expansion to get expansions with no current_match value.
    # This will get Literal("hey") which wasn't matched.
    print(filter_expansion(rule.expansion, lambda x: not x.current_match)[0])

    # Use map_expansion to print a representation of the rule's expansion tree
    def f(x):
        # Print the expansion with an indentation based on the number of
        # ancestors
        n, p = 0, x.parent
        while p:
            n += 4
            p = p.parent

        print("%s%s" % (" " * n, x))

    map_expansion(rule.expansion, f)


if __name__ == '__main__':
    main()
