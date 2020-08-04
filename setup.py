#!/usr/bin/env python
# coding=utf-8
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""setuptools install script"""
import pathlib
from setuptools import setup

if __name__ == "__main__":
    README = (pathlib.Path(__file__).parent / "README.md").read_text()

    setup(
        author="Tyson Smith",
        author_email="twsmith@mozilla.com",
        classifiers=[
            'Topic :: Software Development :: Testing',
            'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
            'Programming Language :: Python :: 3',
        ],
        description="PrefPicker - Manage & generate prefs.js files",
        entry_points={
            "console_scripts": ["prefpicker = prefpicker.main:main"]
        },
        extra_requires=[
            "pytest",
            "pytest-cov",
            "pytest-pylint"
        ],
        include_package_data=True,
        install_requires=[
            "pyyaml"
        ],
        keywords="firefox fuzz fuzzing test testing",
        license="MPL 2.0",
        long_description=README,
        long_description_content_type="text/markdown",
        maintainer="Mozilla Fuzzing Team",
        maintainer_email="fuzzing@mozilla.com",
        name="prefpicker",
        packages=["prefpicker"],
        url="https://github.com/MozillaSecurity/prefpicker",
        version="1.0.6")
