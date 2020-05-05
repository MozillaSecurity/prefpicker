# coding=utf-8
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from datetime import datetime
from hashlib import sha1
from os import listdir
from os.path import abspath, dirname, isdir, join as pathjoin
from random import choice

from yaml import safe_load


__author__ = "Tyson Smith"
__credits__ = ["Tyson Smith"]


class SourceDataError(Exception):
    """This is raised when issues are found in the source data."""


class PrefPicker(object):

    __slots__ = ("prefs", "variants")

    def __init__(self):
        self.prefs = dict()
        self.variants = set(["default"])

    def check_combinations(self):
        """Count the number of combinations for each variation. Only return
           variants that have more than one combination.

        Args:
            None

        Yields:
            tuple: variant and number of potential combinations
        """
        combos = dict.fromkeys(self.variants, 1)
        for variants in self.prefs.values():
            for variant in combos:
                # use 'default' if pref does not have a matching variant entry
                if variant not in variants:
                    combos[variant] *= len(variants["default"])
                else:
                    combos[variant] *= len(variants[variant])
        for variant, count in sorted(combos.items()):
            if count > 1:
                yield (variant, count)

    def check_duplicates(self):
        """Look for variants with values that appear more than once per variant.

        Args:
            None

        Yields:
            tuple: pref and the variant
        """
        for pref, variants in sorted(self.prefs.items()):
            for variant in variants:
                if len(variants[variant]) != len(set(variants[variant])):
                    yield (pref, variant)

    def check_overwrites(self):
        """Look for variants that overwrite the default with the same value.

        Args:
            None

        Yields:
            tuple: pref, variant and the value
        """
        for pref, variants in sorted(self.prefs.items()):
            for variant in variants:
                if variant == "default":
                    continue
                for value in variants[variant]:
                    if value in variants["default"]:
                        yield (pref, variant, value)

    def create_prefsjs(self, dest, variant="default"):
        """Write a `prefs.js` file based on the specified variant. The output file
           will also include comments containing the variant, a timestamp and a
           fingerprint. The fingerprint is a hash of pref/value pairs which can
           be used to help catch different files without a diff.

        Args:
            dest (str): Name including path of file to create.
            variant (str): Used to pick the values to output.

        Returns:
            None
        """
        # create a fingerprint based on prefs/values combinations
        uid = sha1()
        with open(dest, "w") as prefs_fp:
            prefs_fp.write("// Generated with PrefPicker @ ")
            prefs_fp.write(datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"))
            prefs_fp.write("\n// Variant %r\n" % (variant,))
            for pref, variants in sorted(self.prefs.items()):
                # choose values
                if variant not in variants or variant == "default":
                    value = choice(variants["default"])
                    default_variant = True
                else:
                    value = choice(variants[variant])
                    default_variant = False
                if value is None:
                    # skipping pref
                    continue
                # sanitize value for writing
                if isinstance(value, bool):
                    sanitized = "true" if value else "false"
                elif isinstance(value, int):
                    sanitized = str(value)
                elif isinstance(value, str):
                    sanitized = repr(value)
                else:
                    prefs_fp.write("// Error sanitizing pref %r value %r\n" % (pref, value))
                    raise SourceDataError("Unknown datatype %r" % (type(value),))
                # write to prefs.js file
                if not default_variant:
                    prefs_fp.write("// %r defined by variant %r\n" % (pref, variant))
                prefs_fp.write("user_pref(\"%s\", %s);\n" % (pref, sanitized))
                # update fingerprint
                uid.update(pref.encode(encoding="utf-8", errors="ignore"))
                uid.update(sanitized.encode(encoding="utf-8", errors="ignore"))
            prefs_fp.write("// Fingerprint %r\n" % (uid.hexdigest(),))

    @classmethod
    def load_template(cls, input_yml):
        """Load data from a template YAML file.

        Args:
            input_yml (str): Path to input file.

        Returns:
            PrefPicker
        """
        with open(input_yml, "r") as in_fp:
            raw_prefs = safe_load(in_fp.read())
        cls.verify_data(raw_prefs)
        picker = cls()
        picker.variants = set(raw_prefs["variant"] + ["default"])
        picker.prefs = raw_prefs["pref"]
        return picker

    @staticmethod
    def templates():
        """Available YAML template files.

        Args:
            None

        Yields:
            str: Filename including path to each template file.
        """
        path = abspath(pathjoin(dirname(__file__), "templates"))
        if isdir(path):
            for template in listdir(path):
                if template.lower().endswith(".yml"):
                    yield pathjoin(path, template)

    @staticmethod
    def verify_data(raw_data):
        """Perform strict sanity checks on raw_data. This exists to help prevent
           the template file from breaking or becoming unmaintainable.

        Args:
            raw_data (dict): Data to verify.

        Returns:
            None
        """
        if "variant" not in raw_data:
            raise SourceDataError("variant list is missing")
        if not isinstance(raw_data["variant"], list):
            raise SourceDataError("variant is not a list")
        valid_variants = set(["default"])
        for variant in raw_data["variant"]:
            if not isinstance(variant, str):
                raise SourceDataError("variant definition must be a string")
            valid_variants.add(variant)
        if "pref" not in raw_data:
            raise SourceDataError("pref group is missing")
        if not isinstance(raw_data["pref"], dict):
            raise SourceDataError("pref is not a dict")
        used_variants = set()
        for pref, variants in raw_data["pref"].items():
            if not variants or "default" not in variants:
                raise SourceDataError("%r is missing 'default' variant" % (pref,))
            for variant in variants:
                if variant not in valid_variants:
                    raise SourceDataError("%r in %r is not a defined variant" % (variant, pref))
                if not isinstance(variants[variant], list):
                    raise SourceDataError("variant %r in %r is not a list" % (variant, pref))
                if not variants[variant]:
                    raise SourceDataError("%r in %r is empty" % (variant, pref))
                used_variants.add(variant)
        if valid_variants - used_variants:
            raise SourceDataError("Unused variants %r" % (" ".join(valid_variants - used_variants),))
