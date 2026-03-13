"""High-level data loading functions for the Mascope SDK."""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Any

import pandas as pd
from loguru import logger
from tqdm import tqdm

if TYPE_CHECKING:
    from .client import MascopeClient


def load_peaks(
    client: MascopeClient,
    workspace: str,
    batches: str | None = None,
    *,
    matches: bool = True,
    areas: bool = True,
    heights: bool = True,
    average: bool = True,
    max_workers: int = 8,
) -> pd.DataFrame | None:
    """Load peaks for all samples across one or more batches.

    Handles the typical workflow of selecting a workspace, filtering batches
    by name, iterating all samples, and concatenating peak data into a single
    DataFrame enriched with batch and sample metadata.

    Requests are made concurrently for better performance. A progress bar is
    displayed during loading.

    :param client: The MascopeClient instance.
    :type client: MascopeClient
    :param workspace: Workspace name (or substring) or workspace ID.
    :type workspace: str
    :param batches: Optional substring filter on batch names (case-insensitive).
                    If not provided, all batches in the workspace are loaded.
    :type batches: str, optional
    :param matches: Include matched compounds/ions/isotopes. Defaults to True.
    :type matches: bool
    :param areas: Include peak areas. Defaults to True.
    :type areas: bool
    :param heights: Include peak heights. Defaults to True.
    :type heights: bool
    :param average: Return averaged data across time. Defaults to True.
    :type average: bool
    :param max_workers: Maximum number of concurrent requests. Defaults to 8.
    :type max_workers: int
    :return: A DataFrame containing all peaks enriched with columns:

             - ``sample_batch_name``: Name of the batch the sample belongs to
             - ``sample_item_name``: Name of the sample
             - ``sample_item_utc_created``: Timestamp of the sample

             Plus all columns from :meth:`~mascope_sdk.resources.samples.SamplesResource.get_peaks`.
             Returns None if no peaks are found.
    :rtype: pd.DataFrame | None
    :raises ValueError: If the workspace or batches cannot be resolved.

    Example::

        mascope = MascopeClient()

        # Load all peaks from batches containing "Uronium"
        peaks = mascope.load_peaks(
            workspace="My Workspace",
            batches="Uronium",
        )

        # Chronological timeseries per compound
        peaks.sort_values("sample_item_utc_created").groupby(
            "target_compound_formula"
        )["area"].sum()

        # Load all peaks from all batches
        peaks = mascope.load_peaks(workspace="My Workspace")
    """
    # Resolve workspace
    from ._resolve import resolve_id

    workspaces = client.workspaces.list()
    workspace_id = resolve_id(
        workspace,
        workspaces,
        id_column="workspace_id",
        name_column="workspace_name",
        entity_label="workspace",
    )
    logger.info("Loading workspace '{}'", workspace)

    # Get batches
    all_batches = client.batches._list_by_id(workspace_id)
    if all_batches is None or all_batches.empty:
        logger.warning("No batches found in workspace")
        return None

    # Filter batches by name
    if batches is not None:
        all_batches = all_batches[
            all_batches["sample_batch_name"].str.contains(batches, case=False, na=False)
        ]
        if all_batches.empty:
            logger.warning("No batches matching '{}'", batches)
            return None

    batch_names = all_batches["sample_batch_name"].tolist()
    logger.info("Found {} batch(es): {}", len(all_batches), batch_names)

    # Collect all (sample_row, batch_name) pairs across batches
    sample_tasks: list[tuple[Any, str]] = []
    for _, batch_row in all_batches.iterrows():
        batch_id = batch_row["sample_batch_id"]
        batch_name = batch_row["sample_batch_name"]

        samples = client.samples._list_by_id(batch_id)
        if samples is None or samples.empty:
            logger.info("Batch '{}': no samples, skipping", batch_name)
            continue

        logger.info("Batch '{}': {} sample(s)", batch_name, len(samples))
        for _, sample_row in samples.iterrows():
            sample_tasks.append((sample_row, batch_name))

    if not sample_tasks:
        logger.warning("No samples found")
        return None

    # Load peaks concurrently with progress bar
    def _fetch_peaks(sample_row: Any, batch_name: str) -> pd.DataFrame | None:
        sample_id = sample_row["sample_item_id"]
        peaks = client.samples.get_peaks(
            sample_id,
            matches=matches,
            areas=areas,
            heights=heights,
            average=average,
        )
        if peaks is None or peaks.empty:
            return None

        # Enrich with batch and sample context
        peaks.insert(0, "sample_batch_name", batch_name)
        peaks.insert(
            peaks.columns.get_loc("sample_item_id") + 1,
            "sample_item_name",
            sample_row["sample_item_name"],
        )
        if "sample_item_utc_created" in sample_row.index:
            peaks.insert(
                peaks.columns.get_loc("sample_item_name") + 1,
                "sample_item_utc_created",
                sample_row["sample_item_utc_created"],
            )
        return peaks

    frames: list[pd.DataFrame] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_fetch_peaks, sample_row, batch_name): sample_row
            for sample_row, batch_name in sample_tasks
        }
        with tqdm(
            total=len(futures),
            desc="Loading peaks",
            unit="sample",
            file=sys.stderr,
            bar_format="{l_bar}{bar:30}{r_bar}",
            colour="green",
        ) as pbar:
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    frames.append(result)
                pbar.update(1)

    if not frames:
        logger.warning("No peaks found")
        return None

    result = pd.concat(frames, ignore_index=True)
    logger.info("Loaded {} peaks total", len(result))
    return result
