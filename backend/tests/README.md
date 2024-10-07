# General info

Tests are stored in the `backend/tests` folder. If the Python test file is not specified, every function with a name starting with "test_" will be run. 

# Run tests

To run the peak detection testing, from the `Mascope\backend` folder type in the terminal:

> pytest --log-cli-level=INFO tests/test_peak_fitting.py

`--log-cli` flag is required for showing logger messages.

Another way to run tests is to use the built-in VS Code [testing module](https://code.visualstudio.com/docs/python/testing). In this case, command line arguments can be set up in VS Code settings in a workspace. Search `@id:python.testing.pytestArgs pytest` in settings and add the `--log-cli-level=INFO` item.

# !!Everything below is deprecated!!

Currently, the signal processing pipeline is tested:
* File conversion: all files are converted within the plausible time frame
* Spectra fitting: the fitting process is completed and there are some peaks found
* Matching: found matches match to true matches (same ions discovered)

# Test server

Testing requires the Mascope test server to be running.
All necessary files are in the folder `Mascope\scripts\deploy\dev.win`:
* Edit variables in `.test_env`
* Run `deploy_test.cmd` to launch the test server

# Test dataset

The test dataset can be found on the NAS drive `192.168.1.44` in the folder `Data\mascope_test_data`.
It is possible to use the folder on the NAS drive directly.
However, the testing process is much faster with a local drive.

# Configuration

Prior to testing update variables in the configuration file `Mascope\backend\tests\config.py`.
The list of testing files can be edited there as well if it needs to be shortened for quicker testing.

# Run tests

To start testing, from the `Mascope\backend` folder run in the terminal:

> poetry run python tests/run.py

# Logging

The logs are available in the folder `mascope_test_data\reports` upon test completion.
