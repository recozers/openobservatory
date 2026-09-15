"""Count the tokens coding agents used, from their local session logs (token leaderboard, docs/token_accounting.md).

    python tools/agent_token_usage.py claude SESSION.jsonl [SUBAGENT.jsonl ...] --until ISO
        [--window NAME=START..END ...]
    python tools/agent_token_usage.py codex ROLLOUT.jsonl

Claude Code writes one transcript line per content block, each repeating its response's usage, so responses are
deduplicated by message id, keeping the largest value of each field. A response's tokens are input, cache writes, cache
reads and output. With --window, a response with any line inside a window is counted in that window instead of the
build, so no response lands in two totals. Responses with any line at or after --until are left out.

Codex writes a token_usage_record for every model response; their sum equals the thread total it records, and total_tokens
is input (cached input included) plus output (reasoning included). The logs are private and stay on the machine they
were written on, so these counts can be reproduced only there.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

CLAUDE_FIELDS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")
CODEX_FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens", "total_tokens")


def lines(path: Path):
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def claude_usage(paths: list[Path], until: str, windows: dict[str, tuple[str, str]]) -> dict:
    responses: dict[tuple, dict] = {}
    for path in paths:
        for e in lines(path):
            if e.get("type") != "assistant":
                continue
            m = e.get("message") or {}
            usage = m.get("usage") or {}
            key = (path.name, m.get("id") or e.get("requestId") or e.get("uuid"))
            r = responses.setdefault(key, {"model": m.get("model"), "times": [], **{f: 0 for f in CLAUDE_FIELDS}})
            r["times"].append(e.get("timestamp") or "")
            for f in CLAUDE_FIELDS:
                r[f] = max(r[f], int(usage.get(f) or 0))
    groups: dict[str, dict] = defaultdict(lambda: {"responses": 0, "first": None, "last": None, **{f: 0 for f in CLAUDE_FIELDS}})
    for r in responses.values():
        if max(r["times"]) >= until:
            group = "after_until"
        else:
            group = next((name for name, (lo, hi) in windows.items() if any(lo <= t <= hi for t in r["times"])), f"build {r['model']}")
        g = groups[group]
        g["responses"] += 1
        g["first"] = min(filter(None, [g["first"], min(r["times"])]))
        g["last"] = max(filter(None, [g["last"], max(r["times"])]))
        for f in CLAUDE_FIELDS:
            g[f] += r[f]
    for g in groups.values():
        g["total"] = sum(g[f] for f in CLAUDE_FIELDS)
    return dict(groups)


def codex_usage(path: Path) -> dict:
    per_response, thread, models, first, last = {}, None, set(), None, None
    for e in lines(path):
        p = e.get("payload") or {}
        if e.get("type") == "turn_context" and p.get("model"):
            models.add(p["model"])
        if e.get("type") == "token_usage_record":
            per_response[p.get("response_id")] = p.get("usage") or {}
            thread = p.get("thread_token_usage") or thread
            first = first or e.get("timestamp")
            last = e.get("timestamp")
    summed = {f: sum(int(u.get(f) or 0) for u in per_response.values()) for f in CODEX_FIELDS}
    return {"responses": len(per_response), "models": sorted(models), "first": first, "last": last, **summed,
            "matches_thread_total": bool(thread) and all(summed[f] == int(thread.get(f) or 0) for f in CODEX_FIELDS)}


def window(text: str) -> tuple[str, tuple[str, str]]:
    name, span = text.split("=", 1)
    start, end = span.split("..", 1)
    return name, (start, end)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="agent", required=True)
    c = sub.add_parser("claude")
    c.add_argument("logs", nargs="+", type=Path)
    c.add_argument("--until", required=True)
    c.add_argument("--window", action="append", default=[], type=window)
    x = sub.add_parser("codex")
    x.add_argument("rollout", type=Path)
    args = ap.parse_args()
    result = claude_usage(args.logs, args.until, dict(args.window)) if args.agent == "claude" else codex_usage(args.rollout)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
