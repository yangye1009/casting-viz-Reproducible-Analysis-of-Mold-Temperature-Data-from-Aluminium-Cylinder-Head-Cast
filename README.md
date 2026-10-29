# casting-viz-Reproducible-Analysis-of-Mold-Temperature-Data-from-Aluminium-Cylinder-Head-Cast
This repository is a **2026 refactoring** of the code from my 2020 B.Eng. thesis, *Design of Casting Data Visualization Based on Python* (School of Materials Science and Engineering, Jiangsu University; supervisor: Assoc. Prof. Zhao Guoping). The thesis used Python to analyse 902 process records from a foundry producing aluminium cylinder heads. 
## Repository layout

```
casting-viz/
├── requirements.txt
├── run_pipeline.py               command-line entry point
├── casting_viz/                  analysis package
│   ├── config.py                 column mapping, physical thresholds, bilingual labels, CJK font fallback
│   ├── loader.py                 read xlsx/csv, normalise headers, validate columns, sort by time
│   ├── cleaning.py               overflow / out-of-range detection, quality report, near-constant screening
│   ├── correlation.py            signed Spearman, correlation ratio η, rank correlation with p-value
│   ├── shifts.py                 gap-based shift segmentation and shift summary
│   ├── mold.py                   per-mold cycle time, outlier flags, per-shift stats, sensor offsets
│   ├── plots.py                  all figures (object-oriented API, generated in loops)
│   └── pipeline.py               chains every step in the order of thesis chapters 5–8
├── tools/
│   └── extract_appendix_a.py     extract raw data from Appendix A 
├── data/
│   └── casting_2020-04_appendixA.csv   902 records recovered from Appendix A
├── tests/
│   └── test_core.py              unit tests + regression tests against the thesis values
└── output/                       generated
    ├── figures/                  9 figures (PNG, 200 dpi)
    └── tables/                   10 result tables (CSV, UTF-8)
```
## Mapping from thesis programs to modules

| Thesis program | Original purpose | New location |
|---|---|---|
| 1–3 | imports, read Excel, rename columns | `config.COLUMN_MAP`, `loader.load_raw` |
| 4–5 | count and remove 32767 overflow values | `cleaning.invalid_mask`, `quality_report`, `clean_mold_temps` |
| 6–7 | plot and drop low-relevance variables | `cleaning.near_constant_columns`, `plots.process_params` |
| 8 | absolute-value correlation heatmap | `correlation.signed_corr`, `eta_table`, `plots.correlation_overview` |
| 9–10 | plot and drop furnace / shift code / running number | `plots.auxiliary_codes` |
| 11–12 | mold temperatures by operator and by mold | `plots.temps_by_group` |
| 13 | shift detection from the largest time gaps | `shifts.assign_shifts`, `shift_summary` |
| 14 | three sensors per shift, all data | `plots.sensor_pairs`  |
| 15 | fluctuation statistics | `mold.temp_fluctuation` |
| 16 | mold 8, three sensors per shift | `mold.mold_cycles`, `plots.temps_by_shift` |
| 17–18 | hand-typed shift ranges + `describe()` | `mold.per_shift_stats` |
| 19 | shift-5 heatmap | `correlation.spearman_with_p` |
| 20 | cycle time vs. temperature plot | `mold.flag_cycle_outliers`, `plots.cycle_vs_temp` |
