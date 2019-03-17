# JSGF Extensions
This package contains extensions to JSGF that aren't part of the JSGF specification.

## Use grammars in conjunction with language models
Standard JSGF can't be used to build or match grammar rules where arbitrary speech from a language model is used in conjunction with JSGF expansions. Most of the `jsgf.ext` package focuses on providing this functionality.

Below is an example of how to use the `DictationGrammar` and `Dictation` classes to that effect:

``` Python
from jsgf import PublicRule, Sequence
from jsgf.ext import Dictation, DictationGrammar

# Create a simple rule using a Dictation expansion.
rule = PublicRule("Hello_X", Sequence("hello", Dictation()))

# Create a new DictationGrammar using the simple rule.
grammar = DictationGrammar([rule])

# Print the compiled grammar
print(grammar.compile())

# Match against some speech strings.
# find_matching_rules has an optional second parameter for advancing to
# the next part of the rule, which is set to False here.
matching = grammar.find_matching_rules("hello", False)
print("Matching rule: %s" % matching[0])  # first part of rule

# Go to the next part of the rule.
matching[0].set_next()

# Match the dictation part. This can be anything.
matching = grammar.find_matching_rules("world")
print("Matching rule: %s" % matching[0])

# The entire match and the original rule's current_match value will both be
'hello world'
print(matching[0].entire_match)
print(rule.expansion.current_match)

```

The output from the above will be:
```
#JSGF V1.0;
grammar default;
public <Hello_X> = hello;

Matching rule: SequenceRule(Sequence(Literal('hello')))
Matching rule: SequenceRule(Sequence(Dictation()))
hello world
hello world

```
