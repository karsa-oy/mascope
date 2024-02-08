import argparse
import re
import os
import glob
import csv
from copy import deepcopy
from .ht3000a import dup_cycles, parse_csv_report


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", help="autosampler log file", type=str, required=True)
    parser.add_argument("-o", "--output", help="resulting batch import cvs file", type=str, required=True)
    parser.add_argument("-p", "--project", default=None, help="project name", type=str)
    parser.add_argument("-e", "--experiment", default=None, help="experiment name", type=str)
    parser.add_argument("-t", "--datetime", help="datetime token (e.g. filename or just YYYY.mm.dd-HHhMMmSSs) for sample search", type=str, required=True)
    parser.add_argument("-d", "--data_pool_path", help="path to H5Data structured data pool for sample search", type=str, required=True)
    return parser.parse_args()

def get_datetime_tokens(sample_fname):
    # returns (dir_token ('YYYY.mm.dd'), file_token ('YYYY_mm_dd_HH_MM_SS'))
    dt_regex = r'.*(\d{4}).(\d{2}).(\d{2}).(\d{2}).(\d{2}).(\d{2}).*'
    dt = re.findall(dt_regex, sample_fname)[0]
    return '.'.join(dt[0:3]), '_'.join(dt)

def get_filenames(search_dir, dir_token, file_token, n_files):
    dirs = list(filter(
            lambda x: os.path.basename(x) >= dir_token,
            glob.glob(os.path.join(search_dir, '20[0-9][0-9].[0-1][0-9].[0-3][0-9]')) ))
    dirs.sort()
    filenames = []
    while len(filenames) < n_files:
        if not dirs:
            break
        the_dir = dirs.pop(0)
        files = list(filter(
            lambda x: get_datetime_tokens(x)[1] >= file_token, 
            glob.glob(os.path.join(the_dir, '*.h5'))))
        files.sort()
        filenames = [*filenames, *files]
    filenames = filenames[0:n_files]
    filenames = [os.path.basename(fn) for fn in filenames]
    return filenames

def assert_non_empty_values(dic, keys):
    for k in keys:
        assert dic[k], f"Missing key: {k} in sample {d}"


def run():
    args = parse_args()
    with open(args.input) as f:
        data = parse_csv_report(f)
        data = dup_cycles(data)

    dir_token, file_token = get_datetime_tokens(args.datetime)
    filenames = get_filenames(args.data_pool_path, dir_token, file_token, len(data))
    assert len(filenames)==len(data), f"Error: not enough samples in {args.data_pool_path} : ({len(filenames)} of {len(data)})"

    res = []
    columns = []    # keep order; some records may miss some keys;
    for d, fn in zip(data, filenames):
        d['title'] = d.get('Sample name')
        d['project'] = d.get('project') or args.project
        d['experiment'] = d.get('experiment') or args.experiment
        d['filename'] = fn
        assert_non_empty_values(d, ['filename', 'title', 'project', 'experiment'])
        for i, c in enumerate(d.keys()):
            try:
                i = columns.index(c)
            except ValueError:      # no such title in columns yet
                columns.insert(i, c)
        res.append(deepcopy(d))

    with open(args.output, 'w', encoding='utf8', newline='') as f:
        writer = csv.DictWriter(f, columns)
        writer.writeheader()
        writer.writerows(res)


if __name__ == '__main__':
    run()
