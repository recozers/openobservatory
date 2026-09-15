#!/usr/bin/env python
"""Check every source URL in the data files and look up archived copies of the dead ones (RFW-32).

    python tools/check_links.py [--out results/link_check.csv] [--limit N]

Collects URLs from data/*.csv (every cell) and every .json file under data/ (every string), deduplicates them, and checks
each one once: HEAD, then GET if HEAD is refused, following redirects, with an identified User-Agent and a 20 s timeout.
Politeness: one request at a time per host with at least PAUSE seconds between them, at most WORKERS hosts in parallel, and
robots.txt is read once per host and honoured. Some hosts are never fetched and are reported as skipped instead:
SEC EDGAR (its policy needs a contact email in the User-Agent, not yet agreed, see RFW-07), the Nominatim and Overpass APIs
(usage policies forbid this kind of traffic), and Google tile or image servers that back map annotations rather than sources.

A link is dead when its final status is 400 or higher, or the connection fails twice. For each dead link the Internet
Archive's availability API is asked for the closest snapshot (https://archive.org/wayback/available?url=...), which reads the
index and never submits a capture. Links that already point at web.archive.org are checked like any other and never looked up.

Output: <out> with one row per URL (status, final URL, archive URL and timestamp, the files that use it), and
<out stem>_dead.csv with the dead ones and, after them, the blocked ones (403, 412, 429: a bot wall or rate limit, so
the page may well exist; check by hand). A host whose TLS certificate this client does not trust is retried without
verification so its status is known, and the row says so. Run it by hand before a release or once a month; it makes several hundred
requests and takes a few minutes.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import threading
import time
import urllib.robotparser
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests

ROOT = Path(__file__).resolve().parents[1]
UA = "openobservatory.info link checker (https://github.com/recozers/openobservatory; tools/check_links.py)"
PAUSE = 1.5      # seconds between requests to the same host
WORKERS = 4      # hosts checked in parallel
TIMEOUT = 20
URL_RE = re.compile(r"https?://[^\s\"'<>\[\]]+")
TRAILING = ".,;:!?"
BLOCKED = {403, 412, 429}   # bot walls and rate limits, not evidence that a page is gone

SKIP_HOSTS = {
    "www.sec.gov": "skipped: SEC EDGAR needs a contact email in the User-Agent (RFW-07)",
    "efts.sec.gov": "skipped: SEC EDGAR needs a contact email in the User-Agent (RFW-07)",
    "nominatim.openstreetmap.org": "skipped: Nominatim usage policy",
    "overpass-api.de": "skipped: Overpass usage policy",
    "www.gstatic.com": "skipped: Google static content behind map annotations, not a source",
    "earth.google.com": "skipped: Google Earth viewer link, not a source",
    "mt1.google.com": "skipped: Google tiles",
}


def clean(url: str) -> str:
    url = url.rstrip(TRAILING)
    # a URL pasted inside markdown or brackets can drag a closing bracket along
    while url and url[-1] in ")]}" and url.count(url[-1]) > url.count({")": "(", "]": "[", "}": "{"}[url[-1]]):
        url = url[:-1]
    return url


def urls_in_text(text: str) -> list[str]:
    return [clean(m) for m in URL_RE.findall(text)]


def urls_in_json(obj) -> list[str]:
    out = []
    if isinstance(obj, dict):
        for v in obj.values():
            out += urls_in_json(v)
    elif isinstance(obj, list):
        for v in obj:
            out += urls_in_json(v)
    elif isinstance(obj, str):
        out += urls_in_text(obj)
    return out


def rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(p)


def collect(data_dir: Path) -> dict[str, set[str]]:
    """url -> set of relative file paths that mention it."""
    found = defaultdict(set)
    for p in sorted(data_dir.glob("*.csv")):
        with open(p, newline="", encoding="utf-8", errors="replace") as f:
            for row in csv.reader(f):
                for cell in row:
                    for u in urls_in_text(cell):
                        found[u].add(rel(p))
    for p in sorted(data_dir.rglob("*.json")):
        try:
            obj = json.load(open(p, encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        for u in urls_in_json(obj):
            found[u].add(rel(p))
    return found


class HostGate:
    """One request at a time per host, PAUSE seconds apart, honouring robots.txt."""

    def __init__(self, session):
        self.session = session
        self.locks = defaultdict(threading.Lock)
        self.last = defaultdict(float)
        self.robots = {}
        self.robots_lock = threading.Lock()

    def allowed(self, url: str) -> bool:
        host = urlsplit(url).netloc
        with self.robots_lock:
            rp = self.robots.get(host)
        if rp is None:
            rp = urllib.robotparser.RobotFileParser()
            try:
                r = self.session.get(f"{urlsplit(url).scheme}://{host}/robots.txt", timeout=TIMEOUT)
                rp.parse(r.text.splitlines() if r.status_code == 200 else [])
            except requests.RequestException:
                rp.parse([])
            with self.robots_lock:
                self.robots[host] = rp
        return rp.can_fetch(UA, url)

    def request(self, method: str, url: str, verify: bool = True):
        host = urlsplit(url).netloc
        with self.locks[host]:
            wait = self.last[host] + PAUSE - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            try:
                return self.session.request(method, url, timeout=TIMEOUT, allow_redirects=True, verify=verify)
            finally:
                self.last[host] = time.monotonic()


def check_one(gate: HostGate, url: str) -> dict:
    host = urlsplit(url).netloc
    rec = dict(url=url, status="", final_url="", note="")
    if host in SKIP_HOSTS:
        rec["note"] = SKIP_HOSTS[host]
        return rec
    try:
        if not gate.allowed(url):
            rec["note"] = "skipped: robots.txt disallows"
            return rec
    except Exception as e:  # noqa: BLE001
        rec["note"] = f"robots.txt check failed: {type(e).__name__}"
    err = None
    verify = True
    for attempt in range(3):
        try:
            r = gate.request("HEAD", url, verify)
            if r.status_code >= 400:  # many servers refuse HEAD; a GET settles it
                r = gate.request("GET", url, verify)
            rec.update(status=str(r.status_code), final_url=r.url if r.url != url else "")
            if not verify:
                rec["note"] = "TLS certificate not trusted by this client (common for Chinese government hosts); content not verified"
            elif r.status_code in BLOCKED:
                rec["note"] = f"blocked or rate-limited ({r.status_code}): the page may exist; check by hand"
            return rec
        except requests.exceptions.SSLError:
            if verify:
                verify = False  # the server answered but its certificate chain is not in this client's bundle
                continue
            err = "SSLError"
        except requests.RequestException as e:
            err = f"{type(e).__name__}"
            time.sleep(PAUSE)
    rec.update(status="error", note=err or "")
    return rec


def wayback(session, url: str) -> tuple[str, str]:
    try:
        r = session.get("https://archive.org/wayback/available", params={"url": url}, timeout=TIMEOUT)
        snap = r.json().get("archived_snapshots", {}).get("closest", {})
        if snap.get("available"):
            return snap.get("url", ""), snap.get("timestamp", "")
    except (requests.RequestException, ValueError):
        pass
    return "", ""


def is_dead(rec: dict) -> bool:
    return rec["status"] == "error" or (rec["status"].isdigit() and int(rec["status"]) >= 400 and int(rec["status"]) not in BLOCKED)


def is_blocked(rec: dict) -> bool:
    return rec["status"].isdigit() and int(rec["status"]) in BLOCKED


def run(found: dict[str, set[str]], out: Path, limit: int | None = None, progress=print):
    session = requests.Session()
    session.headers["User-Agent"] = UA
    gate = HostGate(session)
    urls = sorted(found)
    if limit:
        urls = urls[:limit]
    checked_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    # group by host so one worker walks one host at a time
    by_host = defaultdict(list)
    for u in urls:
        by_host[urlsplit(u).netloc].append(u)
    results = {}
    done = 0

    def walk(host_urls):
        nonlocal done
        for u in host_urls:
            results[u] = check_one(gate, u)
            done += 1
            if done % 25 == 0:
                progress(f"  {done}/{len(urls)} checked")

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        list(ex.map(walk, sorted(by_host.values(), key=len, reverse=True)))
    rows = []
    for u in urls:
        rec = results[u]
        rec.update(checked_at=checked_at, used_in=";".join(sorted(found[u])), n_files=len(found[u]), archive_url="", archive_ts="")
        if (is_dead(rec) or is_blocked(rec)) and "web.archive.org" not in urlsplit(u).netloc:
            time.sleep(1.0)
            rec["archive_url"], rec["archive_ts"] = wayback(session, u)
        rows.append(rec)
    cols = ["url", "status", "final_url", "archive_url", "archive_ts", "note", "n_files", "used_in", "checked_at"]
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    dead = [r for r in rows if is_dead(r)]
    blocked = [r for r in rows if is_blocked(r)]
    with open(out.with_name(out.stem + "_dead.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(dead + blocked)
    skipped = [r for r in rows if r["note"].startswith("skipped")]
    summary = dict(urls=len(rows), ok=sum(1 for r in rows if r["status"].isdigit() and int(r["status"]) < 400),
                   dead=len(dead), dead_with_archive=sum(1 for r in dead if r["archive_url"]), blocked=len(blocked),
                   tls_untrusted=sum(1 for r in rows if r["note"].startswith("TLS")), skipped=len(skipped),
                   redirected=sum(1 for r in rows if r["final_url"]))
    return rows, summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--out", default="results/link_check.csv")
    ap.add_argument("--limit", type=int, default=None, help="check only the first N URLs (for a dry run)")
    args = ap.parse_args()
    found = collect(ROOT / args.data)
    print(f"{len(found)} distinct URLs in {len({f for fs in found.values() for f in fs})} files")
    rows, summary = run(found, ROOT / args.out, args.limit)
    print(summary)
    for r in rows:
        if is_dead(r) or is_blocked(r):
            print(f"  {'BLOCKED' if is_blocked(r) else 'DEAD':7s} {r['status']:5s} {r['url']}  archive={r['archive_url'] or 'none'}  in {r['used_in']}")
    print(f"wrote {args.out} and {Path(args.out).with_name(Path(args.out).stem + '_dead.csv')}")


if __name__ == "__main__":
    sys.exit(main())
