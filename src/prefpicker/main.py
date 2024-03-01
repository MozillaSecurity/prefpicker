# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""prefpicker module main"""

from argparse import ArgumentParser, Namespace
from logging import DEBUG, INFO, basicConfig, getLogger
from os import getenv
from pathlib import Path
from typing import List, Optional

from .prefpicker import PrefPicker, SourceDataError, __version__

__author__ = "Tyson Smith"
__credits__ = ["Tyson Smith"]

LOG = getLogger(__name__)


def parse_args(argv: Optional[List[str]] = None) -> Namespace:
    """Handle argument parsing.

    Args:
        argv: Arguments from the user.

    Returns:
        Parsed and sanitized arguments.
    """
    parser = ArgumentParser(
        description="Manage & generate prefs.js files",
        prog="prefpicker",
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Template containing definitions. This can be the path to a template"
        " (YAML) file or the name of a built-in template. Built-in templates:"
        f" {', '.join(x.name for x in PrefPicker.templates())}",
    )
    parser.add_argument("output", type=Path, help="Path of prefs.js file to create.")
    parser.add_argument(
        "--check", action="store_true", help="Display output of sanity checks."
    )
    parser.add_argument("--variant", default="default", help="Specify variant to use.")
    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show version number.",
    )
    args = parser.parse_args(argv)
    # handle using built-in templates
    builtin_template = PrefPicker.lookup_template(args.input.name)
    if builtin_template:
        args.input = builtin_template
    elif not args.input.is_file():
        parser.error(f"Cannot find input file '{args.input}'")
    # sanity check output
    if args.output.is_dir():
        parser.error(f"Output '{args.output}' is a directory.")
    if not args.output.parent.is_dir():
        parser.error(f"Output '{args.output.parent}' directory does not exist.")
    return args


def main(argv: Optional[List[str]] = None) -> int:
    """
    PrefPicker main entry point

    Run with --help for usage
    """
    if bool(getenv("DEBUG")):  # pragma: no cover
        log_fmt = "%(asctime)s %(levelname).1s %(name)s | %(message)s"
        log_level = DEBUG
    else:
        log_fmt = "%(message)s"
        log_level = INFO
    basicConfig(format=log_fmt, level=log_level)

    args = parse_args(argv)

    LOG.info("Loading %r...", args.input.name)
    try:
        pick = PrefPicker.load_template(args.input)
    except SourceDataError as exc:
        LOG.error("Failed to load '%s': %s", args.input, exc)
        return 1
    LOG.info("Loaded %d prefs and %d variants", len(pick.prefs), len(pick.variants))
    if args.check:
        for combos in pick.check_combinations():
            LOG.info(
                "Check: %r variant has %r possible combination(s)", combos[0], combos[1]
            )
        for overwrites in pick.check_overwrites():
            LOG.info(
                "Check: %r variant %r redefines value %r (may be intentional)",
                overwrites[0],
                overwrites[1],
                overwrites[2],
            )
        for dupes in pick.check_duplicates():
            LOG.info(
                "Check: %r variant %r contains duplicate values", dupes[0], dupes[1]
            )
    if args.variant not in pick.variants:
        LOG.error("Error: Variant %r does not exist", args.variant)
        return 1
    LOG.info("Generating %r using variant %r...", args.output.name, args.variant)
    pick.create_prefsjs(args.output, args.variant)
    LOG.info("Done.")
    return 0
