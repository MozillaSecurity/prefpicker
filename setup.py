#!/usr/bin/env python
# coding=utf-8
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""setuptools install script"""

from setuptools import setup

if __name__ == "__main__":
    setup(
        author="Tyson Smith",
        description="PrefPicker - Manage & generate prefs.js files",
        entry_points={
            "console_scripts": ["prefpicker = prefpicker.main:main"]
        },
        extra_requires=[
            "pytest",
            "pytest-cov",
            "pytest-pylint"
        ],
        install_requires=[
            "pyyaml"
        ],
        keywords="firefox fuzz fuzzing test testing",
        license="MPL 2.0",
        maintainer="Mozilla Fuzzing Team",
        maintainer_email="fuzzing@mozilla.com",
        name="prefpicker",
        packages=["prefpicker"],
        url="https://github.com/MozillaSecurity/prefpicker",
        version="1.0.1")
