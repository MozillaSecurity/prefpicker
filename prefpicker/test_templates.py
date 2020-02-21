# coding=utf-8
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
"""template.py tests"""

import os

from .main import main


def test_templates(tmp_path):
    """sanity check template YAML files"""
    prefs_js = (tmp_path / "prefs.js")
    yml_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "templates")
    checked = []
    for yml in os.listdir(yml_path):
        if not yml.endswith(".yml"):
            continue
        assert main([os.path.join(yml_path, yml), str(prefs_js), "--check"]) == 0
        assert prefs_js.is_file()
        prefs_js.unlink()
        checked.append(yml)
    assert "browser-fuzzing.yml" in checked
