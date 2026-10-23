"""Unit and regression tests.

Run with either of:
    python -m unittest discover -s tests -v
    python -m pytest tests
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from casting_viz import cleaning, correlation, mold, shifts
from casting_viz.config import AnalysisConfig
from casting_viz.loader import load_raw, standardise

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "casting_2020-04_appendixA.csv"
CFG = AnalysisConfig()


def toy_frame() -> pd.DataFrame:
    """Six records, two shifts, two molds, one overflow and one >720 reading."""
    t = pd.to_datetime(["2020-01-01 08:00", "2020-01-01 08:05", "2020-01-01 08:10",
                        "2020-01-01 08:20", "2020-01-01 10:00", "2020-01-01 10:08"])
    return pd.DataFrame({
        "TIME": t,
        "MOLD": [8, 13, 8, 8, 8, 13],
        "OPER": [4, 1, 4, 4, 4, 1],
        "T1": [250, 32767, 255, 260, 240, 245],
        "T2": [260, 270, 265, 900, 250, 255],
        "T3": [240, 230, 245, 250, 230, 235],
    })


class TestLoader(unittest.TestCase):
    def test_headers_with_spaces_are_mapped_and_sorted(self):
        raw = pd.DataFrame({
            "日期与时间": ["2020/4/17 8:05", "2020/4/17 7:57"],
            "模具代码": [8, 16], "操作员号": [4, 3],
            "模温 1": [250, 260], "模温 2": [255, 265], "模温 3": [245, 255],
        })
        df = standardise(raw)
        self.assertEqual(list(df.columns[:6]), ["TIME", "MOLD", "OPER", "T1", "T2", "T3"])
        self.assertTrue(df["TIME"].is_monotonic_increasing)
        self.assertEqual(df.loc[0, "MOLD"], 16)

    def test_missing_column_raises(self):
        with self.assertRaises(KeyError):
            standardise(pd.DataFrame({"日期与时间": ["2020/4/17 8:05"]}))


class TestCleaning(unittest.TestCase):
    def test_invalid_values_become_nan_without_mutating_input(self):
        df = toy_frame()
        out = cleaning.clean_mold_temps(df, CFG)
        self.assertTrue(np.isnan(out.loc[1, "T1"]))          # 32767 overflow
        self.assertTrue(np.isnan(out.loc[3, "T2"]))          # 900 > 720
        self.assertEqual(int(out[["T1", "T2", "T3"]].isna().sum().sum()), 2)
        self.assertEqual(df.loc[1, "T1"], 32767)             # original untouched

    def test_quality_report_separates_overflow_and_out_of_range(self):
        rep = cleaning.quality_report(toy_frame(), CFG).set_index(["MOLD", "sensor"])
        self.assertEqual(rep.loc[(13, "T1"), "overflow_32767"], 1)
        self.assertEqual(rep.loc[(8, "T2"), "out_of_range"], 1)
        self.assertEqual(int(rep["valid"].sum()), 6 * 3 - 2)

    def test_near_constant_rule(self):
        df = pd.DataFrame({"flat": [240.0] * 5, "wavy": [100, 200, 150, 120, 180]})
        res = cleaning.near_constant_columns(df, ["flat", "wavy"], 0.01)
        self.assertTrue(res.loc["flat", "near_constant"])
        self.assertFalse(res.loc["wavy", "near_constant"])


class TestShifts(unittest.TestCase):
    def test_gap_starts_new_shift(self):
        s = shifts.assign_shifts(toy_frame()["TIME"], "30min")
        self.assertEqual(s.tolist(), [1, 1, 1, 1, 2, 2])

    def test_unsorted_input_rejected(self):
        with self.assertRaises(ValueError):
            shifts.assign_shifts(toy_frame()["TIME"][::-1].reset_index(drop=True))

    def test_summary_separates_duration_and_pause(self):
        df = toy_frame()
        df["SHIFT"] = shifts.assign_shifts(df["TIME"])
        summ = shifts.shift_summary(df)
        self.assertEqual(summ.loc[1, "duration"], pd.Timedelta("20min"))
        self.assertEqual(summ.loc[2, "pause_before"], pd.Timedelta("100min"))


class TestCorrelation(unittest.TestCase):
    def test_eta_extremes(self):
        g = pd.Series(["a", "a", "b", "b"])
        self.assertAlmostEqual(correlation.correlation_ratio(g, pd.Series([1, 1, 5, 5])), 1.0)
        self.assertAlmostEqual(correlation.correlation_ratio(g, pd.Series([1, 5, 1, 5])), 0.0)

    def test_eta_ignores_label_numbering(self):
        y = pd.Series([250, 252, 270, 268, 240, 241.0])
        a = correlation.correlation_ratio(pd.Series([8, 8, 13, 13, 16, 16]), y)
        b = correlation.correlation_ratio(pd.Series([3, 3, 1, 1, 2, 2]), y)
        self.assertAlmostEqual(a, b)

    def test_signed_corr_keeps_sign(self):
        df = pd.DataFrame({"x": [1, 2, 3, 4], "y": [8, 6, 4, 2]})
        self.assertAlmostEqual(correlation.signed_corr(df, ["x", "y"]).loc["x", "y"], -1.0)


class TestMold(unittest.TestCase):
    def test_cycle_time_does_not_span_shift_pause(self):
        df = toy_frame()
        df["SHIFT"] = shifts.assign_shifts(df["TIME"])
        sub = mold.mold_cycles(df, 8)
        # mold 8: 08:00, 08:10, 08:20 | pause | 10:00
        self.assertEqual(sub["CYCLE_S"].tolist()[1:3], [600.0, 600.0])
        self.assertTrue(np.isnan(sub["CYCLE_S"].iloc[3]))   # first casting of shift 2
        self.assertEqual(sub["CYCLE_IDX"].tolist(), [1, 2, 3, 1])

    def test_outlier_flag_keeps_values(self):
        c = pd.Series([480, 420, 480, 540, 480, 3000.0])
        flags = mold.flag_cycle_outliers(c, k=3)
        self.assertEqual(flags.tolist(), [False] * 5 + [True])

    def test_strict_mean_propagates_nan(self):
        df = pd.DataFrame({"T1": [np.nan, 250.0], "T2": [260.0, 260.0], "T3": [240.0, 240.0]})
        self.assertTrue(np.isnan(mold.add_mean_temp(df, strict=True).loc[0, "T_MEAN"]))
        self.assertAlmostEqual(mold.add_mean_temp(df, strict=False).loc[0, "T_MEAN"], 250.0)


@unittest.skipUnless(DATA.exists(), "dataset not present")
class TestReproducesThesis(unittest.TestCase):
    """Regression tests: the refactored code must reproduce the thesis figures."""

    @classmethod
    def setUpClass(cls):
        cls.raw = load_raw(DATA)
        cls.df = cleaning.clean_mold_temps(cls.raw, CFG)

    def test_record_count(self):
        self.assertEqual(len(self.raw), 902)

    def test_overflow_rows_section_6_1(self):
        n = self.raw[["T1", "T2", "T3"]].eq(CFG.sensor_overflow).any(axis=1).sum()
        self.assertEqual(n, 267)

    def test_table_7(self):
        fl = mold.temp_fluctuation(self.df)
        self.assertEqual(fl["count"].astype(int).tolist(), [721, 902, 814])
        # the thesis truncates to integers
        self.assertEqual(np.floor(fl["mean"]).astype(int).tolist(), [253, 281, 247])
        self.assertEqual(np.floor(fl["step_std"]).astype(int).tolist(), [23, 64, 48])

    def test_table_6_shift_sizes(self):
        s = shifts.assign_shifts(self.df["TIME"], CFG.shift_gap)
        self.assertEqual(s.value_counts().sort_index().tolist(), [225, 174, 178, 162, 163])

    def test_mold_operator_mapping_section_6_4(self):
        ct = pd.crosstab(self.df["MOLD"], self.df["OPER"])
        self.assertEqual(ct.loc[8].idxmax(), 4)
        self.assertEqual(ct.loc[13].idxmax(), 1)
        self.assertEqual(set(ct.columns[ct.loc[16] > 0]), {2, 3})


@unittest.skipUnless(DATA.exists(), "dataset not present")
class TestPipelineSmoke(unittest.TestCase):
    def test_end_to_end(self):
        from casting_viz.pipeline import run
        with tempfile.TemporaryDirectory() as tmp:
            res = run(DATA, Path(tmp), lang="en")
            self.assertEqual(len(list((Path(tmp) / "figures").glob("*.png"))), 9)
            self.assertIn("08_mold8_per_shift", res)


if __name__ == "__main__":
    unittest.main()
