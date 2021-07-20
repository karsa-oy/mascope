#!/bin/bash
# ================================================================
# Run karsa services on linux desktop
#
set -eu -o pipefail

#set -x
#trap read debug

cd
xterm -e --hold karsa-router-services --url 0.0.0.0
xterm -e --hold karsa-fileio-services --ns TofDaq

# commented out, since karsa-raw-streamer currently fails on linux: TofDaq dependency to be removed
# xterm -e --hold karsa-raw-streamer --config=/vagrant/src/services/services/raw_streamer_config/h5.yaml
# xterm -e --hold karsa-raw-streamer --config=/vagrant/src/services/services/raw_streamer_config/raw.yaml
# xterm -e --hold karsa-fileio-services --ns=H5Data
# xterm -e --hold karsa-fileio-service --ns=OrbitrapData || goto :error
# sleep 7

xterm -e --hold karsa-sample-services
xterm -e --hold karsa-dataviz-services
