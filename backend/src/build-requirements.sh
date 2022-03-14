#!/usr/bin/env bash

# External and internal requirement separation
# is performed to optimize docker image builds

# This rebuilds `external-requirements.txt`
# It collects all external dependencies of Karsa's modules
# and combines them with any `extra-requirements.txt` specified

# pip-compile requires pip-tools and setuptools to run
pip-compile -o external-requirements.txt ./internal-requirements.txt ./extra-requirements.txt

# This removes Karsa internal dependencies from the generated file
sed -i '/^-e file/d' external-requirements.txt
sed -i '/^    # via -r .\/internal-requirements.txt/d' external-requirements.txt