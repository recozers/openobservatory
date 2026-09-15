"""RFW-31: the rules that decide which figure sets a site's load, pinned so a silent change fails a test.

Three layers, each with synthetic inputs:
  1. cap_in_force: which capacity row is in force, and how a measured average is carried forward.
  2. utilisation_prior: the exact band multipliers per basis and site class.
  3. the quarterly band in build_timeline_data.main and the plain-language status in build_status.main: capacity band,
     roofs-only potential, placeholder, radar entry, generator watch, NO2-flux generation, adjacent plant, and the order of
     precedence between them.
"""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import build_status
import build_timeline_data as tld


def tl_rows(*rows):
    cols = ["site_id", "valid_from", "valid_to", "capacity_mw", "capacity_basis", "tier", "source", "url", "notes"]
    return pd.DataFrame([dict(zip(cols, [r[0], r[1], r[2], str(r[3]), r[4], r[5], "", "", r[6] if len(r) > 6 else ""])) for r in rows],
                        columns=cols, dtype=str).fillna("")


class CapInForceTests(unittest.TestCase):
    PUE = 1.25

    def test_measured_electricity_beats_every_other_basis_in_force(self):
        tl = tl_rows(("s", "2024-01-01", "2024-12-31", 50, "facility_measured_annual", "A2"),
                     ("s", "2023-01-01", "", 100, "it_reported", "A2"),
                     ("s", "2023-01-01", "", 300, "facility_design", "A2"),
                     ("s", "2024-06-01", "", 400, "grid_connection", "A1"))
        cap, tier, basis, _ = tld.cap_in_force(tl, "s", "2024-09-30", self.PUE)
        self.assertEqual((cap, tier, basis), (40.0, "A2", "facility_measured_annual"))  # facility electricity ÷ PUE

    def test_it_measured_annual_is_not_divided_by_pue(self):
        tl = tl_rows(("s", "2024-01-01", "2024-12-31", 50, "it_measured_annual", "A1"))
        self.assertEqual(tld.cap_in_force(tl, "s", "2024-09-30", self.PUE)[:3], (50.0, "A1", "it_measured_annual"))

    def test_electricity_beats_water_derived_and_the_newest_measured_year_wins(self):
        tl = tl_rows(("s", "2024-01-01", "2024-12-31", 30, "water_derived_it_annual", "A2"),
                     ("s", "2024-01-01", "2024-12-31", 50, "facility_measured_annual", "A2"))
        self.assertEqual(tld.cap_in_force(tl, "s", "2024-09-30", self.PUE)[2], "facility_measured_annual")
        tl = tl_rows(("s", "2023-01-01", "2024-12-31", 50, "facility_measured_annual", "A2"),
                     ("s", "2024-01-01", "2024-12-31", 60, "facility_measured_annual", "A2"))
        self.assertEqual(tld.cap_in_force(tl, "s", "2024-09-30", self.PUE)[0], 48.0)

    def test_measured_year_is_carried_forward_for_24_months_over_third_party_estimates(self):
        tl = tl_rows(("s", "2024-01-01", "2024-12-31", 50, "facility_measured_annual", "A2", "meta EDI"),
                     ("s", "2025-03-01", "", 100, "it_reported", "A2", "epoch cluster estimate"),
                     ("s", "2025-03-01", "", 300, "facility_design", "A2"))
        cap, tier, basis, note = tld.cap_in_force(tl, "s", "2026-06-30", self.PUE)
        self.assertEqual((cap, basis, note), (40.0, "carried_measured_annual", "meta EDI"))
        self.assertEqual(tld.cap_in_force(tl, "s", "2026-12-31", self.PUE)[2], "carried_measured_annual")   # 24 months exactly
        self.assertEqual(tld.cap_in_force(tl, "s", "2027-01-31", self.PUE)[:3], (100.0, "A2", "it_reported"))  # 25 months: expired

    def test_each_measured_basis_has_its_own_carried_name(self):
        for basis, carried, cap in (("facility_measured_annual", "carried_measured_annual", 40.0),
                                    ("it_measured_annual", "carried_it_measured_annual", 50.0),
                                    ("water_derived_it_annual", "carried_water_derived_it_annual", 50.0)):
            tl = tl_rows(("s", "2024-01-01", "2024-12-31", 50, basis, "A2"))
            self.assertEqual(tld.cap_in_force(tl, "s", "2025-06-30", self.PUE)[:3], (cap, "A2", carried), basis)

    def test_carried_average_is_displaced_only_by_a1_or_a_newer_measurement(self):
        base = ("s", "2024-01-01", "2024-12-31", 50, "facility_measured_annual", "A2")
        a1 = tl_rows(base, ("s", "2025-04-01", "", 200, "grid_connection", "A1"))
        self.assertEqual(tld.cap_in_force(a1, "s", "2025-06-30", self.PUE)[:3], (160.0, "A1", "grid_connection"))
        a1_before = tl_rows(base, ("s", "2024-06-01", "", 200, "grid_connection", "A1"))   # started during the measured year: not newer
        self.assertEqual(tld.cap_in_force(a1_before, "s", "2025-06-30", self.PUE)[2], "carried_measured_annual")
        newer = tl_rows(base, ("s", "2025-01-01", "2025-12-31", 60, "facility_measured_annual", "A2"))
        self.assertEqual(tld.cap_in_force(newer, "s", "2026-06-30", self.PUE)[:3], (48.0, "A2", "carried_measured_annual"))
        self.assertEqual(tld.cap_in_force(newer, "s", "2025-06-30", self.PUE)[:3], (48.0, "A2", "facility_measured_annual"))

    def test_without_measurement_it_figure_beats_facility_figure_whatever_the_row_order_or_date(self):
        tl = tl_rows(("s", "2026-01-01", "", 300, "facility_design", "A2"),
                     ("s", "2024-01-01", "", 100, "it_reported", "A2"))
        for frame in (tl, tl.iloc[::-1]):
            self.assertEqual(tld.cap_in_force(frame, "s", "2026-06-30", self.PUE)[:3], (100.0, "A2", "it_reported"))
        tl = tl_rows(("s", "2024-01-01", "", 300, "facility_design", "A2"), ("s", "2026-01-01", "", 360, "facility_design", "A2"))
        self.assertEqual(tld.cap_in_force(tl, "s", "2026-06-30", self.PUE)[0], 288.0)   # latest start wins among equals, ÷ PUE

    def test_placeholder_and_nothing_in_force(self):
        tl = tl_rows(("s", "2024-01-01", "", 0, "placeholder", "U"))
        self.assertEqual(tld.cap_in_force(tl, "s", "2024-06-30", self.PUE)[:3], (0.0, "U", "placeholder"))
        self.assertEqual(tld.cap_in_force(tl, "s", "2023-06-30", self.PUE), (None, None, None, ""))
        self.assertEqual(tld.cap_in_force(tl, "other", "2024-06-30", self.PUE), (None, None, None, ""))

    def test_it_mw_divides_only_facility_bases(self):
        for basis in ("facility_design", "grid_connection", "facility_measured_annual", "carried_measured_annual"):
            self.assertEqual(tld.it_mw(125.0, basis, 1.25), 100.0, basis)
        for basis in ("it_reported", "it_measured_hpl", "it_measured_annual", "water_derived_it_annual", "carried_water_derived_it_annual", "placeholder"):
            self.assertEqual(tld.it_mw(125.0, basis, 1.25), 125.0, basis)


class UtilisationPriorTests(unittest.TestCase):
    def band(self, basis, site_class="cloud"):
        return tld.utilisation_prior(basis, site_class)[:3]

    def test_exact_multipliers_per_basis(self):
        self.assertEqual(self.band("facility_measured_annual"), (0.9, 1.0, 1.1))
        self.assertEqual(self.band("it_measured_annual"), (0.9, 1.0, 1.1))
        self.assertEqual(self.band("water_derived_it_annual"), (0.5, 1.0, 2.0))
        self.assertEqual(self.band("carried_measured_annual"), (0.7, 1.0, 1.3))
        self.assertEqual(self.band("carried_it_measured_annual"), (0.7, 1.0, 1.3))
        self.assertEqual(self.band("carried_water_derived_it_annual"), (0.4, 1.0, 2.5))
        self.assertEqual(self.band("it_measured_hpl"), (0.4, 0.6, 0.9))

    def test_basis_beats_site_class(self):
        for cls in ("cloud", "ai_training", "hub", "", "radar_candidate"):
            self.assertEqual(self.band("facility_measured_annual", cls), (0.9, 1.0, 1.1), cls)
            self.assertEqual(self.band("water_derived_it_annual", cls), (0.5, 1.0, 2.0), cls)

    def test_documented_capacity_prior_by_site_class(self):
        for cls in ("cloud", "mixed_cloud_ai", "hub"):
            for basis in ("it_reported", "facility_design", "grid_connection"):
                self.assertEqual(self.band(basis, cls), (0.2, 0.4, 0.6), (basis, cls))
        for cls in ("ai_training", "supercomputer", "", "generator_planned"):
            self.assertEqual(self.band("it_reported", cls), (0.5, 0.8, 1.0), cls)


class QuarterBandTests(unittest.TestCase):
    """Runs build_timeline_data.main on a synthetic root: one hall of about 1 ha at the equator, optional capacity rows,
    optional NOx flux months. Reads back the quarter rows."""

    HALL = {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[
        [0.0, 0.0], [0.0009, 0.0], [0.0009, 0.0009], [0.0, 0.0009], [0.0, 0.0]]]},
        "properties": {"name": "h1", "ptype": "hall", "confidence": "medium", "digitised_from": "test", "valid_from": "2023-01-01"}}]}

    def build(self, site_overrides=None, tl=None, flux=None, hall=True):
        cols = ["site_id", "name", "operator", "country", "region", "lat", "lon", "coords_quality", "elev_m", "cooling_arch", "annulus_r_in_m",
                "annulus_r_out_m", "bg_classes_override", "obs_start", "obs_end", "thermal_backend", "capacity_tier", "capacity_mw", "capacity_basis",
                "pue_assumed", "capacity_source", "capacity_url", "in_epoch_db", "notes", "nox_ef_lo", "nox_ef_hi", "nox_ef_note", "site_class", "nox_ef_basis"]
        site = {c: "" for c in cols}
        site.update(site_id="synth", name="Synth", operator="x", country="US", lat="0.00045", lon="0.00045", coords_quality="verified_imagery",
                    capacity_tier="U", pue_assumed="1.25", site_class="cloud")
        site.update(site_overrides or {})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data" / "polygons").mkdir(parents=True)
            (root / "site" / "data" / "timeline").mkdir(parents=True)
            (root / "results_no2").mkdir()
            pd.DataFrame([site]).to_csv(root / "data" / "sites.csv", index=False)
            (tl if tl is not None else tl_rows()).to_csv(root / "data" / "capacity_timeline.csv", index=False)
            if hall:
                (root / "data" / "polygons" / "synth.geojson").write_text(json.dumps(self.HALL))
            if flux:
                pd.DataFrame(flux).set_index("d").to_csv(root / "results_no2" / "flux_synth_monthly.csv")
            with patch.multiple(tld, ROOT=root, DATA=root / "data", SITE=root / "site", OUT=root / "site" / "data" / "timeline"), \
                    contextlib.redirect_stdout(io.StringIO()):
                tld.main()
            t = json.loads((root / "site" / "data" / "timeline" / "synth.json").read_text())
        return {q["q"]: q for q in t["quarters"]}, t

    def test_documented_capacity_band_uses_the_cloud_prior(self):
        q, t = self.build(tl=tl_rows(("synth", "2024-01-01", "", 100, "it_reported", "A2")))
        r = q["2024Q4"]
        self.assertEqual((r["cap_doc_mw"], r["est_lo"], r["est_mid"], r["est_hi"]), (100.0, 20.0, 40.0, 60.0))
        self.assertTrue(r["basis"].startswith("documented capacity in force (A2, it_reported)"), r["basis"])

    def test_measured_then_carried_band_and_the_estimate_does_not_yield_to_a_third_party_figure(self):
        tl = tl_rows(("synth", "2024-01-01", "2024-12-31", 50, "facility_measured_annual", "A2"),
                     ("synth", "2025-01-01", "", 100, "it_reported", "A2"))
        q, _ = self.build(tl=tl)
        m = q["2024Q4"]
        self.assertEqual((m["cap_doc_mw"], m["est_lo"], m["est_mid"], m["est_hi"]), (40.0, 36.0, 40.0, 44.0))
        self.assertTrue(m["basis"].startswith("operator-reported annual electricity (A2, facility_measured_annual)"), m["basis"])
        c = q["2025Q4"]
        self.assertEqual((c["cap_doc_mw"], c["cap_basis"], c["est_lo"], c["est_mid"], c["est_hi"]), (40.0, "carried_measured_annual", 28.0, 40.0, 52.0))

    def test_water_derived_band(self):
        q, _ = self.build(tl=tl_rows(("synth", "2024-01-01", "2024-12-31", 40, "water_derived_it_annual", "A2")))
        w = q["2024Q4"]
        self.assertEqual((w["est_lo"], w["est_mid"], w["est_hi"]), (20.0, 40.0, 80.0))
        self.assertTrue(w["basis"].startswith("water-derived annual IT load"), w["basis"])
        c = q["2025Q4"]
        self.assertEqual((c["cap_basis"], c["est_lo"], c["est_hi"]), ("carried_water_derived_it_annual", 16.0, 100.0))

    def test_roofs_only_gives_a_potential_with_no_midpoint_after_fit_out(self):
        q, t = self.build()
        self.assertAlmostEqual(t["hall_area_ha"], 1.0, places=1)
        early = q["2023Q1"]   # roof on January 2023, fit-out takes six months
        self.assertEqual((early["halls_roofed"], early["est_lo"], early["est_mid"], early["est_hi"]), (1, 0.0, 0.0, 0.0))
        self.assertTrue(early["basis"].startswith("roof on (1.0 ha) but not yet fitted out"), early["basis"])
        later = q["2023Q4"]
        self.assertEqual((later["est_lo"], later["est_mid"]), (0.0, None))
        self.assertAlmostEqual(later["est_hi"], 0.9 * 15.0 * t["hall_area_ha"], places=0)
        self.assertIn("no operating evidence, so 0 to potential", later["basis"])
        self.assertEqual(q["2022Q4"]["basis"], "no roof yet")

    def test_site_density_replaces_the_default_when_documented(self):
        q, t = self.build(site_overrides=dict(capacity_tier="A2", capacity_mw="30", capacity_basis="it_reported"))
        self.assertEqual(t["density_basis"], "site documented capacity / hall area")
        self.assertAlmostEqual(t["density_mw_per_ha"], 30.0 / t["hall_area_ha"], places=0)

    def test_placeholder_means_pre_operation(self):
        q, _ = self.build(tl=tl_rows(("synth", "2022-01-01", "", 0, "placeholder", "U")), hall=False)
        r = q["2022Q4"]
        self.assertEqual((r["cap_doc_mw"], r["est_lo"], r["est_mid"], r["est_hi"], r["basis"]), (0.0, 0.0, 0.0, 0.0, "pre-operation (documented placeholder)"))

    def test_radar_entry_is_never_estimated(self):
        q, _ = self.build(site_overrides=dict(coords_quality="radar_candidate", site_class="radar_candidate", notes="radar_candidate score=0.9 area_ha=6"))
        r = q["2024Q4"]
        self.assertEqual((r["est_lo"], r["est_mid"], r["est_hi"]), (0.0, None, 0.0))
        self.assertTrue(r["basis"].startswith("not estimated: radar-detected structure"), r["basis"])

    def test_generator_watch_overrides_capacity_and_ignores_flux(self):
        flux = [dict(d=f"2025-0{m}", nox_kgh_cal=1000.0, nox_se=100.0, n_days=10) for m in (7, 8, 9)]
        q, _ = self.build(site_overrides=dict(site_class="generator_planned", nox_ef_lo="0.5", nox_ef_hi="1.5", nox_ef_basis="permit_upper_limit"),
                          tl=tl_rows(("synth", "2024-01-01", "", 100, "grid_connection", "A1")), flux=flux)
        r = q["2025Q3"]
        self.assertEqual((r["est_lo"], r["est_mid"], r["est_hi"], r["basis"]), (0.0, None, 0.0, "generator watch: campus load unknown; NOx screen only"))
        self.assertIsNotNone(r["no2_flux"])
        self.assertIn("mw_unavailable_reason", r["no2_flux"])   # a permit ceiling is not an emission factor

    def test_significant_flux_overrides_the_capacity_band(self):
        flux = [dict(d=f"2025-0{m}", nox_kgh_cal=1000.0, nox_se=100.0, n_days=10) for m in (7, 8, 9)]
        tl = tl_rows(("synth", "2024-01-01", "", 100, "it_reported", "A2"))
        q, _ = self.build(site_overrides=dict(nox_ef_lo="0.5", nox_ef_hi="1.5", site_class="ai_training"), tl=tl, flux=flux)
        r = q["2025Q3"]
        self.assertTrue(r["basis"].startswith("NO2-flux on-site generation: 1000 ± 58 kg NOx/h"), r["basis"])
        # quarterly se = sqrt(3 × 100²) / 3 = 57.7; lo = (1000 − 57.7) / 1.5, hi = (1000 + 57.7) / 0.5, midpoint at (0.5 + 1.5) / 2
        self.assertEqual((r["est_lo"], r["est_mid"], r["est_hi"]), (628.0, 1000.0, 2115.0))
        self.assertEqual((q["2025Q2"]["est_lo"], q["2025Q2"]["est_hi"]), (50.0, 100.0))          # AI-training prior on the capacity before the flux

    def test_weak_flux_and_adjacent_plant_leave_the_capacity_band_alone(self):
        weak = [dict(d=f"2025-0{m}", nox_kgh_cal=150.0, nox_se=200.0, n_days=10) for m in (7, 8, 9)]   # 150 < 2 × 115 quarterly se
        tl = tl_rows(("synth", "2024-01-01", "", 100, "it_reported", "A2"))
        q, _ = self.build(site_overrides=dict(nox_ef_lo="0.5", nox_ef_hi="1.5"), tl=tl, flux=weak)
        self.assertTrue(q["2025Q3"]["basis"].startswith("documented capacity in force"))
        strong = [dict(d=f"2025-0{m}", nox_kgh_cal=1000.0, nox_se=100.0, n_days=10) for m in (7, 8, 9)]
        q, _ = self.build(site_overrides=dict(nox_ef_lo="0.5", nox_ef_hi="1.5", nox_ef_note="ADJACENT PLANT, not the campus"), tl=tl, flux=strong)
        self.assertTrue(q["2025Q3"]["basis"].startswith("documented capacity in force"))
        self.assertIsNotNone(q["2025Q3"]["no2_flux"])


class StatusPrecedenceTests(unittest.TestCase):
    """build_status.main on synthetic timelines: which evidence sets the words, the key series and the evidence kind."""

    def render(self, quarters, site=None, timeline_extra=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "site" / "data" / "timeline").mkdir(parents=True)
            s = dict(site_id="synth", name="Synth", lat=1, lon=1, country="US", polygons=[])
            s.update(site or {})
            (root / "site" / "data" / "sites.json").write_text(json.dumps({"sites": [s]}))
            t = dict(quarters=quarters, roof_on={"h1": "2024-01"}, ntl_lit=None)
            t.update(timeline_extra or {})
            (root / "site" / "data" / "timeline" / "synth.json").write_text(json.dumps(t))
            with patch.multiple(build_status, ROOT=root, SITE=root / "site"), contextlib.redirect_stdout(io.StringIO()):
                build_status.main()
            return json.loads((root / "site" / "data" / "status.json").read_text())["sites"][0]

    def q(self, name="2025Q3", **o):
        base = dict(q=name, halls_total=1, halls_roofed=1, cap_doc_mw=100, cap_tier="A2", cap_basis="it_reported", basis="documented capacity in force",
                    est_lo=20, est_mid=40, est_hi=60, fitted_ha=1.0, no2_flux=None)
        base.update(o)
        return base

    def test_dedicated_plant_beats_flux_and_everything_else(self):
        plant = dict(basis="dedicated_plant_measured", plants=[dict(gross_avg_mw=80.0, eligible=True)], allocated_gross_avg_mw=80.0, it_equivalent_avg_mw=64.0)
        r = self.render([self.q(campd=plant, cap_basis="facility_measured_annual", basis="NO2-flux on-site generation: 1000 kg", no2_flux=dict(nox_kgh=1000, nox_se=100))])
        self.assertEqual((r["key"], r["evidence_kind"], r["confidence"]), ("plant", "measured", "high"))
        self.assertTrue(r["running"].startswith("yes: dedicated plant generated 80 MW"))

    def test_flux_beats_reported_electricity(self):
        r = self.render([self.q(cap_basis="facility_measured_annual", basis="NO2-flux on-site generation: 1000 kg", no2_flux=dict(nox_kgh=1000, nox_se=100), est_lo=600, est_mid=1000, est_hi=2000)])
        self.assertEqual((r["key"], r["evidence_kind"], r["combustion"]), ("nox", "measured", True))
        self.assertTrue(r["running"].startswith("yes: on-site generation detected since 2025Q3"))
        weak = self.render([self.q(cap_basis="facility_measured_annual", basis="NO2-flux on-site generation", no2_flux=dict(nox_kgh=150, nox_se=100))])
        self.assertEqual(weak["key"], "capacity")   # not significant: falls through to the reported electricity

    def test_reported_electricity_and_its_carried_year(self):
        r = self.render([self.q("2024Q4", cap_basis="facility_measured_annual", cap_doc_mw=40, est_lo=36, est_mid=40, est_hi=44),
                         self.q("2025Q3", cap_basis="carried_measured_annual", cap_doc_mw=40, est_lo=28, est_mid=40, est_hi=52)])
        self.assertEqual((r["key"], r["evidence_kind"], r["confidence"]), ("capacity", "measured", "high"))
        self.assertEqual(r["running"], "yes: operator reports an average IT load of 40 MW in 2024 (latest published year, carried forward)")
        self.assertIn("operator-reported average IT load", r["series_label"])

    def test_water_derived_and_its_carried_year_are_derived(self):
        r = self.render([self.q("2024Q4", cap_basis="water_derived_it_annual", cap_doc_mw=40, est_lo=20, est_mid=40, est_hi=80),
                         self.q("2025Q3", cap_basis="carried_water_derived_it_annual", cap_doc_mw=40, cap_upper_bound=True, est_lo=16, est_mid=40, est_hi=100)])
        self.assertEqual((r["key"], r["evidence_kind"], r["confidence"]), ("capacity", "derived", "low"))
        self.assertTrue(r["running"].startswith("yes: about 40 MW average IT load in 2024, derived from the operator's published water use"))
        self.assertIn("upper bound", r["running"])
        self.assertTrue(r["running"].endswith("(carried forward)"))

    def test_documented_capacity_is_presumed_with_confidence_by_tier_and_detected_only_with_lights(self):
        a2 = self.render([self.q()])
        self.assertEqual((a2["evidence_kind"], a2["confidence"], a2["key"]), ("presumed", "medium", "capacity"))
        self.assertTrue(a2["running"].startswith("presumably: documented 100 MW in force since 2025Q3"))
        a1 = self.render([self.q(cap_tier="A1")])
        self.assertEqual(a1["confidence"], "high")
        lit = self.render([self.q()], timeline_extra=dict(ntl_lit="2025-05"))
        self.assertEqual(lit["evidence_kind"], "detected")

    def test_roofs_only_and_radar_are_construction(self):
        roofs = self.render([self.q(cap_doc_mw=None, cap_basis=None, est_lo=0, est_mid=None, est_hi=13.5, basis="roofed potential")])
        self.assertEqual((roofs["key"], roofs["evidence_kind"], roofs["confidence"]), ("roofs", "construction", "low"))
        self.assertEqual(roofs["running"], "unknown: roofs on, no activity evidence")
        radar = self.render([self.q(cap_doc_mw=None, est_mid=None, est_hi=0)], site=dict(coords_quality="radar_candidate", notes="score=0.9 area_ha=6"), timeline_extra=dict(ntl_lit="2025-05"))
        self.assertEqual((radar["evidence_kind"], radar["load"]), ("construction", "not estimated (unconfirmed structure)"))


if __name__ == "__main__":
    unittest.main()
