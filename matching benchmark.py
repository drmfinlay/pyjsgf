#!/usr/bin/python
"""
Benchmarking script for pyjsgf's rule expansion matching.

This file makes use of the 'Rule.generate()' method to generate possible matching
strings. Run the script with '-h' or '--help' to see available arguments.

This script uses (roughly) the following grammar::

    #JSGF V1.0;
    grammar default;

    // A repetition of a word
    public <series> = (<words> [<n>])+;

    // Long, sorted list of words from a dictionary.
    <word> =  academy's | ackermanville | ... | wench | yonts;

    // Numbers 'one' to 'twenty'.
    <number> = one | two | ... | nineteen | twenty;


You can specify an alternative rule to benchmark with using the -r/--rule-string
arguments.

"""

import argparse
import time

from jsgf import (AlternativeSet, Repeat, Rule, Sequence, RuleRef, OptionalGrouping,
                  parse_rule_string)


# Random sample of words from the CMU US English dictionary.
WORDS = [
    "academy's", 'ackermanville', 'acri', 'adjudge', 'adventurer', "agencies'",
    'amarante', 'angelucci', 'annoys', 'anselma', 'armbrust', 'bacchus', 'basquez',
    'beakman', 'befuddled', 'bestows', 'body', 'bolshevik', 'bromides', 'bruso',
    'calcified', 'campuses', 'carrico', 'cavalcade', 'cespedes', 'charms',
    'chongqing', "chun's", 'clymene', 'conboy', 'contest', 'corrected', 'costley',
    'cou', 'craney', 'cris', "danju's", 'dehumidified', 'deitsch', 'dejong',
    'derouen', 'desiccated', 'discharges', 'discordant', 'doorn', 'droege',
    'dubray', "ducks'", 'dysert', 'edelson', 'elderkin', 'emblazoned', 'epilepsy',
    'esoteric', 'exaggerates', 'exceptionally', 'exclusively', 'flags', 'flann',
    'flatness', "flowers'", "folks'", 'fraley', 'frankenfood', 'freiman', 'fridley',
    'frugally', 'ftp', 'fundamentalists', 'fuquay', 'garraway', 'garrols', 'gator',
    'genet', 'gizzard', 'glazener', 'golfer', 'goodheart', 'gossard', 'goupil',
    'gratton', 'gunia', 'gutfeld', 'halper', "hanoi's", 'hardens', 'harsco',
    'henson', 'higgerson', 'hirings', 'hodges', 'hostage', 'impressively',
    'improves', 'inception', 'indri', 'inglett', "jeep's", 'jobbers', 'kari',
    'kassing', 'keasling', 'kelty', 'kingsbury', 'kirshner', 'kloss', 'koenigsberg',
    'kolber', 'lagan', 'larks', 'larosa', 'lato', 'latvia', 'lebsack', 'legere',
    'lemmen', 'luker', "mafia's", 'magnifying', 'malaysia', 'malino', "marriott's",
    'masser', 'mcgloin', 'mending', 'messieurs', 'moskolenko', 'moten', 'mourners',
    'mouthwash', "mulheren's", 'niedzielski', 'nondollar', 'ogled', 'ordeal',
    "otterson's", 'overlaid', 'parochialism', 'pazos', 'ponto', "primerica's",
    'promotion', "prosecutors'", 'pubco', 'pullin', 'purves', 'racy', 'reaffirm',
    'reclusive', 'reindel', 'retzlaff', 'rode', 'roederer', 'ronstadt', 'rudd',
    'rufford', 'ruminski', 'sabotaging', 'schriever', 'schwinn', 'serial',
    'shampine', "sharp's", 'shifrin', 'shorn', 'short-sighted', 'showers',
    'simard', 'snacking', 'solvents', 'sopko', 'southin', 'speaker', 'speck',
    'spew', 'stogsdill', 'studer', 'swapes', 'systemix', 'szalay', 'tegtmeyer',
    'terrific', 'teuscher', 'thorburn', 'timm', 'topper', 'treiber', 'truthfulness',
    'typifies', 'typology', 'uart', 'univar', 'veenstra', 'vigliotti', 'viscerally',
    'vogan', 'washbasin', 'wealth', 'wench', 'yonts'
]


# Optional numbers to make the grammar a little more complex.
NUMBERS = [
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
    "eighteen", "nineteen", "twenty"
]


def do_benchmark(rule, strings, args):
    # Match each speech string.
    quiet = args.quiet
    for speech in strings:
        rule.matches(speech)

        # Print (or don't print) speech strings.
        if not quiet:
            print("Generated string: %s" % speech)


def main():
    parser = argparse.ArgumentParser(
        prog="matching benchmark.py",
        description="pyjsgf matching benchmark"
    )
    parser.add_argument(
        "-r", "--rule-string", type=str, default="default",
        help=("Rule to use for benchmarking. "
              "Must be a valid JSGF rule ending with ';'.")
    )
    parser.add_argument(
        "-n", "--n-speech-strings", type=int, default=100, dest="n",
        help="Number of speech strings to generate."
    )
    parser.add_argument(
        "-q", "--quiet", default=False, action="store_true",
        help="Suppress output of generated strings.",
    )
    parser.add_argument(
        "-p", "--profile", default=False, action="store_true",
        help=("Whether to run the benchmark through 'cProfile'. If the module is "
              "not available, then 'profile' will be used instead."),
    )

    # Parse the arguments.
    args = parser.parse_args()

    # Set up rules for testing.
    if not args.rule_string or args.rule_string == 'default':
        word = Rule("word", False, AlternativeSet(*WORDS))
        number = Rule("number", False, AlternativeSet(*NUMBERS))
        rule = Rule("series", True, Repeat(Sequence(
            RuleRef(word), OptionalGrouping(RuleRef(number))
        )))
    else:
        rule = parse_rule_string(args.rule_string)

    # Generate N speech strings to test how well the matching performs.
    strings = []
    for _ in range(args.n):
        strings.append(rule.generate())

    if args.profile:
        try:
            # Try 'cProfile'.
            import cProfile as profile_mod
        except ImportError:
            # Fallback on 'profile' (slower) if it isn't available.
            import profile as profile_mod

        # Run the benchmark via the imported module, passing locals and globals.
        now = time.time()
        profile_mod.runctx("do_benchmark(rule, strings, args)", {}, {
            "do_benchmark": do_benchmark, "rule": rule, "strings": strings,
            "args": args
        })
    else:
        # Run the benchmark without profiling.
        now = time.time()
        do_benchmark(rule, strings, args)

    # Print the time it took to match N generated strings.
    after = time.time()
    print("Matched %d generated strings in %.3f seconds." %
          (args.n, after - now))


if __name__ == '__main__':
    main()
