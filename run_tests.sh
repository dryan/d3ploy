#! /usr/bin/env bash

poetry run coverage erase
poetry run coverage run --source='d3ploy' tests/test.py "$@"
poetry run coverage html
poetry run coverage report --fail-under=100 --skip-covered
