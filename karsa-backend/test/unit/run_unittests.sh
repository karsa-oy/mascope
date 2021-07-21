#!/bin/bash
# ================================================================
# Run unittests
#
set -eu -o pipefail

#set -x
#trap read debug

my_folder=$(dirname $(realpath $BASH_SOURCE))

pushd $my_folder
python3 -m unittest discover -v
popd
