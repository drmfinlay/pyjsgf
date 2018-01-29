from jsgf import Grammar, PublicRule, Sequence, AlternativeSet, HiddenRule, \
    RuleRef, OptionalGrouping


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
    # Create a grammar and add some rules to it
    grammar = Grammar()
    name = HiddenRule("name", AlternativeSet("john", "bob", "anna"))

    # greeting is either: 'hey', 'hey there' or 'hello'
    greeting = HiddenRule("greeting", AlternativeSet(
        Sequence("hey", OptionalGrouping("there")), "hello"))

    # parting_phrase is either: 'good bye' or 'see you'
    parting_phrase = HiddenRule("parting_phrase", AlternativeSet(
        "good bye", "see you"))

    # greet is a greeting followed by a name
    greet = PublicRule("greet", Sequence(RuleRef(greeting), RuleRef(name)))

    # goodbye is a parting phrase followed by a name
    goodbye = PublicRule("goodbye", Sequence(
        RuleRef(parting_phrase), RuleRef(name)))

    grammar.add_rules(name, greeting, parting_phrase, greet, goodbye)

    print("Grammar compiles to the following:")
    print(grammar.compile())

    # Try matching some speech strings
    print_matching(grammar, "hey john")
    print_matching(grammar, "hey there john")
    print_matching(grammar, "see you john")

    # Try matching some hidden rules
    print_matching(grammar, "bob")
    print_matching(grammar, "hey there")
    print_matching(grammar, "good bye")


if __name__ == '__main__':
    main()
