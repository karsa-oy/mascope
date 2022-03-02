import json
import os

from karsalib.util import parse_datetime_from_item_filename
from karsalib.db import SampleManagerDB

db_path = 'test.db' # Path to SampleManager database
db = SampleManagerDB(db_path)

path = '.'
# instrument_dirs = next( os.walk(path) )[1]
instrument_dirs = ['TofDaq'] # List of all instrument directories to walk through

if __name__ == '__main__':
    samples = []
    # Loop through directories in root, assumed to be named by instrument
    for instrument_dir in instrument_dirs:
        instrument_dir_path = os.path.join(path, instrument_dir)
        # Loop through datetime dirs inside
        dt_dirs = next( os.walk(instrument_dir_path) )[1]
        for dt_dir in dt_dirs:
            dt_dir_path = os.path.join(instrument_dir_path, dt_dir)
            sample_dirs = next( os.walk(dt_dir_path) )[1]
            for sample_dir in sample_dirs:
                props_path = os.path.join(dt_dir_path, sample_dir, '.props')
                with open(props_path, 'r') as f:
                    props = json.load(f)
                sample = dict(
                    filename = props['filename'],
                    instrument = props['filename'].split('_')[0],
                    datetime = parse_datetime_from_item_filename(props['filename']).isoformat(),
                    length=props['length'],
                    range=json.dumps(props['range'])
                )
                samples.append(sample)
                # Make database record
                db.sample_file_insert(**sample)
    print(samples)