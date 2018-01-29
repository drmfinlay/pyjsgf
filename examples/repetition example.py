from jsgf import PublicRule, Repeat, KleeneStar, Grammar, Sequence


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
    # The Repeat expansion requires one or more matches for its child expansion.
    # The KleeneStar requires zero or more matches. The Sequence expansion
    # requires all of its children expansions to be spoken in sequence.

    # Create a public rule using a Repeat expansion and another using the
    # KleeneStar expansion.
    rule1 = PublicRule("repeat", Sequence(Repeat("please"), "don't crash"))
    rule2 = PublicRule("kleene", Sequence(KleeneStar("please"), "don't crash"))

    # Create a grammar and add the new rules to it
    grammar = Grammar("g")
    grammar.add_rules(rule1, rule2)

    # Compile the grammar using compile()
    print("Grammar '%s' compiles to:" % grammar.name)
    print(grammar.compile())

    # Find rules in the grammar that match some speech strings
    print_matching(grammar, "don't crash")  # only kleene will match
    print_matching(grammar, "please don't crash")  # both will match
    print_matching(grammar, "please please don't crash")  # both again


if __name__ == '__main__':
    main()
