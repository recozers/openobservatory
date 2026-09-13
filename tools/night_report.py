"""Night-time / diurnal analysis of the ECOSTRESS observations, and the questions
that decide what is pursuable:

  1. per-site night vs day anomaly, diurnal amplitude, frames per year
  2. within-site steps (night and day separately) where the documented load changed
  3. cross-site fit on night frames only (model.py on a night-only CSV)
  4. detection: data-centre halls vs control roofs (night ΔT, day ΔT, amplitude)
  5. detectability: residual night-time noise per site -> minimum detectable step

    python tools/night_report.py --eco data/observations_eco.csv --out results_eco

Writes results_eco/night_report.md, results_eco/site_table.csv, results_eco/within_site.csv,
results_eco/summary.json; runs model.py on night-only and day-only frame subsets.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

MET = ["ta_c", "wind_ms", "tw_c"]
NIGHT_SUN, DAY_SUN = -6.0, 20.0


def it_mw(cap, basis, pue):
    fac = pd.Series(basis).isin(["facility_design", "grid_connection"]).to_numpy()
    cap = pd.to_numeric(pd.Series(cap), errors="coerce").to_numpy(dtype=float)
    return np.where(fac, cap / np.asarray(pue, dtype=float), cap)


def hall_frames(obs: pd.DataFrame, sites: pd.DataFrame, ptype="hall") -> pd.DataFrame:
    d = obs[obs.ptype == ptype].copy()
    d["w"] = d.n_valid_poly.astype(float)
    d["dtw"] = d.delta_t_k * d.w
    first = [c for c in ["sensor", "product_id", "local_solar_hour", "sun_elev_deg", "t_bg_k", "scene_cloud_cover", "capacity_mw", "capacity_basis", "capacity_tier",
                         "view_zenith_deg", "day_night"] + MET if c in d]
    g = d.groupby(["site_id", "datetime_utc"], as_index=False).agg(**{c: (c, "first") for c in first}, dtw=("dtw", "sum"), w=("w", "sum"))
    g["dT"] = g.dtw / g.w
    g["t"] = pd.to_datetime(g.datetime_utc, utc=True, format="ISO8601")
    g["year"] = g.t.dt.year
    g["season"] = pd.cut(g.t.dt.month, [0, 3, 6, 9, 12], labels=["JFM", "AMJ", "JAS", "OND"])
    g["tod"] = np.where(g.sun_elev_deg < NIGHT_SUN, "night", np.where(g.sun_elev_deg > DAY_SUN, "day", "twilight"))
    s = sites.set_index("site_id")
    g["is_control"] = g.site_id.str.startswith("ctrl_")
    g["tier"] = g.site_id.map(s.capacity_tier).fillna("U")
    g["pue"] = pd.to_numeric(g.site_id.map(s.pue_assumed), errors="coerce").fillna(1.2)
    if "capacity_mw" in g:
        g["it_mw"] = it_mw(g.capacity_mw, g.capacity_basis, g.pue)
    else:
        g["it_mw"] = np.nan
    return g


def harmonic(g: pd.DataFrame):
    """ΔT = a + b1 cos(ωh) + b2 sin(ωh): amplitude and hour of maximum of the diurnal cycle."""
    if len(g) < 12 or g.local_solar_hour.nunique() < 6:
        return np.nan, np.nan, np.nan
    w = 2 * np.pi / 24
    X = np.column_stack([np.ones(len(g)), np.cos(w * g.local_solar_hour), np.sin(w * g.local_solar_hour)])
    beta, *_ = np.linalg.lstsq(X, g.dT.to_numpy(), rcond=None)
    amp = float(np.hypot(beta[1], beta[2]))
    peak_h = float((np.arctan2(beta[2], beta[1]) / w) % 24)
    resid = g.dT.to_numpy() - X @ beta
    return amp, peak_h, float(np.std(resid))


def ols_periods(g: pd.DataFrame, add_sun: bool):
    """ΔT ~ period + season + met (+ sun): effects of each later period vs the first."""
    import statsmodels.formula.api as smf
    g = g.dropna(subset=["it_mw"]).copy()
    if g.it_mw.nunique() < 2 or len(g) < 10:
        return None
    levels = sorted(g.it_mw.unique())
    g["period"] = pd.Categorical(g.it_mw.map(lambda v: f"{v:.1f}"), categories=[f"{v:.1f}" for v in levels])
    terms = ["C(period)", "C(season)"] + [c for c in MET if c in g and g[c].notna().mean() > 0.8] + (["sun_elev_deg"] if add_sun else [])
    try:
        m = smf.ols("dT ~ " + " + ".join(terms), data=g).fit()
    except Exception:
        return None
    eff = {}
    for k in m.params.index:
        if k.startswith("C(period)"):
            lvl = k.split("T.")[1].rstrip("]")
            eff[lvl] = (float(m.params[k]), float(m.bse[k]), float(m.pvalues[k]))
    # slope in K per IT-MW with the same covariates
    terms2 = ["it_mw", "C(season)"] + [c for c in MET if c in g and g[c].notna().mean() > 0.8] + (["sun_elev_deg"] if add_sun else [])
    m2 = smf.ols("dT ~ " + " + ".join(terms2), data=g).fit()
    return dict(n=int(m.nobs), ref=f"{levels[0]:.1f}", effects=eff, slope=float(m2.params["it_mw"]), slope_se=float(m2.bse["it_mw"]), slope_p=float(m2.pvalues["it_mw"]),
                period_n={f"{v:.1f}": int((g.it_mw == v).sum()) for v in levels})


def residual_sd(g: pd.DataFrame, add_sun: bool) -> float:
    import statsmodels.formula.api as smf
    if len(g) < 8:
        return float("nan")
    terms = ["C(season)"] + [c for c in MET if c in g and g[c].notna().mean() > 0.8] + (["sun_elev_deg"] if add_sun else [])
    try:
        m = smf.ols("dT ~ " + " + ".join(terms), data=g).fit()
        return float(np.sqrt(m.mse_resid))
    except Exception:
        return float(g.dT.std())


def rank_auc(pos, neg):
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    return float(np.mean([(p > n) + 0.5 * (p == n) for p in pos for n in neg]))


def run_model(obs: pd.DataFrame, subset: pd.Series, out_dir: Path, label: str):
    sub = obs[subset].copy()
    if sub.empty:
        return {"label": label, "status": "no frames"}
    p = out_dir / f"obs_{label}.csv"
    sub.to_csv(p, index=False)
    od = out_dir / f"model_{label}"
    od.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([sys.executable, "-W", "ignore", "model.py", "--obs", str(p), "--out", str(od)], capture_output=True, text=True)
    rep = od / "model_report.json"
    txt = "\n".join(l for l in (r.stdout + "\n" + r.stderr).splitlines() if l.strip() and not l.startswith("/") and "Warning" not in l and "res = md" not in l and not l.lstrip().startswith("return ") and "self.score" not in l)
    res = {"label": label, "stdout": txt[-3000:], "returncode": r.returncode}
    if rep.exists():
        j = json.loads(rep.read_text())
        res.update(status=j.get("status"), n_frames_tier_a=j.get("n_frames_tier_a"), n_sites_tier_a=j.get("n_sites_tier_a"), slope=j.get("slope"),
                   kill=j.get("kill_conditions"), variance=j.get("variance_all_frames"), loso=j.get("loso_all_frames"), within_site=j.get("within_site"))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eco", default="data/observations_eco.csv")
    ap.add_argument("--gee", default="data/observations_gee.csv")
    ap.add_argument("--sites", default="data/sites.csv")
    ap.add_argument("--out", default="results_eco")
    ap.add_argument("--slope-k-per-mw", type=float, default=0.008, help="night-time K per IT-MW used for MW detectability (default 0.008: Colossus night step of ~1 K for ~125 IT-MW)")
    ap.add_argument("--rej", default=None, help="rejections CSV, for the roof-only-masking diagnostic (default: derived from --eco path)")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    sites = pd.read_csv(args.sites, dtype=str, keep_default_na=False)
    obs = pd.read_csv(args.eco, dtype={"product_id": str})
    f = hall_frames(obs, sites)
    gee = pd.read_csv(args.gee, dtype={"product_id": str}) if Path(args.gee).exists() else pd.DataFrame()
    fg = hall_frames(gee, sites) if not gee.empty else pd.DataFrame()

    # ---- 1. per-site table
    rows = []
    for sid, g in f.groupby("site_id"):
        n = g[g.tod == "night"]
        d = g[g.tod == "day"]
        amp, peak, _ = harmonic(g)
        yrs = max((g.t.max() - g.t.min()).days / 365.25, 0.5)
        rows.append(dict(site_id=sid, control=bool(g.is_control.iloc[0]), tier=g.tier.iloc[0], frames=len(g), night=len(n), day=len(d), night_per_year=round(len(n) / yrs, 1),
                         night_dT=round(n.dT.mean(), 2) if len(n) else np.nan, night_sd=round(n.dT.std(), 2) if len(n) > 1 else np.nan,
                         day_dT=round(d.dT.mean(), 2) if len(d) else np.nan, day_sd=round(d.dT.std(), 2) if len(d) > 1 else np.nan,
                         diurnal_amp=round(amp, 2), peak_hour=round(peak, 1) if peak == peak else np.nan,
                         night_resid_sd=round(residual_sd(n, False), 2), landsat_day_dT=round(fg[fg.site_id == sid].dT.mean(), 2) if len(fg) and (fg.site_id == sid).any() else np.nan,
                         first=g.t.min().strftime("%Y-%m"), last=g.t.max().strftime("%Y-%m")))
    site_table = pd.DataFrame(rows).sort_values(["control", "site_id"])
    site_table.to_csv(out / "site_table.csv", index=False)

    # ---- 2. within-site steps
    ws = []
    for sid, g in f.groupby("site_id"):
        if g.is_control.iloc[0]:
            continue
        for tod, add_sun in (("night", False), ("day", True)):
            r = ols_periods(g[g.tod == tod], add_sun)
            if r:
                ws.append(dict(site_id=sid, tod=tod, **r))
    within = pd.DataFrame(ws)
    if not within.empty:
        within.to_csv(out / "within_site.csv", index=False)

    # ---- 3. cross-site fits on night-only and day-only frames (model.py)
    night_ids = set(zip(f.loc[f.tod == "night", "site_id"], f.loc[f.tod == "night", "datetime_utc"]))
    day_ids = set(zip(f.loc[f.tod == "day", "site_id"], f.loc[f.tod == "day", "datetime_utc"]))
    key = list(zip(obs.site_id, obs.datetime_utc))
    m_night = run_model(obs, pd.Series([k in night_ids for k in key], index=obs.index), out, "night")
    m_day = run_model(obs, pd.Series([k in day_ids for k in key], index=obs.index), out, "day")

    # ---- 4. detection: halls vs controls
    dc = site_table[~site_table.control & (site_table.night > 0)]
    ct = site_table[site_table.control & (site_table.night > 0)]
    det = dict(n_dc_sites=int(len(dc)), n_control_sites=int(len(ct)),
               auc_night_dT=rank_auc(dc.night_dT, ct.night_dT), auc_day_dT=rank_auc(dc.day_dT, ct.day_dT), auc_amplitude=rank_auc(dc.diurnal_amp, ct.diurnal_amp),
               auc_landsat_day=rank_auc(dc.landsat_day_dT.dropna(), ct.landsat_day_dT.dropna()),
               dc_night_dT=dict(zip(dc.site_id, dc.night_dT)), ctrl_night_dT=dict(zip(ct.site_id, ct.night_dT)))
    # frame-level AUC too (every night frame, pooled)
    fn = f[f.tod == "night"]
    det["auc_night_frames"] = rank_auc(fn[~fn.is_control].dT, fn[fn.is_control].dT)
    # operating data-centre halls only (label present and > 1 MW at the frame date) vs controls
    op = fn[(~fn.is_control) & (fn.it_mw > 1)]
    det["auc_night_frames_operating_only"] = rank_auc(op.dT, fn[fn.is_control].dT)
    det["operating_night_dT_mean"] = float(op.dT.mean()) if len(op) else float("nan")
    det["control_night_dT_mean"] = float(fn[fn.is_control].dT.mean()) if fn.is_control.any() else float("nan")

    # ---- 5. detectability
    slope = args.slope_k_per_mw
    detect = []
    for _, r in site_table[~site_table.control].iterrows():
        sd, npy = r.night_resid_sd, r.night_per_year
        if not (sd == sd and npy and npy > 0):
            continue
        mde_k = 2.8 * sd * np.sqrt(2.0 / npy)  # 80 % power, two-sided 5 %, one year of night frames on each side of a step
        detect.append(dict(site_id=r.site_id, night_resid_sd_k=round(sd, 2), night_frames_per_year=npy, mde_step_k_one_year=round(mde_k, 2),
                           mde_step_mw_at_slope=round(mde_k / slope, 0) if slope and slope > 0 else np.nan))
    detect = pd.DataFrame(detect)

    # ---- 5b. roof-only masking: frames whose background was >= 50 % clear but the roof failed the pixel threshold, night vs day
    rej_path = Path(args.rej) if args.rej else Path(str(args.eco).replace("observations", "rejections"))
    roofmask = pd.DataFrame()
    if rej_path.exists():
        from dcheat.ecostress import solar_elevation_deg
        rj = pd.read_csv(rej_path)
        rj = rj[rj.reason == "polygon_too_cloudy"].copy()
        if len(rj):
            rj["t"] = pd.to_datetime(rj.datetime_utc, utc=True, format="ISO8601")
            sl = sites.set_index("site_id")
            rj["sun"] = [solar_elevation_deg(t, float(sl.loc[s].lat), float(sl.loc[s].lon)) if s in sl.index else np.nan for s, t in zip(rj.site_id, rj.t)]
            rj["tod"] = np.where(rj.sun < NIGHT_SUN, "night", np.where(rj.sun > DAY_SUN, "day", "twilight"))
            rj["bg_clear"] = rj.n_valid_bg / rj.n_total_bg
            rj = rj[rj.bg_clear >= 0.5]
            acc = f.groupby(["site_id", "tod"]).size().rename("accepted")
            rr = rj.groupby(["site_id", "tod"]).datetime_utc.nunique().rename("roof_only_rejected")
            roofmask = pd.concat([acc, rr], axis=1).fillna(0).reset_index()
            roofmask["roof_only_rejection_rate"] = (roofmask.roof_only_rejected / (roofmask.roof_only_rejected + roofmask.accepted)).round(2)
            roofmask = roofmask[roofmask.tod.isin(["night", "day"])]
            roofmask.to_csv(out / "roof_only_masking.csv", index=False)

    summary = dict(n_obs_rows=int(len(obs)), n_frames=int(len(f)), n_night=int((f.tod == "night").sum()), n_day=int((f.tod == "day").sum()),
                   sites=int(f.site_id.nunique()), slope_used_k_per_mw=slope, detection=det,
                   cross_site_night={k: v for k, v in m_night.items() if k != "stdout"}, cross_site_day={k: v for k, v in m_day.items() if k != "stdout"})
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=str))

    # ---- markdown
    L = []
    L.append(f"# Night-time report\n\n{len(obs)} ECOSTRESS rows, {len(f)} hall frames over {f.site_id.nunique()} sites; {summary['n_night']} night frames (sun < {NIGHT_SUN:.0f} deg), {summary['n_day']} day frames (sun > {DAY_SUN:.0f} deg).\n")
    L.append("## 1. Sites: night vs day anomaly, diurnal amplitude\n")
    L.append(site_table.to_markdown(index=False))
    L.append("\n## 2. Within-site steps where the documented load changed\n")
    if within.empty:
        L.append("none")
    else:
        for _, r in within.iterrows():
            eff = "; ".join(f"{k} MW: {v[0]:+.2f} ± {v[1]:.2f} K (p={v[2]:.3f})" for k, v in r.effects.items())
            L.append(f"- **{r.site_id} / {r.tod}** (n={r.n}, ref {r.ref} MW; frames per level {r.period_n}): {eff}; slope {r.slope:+.4f} ± {r.slope_se:.4f} K per IT-MW (p={r.slope_p:.3f})")
    L.append("\n## 3. Cross-site fit, night-only vs day-only frames (model.py)\n")
    for m in (m_night, m_day):
        L.append(f"### {m['label']}\n```\n{m.get('stdout','')}\n```")
    L.append("\n## 4. Detection: data-centre halls vs control roofs\n")
    L.append("```\n" + json.dumps(det, indent=1, default=str) + "\n```")
    L.append("\n## 5. Detectability of a load step from night frames (one year each side)\n")
    L.append(detect.to_markdown(index=False) if len(detect) else "n/a")
    L.append(f"\nslope used for MW conversion: {slope} K per IT-MW (assumption, see --slope-k-per-mw)\n")
    L.append("\n## 5b. Roof-only masking (background >= 50 % clear, roof below pixel threshold): a load-correlated bias check\n")
    L.append(roofmask.to_markdown(index=False) if len(roofmask) else "n/a")
    (out / "night_report.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
