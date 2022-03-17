#!/bin/bash

# use this to create the python virtual environment and install the vidlog
# module for development ("editing").

# This allows edit in place.
# you can remove the virtual environment by deleting the `venv` directory.
# be sure to deactivate first

PYTHON=venv/bin/python

if [ ! -d venv ]; then
    python3 -m venv venv
    $PYTHON -m pip install -U pip wheel setuptools
    $PYTHON -m pip install -e .
fi
