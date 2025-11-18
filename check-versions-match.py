#! /usr/bin/env python3

import os
import pathlib
import re
import sys


def main():
    # Check __init__.py for version
    init_content = pathlib.Path("d3ploy/__init__.py").read_text()
    init_version = re.search(r'__version__ = "(.+)"', init_content)

    # Also check d3ploy.py for backward compatibility VERSION constant
    d3ploy_content = pathlib.Path("d3ploy/d3ploy.py").read_text()
    d3ploy_version = re.search(r'VERSION = "(.+)"', d3ploy_content)

    pyproject_content = pathlib.Path("pyproject.toml").read_text()
    pyproject_version = re.search(r'version = "(.+)"', pyproject_content)

    # Use __init__.py version if found, otherwise fall back to d3ploy.py
    if init_version:
        d3ploy_ver = init_version.group(1)
    elif d3ploy_version:
        d3ploy_ver = d3ploy_version.group(1)
    else:
        print(
            "Could not find version in d3ploy/__init__.py or d3ploy/d3ploy.py",
            file=sys.stderr,
        )
        sys.exit(os.EX_DATAERR)

    if not pyproject_version:
        print(
            "Could not find version in pyproject.toml",
            file=sys.stderr,
        )
        sys.exit(os.EX_DATAERR)

    if d3ploy_ver != pyproject_version.group(1):
        print(
            f"Versions do not match: {d3ploy_ver} != {pyproject_version.group(1)}",
            file=sys.stderr,
        )
        sys.exit(os.EX_DATAERR)


if __name__ == "__main__":
    main()
