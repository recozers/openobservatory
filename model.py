#!/usr/bin/env python
"""Stage 3: observation CSV in, fitted model + leave-one-site-out report out.

    python model.py                      # defaults: data/observations.csv -> results/
    python model.py --ptype substation   # treat the substation polygons as the observable

Design (see README for the reasoning):

* Observable:  ΔT (K) per acquisition, aggregated over the polygons of one
  type at a site (valid-pixel weighted).
* Primary model:  ΔT ~ capacity_density + met covariates + cooling_arch + (1 | site)
  fitted with statsmodels MixedLM on Tier A sites only.  "capacity_density"
  is documented IT-equivalent MW per hectare of measured roof: a roof's
  temperature excess scales with heat flux per unit area, not with total MW.
  A total-MW variant is fitted for comparison.
* Conditioning comparison: the same model with met covariates dropped, fitted
  only on frames in a narrow weather window (clear, low wind, mild ambient).
* Validation: leave-one-site-out only.  For the held-out site the fitted
  relation is inverted to an implied capacity density from its mean ΔT, and
  compared with the documented value.  Baselines: constant (mean of the
  other sites) and geometry-only (log capacity ~ log roof area; or cooling
  unit counts when a `cooling_units` column is present in sites.csv).
* Kill conditions, evaluated and written into the report:
    1. LOSO error of the thermal model does not beat the geometry baseline.
    2. Met covariates explain more of the variance than capacity does.
* Q̂ for every site (Tier A, B, unknown, China): implied heat rejection with
  an interval that includes residual scatter, coefficient uncertainty and the
  between-site random-effect variance.  U = Q̂ / (C × PUE) is reported only
  where capacity provenance is Tier A.
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"

MET_COVARIATES = ["ta_c", "wind_ms", "tw_c", "sun_elev_deg"]
TIER_A = {"A1", "A2"}


# --------------------------------------------------------------------------
# data preparation
# --------------------------------------------------------------------------

def load_inputs(obs_path, sites_path, polygons_dir):
    obs = pd.read_csv(obs_path, dtype={"product_id": str})
    sites = pd.read_csv(sites_path, dtype=str).fillna("")
    for c in ("lat", "lon", "pue_assumed", "capacity_mw"):
        sites[c] = pd.to_numeric(sites[c], errors="coerce")
    # polygon areas by type
    from dcheat import geom as G
    areas = {}
    for sid in sites.site_id:
        p = Path(polygons_dir) / f"{sid}.geojson"
        if p.exists():
            s = sites.set_index("site_id").loc[sid]
            polys = G.load_site_polygons(p)
            areas[sid] = {k: v / 1e4 for k, v in G.polygon_areas_m2(polys, float(s.lon), float(s.lat)).items()}  # hectares
    return obs, sites, areas


def aggregate_frames(obs: pd.DataFrame, ptype: str) -> pd.DataFrame:
    """One row per (site, acquisition) for the chosen polygon type; ΔT is the
    valid-pixel-weighted mean over that type's polygons."""
    d = obs[obs.ptype == ptype].copy()
    if d.empty:
        return d
    d["w"] = d["n_valid_poly"]
    d["dtw"] = d["delta_t_k"] * d["w"]
    keep_first = ["site_id", "datetime_utc", "product_id", "sensor", "local_solar_hour", "t_bg_k", "t_bg_sd_k", "n_valid_bg", "n_total_bg",
                  "scene_cloud_cover", "sun_elev_deg", "ta_c", "td_c", "rh_pct", "wind_ms", "q_kgkg", "tw_c", "capacity_mw", "capacity_basis", "capacity_tier"]
    keep_first = [c for c in keep_first if c in d]
    g = d.groupby(["site_id", "datetime_utc"], as_index=False)
    out = g.agg(**{c: (c, "first") for c in keep_first if c not in ("site_id", "datetime_utc")},
                dtw=("dtw", "sum"), w=("w", "sum"), n_valid_poly=("n_valid_poly", "sum"), n_total_poly=("n_total_poly", "sum"),
                n_polygons=("polygon", "nunique"))
    out["delta_t_k"] = out["dtw"] / out["w"]
    out["valid_frac_poly"] = out["n_valid_poly"] / out["n_total_poly"]
    return out.drop(columns=["dtw", "w"])


def attach_site_info(frames: pd.DataFrame, sites: pd.DataFrame, areas: dict, ptype: str) -> pd.DataFrame:
    s = sites.set_index("site_id")
    f = frames.copy()
    f["cooling_arch"] = f.site_id.map(s.cooling_arch).fillna("unknown")
    f["pue_assumed"] = f.site_id.map(s.pue_assumed).fillna(1.2)
    f["site_tier"] = f.site_id.map(s.capacity_tier).fillna("U")
    f["area_ha"] = f.site_id.map(lambda x: areas.get(x, {}).get(ptype, np.nan))
    # IT-equivalent capacity: facility-basis numbers are divided by the assumed PUE
    fac = f.capacity_basis.isin(["facility_design", "grid_connection"])
    f["it_mw"] = np.where(fac, f.capacity_mw / f.pue_assumed, f.capacity_mw)
    f["density"] = f["it_mw"] / f["area_ha"]          # MW per hectare of measured roof
    f["log_it_mw"] = np.log(f["it_mw"])
    f["tier_a"] = f.capacity_tier.isin(TIER_A) & f.it_mw.notna()
    return f


def conditioned_mask(f: pd.DataFrame, cfg) -> pd.Series:
    """Narrow-window frames: clear, low wind, ambient in a band and — because
    Landsat never observes at night — low solar elevation as the closest
    available proxy for 'night' (roof solar loading small)."""
    m = (f.wind_ms < cfg["cond_wind_max"]) & (f.ta_c > cfg["cond_ta_min"]) & (f.ta_c < cfg["cond_ta_max"])
    m &= f.scene_cloud_cover < cfg["cond_cloud_max"]
    m &= f.valid_frac_poly >= cfg["cond_valid_frac"]
    if "sun_elev_deg" in f:
        m &= f.sun_elev_deg < cfg["cond_sun_max"]
    return m.fillna(False)


# --------------------------------------------------------------------------
# models
# --------------------------------------------------------------------------

def _design(f: pd.DataFrame, capacity_col: str, met: list[str], arch: bool):
    X = pd.DataFrame({"intercept": 1.0, capacity_col: f[capacity_col].values}, index=f.index)
    for c in met:
        X[c] = f[c].values
    if arch:
        for a in sorted(f.cooling_arch.unique())[1:]:  # first level is the reference
            X[f"arch_{a}"] = (f.cooling_arch == a).astype(float).values
    return X


def fit_mixed(f: pd.DataFrame, capacity_col: str, met: list[str], arch: bool):
    """MixedLM with a random intercept per site.  Falls back to OLS with a
    warning if the mixed fit fails to converge (tiny n)."""
    import statsmodels.api as sm
    X = _design(f, capacity_col, met, arch)
    y = f["delta_t_k"].values
    groups = f["site_id"].values
    try:
        md = sm.MixedLM(y, X, groups=groups)
        res = md.fit(reml=True, method=["lbfgs", "powell"], maxiter=500)
        re_sd = float(np.sqrt(res.cov_re.iloc[0, 0])) if res.cov_re.shape[0] else 0.0
        resid_sd = float(np.sqrt(res.scale))
        return dict(kind="mixedlm", params=res.params.to_dict(), bse=res.bse.to_dict(), re_sd=re_sd, resid_sd=resid_sd,
                    cov=res.cov_params().loc[X.columns, X.columns].values, cols=list(X.columns), converged=bool(res.converged), llf=float(res.llf))
    except Exception as e:  # pragma: no cover
        res = sm.OLS(y, X).fit()
        return dict(kind=f"ols_fallback({type(e).__name__})", params=res.params.to_dict(), bse=res.bse.to_dict(), re_sd=float("nan"),
                    resid_sd=float(np.sqrt(res.scale)), cov=res.cov_params().values, cols=list(X.columns), converged=True, llf=float(res.llf))


def predict_fixed(model: dict, f: pd.DataFrame, capacity_col: str, met: list[str], arch: bool) -> np.ndarray:
    X = _design(f, capacity_col, met, arch)
    for c in model["cols"]:
        if c not in X:
            X[c] = 0.0
    X = X[model["cols"]]
    beta = np.array([model["params"][c] for c in model["cols"]])
    return X.values @ beta


def variance_decomposition(f: pd.DataFrame, capacity_col: str, met: list[str], arch: bool) -> dict:
    """Partial R² of the capacity term and of the met block in a fixed-effects
    OLS (site intercepts absorbed where identifiable), plus the between-site
    share of ΔT variance.  Used for kill condition 2."""
    import statsmodels.api as sm
    y = f["delta_t_k"].values
    full = _design(f, capacity_col, met, arch)
    r2_full = sm.OLS(y, full).fit().rsquared
    no_cap = full.drop(columns=[capacity_col])
    r2_nocap = sm.OLS(y, no_cap).fit().rsquared
    no_met = full.drop(columns=[c for c in met if c in full])
    r2_nomet = sm.OLS(y, no_met).fit().rsquared
    cap_only = full[["intercept", capacity_col]]
    r2_cap_only = sm.OLS(y, cap_only).fit().rsquared
    met_only = full[["intercept"] + [c for c in met if c in full]]
    r2_met_only = sm.OLS(y, met_only).fit().rsquared
    site_means = f.groupby("site_id").delta_t_k.transform("mean")
    between = float(np.var(site_means) / np.var(y)) if np.var(y) > 0 else float("nan")
    return dict(r2_full=float(r2_full), partial_r2_capacity=float(r2_full - r2_nocap), partial_r2_met=float(r2_full - r2_nomet),
                r2_capacity_only=float(r2_cap_only), r2_met_only=float(r2_met_only), between_site_share=between)


# --------------------------------------------------------------------------
# leave-one-site-out
# --------------------------------------------------------------------------

def slope_identified(model: dict, capacity_col: str) -> bool:
    """The inversion ΔT → capacity is only meaningful if the slope is
    distinguishable from zero (|b| > 2 SE).  Otherwise the implied capacity
    is unbounded and is reported as not identified rather than as a number."""
    b, se = model["params"][capacity_col], model["bse"].get(capacity_col, np.nan)
    return bool(se == se and abs(b) > 2 * se)


def invert_capacity(model: dict, f_site: pd.DataFrame, capacity_col: str, met: list[str], arch: bool):
    """Implied capacity (density or log MW) for one site from its frames:
    solve mean(ΔT_obs − ΔT_pred(capacity=0)) = b × capacity.  Returns
    (estimate, standard error, identified)."""
    b = model["params"][capacity_col]
    f0 = f_site.copy()
    f0[capacity_col] = 0.0
    base = predict_fixed(model, f0, capacity_col, met, arch)
    resid = f_site["delta_t_k"].values - base
    ident = slope_identified(model, capacity_col)
    if abs(b) < 1e-9:
        return np.nan, np.nan, False
    est = float(np.mean(resid) / b)
    # uncertainty: residual scatter / sqrt(n) plus between-site sd, both divided by |b|; plus slope uncertainty
    n = len(f_site)
    se_noise = np.sqrt(model["resid_sd"] ** 2 / max(n, 1) + (0.0 if np.isnan(model["re_sd"]) else model["re_sd"] ** 2)) / abs(b)
    se_slope = abs(est) * model["bse"].get(capacity_col, 0.0) / abs(b)
    return est, float(np.hypot(se_noise, se_slope)), ident


def loso(f: pd.DataFrame, capacity_col: str, met: list[str], arch: bool, sites_df: pd.DataFrame, areas: dict, ptype: str, label: str):
    rows = []
    tier_sites = sorted(f.site_id.unique())
    if len(tier_sites) < 3:
        return pd.DataFrame(rows)
    for s in tier_sites:
        train, test = f[f.site_id != s], f[f.site_id == s]
        if train.site_id.nunique() < 2:
            continue
        m = fit_mixed(train, capacity_col, met, arch)
        est, se, ident = invert_capacity(m, test, capacity_col, met, arch)
        truth = float(test[capacity_col].iloc[0])
        area = float(test["area_ha"].iloc[0])
        if capacity_col == "density":
            est_mw, truth_mw = est * area, truth * area
            lo_mw, hi_mw = (est - 1.64 * se) * area, (est + 1.64 * se) * area
        else:
            est_mw, truth_mw = float(np.exp(est)), float(np.exp(truth))
            lo_mw, hi_mw = float(np.exp(est - 1.64 * se)), float(np.exp(est + 1.64 * se))
        ident = bool(ident and est_mw == est_mw and est_mw > 0)
        # baselines: constant (mean log capacity of the other sites) and geometry (log C ~ log area)
        tr_sites = train.groupby("site_id").first()
        const_mw = float(np.exp(np.log(tr_sites.it_mw).mean()))
        geo_mw = geometry_baseline(tr_sites, area, sites_df, s)
        rows.append(dict(model=label, site_id=s, n_frames=len(test), truth_mw=truth_mw,
                         thermal_mw=est_mw if ident else np.nan, thermal_lo_mw=lo_mw if ident else np.nan, thermal_hi_mw=hi_mw if ident else np.nan,
                         thermal_identified=ident, thermal_raw_mw=est_mw,
                         const_mw=const_mw, geometry_mw=geo_mw,
                         thermal_abs_log_err=abs(np.log(est_mw / truth_mw)) if ident else np.nan,
                         const_abs_log_err=abs(np.log(const_mw / truth_mw)), geometry_abs_log_err=abs(np.log(geo_mw / truth_mw)) if geo_mw == geo_mw else np.nan,
                         slope=m["params"][capacity_col], slope_se=m["bse"].get(capacity_col, np.nan), converged=m["converged"]))
    return pd.DataFrame(rows)


def geometry_baseline(tr_sites: pd.DataFrame, area_ha: float, sites_df: pd.DataFrame, held_out: str) -> float:
    """log C ~ a + b log(area): the closest available analogue of a
    cooling-equipment count at 10 m resolution.  If `cooling_units` exists
    for all training sites and the held-out site, use that instead."""
    cu = sites_df.set_index("site_id").get("cooling_units")
    tr = tr_sites[["it_mw", "area_ha"]].dropna()
    if cu is not None:
        cu = pd.to_numeric(cu, errors="coerce")
        if cu.reindex(tr.index).notna().all() and pd.notna(cu.get(held_out, np.nan)) and len(tr) >= 2:
            x = np.log(cu.reindex(tr.index).values)
            b, a = np.polyfit(x, np.log(tr.it_mw.values), 1)
            return float(np.exp(a + b * np.log(cu[held_out])))
    if len(tr) < 2 or np.isnan(area_ha):
        return float("nan")
    if len(tr) == 2:
        # two points: use proportional scaling through the mean density
        return float(np.exp(np.log(tr.it_mw / tr.area_ha).mean()) * area_ha)
    b, a = np.polyfit(np.log(tr.area_ha.values), np.log(tr.it_mw.values), 1)
    return float(np.exp(a + b * np.log(area_ha)))


def summarise_loso(df: pd.DataFrame) -> dict:
    """Median factor errors.  Held-out sites whose thermal inversion is not
    identified (slope ≈ 0 in the training fold) count as failures: they are
    reported separately and, for the kill condition, as unbounded error."""
    if df.empty:
        return {}
    def stats(col):
        v = df[col].dropna()
        return dict(median_abs_log_err=float(v.median()) if len(v) else None, median_factor=float(np.exp(v.median())) if len(v) else None,
                    frac_within_1p4x=float((v < np.log(1.4)).mean()) if len(v) else None, frac_within_2x=float((v < np.log(2.0)).mean()) if len(v) else None, n=int(len(v)))
    out = dict(thermal=stats("thermal_abs_log_err"), geometry=stats("geometry_abs_log_err"), constant=stats("const_abs_log_err"))
    n_unid = int((~df["thermal_identified"].astype(bool)).sum()) if "thermal_identified" in df else 0
    out["thermal"]["n_unidentified"] = n_unid
    out["thermal"]["n_sites"] = int(len(df))
    # kill-condition metric: unidentified folds count as unbounded error
    v = df["thermal_abs_log_err"].where(df.get("thermal_identified", True).astype(bool), np.inf)
    med = float(np.median(v)) if len(v) else np.inf
    out["thermal"]["median_abs_log_err_with_failures"] = None if not np.isfinite(med) else med
    out["thermal"]["majority_unidentified"] = bool(n_unid * 2 >= len(df))
    return out


# --------------------------------------------------------------------------
# within-site tests: documented capacity changes at a fixed site
# --------------------------------------------------------------------------

def within_site_tests(f: pd.DataFrame, met: list[str]) -> list[dict]:
    """For every site whose documented capacity changes inside the observation
    window, regress ΔT on capacity (+ met covariates) using that site's frames
    only.  Roof albedo, emissivity and background type are constant within a
    site, so this isolates the heat term far better than the cross-site fit.
    Reports the coefficient in K per MW, its SE and the period means."""
    import statsmodels.api as sm
    out = []
    for sid, fs in f.groupby("site_id"):
        fs = fs.dropna(subset=["it_mw"])
        if fs.it_mw.nunique() < 2 or len(fs) < 10:
            continue
        X = pd.DataFrame({"intercept": 1.0, "it_mw": fs.it_mw.values}, index=fs.index)
        for c in met:
            if c in fs:
                X[c] = fs[c].values
        res = sm.OLS(fs.delta_t_k.values, X).fit()
        periods = fs.groupby("it_mw").delta_t_k.agg(["count", "mean", "std"]).reset_index()
        out.append(dict(site_id=sid, n_frames=int(len(fs)), coef_k_per_mw=float(res.params["it_mw"]), se=float(res.bse["it_mw"]),
                        p_value=float(res.pvalues["it_mw"]), r2=float(res.rsquared),
                        periods=[dict(it_mw=float(r.it_mw), n=int(r["count"]), mean_dt=float(r["mean"]), sd_dt=float(r["std"]) if r["std"] == r["std"] else None) for _, r in periods.iterrows()],
                        expected_sign_positive=bool(res.params["it_mw"] > 0), significant_2se=bool(abs(res.params["it_mw"]) > 2 * res.bse["it_mw"])))
    return out


# --------------------------------------------------------------------------
# secondary learner (TabPFN if importable, else a GP stand-in)
# --------------------------------------------------------------------------

def secondary_loso(f: pd.DataFrame, capacity_col: str, met: list[str]) -> dict:
    cols = [capacity_col] + met
    X, y = f[cols].values, f["delta_t_k"].values
    name = None
    try:
        from tabpfn import TabPFNRegressor  # type: ignore
        make = lambda: TabPFNRegressor()
        name = "tabpfn"
    except Exception as e:
        from sklearn.gaussian_process import GaussianProcessRegressor
        from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        make = lambda: make_pipeline(StandardScaler(), GaussianProcessRegressor(ConstantKernel() * RBF(length_scale=np.ones(len(cols))) + WhiteKernel(), normalize_y=True))
        name = f"gp_standin (tabpfn unavailable: {type(e).__name__})"
    rows = []
    for s in sorted(f.site_id.unique()):
        tr, te = f.site_id != s, f.site_id == s
        if f[tr].site_id.nunique() < 2:
            continue
        try:
            m = make().fit(X[tr], y[tr])
            # invert by grid search over capacity
            grid = np.linspace(np.nanmin(X[tr][:, 0]) * 0.2, np.nanmax(X[tr][:, 0]) * 3, 120)
            Xt = X[te].copy()
            errs = []
            for gval in grid:
                Xt[:, 0] = gval
                errs.append(np.mean(m.predict(Xt) - y[te]) ** 2)
            est = float(grid[int(np.argmin(errs))])
        except Exception as e:  # pragma: no cover
            est = float("nan")
        rows.append(dict(site_id=s, truth=float(X[te][0, 0]), est=est))
    d = pd.DataFrame(rows)
    if d.empty:
        return dict(learner=name, rows=[])
    d["abs_log_err"] = np.abs(np.log(np.clip(d.est, 1e-6, None) / d.truth))
    return dict(learner=name, median_abs_log_err=float(d.abs_log_err.median()), rows=d.to_dict("records"))


# --------------------------------------------------------------------------
# Q̂ for every site
# --------------------------------------------------------------------------

def site_estimates(model: dict, f_all: pd.DataFrame, capacity_col: str, met: list[str], arch: bool, sites: pd.DataFrame, cfg) -> pd.DataFrame:
    """Implied heat rejection Q̂ (MW, ≈ total electrical power) per site.
    Interval: 5–95 % from residual scatter/√n, between-site SD and slope SE."""
    out = []
    identified = slope_identified(model, capacity_col)
    for sid, fs in f_all.groupby("site_id"):
        est, se, _ = invert_capacity(model, fs, capacity_col, met, arch)
        area = float(fs.area_ha.iloc[0])
        pue = float(fs.pue_assumed.iloc[0])
        if capacity_col == "density":
            it_hat, lo, hi = est * area, (est - 1.64 * se) * area, (est + 1.64 * se) * area
        else:
            it_hat, lo, hi = np.exp(est), np.exp(est - 1.64 * se), np.exp(est + 1.64 * se)
        it_hat, lo, hi = float(it_hat), float(lo), float(hi)
        ok = identified and it_hat == it_hat and lo > 0
        if not ok:  # unbounded: report no number rather than a meaningless one
            it_hat, lo, hi = np.nan, np.nan, np.nan
        q_hat, q_lo, q_hi = it_hat * pue, lo * pue, hi * pue   # heat rejected ≈ IT + cooling overhead
        tier = str(fs.site_tier.iloc[0])
        c_it = float(fs.it_mw.dropna().iloc[-1]) if fs.it_mw.notna().any() else np.nan
        u = (it_hat / c_it) if (ok and tier in TIER_A and c_it == c_it and c_it > 0) else np.nan
        out.append(dict(site_id=sid, n_frames=int(len(fs)), mean_delta_t_k=float(fs.delta_t_k.mean()), sd_delta_t_k=float(fs.delta_t_k.std()),
                        area_ha=area, pue_assumed=pue, it_hat_mw=it_hat, it_lo_mw=lo, it_hi_mw=hi, q_hat_mw=q_hat, q_lo_mw=q_lo, q_hi_mw=q_hi,
                        q_identified=bool(ok), slope_identified=bool(identified),
                        capacity_tier=tier, capacity_it_mw=c_it, utilisation=u,
                        utilisation_identified=bool(ok and tier in TIER_A and c_it == c_it),
                        in_training_set=bool(fs.tier_a.iloc[0])))
    return pd.DataFrame(out)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--obs", default=str(DATA / "observations.csv"))
    ap.add_argument("--sites", default=str(DATA / "sites.csv"))
    ap.add_argument("--polygons", default=str(DATA / "polygons"))
    ap.add_argument("--out", default=str(RESULTS))
    ap.add_argument("--ptype", default="hall", choices=["hall", "cooling", "substation"])
    ap.add_argument("--capacity", default="density", choices=["density", "log_it_mw"])
    ap.add_argument("--met", nargs="*", default=MET_COVARIATES)
    ap.add_argument("--no-arch", action="store_true", help="drop the cooling-architecture term (default: dropped automatically if any level has < 2 sites)")
    ap.add_argument("--cond-wind-max", type=float, default=3.0)
    ap.add_argument("--cond-ta-min", type=float, default=5.0)
    ap.add_argument("--cond-ta-max", type=float, default=25.0)
    ap.add_argument("--cond-cloud-max", type=float, default=20.0)
    ap.add_argument("--cond-valid-frac", type=float, default=0.99)
    ap.add_argument("--cond-sun-max", type=float, default=40.0, help="max solar elevation (deg) in the conditioned window; night proxy")
    ap.add_argument("--min-frames", type=int, default=5)
    ap.add_argument("--exclude-sites", nargs="*", default=[])
    args = ap.parse_args()
    cfg = vars(args)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    obs, sites, areas = load_inputs(args.obs, args.sites, args.polygons)
    frames = aggregate_frames(obs, args.ptype)
    if frames.empty:
        sys.exit(f"no observations of ptype={args.ptype}")
    f_all = attach_site_info(frames, sites, areas, args.ptype)
    f_all = f_all[~f_all.site_id.isin(args.exclude_sites)]
    f_all = f_all.dropna(subset=["delta_t_k"] + [c for c in args.met if c in f_all])
    counts = f_all.groupby("site_id").size()
    f_all = f_all[f_all.site_id.isin(counts[counts >= args.min_frames].index)]
    f_a = f_all[f_all.tier_a & f_all.density.notna()].copy()
    n_sites_a = f_a.site_id.nunique()
    print(f"frames: {len(f_all)} over {f_all.site_id.nunique()} sites; Tier A frames: {len(f_a)} over {n_sites_a} sites", file=sys.stderr)

    arch_counts = f_a.groupby("cooling_arch").site_id.nunique()
    use_arch = (not args.no_arch) and (len(arch_counts) > 1) and (arch_counts.min() >= 2)
    met = [c for c in args.met if c in f_a]
    cap = args.capacity

    report = dict(ptype=args.ptype, capacity_col=cap, met=met, cooling_arch_term=bool(use_arch), arch_site_counts=arch_counts.to_dict(),
                  n_frames_all=int(len(f_all)), n_sites_all=int(f_all.site_id.nunique()), n_frames_tier_a=int(len(f_a)), n_sites_tier_a=int(n_sites_a),
                  frames_per_site=f_all.groupby("site_id").size().to_dict(), config=cfg)

    if n_sites_a < 3:
        report["status"] = "insufficient_tier_a_sites"
        (out / "model_report.json").write_text(json.dumps(report, indent=2, default=float))
        sys.exit("fewer than 3 Tier A sites with frames — nothing to fit; report written")

    # ---- primary fit on all frames
    m_all = fit_mixed(f_a, cap, met, use_arch)
    vd_all = variance_decomposition(f_a, cap, met, use_arch)
    loso_all = loso(f_a, cap, met, use_arch, sites, areas, args.ptype, "all_frames")
    # ---- conditioned fit: narrow weather window, no met covariates
    cmask = conditioned_mask(f_a, cfg)
    f_c = f_a[cmask]
    cond_sites = f_c.groupby("site_id").size()
    f_c = f_c[f_c.site_id.isin(cond_sites[cond_sites >= 3].index)]
    if f_c.site_id.nunique() >= 3:
        m_cond = fit_mixed(f_c, cap, [], use_arch)
        vd_cond = variance_decomposition(f_c, cap, [], use_arch)
        loso_cond = loso(f_c, cap, [], use_arch, sites, areas, args.ptype, "conditioned")
    else:
        m_cond, vd_cond, loso_cond = None, None, pd.DataFrame()
    # ---- total-MW variant for comparison
    alt = "log_it_mw" if cap == "density" else "density"
    m_alt = fit_mixed(f_a, alt, met, use_arch)
    loso_alt = loso(f_a, alt, met, use_arch, sites, areas, args.ptype, f"alt_{alt}")
    # ---- secondary learner
    sec = secondary_loso(f_a, cap, met)
    # ---- within-site capacity steps (uses all sites with a documented change, Tier A only)
    within = within_site_tests(f_a, met)

    loso_df = pd.concat([loso_all, loso_cond, loso_alt], ignore_index=True)
    loso_df.to_csv(out / "loso.csv", index=False)
    s_all, s_cond, s_alt = summarise_loso(loso_all), summarise_loso(loso_cond), summarise_loso(loso_alt)

    # ---- kill conditions
    if s_all and s_all["geometry"]["n"]:
        t_err = s_all["thermal"]["median_abs_log_err_with_failures"]
        kill1 = bool(t_err is None or t_err >= s_all["geometry"]["median_abs_log_err"])
    else:
        kill1 = None
    kill2 = bool(vd_all["partial_r2_met"] > vd_all["partial_r2_capacity"])
    slope = m_all["params"][cap]
    slope_se = m_all["bse"].get(cap, np.nan)
    slope_sig = slope_identified(m_all, cap)

    # ---- Q̂ for all sites from the all-frames model
    est = site_estimates(m_all, f_all, cap, met, use_arch, sites, cfg)
    est.to_csv(out / "site_estimates.csv", index=False)
    f_all.to_csv(out / "frames_used.csv", index=False)

    def clean(m):
        if m is None:
            return None
        return {k: v for k, v in m.items() if k != "cov"}

    report.update(dict(
        status="fitted",
        model_all_frames=clean(m_all), variance_all_frames=vd_all, loso_all_frames=s_all,
        model_conditioned=clean(m_cond), variance_conditioned=vd_cond, loso_conditioned=s_cond, n_frames_conditioned=int(len(f_c)), n_sites_conditioned=int(f_c.site_id.nunique()),
        model_alt=clean(m_alt), loso_alt=s_alt,
        secondary=sec,
        within_site=within,
        slope=dict(value=float(slope), se=float(slope_se), significant_2se=slope_sig, units="K per (MW/ha)" if cap == "density" else "K per log(MW)"),
        kill_conditions=dict(
            loso_not_better_than_geometry_baseline=kill1,
            met_explains_more_than_capacity=kill2,
            verdict=("negative_result" if (kill1 or kill2) else "thermal_channel_adds_information"),
        ),
        loso_rows=loso_df.to_dict("records"),
        site_estimates=est.to_dict("records"),
    ))
    (out / "model_report.json").write_text(json.dumps(report, indent=2, default=float))

    # ---- console summary
    print("\n=== fit on all frames (Tier A) ===")
    print(f"slope on {cap}: {slope:.4f} ± {slope_se:.4f}  (re_sd {m_all['re_sd']:.2f} K, resid_sd {m_all['resid_sd']:.2f} K, {m_all['kind']}, converged={m_all['converged']})")
    print("partial R²: capacity %.3f | met %.3f | between-site share %.3f" % (vd_all["partial_r2_capacity"], vd_all["partial_r2_met"], vd_all["between_site_share"]))
    def mf(o):
        return "n/a" if not o or o.get("median_factor") is None else "%.2f×" % o["median_factor"]
    print("LOSO median factor: thermal %s (%d of %d folds unidentified) | geometry %s | constant %s" % (
        mf(s_all["thermal"]), s_all["thermal"]["n_unidentified"], s_all["thermal"]["n_sites"], mf(s_all["geometry"]), mf(s_all["constant"])))
    if s_cond:
        print("=== conditioned ===  LOSO median factor: thermal %s (%d unidentified) | geometry %s | constant %s (n=%d frames, %d sites)" % (
            mf(s_cond["thermal"]), s_cond["thermal"]["n_unidentified"], mf(s_cond["geometry"]), mf(s_cond["constant"]), len(f_c), f_c.site_id.nunique()))
    print("kill 1 (LOSO not better than geometry):", kill1, "| kill 2 (met > capacity):", kill2, "->", report["kill_conditions"]["verdict"])
    for w in within:
        per = "; ".join(f"{p['it_mw']:.1f} MW: {p['mean_dt']:+.2f} K (n={p['n']})" for p in w["periods"])
        print(f"within-site {w['site_id']}: {w['coef_k_per_mw']:+.4f} ± {w['se']:.4f} K/MW (p={w['p_value']:.3f}) | {per}")
    print(loso_all[["site_id", "n_frames", "truth_mw", "thermal_identified", "thermal_raw_mw", "geometry_mw", "const_mw", "slope", "slope_se"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
