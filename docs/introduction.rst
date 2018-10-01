.. _intro:

============
Introduction
============

.. toctree::
   :maxdepth: 2

pyjsgf can be used to construct JSGF rules and grammars, compile them into strings or files, and find grammar rules that match speech hypothesis strings. Matching speech strings to tags is also supported. There are also parsers for grammars, rules and rule expansions.

There are some usage examples in `pyjsgf/examples <https://github.com/Danesprite/pyjsgf/tree/master/examples>`_ which may help you get started.

Installation
------------
To install pyjsgf, run the following::

  $ pip install pyjsgf

If you are installing in order to *develop* pyjsgf, clone/download the repository, move to the root directory and run::

  $ pip install -e .


Supported Python Versions
-------------------------
pyjsgf has been written and tested for Python 2.7 and 3.5.

Please file an issue if you notice a problem specific to the version of Python you are using.


Unit Testing
------------
There are extensive unit tests in `pyjsgf/test <https://github.com/Danesprite/pyjsgf/tree/master/test>`_. There is also a Travis CI project `here <https://travis-ci.org/Danesprite/pyjsgf>`_. The test coverage is not 100%, but most classes, methods and functions are covered pretty well.


Multilingual Support
--------------------
Due to Python's Unicode support, pyjsgf can be used with Unicode characters for grammar, import and rule names, as well as rule literals. If you need this, it is better to use Python 3 or above where all strings are Unicode strings by default.

If you must use Python 2.x, you'll need to define Unicode strings as either ``u"text"`` or ``unicode(text, encoding)``, which is a little cumbersome. If you want to define Unicode strings in a source code file, you'll need to define the `source code file encoding <https://www.python.org/dev/peps/pep-0263/>`_.


Documentation
-------------
The documentation for this project is written in `reStructuredText <http://docutils.sourceforge.net/rst.html>`_ and built using `Sphinx <http://www.sphinx-doc.org/en/stable>`_. Run the following to build it locally::

  $ cd docs
  $ make html
 
