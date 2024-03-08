# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""prefpicker module"""

from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from random import choice
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple, Union

from yaml import safe_load
from yaml.parser import ParserError
from yaml.scanner import ScannerError

__author__ = "Tyson Smith"
__credits__ = ["Tyson Smith"]
try:
    __version__ = version("prefpicker")
except PackageNotFoundError:  # pragma: no cover
    # package is not installed
    __version__ = "unknown"


class SourceDataError(Exception):
    """This is raised when issues are found in the source data."""


PrefValue = Optional[Union[bool, int, str]]
PrefVariant = Dict[str, List[PrefValue]]


class PrefPicker:  # pylint: disable=missing-docstring
    __slots__ = ("prefs", "variants")

    def __init__(self) -> None:
        self.prefs: Dict[str, Dict[str, PrefVariant]] = {}
        self.variants: Set[str] = {"default"}

    def check_combinations(self) -> Iterator[Tuple[str, int]]:
        """Count the number of combinations for each variation. Only return
           variants that have more than one combination.

        Args:
            None

        Yields:
            Variant and number of potential combinations.
        """
        combos = dict.fromkeys(self.variants, 1)
        for variants in (x["variants"] for x in self.prefs.values()):
            for variant in combos:
                # use 'default' if pref does not have a matching variant entry
                if variant not in variants:
                    combos[variant] *= len(variants["default"])
                else:
                    combos[variant] *= len(variants[variant])
        for variant, count in sorted(combos.items()):
            if count > 1:
                yield (variant, count)

    def check_duplicates(self) -> Iterator[Tuple[str, str]]:
        """Look for variants with values that appear more than once per variant.

        Args:
            None

        Yields:
            Pref name and the variant.
        """
        for pref, keys in sorted(self.prefs.items()):
            variants = keys["variants"]
            for variant in variants:
                if len(variants[variant]) != len(set(variants[variant])):
                    yield (pref, variant)

    def check_overwrites(self) -> Iterator[Tuple[str, str, PrefValue]]:
        """Look for variants that overwrite the default with the same value.

        Args:
            None

        Yields:
            Pref, variant and value.
        """
        for pref, keys in sorted(self.prefs.items()):
            variants = keys["variants"]
            for variant in variants:
                if variant == "default":
                    continue
                for value in variants[variant]:
                    if value in variants["default"]:
                        yield (pref, variant, value)

    def create_prefsjs(self, dest: Path, variant: str = "default") -> None:
        """Write a `prefs.js` file based on the specified variant. The output file
           will also include comments containing the variant and a timestamp.

        Args:
            dest: Path of file to create.
            variant: Used to pick the values to output.

        Returns:
            None
        """
        with dest.open("w") as prefs_fp:
            prefs_fp.write(f"// Generated with PrefPicker ({__version__}) @ ")
            prefs_fp.write(datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"))
            prefs_fp.write(f"\n// Variant {variant!r}\n")
            for pref, keys in sorted(self.prefs.items()):
                variants = keys["variants"]
                # choose values
                if variant not in variants or variant == "default":
                    options = variants["default"]
                    default_variant = True
                else:
                    options = variants[variant]
                    default_variant = False
                value = choice(options)
                if value is None:
                    if len(options) > 1:
                        prefs_fp.write(f"// '{pref}' randomly skipped\n")
                    # skipping pref
                    continue
                if len(options) > 1:
                    prefs_fp.write(f"// '{pref}' available values {options}\n")
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

    @classmethod
    def lookup_template(cls, name: str) -> Optional[Path]:
        """Lookup built-in template Path.

        Args:
            name: Name of template.

        Returns:
            Template that matches 'name' or None.
        """
        path = Path(__file__).parent / "templates" / name
        if path.is_file():
            return path
        return None

    @classmethod
    def load_template(cls, input_yml: Path) -> "PrefPicker":
        """Load data from a template YAML file.

        Args:
            input_yml: Input file.

        Returns:
            PrefPicker object.
        """
        try:
            raw_prefs = safe_load(input_yml.read_bytes())
        except (ScannerError, ParserError):
            raise SourceDataError("invalid YAML") from None
        cls.verify_data(raw_prefs)
        picker = cls()
        picker.variants = set(raw_prefs["variant"] + ["default"])
        # only add relevant parts
        for pref, parts in raw_prefs["pref"].items():
            picker.prefs[pref] = {"variants": parts["variants"]}
        return picker

    @staticmethod
    def templates() -> Iterator[Path]:
        """Available YAML template files.

        Args:
            None

        Yields:
            Template files.
        """
        path = Path(__file__).parent.resolve() / "templates"
        if path.is_dir():
            for template in path.iterdir():
                if template.suffix.lower().endswith(".yml"):
                    yield template

    @staticmethod
    def verify_data(raw_data: Any) -> None:
        """Perform strict sanity checks on raw_data. This exists to help prevent
           the template file from breaking or becoming unmaintainable.

        Args:
            raw_data: Data to verify.

        Returns:
            None
        """
        if not isinstance(raw_data, dict):
            raise SourceDataError("invalid template")
        # check variant list
        if "variant" not in raw_data:
            raise SourceDataError("variant list is missing")
        if not isinstance(raw_data["variant"], list):
            raise SourceDataError("variant is not a list")
        # check variant list entries
        valid_variants = {"default"}
        for variant in raw_data["variant"]:
            if not isinstance(variant, str):
                raise SourceDataError("variant definition must be a string")
            valid_variants.add(variant)
        # check prefs dict
        if "pref" not in raw_data:
            raise SourceDataError("pref group is missing")
        if not isinstance(raw_data["pref"], dict):
            raise SourceDataError("pref is not a dict")
        # check entries in prefs dict
        used_variants = set()
        for pref, keys in raw_data["pref"].items():
            if not isinstance(keys, dict):
                raise SourceDataError(f"{pref!r} entry must contain a dict")
            variants = keys.get("variants")
            if not isinstance(variants, dict):
                raise SourceDataError(f"{pref!r} is missing 'variants' dict")
            if "default" not in variants:
                raise SourceDataError(f"{pref!r} is missing 'default' variant")
            # verify variants
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
                            f"unsupported datatype {type(value).__name__!r} ({pref})"
                        )
                used_variants.add(variant)
        if valid_variants - used_variants:
            raise SourceDataError(
                f"Unused variants {' '.join(valid_variants - used_variants)!r}"
            )
