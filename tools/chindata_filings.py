"""Chindata's per-data-centre tables, and a hub-name search of US-listed Chinese operators' annual reports (RFW-07).

    python tools/chindata_filings.py fetch    # download the documents into data/cache/sec_archive/ (network, polite)
    python tools/chindata_filings.py build    # parse and check the tables, write results_cn/, update the disclosures file

SEC's EDGAR refuses automated requests whose User-Agent carries no contact email, and this project has no agreed contact
address. The documents are therefore read from the Internet Archive's copies of their SEC URLs; an "id_" snapshot returns
the archived bytes unchanged. Every output row cites the SEC URL, and results_cn/sec_archive_sources.csv records the
snapshot and the SHA-256 of what was parsed. EDGAR's full-text search is not reachable this way, so the hub-name search
covers only the annual reports listed below.

The tables give, per data centre and date, capacity in service, contracted capacity, capacity with indication of
interest and utilised capacity, or the same as ratios in the 2020 prospectus. "Utilised" is capacity in customer use as
Chindata reports it; its revenue recognition follows utilisation. It is a commercial figure, not a power measurement.
The filings do not give each data centre's city. data/chindata_dc_locations.csv holds the few locations Chindata's own
releases state, each with a verbatim quote that `build` checks against the cached document.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import html
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache" / "sec_archive"
OUT = ROOT / "results_cn"
DISCLOSURES = ROOT / "data" / "cn_operator_disclosures.csv"
LOCATIONS = ROOT / "data" / "chindata_dc_locations.csv"
SOURCES = OUT / "sec_archive_sources.csv"
OPERATOR = "Chindata Group (NASDAQ: CD, delisted 2023)"
TAG = "chindata_dc_table"
USER_AGENT = "OpenObservatory/1.0 (+https://openobservatory.info; https://github.com/recozers/openobservatory)"

CD = "https://www.sec.gov/Archives/edgar/data/1807192/"
VNET = "https://www.sec.gov/Archives/edgar/data/1508475/"
GDS = "https://www.sec.gov/Archives/edgar/data/1526125/"


@dataclass(frozen=True)
class Doc:
    key: str
    company: str
    form: str
    filed: str  # filing or prospectus date when known; annual reports without one are dated at fetch from their signature
    sec_url: str
    role: str   # tables, locations or search


DOCUMENTS = [
    Doc("cd_ipo_2020", "Chindata", "424B4 prospectus", "2020-09-29", CD + "000119312520259613/d853939d424b4.htm", "tables"),
    Doc("cd_20f_2021", "Chindata", "20-F FY2021", "2022-04-29", CD + "000156459022016827/cd-20f_20211231.htm", "tables"),
    Doc("cd_20f_2022", "Chindata", "20-F FY2022", "2023-04-28", CD + "000095017023015950/cd-20221231.htm", "tables"),
    Doc("cd_pr_2021q4", "Chindata", "6-K exhibit 99.1, Q4 2021 results", "2022-03-10", CD + "000156459022009444/cd-ex991_6.htm", "locations"),
    Doc("cd_pr_2022q2", "Chindata", "6-K exhibit 99.1, Q2 2022 results", "2022-08-25", CD + "000156459022030085/cd-ex991_6.htm", "locations"),
    Doc("cd_pr_2022q3", "Chindata", "6-K exhibit 99.1, Q3 2022 results", "2022-11-22", CD + "000095017022025569/cd-ex99_1.htm", "locations"),
    Doc("cd_pr_2023q2", "Chindata", "6-K exhibit 99.1, Q2 2023 results", "2023-08-31", CD + "000095017023045611/cd-ex99_1.htm", "locations"),
    Doc("vnet_20f_2019", "VNET", "20-F FY2019", "", VNET + "000110465920042437/a19-24584_120f.htm", "search"),
    Doc("vnet_20f_2020", "VNET", "20-F FY2020", "", VNET + "000110465921056551/vnet-20201231x20f.htm", "search"),
    Doc("vnet_20f_2022", "VNET", "20-F FY2022", "", VNET + "000110465923050330/vnet-20221231x20f.htm", "search"),
    Doc("vnet_20f_2023", "VNET", "20-F FY2023", "", VNET + "000110465924052273/vnet-20231231x20f.htm", "search"),
    Doc("vnet_20f_2024", "VNET", "20-F FY2024", "", VNET + "000141057825000905/vnet-20241231x20f.htm", "search"),
    Doc("gds_20f_2019", "GDS", "20-F FY2019", "", GDS + "000110465920047853/gds-20191231x20f.htm", "search"),
    Doc("gds_20f_2020", "GDS", "20-F FY2020", "", GDS + "000110465921049104/gds-20201231x20f.htm", "search"),
    Doc("gds_20f_2022", "GDS", "20-F FY2022", "", GDS + "000110465923041218/gds-20221231x20f.htm", "search"),
    Doc("gds_20f_2024", "GDS", "20-F FY2024", "", GDS + "000141057825000935/gds-20241231x20f.htm", "search"),
]
DOCS = {d.key: d for d in DOCUMENTS}
SEARCH_KEYS = [d.key for d in DOCUMENTS if d.role in ("search", "tables")]

HUB_TERMS = {
    "Ulanqab": r"Ulanqab|Ulanchabu|Wulanchabu",
    "Zhangbei": r"Zhangbei",
    "Horinger": r"Horinger|Helingeer|Helinge['’]er|Hohhot",
    "Gui'an": r"Gui['’]an\b|\bGuian\b",
    "Zhongwei": r"Zhongwei",
}


# ---------------------------------------------------------------- documents

def html_to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    return re.sub(r"\s+", " ", text).strip()


def normalise_quote(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("’", "'").replace("‘", "'")).strip()


def cached_text(key: str) -> str | None:
    path = CACHE / f"{key}.html"
    return html_to_text(path.read_text(encoding="utf-8", errors="replace")) if path.exists() else None


def signature_date(text: str) -> str:
    signed = re.findall(r"Date:\s*([A-Z][a-z]+ \d{1,2}, \d{4})", text)
    return datetime.strptime(signed[-1], "%B %d, %Y").date().isoformat() if signed else ""


def read_sources() -> dict[str, dict]:
    if not SOURCES.exists():
        return {}
    with SOURCES.open(newline="", encoding="utf-8") as f:
        return {r["key"]: r for r in csv.DictReader(f)}


def fetch(keys: list[str], pause: float) -> int:
    import requests

    CACHE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(exist_ok=True)
    sources = read_sources()
    failures = 0
    for key in keys:
        doc = DOCS[key]
        path = CACHE / f"{key}.html"
        if path.exists() and key in sources:
            continue
        response = None
        for attempt in range(4):
            try:
                r = requests.get(f"https://web.archive.org/web/2026id_/{doc.sec_url}", headers={"User-Agent": USER_AGENT}, timeout=300)
                if r.status_code == 200 and len(r.content) > 1500 and re.search(r"/web/\d{14}id_/", r.url):
                    response = r
                    break
                print(f"{key}: HTTP {r.status_code}, attempt {attempt + 1}", file=sys.stderr)
            except requests.RequestException as err:
                print(f"{key}: {err.__class__.__name__}, attempt {attempt + 1}", file=sys.stderr)
            time.sleep(30 * (attempt + 1))
        if response is None:
            failures += 1
            continue
        data = response.content
        if data[:2] == b"\x1f\x8b":
            data = gzip.decompress(data)
        path.write_bytes(data)
        text = html_to_text(data.decode("utf-8", errors="replace"))
        filed = doc.filed or signature_date(text)
        sources[key] = {"key": key, "company": doc.company, "form": doc.form, "filed": filed, "sec_url": doc.sec_url,
                        "archive_url": response.url, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                        "retrieved_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        print(f"{key}: {len(data):,} bytes from {response.url}", file=sys.stderr)
        write_csv(SOURCES, [sources[k] for k in DOCS if k in sources],
                  ["key", "company", "form", "filed", "sec_url", "archive_url", "sha256", "bytes", "retrieved_utc"])
        time.sleep(pause)
    return failures


# ---------------------------------------------------------------- tables

INTRO = re.compile(r"The following table sets forth details concerning our data centers (in service|under construction) "
                   r"as of ([A-Z][a-z]+ \d{1,2}, \d{4}):")
REGION = r"(?:Greater Beijing Area|Yangtze River Delta Area|Greater Bay Area), (?:mainland )?China|Malaysia|India"
CODE = r"(?:CN|CE|CS|MY|BBY)\d+(?:-[A-Z0-9]+)?"
CELL = r"(?:\d+(?:\.\d+)?%?|—)"
HEADERS = [
    (r"(?:IT )?Capacity in Service \(MW\)", "it_capacity_in_service_mw", "MW"),
    (r"Contracted IT Capacity(?: \(MW\))?", "contracted_it_capacity_mw", "MW"),
    (r"IoI IT Capacity \(MW\)", "ioi_it_capacity_mw", "MW"),
    (r"Utilized IT Capacity ?\(MW\)", "utilized_it_capacity_mw", "MW"),
    (r"Designed IT Capacity \(MW\)", "designed_it_capacity_mw", "MW"),
    (r"Planned Capacity \(MW\)", "planned_capacity_mw", "MW"),
    (r"Contracted Ratio", "contracted_ratio_pct", "%"),
    (r"IoI Ratio", "ioi_ratio_pct", "%"),
    (r"Utilization Ratio", "utilization_ratio_pct", "%"),
]


@dataclass
class Table:
    status: str
    as_of: str
    columns: list[tuple[str, str]]
    rows: list[dict] = field(default_factory=list)
    total: dict = field(default_factory=dict)


def cell(value: str) -> float | None:
    return None if value == "—" else float(value.rstrip("%"))


def parse_tables(text: str) -> list[Table]:
    tables = []
    for m in INTRO.finditer(text):
        window = text[m.end(): m.end() + 8000]
        first_region = re.search(REGION, window)
        if not first_region:
            continue
        header = window[: first_region.start()]
        found = sorted((h.start(), -len(h.group(0)), metric, unit) for pat, metric, unit in HEADERS for h in re.finditer(pat, header))
        columns, end = [], -1
        for start, neg_len, metric, unit in found:
            if start >= end:
                columns.append((metric, unit))
                end = start - neg_len
        n = len(columns)
        body = re.compile(rf"(?P<region>{REGION})|(?P<code>{CODE})(?:\s*\(\d\))?\s+(?P<type>Hyperscale|Wholesale)\s+"
                          rf"(?P<tenure>Leased|Owned)\s+(?P<vals>{CELL}(?:\s+{CELL}){{{n - 1}}})|Total\s+(?P<tvals>{CELL}(?:\s+{CELL}){{{n - 1}}})")
        table = Table("in_service" if m.group(1) == "in service" else "under_construction",
                      datetime.strptime(m.group(2), "%B %d, %Y").date().isoformat(), columns)
        region = None
        for b in body.finditer(window, first_region.start()):
            if b.group("region"):
                region = b.group("region")
            elif b.group("code"):
                values = dict(zip([c[0] for c in columns], map(cell, b.group("vals").split())))
                table.rows.append({"data_center": b.group("code"), "type": b.group("type"), "tenure": b.group("tenure"),
                                   "region": region, "values": values})
            else:
                table.total = dict(zip([c[0] for c in columns], map(cell, b.group("tvals").split())))
                break
        tables.append(table)
    return tables


def check_totals(table: Table) -> list[dict]:
    """Rows are rounded to whole MW or percent, so MW sums may miss the total by up to half a unit per row; ratio columns
    are checked as a capacity-weighted mean, treating a dash as zero."""
    checks = []
    capacity = next(metric for metric, unit in table.columns if unit == "MW")
    for metric, unit in table.columns:
        reported = table.total.get(metric)
        if unit == "MW":
            got = sum(r["values"][metric] or 0 for r in table.rows)
            tolerance = max(1.0, 0.5 * sum(1 for r in table.rows if r["values"][metric] is not None))
        else:
            weight = sum(r["values"][capacity] or 0 for r in table.rows)
            got = sum((r["values"][capacity] or 0) * (r["values"][metric] or 0) for r in table.rows) / weight if weight else 0
            tolerance = 2.0
        ok = reported is None and got == 0 or reported is not None and abs(got - reported) <= tolerance
        checks.append({"as_of": table.as_of, "status": table.status, "metric": metric, "row_sum_or_weighted_mean": round(got, 2),
                       "reported_total": "—" if reported is None else reported, "tolerance": tolerance, "ok": ok})
    return checks


# ---------------------------------------------------------------- locations and disclosure rows

def read_locations() -> dict[str, dict]:
    with LOCATIONS.open(newline="", encoding="utf-8") as f:
        return {r["data_center"]: r for r in csv.DictReader(f)}


def verify_locations(locations: dict[str, dict], texts: dict[str, str]) -> list[str]:
    problems = []
    for code, row in locations.items():
        text = texts.get(row["source_key"])
        if text is None:
            problems.append(f"{code}: {row['source_key']} is not cached; run fetch")
        elif normalise_quote(row["quote"]) not in normalise_quote(text):
            problems.append(f"{code}: quote not found in {row['source_key']}")
    return problems


DEFINITIONS = {
    "it_capacity_in_service_mw": "capacity in service: total capacity available for utilisation (filing definition)",
    "contracted_it_capacity_mw": "contracted: capacity clients are required to pay for (filing definition)",
    "ioi_it_capacity_mw": "indication of interest: capacity under substantial negotiation, not yet contracted (filing definition)",
    "utilized_it_capacity_mw": "utilised: capacity in customer use as Chindata reports it; commercial, not a power measurement",
    "designed_it_capacity_mw": "under construction: designed capacity, not in service",
    "planned_capacity_mw": "under construction: planned capacity, not in service",
    "contracted_ratio_pct": "contracted capacity as a share of {base}",
    "ioi_ratio_pct": "indication-of-interest capacity as a share of {base}",
    "utilization_ratio_pct": "utilised capacity as a share of capacity in service; commercial, not a power measurement",
}


def disclosure_rows(tables_by_doc: dict[str, list[Table]], locations: dict[str, dict], sources: dict[str, dict]) -> list[dict]:
    rows = []
    for key, tables in tables_by_doc.items():
        doc, source = DOCS[key], sources.get(key, {})
        for table in tables:
            base = "capacity in service" if table.status == "in_service" else "planned capacity"
            for r in table.rows:
                if "China" not in (r["region"] or ""):
                    continue
                loc = locations.get(r["data_center"])
                region = r["region"].split(",")[0]
                hub = loc["hub"] if loc else f"{region} (Chindata region; the filings do not give this data centre's city)"
                campus = f"Chindata {r['data_center']}" + (f" ({loc['stated_location']})" if loc else "")
                for metric, unit in table.columns:
                    value = r["values"][metric]
                    if value is None:
                        continue
                    status = "in service" if table.status == "in_service" else "under construction"
                    rows.append({
                        "hub": hub, "campus": campus, "operator": OPERATOR, "metric": metric,
                        "value": f"{value:g}", "unit": unit, "period": table.as_of,
                        "source_type": f"SEC {doc.form} (filed {doc.filed}), table of data centers {status}",
                        "source_url": doc.sec_url,
                        "note": f"{TAG}; {DEFINITIONS[metric].format(base=base)}; {r['type'].lower()}, {r['tenure'].lower()}"
                                + (f"; location: {loc['source_key']}" if loc else "")
                                + (f"; read from {source['archive_url']}" if source.get("archive_url") else ""),
                    })
    return rows


def update_disclosures(new_rows: list[dict]) -> tuple[int, int]:
    raw = DISCLOSURES.read_bytes()
    terminator = "\r\n" if b"\r\n" in raw[:4096] else "\n"  # keep the file's own line endings so diffs stay small
    with DISCLOSURES.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields, existing = reader.fieldnames, list(reader)
    kept = [r for r in existing if not r["note"].startswith(TAG)]
    write_csv(DISCLOSURES, kept + new_rows, fields, terminator)
    return len(existing) - len(kept), len(new_rows)


# ---------------------------------------------------------------- hub-name search

def hub_mentions(key: str, text: str) -> list[dict]:
    out = []
    for hub, pattern in HUB_TERMS.items():
        for m in re.finditer(pattern, text):
            context = text[max(0, m.start() - 250): m.end() + 250]
            figures = re.findall(r"\b\d[\d,.]*\s?(?:MW|megawatts?|sq(?:uare)?\.? ?m(?:eters)?|sqm|cabinets|racks)\b", context)
            out.append({"key": key, "hub": hub, "matched": m.group(0), "offset": m.start(),
                        "figures_nearby": "; ".join(dict.fromkeys(figures)), "context": context})
    return out


# ---------------------------------------------------------------- build

def write_csv(path: Path, rows: list[dict], fields: list[str], terminator: str = "\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator=terminator)
        w.writeheader()
        w.writerows(rows)


def build() -> int:
    sources = read_sources()
    texts = {k: t for k in DOCS if (t := cached_text(k)) is not None}
    missing = [k for k in DOCS if k not in texts]
    if missing:
        print(f"not cached: {', '.join(missing)}; run fetch first", file=sys.stderr)
        return 1
    for key, source in sources.items():
        if not source.get("filed") and key in texts:
            source["filed"] = signature_date(texts[key])
    if sources:
        write_csv(SOURCES, [sources[k] for k in DOCS if k in sources], list(next(iter(sources.values())).keys()))
    locations = read_locations()
    problems = verify_locations(locations, texts)

    tables_by_doc, detail, checks = {}, [], []
    for key in (d.key for d in DOCUMENTS if d.role == "tables"):
        tables_by_doc[key] = parse_tables(texts[key])
        for table in tables_by_doc[key]:
            for c in check_totals(table):
                checks.append({"key": key, **c})
                if not c["ok"]:
                    problems.append(f"{key} {table.as_of} {table.status} {c['metric']}: rows give {c['row_sum_or_weighted_mean']}, total {c['reported_total']}")
            for r in table.rows:
                loc = locations.get(r["data_center"], {})
                for metric, unit in table.columns:
                    v = r["values"][metric]
                    detail.append({"key": key, "filed": DOCS[key].filed, "as_of": table.as_of, "status": table.status,
                                   "region": r["region"], "data_center": r["data_center"], "type": r["type"], "tenure": r["tenure"],
                                   "metric": metric, "value": "" if v is None else f"{v:g}", "unit": unit,
                                   "reported_as": "—" if v is None else "", "stated_location": loc.get("stated_location", ""),
                                   "hub": loc.get("hub", "")})
        if len(tables_by_doc[key]) != 2:
            problems.append(f"{key}: expected 2 tables, parsed {len(tables_by_doc[key])}")
    write_csv(OUT / "chindata_data_centres.csv", detail, list(detail[0].keys()))
    write_csv(OUT / "chindata_table_checks.csv", checks, list(checks[0].keys()))

    mentions = []
    for key in SEARCH_KEYS:
        for m in hub_mentions(key, texts[key]):
            src = sources.get(key, {})
            mentions.append({"company": DOCS[key].company, "form": DOCS[key].form, "filed": src.get("filed", DOCS[key].filed),
                             "sec_url": DOCS[key].sec_url, **{k: v for k, v in m.items() if k != "key"}})
    write_csv(OUT / "edgar_hub_mentions.csv", mentions,
              ["company", "form", "filed", "sec_url", "hub", "matched", "offset", "figures_nearby", "context"])

    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    removed, added = update_disclosures(disclosure_rows(tables_by_doc, locations, sources))
    counts = defaultdict(int)
    for m in mentions:
        counts[(m["company"], m["hub"])] += 1
    print(f"{sum(len(t.rows) for ts in tables_by_doc.values() for t in ts)} table rows parsed; all totals within rounding")
    print(f"disclosures: replaced {removed} {TAG} rows with {added}")
    print(f"hub mentions in {len(SEARCH_KEYS)} documents: " + (", ".join(f"{c} {h} {n}" for (c, h), n in sorted(counts.items())) or "none"))
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--pause", type=float, default=10.0, help="seconds between downloads")
    sub.add_parser("build")
    args = ap.parse_args()
    sys.exit(fetch(list(DOCS), args.pause) if args.command == "fetch" else build())


if __name__ == "__main__":
    main()
