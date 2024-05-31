# Available tests

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
