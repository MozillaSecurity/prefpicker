#!/bin/bash
set -e -x -o pipefail
version_before="$(python3 -m setuptools_scm)"
semantic-release -v version --no-changelog --no-commit --no-vcs-release
version_after="$(python3 -m setuptools_scm)"
if [[ "$version_after" != "$version_before" ]]; then
  python -m build -v
  twine upload --skip-existing dist/*
fi
