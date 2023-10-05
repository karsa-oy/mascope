import asyncio
import os
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv

from backend.db.conn import conn
from backend.lib.peak import detect_peaks, get_peaks
from backend.server import sio

load_dotenv()

# === sample batches === #


async def export_peaks(sample_batch_df, sample_item_df):
    peak_data = []
    [sample_batch_name] = sample_batch_df["sample_batch_name"].tolist()
    for index, row in sample_item_df.iterrows():
        try:
            sample_file = await detect_peaks(
                row["filename"], u_list=None, if_exists="append"
            )
            peak_data_item = get_peaks(sample_file, "area").sum(dim="time")
        except Exception as e:
            print(repr(e))
            continue
        peak_data.extend(
            [
                (
                    sample_batch_name,
                    row["sample_item_name"],
                    row["sample_item_type"],
                    row["filter_id"],
                    row["filename"],
                    peak.mz.item(),
                    peak.item(),
                )
                for peak in peak_data_item
            ]
        )
    batch_peak_df = pd.DataFrame.from_records(
        peak_data,
        columns=(
            "batch name",
            "sample name",
            "sample type",
            "filter id",
            "filename",
            "mz",
            "intensity",
        ),
    )

    dt_str = datetime.now().isoformat().replace("-", "").replace(":", "").split(".")[0]

    peakfile_path = os.environ.get("MASCOPE_PRIVATE_DATADIR", ".")
    peakfile_filename = (
        dt_str + "_peaks_" + sample_batch_name.replace(" ", "_") + ".parquet"
    )
    print(f"Writing peak data to file {peakfile_filename}")
    batch_peak_df.to_parquet(
        os.path.join(peakfile_path, peakfile_filename), index=False
    )
    print("Write complete")


@sio.event(namespace="/")
async def sample_batch_export_peaks(sid, sample_batch_id):
    with conn:
        # batch data
        sample_batch_df = pd.read_sql(
            f"""
            SELECT
                sample_batch_name
            FROM sample_batch
            WHERE sample_batch_id == ?
            """,
            conn,
            params=[sample_batch_id],
        )
        # sample item data
        sample_item_df = pd.read_sql(
            f"""
            SELECT
                filename,
                sample_item_name,
                sample_item_type,
                filter_id
            FROM sample_item
            WHERE sample_batch_id == ?
            """,
            conn,
            params=[sample_batch_id],
        )
    task = sio.start_background_task(export_peaks, sample_batch_df, sample_item_df)
    try:
        await asyncio.gather(task)
        await sio.emit("sample_batch_export_peaks_ready", room=sid, namespace="/")
    except Exception as e:
        await sio.emit(
            "sample_batch_export_peaks_failed", repr(e), room=sid, namespace="/"
        )
