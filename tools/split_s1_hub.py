"""Split a per-hub Sentinel-1 timeline (columns VV:<site_id>, VH:<site_id>) into results_s1/<site_id>.csv files with
columns VV:structure and VH:structure, matching each radar-candidate site's single polygon named "structure".

    python tools/split_s1_hub.py results_s1/horinger_newsites.csv
"""
import sys
from pathlib import Path

import pandas as pd

for f in sys.argv[1:]:
    piv = pd.read_csv(f, index_col=0)
    sids = sorted({c.split(":", 1)[1] for c in piv.columns if ":" in c})
    for sid in sids:
        cols = {f"VV:{sid}": "VV:structure", f"VH:{sid}": "VH:structure"}
        out = piv[[c for c in cols if c in piv.columns]].rename(columns=cols)
        out.to_csv(Path(f).parent / f"{sid}.csv")
    print(f"{f}: {len(sids)} site files")
