# coding=utf-8
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""prefpicker module main"""

import argparse
import logging
import os

from . import PrefPicker

__author__ = "Tyson Smith"
__credits__ = ["Tyson Smith"]

LOG = logging.getLogger("prefpicker")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="PrefPicker - Manage & generate prefs.js files")
    parser.add_argument(
        "input",
        help="YAML file containing definitions")
    parser.add_argument(
        "output",
        help="Name of prefs.js file to create")
    parser.add_argument(
        "--lint", action="store_true",
        help="Display lint results")
    parser.add_argument(
        "--variant", default="default",
        help="Specify variant to use")
    return parser.parse_args(argv)


def main(argv=None):  # pylint: disable=missing-docstring
    log_level = logging.INFO
    log_fmt = "%(message)s"
    if bool(os.getenv("DEBUG")):  # pragma: no cover
        log_level = logging.DEBUG
        log_fmt = "%(levelname).1s %(name)s [%(asctime)s] %(message)s"
    logging.basicConfig(format=log_fmt, datefmt="%Y-%m-%d %H:%M:%S", level=log_level)

    args = parse_args(argv)

    LOG.info("Loading %r...", os.path.basename(args.input))
    if not os.path.isfile(args.input):
        LOG.error("Error: Cannot find input YAML %r", args.input)
        return 1
    pick = PrefPicker.load_template(args.input)
    LOG.info("Loaded %d prefs and %d variants", len(pick.prefs), len(pick.variants))
    if args.lint:
        results = pick.lint_overwrites()
        for result in results:
            LOG.info("Lint: %r variant %r redefines value %r (may be intentional)",
                result[0], result[1], result[2])
        results = pick.lint_duplicates()
        for result in results:
            LOG.info("Lint: %r variant %r contains duplicate values", result[0], result[1])
    if args.variant not in pick.variants:
        LOG.error("Error: Variant %r does not exist", args.variant)
        return 1
    LOG.info("Generating %r using variant %r...", os.path.basename(args.output), args.variant)
    pick.create_prefsjs(args.output, args.variant)
    LOG.info("Done.")
    return 0
