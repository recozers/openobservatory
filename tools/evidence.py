"""Findings from merged requests for work, gathered for the public site.

Everything a merged request for work says about a site, a country or the whole inventory reaches the site through this
module, with no hand wiring. `build_status.py` calls `build()`, which

1. runs the adapters below. Each reads the committed results of one merged request and turns its rows into findings, so
   when that request's script is rerun and merged, the site changes on the next build;
2. reads every `data/evidence/*.csv`, which contributors write by hand or from their own scripts (columns in
   `data/evidence/README.md`);
3. validates every finding, writes `site/data/evidence.json` and returns the findings per site for `status.json`.

The map views, the list, the research view and the findings page all read these. Findings sit beside the estimates and never
change a number. The one change to the plain-language status is an imagery verdict (`answers` = where), which replaces
"unconfirmed" in a radar-found entry's Built line.

    python tools/evidence.py            # validate, write site/data/evidence.json, print counts per request
    python tools/evidence.py --check    # validate only; exit 1 on any problem
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_requests_page import slug  # noqa: E402

REPO = "https://github.com/recozers/openobservatory"
EVIDENCE_DIR = "data/evidence"
OUT = "site/data/evidence.json"

COLUMNS = ["subject", "request", "answers", "finding", "detail", "verdict", "confidence", "period", "source",
           "pull_request", "recorded"]
REQUIRED = ("subject", "request", "answers", "finding", "confidence", "source")
ANSWERS = ("where", "built", "capacity", "running", "utilisation", "workload", "sources")
CONFIDENCE = ("high", "medium", "low")
VERDICTS = ("data-hall complex", "unclear", "not a data centre")
REQUEST_ID = re.compile(r"^(RFW|T|PAID)-\d{2}$")
_DATE = r"\d{4}(?:-\d{2}(?:-\d{2})?)?|\d{4}Q[1-4]|FY\d{4}"
PERIOD = re.compile(rf"^(?:{_DATE})(?:\.\.(?:{_DATE}))?$")
MAX_FINDING, MAX_DETAIL = 400, 1500
COUNTRIES = {"AE": "United Arab Emirates", "AU": "Australia", "CN": "China", "DK": "Denmark", "GB": "United Kingdom",
             "ID": "Indonesia", "IE": "Ireland", "JP": "Japan", "MY": "Malaysia", "NO": "Norway", "PT": "Portugal",
             "SE": "Sweden", "US": "United States"}
# Chinese hubs: the radar review's hub key -> (label, inventory entry for the hub as a whole)
HUBS = {"ulanqab": ("Ulanqab", "ulanqab_hub"), "horinger": ("Horinger", "helingeer_hub"),
        "zhangbei": ("Zhangbei", "zhangbei_hub"), "guian": ("Gui'an", "guian_hub"), "qingyang": ("Qingyang", "qingyang_hub"),
        "zhongwei": ("Zhongwei", "zhongwei_hub"), "chongqing": ("Chongqing", "chongqing_hub")}
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


class EvidenceError(ValueError):
    pass


# ---------------------------------------------------------------- helpers

def read_csv(root: Path, rel: str) -> list[dict]:
    with (root / rel).open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def month(value) -> str:
    m = re.match(r"^(\d{4})-(\d{2})", str(value or ""))
    return f"{MONTHS[int(m.group(2)) - 1]} {m.group(1)}" if m else str(value or "")


def sigma(z: float) -> str:
    return f"{z:.2f}σ".replace("-", "−")


def join_and(parts: list[str]) -> str:
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


def pr_number(text) -> str:
    m = re.search(r"pull request (\d+)", str(text or ""))
    return m.group(1) if m else ""


def finding(subject, request, answers, text, source, confidence, detail="", verdict="", period="", pull_request="",
            recorded="") -> dict:
    return dict(subject=subject, request=request, answers=answers, finding=text, detail=detail, verdict=verdict,
                confidence=confidence, period=period, source=source, pull_request=str(pull_request or ""),
                recorded=recorded)


def hub_subject(hub: str, sites: dict) -> str:
    site = HUBS.get(hub, ("", ""))[1]
    return site if site in sites else "country:CN"


def request_key(request_id: str):
    prefix, _, n = request_id.partition("-")
    return ({"RFW": 0, "T": 1, "PAID": 2}.get(prefix, 3), int(n) if n.isdigit() else 0)


# ---------------------------------------------------------------- adapters

ADAPTERS: list[dict] = []


def adapter(request: str, *reads: str):
    """Register a function that turns one merged request's committed results into findings."""
    def register(fn):
        ADAPTERS.append(dict(request=request, reads=reads, fn=fn, name=fn.__name__))
        return fn
    return register


@adapter("RFW-01", "data/cn_radar_review.csv")
def radar_review(root: Path, sites: dict) -> list[dict]:
    """Imagery verdicts on the radar-found structures in China (pull request 16). Structures that left the inventory are
    reported on their hub, so the rejections stay visible."""
    out = []
    for r in read_csv(root, "data/cn_radar_review.csv"):
        paths = [p for p in r["evidence"].split(";") if p]
        checks = "; ".join(f"{label}: {r[col].strip()}" for label, col in
                           (("Web imagery", "highres_check"), ("OpenStreetMap", "osm_context"), ("Outline", "outline_check"))
                           if (r.get(col) or "").strip())
        common = dict(detail=checks, pull_request=pr_number(r.get("reviewer")), recorded=r.get("reviewed_on", ""))
        source = paths[0] if paths else "data/cn_radar_review.csv"
        if r["site_id"] in sites:
            out.append(finding(r["site_id"], "RFW-01", "where", f"Imagery review: {r['verdict']}. {r['reason']}", source,
                               r["confidence"], verdict=r["verdict"], **common))
        else:
            area, lat, lon = num(r["area_ha"]), num(r["lat"]), num(r["lon"])
            where = f", {area:.0f} ha at {lat:.4f}, {lon:.4f}" if None not in (area, lat, lon) else ""
            out.append(finding(hub_subject(r["hub"], sites), "RFW-01", "where",
                               f"Radar structure {r['site_id']}{where}: reviewed as {r['verdict']}, so it is not in the "
                               f"inventory. {r['reason']}", source, r["confidence"], **common))
    return out


@adapter("RFW-03", "results_cn/construction_index_entries.csv")
def construction_index(root: Path, sites: dict) -> list[dict]:
    """Radar dating windows per structure and a construction summary per hub (pull request 17)."""
    entries = read_csv(root, "results_cn/construction_index_entries.csv")
    out = []
    for r in entries:
        if r["site_id"] not in sites:
            continue  # rejected structures are counted in their hub's summary below
        start, end = r["window_from"], r["window_to"]
        window = f"to {month(start)}" if start == end else f"between {month(start)} and {month(end)}"
        spread = int(num(r["spread_months"]) or 0)
        label = HUBS.get(r["hub"], (r["hub"],))[0]
        out.append(finding(
            r["site_id"], "RFW-03", "built",
            f"Radar dates the structure {window}. It counts in {label}'s construction index for {r['quarter']} as "
            f"{'a data-hall complex' if r['verdict'] == 'data-hall complex' else r['verdict']}.",
            "results_cn/construction_index_entries.csv", "medium" if spread <= 3 else "low",
            detail=f"Sentinel-1 dating: the window runs from the onset of the radar rise to the first month of the sustained "
                   f"plateau ({spread} month{'' if spread == 1 else 's'}). Area {num(r['area_ha']) or 0:.1f} ha is the radar outline, not floor space.",
            period=start if start == end else f"{start}..{end}", pull_request=17))
    plural = {"data-hall complex": "data-hall complexes", "unclear": "unclear", "not a data centre": "not data centres"}
    by_hub = defaultdict(list)
    for r in entries:
        by_hub[r["hub"]].append(r)
    for hub, rows in by_hub.items():
        quarters = sorted(r["quarter"] for r in rows)
        parts = []
        for verdict in VERDICTS:
            chosen = [r for r in rows if r["verdict"] == verdict]
            if chosen:
                name = verdict if len(chosen) == 1 else plural[verdict]
                parts.append(f"{len(chosen)} {name} ({sum(num(r['area_ha']) or 0 for r in chosen):.0f} ha)")
        others = [r["verdict"] for r in rows if r["verdict"] not in VERDICTS]
        if others:
            parts.append(f"{len(others)} without a verdict")
        label = HUBS.get(hub, (hub,))[0]
        out.append(finding(
            hub_subject(hub, sites), "RFW-03", "built",
            f"Radar construction index for {label}: {len(rows)} new hall-like "
            f"{'structure' if len(rows) == 1 else 'structures'} of 5 ha or more appeared "
            + (f"in {quarters[0]}" if quarters[0] == quarters[-1] else f"between {quarters[0]} and {quarters[-1]}")
            + f": {join_and(parts)}.",
            "results_cn/construction_index.csv", "low",
            detail="Areas are radar outlines, not floor space, and unclear structures are not counted as data halls. The "
                   "index shows where building went on in the parks scanned so far; it does not measure capacity, fit-out "
                   "or operation. Counts per quarter, with the area dated firmly inside each quarter, are in the source file.",
            period=quarters[0] if quarters[0] == quarters[-1] else f"{quarters[0]}..{quarters[-1]}", pull_request=17))
    return out


@adapter("RFW-07", "results_cn/chindata_data_centres.csv", "results_cn/sec_archive_sources.csv",
         "data/chindata_dc_locations.csv", "results_cn/edgar_hub_mentions.csv")
def chindata(root: Path, sites: dict) -> list[dict]:
    """Chindata's per-data-centre tables, its stated locations and the hub-name search (pull request 15)."""
    docs = {r["key"]: r for r in read_csv(root, "results_cn/sec_archive_sources.csv")}
    groups = defaultdict(list)
    for r in read_csv(root, "results_cn/chindata_data_centres.csv"):
        if r["status"] == "in_service" and r["region"].startswith("Greater Beijing Area"):
            groups[(r["as_of"], r["key"])].append(r)
    out = []
    for (as_of, key), rows in sorted(groups.items()):
        def metric(name):
            return {r["data_center"]: num(r["value"]) for r in rows if r["metric"] == name and num(r["value"]) is not None}
        cap, used, ratio = metric("it_capacity_in_service_mw"), metric("utilized_it_capacity_mw"), metric("utilization_ratio_pct")
        total = sum(cap.values())
        if not total:
            continue
        if used:
            in_use = f"{sum(used.values()):.0f} MW of it in customer use ({100 * sum(used.values()) / total:.0f} %)"
        elif ratio:
            weighted = sum(cap[d] * ratio[d] / 100 for d in cap if d in ratio)
            in_use = f"{100 * weighted / total:.1f} % in customer use, weighting each data centre's ratio by its capacity"
        else:
            continue
        doc = docs[key]
        out.append(finding(
            "country:CN", "RFW-07", "utilisation",
            f"Chindata's {doc['form']} lists {len(cap)} data centres in service in its Greater Beijing Area on {as_of}: "
            f"{total:.0f} MW, {in_use}.",
            doc["sec_url"], "high",
            detail="Capacity in customer use is Chindata's commercial measure, not a power measurement. The filing gives no "
                   "city for most data centres, so these figures are not attached to inventory sites.",
            period=as_of, pull_request=15))
    located = defaultdict(list)
    for r in read_csv(root, "data/chindata_dc_locations.csv"):
        if "not stated" not in r["hub"]:
            located[r["hub"]].append(r["data_center"])
    if located:
        out.append(finding(
            "country:CN", "RFW-07", "where",
            f"Chindata's own releases locate {sum(len(d) for d in located.values())} of its data centres: "
            + "; ".join(f"{join_and(dcs)}, {hub}" for hub, dcs in located.items()) + ".",
            "data/chindata_dc_locations.csv", "medium",
            detail="Each location is quoted verbatim from a Chindata release. The Hebei campus is taken as Zhangjiakou "
                   "because the FY2022 20-F names Chindata's campuses as Zhangjiakou and Datong.",
            pull_request=15))
    from tools.chindata_filings import DOCS, HUB_TERMS, SEARCH_KEYS
    searched = [DOCS[k] for k in SEARCH_KEYS]
    annual = sum(1 for d in searched if d.form.startswith("20-F"))
    prospectuses = len(searched) - annual
    documents = f"{annual} annual reports" + (f" and {'a prospectus' if prospectuses == 1 else f'{prospectuses} other filings'}"
                                              if prospectuses else "")
    companies = sorted({d.company for d in searched})
    mentions = read_csv(root, "results_cn/edgar_hub_mentions.csv")
    for label in HUB_TERMS:
        hub = label.lower().replace("'", "")
        hits = [m for m in mentions if m["hub"] == label]
        near = [m for m in hits if (m.get("figures_nearby") or "").strip()]
        who = sorted({m["company"] for m in hits})
        said = (f"{join_and(who)} {'mentions' if len(who) == 1 else 'mention'} it {len(hits)} times, "
                + ("none of them next to a figure" if not near else f"{len(near)} of them next to a figure")) if hits else "none of them names it"
        out.append(finding(
            hub_subject(hub, sites), "RFW-07", "capacity",
            f"A search of {documents} from {join_and(companies)} found "
            f"{'no' if not near else 'possible'} capacity or utilisation figures for {label}: {said}.",
            "results_cn/edgar_hub_mentions.csv", "medium",
            detail="The search covered the reports the Internet Archive holds; EDGAR's full-text search, which would "
                   "include current reports, has not been run (RFW-07).",
            pull_request=15))
    return out


@adapter("RFW-14", "results_no2/plume_date_sensitivity.csv")
def plume_dates(root: Path, sites: dict) -> list[dict]:
    """The plume test at seven start dates under the current and season-matched tests (pull request 19)."""
    series = defaultdict(dict)
    for r in read_csv(root, "results_no2/plume_date_sensitivity.csv"):
        series[(r["role"], r["file_site"], r["series"])][int(r["offset_months"])] = r
    out = []
    for (role, _, sid), by_offset in series.items():
        if role != "site" or sid not in sites or 0 not in by_offset:
            continue
        at = by_offset[0]
        z_now, z_season = num(at["z_current"]), num(at["z_season"])
        if z_now is None or z_season is None:
            continue
        season = {o: num(r["z_season"]) for o, r in by_offset.items()}
        clears = sum(1 for z in season.values() if z is not None and z >= 2.5)
        passes = all(season.get(o) is not None and season[o] >= 2.5 for o in (-1, 0, 1))
        out.append(finding(
            sid, "RFW-14", "running",
            f"NO₂ plume test at the documented start, {month(at['documented'])}: {sigma(z_now)} with the current test, "
            f"{sigma(z_season)} season-matched. The season-matched score reaches 2.5σ at {clears} of {len(season)} start "
            f"dates within three months.",
            "results_no2/plume_date_sensitivity.csv", "medium",
            detail=("Passes" if passes else "Does not pass") + " the rule RFW-14 recommends: a season-matched score of 2.5σ "
                   "or more at the documented start and at the months either side. A plume shows fuel burning near the "
                   "site, not the campus's electricity use, and a city-edge or adjacent-plant plume has to be ruled out.",
            period=at["documented"][:7], pull_request=19))
    controls = {k: v for k, v in series.items() if k[0] == "control" and 0 in v}
    if controls:
        def count(test, offsets=None):
            return sum(1 for v in controls.values()
                       if any((num(r[test]) or 0) >= 2.5 for o, r in v.items() if offsets is None or o in offsets))
        top = max((num(r["z_season"]) for v in controls.values() for r in v.values() if num(r["z_season"]) is not None),
                  default=None)
        out.append(finding(
            "global", "RFW-14", "running",
            f"Plume test control points: {count('z_current', {0})} of {len(controls)} reach 2.5σ at the documented start "
            f"with the current test and {count('z_season', {0})} with the season-matched test; across all seven start "
            f"dates, {count('z_current')} and {count('z_season')}"
            + (f" (highest season-matched score {sigma(top)})." if top is not None else "."),
            "results_no2/plume_date_sensitivity.csv", "high",
            detail="Control points sit away from any campus, so a score of 2.5σ there is a false alarm.",
            pull_request=19))
    return out


@adapter("RFW-19", "data/microsoft_metro_fy25.csv", "data/operator_disclosures.csv")
def microsoft_metros(root: Path, sites: dict) -> list[dict]:
    """Microsoft's FY25 electricity per metro, as context for the campuses in each metro (pull request 21)."""
    rows = read_csv(root, "data/microsoft_metro_fy25.csv")
    urls = {r["site_id"]: r["source_url"] for r in read_csv(root, "data/operator_disclosures.csv")
            if r["metric"] == "electricity_mwh" and r["source_url"]}
    out = []
    for r in rows:
        mwh, avg = num(r["electricity_mwh"]), num(r["avg_mw"])
        campuses = [c for c in (r.get("inventory_campuses") or "").split(";") if c in sites]
        if mwh is None or not campuses:
            continue
        note = re.sub(r"^context:\s*", "", r.get("attribution") or "").strip()
        for campus in campuses:
            out.append(finding(
                campus, "RFW-19", "utilisation",
                f"Microsoft reports {mwh:,.0f} MWh for its {r['location']} data centres in FY25, "
                f"{avg:.{1 if avg < 10 else 0}f} MW on average: "
                f"context for this campus, not its load.",
                urls.get(r["site_id"], "data/microsoft_metro_fy25.csv"), "high",
                detail=(note[:1].upper() + note[1:] + ".") if note else "",
                period="FY2025", pull_request=21))
    unmatched = sorted((r for r in rows if not (r.get("inventory_campuses") or "").strip() and num(r["electricity_mwh"])),
                       key=lambda r: -num(r["electricity_mwh"]))
    total = sum(num(r["electricity_mwh"]) or 0 for r in rows)
    if rows and unmatched:
        largest = [f"{r['location']} at {num(r['electricity_mwh']) / 1e6:.2f} TWh" for r in unmatched[:3]]
        out.append(finding(
            "global", "RFW-19", "utilisation",
            f"Microsoft's FY25 table gives electricity for {len(rows)} metros, {total / 1e6:.1f} TWh in all. "
            f"{len(unmatched)} have no inventory campus; the largest are {join_and(largest)}.",
            urls.get(rows[0]["site_id"], "data/microsoft_metro_fy25.csv"), "high",
            detail="A metro figure covers every Microsoft data centre in the metro, so none is attributed to a single "
                   "campus (docs/microsoft_metro_notes.md).",
            period="FY2025", pull_request=21))
    return out


EIA_STATUS = {"OP": "operating", "SB": "on standby", "OS": "out of service", "OA": "out of service", "P": "planned",
              "L": "awaiting approval", "T": "approved", "U": "under construction", "V": "under construction",
              "TS": "built, not yet in commercial operation"}
EIA_TECH = {"Natural Gas Fired Combined Cycle": "gas combined cycle", "Natural Gas Fired Combustion Turbine": "gas turbines",
            "Natural Gas Internal Combustion Engine": "gas engines", "Petroleum Liquids": "oil-fired units"}


@adapter("RFW-20", "results/eia860m_candidates.csv")
def eia860m(root: Path, sites: dict) -> list[dict]:
    """Fossil and fuel-cell plants in EIA-860M near inventory sites, each checked against a permit or statement (pull request 22)."""
    out = []
    for r in read_csv(root, "results/eia860m_candidates.csv"):
        if r["nearest_site"] not in sites:
            continue
        techs = []
        for part in r["technologies"].split("; "):
            name = re.sub(r"\s+[\d.]+ MW$", "", part)
            label = EIA_TECH.get(name, name.lower())
            if label not in techs:
                techs.append(label)
        statuses = []
        for code in r["statuses"].split("; "):
            label = EIA_STATUS.get(code.strip(), code.strip())
            if label and label not in statuses:
                statuses.append(label)
        mw, km = num(r["nameplate_mw"]) or 0, num(r["distance_km"]) or 0
        out.append(finding(
            r["nearest_site"], "RFW-20", "utilisation",
            f"{r['plant_name']}, {r['entity']}, {km:.1f} km away: {mw:,.0f} MW of {join_and(techs)} in EIA-860M, "
            f"first operation {month(r['first_operation'])}, EIA status {join_and(statuses)}. Verdict: {r['verdict']}.",
            r["evidence_url"] or "results/eia860m_candidates.csv", "high" if r["evidence_url"] else "medium",
            detail=r.get("review_note", ""), period=r["first_operation"], pull_request=22))
    return out


@adapter("RFW-32", "results/link_check.csv", "results/link_check_dead.csv")
def link_check(root: Path, sites: dict) -> list[dict]:
    """Dead or blocked source links, on the sites whose records cite them, and the overall count (pull request 18)."""
    checked = read_csv(root, "results/link_check.csv")
    dead = read_csv(root, "results/link_check_dead.csv")
    cache: dict[str, list[dict]] = {}
    out = []

    def cited_by(url: str, files: list[str]) -> list[str]:
        found = []
        for rel in files:
            m = re.fullmatch(r"data/polygons/([\w\-]+)\.geojson", rel)
            if m:
                found.append(m.group(1))
            elif rel.endswith(".csv") and (root / rel).exists():
                if rel not in cache:
                    cache[rel] = read_csv(root, rel)
                found += [row["site_id"] for row in cache[rel] if row.get("site_id") and any(url in (v or "") for v in row.values())]
        return sorted({s for s in found if s in sites})

    def what(status: str, note: str) -> str:
        if status == "error":
            return f"a connection error ({note})" if note else "a connection error"
        if status in ("401", "403", "412", "429"):
            return f"HTTP {status}, which usually means the site blocks automated checks; the page may still exist"
        return f"HTTP {status}"

    for r in dead:
        for sid in cited_by(r["url"], [f for f in r["used_in"].split(";") if f]):
            archive = f" The Internet Archive has a copy: {r['archive_url']}" if r.get("archive_url") else " No archived copy was found."
            out.append(finding(
                sid, "RFW-32", "sources",
                f"A source cited for this site returned {what(r['status'], r.get('note') or '')} on {r['checked_at'][:10]}: {r['url']}",
                "results/link_check_dead.csv",
                "high" if r["status"] in ("404", "410") else "medium" if r["status"] == "error" else "low",
                detail=archive.strip(), pull_request=18, recorded=r["checked_at"][:10]))
    if checked:
        names = {"error": "connection errors", "404": "not found", "410": "gone", "403": "forbidden", "429": "rate-limited",
                 "412": "refused"}
        counts = Counter(r["status"] for r in dead)
        tested = [r for r in checked if (r.get("status") or "").strip()]
        date = max((r["checked_at"] for r in checked if r.get("checked_at")), default="")[:10]
        out.append(finding(
            "global", "RFW-32", "sources",
            f"Source link check on {date}: {len(dead)} of {len(tested)} links failed ("
            + ", ".join(f"{n} {names.get(s, 'HTTP ' + s)}" for s, n in counts.most_common())
            + f"); {sum(1 for r in dead if r.get('archive_url'))} of those have an archived copy. "
            f"{len(checked) - len(tested)} links were not fetched, such as SEC EDGAR's.",
            "results/link_check_dead.csv", "high",
            detail="The source file lists each failed link, the files that cite it and any archived copy. Blocked and "
                   "rate-limited pages may still exist.", pull_request=18, recorded=date))
    return out


# ---------------------------------------------------------------- contributed files, validation, output

def inventory(root: Path) -> dict:
    return {r["site_id"]: r for r in read_csv(root, "data/sites.csv")}


def request_titles(root: Path) -> dict:
    titles = {}
    for line in (root / "REQUESTS_FOR_WORK.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^#{2,6} ((?:RFW|T|PAID)-\d{2}) (.+?)\s*$", line)
        if m:
            titles[m.group(1)] = dict(title=m.group(2), anchor=slug(f"{m.group(1)} {m.group(2)}"))
    return titles


def contributed(root: Path) -> tuple[list[tuple[str, dict]], list[str]]:
    rows, errors = [], []
    for path in sorted((root / EVIDENCE_DIR).glob("*.csv")):
        rel = path.relative_to(root).as_posix()
        with path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            header = reader.fieldnames or []
            unknown = [c for c in header if c not in COLUMNS]
            missing = [c for c in REQUIRED if c not in header]
            if unknown or missing:
                errors.append(f"{rel}: header must use the columns {', '.join(COLUMNS)}"
                              + (f"; unknown: {', '.join(unknown)}" if unknown else "")
                              + (f"; missing: {', '.join(missing)}" if missing else ""))
                continue
            for line, r in enumerate(reader, start=2):
                if None in r:
                    errors.append(f"{rel}:{line}: more fields than columns (quote any value that contains a comma)")
                    continue
                rows.append((f"{rel}:{line}", {c: (r.get(c) or "").strip() for c in COLUMNS}))
    return rows, errors


def validate(row: dict, where: str, sites: dict, requests: dict, root: Path) -> list[str]:
    problems = []
    for col in REQUIRED:
        if not row.get(col):
            problems.append(f"{col} is empty")
    subject = row.get("subject", "")
    site = subject in sites
    if subject and not (site or subject == "global" or re.fullmatch(r"country:[A-Z]{2}", subject)):
        problems.append(f"subject {subject!r} is not an inventory site_id, country:<two-letter code> or global")
    request = row.get("request", "")
    if request and not (REQUEST_ID.match(request) and request in requests):
        problems.append(f"request {request!r} is not a heading in REQUESTS_FOR_WORK.md")
    if row.get("answers") and row["answers"] not in ANSWERS:
        problems.append(f"answers must be one of {', '.join(ANSWERS)}")
    if row.get("confidence") and row["confidence"] not in CONFIDENCE:
        problems.append(f"confidence must be one of {', '.join(CONFIDENCE)}")
    if row.get("verdict"):
        if row["verdict"] not in VERDICTS:
            problems.append(f"verdict must be one of {', '.join(VERDICTS)}")
        if row.get("answers") != "where" or not site:
            problems.append("a verdict needs answers = where and an inventory site as the subject")
    text = row.get("finding", "")
    if len(text) > MAX_FINDING or "\n" in text:
        problems.append(f"finding must be one line of at most {MAX_FINDING} characters")
    if len(row.get("detail", "")) > MAX_DETAIL:
        problems.append(f"detail must be at most {MAX_DETAIL} characters")
    if row.get("period") and not PERIOD.match(row["period"]):
        problems.append("period must look like 2025, 2025-01, 2025-01-31, 2025Q1 or FY2025, or two of them joined by ..")
    if row.get("pull_request") and not row["pull_request"].isdigit():
        problems.append("pull_request must be a number")
    if row.get("recorded") and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["recorded"]):
        problems.append("recorded must be a date, YYYY-MM-DD")
    source = row.get("source", "")
    if source and not source.startswith(("https://", "http://")):
        parts = Path(source).parts
        if source.startswith("/") or ".." in parts or not (root / source).exists():
            problems.append(f"source {source!r} is neither a URL nor a file in the repository")
        elif parts[:2] == ("data", "private") or parts[0] in (".env", "secrets"):
            problems.append("source must not point at private files")
    return [f"{where}: {p}" for p in problems]


def collect(root: Path = ROOT, adapters: list[dict] | None = None):
    """Every finding with where it came from, and every problem found. Returns (rows, errors, sites, requests)."""
    sites, requests = inventory(root), request_titles(root)
    rows, errors = [], []
    for a in ADAPTERS if adapters is None else adapters:
        try:
            produced = a["fn"](root, sites)
        except (FileNotFoundError, KeyError) as e:
            errors.append(f"adapter {a['name']} ({a['request']}) could not read its results: {e!r}")
            continue
        origin = ", ".join(a["reads"])
        for i, r in enumerate(produced, start=1):
            if r.get("request") != a["request"]:
                errors.append(f"adapter {a['name']}, finding {i}: request must be {a['request']}")
            rows.append((f"adapter {a['name']}, finding {i}", origin, r))
    extra, problems = contributed(root)
    errors += problems
    rows += [(where, where.rsplit(":", 1)[0], r) for where, r in extra]
    for where, _, r in rows:
        errors += validate(r, where, sites, requests, root)
    return rows, errors, sites, requests


def public(row: dict, origin: str, sites: dict, requests: dict) -> dict:
    subject = row["subject"]
    kind = "global" if subject == "global" else "country" if subject.startswith("country:") else "site"
    name = (sites[subject]["name"] if kind == "site" else "All sites" if kind == "global"
            else COUNTRIES.get(subject[8:], subject[8:]))
    source = row["source"]
    if source.startswith(("http://", "https://")):
        url, label = source, urlparse(source).netloc.removeprefix("www.")
    else:
        url, label = f"{REPO}/blob/main/{source}", source
    request = requests[row["request"]]
    return dict(subject=subject, subject_type=kind, subject_name=name, request=row["request"],
                request_title=request["title"], request_anchor=request["anchor"], answers=row["answers"],
                finding=row["finding"], detail=row.get("detail", ""), verdict=row.get("verdict", ""),
                confidence=row["confidence"], period=row.get("period", ""), source_url=url, source_label=label,
                pull_request=int(row["pull_request"]) if row.get("pull_request") else None,
                recorded=row.get("recorded", ""), origin=origin)


def latest_verdict(site_findings: list[dict]) -> dict | None:
    """The imagery verdict that applies to a site: the most recently recorded, and the later one on a tie."""
    reviews = [(f.get("recorded") or "", i, f) for i, f in enumerate(site_findings) if f.get("verdict")]
    return max(reviews, key=lambda t: t[:2])[2] if reviews else None


def build(root: Path = ROOT, write: bool = True, out: Path | None = None, adapters: list[dict] | None = None) -> dict:
    """Validate, write site/data/evidence.json (or `out`) and return {site_id: [findings]}. Raises EvidenceError on any
    problem, so a bad finding stops the site build instead of reaching the site."""
    rows, errors, sites, requests = collect(root, adapters)
    if errors:
        raise EvidenceError("Findings from requests for work failed validation:\n  " + "\n  ".join(errors))
    order = {"global": 0, "country": 1, "site": 2}
    items = [public(r, origin, sites, requests) for _, origin, r in rows]
    ranked = sorted(enumerate(items), key=lambda t: (request_key(t[1]["request"]), order[t[1]["subject_type"]],
                                                     t[1]["subject_name"].lower(), ANSWERS.index(t[1]["answers"]), t[0]))
    items = [f for _, f in ranked]
    if write:
        payload = dict(
            note="Findings from merged requests for work, built by tools/evidence.py from committed results and "
                 "data/evidence/*.csv. They sit beside the estimates and do not change them.",
            requests={rid: requests[rid] for rid in sorted({f["request"] for f in items}, key=request_key)},
            findings=items)
        (out or root / OUT).write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    per_site = defaultdict(list)
    for f in items:
        if f["subject_type"] == "site":
            per_site[f["subject"]].append(f)
    return dict(per_site)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="validate only; exit 1 on any problem")
    args = ap.parse_args(argv)
    rows, errors, _, _ = collect(ROOT)
    for e in errors:
        print(e, file=sys.stderr)
    counts = Counter(r["request"] for _, _, r in rows)
    for request in sorted(counts, key=request_key):
        print(f"{request:8s} {counts[request]:4d} findings")
    if errors:
        print(f"{len(errors)} problems", file=sys.stderr)
        return 1
    if not args.check:
        per_site = build(ROOT)
        print(f"Wrote {OUT}: {len(rows)} findings, {len(per_site)} sites with findings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
