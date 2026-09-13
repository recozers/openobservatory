"""Line up construction dates from the three sources per hall: Sentinel-2 roof-on month (validated), Sentinel-1
VV structure-on month (pilot) and the site's VIIRS lit-up month (pilot).

    python tools/pilot_compare.py            # all sites with results
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.ntl_timeline import lit_month  # noqa: E402
from tools.s1_timeline import s1_on  # noqa: E402


def main():
    tl_dir = Path("site/data/timeline")
    for tj in sorted(tl_dir.glob("*.json")):
        sid = tj.stem
        tl = json.loads(tj.read_text())
        s1f, ntlf = Path(f"results_s1/{sid}.csv"), Path(f"results_ntl/{sid}.csv")
        if not s1f.exists() and not ntlf.exists():
            continue
        print(f"\n== {sid}")
        if ntlf.exists():
            ntl = pd.read_csv(ntlf, index_col=0)
            print(f"  VIIRS lit-up month: {lit_month(ntl['diff'])}   (months {ntl.index[0]}..{ntl.index[-1]}, n={len(ntl)})")
        if s1f.exists():
            s1 = pd.read_csv(s1f, index_col=0)
            print(f"  {'hall':26s} {'S2 roof-on':>12s}  S1 VV-on")
            for h, ro in tl.get("roof_on", {}).items():
                col = f"VV:{h}"
                print(f"  {h:26s} {str(ro):>12s}  {s1_on(s1[col]) if col in s1 else '-'}")


if __name__ == "__main__":
    main()
