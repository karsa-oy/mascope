#!/usr/bin/env bash

karsa-router-service --url 0.0.0.0 & \
karsa-fileio-service --ns TofDaq & \
karsa-sample-service & \
karsa-signal-service & \
sleep 10 & \
rm -rf DataViz_*.db & \
karsa-dataviz-service & \
wait