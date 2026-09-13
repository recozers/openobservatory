"""Recall check for the night-lights change scan: for each region CSV from tools/ntl_scan.py, report the nearest
blob to each known campus in that region (distance, rank, brightness), and the number of blobs (false-positive load).

    python tools/scan_check.py
"""
from __future__ import annotations

import glob

import numpy as np
import pandas as pd

KNOWN = {
    "abilene_tx": [("stargate_abilene", 32.500, -99.783)],
    "memphis": [("colossus_memphis", 35.0592, -90.1557), ("colossus2_southaven", 34.998, -90.035)],
    "indiana_rainier": [("rainier_in", 41.679, -86.471)],
    "wisconsin_fairwater": [("fairwater_wi", 42.6736, -87.9001)],
    "louisiana_hyperion": [("hyperion_la", 32.478, -91.63)],
    "ohio_newalbany": [("prometheus_oh", 40.062, -82.746)],
    "inner_mongolia": [("cn_ulanqab_park", 41.055, 113.16), ("cn_horinger_cloud_valley", 40.545, 111.805), ("cn_zhangbei_alibaba", 41.20, 114.73)],
    "ningxia_gansu": [("zhongwei_hub", 37.6, 105.2), ("qingyang_hub", 35.73, 107.64)],
    "guizhou": [("guian_hub", 26.4, 106.42)],
    "chongqing": [("chongqing_hub", 29.85, 106.62)],
    "china_hubs": [("cn_ulanqab_park", 41.055, 113.16), ("cn_horinger_cloud_valley", 40.545, 111.805), ("cn_zhangbei_alibaba", 41.20, 114.73),
                   ("zhongwei_hub", 37.6, 105.2), ("qingyang_hub", 35.73, 107.64), ("guian_hub", 26.4, 106.42), ("chongqing_hub", 29.85, 106.62),
                   ("nscc_wuxi", 31.54861, 120.24804), ("nscc_guangzhou", 23.07306, 113.38861)],
}


def km(lat1, lon1, lat2, lon2):
    return 6371 * np.sqrt(((lat2 - lat1) * np.pi / 180) ** 2 + ((lon2 - lon1) * np.pi / 180 * np.cos(lat1 * np.pi / 180)) ** 2)


def main():
    for f in sorted(glob.glob("results_ntl/scan_*.csv")):
        name = f.split("scan_")[1][:-4]
        d = pd.read_csv(f)
        print(f"\n{name}: {len(d)} blobs")
        if len(d):
            print(d.head(5).to_string(index=False))
        for sid, la, lo in KNOWN.get(name, []):
            if not len(d):
                print(f"  {sid}: no blobs"); continue
            dist = km(la, lo, d.lat, d.lon)
            i = int(dist.idxmin())
            print(f"  {sid}: nearest blob {dist.min():.1f} km, rank {i + 1}/{len(d)}, {d.loc[i, 'n_px']} px, early {d.loc[i, 'early']} late {d.loc[i, 'late']} diff {d.loc[i, 'diff']}")


if __name__ == "__main__":
    main()
