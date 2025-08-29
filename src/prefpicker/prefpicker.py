# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""prefpicker module"""

from __future__ import annotations

from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from json import dumps
from pathlib import Path
from random import choice
from typing import TYPE_CHECKING, Any, Union

from yaml import safe_load
from yaml.parser import ParserError
from yaml.scanner import ScannerError

if TYPE_CHECKING:
    from collections.abc import Generator

__author__ = "Tyson Smith"
__credits__ = ["Tyson Smith"]
try:
    __version__ = version("prefpicker")
except PackageNotFoundError:  # pragma: no cover
    # package is not installed
    __version__ = "unknown"


class SourceDataError(Exception):
    """This is raised when issues are found in the source data."""


# Python <= 3.9 requires the use of Union
PrefValue = Union[bool, int, str, None]
PrefVariant = dict[str, list[PrefValue]]


class PrefPicker:
    """Manage prefs and generate prefs.js files for use with Firefox.

    Attributes:
        prefs: Contains pref names and values group by variant.
        variants: Use to group sets of pref values.
    """

    __slots__ = ("prefs", "variants")

    def __init__(self) -> None:
        self.prefs: dict[str, dict[str, PrefVariant]] = {}
        self.variants: dict[str, str] = {}

    def check_duplicates(self) -> Generator[tuple[str, str]]:
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

    def check_overwrites(self) -> Generator[tuple[str, str, PrefValue]]:
        """Look for variants that overwrite the parent with the same value.

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
                parent = self.variants[variant]
                for value in variants[variant]:
                    if value in variants[parent]:
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
            prefs_fp.write(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z"))
            prefs_fp.write(f"\n// Variant '{variant}'\n")
            for pref, keys in sorted(self.prefs.items()):
                pref_variants = keys["variants"]
                # choose values
                current_variant = variant
                while True:
                    if current_variant in pref_variants:
                        options = pref_variants[current_variant]
                        break
                    # no variant defined values, check parent
                    current_variant = self.variants[current_variant]

                value = choice(options)
                if value is None:
                    if len(options) > 1:
                        prefs_fp.write(
                            f"// '{pref}' skipped, options {dumps(options)}\n"
                        )
                    # skipping pref
                    continue
                if len(options) > 1:
                    prefs_fp.write(f"// '{pref}' options {dumps(options)}\n")
                # sanitize value for writing
                if isinstance(value, bool):
                    sanitized = "true" if value else "false"
                elif isinstance(value, int):
                    sanitized = str(value)
                elif isinstance(value, str):
                    sanitized = f"'{value}'"
                else:
                    prefs_fp.write(f"// Failed to sanitized {value!r} ({pref})\n")
                    raise SourceDataError(
                        f"Unsupported datatype {type(value).__name__!r}"
                    )
                # write to prefs.js file
                if current_variant != "default":
                    prefs_fp.write(f"// '{pref}' defined by variant '{variant}'\n")
                prefs_fp.write(f'user_pref("{pref}", {sanitized});\n')

    @classmethod
    def lookup_template(cls, name: str) -> Path | None:
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
    def load_template(cls, input_yml: Path) -> PrefPicker:
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
        picker.variants.update(raw_prefs["variant"])
        # only add relevant parts
        for pref, parts in raw_prefs["pref"].items():
            picker.prefs[pref] = {"variants": parts["variants"]}
        return picker

    @staticmethod
    def templates() -> Generator[Path]:
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
        # check variant dict
        if "variant" not in raw_data:
            raise SourceDataError("variant dict is missing")
        if not isinstance(raw_data["variant"], dict):
            raise SourceDataError("variant must be a dict")
        # check variant entries
        valid_variants = {"default"}
        for variant, parent in raw_data["variant"].items():
            if not isinstance(variant, str):
                raise SourceDataError("variant name must be a string")
            if not variant:
                raise SourceDataError("variant name is empty")
            valid_variants.add(variant)
            if not isinstance(parent, str):
                raise SourceDataError("variant parent name must be a string")
        # check variant parents
        for variant in valid_variants:
            parent = raw_data["variant"].get(variant, "default")
            while parent != "default":
                if parent == variant:
                    raise SourceDataError("variant cannot be parent of itself")
                if parent not in valid_variants:
                    raise SourceDataError(
                        f"variant parent '{parent}' is an undefined variant"
                    )
                parent = raw_data["variant"][parent]
        # check prefs dict
        if "pref" not in raw_data:
            raise SourceDataError("pref dict is missing")
        if not isinstance(raw_data["pref"], dict):
            raise SourceDataError("pref must be a dict")
        # check entries in prefs dict
        used_variants: set[str] = set()
        for pref, keys in raw_data["pref"].items():
            if not isinstance(keys, dict):
                raise SourceDataError(f"{pref!r} entry must contain a dict")
            variants = keys.get("variants")
            if not isinstance(variants, dict):
                raise SourceDataError(f"{pref!r} is missing 'variants' dict")
            if "default" not in variants:
                raise SourceDataError(f"{pref!r} is missing 'default' variant")
            # verify pref specific variants
            for variant in variants:
                if not isinstance(variant, str):
                    raise SourceDataError(f"{pref!r} variants must be strings")
                if variant not in valid_variants:
                    raise SourceDataError(
                        f"{variant!r} in {pref!r} is an undefined variant"
                    )
                if not isinstance(variants[variant], list):
                    raise SourceDataError(
                        f"variant {variant!r} in {pref!r} must be a list"
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
