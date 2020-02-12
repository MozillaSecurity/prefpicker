# coding=utf-8
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
"""prefpicker.py tests"""

import pytest

from .prefpicker import PrefPicker, SourceDataError


def test_prefpicker_01(tmp_path):
    """test simple PrefPicker"""
    yml = (tmp_path / "test.yml")
    yml.write_text("""
        variant: []
        pref:
          test.a:
            default: [1]""")
    picker = PrefPicker.load_template(str(yml))
    assert len(picker.variants) == 1
    assert "default" in picker.variants
    assert len(picker.prefs) == 1
    assert "test.a" in picker.prefs

def test_prefpicker_02():
    """test PrefPicker.verify_data() template missing/bad variant"""
    raw_data = {"pref": {"a.b": {"default": [1]}}}
    with pytest.raises(SourceDataError, match="variant list is missing"):
        PrefPicker.verify_data(raw_data)
    # variant is invalid type
    raw_data = {"variant": [{"bad": 1}]}
    with pytest.raises(SourceDataError, match="variant definition must be a string"):
        PrefPicker.verify_data(raw_data)
    raw_data = {
        "pref": {"a.b": {"default": [1]}},
        "variant": "invalid"}
    with pytest.raises(SourceDataError, match="variant is not a list"):
        PrefPicker.verify_data(raw_data)

def test_prefpicker_03():
    """test PrefPicker.verify_data() template missing/bad pref"""
    raw_data = {"variant": []}
    with pytest.raises(SourceDataError, match="pref group is missing"):
        PrefPicker.verify_data(raw_data)
    # pref is invalid type
    raw_data = {"pref": [], "variant": []}
    with pytest.raises(SourceDataError, match="pref is not a dict"):
        PrefPicker.verify_data(raw_data)

def test_prefpicker_04():
    """test PrefPicker.verify_data() template with pref missing default variant"""
    raw_data = {
        "variant": [],
        "pref": {"test.a": ""}}
    with pytest.raises(SourceDataError, match="'test.a' is missing 'default' variant"):
        PrefPicker.verify_data(raw_data)

def test_prefpicker_05():
    """test PrefPicker.verify_data() template with undefined variant"""
    raw_data = {
        "variant": [],
        "pref": {"test.a": {
            "default": [1],
            "typo": [2]}}}
    with pytest.raises(SourceDataError, match="'typo' in 'test.a' is not a defined variant"):
        PrefPicker.verify_data(raw_data)

def test_prefpicker_06():
    """test PrefPicker.verify_data() template with unused variant"""
    raw_data = {
        "variant": ["unused"],
        "pref": {"a.b": {"default": [1]}}}
    with pytest.raises(SourceDataError, match="Unused variants 'unused'"):
        PrefPicker.verify_data(raw_data)

def test_prefpicker_07():
    """test PrefPicker.verify_data() template with empty variant"""
    raw_data = {
        "variant": [],
        "pref": {"test.a": {"default": []}}}
    with pytest.raises(SourceDataError, match="'default' in 'test.a' is empty"):
        PrefPicker.verify_data(raw_data)

def test_prefpicker_08():
    """test PrefPicker.verify_data() template with invalid variant"""
    raw_data = {
        "variant": [],
        "pref": {"test.a": {"default": "invalid"}}}
    with pytest.raises(SourceDataError, match="variant 'default' in 'test.a' is not a list"):
        PrefPicker.verify_data(raw_data)

def test_prefpicker_09():
    """test PrefPicker.check_overwrites()"""
    raw_data = {
        "variant": ["fail", "safe"],
        "pref": {
            "test.a": {
                "default": [1],
                "fail": [1, 2],
                "safe": [3]
            },
            "test.b": {
                "default": [9],
                "safe": [None]}}}
    # use verify_data just to sanity check test data
    PrefPicker.verify_data(raw_data)
    ppick = PrefPicker()
    ppick.variants = set(raw_data["variant"] + ["default"])
    ppick.prefs = raw_data["pref"]
    results = tuple(ppick.check_overwrites())
    assert results
    assert results[0][0] == "test.a"
    assert results[0][1] == "fail"
    assert results[0][2] == 1

def test_prefpicker_10():
    """test PrefPicker.check_duplicates()"""
    raw_data = {
        "variant": ["fail", "safe"],
        "pref": {
            "test.a": {
                "default": [1],
                "fail": [1, 2, 3, 1],
                "safe": [3]
            },
            "test.b": {
                "default": [9],
                "safe": [None]}}}
    # use verify_data just to sanity check test data
    PrefPicker.verify_data(raw_data)
    ppick = PrefPicker()
    ppick.variants = set(raw_data["variant"] + ["default"])
    ppick.prefs = raw_data["pref"]
    results = tuple(ppick.check_duplicates())
    assert results
    assert results[0][0] == "test.a"
    assert results[0][1] == "fail"

def test_prefpicker_11():
    """test PrefPicker.check_combinations()"""
    raw_data = {
        "variant": ["v1", "v2"],
        "pref": {
            "test.a": {
                "default": [1],
                "v1": [1, 2, 3, 4],
                "v2": [3]
            },
            "test.b": {
                "default": [2],
                "v1": [1, 2],
                "v2": [3]
            },
            "test.c": {
                "default": [1, 3],
                "v2": [None]}}}
    # use verify_data just to sanity check test data
    PrefPicker.verify_data(raw_data)
    ppick = PrefPicker()
    ppick.variants = set(raw_data["variant"] + ["default"])
    ppick.prefs = raw_data["pref"]
    results = tuple(ppick.check_combinations())
    assert len(results) == 2
    assert results[0][0] == "default"
    assert results[0][1] == 2
    assert results[1][0] == "v1"
    assert results[1][1] == 16

def test_prefpicker_12(tmp_path):
    """test simple PrefPicker.create_prefsjs()"""
    ppick = PrefPicker()
    prefs = (tmp_path / "prefs.js")
    ppick.create_prefsjs(str(prefs))
    assert prefs.is_file()
    # check only comments were written to the document
    with prefs.open("r") as in_fp:
        for line in in_fp:
            assert line.startswith("//")
        assert in_fp.tell() > 0

def test_prefpicker_13(tmp_path):
    """test PrefPicker.create_prefsjs() with variants"""
    raw_data = {
        "variant": ["test", "skip"],
        "pref": {
            "test.a": {
                "default": [0],
                "test": [1],
                "skip": [2]
            },
            "test.b": {
                "default": [True]}}}
    PrefPicker.verify_data(raw_data)
    ppick = PrefPicker()
    ppick.variants = set(raw_data["variant"] + ["default"])
    ppick.prefs = raw_data["pref"]
    prefs = (tmp_path / "prefs.js")
    # test with 'default' variant
    ppick.create_prefsjs(str(prefs))
    assert prefs.is_file()
    prefs_data = prefs.read_text()
    assert "defined by variant 'default'" not in prefs_data
    assert "user_pref(\"test.a\", 0);\n" in prefs_data
    assert "user_pref(\"test.b\", true);\n" in prefs_data
    # test with 'test' variant
    ppick.create_prefsjs(str(prefs), variant="test")
    assert prefs.is_file()
    prefs_data = prefs.read_text()
    assert "user_pref(\"test.a\", 1);\n" in prefs_data
    assert "user_pref(\"test.b\", true);\n" in prefs_data
    assert "// 'test.a' defined by variant 'test'" in prefs_data

def test_prefpicker_14(tmp_path):
    """test PrefPicker.create_prefsjs() with different values"""
    raw_data = {
        "variant": [],
        "pref": {
            "test.a": {
                "default": [0, 1],
            },
            "test.b": {
                "default": [None],
            },
            "test.c": {
                "default": ["test string"],
            },
            "test.d": {
                "default": ["'test' \"string\""],
            },
            "test.e": {
                "default": [True],
            },
            "test.f": {
                "default": [False]}}}
    PrefPicker.verify_data(raw_data)
    ppick = PrefPicker()
    ppick.variants = set(raw_data["variant"] + ["default"])
    ppick.prefs = raw_data["pref"]
    prefs = (tmp_path / "prefs.js")
    ppick.create_prefsjs(str(prefs))
    assert prefs.is_file()
    prefs_data = prefs.read_text()
    assert "user_pref(\"test.b\"," not in prefs_data
    assert "user_pref(\"test.c\", 'test string');" in prefs_data
    # test with unsupported value datatype
    raw_data = {
        "variant": [],
        "pref": {"boom.": {"default": [1.01]}}}
    ppick.variants = set(raw_data["variant"] + ["default"])
    ppick.prefs = raw_data["pref"]
    with pytest.raises(SourceDataError, match="Unknown datatype"):
        ppick.create_prefsjs(str(prefs))
