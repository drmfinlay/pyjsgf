"""
Example demonstrating the use of JSGF tags and related methods.
"""

from jsgf import PublicRule, Grammar


def main():
    # Define a new 'hello' rule with a tag on the root expansion.
    r = PublicRule("hello", "hello world")
    r.expansion.tag = "greet"

    # Get the tags of the new rule and print them.
    print("Tags: %s\n" % r.tags)

    # Initialise a new grammar and add the 'hello' rule to it.
    g = Grammar()
    g.add_rule(r)

    # Print the compiled grammar
    print("Compiled grammar is:\n%s" % g.compile())

    # Find and print rules tagged with "greet"
    print("Tagged rules are:\n%s" % g.find_tagged_rules("greet"))


if __name__ == '__main__':
    main()
