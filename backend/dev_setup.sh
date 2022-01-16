#!/bin/bash
# ================================================================
# Run karsa development setup
#
set -eu -o pipefail

#set -x
#trap read debug

cd /vagrant/src

echo ========================
echo   2. Install karsalib package:
echo ========================
  python3 -m pip install --user -e karsalib

echo ========================
echo   3. Install hw_interfaces package:
echo ========================
  python3 -m pip install --user -e hw_interfaces

echo ========================
echo   4. Install karsaimg package:
echo ========================
  python3 -m pip install --user -e karsaimg

echo ========================
echo   5. Install scenthound package:
echo ========================
  python3 -m pip install --user -e scenthound

echo ========================
echo   6. Install backend services:
echo ========================
  python3 -m pip install --user -e router_service
  python3 -m pip install --user -e tof_service
  python3 -m pip install --user -e services

  python3 -m pip install --user py-spy

echo ========================
echo   7. Dev setup for backend is done.
echo 
echo   8. To start the services, run the script:
echo     ./run_services.sh
echo ========================
