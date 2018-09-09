Changelog
=========

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog`_, using the `reStructuredText format`_ instead of Markdown.

This project adheres to `Semantic Versioning`_ starting with version `1.1.1`_.


Unreleased_
-----------

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
.. _Unreleased: https://github.com/Danesprite/pyjsgf/compare/v1.4.1...HEAD
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

