# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""prefpicker module"""

from datetime import datetime
from hashlib import sha1
from os import listdir
from os.path import abspath, dirname, isdir
from os.path import join as pathjoin
from random import choice

from yaml import safe_load
from yaml.parser import ParserError
from yaml.scanner import ScannerError

__author__ = "Tyson Smith"
__credits__ = ["Tyson Smith"]


class SourceDataError(Exception):
    """This is raised when issues are found in the source data."""


class PrefPicker:  # pylint: disable=missing-docstring

    __slots__ = ("prefs", "variants")

    def __init__(self):
        self.prefs = dict()
        self.variants = {"default"}

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
            prefs_fp.write(f"\n// Variant {variant!r}\n")
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
                    prefs_fp.write(f"// Failed to sanitized {value!r} ({pref})\n")
                    raise SourceDataError(
                        f"Unsupported datatype {type(value).__name__!r}"
                    )
                # write to prefs.js file
                if not default_variant:
                    prefs_fp.write(f"// {pref!r} defined by variant {variant!r}\n")
                prefs_fp.write(f'user_pref("{pref}", {sanitized});\n')
                # update fingerprint
                uid.update(pref.encode(encoding="utf-8", errors="ignore"))
                uid.update(sanitized.encode(encoding="utf-8", errors="ignore"))
            prefs_fp.write(f"// Fingerprint {uid.hexdigest()!r}\n")

    @classmethod
    def load_template(cls, input_yml):
        """Load data from a template YAML file.

        Args:
            input_yml (str): Path to input file.

        Returns:
            PrefPicker
        """
        try:
            with open(input_yml) as in_fp:
                raw_prefs = safe_load(in_fp.read())
        except (ScannerError, ParserError):
            raise SourceDataError("invalid YAML") from None
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
        valid_variants = {"default"}
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
                raise SourceDataError(f"{pref!r} is missing 'default' variant")
            for variant in variants:
                if variant not in valid_variants:
                    raise SourceDataError(
                        f"{variant!r} in {pref!r} is not a defined variant"
                    )
                if not isinstance(variants[variant], list):
                    raise SourceDataError(
                        f"variant {variant!r} in {pref!r} is not a list"
                    )
                if not variants[variant]:
                    raise SourceDataError(f"{variant!r} in {pref!r} is empty")
                for value in variants[variant]:
                    if value is not None and not isinstance(value, (bool, int, str)):
                        raise SourceDataError(
                            "unsupported datatype %r (%s)"
                            % (type(value).__name__, pref)
                        )
                used_variants.add(variant)
        if valid_variants - used_variants:
            raise SourceDataError(
                f"Unused variants {' '.join(valid_variants - used_variants)!r}"
            )
