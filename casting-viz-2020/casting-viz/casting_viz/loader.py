"""Load raw foundry data (thesis Programs 1-3).

Original version::

    df = pd.read_excel("C:/Users/fengs/Desktop/2020.xlsx", parse_dates=['日期与时间'])
    df.rename(columns={...}, inplace=True)

Improvements: path is a parameter, both Excel and CSV are accepted, header
whitespace is normalised, required columns are validated, and records are
sorted chronologically so that time differences are always meaningful.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import COLUMN_MAP, MOLD_TEMPS

REQUIRED = ["TIME", "MOLD", "OPER", *MOLD_TEMPS]


def load_raw(path: str | Path) -> pd.DataFrame:
    """Read an Excel/CSV export and return a tidy DataFrame with English columns."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    elif suffix == ".csv":
        df = pd.read_csv(path, encoding="utf-8-sig")
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    return standardise(df)


def standardise(df: pd.DataFrame) -> pd.DataFrame:
    """Rename Chinese headers, parse timestamps, sort by time."""
    df = df.copy()
    df.columns = [str(c).replace(" ", "").strip() for c in df.columns]
    df = df.rename(columns=COLUMN_MAP)

    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns after renaming: {missing}")

    df["TIME"] = pd.to_datetime(df["TIME"])
    numeric = df.columns.drop("TIME")
    df[numeric] = df[numeric].apply(pd.to_numeric, errors="coerce")

    return df.sort_values("TIME", kind="stable").reset_index(drop=True)
