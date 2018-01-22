#! /bin/bash

pandoc --from=markdown --to=rst --output=README.rst README.md
python setup.py clean
python setup.py sdist
twine upload dist/*
rm README.rst
rm -r dist
