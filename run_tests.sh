#! /usr/bin/env bash

pipenv run coverage erase
pipenv run coverage run --source='d3ploy' tests/test.py "$@"
pipenv run coverage html
pipenv run coverage report --fail-under=100 --skip-covered
