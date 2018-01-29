from jsgf import PublicRule, HiddenRule, RuleRef, Grammar


def main():
    # Create a hidden (private) rule
    rule1 = HiddenRule("hello", "hello")

    # Create a public rule referencing rule1
    rule2 = PublicRule("greet", RuleRef(rule1))

    # Create a grammar and add the new rules to it
    grammar = Grammar("g")
    grammar.add_rules(rule1, rule2)

    # Compile the grammar using compile()
    print("Grammar '%s' compiles to:" % grammar.name)
    print(grammar.compile())

    # Find rules matching 'hello'
    # rule2 will be found, but not rule1 because it is hidden
    print("Matching rule: %s" % grammar.find_matching_rules("hello")[0])


if __name__ == '__main__':
    main()
