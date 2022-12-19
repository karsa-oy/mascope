# -*- coding: utf-8 -*-
"""
Created on Mon Dec  5 10:10:08 2022

@author: Oskari Kausiala
"""

import argparse
import asyncio
import pandas as pd

from backend.api.scenthound import process_sample
from backend.db.conn import conn


def parse_cmd_args():
    """
    Parse command line arguments
    ------------------------------
    Return dict
    Default argument values: see default_args.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-b", "--batch_id",
        help="sample batch id",
        type=str, required=True
    )
    all_args = parser.parse_args()
    cmdline_args = {}
    for arg in vars(all_args):
        if vars(all_args)[arg] is None:
            continue
        cmdline_args[arg] = vars(all_args)[arg]
    return cmdline_args



if __name__ == '__main__':
    args = parse_cmd_args()
    sample_batch_id = args['batch_id']
    
    with conn:
        sample_item_df = pd.read_sql("""
            SELECT
                sample_item_id,
                sample_batch_id,
                filename
            FROM sample_item
            WHERE sample_batch_id == ?
            """,
            conn,
            params=[sample_batch_id]
        )

    loop = asyncio.get_event_loop()
    for i, sample_item in sample_item_df.iterrows():
        print(f"Processing {((i)/len(sample_item_df)):.2f}")
        loop.run_until_complete(
            process_sample(
                sample_item
            )
        )
    print("Completed!")