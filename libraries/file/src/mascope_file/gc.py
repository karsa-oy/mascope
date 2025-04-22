import os
import shutil

from mascope_file.runtime import runtime


def instrument_dirs() -> list[str]:
    """
    Get a list of all instrument directories in the filestore.

    :return: A list of absolute paths to all instrument directories
    :rtype: list[str]
    """
    root = runtime.filestore()
    paths = [os.path.join(root, item) for item in os.listdir(root)]
    return [path for path in paths if os.path.isdir(path)]


def gc_filestore() -> None:
    """
    Garbage collection for the filestore.

    Removes empty directories in the filestore by:
    1. Checking all instrument directories
    2. Removing any empty subdirectories within each instrument directory
    3. Removing any instrument directories that become empty after step 2

    :return: None
    :rtype: None
    """
    # check all intrument directories
    for instrument_dir in instrument_dirs():
        # check each item in the instrument directory
        for item in os.listdir(instrument_dir):
            item_path = os.path.join(instrument_dir, item)
            # if its an empty directory, remove it
            if os.path.isdir(item_path) and not os.listdir(item_path):
                runtime.logger.info(f"Removing empty filestore directory: {item_path}")
                shutil.rmtree(item_path)
        # after removing empty subfolders, check if instrument dir is empty
        if not os.listdir(instrument_dir):
            # remove the instrument dir if it's empty:
            runtime.logger.info(f"Removing empty filestore directory: {instrument_dir}")
            shutil.rmtree(instrument_dir)
