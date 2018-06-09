"""
Example demonstrating the use of JSGF tags and related methods/properties.
"""

from jsgf import PublicRule, Grammar, AlternativeSet, Literal, Sequence


def main():
    # Define a open/close file rule.
    open, close = Literal("open"), Literal("close")
    open.tag, close.tag = "OPEN", "CLOSE"
    cmd = PublicRule("command", Sequence(AlternativeSet(open, close), "the file"))

    # Print the tags of the 'command' rule.
    print("Tags: %s\n" % cmd.tags)

    # Initialise a new grammar and add the rule to it.
    g = Grammar()
    g.add_rule(cmd)

    # Print the compiled grammar
    print("Compiled grammar is:\n%s" % g.compile())

    # Find and print rules tagged with "OPEN"
    print("Tagged rules are:\n%s\n" % g.find_tagged_rules("OPEN"))

    # Matching tags can be retrieved using r.get_tags_matching
    # The Rule.matched_tags property can also be used if Rule.matches or
    # Grammar.find_matching_rules has been called first.
    speech = "open the file"
    print("Tags matching '%s' are: %s" % (speech, cmd.get_tags_matching(speech)))


if __name__ == '__main__':
    main()
