#! /bin/bash

uv run python setup.py clean
uv run python setup.py sdist
uv run twine upload dist/*
rm -r dist
