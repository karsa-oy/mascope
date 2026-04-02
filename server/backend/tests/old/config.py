import glob
import os


TEST_SERVER_URL = "http://localhost:8080/"
# time limit for server start
START_TIMEOUT = 5
# Time limit for file convertion to complete, tof needs 150 max
CONVERTION_TIMEOUT = 500

# Path to the test data folder
BASE_PATH = r"\\192.168.1.44\share\Data\mascope_test_data"

WATCH_PATH = os.path.join(BASE_PATH, "for_convertion")
DATA_PATH = os.path.join(BASE_PATH, "raw_data")
CONVERTED_FILES_PATH = os.path.join(BASE_PATH, "test_instrument")
TARGETS_PATH = os.path.join(BASE_PATH, "targets.json")
RES_FUNCTIONS_PATH = os.path.join(BASE_PATH, "resolution_functions.json")
LOG_PATH = os.path.join(BASE_PATH, "reports")

# Get list of test files
file_dict = {
    "Raw": glob.glob(os.path.join(DATA_PATH, "KORBI2", "positive_polarity", "*.raw"))
    + glob.glob(os.path.join(DATA_PATH, "KORBI2", "negative_polarity", "*.raw")),
    "H5": glob.glob(os.path.join(DATA_PATH, "KLTOF1", "positive_polarity", "*.h5"))
    + glob.glob(os.path.join(DATA_PATH, "KLTOF1", "negative_polarity", "*.h5")),
}
