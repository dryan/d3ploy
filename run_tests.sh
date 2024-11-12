#! /usr/bin/env bash

set -e

uv run coverage erase
uv run coverage run --source='d3ploy' tests/test.py "$@"
uv run coverage html
uv run coverage report --fail-under=100 --skip-covered
