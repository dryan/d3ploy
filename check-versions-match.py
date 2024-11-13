#! /usr/bin/env python3

import os
import pathlib
import re
import sys


def main():
    d3ploy_content = pathlib.Path("d3ploy/d3ploy.py").read_text()
    d3ploy_version = re.search(r'VERSION = "(.+)"', d3ploy_content)
    pyproject_content = pathlib.Path("pyproject.toml").read_text()
    pyproject_version = re.search(r'version = "(.+)"', pyproject_content)

    if d3ploy_version.group(1) != pyproject_version.group(1):
        print(
            f"Versions do not match: {d3ploy_version.group(1)} != {pyproject_version.group(1)}",
            file=sys.stderr,
        )
        sys.exit(os.EX_DATAERR)


if __name__ == "__main__":
    main()
