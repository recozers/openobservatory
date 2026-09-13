#!/usr/bin/env python
"""Serve site/ locally and screenshot the map, one site panel and the methods
modal with headless Chromium (Playwright).  Used as a render check.

    python tools/screenshot.py --out shots/
"""
import argparse
import http.server
import os
import socketserver
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def serve(directory, port):
    handler = lambda *a, **k: http.server.SimpleHTTPRequestHandler(*a, directory=str(directory), **k)
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="shots")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--site", default="nsa_utah")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    httpd = serve(ROOT / "site", args.port)
    url = f"http://127.0.0.1:{args.port}/index.html"
    with sync_playwright() as p:
        kw = {}
        exe = os.environ.get("PLAYWRIGHT_CHROMIUM", "/opt/pw-browsers/chromium")
        if os.path.exists(exe):
            kw["executable_path"] = exe
        browser = p.chromium.launch(**kw)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2500)
        page.screenshot(path=str(out / "map.png"))
        page.close()
        page = browser.new_page(viewport={"width": 1400, "height": 900})  # fresh page: a same-page hash change would not reload
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url + "#" + args.site, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3500)
        page.screenshot(path=str(out / f"panel_{args.site}.png"))
        page.click("#btn-methods")
        page.wait_for_timeout(500)
        page.screenshot(path=str(out / "methods.png"))
        page.click("#modal-close")
        page.click("#btn-results")
        page.wait_for_timeout(500)
        page.screenshot(path=str(out / "results.png"))
        browser.close()
    httpd.shutdown()
    # basemap tile fetches fail offline; that is expected and not a page bug
    errors = [e for e in errors if "tile.openstreetmap" not in e and "ERR_TUNNEL_CONNECTION_FAILED" not in e and "Failed to fetch" not in e and "favicon" not in e]
    print("screenshots in", out)
    print("console errors (excluding offline tile fetches):", errors if errors else "none")


if __name__ == "__main__":
    main()
