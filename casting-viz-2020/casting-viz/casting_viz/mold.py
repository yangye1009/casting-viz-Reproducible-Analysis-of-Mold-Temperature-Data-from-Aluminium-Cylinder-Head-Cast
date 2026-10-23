"""Single-mold analysis (thesis Programs 15, 16, 18 and 20).

Original issues fixed here:

* The cycle time was taken from ``df['TIME'].diff()`` and therefore included
  the pause between shifts (one "cycle" in shift 5 lasted 71 min). It is now
  computed per mold *within* each shift, so the first casting of a shift has
  no cycle time instead of an artificial one.
* Long cycles were overwritten by a fixed value
  (``shift5['cycletime'][... > 1000] = 600``). They are now *flagged* with a
  Tukey fence and excluded from correlation analysis, keeping the raw value.
* Per-shift statistics were produced by five copy-pasted ``describe()`` calls
  on hand-typed row ranges; one ``groupby`` now does it for any number of shifts.
* The mean of T1-T3 can be computed strictly (NaN if any sensor is missing,
  as in the thesis) or from the available sensors.
"""
from __future__ import annotations

import pandas as pd

from .config import MOLD_TEMPS


def add_mean_temp(df: pd.DataFrame, strict: bool = True,
                  cols: list[str] = MOLD_TEMPS) -> pd.DataFrame:
    """Add T_MEAN; *strict* requires all three sensors to be valid."""
    out = df.copy()
    out["T_MEAN"] = out[cols].mean(axis=1, skipna=not strict)
    return out


def temp_fluctuation(df: pd.DataFrame, cols: list[str] = MOLD_TEMPS) -> pd.DataFrame:
    """Level and record-to-record change of each sensor (thesis Program 15 / Table 7)."""
    level = df[cols].describe().T
    step = df[cols].diff().describe().T.add_prefix("step_")
    return pd.concat([level, step[["step_min", "step_max", "step_std"]]], axis=1).round(1)


def mold_cycles(df: pd.DataFrame, mold: int, shift_col: str = "SHIFT") -> pd.DataFrame:
    """Records of one mold with cycle index and cycle time inside each shift."""
    sub = df.loc[df["MOLD"] == mold].copy()
    if sub.empty:
        raise ValueError(f"No records for mold {mold}")
    grouped = sub.groupby(shift_col)
    sub["CYCLE_IDX"] = grouped.cumcount() + 1
    sub["CYCLE_S"] = grouped["TIME"].diff().dt.total_seconds()
    return sub


def flag_cycle_outliers(cycle_s: pd.Series, k: float = 3.0) -> pd.Series:
    """True for cycle times above Q3 + k*IQR (interruptions, not normal cycles)."""
    q1, q3 = cycle_s.quantile([0.25, 0.75])
    return cycle_s > q3 + k * (q3 - q1)


def per_shift_stats(sub: pd.DataFrame, shift_col: str = "SHIFT",
                    cols: list[str] = MOLD_TEMPS) -> pd.DataFrame:
    """Thesis Tables 8-12 in one table: temperature range/mean and cycle statistics."""
    agg: dict[str, tuple[str, str]] = {"n_castings": ("TIME", "size")}
    for c in cols:
        agg |= {f"{c}_min": (c, "min"), f"{c}_max": (c, "max"),
                f"{c}_mean": (c, "mean"), f"{c}_valid": (c, "count")}
    agg |= {"cycle_min_s": ("CYCLE_S", "min"), "cycle_median_s": ("CYCLE_S", "median"),
            "cycle_mean_s": ("CYCLE_S", "mean"), "cycle_max_s": ("CYCLE_S", "max")}
    return sub.groupby(shift_col).agg(**agg).round(1)


def sensor_offsets(sub: pd.DataFrame) -> pd.DataFrame:
    """Quantify the 'approximately constant temperature difference' between sensors."""
    diffs = pd.DataFrame({
        "T2 - T1": sub["T2"] - sub["T1"],
        "T1 - T3": sub["T1"] - sub["T3"],
        "T_MEAN - T1": sub["T_MEAN"] - sub["T1"] if "T_MEAN" in sub else pd.NA,
    })
    return diffs.describe().T[["count", "mean", "std", "min", "50%", "max"]].round(1)
