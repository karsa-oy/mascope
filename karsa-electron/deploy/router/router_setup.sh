#!/bin/bash

## The script sets up python Router service

set -eu -o pipefail

echo AAA Set up Karsa Router service...


my_folder=$(dirname $(realpath $BASH_SOURCE))
pushd $my_folder

python3 -m pip install -r router_requirements.txt

popd
exit 0
