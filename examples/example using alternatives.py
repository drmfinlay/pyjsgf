from jsgf import PublicRule, AlternativeSet, Grammar, Sequence


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
    # Create a new public rule using speech alternatives
    # Note that the Sequence expansion requires all of its children expansions
    # to be spoken in sequence
    rule = PublicRule("greet", Sequence(AlternativeSet("hello", "hey"), "there"))

    # Create a grammar and add the new rule to it
    grammar = Grammar("g")
    grammar.add_rule(rule)

    # Compile the grammar using compile()
    print("Grammar '%s' compiles to:" % grammar.name)
    print(grammar.compile())

    # Find rules in the grammar that match some speech strings
    print_matching(grammar, "hello there")
    print_matching(grammar, "hey there")

    # 'hello hey there' will not match because only one alternative in an
    # AlternativeSet expansion can be matched
    print_matching(grammar, "hello hey there")


if __name__ == '__main__':
    main()
