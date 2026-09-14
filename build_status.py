"""Plain-language status per site for the front page: built / running / load / confidence / how we know,
plus one key series to draw.  Reads site/data/sites.json and site/data/timeline/<site>.json; writes
site/data/status.json.

    python build_status.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"


def basis_is_comb(t):
    q = (t or {}).get("quarters") or []
    return bool(q) and str(q[-1].get("basis", "")).startswith("NO2-flux on-site")


def month_label(ym):
    try:
        return pd.Period(ym, freq="M").strftime("%b %Y")
    except Exception:
        return str(ym)


def main():
    data = json.loads((SITE / "data" / "sites.json").read_text())
    out = []
    for s in data["sites"]:
        sid = s["site_id"]
        if sid.startswith("ctrl_"):
            continue
        tp = SITE / "data" / "timeline" / f"{sid}.json"
        t = json.loads(tp.read_text()) if tp.exists() else None
        Q = t["quarters"] if t else []
        last = Q[-1] if Q else None
        roof_on = (t or {}).get("roof_on", {})
        halls_total = last["halls_total"] if last else 0
        # ---- built
        dated = sorted(v for v in roof_on.values() if v not in ("existing", "not_yet", "unknown", None))
        existing = sum(1 for v in roof_on.values() if v == "existing")
        if halls_total == 0:
            built = "turbine yard; no halls mapped" if basis_is_comb(t) else ("no halls mapped" if s.get("polygons") else "approximate location only, no polygons")
            built_conf = "low"
        else:
            roofed = last["halls_roofed"]
            when = f", roofed {month_label(dated[0])} to {month_label(dated[-1])}" if len(dated) > 1 else (f", roofed {month_label(dated[0])}" if dated else (", present at the start of observations" if existing == halls_total else ""))
            if existing and dated:
                span = month_label(dated[0]) if dated[0] == dated[-1] else f"{month_label(dated[0])} to {month_label(dated[-1])}"
                when = f"; {existing} present at first observations; {len(dated)} roofed {span}"
            unknown_roofs = sum(v == "unknown" for v in roof_on.values())
            built = f"{roofed} of {halls_total} halls{when}" + (f"; {unknown_roofs} roof dates unresolved" if unknown_roofs else "")
            built_conf = "low" if unknown_roofs else ("high" if (t or {}).get("s2_available") else "medium")
            if s.get("coords_quality") == "radar_candidate":
                import re as _re
                m = _re.search(r"score=([\d.]+) area_ha=([\d.]+)", str(s.get("notes") or ""))
                score, area = (m.group(1), m.group(2)) if m else ("?", "?")
                ron = str((t or {}).get("radar_on", {}).get("structure") or "")
                first = f"structure on {month_label(ron[:7])} (radar)" if ron[:4].isdigit() else ("radar sees no sustained step since 2018 yet" if ron.startswith("not_yet") else "structure date pending (radar timeline not run)")
                built = f"radar-detected new structure, {float(area):.0f} ha, {first}; hall-like score {score}; unconfirmed, operator unknown"
                built_conf = "low"
            if any(p.get("confidence") == "low" for p in s.get("polygons", [])):
                built_conf = "low"
            elif any(p.get("confidence") == "medium" for p in s.get("polygons", [])) and built_conf == "high":
                built_conf = "medium"
        # ---- running / load
        basis = last["basis"] if last else ""
        fx_months = []
        if t and t.get("quarters"):
            for q in Q:
                f = q.get("no2_flux")
                if f and f.get("nox_se") is not None and f.get("nox_kgh", 0) > 2 * f["nox_se"] and f.get("nox_kgh", 0) > 100:
                    fx_months.append(q["q"])
        # site-level plume test: combustion "detected" only if the downwind-minus-upwind change at the documented start is >= 2.5 sigma
        no2_active = []
        pt = ROOT / "results_no2" / f"{sid}.csv"
        if pt.exists():
            try:
                n2 = pd.read_csv(pt, index_col=0)
                n2 = n2[n2.site == sid] if "site" in n2 else n2
                n2.index = pd.to_datetime(n2.index)
                start = next((q["q"] for q in Q if (q.get("cap_doc_mw") or 0) > 0), None)
                if start:
                    cut = pd.Period(start, freq="Q").start_time
                    a, b = n2[n2.index >= cut].dw_minus_uw, n2[n2.index < cut].dw_minus_uw
                    if len(a) > 10 and len(b) > 10:
                        z = (a.mean() - b.mean()) / ((a.var() / len(a) + b.var() / len(b)) ** 0.5)
                        if z >= 2.5:
                            no2_active = [start]
            except Exception:
                pass
        cap_now = last["cap_doc_mw"] if last else None
        cap_since = next((q["q"] for q in Q if (q.get("cap_doc_mw") or 0) > 0), None)
        adjacent = "ADJACENT PLANT" in str(s.get("nox_ef_note") or "")
        plant = (last or {}).get("campd") or {}
        if plant.get("basis") == "dedicated_plant_measured":
            gross = sum(p["gross_avg_mw"] for p in plant["plants"] if p["eligible"])
            running = (f"yes: dedicated plant generated {gross:.0f} MW average in {last['q']}" if gross > 0 else f"no generation reported by dedicated plant in {last['q']}; campus operation unknown")
            load = f"{plant['allocated_gross_avg_mw']:.0f} MW allocated gross output; {plant['it_equivalent_avg_mw']:.0f} MW IT equivalent using assumed PUE. Not a campus meter; losses and uncertainty unmeasured"
            conf, key = "high", "plant"
        elif basis.startswith("NO2-flux on-site") and fx_months:
            running = f"yes: on-site generation detected since {fx_months[0]}"
            load = f"about {last['est_mid']:.0f} MW from NO₂ (range {last['est_lo']:.0f}–{last['est_hi']:.0f}; megawatts uncertain 2–3× from the emission factor; quarterly NOx ±20 %, single months ±20–50 %)"
            conf, key = "high", "nox"
        elif (str((last or {}).get("cap_basis") or "").endswith("measured_annual")
              or "water_derived" in str((last or {}).get("cap_basis") or "")) and cap_now is not None:
            meas_q = [q for q in Q if str(q.get("cap_basis") or "") in ("facility_measured_annual", "it_measured_annual", "water_derived_it_annual")]
            yr = meas_q[-1]["q"][:4] if meas_q else "?"
            carried = "carried" in str(last.get("cap_basis"))
            water = "water" in str(last.get("cap_basis")) or (meas_q and "water" in str(meas_q[-1].get("cap_basis")))
            if water:
                ub = " and an upper bound, since one water figure covers two campuses" if last.get("cap_upper_bound") else ""
                running = f"yes: about {cap_now:.0f} MW average IT load in {yr}, derived from the operator's published water use (uncertain to about ×2{ub})" + (" (carried forward)" if carried else "")
                load = f"about {last['est_mid']:.0f} MW from water use ÷ WUE (range {last['est_lo']:.0f}–{last['est_hi']:.0f}); an annual average, method validated only to about ×2"
                conf, key = "low", "capacity"
            else:
                running = f"yes: operator reports an average IT load of {cap_now:.0f} MW in {yr}" + (" (latest published year, carried forward)" if carried else "")
                load = f"about {last['est_mid']:.0f} MW, operator-reported annual electricity ÷ 8760 h (range {last['est_lo']:.0f}–{last['est_hi']:.0f}); an average, not a peak"
                conf, key = "high", "capacity"
        elif no2_active and cap_now:
            running = f"yes: combustion activity detected (NO₂) since {no2_active[0]}; documented {cap_now:.0f} MW in force"
            load = f"documented capacity {cap_now:.0f} MW × utilisation prior = {last['est_lo']:.0f}–{last['est_hi']:.0f} MW; not directly measured"
            conf, key = "medium", "roofs" if (t or {}).get("s2_available") else "capacity"
        elif cap_now:
            running = f"presumably: documented {cap_now:.0f} MW in force since {cap_since}; not directly observed"
            load = f"{last['est_lo']:.0f}–{last['est_hi']:.0f} MW assumed from documented capacity; not directly measured"
            conf, key = ("high" if str(last.get("cap_tier")) == "A1" else "medium"), "roofs" if (t or {}).get("s2_available") and dated else "capacity"
        elif last and last["est_hi"] > 0:
            running = "unknown: roofs on, no activity evidence"
            load = f"0–{last['est_hi']:.0f} MW (roofed area × density prior); no evidence of operation"
            conf, key = "low", "roofs"
        else:
            running = "unknown: no operating evidence" if cap_now is None else "not yet: no positive documented capacity"
            load = "unknown" if cap_now is None else "0 MW documented capacity; actual load not measured"
            conf, key = "low", "roofs" if halls_total else "none"
        if s.get("coords_quality") == "radar_candidate":
            running = "unknown: new structure found by radar, not confirmed as a data centre; no activity evidence"
            load = "not estimated (unconfirmed structure)"
            conf, key = "low", "roofs"
        if adjacent:
            running += "; the NO₂ series shown is the adjacent power plant, not the campus"
        # ---- how we know
        how = []
        if (t or {}).get("water_monthly"):
            how.append("Municipal monthly water deliveries, with separate customer and return records; water evidence only, not electricity use")
        if any(q.get("campd") for q in Q):
            how.append("EPA CAMPD plant generation; campus allocation only where separately verified at >=80%; other plant records are evidence only")
        if (t or {}).get("s2_available"):
            how.append("Sentinel-2 roof dating")
        if any(v == "radar" for v in (t or {}).get("roof_basis", {}).values()):
            how.append("Sentinel-1 radar structure dating (where brightness dating could not)")
        lit = (t or {}).get("ntl_lit") or ""
        if lit[:4].isdigit():
            how.append(f"VIIRS night lights: campus lit from {month_label(lit[:7])} (construction and energisation, not load)")
        if (t or {}).get("no2_available"):
            how.append("TROPOMI NO₂ plume test")
        if fx_months or adjacent:
            how.append("TROPOMI NOx flux (calibrated on EPA-monitored plants)")
        if (t or {}).get("thermal_night_available"):
            how.append("ECOSTRESS night thermal (negative: roofs do not track load)")
        if any(str(q.get("cap_basis") or "") in ("facility_measured_annual", "it_measured_annual") for q in Q):
            how.append("operator-reported annual electricity per site (Meta Environmental Data Index; ORNL Frontier reports)")
        if any(str(q.get("cap_basis") or "") == "water_derived_it_annual" for q in Q):
            how.append("annual IT energy derived from the operator's published water use and WUE (±30 %)")
        if s.get("capacity_source"):
            how.append(f"documented capacity: {s['capacity_source'][:90]}")
        # ---- key series
        series = []
        if key == "plant":
            series = [dict(x=q["q"], y=(q.get("campd") or {}).get("allocated_gross_avg_mw")) for q in Q]
            series_label = "allocated plant gross output, MW average (not a campus meter)"
        elif key == "nox":
            for q in Q:
                f = q.get("no2_flux")
                series.append(dict(x=q["q"], y=(f or {}).get("nox_kgh"), se=(f or {}).get("nox_se")))
            series_label = "NOx emission rate, kg/h (calibrated)"
        elif key == "roofs":
            for q in Q:
                series.append(dict(x=q["q"], y=q["halls_roofed"], y2=q["fitted_ha"]))
            series_label = f"halls roofed (of {halls_total})"
        elif key == "capacity":
            for q in Q:
                series.append(dict(x=q["q"], y=q.get("cap_doc_mw")))
            measured = any(str(q.get("cap_basis") or "") in ("facility_measured_annual", "it_measured_annual") for q in Q)
            series_label = "operator-reported average IT load, MW (annual; documented capacity where no report)" if measured else "documented capacity, MW"
        else:
            series_label = ""
        # recent change
        recent = ""
        if key == "nox" and len(series) >= 2 and series[-1]["y"] and series[-2]["y"]:
            d = series[-1]["y"] - series[-2]["y"]
            recent = f"NOx {'+' if d >= 0 else ''}{d / series[-2]['y'] * 100:.0f}% vs previous quarter"
        elif key == "roofs" and dated:
            recent = f"last roof completed {month_label(dated[-1])}"
        out.append(dict(site_id=sid, name=s["name"], operator=s.get("operator", ""), country=s.get("country", ""), lat=s["lat"], lon=s["lon"],
                        built=built, built_conf=built_conf, running=running, load=load, confidence=conf, how=how, key=key, series=series, series_label=series_label,
                        recent=recent, est_mid=(last or {}).get("est_mid"), est_hi=(last or {}).get("est_hi") or 0, last_q=(last or {}).get("q"),
                        polygons_low=bool(s.get("polygons") and any(p.get("confidence") == "low" for p in s["polygons"])),
                        combustion=key == "nox",
                        evidence_kind=("derived" if running.startswith("yes: about") else "measured" if (key in ("nox", "plant") or running.startswith("yes: operator reports"))
                                       else "detected" if running.startswith("yes") or (str((t or {}).get("ntl_lit") or "")[:4].isdigit() and running.startswith("presumably"))
                                       else "presumed" if running.startswith("presumably")
                                       else "construction")))
        if s.get("site_class") == "generator_planned":
            from tools.generator_watchlist import public_status
            out[-1].update(public_status(ROOT, s))
    out.sort(key=lambda r: (-(1 if r["combustion"] else 0), -(r["est_hi"] or 0)))
    (SITE / "data" / "status.json").write_text(json.dumps(dict(generated=data.get("generated"), sites=out), indent=0))
    for r in out:
        print(f"{r['site_id']:26s} built: {r['built'][:44]:44s} | running: {r['running'][:60]:60s} | {r['confidence']}")


if __name__ == "__main__":
    main()
