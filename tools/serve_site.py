"""Serve the static site locally with caching disabled, so a rebuild shows up on the next reload.

    python tools/serve_site.py            # http://localhost:8000
    python tools/serve_site.py --port 8765

Python's plain http.server sends Last-Modified without Cache-Control, which lets browsers reuse old JSON and JS after a
rebuild. This sends Cache-Control: no-store on every response.
"""
from __future__ import annotations

import argparse
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SITE = Path(__file__).resolve().parents[1] / "site"


class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, max-age=0")
        super().end_headers()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--bind", default="127.0.0.1")
    args = ap.parse_args()
    handler = functools.partial(NoCacheHandler, directory=str(SITE))
    print(f"serving {SITE} at http://localhost:{args.port} (no-store)", flush=True)
    ThreadingHTTPServer((args.bind, args.port), handler).serve_forever()


if __name__ == "__main__":
    main()
