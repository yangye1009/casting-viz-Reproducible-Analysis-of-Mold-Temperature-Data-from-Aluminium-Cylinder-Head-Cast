"""Production-shift segmentation (thesis Programs 13 and 17).

Original version::

    delta_T = df['TIME'].diff()
    t = df.sort_values(by='delta_T')[897:902]     # five largest gaps, by position
    ...
    shift1 = df[...].loc[1:65]                     # boundaries typed by hand
    shift5 = df[...].loc[279:358]

The boundaries were found once and then hard-coded as row numbers, so the
script only worked for this one file. Here a shift is defined as a run of
records with no gap longer than ``shift_gap``; boundaries are recomputed for
any input.
"""
from __future__ import annotations

import pandas as pd


def assign_shifts(times: pd.Series, gap: str | pd.Timedelta = "30min") -> pd.Series:
    """Label each timestamp with a 1-based shift number.

    A new shift starts whenever the time since the previous record exceeds *gap*.
    *times* must be sorted ascending.
    """
    if not times.is_monotonic_increasing:
        raise ValueError("times must be sorted ascending")
    breaks = times.diff() > pd.Timedelta(gap)
    return (breaks.cumsum() + 1).astype(int).rename("SHIFT")


def shift_summary(df: pd.DataFrame, shift_col: str = "SHIFT") -> pd.DataFrame:
    """One row per shift: start, end, records, duration and pause before it.

    Reproduces thesis Table 6, but separates the working time of a shift from
    the pause between shifts (the original 'shift duration' included the pause).
    """
    g = df.groupby(shift_col)["TIME"]
    summary = pd.DataFrame({
        "start": g.min(),
        "end": g.max(),
        "n_records": g.size(),
    })
    summary["cumulative_records"] = summary["n_records"].cumsum()
    summary["duration"] = summary["end"] - summary["start"]
    summary["pause_before"] = summary["start"] - summary["end"].shift()
    return summary
