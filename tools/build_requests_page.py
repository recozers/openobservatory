"""Render REQUESTS_FOR_WORK.md (the source of truth) to site/requests.html for the public site.

    python tools/build_requests_page.py            # writes site/requests.html
    python tools/build_requests_page.py --check    # exit 1 if site/requests.html is out of date

Edit the Markdown file, never the HTML. The converter handles the subset the file uses: headings (anchors match GitHub's, so
the same #links work on GitHub and on the site), paragraphs, bullet and numbered lists with indented continuation lines,
pipe tables, fenced code blocks, links, bold and inline code. All text is HTML-escaped.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "REQUESTS_FOR_WORK.md"
TARGET = ROOT / "site" / "requests.html"
REPO = "https://github.com/recozers/openobservatory"


def slug(text: str) -> str:
    """GitHub's heading anchor: lowercase, drop characters that are not letters, digits, spaces, hyphens or underscores,
    then turn spaces into hyphens."""
    text = re.sub(r"[^\w\- ]", "", text.strip().lower(), flags=re.UNICODE)
    return text.replace(" ", "-")


def inline(text: str) -> str:
    codes: list[str] = []

    def keep_code(m):
        codes.append(f"<code>{html.escape(m.group(1))}</code>")
        return f"\x00{len(codes) - 1}\x00"

    text = re.sub(r"`([^`]+)`", keep_code, text)
    text = html.escape(text, quote=False)

    def link(m):
        label, url = m.group(1), html.unescape(m.group(2))  # the text was escaped above; escape the URL once, not twice
        if url.startswith(("http://", "https://")):
            return f'<a href="{html.escape(url)}" target="_blank" rel="noopener">{label}</a>'
        if url.startswith("#"):
            return f'<a href="{html.escape(url)}">{label}</a>'
        return f'<a href="{REPO}/blob/main/{html.escape(url)}" target="_blank" rel="noopener">{label}</a>'

    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], text)


def render_markdown(md: str) -> str:
    lines = md.split("\n")
    out: list[str] = []
    para: list[str] = []
    i = 0

    def flush_para():
        if para:
            out.append(f"<p>{inline(' '.join(s.strip() for s in para))}</p>")
            para.clear()

    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            flush_para()
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            out.append(f"<pre><code>{html.escape(chr(10).join(lines[i + 1:j]))}</code></pre>")
            i = j + 1
            continue
        m = re.match(r"^(#{1,4}) (.+)$", line)
        if m:
            flush_para()
            level, title = len(m.group(1)), m.group(2).strip()
            out.append(f'<h{level} id="{slug(title)}">{inline(title)}</h{level}>')
            i += 1
            continue
        if line.startswith("|"):
            flush_para()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            head, body = rows[0], [r for r in rows[1:] if not all(re.fullmatch(r":?-{3,}:?", c) for c in r)]
            out.append('<div class="table-wrap"><table><thead><tr>' + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>" +
                       "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body) + "</tbody></table></div>")
            continue
        m = re.match(r"^(- |\d+\. )(.*)$", line)
        if m:
            flush_para()
            tag = "ul" if m.group(1) == "- " else "ol"
            items: list[str] = []
            while i < len(lines):
                m2 = re.match(r"^(- |\d+\. )(.*)$", lines[i])
                if m2 and (("ul" if m2.group(1) == "- " else "ol") == tag):
                    items.append(m2.group(2))
                elif lines[i].startswith("  ") and lines[i].strip() and items:
                    items[-1] += " " + lines[i].strip()
                else:
                    break
                i += 1
            out.append(f"<{tag}>" + "".join(f"<li>{inline(it)}</li>" for it in items) + f"</{tag}>")
            continue
        if not line.strip():
            flush_para()
        else:
            para.append(line)
        i += 1
    flush_para()
    return "\n".join(out)


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Requests for work · Open Observatory</title>
<link rel="stylesheet" href="style.css">
<style>
  .wrap {{ max-width: 900px; margin: 0 auto; padding: 18px 16px 48px; }}
  .nav {{ font-size: 13px; margin: 0 0 12px; }}
  .doc {{ background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 8px 24px 24px; line-height: 1.55; font-size: 14.5px; }}
  .doc h1 {{ font-size: 26px; margin: 16px 0 8px; }}
  .doc h2 {{ font-size: 19px; margin: 28px 0 8px; padding-top: 12px; border-top: 1px solid var(--line); }}
  .doc h3 {{ font-size: 16px; margin: 22px 0 6px; color: var(--muted); text-transform: uppercase; letter-spacing: .03em; }}
  .doc h4 {{ font-size: 15.5px; margin: 20px 0 4px; }}
  .doc h2, .doc h3, .doc h4 {{ scroll-margin-top: 12px; }}
  .doc ul, .doc ol {{ padding-left: 22px; }}
  .doc li {{ margin: 4px 0; }}
  .doc code {{ font-size: 12.5px; background: #f1efe9; padding: 1px 4px; border-radius: 4px; overflow-wrap: anywhere; }}
  .doc pre {{ background: #f6f5f1; border: 1px solid var(--line); border-radius: 8px; padding: 12px; overflow-x: auto; }}
  .doc pre code {{ background: none; padding: 0; font-size: 12.5px; white-space: pre; }}
  .table-wrap {{ overflow-x: auto; }}
  .doc table {{ border-collapse: collapse; width: 100%; font-size: 13.5px; }}
  .doc th, .doc td {{ text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--line); vertical-align: top; }}
  .doc th {{ font-weight: 650; }}
  .doc td:first-child {{ white-space: nowrap; }}
  .source {{ font-size: 12.5px; color: var(--muted); margin-top: 14px; }}
  .claims-note {{ font-size: 13px; color: var(--muted); margin: 0 0 10px; }}
  .claim-badge {{ display: inline-block; font-size: 12px; font-weight: 600; letter-spacing: 0; text-transform: none; padding: 1px 7px;
    border-radius: 10px; background: #e3f1e6; color: #1b6b34; text-decoration: none; white-space: nowrap; vertical-align: middle; }}
</style>
</head>
<body>
<div class="wrap">
  <p class="nav"><a href="index.html">Map</a> · <a href="list.html">List</a> · <a href="map.html">Quarterly detail</a> · <a href="findings.html">Findings</a> · <a href="leaderboard.html">Leaderboard</a> · <a href="{repo}">Code</a></p>
  <p id="live-claims" class="claims-note" hidden></p>
  <div class="doc">
{body}
  </div>
  <p class="source">This page is generated from <a href="{repo}/blob/main/REQUESTS_FOR_WORK.md">REQUESTS_FOR_WORK.md</a>. Propose changes to that file in a pull request.</p>
</div>
<script src="claims.js"></script>
</body>
</html>
"""


def build() -> str:
    return TEMPLATE.format(body=render_markdown(SOURCE.read_text(encoding="utf-8")), repo=REPO)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    page = build()
    if args.check:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != page:
            sys.exit("site/requests.html is out of date: run python tools/build_requests_page.py")
        print("site/requests.html is current")
        return
    TARGET.write_text(page, encoding="utf-8")
    print(f"wrote {TARGET.relative_to(ROOT)}", file=sys.stderr)


if __name__ == "__main__":
    main()
