@echo off

pushd router_service\router_service
:: start Router locally, if not already running
powershell Test-NetConnection 127.0.0.1 -p 5010 | find /i "failed" && start cmd /k python Router.py
popd

pushd tof_service\tof_service
start cmd /k python TOFService.py
popd

pushd services\services
start cmd /k python FileService.py
start cmd /k python DataVizService.py
::start cmd /k python SignalProcessorService.py
popd
