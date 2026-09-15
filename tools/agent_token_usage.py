"""Count the tokens a coding agent used, from its local session logs, for the token leaderboard.

    python tools/agent_token_usage.py claude SESSION.jsonl [SUBAGENT.jsonl ...] [--until ISO] [--window NAME=START..END ...]
    python tools/agent_token_usage.py codex ROLLOUT.jsonl [--until ISO] [--window NAME=START..END ...]

Claude Code keeps sessions in ~/.claude/projects/<folder>/<session>.jsonl, with subagents in <session>/subagents/. Codex
keeps them in ~/.codex/sessions/<year>/<month>/<day>/rollout-<id>.jsonl. Times are UTC, as the logs write them.

Every model response is placed in one group. A response with any log line at or after --until is "after until". A response
with any line inside a --window is reported under that window's name. Everything else is "counted <model>". Report the
"counted" groups, and pass windows for unrelated work in the same session so it stays out.

Claude Code writes one transcript line per content block, each repeating the response's usage, so responses are
deduplicated by message id, keeping the largest value of each field. Tokens are uncached input, cache writes, cache reads
and output. Codex writes a token_usage_record per response; its total_tokens is input, cached input included, plus output,
reasoning included. Those records add up to the thread total Codex stores, which can be higher than the running counter
it shows on screen. `matches_thread_total` reports that check over the whole session.

With --pricing data/api_pricing.csv each group also gets `usd`: what its responses would cost at API list prices. Claude
cache writes are priced at the 5-minute or 1-hour rate as the log records them, and a response in fast mode at twice the
rates. A Codex response with more than 272K input tokens is priced at the long-context rates. Responses from a model the
pricing file does not list are counted in `unpriced_responses` and add nothing to `usd`.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

CLAUDE_FIELDS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")
CODEX_FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens", "total_tokens")
NO_CUTOFF = "9999"
LONG_CONTEXT_INPUT = 272_000  # OpenAI: longer prompts are priced at the long-context rates for the whole request


def load_pricing(path: Path | None) -> dict[tuple[str, str], dict]:
    if not path:
        return {}
    with path.open(newline="", encoding="utf-8") as f:
        return {(r["model_id"], r["tier"]): {k: float(v) for k, v in r.items() if k.endswith("_per_mtok")} for r in csv.DictReader(f)}


def claude_cost(r: dict, pricing: dict) -> float | None:
    rate = pricing.get((r["model"], "standard"))
    if not rate:
        return None
    scale = 2.0 if r.get("speed") == "fast" else 1.0
    return scale * (r["input_tokens"] * rate["input_per_mtok"] + r["cache_write_5m"] * rate["cache_write_5m_per_mtok"]
                    + r["cache_write_1h"] * rate["cache_write_1h_per_mtok"] + r["cache_read_input_tokens"] * rate["cache_read_per_mtok"]
                    + r["output_tokens"] * rate["output_per_mtok"]) / 1e6


def codex_cost(r: dict, pricing: dict) -> float | None:
    tier = "long_context" if r["input_tokens"] > LONG_CONTEXT_INPUT else "standard"
    rate = pricing.get((r["model"], tier))
    if not rate:
        return None
    uncached = max(0, r["input_tokens"] - r["cached_input_tokens"] - r["cache_write_input_tokens"])
    return (uncached * rate["input_per_mtok"] + r["cached_input_tokens"] * rate["cache_read_per_mtok"]
            + r["cache_write_input_tokens"] * rate["cache_write_5m_per_mtok"] + r["output_tokens"] * rate["output_per_mtok"]) / 1e6


def lines(path: Path):
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def group_for(times: list[str], model: str | None, until: str, windows: dict[str, tuple[str, str]]) -> str:
    if max(times) >= until:
        return "after until"
    inside = next((name for name, (lo, hi) in windows.items() if any(lo <= t <= hi for t in times)), None)
    return inside or f"counted {model}"


def summarise(responses: list[dict], fields: tuple[str, ...], until: str, windows: dict[str, tuple[str, str]], cost=None) -> dict:
    groups: dict[str, dict] = defaultdict(lambda: {"responses": 0, "first": None, "last": None, **{f: 0 for f in fields}})
    for r in responses:
        g = groups[group_for(r["times"], r["model"], until, windows)]
        if cost:
            usd = cost(r)
            if usd is None:
                g["unpriced_responses"] = g.get("unpriced_responses", 0) + 1
            else:
                g["usd"] = g.get("usd", 0.0) + usd
        g["responses"] += 1
        g["first"] = min(filter(None, [g["first"], min(r["times"])]))
        g["last"] = max(filter(None, [g["last"], max(r["times"])]))
        for f in fields:
            g[f] += r[f]
    return dict(groups)


def claude_usage(paths: list[Path], until: str = NO_CUTOFF, windows: dict[str, tuple[str, str]] | None = None,
                 pricing: dict | None = None) -> dict:
    responses: dict[tuple, dict] = {}
    for path in paths:
        for e in lines(path):
            if e.get("type") != "assistant":
                continue
            m = e.get("message") or {}
            usage = m.get("usage") or {}
            key = (str(path), m.get("id") or e.get("requestId") or e.get("uuid"))
            r = responses.setdefault(key, {"model": m.get("model"), "times": [], "speed": None, "cache_write_5m": 0, "cache_write_1h": 0,
                                           **{f: 0 for f in CLAUDE_FIELDS}})
            r["times"].append(e.get("timestamp") or "")
            r["speed"] = usage.get("speed") or r["speed"]
            for f in CLAUDE_FIELDS:
                r[f] = max(r[f], int(usage.get(f) or 0))
            split = usage.get("cache_creation") or {}
            r["cache_write_1h"] = max(r["cache_write_1h"], int(split.get("ephemeral_1h_input_tokens") or 0))
            # A write without a recorded split is priced at the API's default five-minute lifetime.
            r["cache_write_5m"] = max(r["cache_write_5m"], int(split.get("ephemeral_5m_input_tokens") or 0)
                                      if split else int(usage.get("cache_creation_input_tokens") or 0))
    cost = (lambda r: claude_cost(r, pricing)) if pricing else None
    groups = summarise(list(responses.values()), CLAUDE_FIELDS, until, windows or {}, cost)
    for g in groups.values():
        g["total"] = sum(g[f] for f in CLAUDE_FIELDS)
        if "usd" in g:
            g["usd"] = round(g["usd"], 4)
    return groups


def codex_usage(path: Path, until: str = NO_CUTOFF, windows: dict[str, tuple[str, str]] | None = None,
                pricing: dict | None = None) -> dict:
    per_response, thread, model = {}, None, None
    for e in lines(path):
        p = e.get("payload") or {}
        if e.get("type") == "turn_context" and p.get("model"):
            model = p["model"]
        if e.get("type") == "token_usage_record":
            u = p.get("usage") or {}
            per_response[p.get("response_id")] = {"model": model, "times": [e.get("timestamp") or ""],
                                                  "cache_write_input_tokens": int(u.get("cache_write_input_tokens") or 0),
                                                  **{f: int(u.get(f) or 0) for f in CODEX_FIELDS}}
            thread = p.get("thread_token_usage") or thread
    cost = (lambda r: codex_cost(r, pricing)) if pricing else None
    groups = summarise(list(per_response.values()), CODEX_FIELDS, until, windows or {}, cost)
    for g in groups.values():
        if "usd" in g:
            g["usd"] = round(g["usd"], 4)
    summed = {f: sum(r[f] for r in per_response.values()) for f in CODEX_FIELDS}
    return {"groups": groups, "matches_thread_total": bool(thread) and all(summed[f] == int(thread.get(f) or 0) for f in CODEX_FIELDS)}


def window(text: str) -> tuple[str, tuple[str, str]]:
    name, span = text.split("=", 1)
    start, end = span.split("..", 1)
    return name, (start, end)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="agent", required=True)
    for name in ("claude", "codex"):
        s = sub.add_parser(name)
        s.add_argument("logs", nargs="+" if name == "claude" else 1, type=Path)
        s.add_argument("--until", default=NO_CUTOFF, help="leave out responses from this UTC time on")
        s.add_argument("--window", action="append", default=[], type=window, help="NAME=START..END, reported separately")
        s.add_argument("--pricing", type=Path, help="data/api_pricing.csv, to add each group's cost at API list prices")
    args = ap.parse_args()
    windows, pricing = dict(args.window), load_pricing(args.pricing)
    result = (claude_usage(args.logs, args.until, windows, pricing) if args.agent == "claude"
              else codex_usage(args.logs[0], args.until, windows, pricing))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
