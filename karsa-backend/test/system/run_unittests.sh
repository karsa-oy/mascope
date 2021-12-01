#!/bin/bash
# ================================================================
# Run unittests
#
set -eu -o pipefail

#set -x
#trap read debug

my_folder=$(dirname $(realpath $BASH_SOURCE))

cd
xterm -hold -e python3 -m unittest discover -f -v -s $my_folder
