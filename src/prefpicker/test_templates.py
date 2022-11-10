# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
"""template.py tests"""

from difflib import unified_diff

from yaml import safe_dump, safe_load

from .main import main
from .prefpicker import PrefPicker


def test_templates_01(tmp_path):
    """sanity check template YAML files"""
    prefs_js = tmp_path / "prefs.js"
    checked = []
    for template in PrefPicker.templates():
        assert main([str(template), str(prefs_js), "--check"]) == 0
        assert prefs_js.is_file()
        prefs_js.unlink()
        checked.append(template.name)
    assert "browser-fuzzing.yml" in checked


def test_templates_02():
    """check formatting of template YAML files"""
    for template in PrefPicker.templates():
        with template.open() as in_fp:
            # remove comments
            input_yml = "".join(x for x in in_fp if not x.lstrip().startswith("#"))
        formatted_yml = safe_dump(safe_load(input_yml), indent=2, width=100)
        diff = tuple(
            unified_diff(
                input_yml.splitlines(),
                formatted_yml.splitlines(),
                fromfile=str(template),
                tofile="formatting fixes",
                lineterm="",
            )
        )
        if diff:
            formatted = "\n".join(diff)
            raise AssertionError(f"Formatting changes required:\n{formatted}")
