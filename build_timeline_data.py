"""Quarterly per-site timelines for the map panel: what was built, what evidence of activity exists,
and an explicitly assumption-based load estimate with a band.

    python build_timeline_data.py            # writes site/data/timeline/<site_id>.json + index.json

Evidence streams (each optional; missing ones are reported as absent, never invented):
  - capacity timeline   data/capacity_timeline.csv           documented capacity in force (IT-equivalent MW)
  - Sentinel-2 roofs     results_s2/<site>.csv                roof-on month per hall (tools/s2_roof_timeline.py)
  - ECOSTRESS night      data/observations_eco.csv            hall ΔT at night (sun < -6°), quarterly mean ± se
  - Landsat day          data/observations_gee.csv            hall ΔT by day, quarterly mean ± se
  - TROPOMI NO2          results_no2/<site>.csv               downwind-minus-upwind excess, quarterly vs pre-change baseline

Load estimate rule (stated in the panel):
  documented capacity in force  -> lo 0.5x, mid 0.8x, hi 1.0x   (training clusters run near-constant once installed)
  else roofs on >= 6 months     -> lo 0.3x, mid 0.6x, hi 0.9x of roofed area x density prior
  else                          -> 0 (roof not on, or not yet fitted out)
Density prior: the site's own documented capacity / hall area when tier A, else 15 MW/ha (AI-era hall).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from dcheat import geom as G

ROOT = Path(__file__).resolve().parent
DATA, SITE = ROOT / "data", ROOT / "site"
OUT = SITE / "data" / "timeline"
DENSITY_DEFAULT = 15.0  # IT-MW per hectare of hall roof, AI-era
FIT_OUT_MONTHS = 6


def quarters(start="2018Q1", end=None):
    end = end or pd.Timestamp.utcnow().to_period("Q")
    return list(pd.period_range(start, end, freq="Q"))


def it_mw(cap, basis, pue):
    return cap / pue if basis in ("facility_design", "grid_connection") else cap


def cap_in_force(tl, sid, date, pue):
    r = tl[(tl.site_id == sid) & (tl.valid_from <= date) & ((tl.valid_to == "") | (tl.valid_to >= date))]
    if r.empty:
        return None, None, None
    # Epoch carries IT and facility figures for the same date. Prefer direct IT
    # over a PUE conversion; never sum the two or depend on CSV row order.
    r = r.assign(it_preferred=r.capacity_basis.isin(["it_reported", "it_measured_hpl"]))
    r = r.sort_values(["it_preferred", "valid_from"]).iloc[-1]
    cap = float(r.capacity_mw)
    if r.capacity_basis == "placeholder":
        return 0.0, r.tier, "placeholder"
    return it_mw(cap, r.capacity_basis, pue), r.tier, r.capacity_basis


def quarterly_stats(df, tcol, vcol):
    if df.empty:
        return {}
    d = df.copy()
    d["q"] = pd.to_datetime(d[tcol], utc=True, format="ISO8601").dt.tz_convert(None).dt.to_period("Q").astype(str)
    g = d.groupby("q")[vcol].agg(["mean", "std", "count"])
    return {q: dict(mean=round(float(r["mean"]), 2), se=round(float(r["std"] / math.sqrt(r["count"])), 2) if r["count"] > 1 and pd.notna(r["std"]) else None, n=int(r["count"])) for q, r in g.iterrows()}


def hall_frames(obs, sid, tod):
    d = obs[(obs.site_id == sid) & (obs.ptype == "hall")].copy()
    if d.empty:
        return d
    if tod == "night":
        d = d[d.sun_elev_deg < -6]
    elif tod == "day":
        d = d[d.sun_elev_deg > 20]
    d["w"] = d.n_valid_poly
    d["dtw"] = d.delta_t_k * d.w
    g = d.groupby("datetime_utc", as_index=False).agg(dtw=("dtw", "sum"), w=("w", "sum"))
    g["dT"] = g.dtw / g.w
    return g


def main():
    from tools.epoch_roof_review import construction_context, review
    epoch_context = construction_context(ROOT)
    sites = pd.read_csv(DATA / "sites.csv", dtype=str).fillna("")
    tl = pd.read_csv(DATA / "capacity_timeline.csv", dtype=str).fillna("")
    eco = pd.read_csv(DATA / "observations_eco.csv", dtype={"product_id": str}) if (DATA / "observations_eco.csv").exists() else pd.DataFrame()
    gee = pd.read_csv(DATA / "observations_gee.csv", dtype={"product_id": str}) if (DATA / "observations_gee.csv").exists() else pd.DataFrame()
    OUT.mkdir(parents=True, exist_ok=True)
    index = {}
    for _, s in sites.iterrows():
        sid = s.site_id
        if sid.startswith("ctrl_"):
            continue
        pue = float(s.pue_assumed) if s.pue_assumed else 1.2
        lat, lon = float(s.lat), float(s.lon)
        pfile = DATA / "polygons" / f"{sid}.geojson"
        halls = []
        if pfile.exists():
            for p in G.load_site_polygons(pfile):
                if p.ptype == "hall":
                    halls.append(dict(name=p.name, area_ha=G.polygon_areas_m2([p], lon, lat)[p.ptype] / 1e4, valid_from=p.valid_from,
                                      props=p.props,
                                      roof_date_required=p.props.get("roof_date_required", False)))
        hall_area = sum(h["area_ha"] for h in halls)
        # roof-on month per hall from Sentinel-2, falling back to the polygon's valid_from, else "existing"
        roof_on = {}
        roof_evidence = {}
        s2 = ROOT / "results_s2" / f"{sid}.csv"
        s2_available = False
        if s2.exists():
            piv = pd.read_csv(s2, index_col=0)
            s2_available = bool(not piv.empty and piv.notna().any().any())
            from tools.s2_roof_timeline import roof_on_month
            vf = {h["name"]: h["valid_from"] for h in halls}
            required = {h["name"]: h["roof_date_required"] for h in halls}
            for c in piv.columns:
                r = roof_on_month(piv[c])
                valid = piv[c].dropna()
                roof_evidence[c] = dict(rule="visible_brightness", first_observation=str(valid.index[0]) if len(valid) else None,
                                        valid_months=len(valid), inferred_roof_on=r)
                props = next((h['props'] for h in halls if h['name'] == c), {})
                conflict = review(r, props, epoch_context.get(sid))
                if conflict:
                    roof_evidence[c]['review_required'] = conflict
                    r = 'unknown'
                if r == "not_yet" and required.get(c):
                    # Planned footprints do not prove a roof; dark roofs also
                    # cannot be distinguished from soil by a non-detection.
                    r = "unknown"
                elif r == "not_yet":
                    # brightness dating only catches new bright roofs: a polygon digitised without a valid_from is an existing
                    # structure by declaration; one with a valid_from keeps the analyst's date (lower confidence)
                    r = "existing" if not vf.get(c) else vf[c][:7]
                roof_on[c] = r
        for h in halls:
            if h["name"] not in roof_on:
                roof_on[h["name"]] = "unknown" if h["roof_date_required"] else (h["valid_from"][:7] if h["valid_from"] else "existing")
        # density prior
        tier = s.capacity_tier or "U"
        cap_site = float(s.capacity_mw) if s.capacity_mw else None
        if tier in ("A1", "A2") and cap_site and hall_area > 0:
            density, density_basis = it_mw(cap_site, s.capacity_basis, pue) / hall_area, "site documented capacity / hall area"
        else:
            density, density_basis = DENSITY_DEFAULT, f"default {DENSITY_DEFAULT:.0f} MW/ha"
        # evidence streams
        night = quarterly_stats(hall_frames(eco, sid, "night"), "datetime_utc", "dT") if not eco.empty else {}
        day = quarterly_stats(hall_frames(gee, sid, "day"), "datetime_utc", "dT") if not gee.empty else {}
        no2f = ROOT / "results_no2" / f"{sid}.csv"
        no2q, no2_base, no2_available = {}, None, no2f.exists()
        if no2_available:
            n2 = pd.read_csv(no2f, index_col=0)
            n2 = n2[n2.site == sid] if "site" in n2 else n2
            n2.index = pd.to_datetime(n2.index)
            change = tl[(tl.site_id == sid) & (tl.capacity_basis != "placeholder")].valid_from.min() or None
            pre = n2[n2.index < pd.Timestamp(change)] if change else n2.iloc[: len(n2) // 2]
            no2_base = dict(mean=float(pre.dw_minus_uw.mean()), se=float(pre.dw_minus_uw.std() / math.sqrt(max(len(pre), 1))), n=int(len(pre)))
            g = n2.groupby(n2.index.to_period("Q").astype(str)).dw_minus_uw.agg(["mean", "std", "count"])
            for q, r in g.iterrows():
                se = float(r["std"] / math.sqrt(r["count"])) if r["count"] > 1 else None
                z = (float(r["mean"]) - no2_base["mean"]) / math.sqrt((se or 0) ** 2 + no2_base["se"] ** 2) if se else None
                no2q[q] = dict(excess=round(float(r["mean"]), 2), se=round(se, 2) if se else None, n=int(r["count"]), z=round(z, 1) if z is not None else None)
        # NO2-flux generation estimate (sites with on-site combustion): calibrated NOx kg/h per month -> MW at an emission-factor range
        fluxf = ROOT / "results_no2" / f"flux_{sid}_monthly.csv"
        fluxq = {}
        # kg NOx per MWh: site-specific if sites.csv has nox_ef_lo/nox_ef_hi, else uncontrolled simple-cycle turbines 0.5-1.0 (25-60 ppm)
        EF_LO = float(s.get("nox_ef_lo") or 0.5) if str(s.get("nox_ef_lo") or "").strip() else 0.5
        EF_HI = float(s.get("nox_ef_hi") or 1.0) if str(s.get("nox_ef_hi") or "").strip() else 1.0
        if fluxf.exists():
            fm = pd.read_csv(fluxf, index_col=0)
            fm["q"] = pd.PeriodIndex(fm.index, freq="M").asfreq("Q").astype(str)
            for q, g in fm.groupby("q"):
                kgh = float(g.nox_kgh_cal.mean()); se = float(np.sqrt((g.nox_se ** 2).sum()) / len(g))
                fluxq[q] = dict(nox_kgh=round(kgh, 0), nox_se=round(se, 0), mw_lo=round(max(kgh - se, 0) / EF_HI, 0), mw_hi=round(max(kgh + se, 0) / EF_LO, 0), n_days=int(g.n_days.sum()))
        # quarters
        rows = []
        for q in quarters():
            qs = str(q)
            qend = min(q.end_time.strftime("%Y-%m-%d"), pd.Timestamp.utcnow().strftime("%Y-%m-%d"))
            cap, cap_tier, cap_basis = cap_in_force(tl, sid, qend, pue)
            roofed = [h for h in halls if (roof_on.get(h["name"]) == "existing" and
                      (not h["roof_date_required"] or (roof_evidence.get(h["name"], {}).get("first_observation") or "9999") <= qend[:7]))
                      or (roof_on.get(h["name"]) not in ("existing", "not_yet", "unknown", None) and roof_on[h["name"]] <= qend[:7])]
            fitted = [h for h in roofed if roof_on.get(h["name"]) == "existing" or (pd.Period(roof_on[h["name"]], freq="M") + FIT_OUT_MONTHS) <= pd.Period(qend[:7], freq="M")]
            built_ha = sum(h["area_ha"] for h in roofed)
            fitted_ha = sum(h["area_ha"] for h in fitted)
            if cap is not None and cap > 0:
                lo, mid, hi, basis = 0.5 * cap, 0.8 * cap, 1.0 * cap, f"documented capacity in force ({cap_tier}, {cap_basis}) × utilisation assumption 0.5–1.0"
            elif cap == 0.0 and cap_basis == "placeholder" and fitted_ha == 0:
                lo, mid, hi, basis = 0.0, 0.0, 0.0, "pre-operation (documented placeholder)"
            elif (fitted_ha > 0 and cap is None) or (cap == 0.0 and fitted_ha > 0):
                # roofs alone do not prove operation: give the potential as the upper bound, and a midpoint only with an activity signal
                c = fitted_ha * density
                n2 = no2q.get(qs)
                active = bool(n2 and n2.get("z") is not None and n2["z"] > 2)
                if active:
                    lo, mid, hi, basis = 0.3 * c, 0.6 * c, 0.9 * c, f"roofed ≥{FIT_OUT_MONTHS} months ({fitted_ha:.1f} ha) × {density:.1f} MW/ha ({density_basis}); NO2 plume active this quarter → utilisation 0.3–0.9"
                else:
                    lo, mid, hi, basis = 0.0, None, 0.9 * c, f"roofed ≥{FIT_OUT_MONTHS} months ({fitted_ha:.1f} ha) × {density:.1f} MW/ha ({density_basis}) is the potential; no operating evidence, so 0 to potential"
            elif built_ha > 0:
                lo, mid, hi, basis = 0.0, 0.0, 0.0, f"roof on ({built_ha:.1f} ha) but not yet fitted out"
            else:
                lo, mid, hi, basis = 0.0, 0.0, 0.0, "no roof yet"
            fx = fluxq.get(qs)
            adj = "ADJACENT PLANT" in str(s.get("nox_ef_note") or "")
            if fx and not adj and fx["nox_kgh"] > 2 * fx["nox_se"] and fx["nox_kgh"] > 100:
                lo, mid, hi, basis = fx["mw_lo"], round(fx["nox_kgh"] / ((EF_LO + EF_HI) / 2), 0), fx["mw_hi"], (("ADJACENT PLANT generation, not campus load: " if adj else "NO2-flux on-site generation: ") + f"{fx['nox_kgh']:.0f} ± {fx['nox_se']:.0f} kg NOx/h (TROPOMI, calibrated on 5 plants) at {EF_LO}-{EF_HI} kg NOx/MWh, midpoint at {(EF_LO + EF_HI) / 2}")
            rows.append(dict(q=qs, cap_doc_mw=None if cap is None else round(cap, 1), cap_tier=cap_tier, cap_basis=cap_basis, no2_flux=fx,
                             halls_roofed=len(roofed), halls_total=len(halls), built_ha=round(built_ha, 1), fitted_ha=round(fitted_ha, 1),
                             est_lo=round(lo, 1), est_mid=None if mid is None else round(mid, 1), est_hi=round(hi, 1), basis=basis,
                             night=night.get(qs), day=day.get(qs), no2=no2q.get(qs)))
        # trim leading quarters with nothing at all
        first = next((i for i, r in enumerate(rows) if r["halls_roofed"] or r["night"] or r["day"] or r["no2"] or (r["cap_doc_mw"] or 0) > 0), 0)
        rows = rows[max(0, first - 1):]
        out = dict(site_id=sid, name=s["name"], tier=tier, density_mw_per_ha=round(density, 1), density_basis=density_basis,
                   hall_area_ha=round(hall_area, 1), roof_on=roof_on, roof_evidence=roof_evidence, s2_available=s2_available, no2_available=no2_available, no2_baseline=no2_base,
                   thermal_night_available=bool(night), thermal_day_available=bool(day), quarters=rows,
                   caveat="Load is not measured by any sensor here. The estimate is documented capacity, or roofed area × a density prior, "
                          "times a utilisation assumption. Night-time roof temperature does not respond to load (see the overnight report); "
                          "NO2 plumes indicate on-site combustion only; Sentinel-2 dates roofs and fit-out.")
        (OUT / f"{sid}.json").write_text(json.dumps(out, indent=0, default=str))
        last = rows[-1] if rows else None
        index[sid] = dict(est_mid=last["est_mid"] if last else 0, est_lo=last["est_lo"] if last else 0, est_hi=last["est_hi"] if last else 0,
                          basis=last["basis"] if last else "", s2=s2_available, no2=no2_available, night=bool(night), quarters=len(rows))
        print(f"{sid:18s} quarters={len(rows):2d} s2={'y' if s2_available else '-'} no2={'y' if no2_available else '-'} night={'y' if night else '-'}  latest est {index[sid]['est_lo']:.0f}–{index[sid]['est_hi']:.0f} MW ({index[sid]['basis'][:60]})")
    (OUT / "index.json").write_text(json.dumps(index, indent=1))


if __name__ == "__main__":
    main()
