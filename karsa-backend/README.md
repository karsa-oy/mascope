### Description 
This project contains karsa-backend - Karsa Router and backend services.

Sources can be found here:
1. Karsa Router and backend services - https://gitlab.com/karsa_dev/karsa_msview/karsa-backend/


### Setup Requirements 
* > python 3.8 or conda


### Project setup

1) run development setup for the project

dev_setup.cmd

2) start all the backend services in dev.mode

run_services.cmd


### Project setup for linux
1) Have VirtualBox and vagrant installed

2) go to vbox\backend folder

cd vbox\backend

1) run development setup for the project in VirtualBox virtual environment

vagrant up


### Project profiling
1) py-spy profiler comes along with dev.setup: https://github.com/benfred/py-spy

py-spy record -o profile.svg --pid 12345


### Project testing
#### Unittesting
1) Unittests are located in test/unit directory

test\unit\run_unittests.cmd


### Compile and build distribution packages
1) from each service folder, run build.cmd: find .whl release package in dist folder

2) use pip to install release package locally
