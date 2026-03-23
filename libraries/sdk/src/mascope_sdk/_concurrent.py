"""Shared progress bar and concurrent execution helpers."""

import sys
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import Any, Callable, TypeVar

from tqdm import tqdm

#: Default tqdm keyword arguments used across the SDK.
_TQDM_DEFAULTS = {
    "file": sys.stderr,
    "bar_format": "{l_bar}{bar:30}{r_bar}",
    "colour": "green",
}

T = TypeVar("T")


def progress_bar(total: int, desc: str, unit: str = "it") -> tqdm:
    """Create a tqdm progress bar with the SDK's default styling."""
    return tqdm(total=total, desc=desc, unit=unit, **_TQDM_DEFAULTS)


def run_concurrent(
    func: Callable[..., T | None],
    tasks: list[tuple[Any, ...]],
    *,
    max_workers: int = 8,
    desc: str = "Processing",
    unit: str = "it",
) -> list[T]:
    """Execute *func* concurrently over *tasks* with a progress bar.

    Each element of *tasks* is an args-tuple unpacked into *func*.
    Returns a list of non-None results.

    On error, all pending futures are cancelled before re-raising so
    that ``ThreadPoolExecutor.shutdown(wait=True)`` does not block on
    futures that haven't started yet.
    """
    if max_workers > 8:
        raise ValueError("max_workers cannot exceed 8 to avoid overloading the API")

    if not tasks:
        return []

    results: list[T] = []
    futures: dict[Future[T | None], tuple[Any, ...]] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for args in tasks:
            futures[executor.submit(func, *args)] = args

        pbar = progress_bar(len(futures), desc=desc, unit=unit)
        try:
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    results.append(result)
                pbar.update(1)
        except BaseException:
            # Cancel remaining futures so shutdown() doesn't block
            for f in futures:
                f.cancel()
            raise
        finally:
            pbar.close()

    return results
