"""Correlation analysis (thesis Programs 8 and 19).

Original version::

    dfData = abs(df.corr())
    sns.heatmap(dfData, annot=True, vmax=1, square=True, cmap="Blues")

Three issues are fixed here:

1. ``abs()`` discards the sign, so the heatmap cannot show whether a
   relation is positive or negative (yet the thesis concluded "positive").
   Signed coefficients are kept and drawn on a diverging colour map.
2. Mold code, operator id, furnace id and shift code are *nominal* labels.
   A Pearson coefficient between "mold 8 / 13 / 16" and a temperature depends
   on the arbitrary numbering. The correlation ratio η (eta) is used instead:
   the share of temperature variance explained by the grouping (η² = R² of a
   one-way ANOVA), which is independent of how the labels are numbered.
3. Since pandas 2.0, ``df.corr()`` raises on a datetime column; numeric
   columns are now selected explicitly.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def signed_corr(df: pd.DataFrame, cols: list[str], method: str = "spearman") -> pd.DataFrame:
    """Signed correlation matrix over *cols* (pairwise, NaN-aware)."""
    return df[cols].corr(method=method, numeric_only=True)


def correlation_ratio(categories: pd.Series, values: pd.Series) -> float:
    """η = sqrt(SS_between / SS_total) for a nominal *categories* vs numeric *values*.

    Returns 0 when the group means are identical and 1 when the categories
    fully determine the values. NaN values are ignored.
    """
    frame = pd.DataFrame({"g": categories, "y": values}).dropna()
    if frame.empty or frame["y"].var(ddof=0) == 0:
        return float("nan")
    grand_mean = frame["y"].mean()
    grouped = frame.groupby("g")["y"]
    ss_between = (grouped.size() * (grouped.mean() - grand_mean) ** 2).sum()
    ss_total = ((frame["y"] - grand_mean) ** 2).sum()
    return float(np.sqrt(ss_between / ss_total))


def eta_table(df: pd.DataFrame, cat_cols: list[str], value_cols: list[str]) -> pd.DataFrame:
    """η for every (categorical code, numeric variable) pair."""
    table = pd.DataFrame(index=cat_cols, columns=value_cols, dtype=float)
    for c in cat_cols:
        for v in value_cols:
            table.loc[c, v] = correlation_ratio(df[c], df[v])
    return table.round(3)


def spearman_with_p(x: pd.Series, y: pd.Series) -> tuple[float, float, int]:
    """Spearman ρ, two-sided p-value and sample size, ignoring NaN pairs."""
    pair = pd.concat([x, y], axis=1).dropna()
    if len(pair) < 3:
        return float("nan"), float("nan"), len(pair)
    rho, p = stats.spearmanr(pair.iloc[:, 0], pair.iloc[:, 1])
    return float(rho), float(p), len(pair)
