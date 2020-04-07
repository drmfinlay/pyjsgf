Changelog
=========

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog`_, using the `reStructuredText format`_ instead of Markdown.

This project adheres to `Semantic Versioning`_ starting with version `1.1.1`_.

1.9.0_ -- 2020-04-07
--------------------

Added
^^^^^
* Add JSGF import resolution.
* Add new Grammar methods for getting Rule objects by name.
* Add 'grammar_name', 'rule_name' and 'wildcard_import' Import class properties.
* Add 'qualified_name' and 'fully_qualified_name' Rule class properties.

Changed
^^^^^^^
* Add missing Grammar 'import_names' property.
* Add missing Grammar 'remove_imports()' method.
* Change Grammar class to silently reject duplicate Import objects.
* Rename HiddenRule rule classes to PrivateRule instead and leave in HiddenRule aliases.

Fixed
^^^^^
* Change Grammar.get_rule_from_name() method to validate the 'name' parameter.
* Change Grammar.remove_import() to only accept Import objects.
* Fix bug in Grammar.add_rule() that could cause RecursionErrors.


1.8.0_ -- 2020-01-31
--------------------

Added
^^^^^
* Add 'case_sensitive' properties to Literal, Rule & Grammar classes.

Changed
^^^^^^^
* Change ChildList into a list wrapper class instead of a sub-class.

Fixed
^^^^^
* Fix a pyparsing-related bug with the Repeat expansion class.
* Fix issues preventing serialization of expansions, rules and grammars.


1.7.1_ -- 2019-07-10
--------------------

Added
^^^^^
* Add 'matching benchmark.py' script.

Changed
^^^^^^^
* Add a classifier for Python 3.4 in setup.py as it is a supported version.
* Rewrite Expansion.repetition_ancestor property.
* Use the setuptools.find_packages() function in setup.py instead of defining packages manually.

Fixed
^^^^^
* Fix missing call to reset_for_new_match() in Rule.find_matching_part(). Some tests have also been added.


1.7.0_ -- 2019-06-19
--------------------

Added
^^^^^
* Add Expansion and Rule `generate()` methods for generating matching strings. Thanks `@embie27`_.
* Add unit tests for `generate()` methods into a new *test/test_generators.py* file. Thanks `@embie27`_.

Changed
^^^^^^^
* Include the `mock` package in *requirements.txt* (test requirement).

Fixed
^^^^^
* Fix two rule expansion parser bugs related to unary operators (`+` or `*`).
* Keep required groupings during parsing to avoid unexpected consequences. Thanks `@synesthesiam`_.


1.6.0_ -- 2019-03-17
--------------------

Added
^^^^^
* Add support for JSGF alternative weights to the AlternativeSet class and the rule expansion parser.
* Add 'Expansion.matching_slice' property for getting the slice of the last speech string that matched an Expansion.
* Add 'Repeat.get_expansion_slices' method for getting matching slices of repeated rule expansions.

Changed
^^^^^^^
* Change AlternativeSet 'weights' list to use a dictionary instead.
* Change grammar class and parser to allow for optional grammar header values.
* Change input and output of the 'save_current_matches' and 'restore_current_matches' expansion functions.
* Change jsgf.ext.Dictation expansions to compile as "<DICTATION>" instead of "".
* Simplify the parser code and improve its performance.
* Use '<NULL>' instead of '<VOID>' to compile expansions that should have children but don't.

Fixed
^^^^^
* Fix parser bug where sequences can lose tags. Thanks `@synesthesiam`_.
* Fix parser bug with sequences and alternative sets.

1.5.1_ -- 2018-10-28
--------------------

Added
^^^^^
* Add section in parser documentation with EBNF for the grammar parser.

Changed
^^^^^^^
* Change install instructions to use pip instead.

Fixed
^^^^^
* Fix a few problems with the README.
* Fix missing newlines from Grammar.compile_to_file(). Thanks `@daanzu`_.

1.5.0_ -- 2018-09-11
--------------------

Added
^^^^^
* Add Expansion.matcher_element property.
* Add Expansion.invalidate_matcher method.
* Add Rule.find_matching_part method. Thanks `@embie27`_.
* Add docstrings to undocumented classes and methods.
* Add Sphinx documentation project files in `docs/` and use autodoc for automatic module, class, class member and function documentation.
* Add `CHANGELOG.rst` file and include it in the documentation.

Changed
^^^^^^^
* Make speech string matching scale to large rules/grammars.
* Make jsgf.ext.Dictation expansions match correctly in most circumstances.
* Allow rules to use optional only rule expansions.
* Update docstrings in all Python modules.
* Change internal matching method to implement for subclasses from _matches_internal to _make_matcher_element.

Deprecated
^^^^^^^^^^
* Add deprecation note for the Grammar.compile_grammar method.
* Deprecate the ExpansionError and MatchError classes.

Fixed
^^^^^
* Fix `issue #12`_ and probably some other bugs where speech wouldn't match rules properly.
* Fix __hash__ methods for the Dictation and AlternativeSet classes.

Removed
^^^^^^^
* Remove support for matching ambiguous rule expansion because it is not worth the performance hit.


1.4.1_ -- 2018-08-20
--------------------

Added
^^^^^
* Add ChildList list subclass for storing rule expansion children and updating parent-child relationships appropriately on list operations.

Changed
^^^^^^^
* Change Literal.text attribute into a property with some validation.

Fixed
^^^^^
* Fix AlternativeSet bug with parser (`issue #9`_). Thanks `@embie27`_.


1.4.0_ -- 2018-08-09
--------------------

Added
^^^^^
* Implement grammar, rule and expansion parsers.
* Add setters for the BaseRef name property and Expansion children property.

Changed
^^^^^^^
* Allow imported rule names to be used by NamedRuleRefs.

Fixed
^^^^^
* Fix NamedRuleRefs for rule expansion functions and the Rule.dependencies property.


1.3.0_ -- 2018-07-14
--------------------

Added
^^^^^
* Add methods/properties to the Rule and Grammar classes for JSGF tag
  support.
* Add rule resolution for NamedRuleRef class.
* Add method and property for checking expansion match values for each repetition.

Fixed
^^^^^
* Fix various bugs with JSGF rule expansions.


1.2.3_ -- 2018-06-02
--------------------

Added
^^^^^
* Add 'six' as a required package to support Python versions 2.x and 3.x.

Changed
^^^^^^^
* Change add_rule methods of grammar classes to silently fail when adding rules that are already in grammars.

Fixed
^^^^^
* Fix hash implementations and __str__ methods for rule classes.
* Other minor fixes.

1.2.2_ -- 2018-04-28
--------------------

Added
^^^^^
* Add Expansion.collect_leaves method.

Changed
^^^^^^^
* Reset match data for unmatched branches of expansion trees.
* Change Expansion leaf properties to also return RuleRefs.
* Move some Literal class properties to the Expansion superclass.


1.2.1_ -- 2018-04-27
--------------------

Added
^^^^^
* Add calculation caching to improve matching performance.
* Add optional shallow parameter to Expansion functions like map_expansion.

Fixed
^^^^^
* Fix bug with BaseRef/RuleRef comparison.
* Fix bug in expand_dictation_expansion function.


1.2.0_ -- 2018-04-09
--------------------

Added
^^^^^
* Add a few methods and properties to Expansion classes.
* Add JointTreeContext class and find_expansion function.
* Add __rep__ methods to base classes for convenience.

Fixed
^^^^^
* Fix a bug where rules with mutiple RuleRefs wouldn't match.


1.1.1_ -- 2018-03-26
--------------------

First tagged release and start of proper versioning. Too many changes to list here, see the changes by following the link above.


.. Release links.
.. _Unreleased: https://github.com/Danesprite/pyjsgf/compare/v1.9.0...HEAD
.. _1.9.0: https://github.com/Danesprite/pyjsgf/compare/v1.8.0...v1.9.0
.. _1.8.0: https://github.com/Danesprite/pyjsgf/compare/v1.7.1...v1.8.0
.. _1.7.1: https://github.com/Danesprite/pyjsgf/compare/v1.7.0...v1.7.1
.. _1.7.0: https://github.com/Danesprite/pyjsgf/compare/v1.6.0...v1.7.0
.. _1.6.0: https://github.com/Danesprite/pyjsgf/compare/v1.5.1...v1.6.0
.. _1.5.1: https://github.com/Danesprite/pyjsgf/compare/v1.5.0...v1.5.1
.. _1.5.0: https://github.com/Danesprite/pyjsgf/compare/v1.4.1...v1.5.0
.. _1.4.1: https://github.com/Danesprite/pyjsgf/compare/v1.4.0...v1.4.1
.. _1.4.0: https://github.com/Danesprite/pyjsgf/compare/v1.3.0...v1.4.0
.. _1.3.0: https://github.com/Danesprite/pyjsgf/compare/v1.2.3...v1.3.0
.. _1.2.3: https://github.com/Danesprite/pyjsgf/compare/v1.2.2...v1.2.3
.. _1.2.2: https://github.com/Danesprite/pyjsgf/compare/v1.2.1...v1.2.2
.. _1.2.1: https://github.com/Danesprite/pyjsgf/compare/v1.2.0...v1.2.1
.. _1.2.0: https://github.com/Danesprite/pyjsgf/compare/v1.1.1...v1.2.0
.. _1.1.1: https://github.com/Danesprite/pyjsgf/compare/01153...v1.1.1

.. Other links.
.. _Keep a Changelog: https://keepachangelog.com/en/1.0.0/
.. _reStructuredText format: http://docutils.sourceforge.net/rst.html
.. _Semantic Versioning: https://semver.org/spec/v2.0.0.html
.. _issue #9: https://github.com/Danesprite/pyjsgf/issues/9
.. _issue #12: https://github.com/Danesprite/pyjsgf/issues/12
.. _@embie27: https://github.com/embie27
.. _@daanzu: https://github.com/daanzu
.. _@synesthesiam: https://github.com/synesthesiam
