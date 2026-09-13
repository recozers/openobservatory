"""Hall-morphology classifier for radar candidates: is a new large structure a data-hall complex?

Training set: results_campus/train_features.csv (OSM-tagged data-centre footprints vs large warehouse/factory roofs,
satellite-embedding means at 50 m and 250 m, 2024). Model: standardised logistic regression, C chosen by region-grouped
cross-validation. Application: candidate features from tools/cand_features.py. Labels for the candidates come from
geometry (a candidate intersecting a known hall polygon is positive), from files named neg_* or china/blob* (industrial
negatives) and from hand-verified ranks; everything else is unlabeled and only ranked.

    python tools/cand_classifier.py --features results_cand/candidate_features.csv --out results_cand/scores.csv
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import shape
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

SITE_OF_FILE = {"pos_abilene": "stargate_abilene", "pos_rainier": "rainier_in", "pos_fairwater": "fairwater_wi", "pos_prometheus": "prometheus_oh",
                "pos_hyperion": "hyperion_la", "ulanqab": "cn_ulanqab_park", "horinger": "cn_horinger_cloud_valley", "zhangbei": "cn_zhangbei_alibaba"}
VERIFIED_POS = {("horinger", 1), ("horinger", 2), ("horinger", 3), ("ulanqab", 1), ("ulanqab", 2)}   # chips inspected 13 Sep 2026
VERIFIED_NEG = {("ulanqab", 3)}                                                                      # photovoltaic compound
# industrial negative boxes: only candidates within NEG_RADIUS_KM of the plant are labeled negative, because the Intel Ohio
# box overlaps the New Albany data-centre district and north Phoenix has data centres of its own
NEG_CENTRES = {"neg_hyundai_ga": (32.16, -81.34), "neg_blueoval_tn": (35.47, -89.40), "neg_intel_oh": (40.14, -82.69), "neg_tsmc_az": (33.68, -112.11)}
NEG_RADIUS_KM = 3.0


def km(lat1, lon1, lat2, lon2):
    return 6371 * np.sqrt(((lat2 - lat1) * np.pi / 180) ** 2 + ((lon2 - lon1) * np.pi / 180 * np.cos(lat1 * np.pi / 180)) ** 2)


def hall_union(site):
    p = Path("data/polygons") / f"{site}.geojson"
    if not p.exists():
        return None
    from shapely.ops import unary_union
    g = json.load(open(p))
    return unary_union([shape(f["geometry"]) for f in g["features"] if f["properties"].get("ptype") == "hall"])


def label_candidates(df):
    labels, groups = [], []
    halls = {}
    for _, r in df.iterrows():
        f = Path(r.file)
        key = f.stem.replace("_candidates", "")
        grp = key
        lab = np.nan
        if "china/" in r.file:
            lab = 0.0
        elif key in NEG_CENTRES:
            la, lo = NEG_CENTRES[key]
            lab = 0.0 if km(la, lo, r.lat, r.lon) <= NEG_RADIUS_KM else np.nan
        else:
            site = SITE_OF_FILE.get(key)
            if site:
                if site not in halls:
                    halls[site] = hall_union(site)
                gj = json.load(open(f))
                geom = next((shape(ft["geometry"]) for ft in gj["features"] if ft["properties"].get("name") == r["name"]), None)
                if halls[site] is not None and geom is not None and geom.intersects(halls[site]):
                    lab = 1.0
        if (key, r["rank"]) in VERIFIED_POS:
            lab = 1.0
        if (key, r["rank"]) in VERIFIED_NEG:
            lab = 0.0
        labels.append(lab); groups.append(grp)
    df = df.copy(); df["label"] = labels; df["group"] = groups
    return df


def candidates_only(cand, feat_cols, out):
    """Train on the labeled candidates themselves (hard negatives: new industrial structures; positives: halls at known
    campuses) and validate leave-one-group-out, where a group is a site box or a national blob."""
    lab = cand.dropna(subset=["label"]).copy()
    X, y, g = lab[feat_cols].values, lab.label.values.astype(int), lab.group.values
    print(f"\ncandidate-only training: {len(lab)} labeled ({int(y.sum())} positives) in {len(set(g))} groups")
    from sklearn.model_selection import LeaveOneGroupOut
    best = None
    for C in (0.01, 0.03, 0.1, 0.3, 1.0):
        oof = np.full(len(y), np.nan)
        for tri, tei in LeaveOneGroupOut().split(X, y, g):
            if len(np.unique(y[tri])) < 2:
                continue
            m = make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=3000, class_weight="balanced")).fit(X[tri], y[tri])
            oof[tei] = m.predict_proba(X[tei])[:, 1]
        ok = ~np.isnan(oof)
        auc = roc_auc_score(y[ok], oof[ok])
        kept = [(thr, int(((y == 1) & (oof >= thr)).sum()), int(((y == 0) & (oof >= thr)).sum())) for thr in (0.5, 0.8, 0.9)]
        print(f"  C={C}: leave-one-group-out AUC {auc:.3f}; kept (thr, pos, neg): {kept}")
        if best is None or auc > best[1]:
            best = (C, auc, oof.copy())
    model = make_pipeline(StandardScaler(), LogisticRegression(C=best[0], max_iter=3000, class_weight="balanced")).fit(X, y)
    cand = cand.copy()
    cand["score_cand"] = model.predict_proba(cand[feat_cols].values)[:, 1]
    cand.loc[lab.index, "score_oof"] = best[2]
    print(f"  chosen C={best[0]}; positives' out-of-fold scores: {np.round(np.sort(best[2][y == 1]), 2).tolist()}")
    return cand, model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", nargs="+", required=True)
    ap.add_argument("--train", default="results_campus/train_features.csv")
    ap.add_argument("--out", default="results_cand/scores.csv")
    ap.add_argument("--scale", default="r", help="embedding scales to use: r (50 m), m (250 m) or rm")
    args = ap.parse_args()
    suffixes = tuple(f"_{c}" for c in args.scale)
    cand = pd.concat([pd.read_csv(f) for f in args.features], ignore_index=True)
    feat_cols = [c for c in cand.columns if c.startswith("A") and c.endswith(suffixes)]
    cand = cand.dropna(subset=feat_cols)
    cand = label_candidates(cand)
    cand["score"] = np.nan
    if not Path(args.train).exists():
        # the OSM-trained stage (results_campus/train_features.csv, not in the public repo) is optional: it failed to
        # transfer (AUC 0.70 on new industrial structures), and the candidate-trained model below is the one in use
        print(f"no {args.train}: skipping the OSM-trained model", file=sys.stderr)
        cand, _ = candidates_only(cand, feat_cols, args.out)
        write_scores(cand, args.out)
        return
    tr = pd.read_csv(args.train)
    tr = tr[tr.src.isin(["osm_dc", "osm_roof"])]
    tr = tr.dropna(subset=feat_cols)
    # folds grouped by 5-degree cells so each held-out fold has both classes from the same places
    cells = (tr.lat // 5).astype(int).astype(str) + "_" + (tr.lon // 5).astype(int).astype(str)
    X, y, g = tr[feat_cols].values, tr.label.values, cells.values
    print(f"training rows {len(tr)} (positives {int(y.sum())}), features {len(feat_cols)}, {len(set(g))} spatial cells")
    best = None
    for C in (0.003, 0.01, 0.03, 0.1, 0.3):
        aucs = []
        for tri, tei in GroupKFold(n_splits=5).split(X, y, g):
            if len(np.unique(y[tei])) < 2:
                continue
            m = make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=2000)).fit(X[tri], y[tri])
            aucs.append(roc_auc_score(y[tei], m.predict_proba(X[tei])[:, 1]))
        print(f"  C={C}: cell-grouped CV AUC {np.mean(aucs):.3f}")
        if best is None or np.mean(aucs) > best[1]:
            best = (C, np.mean(aucs))
    model = make_pipeline(StandardScaler(), LogisticRegression(C=best[0], max_iter=2000)).fit(X, y)
    cand["score"] = model.predict_proba(cand[feat_cols].values)[:, 1]
    lab = cand.dropna(subset=["label"])
    if lab.label.nunique() == 2:
        print(f"\nlabeled candidates: {int((lab.label == 1).sum())} positives, {int((lab.label == 0).sum())} negatives; AUC {roc_auc_score(lab.label, lab.score):.3f}")
        for thr in (0.5, 0.7, 0.9):
            tp = int(((lab.label == 1) & (lab.score >= thr)).sum()); fp = int(((lab.label == 0) & (lab.score >= thr)).sum())
            print(f"  score >= {thr}: {tp}/{int((lab.label == 1).sum())} positives kept, {fp}/{int((lab.label == 0).sum())} negatives kept")
    cand, _ = candidates_only(cand, feat_cols, args.out)
    write_scores(cand, args.out)


def write_scores(cand, out):
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    cand.sort_values("score_cand", ascending=False).to_csv(out, index=False)
    cand = cand.copy()
    cand["key"] = cand.file.map(lambda f: Path(f).stem.replace("_candidates", ""))
    for key, gdf in cand.groupby("key"):
        if key.startswith("blob"):
            continue
        top = gdf.sort_values("score_cand", ascending=False).head(6)
        print(f"\n{key}: {len(gdf)} candidates; top by candidate-trained score (score_oof = held-out where labeled):")
        print(top[["rank", "area_ha", "rise_db", "bright", "score", "score_cand", "score_oof", "label"]].round(3).to_string(index=False))
    blobs = cand[cand.key.str.startswith("blob")]
    if len(blobs):
        print(f"\nnational blobs: {len(blobs)} candidates; {int((blobs.score_cand >= 0.9).sum())} score >= 0.9, {int((blobs.score_cand >= 0.5).sum())} >= 0.5")
        print(blobs.sort_values("score_cand", ascending=False).head(8)[["file", "rank", "area_ha", "bright", "score_cand", "score_oof"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
