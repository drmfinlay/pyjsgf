from jsgf import PublicRule, Literal, Grammar


def main():
    # Create a public rule with the name 'hello' and a Literal expansion
    # 'hello world'.
    rule = PublicRule("hello", Literal("hello world"))

    # Note that the following creates the same rule:
    rule = PublicRule("hello", "hello world")

    # Create a grammar and add the new rule to it
    grammar = Grammar("g")
    grammar.add_rule(rule)

    # Compile the grammar using compile_grammar()
    print("Grammar '%s' compiles to:" % grammar.name)
    print(grammar.compile_grammar())

    # Find rules in the grammar that match 'hello world'
    speech = "hello world"
    matching = grammar.find_matching_rules(speech)
    print("The following rules matched '%s':" % speech)
    for match in matching:
        print(match)

if __name__ == '__main__':
    main()
