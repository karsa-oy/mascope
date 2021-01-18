#!/bin/bash

## The script runs python Router service

set -eu -o pipefail

echo AAA Starting Karsa Router service...


my_folder=$(dirname $(realpath $BASH_SOURCE))
pushd $my_folder/../..

python3 py_code/Router.py

popd
exit 0
