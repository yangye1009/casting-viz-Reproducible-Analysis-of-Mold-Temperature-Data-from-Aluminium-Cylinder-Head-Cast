"""Figures (thesis Programs 6, 8, 9, 11, 12, 14, 16, 19, 20).

The original appendix contained ~450 lines of near-identical ``plt.subplot``
blocks, one per panel, with row ranges typed by hand. Each figure is now a
function that loops over sensors / groups / shifts, uses the object-oriented
matplotlib API (``fig, axes``), and returns the figure so it can be saved,
shown or tested.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from .config import MOLD_TEMPS

SENSOR_COLOURS = {"T1": "tab:red", "T2": "tab:green", "T3": "tab:blue", "T_MEAN": "black"}


def save(fig: plt.Figure, out_dir: Path, name: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.png"
    fig.savefig(path)
    return path


# --------------------------------------------------------------------------- #
# Chapter 6 – which variables matter?
# --------------------------------------------------------------------------- #
def process_params(df: pd.DataFrame, L: dict, cv: pd.Series | None = None) -> plt.Figure:
    """Program 6: melt temperature, cooling water and solidification time over time.

    If *cv* (coefficient of variation per column) is given, the largest CV of
    each panel is printed in its title, linking the figure to the drop rule.
    """
    panels = [
        (L["melt"], ["MELT_T"], L["temp"]),
        (L["cw_high"], ["CW1", "CW2", "CW3"], L["temp"]),
        (L["cw_low"], ["CW4", "CW5", "CW6", "CW7"], L["temp"]),
        (L["solid"], ["SOLID_TIME"], L["seconds"]),
    ]
    fig, axes = plt.subplots(len(panels), 1, figsize=(11, 9), sharex=True)
    for ax, (title, cols, ylabel) in zip(axes, panels):
        for c in cols:
            ax.plot(df["TIME"], df[c], lw=0.8, label=c)
        lo, hi = df[cols].min().min(), df[cols].max().max()
        pad = max(5.0, 0.5 * (hi - lo))          # show flatness on an honest scale
        ax.set_ylim(lo - pad, hi + pad)
        if cv is not None:
            title = f"{title}  (CV ≤ {100 * cv[cols].max():.2f} %)"
        ax.set(title=title, ylabel=ylabel)
        ax.legend(loc="upper right", ncol=len(cols), fontsize=8)
    axes[-1].set_xlabel(L["time"])
    fig.suptitle(L["process_title"], fontweight="bold")
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


def auxiliary_codes(df: pd.DataFrame, L: dict, shift_col: str = "SHIFT") -> plt.Figure:
    """Program 9: furnace id, shift code and running number over time.

    Production pauses found by the shift segmentation are shaded grey.
    """
    panels = [("FURNACE", L["furnace"], "crimson"),
              ("SHIFT_CODE", L["shift_code"], "goldenrod"),
              ("FLOW", L["flow"], "teal")]
    fig, axes = plt.subplots(len(panels), 1, figsize=(11, 7), sharex=True)
    pauses = []
    if shift_col in df:
        bounds = df.groupby(shift_col)["TIME"].agg(["min", "max"])
        pauses = list(zip(bounds["max"].iloc[:-1], bounds["min"].iloc[1:]))
    for ax, (col, title, colour) in zip(axes, panels):
        ax.step(df["TIME"], df[col], where="post", lw=0.8, color=colour)
        for start, end in pauses:
            ax.axvspan(start, end, color="grey", alpha=0.25, lw=0)
        ax.yaxis.get_major_locator().set_params(integer=True)
        ax.set(title=title, ylabel=col)
    axes[-1].set_xlabel(L["time"])
    fig.suptitle(L["codes_title"], fontweight="bold")
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


def data_quality(report: pd.DataFrame, L: dict, by: str = "MOLD") -> plt.Figure:
    """New: where do invalid readings come from? (mold x sensor)."""
    report = report.copy()
    report["key"] = report[by].astype(str) + " · " + report["sensor"]
    fig, ax = plt.subplots(figsize=(10, 4))
    x = np.arange(len(report))
    ax.bar(x, report["valid"], color="lightgrey", label=L["valid"])
    ax.bar(x, report["overflow_32767"], bottom=report["valid"],
           color="tab:red", label=L["overflow"])
    ax.bar(x, report["out_of_range"], bottom=report["valid"] + report["overflow_32767"],
           color="tab:orange", label=L["out_of_range"])
    ax.set_xticks(x, report["key"], rotation=45, ha="right")
    ax.set(ylabel=L["count"], xlabel=f"{L['mold']} · sensor", title=L["quality_title"])
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0))
    return fig


def correlation_overview(corr: pd.DataFrame, eta: pd.DataFrame, L: dict) -> plt.Figure:
    """Program 8, corrected: signed Spearman matrix + correlation ratio η for codes."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5),
                                   gridspec_kw={"width_ratios": [1.25, 1]})
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    sns.heatmap(corr, mask=mask, annot=True, fmt=".2f", vmin=-1, vmax=1, center=0,
                cmap="vlag", square=True, cbar_kws={"shrink": 0.7}, ax=ax1)
    ax1.set_title(L["corr_title"])
    sns.heatmap(eta, annot=True, fmt=".2f", vmin=0, vmax=1, cmap="Blues",
                cbar_kws={"shrink": 0.7}, ax=ax2)
    ax2.set_title(L["eta_title"])
    for ax in (ax1, ax2):
        ax.grid(False)
    fig.tight_layout()
    return fig


def temps_by_group(df: pd.DataFrame, group: str, L: dict) -> plt.Figure:
    """Programs 11 & 12: T1-T3 over time, one line per operator or mold."""
    group_label = L["oper"] if group == "OPER" else L["mold"]
    levels = sorted(df[group].dropna().unique())
    colours = dict(zip(levels, sns.color_palette("tab10", len(levels))))
    fig, axes = plt.subplots(len(MOLD_TEMPS), 1, figsize=(11, 8), sharex=True, sharey=True)
    for ax, sensor in zip(axes, MOLD_TEMPS):
        for lv in levels:
            part = df.loc[df[group] == lv]
            ax.plot(part["TIME"], part[sensor], lw=0.8, marker=".", ms=2,
                    color=colours[lv], label=f"{group_label} {lv:g}")
        ax.set(title=sensor, ylabel=L["temp"])
    axes[0].legend(loc="upper right", ncol=len(levels), fontsize=8)
    axes[-1].set_xlabel(L["time"])
    fig.suptitle(L["by_group_title"].format(group=group_label), fontweight="bold")
    fig.autofmt_xdate()
    return fig


def temps_by_shift(df: pd.DataFrame, L: dict, x: str = "TIME",
                   title: str | None = None, shift_col: str = "SHIFT") -> plt.Figure:
    """Programs 14 & 16: one panel per shift with T1, T2, T3 and their mean."""
    shifts = sorted(df[shift_col].unique())
    fig, axes = plt.subplots(len(shifts), 1, figsize=(11, 2.1 * len(shifts)),
                             sharey=True, sharex=(x == "CYCLE_IDX"), squeeze=False)
    for ax, s in zip(axes[:, 0], shifts):
        part = df.loc[df[shift_col] == s]
        for c in [*MOLD_TEMPS, "T_MEAN"]:
            if c in part:
                ax.plot(part[x], part[c], lw=0.9 if c != "T_MEAN" else 1.4,
                        color=SENSOR_COLOURS[c], label=L["avg"] if c == "T_MEAN" else c)
        ax.set_title(f"{L['shift']} {s}", loc="left", fontsize=10)
        ax.set_ylabel(L["temp"])
    axes[0, 0].legend(loc="upper right", ncol=4, fontsize=8)
    axes[-1, 0].set_xlabel(L["cycle_idx"] if x == "CYCLE_IDX" else L["time"])
    fig.suptitle(title or L["by_shift_title"], fontweight="bold")
    fig.tight_layout()
    return fig


def sensor_pairs(df: pd.DataFrame, L: dict, group: str = "MOLD") -> plt.Figure:
    """Program 14, redesigned: pairwise sensor agreement, coloured by mold.

    The original plotted all castings of a shift as one line. Because
    consecutive records belong to *different* molds, that line zig-zags
    between molds and hides the sensor relationship it was meant to show.
    A scatter of T1 vs T2, T1 vs T3 and T2 vs T3 (with the y = x line) shows
    the inter-sensor offset per mold and makes faulty readings stand out.
    """
    pairs = [("T1", "T2"), ("T1", "T3"), ("T2", "T3")]
    levels = sorted(df[group].dropna().unique())
    colours = dict(zip(levels, sns.color_palette("tab10", len(levels))))
    lo = np.nanmin(df[MOLD_TEMPS].to_numpy()) - 10
    hi = np.nanmax(df[MOLD_TEMPS].to_numpy()) + 10
    fig, axes = plt.subplots(1, len(pairs), figsize=(14, 4.6))
    for ax, (a, b) in zip(axes, pairs):
        for lv in levels:
            part = df.loc[df[group] == lv, [a, b]].dropna()
            ax.scatter(part[a], part[b], s=8, alpha=0.5, color=colours[lv],
                       label=f"{L['mold']} {lv:g} (n={len(part)})")
        ax.plot([lo, hi], [lo, hi], color="black", lw=0.8, ls="--")
        ax.set(xlim=(lo, hi), ylim=(lo, hi), xlabel=f"{a} (°C)", ylabel=f"{b} (°C)",
               aspect="equal")
        ax.legend(loc="upper left", fontsize=7, markerscale=2)
    fig.suptitle(L["pairs_title"], fontweight="bold")
    fig.tight_layout()
    return fig


def cycle_vs_temp(part: pd.DataFrame, L: dict, mold: int, shift: int,
                  temp_col: str = "T1", rho: float | None = None,
                  p: float | None = None, jitter_s: float = 8.0,
                  seed: int = 0) -> plt.Figure:
    """Program 20, corrected.

    The original drew seconds and °C on the same y-axis. Here (a) shows cycle
    time as bars with temperatures on a twin axis, and (b) is a scatter plot
    with a least-squares line, annotated with Spearman ρ. Because timestamps
    have 60 s resolution, x is jittered slightly in (b) for display only.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.5),
                                   gridspec_kw={"width_ratios": [1.6, 1]})
    ax1.bar(part["CYCLE_IDX"], part["CYCLE_S"], color="lightgrey", width=0.8,
            label=L["cycle_time"])
    ax1.set(xlabel=L["cycle_idx"], ylabel=L["cycle_time"])
    ax1b = ax1.twinx()
    for c in MOLD_TEMPS:
        ax1b.plot(part["CYCLE_IDX"], part[c], lw=1.1, color=SENSOR_COLOURS[c], label=c)
    ax1b.set_ylabel(L["temp"])
    ax1b.grid(False)
    ax1b.spines["right"].set_visible(True)
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax1b.get_legend_handles_labels()
    ax1b.legend(h1 + h2, l1 + l2, loc="upper right", ncol=4, fontsize=8)

    valid = part[["CYCLE_S", temp_col]].dropna()
    rng = np.random.default_rng(seed)
    x_disp = valid["CYCLE_S"] + rng.uniform(-jitter_s, jitter_s, len(valid))
    ax2.scatter(x_disp, valid[temp_col], s=18, color=SENSOR_COLOURS[temp_col],
                alpha=0.7, edgecolor="none")
    if len(valid) >= 3 and valid["CYCLE_S"].nunique() > 1:
        slope, intercept = np.polyfit(valid["CYCLE_S"], valid[temp_col], 1)
        xs = np.linspace(valid["CYCLE_S"].min(), valid["CYCLE_S"].max(), 50)
        ax2.plot(xs, slope * xs + intercept, color="black", lw=1)
    if rho is not None:
        ax2.text(0.03, 0.95, f"{L['rho']} = {rho:.2f}, p = {p:.3f}, n = {len(valid)}",
                 transform=ax2.transAxes, va="top", fontsize=9)
    ax2.text(0.97, 0.02, L["jitter_note"], transform=ax2.transAxes,
             ha="right", va="bottom", fontsize=7, color="grey")
    ax2.set(xlabel=L["cycle_time"], ylabel=f"{temp_col} (°C)")

    fig.suptitle(L["cycle_title"].format(mold=mold, shift=shift), fontweight="bold")
    fig.tight_layout()
    return fig
