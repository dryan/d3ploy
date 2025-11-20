#! /usr/bin/env python3

import os
import pathlib
import re
import sys


def main():
    # Check __init__.py for version
    init_content = pathlib.Path("d3ploy/__init__.py").read_text()
    init_version = re.search(r'__version__ = "(.+)"', init_content)

    pyproject_content = pathlib.Path("pyproject.toml").read_text()
    pyproject_version = re.search(r'version = "(.+)"', pyproject_content)

    if not init_version:
        print(
            "Could not find version in d3ploy/__init__.py",
            file=sys.stderr,
        )
        sys.exit(os.EX_DATAERR)

    if not pyproject_version:
        print(
            "Could not find version in pyproject.toml",
            file=sys.stderr,
        )
        sys.exit(os.EX_DATAERR)

    d3ploy_ver = init_version.group(1)
    pyproject_ver = pyproject_version.group(1)

    if d3ploy_ver != pyproject_ver:
        print(
            f"Versions do not match: {d3ploy_ver} != {pyproject_ver}",
            file=sys.stderr,
        )
        sys.exit(os.EX_DATAERR)


if __name__ == "__main__":
    main()
