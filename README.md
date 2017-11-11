# pyjsgf
JSpeech Grammar Format (JSGF) compiler and matcher for Python.

JSGF is a format used to textually represent grammars for speech recognition engines. You can read the JSGF specification [here](https://www.w3.org/TR/jsgf/).

This Python package can be used to construct JSGF rules and grammars, compile them into strings or files, and find rules in grammars that match given speech text. Speech text can be strings received from a recognition engine's speech hypothesis, for example.

## Usage Example
The following is a usage example for how to create a JSGF grammar with one rule, compile it and find matching rules given the speech string "hello world":
``` Python
from jsgf import PublicRule, Literal, Grammar

# Create a public rule with the name 'hello' and a Literal expansion 'hello world'.
rule = PublicRule("hello", Literal("hello world"))

# Create a grammar and add the new rule to it.
grammar = Grammar()
grammar.add_rule(rule)

# Compile the grammar using compile_grammar()
# compile_to_file(file_path) may be used to write a compiled grammar to
# a file instead.
# Compilation is not required for finding matching rules.
print(grammar.compile_grammar())

# Find rules in the grammar that match 'hello world'.
matching = grammar.find_matching_rules("hello world")
print("Matching: %s" % matching[0])


```

Running the above code would output:
```
#JSGF V1.0 UTF-8 en;
grammar default;
public <hello> = hello world;

Matching: PublicRule(Literal('hello world'))

```

The first line of the grammar can be changed using the `jsgf_version`, `charset_name`, and `language_name` parameters of the `compile_grammar` and `compile_to_file` methods of the `Grammar` class.

There are more examples on ways to use this package [here](examples/).


# Python version
This package has been written for Python 2.7 and does not yet work with Python 3+.
