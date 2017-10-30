# JSGF Extensions
This package contains extensions to JSGF that aren't part of the JSGF specification.

## Use grammars in conjunction with language models
JSGF can't be used to build speech grammars where speech from a language model can be used in conjunction with grammar rules.
For example, the speech hypothesis from a speech decoder, such as CMU Pocket Sphinx, can be used in conjunction with JSGF grammars in sequence as below:

``` Python
PublicRule("greet", Sequence(Literal("hello"), Dictation()))

```

which translates to:

`public <greet> = hello { dictation };`


*hello* will be recognised by a speech decoder with the grammar loaded, then another decoder can be used to recognise speech from a language model and give the hypothesis. We can use 'world' as an example:
Speech: hello <utterance break> world
