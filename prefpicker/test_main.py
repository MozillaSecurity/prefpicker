# coding=utf-8
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
"""main.py tests"""

from os.path import basename

from .main import main
from . import PrefPicker

def test_main_01(tmp_path):
    """test main()"""
    prefs_js = (tmp_path / "prefs.js")
    yml = (tmp_path / "test.yml")
    yml.write_text("""
        variant: []
        pref:
          test.a:
            default: [1]""")
    assert main([str(yml), str(prefs_js), "--variant", "default"]) == 0
    assert prefs_js.is_file()

def test_main_02(tmp_path):
    """test main() with missing input"""
    prefs_js = (tmp_path / "prefs.js")
    assert main(["missing.yml", str(prefs_js)]) == 1
    assert not prefs_js.is_file()

def test_main_03(tmp_path):
    """test main() with builtin input"""
    prefs_js = (tmp_path / "prefs.js")
    templates = tuple(basename(x) for x in PrefPicker.templates())
    assert templates
    assert main([templates[0], str(prefs_js)]) == 0
    assert prefs_js.is_file()

def test_main_04(tmp_path):
    """test main() with invalid variant"""
    prefs_js = (tmp_path / "prefs.js")
    yml = (tmp_path / "test.yml")
    yml.write_text("""
        variant: []
        pref:
          test.a:
            default: [1]""")
    assert main([str(yml), str(prefs_js), "--variant", "x"]) == 1
    assert not prefs_js.is_file()

def test_main_05(tmp_path):
    """test main() with check results"""
    prefs_js = (tmp_path / "prefs.js")
    yml = (tmp_path / "test.yml")
    yml.write_text("""
        variant: [extra]
        pref:
          test.a:
            default: [1, 1]
            extra: [1, 1]""")
    assert main([str(yml), str(prefs_js), "--check", "--variant", "extra"]) == 0
    assert prefs_js.is_file()
