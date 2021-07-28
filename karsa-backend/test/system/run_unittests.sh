#!/bin/bash
# ================================================================
# Run unittests
#
set -eu -o pipefail

#set -x
#trap read debug

my_folder=$(dirname $(realpath $BASH_SOURCE))

cd $my_folder
xterm -hold -e python3 -m unittest discover -v
