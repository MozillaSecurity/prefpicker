# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
"""main.py tests"""

from pytest import raises

from .main import main
from .prefpicker import PrefPicker


def test_main_01(tmp_path):
    """test main()"""
    prefs_js = tmp_path / "prefs.js"
    yml = tmp_path / "test.yml"
    yml.write_text(
        """
        variant: []
        pref:
          test.a:
            variants:
              default: [1]"""
    )
    assert main([str(yml), str(prefs_js), "--variant", "default"]) == 0
    assert prefs_js.is_file()


def test_main_02(capsys):
    """test main() with missing input"""
    with raises(SystemExit):
        main(["missing.yml", "prefs.js"])
    assert "Cannot find input file 'missing.yml'" in capsys.readouterr()[1]


def test_main_03(tmp_path):
    """test main() with built-in input"""
    prefs_js = tmp_path / "prefs.js"
    templates = tuple(x.name for x in PrefPicker.templates())
    assert templates
    assert main([templates[0], str(prefs_js)]) == 0
    assert prefs_js.is_file()


def test_main_04(tmp_path):
    """test main() with invalid variant"""
    prefs_js = tmp_path / "prefs.js"
    yml = tmp_path / "test.yml"
    yml.write_text(
        """
        variant: []
        pref:
          test.a:
            variants:
              default: [1]"""
    )
    assert main([str(yml), str(prefs_js), "--variant", "x"]) == 1
    assert not prefs_js.is_file()


def test_main_05(tmp_path):
    """test main() with check results"""
    prefs_js = tmp_path / "prefs.js"
    yml = tmp_path / "test.yml"
    yml.write_text(
        """
        variant: [extra]
        pref:
          test.a:
            variants:
              default: [1, 1]
              extra: [1, 1]"""
    )
    assert main([str(yml), str(prefs_js), "--check", "--variant", "extra"]) == 0
    assert prefs_js.is_file()


def test_main_06(capsys, tmp_path):
    """test main() with invalid output path"""
    yml = tmp_path / "test.yml"
    yml.touch()
    # output is a directory
    with raises(SystemExit):
        main([str(yml), str(tmp_path)])
    assert "is a directory." in capsys.readouterr()[1]
    # output to missing directory
    with raises(SystemExit):
        main([str(yml), str(tmp_path / "missing" / "prefs.js")])
    assert "directory does not exist." in capsys.readouterr()[1]


def test_main_07(tmp_path):
    """test main() with invalid input"""
    yml = tmp_path / "test.yml"
    yml.write_text("{test{")
    assert main([str(yml), str(tmp_path / "prefs.js")]) == 1
