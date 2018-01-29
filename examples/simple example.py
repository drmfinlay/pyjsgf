from jsgf import PublicRule, Literal, Grammar


def main():
    # Create a public rule with the name 'hello' and a Literal expansion
    # 'hello world'.
    rule = PublicRule("hello", Literal("hello world"))

    # Note that the following creates the same rule:
    rule = PublicRule("hello", "hello world")

    # Create a grammar and add the new rule to it
    grammar = Grammar()
    grammar.add_rule(rule)

    # Compile the grammar using compile()
    # compile_to_file(file_path) may be used to write a compiled grammar to
    # a file instead.
    # Compilation is not required for finding matching rules.
    print(grammar.compile())

    # Find rules in the grammar that match 'hello world'.
    matching = grammar.find_matching_rules("hello world")
    print("Matching: %s" % matching[0])


if __name__ == '__main__':
    main()
