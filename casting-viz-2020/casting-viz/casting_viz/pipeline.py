"""End-to-end analysis pipeline: raw export -> cleaned data -> tables + figures.

Steps follow the thesis chapters:
    Ch.5  load & rename                       (Programs 1-3)
    Ch.6  clean, select variables, correlate  (Programs 4-12)
    Ch.7  shifts and sensor behaviour         (Programs 13-16)
    Ch.8  single-mold cycle analysis          (Programs 17-20)
"""
from __future__ import annotations

import argparse
import logging
from dataclasses import replace
from pathlib import Path

import pandas as pd

from . import cleaning, correlation, mold, plots, shifts
from .config import CATEGORICAL_CODES, MOLD_TEMPS, PROCESS_PARAMS, AnalysisConfig, setup_matplotlib
from .loader import load_raw

log = logging.getLogger("casting_viz")


def run(input_path: Path, out_dir: Path, lang: str = "en",
        cfg: AnalysisConfig = AnalysisConfig(), show: bool = False) -> dict[str, pd.DataFrame]:
    L = setup_matplotlib(lang, interactive=show)
    import matplotlib.pyplot as plt

    fig_dir, tab_dir = out_dir / "figures", out_dir / "tables"
    tab_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, pd.DataFrame] = {}

    def emit_table(name: str, table: pd.DataFrame, index: bool = True) -> None:
        results[name] = table
        table.to_csv(tab_dir / f"{name}.csv", index=index, encoding="utf-8-sig")

    def emit_fig(name: str, fig: plt.Figure) -> None:
        path = plots.save(fig, fig_dir, name)
        log.info("  figure  -> %s", path)
        if not show:
            plt.close(fig)

    # ---- Ch.5: load --------------------------------------------------------
    raw = load_raw(input_path)
    log.info("Loaded %d records x %d columns (%s .. %s)", len(raw), raw.shape[1],
             raw["TIME"].min(), raw["TIME"].max())

    # ---- Ch.6.1: data quality & cleaning ----------------------------------
    # Programs 4-5
    bad = cleaning.invalid_mask(raw, cfg)
    log.info("Records with >=1 invalid mold temperature: %d / %d",
             int(bad.any(axis=1).sum()), len(raw))
    quality = cleaning.quality_report(raw, cfg)
    emit_table("01_quality_by_mold_sensor", quality, index=False)
    emit_fig("01_data_quality", plots.data_quality(quality, L))
    df = cleaning.clean_mold_temps(raw, cfg)

    # ---- Ch.6.2: near-constant process parameters -------------------------
    constancy = cleaning.near_constant_columns(df, PROCESS_PARAMS, cfg.near_constant_cv)
    emit_table("02_process_param_variation", constancy)
    emit_fig("02_process_params", plots.process_params(df, L, constancy["cv"]))
    dropped = constancy.index[constancy["near_constant"]].tolist()
    log.info("Near-constant (CV < %.2f) and dropped: %s", cfg.near_constant_cv, dropped)
    df = df.drop(columns=dropped)

    # ---- Ch.7.1: shift segmentation (needed before grouping) --------------
    df["SHIFT"] = shifts.assign_shifts(df["TIME"], cfg.shift_gap)
    emit_table("03_shift_summary", shifts.shift_summary(df))
    emit_fig("03_auxiliary_codes", plots.auxiliary_codes(df, L))

    # ---- Ch.6.3: correlation ----------------------------------------------
    num_cols = ["FLOW", *MOLD_TEMPS]
    spearman = correlation.signed_corr(df, num_cols)
    eta = correlation.eta_table(df, [c for c in CATEGORICAL_CODES if c in df], MOLD_TEMPS)
    emit_table("04_spearman", spearman.round(3))
    emit_table("04_eta_codes_vs_temps", eta)
    emit_fig("04_correlation", plots.correlation_overview(spearman, eta, L))

    # ---- Ch.6.4: operator / mold grouping ---------------------------------
    emit_table("05_mold_operator_crosstab", pd.crosstab(df["MOLD"], df["OPER"]))
    emit_fig("05_temps_by_operator", plots.temps_by_group(df, "OPER", L))
    emit_fig("06_temps_by_mold", plots.temps_by_group(df, "MOLD", L))

    # ---- Ch.7.2: three-sensor behaviour, all data -------------------------
    df = mold.add_mean_temp(df, strict=True)
    emit_table("07_temp_fluctuation", mold.temp_fluctuation(df))
    emit_fig("07_sensor_agreement", plots.sensor_pairs(df, L))

    # ---- Ch.8: focus mold --------------------------------------------------
    m = cfg.focus_mold
    sub = mold.mold_cycles(df, m)
    sub["CYCLE_OUTLIER"] = mold.flag_cycle_outliers(sub["CYCLE_S"], cfg.cycle_iqr_k)
    log.info("Mold %d: %d castings, %d cycle-time outliers flagged",
             m, len(sub), int(sub["CYCLE_OUTLIER"].sum()))
    emit_table(f"08_mold{m}_per_shift", mold.per_shift_stats(sub))
    emit_table(f"08_mold{m}_sensor_offsets", mold.sensor_offsets(sub))
    emit_fig(f"08_mold{m}_by_shift",
             plots.temps_by_shift(sub, L, x="CYCLE_IDX",
                                  title=L["mold_shift_title"].format(mold=m)))

    # Cycle time vs temperature, per shift and pooled (outliers excluded)
    usable = sub.loc[~sub["CYCLE_OUTLIER"]]
    rows = []
    for label, part in [*usable.groupby("SHIFT"), ("all", usable)]:
        for c in MOLD_TEMPS:
            rho, p, n = correlation.spearman_with_p(part["CYCLE_S"], part[c])
            rows.append({"shift": label, "sensor": c, "rho": round(rho, 3),
                         "p_value": round(p, 4), "n": n})
    cyc_corr = pd.DataFrame(rows)
    emit_table(f"09_mold{m}_cycle_vs_temp_spearman", cyc_corr, index=False)

    best_shift = int(usable.groupby("SHIFT")["CYCLE_S"].count().idxmax())
    part = usable.loc[usable["SHIFT"] == best_shift]
    r = cyc_corr.query("shift == @best_shift and sensor == 'T1'").iloc[0]
    emit_fig(f"09_mold{m}_cycle_vs_temp_shift{best_shift}",
             plots.cycle_vs_temp(part, L, m, best_shift, "T1", r["rho"], r["p_value"]))

    if show:
        plt.show()
    log.info("Done. Tables in %s, figures in %s", tab_dir, fig_dir)
    return results


def main(argv: list[str] | None = None) -> None:
    root = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser(description="Foundry mold-temperature analysis pipeline")
    p.add_argument("--input", type=Path, default=root / "data" / "casting_2020-04_appendixA.csv",
                   help="raw .xlsx or .csv export")
    p.add_argument("--out", type=Path, default=root / "output")
    p.add_argument("--lang", choices=["en", "zh"], default="en", help="figure label language")
    p.add_argument("--mold", type=int, default=AnalysisConfig.focus_mold)
    p.add_argument("--shift-gap", default=AnalysisConfig.shift_gap,
                   help="pause that separates two shifts, e.g. 30min")
    p.add_argument("--show", action="store_true", help="also open figures interactively")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    cfg = replace(AnalysisConfig(), focus_mold=args.mold, shift_gap=args.shift_gap)
    run(args.input, args.out, args.lang, cfg, args.show)


if __name__ == "__main__":
    main()
