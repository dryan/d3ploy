#! /bin/bash

poetry run python setup.py clean
poetry run python setup.py sdist
poetry run twine upload dist/*
rm -r dist
