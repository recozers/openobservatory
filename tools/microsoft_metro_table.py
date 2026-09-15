#!/usr/bin/env python
"""Microsoft's FY25 datacenter electricity and water by metro (Table 15 of the 2026 Environmental Data Fact Sheet), RFW-19.

    python tools/microsoft_metro_table.py [--pdf path/to/2026-Microsoft-Environmental-Data-Fact-Sheet-PDF.pdf]

Downloads the fact sheet (or reads a local copy), checks its SHA-256 against the value recorded below, reads page 25 with
pypdf, and parses the 29 rows of Table 15: region, location (metro), country, electricity consumption (MWh), water
withdrawal (ML), share of non-potable water (%), the same withdrawal in Olympic pools, and water replenishment (ML, or "*"
for a priority location without volumetric benefit yet). The pools column, which is withdrawal / 2.5 ML, disambiguates the
optional columns. Writes

  data/microsoft_metro_fy25.csv        the table as published, one row per metro, plus the site ids used here
  data/operator_disclosures.csv        one electricity_mwh row per metro (site_id microsoft_<metro>, year 2025, note carrying
                                       the water figures, the fiscal-year caveat and the attribution decision), replacing any
                                       earlier row with the same site_id, metric, year and source_table

Attribution (METRO_CONTEXT): a metro figure is attributed to an inventory campus only when the metro is effectively one
campus. None of the metros that hold inventory campuses is: Phoenix, San Antonio and Des Moines each hold several Microsoft
campuses, so their rows stay context, upper bounds for Goodyear, SAT14/SAT40 and Project Osmium. Because the metro ids are not
in data/sites.csv, tools/ingest_disclosures.py lists them as "disclosed but not in the inventory" and the site is unchanged.
Fiscal year FY25 runs July 2024 to June 2025; the rows carry year 2025 with the period in the note, never a calendar-year claim.
Boundary (footnotes, p. 26): Microsoft-owned datacenters under Microsoft operational control, excluding commissioning and
locations under 1 % of the owned total; electricity is primary data where available, else estimated from capacity.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = "https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/msc/documents/presentations/CSR/2026-Microsoft-Environmental-Data-Fact-Sheet-PDF.pdf"
SHA256 = "0fd180837df00b3427c3eae484a492224b8f18c381e82a2aed98b04553a197f6"
PAGE = 25  # 1-based page of Table 15; footnotes on page 26
TABLE = "2026 Environmental Data Fact Sheet, Table 15 - FY25 Datacenter water and electricity use by location, p. 25 (footnotes p. 26)"
PERIOD = "Microsoft fiscal year FY25, 1 July 2024 to 30 June 2025 (not a calendar year)"

# (region, location as printed, country as printed, site_id used in data/water_derived_loads.csv and here)
ROWS = [
    ("Asia Pacific", "Auckland", "New Zealand", "microsoft_auckland"),
    ("Asia Pacific", "Busan", "South Korea", "microsoft_busan"),
    ("Asia Pacific", "Jakarta", "Indonesia", "microsoft_jakarta"),
    ("Asia Pacific", "Kuala Lumpur", "Malaysia", "microsoft_kuala_lumpur"),
    ("Asia Pacific", "Melbourne", "Australia", "microsoft_melbourne"),
    ("Asia Pacific", "Singapore", "Singapore", "microsoft_singapore"),
    ("Asia Pacific", "Sydney", "Australia", "microsoft_sydney"),
    ("Asia Pacific", "Taipei", "Taiwan", "microsoft_taipei"),
    ("Europe", "Copenhagen", "Denmark", "microsoft_copenhagen"),
    ("Europe", "Dublin", "Ireland", "microsoft_dublin"),
    ("Europe", "Gävle – Sandviken", "Sweden", "microsoft_gavle_sandviken"),
    ("Europe", "Hollands Kroon", "Netherlands", "microsoft_hollands_kroon"),
    ("Europe", "Madrid", "Spain", "microsoft_madrid"),
    ("Europe", "Malmo", "Sweden", "microsoft_malmo"),
    ("Europe", "Milan", "Italy", "microsoft_milan"),
    ("Europe", "Vienna", "Austria", "microsoft_vienna"),
    ("Europe", "Warsaw", "Poland", "microsoft_warsaw"),
    ("Americas", "Ashburn (VA)", "United States of America", "microsoft_ashburn"),
    ("Americas", "Atlanta (GA)", "United States of America", "microsoft_atlanta"),
    ("Americas", "Boydton (VA)", "United States of America", "microsoft_boydton"),
    ("Americas", "Cheyenne (WY)", "United States of America", "microsoft_cheyenne"),
    ("Americas", "Chicago (IL)", "United States of America", "microsoft_chicago"),
    ("Americas", "Des Moines (IA)", "United States of America", "microsoft_des_moines"),
    ("Americas", "East Wenatchee (WA)", "United States of America", "microsoft_east_wenatchee"),
    ("Americas", "Manassas (VA)", "United States of America", "microsoft_manassas"),
    ("Americas", "Phoenix (AZ)", "United States of America", "microsoft_phoenix"),
    ("Americas", "Queretaro", "Mexico", "microsoft_queretaro"),
    ("Americas", "Quincy (WA)", "United States of America", "microsoft_quincy"),
    ("Americas", "San Antonio (TX)", "United States of America", "microsoft_san_antonio"),
]

# Which inventory campuses sit in each metro, and why the metro figure is or is not attributed to them.
METRO_CONTEXT = {
    "microsoft_phoenix": ("epoch_microsoft_goodyear", "context: the Phoenix metro holds several Microsoft campuses (Goodyear and El Mirage among them), so the row is an upper bound for Goodyear, not its load"),
    "microsoft_san_antonio": ("epoch_microsoft_sat14;epoch_microsoft_sat40", "context: the San Antonio metro holds SAT14, SAT40 and Microsoft's older Westover Hills campus, so the row is an upper bound for either inventory campus, not its load"),
    "microsoft_des_moines": ("epoch_microsoft_project_osmium", "context: the Des Moines metro holds several West Des Moines campuses (Project Osmium is one), so the row is an upper bound for Osmium, not its load"),
    "microsoft_atlanta": ("epoch_microsoft_fairwater_atlanta", "context: Fairwater Atlanta went live in October 2025, after FY25, so this small row is Microsoft's other Atlanta capacity, not Fairwater"),
    "microsoft_chicago": ("", "context: no inventory campus; Fairwater (Mount Pleasant, WI) is 100 km north and was not operating in FY25"),
    "microsoft_boydton": ("", "context: effectively one campus (Microsoft's Boydton site), but no inventory campus yet; a candidate for RFW-18 with sourced coordinates and polygons"),
    "microsoft_cheyenne": ("", "context: no inventory Microsoft campus; the Cheyenne inventory sites are Meta's and the Project Jade generator watch"),
    "microsoft_dublin": ("", "context: no inventory Microsoft campus (Grange Castle is in the inventory only through the NO2 flux work); useful against Ireland's official total in data/regional_dc_load.csv"),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(pdf: Path | None) -> Path:
    if pdf and pdf.exists():
        return pdf
    import requests
    out = ROOT / "data" / "cache" / "2026-Microsoft-Environmental-Data-Fact-Sheet-PDF.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    if not out.exists():
        r = requests.get(URL, headers={"User-Agent": "openobservatory.info research (https://github.com/recozers/openobservatory)"}, timeout=120)
        r.raise_for_status()
        out.write_bytes(r.content)
    return out


def page_text(pdf: Path, page: int) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        sys.exit("pypdf is needed to read the fact sheet: pip install pypdf")
    return PdfReader(str(pdf)).pages[page - 1].extract_text() or ""


def number(tok: str):
    return int(tok.replace(",", ""))


def parse_row(text: str, location: str, country: str) -> dict:
    """The numbers after '<location> <country>' on one line: electricity, water, then optional non-potable %, pools, replenishment."""
    pat = re.escape(location) + r"\s+" + re.escape(country) + r"\s+([\d,–*\s]+?)\s*(?:\n|$)"
    m = re.search(pat, text)
    if not m:
        raise ValueError(f"row not found: {location}, {country}")
    toks = m.group(1).split()
    elec = number(toks[0])
    water = None if toks[1] == "–" else number(toks[1])
    rest = toks[2:]
    non_potable = pools = repl = None
    repl_flag = ""
    if water is None:
        # withdrawal under 1 ML: the pools column is also '–'
        if rest and rest[0] == "–":
            rest = rest[1:]
    else:
        expected = water / 2.5
        idx = next((i for i, t in enumerate(rest) if t not in ("–", "*") and abs(number(t) - expected) <= 1), None)
        if idx is None:
            raise ValueError(f"pools column not found for {location}: {toks}")
        pools = number(rest[idx])
        if idx == 1:
            non_potable = number(rest[0])
        elif idx > 1:
            raise ValueError(f"too many columns before pools for {location}: {toks}")
        rest = rest[idx + 1:]
    if rest:
        if rest[0] == "*":
            repl_flag = "* priority replenishment location, no volumetric benefit yet (expected by FY30)"
        else:
            repl = number(rest[0])
        if len(rest) > 1:
            raise ValueError(f"unexpected trailing columns for {location}: {toks}")
    return dict(electricity_mwh=elec, water_withdrawal_ml=water, non_potable_pct=non_potable, pools=pools,
                replenishment_ml=repl, replenishment_flag=repl_flag)


def parse_table(text: str) -> list[dict]:
    rows = []
    for region, location, country, sid in ROWS:
        r = dict(site_id=sid, region=region, location=location, country=country)
        r.update(parse_row(text, location, country))
        rows.append(r)
    return rows


def write_table(rows: list[dict], path: Path):
    cols = ["site_id", "region", "location", "country", "electricity_mwh", "avg_mw", "water_withdrawal_ml", "non_potable_pct", "pools", "replenishment_ml", "replenishment_flag", "inventory_campuses", "attribution"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            campuses, decision = METRO_CONTEXT.get(r["site_id"], ("", "context: no inventory campus in this metro"))
            w.writerow({**{k: ("" if r.get(k) is None else r.get(k)) for k in cols if k in r}, "avg_mw": round(r["electricity_mwh"] / 8760, 1),
                        "inventory_campuses": campuses, "attribution": decision})


def upsert_disclosures(rows: list[dict], path: Path):
    """Append one row per metro, first dropping any earlier rows this script wrote (they are single lines carrying TABLE).
    Existing rows are kept byte for byte; the file is never re-serialised."""
    with open(path, encoding="utf-8", newline="") as f:   # keep the file's own line endings
        text = f.read()
    lines = text.split("\n")
    eol = "\r\n" if lines[0].endswith("\r") else "\n"
    header = lines[0].rstrip("\r").split(",")
    kept = [ln for ln in lines if not (ln.startswith("microsoft_") and TABLE in ln)]
    while kept and kept[-1] == "":
        kept.pop()
    new = []
    for r in rows:
        campuses, decision = METRO_CONTEXT.get(r["site_id"], ("", "context: no inventory campus in this metro"))
        water = "under 1 ML" if r["water_withdrawal_ml"] is None else f"{r['water_withdrawal_ml']} ML"
        extra = []
        if r["non_potable_pct"] is not None:
            extra.append(f"{r['non_potable_pct']} % non-potable")
        if r["replenishment_ml"] is not None:
            extra.append(f"replenishment {r['replenishment_ml']} ML")
        if r["replenishment_flag"]:
            extra.append("priority replenishment location, no volumetric benefit yet")
        note = (f"{PERIOD}. Metro total for all Microsoft-owned datacenters in the {r['location']} metro ({r['country']}); water withdrawal {water}"
                + ("; " + ", ".join(extra) if extra else "") + f". Average facility load {r['electricity_mwh'] / 8760:.0f} MW over the fiscal year. "
                + (f"Inventory campuses in this metro: {campuses}. " if campuses else "") + decision[0].upper() + decision[1:] + ".")
        rec = dict(site_id=r["site_id"], site_name=f"Microsoft {r['location']} metro ({r['country']})", operator="Microsoft", year="2025",
                   metric="electricity_mwh", value=str(r["electricity_mwh"]), unit="MWh", source_url=URL, source_table=TABLE, note=note)
        new.append(rec)
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=header, lineterminator=eol)
    w.writerows(new)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(kept) + "\n" + buf.getvalue())
    return len(new)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", type=Path, default=None, help="local copy of the fact sheet; downloaded to data/cache/ if absent")
    ap.add_argument("--table-out", default="data/microsoft_metro_fy25.csv")
    ap.add_argument("--disclosures", default="data/operator_disclosures.csv")
    args = ap.parse_args()
    pdf = fetch(args.pdf)
    digest = sha256(pdf)
    if digest != SHA256:
        sys.exit(f"fact sheet SHA-256 {digest} differs from the recorded {SHA256}; check the table before trusting the parse")
    rows = parse_table(page_text(pdf, PAGE))
    write_table(rows, ROOT / args.table_out)
    n = upsert_disclosures(rows, ROOT / args.disclosures)
    total = sum(r["electricity_mwh"] for r in rows)
    print(f"{len(rows)} metros, {total:,} MWh in FY25 ({total / 8760:,.0f} MW average); {n} disclosure rows written")
    for r in rows:
        print(f"  {r['location']:22s} {r['electricity_mwh']:>10,} MWh  {r['electricity_mwh'] / 8760:7.1f} MW  water {r['water_withdrawal_ml'] or '<1':>5} ML")


if __name__ == "__main__":
    main()
