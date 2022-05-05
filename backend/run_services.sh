#!/bin/bash
# ================================================================
# Run karsa services on linux desktop
#
set -eu -o pipefail

#set -x
#trap read debug

cd
echo Set MASCOPE_DATADIR for karsa services
export MASCOPE_DATADIR="/data"

echo running karsa-router-service
xterm -hold -e "karsa-router-service --url 0.0.0.0; bash" &

echo running karsa-fileio-service
rm -rf FileIo_*.db
xterm -hold -e "karsa-fileio-service --ns TofDaq; bash" &

echo running karsa-sample-service
xterm -hold -e "karsa-sample-service; bash" &

echo running karsa-signal-service
xterm -hold -e "karsa-signal-service; bash" &

sleep 10

echo running karsa-dataviz-service
rm -rf DataViz_*.db
xterm -hold -e "karsa-dataviz-service; bash" &

# commented out, since karsa-file-streamer currently fails on linux: TofDaq dependency to be removed
# xterm -hold -e "karsa-file-streamer --config=/vagrant/src/services/services/file_streamer_config/h5.yaml --transit; bash" &
# xterm -hold -e "karsa-file-streamer --config=/vagrant/src/services/services/file_streamer_config/raw.yaml --transit; bash" &
# xterm -hold -e "karsa-fileio-service --ns=H5Data; bash" &
# xterm -hold -e "karsa-fileio-service --ns=OrbitrapData; bash" &
# sleep 7
