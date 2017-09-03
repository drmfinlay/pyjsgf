# pyjsgf
JSpeech Grammar Format (JSGF) compiler and matcher for Python

JSGF is a format used to textually represent grammars for speech recognition engines. 
You can read the JSGF specification [here](https://www.w3.org/TR/jsgf/).

This Python package can be used to construct JSGF rules and grammars, compile them into 
strings or files, and match speech text to the matching rule objects used to compile 
the grammars. Speech text can be from a recognition engine's speech hypothesis, for 
example.
