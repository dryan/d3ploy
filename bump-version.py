#! /usr/bin/env python3

import argparse
import pathlib
import re

from packaging.version import Version
from packaging.version import parse


def main():
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument(
        "version_type",
        choices=["major", "minor", "patch"],
        default="patch",
        nargs="?",
    )
    args_parser.add_argument("--prerelease", action="store_true")
    args = args_parser.parse_args()
    version_type = args.version_type
    prerelease = args.prerelease
    pyproject_content = pathlib.Path("pyproject.toml").read_text()
    pyproject_version = re.search(r'version = "(.+)"', pyproject_content).group(1)
    pyproject_version = parse(pyproject_version)
    new_version = Version(str(pyproject_version))
    match version_type:
        case "major":
            new_version = Version(f'{".".join([str(new_version.major + 1), "0", "0"])}')
        case "minor":
            new_version = Version(
                f'{".".join([str(new_version.major), str(new_version.minor + 1), "0"])}'
            )
        case "patch":
            if pyproject_version.pre and prerelease:
                new_version = Version(
                    f'{".".join([str(new_version.major), str(new_version.minor), str(new_version.micro)])}{new_version.pre[0]}{new_version.pre[1] + 1}'
                )
            else:
                new_version = Version(
                    f'{".".join([str(new_version.major), str(new_version.minor), str(new_version.micro + 1)])}'
                )
    if prerelease and not new_version.pre:
        new_version = Version(
            f"{new_version}{new_version.pre[0] or 'a' if new_version.pre else 'a'}{new_version.pre[1] + 1 if new_version.pre else 1}"
        )

    if new_version != pyproject_version:
        print(f"Updating version from {pyproject_version} to {new_version}")
        pyproject_content = re.sub(
            r'version = "(.+)"',
            f'version = "{new_version}"',
            pyproject_content,
        )
        pathlib.Path("pyproject.toml").write_text(pyproject_content)
        d3ploy_content = pathlib.Path("d3ploy/d3ploy.py").read_text()
        d3ploy_content = re.sub(
            r'VERSION = "(.+)"',
            f'VERSION = "{new_version}"',
            d3ploy_content,
        )
        pathlib.Path("d3ploy/d3ploy.py").write_text(d3ploy_content)


if __name__ == "__main__":
    main()
