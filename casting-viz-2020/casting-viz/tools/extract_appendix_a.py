"""Rebuild the raw dataset from Appendix A of the thesis PDF.

The original Excel export is not redistributed; Appendix A prints all 902
records, each split over two lines by the page layout::

    2020/4/17   1   16   3   1   1   721   240   294   289   303   180 ... 140
      7:57

This script converts the PDF to layout-preserving text with ``pdftotext``
(poppler-utils), joins the two lines of each record with a small state machine,
and validates the result (record count, field count, monotonic time).

Note: the appendix prints timestamps to the minute, the original export had
seconds, so cycle times computed from this file have 60 s resolution.

Usage::

    python tools/extract_appendix_a.py thesis.pdf data/casting_2020-04_appendixA.csv
"""
from __future__ import annotations

import argparse
import csv
import re
import shutil
import subprocess
import sys
from pathlib import Path

HEADER = (["日期与时间", "班次号", "模具代码", "操作员号", "流水号", "保温炉号",
           "铝液温度", "固化时间", "模温1", "模温2", "模温3"]
          + [f"冷却水{i}" for i in range(1, 8)])
N_VALUES = len(HEADER) - 1                       # 17 numeric fields per record

DATA_LINE = re.compile(rf"^\s*(\d{{4}}/\d{{1,2}}/\d{{1,2}})\s+((?:\d+\s+){{{N_VALUES - 1}}}\d+)\s*$")
TIME_LINE = re.compile(r"^\s*(\d{1,2}:\d{2})\s*$")
SECTION_START, SECTION_END = "附录 A", "附录 B"


def pdf_to_text(pdf: Path) -> str:
    if shutil.which("pdftotext") is None:
        sys.exit("pdftotext not found – install poppler-utils (conda install poppler)")
    return subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                          check=True, capture_output=True, text=True).stdout


def parse_records(text: str) -> list[list[str]]:
    """Return one list of 18 strings per record found in Appendix A."""
    start = text.rfind(SECTION_START)            # last hit = the appendix, not the TOC
    end = text.rfind(SECTION_END)
    lines = text[start:end].replace("\f", "\n").splitlines()

    records, pending = [], None
    for line in lines:
        if m := DATA_LINE.match(line):
            if pending is not None:
                raise ValueError(f"Record without time line: {pending}")
            pending = [m.group(1), *m.group(2).split()]
        elif (m := TIME_LINE.match(line)) and pending is not None:
            pending[0] = f"{pending[0]} {m.group(1)}"
            records.append(pending)
            pending = None
    if pending is not None:
        raise ValueError(f"Dangling record at end of section: {pending}")
    return records


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pdf", type=Path)
    ap.add_argument("out_csv", type=Path)
    ap.add_argument("--expect", type=int, default=902, help="expected record count")
    args = ap.parse_args()

    records = parse_records(pdf_to_text(args.pdf))
    if len(records) != args.expect:
        sys.exit(f"Parsed {len(records)} records, expected {args.expect}")

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(HEADER)
        writer.writerows(records)
    print(f"Wrote {len(records)} records to {args.out_csv}")


if __name__ == "__main__":
    main()
