"""Central configuration for the casting-data pipeline.

Everything that was hard-coded in the original 2020 thesis script (file paths,
magic numbers such as 32767 / 720, row-index ranges for each shift, colours,
Chinese font) is collected here so that the analysis code stays generic.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import matplotlib
from matplotlib import font_manager

log = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# 1. Column mapping (thesis Program 3, extended to every column)
# --------------------------------------------------------------------------- #
# Raw headers are Chinese; whitespace is stripped before lookup, so both
# "模温 1" and "模温1" map correctly.
COLUMN_MAP: dict[str, str] = {
    "日期与时间": "TIME",
    "班次号": "SHIFT_CODE",   # crew/shift code recorded by the PLC (1-3)
    "模具代码": "MOLD",
    "操作员号": "OPER",
    "流水号": "FLOW",          # running casting number, reset daily
    "保温炉号": "FURNACE",     # holding-furnace id
    "铝液温度": "MELT_T",      # aluminium melt temperature, degC
    "固化时间": "SOLID_TIME",  # solidification time, s
    "模温1": "T1",
    "模温2": "T2",
    "模温3": "T3",
    **{f"冷却水{i}": f"CW{i}" for i in range(1, 8)},  # cooling-water temps
}

MOLD_TEMPS: list[str] = ["T1", "T2", "T3"]
PROCESS_PARAMS: list[str] = ["MELT_T", "SOLID_TIME"] + [f"CW{i}" for i in range(1, 8)]
CATEGORICAL_CODES: list[str] = ["SHIFT_CODE", "MOLD", "OPER", "FURNACE"]


# --------------------------------------------------------------------------- #
# 2. Analysis parameters (physically / statistically justified)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class AnalysisConfig:
    # 32767 = INT16_MAX: the PLC writes this when a thermocouple reading overflows.
    sensor_overflow: int = 32767
    # A mold cannot be hotter than the melt poured into it (~720 degC).
    max_plausible_mold_t: float = 720.0
    # Coefficient of variation below which a signal is treated as constant.
    near_constant_cv: float = 0.01
    # Any gap between consecutive records longer than this starts a new shift.
    # Observed: within-shift gaps <= 15 min, between-shift gaps 65-97 min.
    shift_gap: str = "30min"
    # Tukey fence multiplier for flagging abnormal cycle times (production stops).
    cycle_iqr_k: float = 3.0
    # Mold analysed in detail (Chapter 8 of the thesis).
    focus_mold: int = 8


# --------------------------------------------------------------------------- #
# 3. Bilingual figure labels
# --------------------------------------------------------------------------- #
LABELS: dict[str, dict[str, str]] = {
    "en": {
        "time": "Time",
        "temp": "Temperature (°C)",
        "seconds": "Time (s)",
        "melt": "Melt temperature",
        "cw_high": "Cooling water 1-3",
        "cw_low": "Cooling water 4-7",
        "solid": "Solidification time",
        "furnace": "Holding furnace",
        "shift_code": "Shift code",
        "flow": "Running number",
        "oper": "Operator",
        "mold": "Mold",
        "shift": "Shift",
        "cycle_idx": "Cycle index within shift",
        "cycle_time": "Cycle time (s)",
        "avg": "mean(T1-T3)",
        "corr_title": "Spearman correlation (signed)",
        "eta_title": "Correlation ratio η: how much each code explains",
        "quality_title": "Invalid mold-temperature readings by mold and sensor",
        "overflow": "Overflow (32767)",
        "out_of_range": "Out of range (>720 °C)",
        "count": "Number of readings",
        "valid": "Valid",
        "pairs_title": "Sensor agreement across all castings (colour = mold)",
        "jitter_note": "x jittered ±8 s for visibility",
        "process_title": "Near-constant process parameters",
        "codes_title": "Auxiliary codes over time",
        "by_group_title": "Mold temperatures grouped by {group}",
        "by_shift_title": "Mold temperatures per shift",
        "mold_shift_title": "Mold {mold}: T1-T3 per shift",
        "cycle_title": "Mold {mold}, shift {shift}: cycle time vs. mold temperature",
        "rho": "ρ",
    },
    "zh": {
        "time": "时间",
        "temp": "温度 (°C)",
        "seconds": "时间 (s)",
        "melt": "铝液温度",
        "cw_high": "冷却水 1-3",
        "cw_low": "冷却水 4-7",
        "solid": "固化时间",
        "furnace": "保温炉号",
        "shift_code": "班次号",
        "flow": "流水号",
        "oper": "操作员",
        "mold": "模具",
        "shift": "班次",
        "cycle_idx": "班次内模次序号",
        "cycle_time": "浇铸节拍 (s)",
        "avg": "T1-T3 平均",
        "corr_title": "Spearman 相关系数（带符号）",
        "eta_title": "相关比 η：各代号对模温的解释程度",
        "quality_title": "各模具、各测温点的无效模温读数",
        "overflow": "溢出值 (32767)",
        "out_of_range": "超出范围 (>720 °C)",
        "count": "读数个数",
        "valid": "有效",
        "pairs_title": "全部数据中三个测温点的一致性（颜色 = 模具）",
        "jitter_note": "横坐标加 ±8 s 抖动以便观察",
        "process_title": "近似恒定的工艺参数",
        "codes_title": "辅助代号随时间变化",
        "by_group_title": "按{group}分组的模具温度",
        "by_shift_title": "各班次模具温度",
        "mold_shift_title": "模具 {mold}：各班次 T1-T3",
        "cycle_title": "模具 {mold} 班次 {shift}：浇铸节拍与模温",
        "rho": "ρ",
    },
}

# Fonts tried in order when Chinese labels are requested (Win / macOS / Linux).
# matplotlib registers only the first face of a .ttc collection, so Noto CJK
# may appear under its JP/TC/KR name; all of them contain Chinese glyphs.
_CJK_FONTS = ["SimHei", "Microsoft YaHei", "PingFang SC", "Heiti SC", "Songti SC",
              "Noto Sans CJK SC", "Noto Sans CJK JP", "Noto Sans CJK TC",
              "Source Han Sans SC", "WenQuanYi Micro Hei", "WenQuanYi Zen Hei"]


def _find_cjk_fonts() -> list[str]:
    installed = {f.name for f in font_manager.fontManager.ttflist}
    found = [f for f in _CJK_FONTS if f in installed]
    if not found:  # last resort: any font whose name looks CJK
        found = sorted(n for n in installed if "CJK" in n or n.endswith((" Hei", " SC")))
    return found


def setup_matplotlib(lang: str = "en", interactive: bool = False) -> dict[str, str]:
    """Configure matplotlib once and return the label dictionary for *lang*."""
    if lang not in LABELS:
        raise ValueError(f"lang must be one of {sorted(LABELS)}, got {lang!r}")
    if not interactive:
        matplotlib.use("Agg")  # headless: figures are written to disk

    import matplotlib.pyplot as plt  # imported after backend selection

    plt.rcParams.update({
        "figure.dpi": 110,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
        "axes.grid": True,
        "grid.linestyle": ":",
        "grid.alpha": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.frameon": False,
        "axes.unicode_minus": False,
    })

    if lang == "zh":
        available = _find_cjk_fonts()
        if available:
            plt.rcParams["font.family"] = "sans-serif"
            plt.rcParams["font.sans-serif"] = available + plt.rcParams["font.sans-serif"]
            log.info("Using CJK font: %s", available[0])
        else:
            log.warning("No CJK font found; Chinese labels may render as boxes.")
    return LABELS[lang]
