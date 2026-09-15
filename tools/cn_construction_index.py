#!/usr/bin/env python
"""Quarterly construction index for the Chinese hubs from the radar-detected structures (RFW-03).

For every entry in data/cn_radar_review.csv (confirmed, unclear and rejected alike) the script takes the structure's area
from the radar scan and dates it from its Sentinel-1 series in results_s1/<site_id>.csv with the site's own rule
(tools/s1_timeline.s1_on: VV at least 4 dB above the 20th percentile of earlier months, sustained six months). That rule
returns the first month of the sustained plateau, so it is the latest defensible date; the earliest is the onset of the rise,
taken here as the first month of the run of consecutive months at or above half the jump (base + 2 dB) that leads into the
plateau, looking back at most six months. The window between the two is the dating spread. The rule itself has been checked
only against Sentinel-2 roof dates at Abilene (agreement within 0 to 4 months at 12 halls), never against construction records.

    python tools/cn_construction_index.py [--review data/cn_radar_review.csv] [--out results_cn/construction_index.csv]

Writes
  results_cn/construction_index_entries.csv  one row per structure: verdict, area, default date, window, spread, quarter
  results_cn/construction_index.csv          hub x quarter x verdict: count, area by default date, and the area whose whole
                                             window lies inside the quarter (firm) or overlaps it (possible), i.e. a low and
                                             a high bound from the dating spread
Verdict classes stay separate so a reader can add them or not. The index counts new hall-like structures of 5 ha or more
found by the radar scan; it is not a measure of data-centre capacity and says nothing about fit-out or operation.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.s1_timeline import s1_on  # noqa: E402

JUMP = 4.0        # dB, the site's rule
LOOKBACK = 6      # months: how far before the plateau the onset may sit


def month_of(result: str) -> str | None:
    """s1_on returns 'YYYY-MM (base ...)' or 'not_yet' / 'insufficient'."""
    return result[:7] if result[:4].isdigit() else None


def quarter_of(ym: str) -> str:
    y, m = int(ym[:4]), int(ym[5:7])
    return f"{y}Q{(m - 1) // 3 + 1}"


def months_between(a: str, b: str) -> int:
    return (int(b[:4]) - int(a[:4])) * 12 + int(b[5:7]) - int(a[5:7])


def quarters_between(q_from: str, q_to: str) -> list[str]:
    y, q = int(q_from[:4]), int(q_from[5])
    out = []
    while True:
        cur = f"{y}Q{q}"
        out.append(cur)
        if cur == q_to:
            return out
        q += 1
        if q == 5:
            y, q = y + 1, 1


def onset(series: pd.Series, default: str, base: float, lookback: int = LOOKBACK) -> str:
    """First month of the run of months at or above base + JUMP/2 that ends at the plateau month `default`."""
    v = series.dropna()
    idx = list(v.index)
    k = idx.index(default)
    j = k
    while j > 0 and k - (j - 1) <= lookback and float(v.iloc[j - 1]) >= base + JUMP / 2:
        j -= 1
    return idx[j]


def date_entry(series: pd.Series) -> dict:
    res = s1_on(series, jump=JUMP)
    default = month_of(res)
    if default is None:
        return dict(structure_on="", window_from="", window_to="", spread_months="", quarter="", base_db="")
    base = float(re.search(r"base (-?[\d.]+) dB", res).group(1))
    lo = onset(series, default, base)
    return dict(structure_on=default, window_from=lo, window_to=default, spread_months=months_between(lo, default),
                quarter=quarter_of(default), base_db=round(base, 1))


def build(review_path: Path, s1_dir: Path):
    review = list(csv.DictReader(open(review_path, encoding="utf-8")))
    entries = []
    for r in review:
        sid = r["site_id"]
        f = s1_dir / f"{sid}.csv"
        rec = dict(site_id=sid, hub=r["hub"], verdict=r["verdict"], area_ha=float(r["area_ha"]))
        if not f.exists():
            rec.update(structure_on="", window_from="", window_to="", spread_months="", quarter="", base_db="", note="no radar series")
        else:
            piv = pd.read_csv(f, index_col=0)
            col = next(c for c in piv.columns if c.startswith("VV:"))
            rec.update(date_entry(piv[col]))
            rec["note"] = "before the 2021-2026 scan window" if rec["structure_on"] and rec["structure_on"] < "2021-01" else ""
        entries.append(rec)

    agg = defaultdict(lambda: dict(n=0, area_ha=0.0, n_firm=0, area_firm_ha=0.0, area_possible_ha=0.0, entries=[]))
    for e in entries:
        if not e["structure_on"]:
            continue
        key = (e["hub"], e["quarter"], e["verdict"])
        a = agg[key]
        a["n"] += 1
        a["area_ha"] += e["area_ha"]
        a["entries"].append(e["site_id"])
        q_lo, q_hi = quarter_of(e["window_from"]), quarter_of(e["window_to"])
        if q_lo == q_hi == e["quarter"]:
            a["n_firm"] += 1
            a["area_firm_ha"] += e["area_ha"]
        for q in quarters_between(q_lo, q_hi):
            agg[(e["hub"], q, e["verdict"])]["area_possible_ha"] += e["area_ha"]
    rows = []
    for (hub, q, verdict), a in sorted(agg.items()):
        rows.append(dict(hub=hub, quarter=q, verdict=verdict, n=a["n"], area_ha=round(a["area_ha"], 1),
                         n_firm=a["n_firm"], area_firm_ha=round(a["area_firm_ha"], 1),
                         area_possible_ha=round(a["area_possible_ha"], 1), entries=";".join(a["entries"])))
    return entries, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", default="data/cn_radar_review.csv")
    ap.add_argument("--s1-dir", default="results_s1")
    ap.add_argument("--out", default="results_cn/construction_index.csv")
    args = ap.parse_args()
    entries, rows = build(ROOT / args.review, ROOT / args.s1_dir)
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    ecols = ["site_id", "hub", "verdict", "area_ha", "structure_on", "window_from", "window_to", "spread_months", "quarter", "base_db", "note"]
    with open(out.with_name(out.stem + "_entries.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ecols)
        w.writeheader()
        w.writerows([{k: e.get(k, "") for k in ecols} for e in entries])
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    df = pd.DataFrame(rows)
    print(f"{len(entries)} structures, {sum(1 for e in entries if e['structure_on'])} dated")
    spread = [e["spread_months"] for e in entries if e["structure_on"]]
    print(f"dating spread, onset to plateau: median {pd.Series(spread).median():.0f} months, max {max(spread)}; "
          f"{sum(1 for e in entries if e['structure_on'] and quarter_of(e['window_from']) == quarter_of(e['window_to']))} of {len(spread)} firm within one quarter")
    piv = df[df.n > 0].pivot_table(index=["hub", "quarter"], columns="verdict", values="area_ha", aggfunc="sum", fill_value=0)
    print(piv.round(1).to_string())
    print(f"wrote {out} and {out.with_name(out.stem + '_entries.csv')}")


if __name__ == "__main__":
    main()
