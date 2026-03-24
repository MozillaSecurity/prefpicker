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


def test_main_08(tmp_path):
    """test main() with --json override and prefs not in template"""
    prefs_js = tmp_path / "prefs.js"
    yml = tmp_path / "test.yml"
    yml.write_text(
        """
        variant: []
        pref:
          test.a:
            variants:
              default: [1]
          test.b:
            variants:
              default: [true]"""
    )
    json_file = tmp_path / "overrides.json"
    json_file.write_text('{"test.a": 99, "test.new": false}')
    assert main([str(yml), str(prefs_js), "--json", str(json_file)]) == 0
    assert prefs_js.is_file()
    prefs_data = prefs_js.read_text()
    assert 'user_pref("test.a", 99);' in prefs_data
    assert "defined by --json override" in prefs_data
    assert 'user_pref("test.b", true);' in prefs_data
    assert 'user_pref("test.new", false);' in prefs_data
    assert "// 'test.new' defined by --json (not in template)" in prefs_data


def test_main_09(capsys, tmp_path):
    """test main() with missing --json file"""
    yml = tmp_path / "test.yml"
    yml.touch()
    with raises(SystemExit):
        main([str(yml), str(tmp_path / "prefs.js"), "--json", "missing.json"])
    assert "Cannot find JSON file 'missing.json'" in capsys.readouterr()[1]


def test_main_10(tmp_path):
    """test main() with invalid JSON content"""
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
    # invalid JSON syntax
    json_file = tmp_path / "bad.json"
    json_file.write_text("{bad json")
    assert main([str(yml), str(prefs_js), "--json", str(json_file)]) == 1
    # non-UTF-8 bytes
    json_file.write_bytes(b"\x80\x81\x82")
    assert main([str(yml), str(prefs_js), "--json", str(json_file)]) == 1


def test_main_11(tmp_path):
    """test main() with non-dict JSON content"""
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
    json_file = tmp_path / "list.json"
    json_file.write_text("[1, 2, 3]")
    assert main([str(yml), str(prefs_js), "--json", str(json_file)]) == 1
