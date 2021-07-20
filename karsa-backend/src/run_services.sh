#!/bin/bash
# ================================================================
# Run karsa services on linux desktop
#
set -eu -o pipefail

#set -x
#trap read debug

cd
echo running karsa-router-service
xterm -hold -e karsa-router-service --url 0.0.0.0 &

echo running karsa-fileio-service
rm -rf FileIo_*.db
xterm -hold -e karsa-fileio-service --ns TofDaq &

echo running karsa-sample-service
xterm -hold -e karsa-sample-service &

sleep 10

echo running karsa-dataviz-service
rm -rf DataViz_*.db
xterm -hold -e karsa-dataviz-service &

# commented out, since karsa-raw-streamer currently fails on linux: TofDaq dependency to be removed
# xterm -hold -e karsa-raw-streamer --config=/vagrant/src/services/services/raw_streamer_config/h5.yaml
# xterm -hold -e karsa-raw-streamer --config=/vagrant/src/services/services/raw_streamer_config/raw.yaml
# xterm -hold -e karsa-fileio-service --ns=H5Data
# xterm -hold -e karsa-fileio-service --ns=OrbitrapData || goto :error
# sleep 7
