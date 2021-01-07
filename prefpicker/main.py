# coding=utf-8
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""prefpicker module main"""

import argparse
import logging
import os

from .prefpicker import PrefPicker, SourceDataError

__author__ = "Tyson Smith"
__credits__ = ["Tyson Smith"]

LOG = logging.getLogger(__name__)


def parse_args(argv=None):
    templates = (os.path.basename(x) for x in PrefPicker.templates())
    parser = argparse.ArgumentParser(description="PrefPicker - Manage & generate prefs.js files")
    parser.add_argument(
        "input",
        help="Template containing definitions. This can be the path "
             "to a template (YAML) file or the name of a built-in template. "
             "Built-in templates: %s" % (", ".join(templates),))
    parser.add_argument(
        "output",
        help="Path of prefs.js file to create.")
    parser.add_argument(
        "--check", action="store_true",
        help="Display output of sanity checks.")
    parser.add_argument(
        "--variant", default="default",
        help="Specify variant to use.")
    args = parser.parse_args(argv)
    # handle using built-in templates
    if not os.path.isfile(args.input):
        tpath = os.path.abspath(os.path.join(os.path.dirname(__file__), "templates"))
        builtin = os.path.join(tpath, args.input)
        if os.path.isfile(builtin):
            args.input = builtin
    # sanity check input
    if not os.path.isfile(args.input):
        parser.error("Cannot find input file %r" % (args.input,))
    # sanity check output
    if os.path.isdir(args.output):
        parser.error("Output %r is a directory." % (args.output,))
    out_dir = os.path.abspath(os.path.dirname(args.output))
    if not os.path.isdir(out_dir):
        parser.error("Output %r directory does not exist." % (out_dir,))
    return args


def main(argv=None):  # pylint: disable=missing-docstring
    if bool(os.getenv("DEBUG")):  # pragma: no cover
        log_fmt = "%(asctime)s %(levelname).1s %(name)s | %(message)s"
        log_level = logging.DEBUG
    else:
        log_fmt = "%(message)s"
        log_level = logging.INFO
    logging.basicConfig(format=log_fmt, level=log_level)

    args = parse_args(argv)

    LOG.info("Loading %r...", os.path.basename(args.input))
    try:
        pick = PrefPicker.load_template(args.input)
    except SourceDataError as exc:
        LOG.error("Failed to load %r: %s", args.input, str(exc))
        return 1
    LOG.info("Loaded %d prefs and %d variants", len(pick.prefs), len(pick.variants))
    if args.check:
        for result in pick.check_combinations():
            LOG.info("Check: %r variant has %r possible combination(s)", result[0], result[1])
        for result in pick.check_overwrites():
            LOG.info("Check: %r variant %r redefines value %r (may be intentional)",
                     result[0], result[1], result[2])
        for result in pick.check_duplicates():
            LOG.info("Check: %r variant %r contains duplicate values", result[0], result[1])
    if args.variant not in pick.variants:
        LOG.error("Error: Variant %r does not exist", args.variant)
        return 1
    LOG.info("Generating %r using variant %r...", os.path.basename(args.output), args.variant)
    pick.create_prefsjs(args.output, args.variant)
    LOG.info("Done.")
    return 0
