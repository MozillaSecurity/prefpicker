# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
"""prefpicker.py tests"""

from pytest import mark, raises

from .prefpicker import PrefPicker, SourceDataError


def test_prefpicker_load_template(tmp_path):
    """test simple PrefPicker"""
    yml = tmp_path / "test.yml"
    yml.write_text(
        """
        variant: {}
        pref:
          test.a:
            variants:
              default: [1]"""
    )
    picker = PrefPicker.load_template(yml)
    assert not picker.variants
    assert len(picker.prefs) == 1
    assert "test.a" in picker.prefs


@mark.parametrize(
    "data, msg",
    [
        # invalid template
        ([], "invalid template"),
        # variant list missing
        ({"pref": {"a.b": {"variants": {"default": [1]}}}}, "variant dict is missing"),
        # variant definition has invalid name type
        ({"variant": {"bad": 1}}, "variant parent name must be a string"),
        # variant definition has invalid parent name type
        ({"variant": {1: "bad"}}, "variant name must be a string"),
        # variant is invalid type
        ({"variant": ""}, "variant must be a dict"),
        # undefined variant parent
        ({"variant": {"a": "bad"}}, "variant parent 'bad' is an undefined variant"),
        # variant name is empty
        ({"variant": {"": "default"}}, "variant name is empty"),
        # variant cannot be parent of itself
        (
            {"variant": {"a": "b", "b": "c", "c": "a"}},
            "variant cannot be parent of itself",
        ),
        # pref dict missing
        ({"variant": {}}, "pref dict is missing"),
        # pref is invalid type
        ({"pref": [], "variant": {}}, "pref must be a dict"),
        # pref entry is invalid
        ({"pref": {"a.b": None}, "variant": {}}, "'a.b' entry must contain a dict"),
        # pref variants is invalid
        (
            {"pref": {"a.b": {"variants": None}}, "variant": {}},
            "'a.b' is missing 'variants' dict",
        ),
        # pref missing default variant
        (
            {"variant": {}, "pref": {"test.a": {"variants": {}}}},
            "'test.a' is missing 'default' variant",
        ),
        # pref variants must be strings
        (
            {
                "variant": {},
                "pref": {"test.a": {"variants": {"default": ["a"], 1: "bad"}}},
            },
            "'test.a' variants must be strings",
        ),
        # template with undefined variant
        (
            {"variant": {}, "pref": {"a.b": {"variants": {"default": [1], "x": [2]}}}},
            "'x' in 'a.b' is an undefined variant",
        ),
        # template with unused variant
        (
            {
                "variant": {"unused": "default"},
                "pref": {"a.b": {"variants": {"default": [1]}}},
            },
            "Unused variants 'unused'",
        ),
        # pref with empty variant list
        (
            {"variant": {}, "pref": {"a.b": {"variants": {"default": []}}}},
            "'default' in 'a.b' is empty",
        ),
        # pref with invalid variant type
        (
            {"variant": {}, "pref": {"a.b": {"variants": {"default": "x"}}}},
            "variant 'default' in 'a.b' must be a list",
        ),
        # pref variant with invalid type
        (
            {"variant": {}, "pref": {"a.b": {"variants": {"default": [1.11]}}}},
            "unsupported datatype 'float' \\(a.b\\)",
        ),
    ],
)
def test_prefpicker_verify_data_errors(data, msg):
    """test PrefPicker.verify_data() - errors"""
    with raises(SourceDataError, match=msg):
        PrefPicker.verify_data(data)


def test_prefpicker_create_prefsjs_empty(tmp_path):
    """test simple PrefPicker.create_prefsjs() - no prefs"""
    ppick = PrefPicker()
    prefs = tmp_path / "prefs.js"
    ppick.create_prefsjs(prefs)
    assert prefs.is_file()
    # check only comments were written to the document
    with prefs.open("r") as in_fp:
        for line in in_fp:
            assert line.startswith("//")
        assert in_fp.tell() > 0


@mark.parametrize(
    "data, variant",
    [
        # select data from default
        ({"variant": {}, "pref": {"a.b": {"variants": {"default": [0]}}}}, "default"),
        # select data from default
        (
            {
                "variant": {"v1": "default"},
                "pref": {"a.b": {"variants": {"default": [0], "v1": [1]}}},
            },
            "default",
        ),
        # select data from v1
        (
            {
                "variant": {"v1": "default"},
                "pref": {"a.b": {"variants": {"default": [1], "v1": [0]}}},
            },
            "v1",
        ),
        # select data from v2
        (
            {
                "variant": {"v1": "default", "v2": "v1"},
                "pref": {"a.b": {"variants": {"default": [2], "v1": [1], "v2": [0]}}},
            },
            "v2",
        ),
        # include data from default
        (
            {
                "variant": {"v1": "default"},
                "pref": {
                    "a.b": {"variants": {"default": [0]}},
                    "c.b": {"variants": {"default": [0], "v1": [1]}},
                },
            },
            "v1",
        ),
        # select data from parent variant
        (
            {
                "variant": {"v1": "default", "v2": "v1"},
                "pref": {
                    "a.b": {"variants": {"default": [1], "v1": [0]}},
                    "c.b": {"variants": {"default": [0], "v2": [1]}},
                },
            },
            "v2",
        ),
        # include data from default
        (
            {
                "variant": {"v1": "default", "v2": "default"},
                "pref": {
                    "a.b": {"variants": {"default": [0], "v1": [1]}},
                    "c.b": {"variants": {"default": [0], "v2": [1]}},
                },
            },
            "v2",
        ),
    ],
)
def test_prefpicker_variant_value_selection(tmp_path, data, variant):
    """test PrefPicker verify data and variant value selection"""
    PrefPicker.verify_data(data)
    ppick = PrefPicker()
    ppick.variants = data["variant"]
    ppick.prefs = data["pref"]
    prefs = tmp_path / "prefs.js"
    ppick.create_prefsjs(prefs, variant=variant)
    assert prefs.is_file()
    assert 'user_pref("a.b", 0);' in prefs.read_text()


def test_prefpicker_check_overwrites():
    """test PrefPicker.check_overwrites()"""
    raw_data = {
        "variant": {"fail": "default", "safe": "default"},
        "pref": {
            "test.a": {"variants": {"default": [1], "fail": [1, 2], "safe": [3]}},
            "test.b": {"variants": {"default": [9], "safe": [None]}},
        },
    }
    # use verify_data just to sanity check test data
    PrefPicker.verify_data(raw_data)
    ppick = PrefPicker()
    ppick.variants = raw_data["variant"]
    ppick.prefs = raw_data["pref"]
    results = tuple(ppick.check_overwrites())
    assert results
    assert results[0][0] == "test.a"
    assert results[0][1] == "fail"
    assert results[0][2] == 1


def test_prefpicker_check_duplicates():
    """test PrefPicker.check_duplicates()"""
    raw_data = {
        "variant": {"fail": "default", "safe": "default"},
        "pref": {
            "test.a": {"variants": {"default": [1], "fail": [1, 2, 3, 1], "safe": [3]}},
            "test.b": {"variants": {"default": [9], "safe": [None]}},
        },
    }
    # use verify_data just to sanity check test data
    PrefPicker.verify_data(raw_data)
    ppick = PrefPicker()
    ppick.variants = raw_data["variant"]
    ppick.prefs = raw_data["pref"]
    results = tuple(ppick.check_duplicates())
    assert results
    assert results[0][0] == "test.a"
    assert results[0][1] == "fail"


def test_prefpicker_create_prefsjs_basic_variants(tmp_path):
    """test PrefPicker.create_prefsjs() with variants"""
    raw_data = {
        "variant": {"test": "default", "skip": "default"},
        "pref": {
            "test.a": {"variants": {"default": [0], "test": [1], "skip": [2]}},
            "test.b": {"variants": {"default": [True]}},
        },
    }
    PrefPicker.verify_data(raw_data)
    ppick = PrefPicker()
    ppick.variants = raw_data["variant"]
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


def test_prefpicker_create_prefsjs_pref_value_types(tmp_path):
    """test PrefPicker.create_prefsjs() with different prefs value types"""
    raw_data = {
        "variant": {},
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
    ppick.variants = raw_data["variant"]
    ppick.prefs = raw_data["pref"]
    prefs = tmp_path / "prefs.js"
    ppick.create_prefsjs(prefs)
    assert prefs.is_file()
    prefs_data = prefs.read_text()
    assert 'user_pref("test.b",' not in prefs_data
    assert "user_pref(\"test.c\", 'test string');" in prefs_data
    # test with unsupported value datatype
    raw_data = {"variant": {}, "pref": {"boom.": {"variants": {"default": [1.01]}}}}
    ppick.variants = raw_data["variant"]
    ppick.prefs = raw_data["pref"]
    with raises(SourceDataError, match="Unsupported datatype"):
        ppick.create_prefsjs(prefs)


def test_prefpicker_load_invalid_yaml(tmp_path):
    """test PrefPicker.load_template() with invalid YAML"""
    yml = tmp_path / "test.yml"
    yml.write_text("{-{-{-{-:::")
    with raises(SourceDataError, match=r"invalid YAML"):
        PrefPicker.load_template(yml)


def test_prefpicker_lookup_template():
    """test PrefPicker.lookup_template()"""
    # unknown template
    assert PrefPicker.lookup_template("missing") is None
    # existing template
    template = next(PrefPicker.templates())
    assert template
    assert PrefPicker.lookup_template(template.name)
