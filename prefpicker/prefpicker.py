# coding=utf-8
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import hashlib
import random

import yaml


__author__ = "Tyson Smith"
__credits__ = ["Tyson Smith"]


class SourceDataError(Exception):
    """This is raised when issues are found in the source data."""


class PrefPicker(object):

    def __init__(self):
        self.prefs = dict()
        self.variants = set(["default"])

    def create_prefsjs(self, dest, variant="default"):
        # create a fingerprint based on prefs/values combinations
        uid = hashlib.sha1()
        with open(dest, "w") as prefs_fp:
            prefs_fp.write("// Generated with PrefPicker @ ")
            prefs_fp.write(datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"))
            prefs_fp.write("\n// Variant %r\n" % (variant,))
            for pref, variants in sorted(self.prefs.items()):
                if variant not in variants or variant == "default":
                    value = random.choice(variants["default"])
                    default_variant = True
                else:
                    value = random.choice(variants[variant])
                    default_variant = False
                if value is None:
                    # skipping pref
                    continue
                if not default_variant:
                    prefs_fp.write("// %r defined by variant %r\n" % (pref, variant))
                # write pref to prefs.js file
                prefs_fp.write("user_pref(\"%s\", " % (pref,))
                # handle writing different datatypes to th prefs.js
                if isinstance(value, bool):
                    sanitized = "true" if value else "false"
                elif isinstance(value, int):
                    sanitized = str(value)
                elif isinstance(value, str):
                    sanitized = repr(value)
                else:
                    raise SourceDataError("Unknown datatype %r" % (type(value),))
                prefs_fp.write(sanitized)
                prefs_fp.write(");\n")
                uid.update(pref.encode(encoding="utf-8", errors="ignore"))
                uid.update(sanitized.encode(encoding="utf-8", errors="ignore"))
            prefs_fp.write("// Fingerprint %r\n" % (uid.hexdigest(),))

    def lint_duplicates(self):
        matches = list()
        for pref, variants in sorted(self.prefs.items()):
            for variant in variants:
                if len(variants[variant]) != len(set(variants[variant])):
                    matches.append((pref, variant))
        return matches

    def lint_overwrites(self):
        matches = list()
        for pref, variants in sorted(self.prefs.items()):
            for variant in variants:
                if variant == "default":
                    continue
                for value in variants[variant]:
                    if value in variants["default"]:
                        matches.append((pref, variant, value))
        return matches

    @classmethod
    def load_template(cls, input_yml):
        with open(input_yml, "r") as in_fp:
            raw_prefs = yaml.safe_load(in_fp.read())
        cls.verify_data(raw_prefs)
        picker = cls()
        picker.variants = set(raw_prefs["variant"] + ["default"])
        picker.prefs = raw_prefs["pref"]
        return picker

    @staticmethod
    def verify_data(raw_data):
        if "variant" not in raw_data:
            raise SourceDataError("variant list is missing")
        if not isinstance(raw_data["variant"], list):
            raise SourceDataError("variant is not a list")
        valid_variants = set(raw_data["variant"] + ["default"])
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
