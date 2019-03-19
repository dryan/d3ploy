#! /bin/bash

pandoc --from=markdown --to=rst --output=README.rst README.md
pipenv python setup.py clean
pipenv python setup.py sdist
twine upload dist/*
rm README.rst
rm -r dist
