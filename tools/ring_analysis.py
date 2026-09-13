"""Is load-related heat visible next to the halls (35-150 m ring: chillers, dry coolers, switchgear, paving)
at night, where the roofs show none?  Compares ring vs roof by period and time of day, with the same
season + weather adjustment used elsewhere."""
import sys
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, "/Users/stuartbladon/Documents/Duke/Duke2025/Meridian/Meridian")
obs = pd.read_csv(REPO / "data/observations_eco.csv", dtype={"product_id": str})
sites = pd.read_csv(REPO / "data/sites.csv", dtype=str, keep_default_na=False).set_index("site_id")
obs["t"] = pd.to_datetime(obs.datetime_utc, utc=True, format="ISO8601")
obs["tod"] = np.where(obs.sun_elev_deg < -6, "night", np.where(obs.sun_elev_deg > 20, "day", "twilight"))
obs["season"] = pd.cut(obs.t.dt.month, [0, 3, 6, 9, 12], labels=["JFM", "AMJ", "JAS", "OND"])
pue = pd.to_numeric(obs.site_id.map(sites.pue_assumed), errors="coerce").fillna(1.2)
fac = obs.capacity_basis.isin(["facility_design", "grid_connection"])
obs["it_mw"] = np.where(fac, obs.capacity_mw / pue, obs.capacity_mw)

def per_poly_frames(d):
    d = d.copy(); d["w"] = d.n_valid_poly; d["dtw"] = d.delta_t_k * d.w
    g = d.groupby(["site_id", "datetime_utc"], as_index=False).agg(dtw=("dtw", "sum"), w=("w", "sum"), tod=("tod", "first"), season=("season", "first"),
                                                                  it_mw=("it_mw", "first"), ta_c=("ta_c", "first"), wind_ms=("wind_ms", "first"), tw_c=("tw_c", "first"), sun=("sun_elev_deg", "first"), t=("t", "first"))
    g["dT"] = g.dtw / g.w
    return g

def effects(g, add_sun):
    g = g.dropna(subset=["it_mw"]).copy()
    if g.it_mw.nunique() < 2 or len(g) < 10:
        return None
    lv = sorted(g.it_mw.unique()); g["period"] = pd.Categorical(g.it_mw.map(lambda v: f"{v:.0f}"), categories=[f"{v:.0f}" for v in lv])
    f = "dT ~ C(period) + C(season) + ta_c + wind_ms + tw_c" + (" + sun" if add_sun else "")
    try:
        m = smf.ols(f, data=g).fit()
    except Exception:
        return None
    return {k.split("T.")[1].rstrip("]"): (m.params[k], m.bse[k], m.pvalues[k]) for k in m.params.index if k.startswith("C(period)")}, int(m.nobs), {f"{v:.0f}": int((g.it_mw == v).sum()) for v in lv}

print("RING (hall_surround / east_yard, ptype cooling) vs ROOF (halls): mean night and day dT by site, and load-period effects\n")
for sid in ["colossus_memphis", "stargate_abilene", "fairwater_wi", "rainier_in", "prometheus_oh", "hyperion_la"]:
    d = obs[obs.site_id == sid]
    for label, sel in (("roof", d.ptype == "hall"), ("ring", (d.ptype == "cooling") & (d.polygon == "hall_surround")), ("yard", (d.ptype == "cooling") & (d.polygon != "hall_surround"))):
        dd = d[sel]
        if dd.empty:
            continue
        g = per_poly_frames(dd)
        n, dy = g[g.tod == "night"], g[g.tod == "day"]
        line = f"{sid:18s} {label:5s} night {n.dT.mean():+.2f} K (n={len(n):3d})  day {dy.dT.mean():+.2f} K (n={len(dy):3d})"
        for tod, add_sun in (("night", False), ("day", True)):
            r = effects(g[g.tod == tod], add_sun)
            if r:
                eff, nobs, pn = r
                line += f" | {tod} step vs {min(pn, key=lambda k: float(k))} MW: " + ", ".join(f"{k} MW {v[0]:+.2f}±{v[1]:.2f} (p={v[2]:.2f})" for k, v in eff.items())
        print(line)
    print()
# ring minus roof at night in the operating period, per site (same acquisitions)
print("Same-acquisition night difference ring - roof (K), operating period only (it_mw > 1):")
for sid in ["colossus_memphis", "stargate_abilene", "fairwater_wi", "rainier_in", "prometheus_oh"]:
    d = obs[(obs.site_id == sid) & (obs.tod == "night") & (obs.it_mw > 1)]
    roof = per_poly_frames(d[d.ptype == "hall"]).set_index("datetime_utc").dT
    ring = per_poly_frames(d[(d.ptype == "cooling") & (d.polygon == "hall_surround")]).set_index("datetime_utc").dT
    j = pd.concat([roof.rename("roof"), ring.rename("ring")], axis=1).dropna()
    if len(j):
        diff = j.ring - j.roof
        print(f"  {sid:18s} n={len(j):3d}  ring-roof {diff.mean():+.2f} ± {diff.std()/np.sqrt(len(j)):.2f} K   (roof {j.roof.mean():+.2f}, ring {j.ring.mean():+.2f})")
