# casting-viz: Reproducible Analysis of Mold-Temperature Data from Aluminium Cylinder-Head Casting



This repository is a **2026 refactoring** of the code from my 2020 B.Eng. thesis, *Design of Casting Data Visualization Based on Python* (School of Materials Science and Engineering, Jiangsu University; supervisor: Assoc. Prof. Zhao Guoping). The thesis used Python to analyse 902 process records from a foundry producing aluminium cylinder heads. The analysis focused on the data quality, influencing factors and stability of three mold thermocouples (T1–T3).

The refactoring had three goals:

- **Reproducibility.** One command regenerates every figure and table from the raw data.
- **Correctness.** Statistical and programming issues in the original code are fixed.
- **Maintainability.** About 400 lines of copy-pasted plotting script are now **tested, reusable** modules.

Every key number from the thesis is checked against the refactored output (Section 6).

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

## 4. Main corrections

### 4.1 Overflow values were never actually removed (chained assignment)

```python
# original (Program 5)
df['T1'][df['T1'] > 720] = None
# refactored
out[cols] = out[cols].mask(invalid_mask(out, cfg, cols))
```

The original line uses chained assignment. Since pandas 3.0, Copy-on-Write makes it modify only a temporary copy. The 32767 overflow values therefore stay in the data, and no error is raised (verified). The new version replaces them in one step, leaves the input untouched, and is covered by a unit test.

### 4.2 The heatmap discarded the sign and applied Pearson to label codes

`abs(df.corr())` removes the sign, so the heatmap cannot distinguish positive from negative relationships. Section 8.31 of the thesis nevertheless concluded that the correlation was "positive". In addition, mold id, operator id and furnace id are **nominal** variables: 8/13/16 are labels. A Pearson coefficient on them changes if the labels are renumbered.

The refactored code uses two measures instead:

- **Signed Spearman correlation** between continuous variables.
- **Correlation ratio η** (√R² of a one-way ANOVA) between codes and temperatures. η does not depend on how the labels are numbered.

### 4.3 Shift boundaries: from hand-typed row numbers to automatic gap detection

The original code first located the five largest time gaps by hand. It then hard-coded each shift's rows (e.g. `loc[279:358]`), so it worked for only this one file. Now any gap longer than 30 minutes starts a new shift. The observed within-shift maximum is 15 minutes and the between-shift gaps are 65–97 minutes, so the threshold sits between the two. It can be adjusted with `--shift-gap`.

### 4.4 Cycle time spanned production pauses and outliers were overwritten

The original cycle time was taken from the time difference between consecutive records in the whole dataset. It therefore included the pause between shifts (one "cycle" in shift 5 lasted 71 min). Long cycles were then overwritten with `shift5['cycletime'][... > 1000] = 600`.

The refactored code changes both steps:

- Cycle time is now computed between consecutive castings of the **same mold within the same shift**. The first casting of each shift has no cycle time.
- Abnormally long cycles are **flagged** with a Tukey fence (Q3 + 3·IQR = 900 s). Their raw values are kept, and they are excluded only from the correlation analysis.

### 4.5 The three-sensor plot mixed different molds

Program 14 drew every record of a shift as one line. Consecutive records belong to different molds, so the zig-zag pattern reflected mold switching, not temperature fluctuation. The plot is replaced by pairwise scatter plots (T1–T2, T1–T3, T2–T3), coloured by mold, with a y = x reference line. Each mold's sensor offsets and any sensor faults are now visible at a glance.

### 4.6 Other engineering improvements

- File paths, thresholds, colours and fonts are all parameters.
- Every figure uses the `fig, axes` object-oriented API and is generated in a loop.
- Seconds and °C no longer share one y-axis; twin axes are used instead.
- Chinese fonts fall back automatically on Windows, macOS and Linux.
- `df.corr()` raises an error on date columns in pandas ≥ 2.0, so numeric columns are now selected explicitly.

## 5. Results

| Figure | Finding |
|---|---|
| ![](output/figures/01_data_quality.png) | **Data quality.** All invalid readings come from just two sensors. T1 on mold 13 has essentially failed (181 of 182 readings are 32767). T3 on mold 16 is 24% invalid: 86 overflows plus two readings of 828 °C and 846 °C. Mold 8 has no invalid readings at all, which is the direct reason its data were "the most complete". |
| ![](output/figures/02_process_params.png) | **Variable screening.** Melt temperature, solidification time and all seven cooling-water channels have a coefficient of variation below 0.3% and are dropped under a CV < 1% rule. This agrees with the thesis's visual judgement but is now a reproducible criterion. |
| ![](output/figures/04_correlation.png) | **Correlation.** Furnace id and shift code have η < 0.1 and can be ignored. Operator id (η = 0.69–0.75) and mold id (η = 0.47–0.62) explain much of the variation in T1 and T2. The running number has only a weak positive correlation with mold temperature (ρ ≈ 0.10–0.14). Note that operator and mold are nested (mold 16 is shared by operators 2 and 3), so these data cannot separate an operator effect from a mold effect. |
| ![](output/figures/07_sensor_agreement.png) | **Sensor agreement.** Mold 8 points lie close to the diagonal with stable offsets (T2−T1 = 10.2 ± 7.3 °C, T1−T3 = 10.8 ± 4.3 °C). On mold 16, T2 drifts far above T1 (up to 481 °C). T3 also shows sporadic 380–640 °C spikes in the same period it begins to overflow, which may signal an emerging sensor fault. |
| ![](output/figures/08_mold8_by_shift.png) | **Mold 8 stability.** Mean T1 across the five shifts is 243.8–247.1 °C, and the median cycle time is 420–480 s. The first casting of each shift is noticeably hotter, consistent with the mold being held warm during the pause. |
| ![](output/figures/09_mold8_cycle_vs_temp_shift5.png) | **Cycle time vs. temperature.** The association is positive but weak. Only shift 5 is significant (T1: ρ = 0.29, p = 0.012, n = 77); pooling all shifts gives ρ = 0.11–0.14 (n = 327, p = 0.01–0.05). With 18 tests in total, the shift-5 result would not survive a Bonferroni correction (0.05/18 ≈ 0.003). The thesis claim "longer cycles mean hotter molds" should therefore be softened to "a weak positive association". |

Full numerical results are in `output/tables/`.

## 6. Agreement with the thesis (regression tests)

`tests/test_core.py::TestReproducesThesis` automatically checks that the refactored code reproduces the key numbers in the thesis:

| Item | Thesis | Refactored |
|---|---|---|
| Records | 902 | 902 ✓ |
| Records containing 32767 (Sec. 6.1) | 267 | 267 ✓ |
| Valid T1 / T2 / T3 readings (Table 7) | 721 / 902 / 814 | 721 / 902 / 814 ✓ |
| Mean mold temperature (Table 7) | 253 / 281 / 247 | 253.4 / 281.3 / 247.5 ✓ |
| Std. of record-to-record change (Table 7) | 23 / 64 / 48 | 23.2 / 64.7 / 48.6 ✓ |
| Records per shift (Table 6) | 225 / 174 / 178 / 162 / 163 | identical ✓ |
| Mold–operator mapping (Sec. 6.4) | 8↔4, 13↔1, 16↔2 and 3 | identical ✓ |

The re-check also uncovered several typos or calculation errors in the thesis, corrected here:

- Table 5 lists the mold codes as "3, 16, 18"; they are **8, 13, 16**.
- In Table 7, the T1 range should be 154–315 °C (the thesis says 145), and the T2 maximum should be **481 °C** (the thesis says 418).
- Table 8 (shift 1) and Table 12 (shift 5) contain identical values, a copy error. Recomputed: shift 1 T1 is 224–296 °C (mean 246.3); shift 5 T1 is 224–301 °C (mean 247.1).
- The "shift duration" in Table 6 includes the pause before the next shift. Actual production time per shift is 10 h 23 min to 10 h 52 min.

## 7. Limitations and next steps

- **Time resolution.** Appendix A prints timestamps only to the minute, so cycle times recovered from it have a resolution of 60 s. The original Excel export with seconds can be used directly via `--input`.
- **Sensor spikes below 720 °C are not filtered.** The spikes in mold 16's T3 remain in the data. A next step is to exploit the strong agreement between the three sensors (ρ = 0.81–0.92) with a cross-sensor residual test, or to use a Hampel/MAD filter.
- Mold 8 has a few 60 s cycle times, which are physically implausible and probably logging artifacts. Only unusually long cycles are flagged at present.
- The data cover only 2.5 days and are observational. Mold and operator are confounded, so the results do not support causal conclusions.
- Possible extensions: SPC control charts for real-time monitoring, and comparison with ProCAST solidification simulations (proposed in the thesis conclusion).

## 8. Data note

`data/casting_2020-04_appendixA.csv` is generated by `tools/extract_appendix_a.py`, which parses Appendix A of the thesis. The parsed data match the statistics reported in the thesis item by item. Column headers keep their original Chinese names and are mapped to English by `config.COLUMN_MAP` when loaded.

```bash
python tools/extract_appendix_a.py thesis.pdf data/casting_2020-04_appendixA.csv
```
