"""Data cleaning (thesis Programs 4, 5, 7 and 10).

Original version::

    df['T1'][df['T1'] > 720] = None      # Program 5

This is *chained assignment*. Since pandas 3.0 (Copy-on-Write) it silently
modifies a temporary copy, so the 32767 overflow values were never removed.
Here invalid readings are replaced with ``DataFrame.mask`` in a single step.

Programs 7 and 10 dropped columns after visual inspection; that decision is
now made by a reproducible rule (coefficient of variation) and reported.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import MOLD_TEMPS, AnalysisConfig


def invalid_mask(df: pd.DataFrame, cfg: AnalysisConfig,
                 cols: list[str] = MOLD_TEMPS) -> pd.DataFrame:
    """Boolean mask of physically impossible mold-temperature readings."""
    values = df[cols]
    return values.eq(cfg.sensor_overflow) | values.gt(cfg.max_plausible_mold_t) | values.le(0)


def quality_report(df: pd.DataFrame, cfg: AnalysisConfig,
                   by: str = "MOLD", cols: list[str] = MOLD_TEMPS) -> pd.DataFrame:
    """Count overflow / out-of-range readings per *by* group and sensor.

    Answers *where* the bad data come from, e.g. whether a single
    thermocouple on a single mold is responsible.
    """
    overflow = df[cols].eq(cfg.sensor_overflow)
    out_of_range = invalid_mask(df, cfg, cols) & ~overflow

    long = pd.DataFrame({
        by: np.repeat(df[by].to_numpy(), len(cols)),
        "sensor": np.tile(cols, len(df)),
        "overflow_32767": overflow.to_numpy().ravel(),
        "out_of_range": out_of_range.to_numpy().ravel(),
    })
    report = (long.groupby([by, "sensor"])
                  .agg(n_records=("sensor", "size"),
                       overflow_32767=("overflow_32767", "sum"),
                       out_of_range=("out_of_range", "sum"))
                  .reset_index())
    report["valid"] = report["n_records"] - report["overflow_32767"] - report["out_of_range"]
    report["valid_ratio"] = (report["valid"] / report["n_records"]).round(3)
    return report


def clean_mold_temps(df: pd.DataFrame, cfg: AnalysisConfig,
                     cols: list[str] = MOLD_TEMPS) -> pd.DataFrame:
    """Return a copy in which invalid mold temperatures are NaN."""
    out = df.copy()
    out[cols] = out[cols].mask(invalid_mask(out, cfg, cols)).astype(float)
    return out


def near_constant_columns(df: pd.DataFrame, cols: list[str],
                          cv_threshold: float) -> pd.DataFrame:
    """Coefficient of variation (std / |mean|) for each column, with a verdict.

    Replaces the visual judgement of Program 6 ("these curves look flat").
    """
    present = [c for c in cols if c in df.columns]
    stats = df[present].agg(["mean", "std", "min", "max"]).T
    stats["cv"] = stats["std"] / stats["mean"].abs().replace(0, np.nan)
    stats["cv"] = stats["cv"].fillna(0.0)
    stats["near_constant"] = stats["cv"] < cv_threshold
    return stats.round(4)
