from jsgf import PublicRule, OptionalGrouping, Grammar, Sequence


def print_matching(grammar, speech):
    matching = grammar.find_matching_rules(speech)
    if not matching:
        print("No rules matched '%s'." % speech)
    else:
        print("Rules matching '%s':" % speech)
        for r in matching:
            print(r)
    print("")


def main():
    # The Sequence expansion requires all of its children expansions to be spoken
    # in sequence. The OptionalGrouping expansion optionally requires its child
    # expansion to be spoken.

    # Create a public rule using an optional expansion
    rule = PublicRule("greet", Sequence("hey", OptionalGrouping("there")))

    # Create a grammar and add the new rule to it
    grammar = Grammar("g")
    grammar.add_rule(rule)

    # Compile the grammar using compile()
    print("Grammar '%s' compiles to:" % grammar.name)
    print(grammar.compile())

    # Use or do not use the optional word 'there'
    print_matching(grammar, "hey")
    print_matching(grammar, "hey there")


if __name__ == '__main__':
    main()
