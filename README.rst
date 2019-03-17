pyjsgf
======

|Build Status|
|Docs Status|

JSpeech Grammar Format (JSGF) compiler, matcher and parser package for
Python.

JSGF is a format used to textually represent grammars for speech
recognition engines. You can read the JSGF specification
`here <https://www.w3.org/TR/jsgf/>`__.

pyjsgf can be used to construct JSGF rules and grammars, compile them
into strings or files, and find grammar rules that match speech
hypothesis strings. Matching speech strings to tags is also supported.
There are also parsers for grammars, rules and rule expansions.

pyjsgf has been written and tested for Python 2.7 and Python 3.5.

The documentation for this project is `on
readthedocs.org <https://pyjsgf.readthedocs.io/>`__.

Installation
------------
To install pyjsgf, run the following::

  $ pip install pyjsgf

If you are installing in order to *develop* pyjsgf, clone/download the repository, move to the root directory and run::

  $ pip install -e .


Usage Example
-------------

The following is a usage example for how to create a JSGF grammar with
one rule, compile it and find matching rules given the speech string
"hello world":

.. code:: python

    from jsgf import PublicRule, Literal, Grammar

    # Create a public rule with the name 'hello' and a Literal expansion 'hello world'.
    rule = PublicRule("hello", Literal("hello world"))

    # Create a grammar and add the new rule to it.
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

Running the above code would output:

::

    #JSGF V1.0;
    grammar default;
    public <hello> = hello world;

    Matching: PublicRule(name='hello', expansion=Literal('hello world'))


The first line of the grammar can be changed using the ``jsgf_version``,
``charset_name``, and ``language_name`` members of the ``Grammar``
class.

There are some usage examples in `pyjsgf/examples <https://github.com/Danesprite/pyjsgf/tree/master/examples>`_ which may help you get started.

Multilingual support
--------------------

Due to Python's Unicode support, pyjsgf can be used with Unicode
characters for grammar, import and rule names, as well as rule literals.
If you need this, it is better to use Python 3 or above where all
strings are Unicode strings by default.

If you must use Python 2.x, you'll need to define Unicode strings as
either ``u"text"`` or ``unicode(text, encoding)``, which is a little
cumbersome. If you want to define Unicode strings in a source code file,
you'll need to define the `source code file
encoding <https://www.python.org/dev/peps/pep-0263/>`__.

.. |Build Status| image:: https://travis-ci.org/Danesprite/pyjsgf.svg?branch=master
   :target: https://travis-ci.org/Danesprite/pyjsgf
.. |Docs Status| image:: https://readthedocs.org/projects/pyjsgf/badge/?version=latest&style=flat
   :target: https://pyjsgf.readthedocs.io
