# casting-viz: Reproducible Analysis of Mold-Temperature Data from Aluminium Cylinder-Head Casting

This repository is a **2026 refactoring** of the code from my 2020 B.Eng. thesis, *Design of Casting Data Visualization Based on Python* (School of Materials Science and Engineering, Jiangsu University; supervisor: Assoc. Prof. Zhao Guoping). The thesis used Python to analyse 902 process records from a foundry producing aluminium cylinder heads. The analysis focused on the data quality, influencing factors and stability of three mold thermocouples (T1–T3).
---

## 1. Quick start

```bash
pip install -r requirements.txt

python run_pipeline.py                     # bundled data, English labels -> output/
python run_pipeline.py --lang zh           # Chinese figure labels
python run_pipeline.py --input raw.xlsx --mold 16 --shift-gap 45min

python -m unittest discover -s tests -v    # 20 unit + regression tests
```

Requirements: Python ≥ 3.10, pandas ≥ 2.0 (verified on pandas 3.0), matplotlib, seaborn and scipy.

## 2. Repository layout

```
casting-viz/
├── README.md / README_EN.md      documentation (Chinese / English)
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
│   └── extract_appendix_a.py     rebuilds the raw data from Appendix A of the thesis PDF (regex + state machine)
├── data/
│   └── casting_2020-04_appendixA.csv   902 records recovered from Appendix A
├── tests/
│   └── test_core.py              unit tests + regression tests against the thesis values
└── output/                       generated
    ├── figures/                  9 figures (PNG, 200 dpi)
    └── tables/                   10 result tables (CSV, UTF-8)
```

## 3. Mapping from thesis programs to modules

| Thesis program | Original purpose | New location |
|---|---|---|
| 1–3 | imports, read Excel, rename columns | `config.COLUMN_MAP`, `loader.load_raw` |
| 4–5 | count and remove 32767 overflow values | `cleaning.invalid_mask`, `quality_report`, `clean_mold_temps` |
| 6–7 | plot and drop low-relevance variables | `cleaning.near_constant_columns`, `plots.process_params` |
| 8 | absolute-value correlation heatmap | `correlation.signed_corr`, `eta_table`, `plots.correlation_overview` |
| 9–10 | plot and drop furnace / shift code / running number | `plots.auxiliary_codes` |
| 11–12 | mold temperatures by operator and by mold | `plots.temps_by_group` |
| 13 | shift detection from the largest time gaps | `shifts.assign_shifts`, `shift_summary` |
| 14 | three sensors per shift, all data | `plots.sensor_pairs` (redesigned, see 4.5) |
| 15 | fluctuation statistics | `mold.temp_fluctuation` |
| 16 | mold 8, three sensors per shift | `mold.mold_cycles`, `plots.temps_by_shift` |
| 17–18 | hand-typed shift ranges + `describe()` | `mold.per_shift_stats` |
| 19 | shift-5 heatmap | `correlation.spearman_with_p` |
| 20 | cycle time vs. temperature plot | `mold.flag_cycle_outliers`, `plots.cycle_vs_temp` |

## 4. Results

| Figure | Finding |
|---|---|
| ![](output/figures/01_data_quality.png) | **Data quality.** All invalid readings come from just two sensors. T1 on mold 13 has essentially failed (181 of 182 readings are 32767). T3 on mold 16 is 24% invalid: 86 overflows plus two readings of 828 °C and 846 °C. Mold 8 has no invalid readings at all, which is the direct reason its data were "the most complete". |
| ![](output/figures/02_process_params.png) | **Variable screening.** Melt temperature, solidification time and all seven cooling-water channels have a coefficient of variation below 0.3% and are dropped under a CV < 1% rule. This agrees with the thesis's visual judgement but is now a reproducible criterion. |
| ![](output/figures/04_correlation.png) | **Correlation.** Furnace id and shift code have η < 0.1 and can be ignored. Operator id (η = 0.69–0.75) and mold id (η = 0.47–0.62) explain much of the variation in T1 and T2. The running number has only a weak positive correlation with mold temperature (ρ ≈ 0.10–0.14). Note that operator and mold are nested (mold 16 is shared by operators 2 and 3), so these data cannot separate an operator effect from a mold effect. |
| ![](output/figures/07_sensor_agreement.png) | **Sensor agreement.** Mold 8 points lie close to the diagonal with stable offsets (T2−T1 = 10.2 ± 7.3 °C, T1−T3 = 10.8 ± 4.3 °C). On mold 16, T2 drifts far above T1 (up to 481 °C). T3 also shows sporadic 380–640 °C spikes in the same period it begins to overflow, which may signal an emerging sensor fault. |
| ![](output/figures/08_mold8_by_shift.png) | **Mold 8 stability.** Mean T1 across the five shifts is 243.8–247.1 °C, and the median cycle time is 420–480 s. The first casting of each shift is noticeably hotter, consistent with the mold being held warm during the pause. |
| ![](output/figures/09_mold8_cycle_vs_temp_shift5.png) | **Cycle time vs. temperature.** The association is positive but weak. Only shift 5 is significant (T1: ρ = 0.29, p = 0.012, n = 77); pooling all shifts gives ρ = 0.11–0.14 (n = 327, p = 0.01–0.05). With 18 tests in total, the shift-5 result would not survive a Bonferroni correction (0.05/18 ≈ 0.003). The thesis claim "longer cycles mean hotter molds" should therefore be softened to "a weak positive association". |

Full numerical results are in `output/tables/`.

