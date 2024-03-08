# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
"""prefpicker.py tests"""

from pytest import mark, raises

from .prefpicker import PrefPicker, SourceDataError


def test_prefpicker_01(tmp_path):
    """test simple PrefPicker"""
    yml = tmp_path / "test.yml"
    yml.write_text(
        """
        variant: []
        pref:
          test.a:
            variants:
              default: [1]"""
    )
    picker = PrefPicker.load_template(yml)
    assert len(picker.variants) == 1
    assert "default" in picker.variants
    assert len(picker.prefs) == 1
    assert "test.a" in picker.prefs


@mark.parametrize(
    "data, msg",
    [
        # invalid template
        ([], "invalid template"),
        # variant list missing
        ({"pref": {"a.b": {"variants": {"default": [1]}}}}, "variant list is missing"),
        # variant definition is invalid type
        ({"variant": [{"bad": 1}]}, "variant definition must be a string"),
        # variant is invalid type
        ({"variant": ""}, "variant is not a list"),
        # pref dict missing
        ({"variant": []}, "pref group is missing"),
        # pref is invalid type
        ({"pref": [], "variant": []}, "pref is not a dict"),
        # pref entry is invalid
        ({"pref": {"a.b": None}, "variant": []}, "'a.b' entry must contain a dict"),
        # pref variants is invalid
        (
            {"pref": {"a.b": {"variants": None}}, "variant": []},
            "'a.b' is missing 'variants' dict",
        ),
        # pref missing default variant
        (
            {"variant": [], "pref": {"test.a": {"variants": {}}}},
            "'test.a' is missing 'default' variant",
        ),
        # template with undefined variant
        (
            {"variant": [], "pref": {"a.b": {"variants": {"default": [1], "x": [2]}}}},
            "'x' in 'a.b' is not a defined variant",
        ),
        # template with unused variant
        (
            {"variant": ["unused"], "pref": {"a.b": {"variants": {"default": [1]}}}},
            "Unused variants 'unused'",
        ),
        # pref with empty variant list
        (
            {"variant": [], "pref": {"a.b": {"variants": {"default": []}}}},
            "'default' in 'a.b' is empty",
        ),
        # pref with invalid variant type
        (
            {"variant": [], "pref": {"a.b": {"variants": {"default": "x"}}}},
            "variant 'default' in 'a.b' is not a list",
        ),
        # pref variant with invalid type
        (
            {"variant": [], "pref": {"a.b": {"variants": {"default": [1.11]}}}},
            "unsupported datatype 'float' \\(a.b\\)",
        ),
    ],
)
def test_prefpicker_02(data, msg):
    """test PrefPicker.verify_data()"""
    with raises(SourceDataError, match=msg):
        PrefPicker.verify_data(data)


def test_prefpicker_03():
    """test PrefPicker.check_overwrites()"""
    raw_data = {
        "variant": ["fail", "safe"],
        "pref": {
            "test.a": {"variants": {"default": [1], "fail": [1, 2], "safe": [3]}},
            "test.b": {"variants": {"default": [9], "safe": [None]}},
        },
    }
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


def test_prefpicker_04():
    """test PrefPicker.check_duplicates()"""
    raw_data = {
        "variant": ["fail", "safe"],
        "pref": {
            "test.a": {"variants": {"default": [1], "fail": [1, 2, 3, 1], "safe": [3]}},
            "test.b": {"variants": {"default": [9], "safe": [None]}},
        },
    }
    # use verify_data just to sanity check test data
    PrefPicker.verify_data(raw_data)
    ppick = PrefPicker()
    ppick.variants = set(raw_data["variant"] + ["default"])
    ppick.prefs = raw_data["pref"]
    results = tuple(ppick.check_duplicates())
    assert results
    assert results[0][0] == "test.a"
    assert results[0][1] == "fail"


def test_prefpicker_05():
    """test PrefPicker.check_combinations()"""
    raw_data = {
        "variant": ["v1", "v2"],
        "pref": {
            "test.a": {"variants": {"default": [1], "v1": [1, 2, 3, 4], "v2": [3]}},
            "test.b": {"variants": {"default": [2], "v1": [1, 2], "v2": [3]}},
            "test.c": {"variants": {"default": [1, 3], "v2": [None]}},
        },
    }
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


def test_prefpicker_06(tmp_path):
    """test simple PrefPicker.create_prefsjs()"""
    ppick = PrefPicker()
    prefs = tmp_path / "prefs.js"
    ppick.create_prefsjs(prefs)
    assert prefs.is_file()
    # check only comments were written to the document
    with prefs.open("r") as in_fp:
        for line in in_fp:
            assert line.startswith("//")
        assert in_fp.tell() > 0


def test_prefpicker_07(tmp_path):
    """test PrefPicker.create_prefsjs() with variants"""
    raw_data = {
        "variant": ["test", "skip"],
        "pref": {
            "test.a": {"variants": {"default": [0], "test": [1], "skip": [2]}},
            "test.b": {"variants": {"default": [True]}},
        },
    }
    PrefPicker.verify_data(raw_data)
    ppick = PrefPicker()
    ppick.variants = set(raw_data["variant"] + ["default"])
    ppick.prefs = raw_data["pref"]
    prefs = tmp_path / "prefs.js"
    # test with 'default' variant
    ppick.create_prefsjs(prefs)
    assert prefs.is_file()
    prefs_data = prefs.read_text()
    assert "defined by variant 'default'" not in prefs_data
    assert 'user_pref("test.a", 0);\n' in prefs_data
    assert 'user_pref("test.b", true);\n' in prefs_data
    # test with 'test' variant
    ppick.create_prefsjs(prefs, variant="test")
    assert prefs.is_file()
    prefs_data = prefs.read_text()
    assert 'user_pref("test.a", 1);\n' in prefs_data
    assert 'user_pref("test.b", true);\n' in prefs_data
    assert "// 'test.a' defined by variant 'test'" in prefs_data


def test_prefpicker_08(tmp_path):
    """test PrefPicker.create_prefsjs() with different values"""
    raw_data = {
        "variant": [],
        "pref": {
            # type int
            "test.a": {
                "variants": {
                    "default": [0, 1],
                }
            },
            # type None (skip)
            "test.b": {
                "variants": {
                    "default": [None],
                }
            },
            # type string
            "test.c": {
                "variants": {
                    "default": ["test string"],
                }
            },
            # type string (with quotes)
            "test.d": {
                "variants": {
                    "default": ["'test' \"string\""],
                }
            },
            # type bool
            "test.e": {
                "variants": {
                    "default": [True, False],
                }
            },
            # add None twice to trigger the 'skip' code path and write out comment
            "test.f": {
                "variants": {
                    "default": [None, None],
                }
            },
            # mixed types
            "test.g": {
                "variants": {
                    "default": ["foo", True, 0],
                }
            },
        },
    }
    PrefPicker.verify_data(raw_data)
    ppick = PrefPicker()
    ppick.variants = set(raw_data["variant"] + ["default"])
    ppick.prefs = raw_data["pref"]
    prefs = tmp_path / "prefs.js"
    ppick.create_prefsjs(prefs)
    assert prefs.is_file()
    prefs_data = prefs.read_text()
    assert 'user_pref("test.b",' not in prefs_data
    assert "user_pref(\"test.c\", 'test string');" in prefs_data
    # test with unsupported value datatype
    raw_data = {"variant": [], "pref": {"boom.": {"variants": {"default": [1.01]}}}}
    ppick.variants = set(raw_data["variant"] + ["default"])
    ppick.prefs = raw_data["pref"]
    with raises(SourceDataError, match="Unsupported datatype"):
        ppick.create_prefsjs(prefs)


def test_prefpicker_09(tmp_path):
    """test PrefPicker.load_template() with invalid YAML"""
    yml = tmp_path / "test.yml"
    yml.write_text("{-{-{-{-:::")
    with raises(SourceDataError, match=r"invalid YAML"):
        PrefPicker.load_template(yml)


def test_prefpicker_10():
    """test PrefPicker.lookup_template()"""
    # unknown template
    assert PrefPicker.lookup_template("missing") is None
    # existing template
    template = tuple(PrefPicker.templates())[0]
    assert template
    assert PrefPicker.lookup_template(template.name)
