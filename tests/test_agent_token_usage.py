"""tools/agent_token_usage.py counts each model response once and in exactly one group."""
import json
import tempfile
import unittest
from pathlib import Path

from tools import agent_token_usage as atu


def claude_line(msg_id, ts, model="claude-x", inp=0, cw=0, cr=0, out=0):
    return {"type": "assistant", "timestamp": ts, "message": {"id": msg_id, "model": model, "usage": {
        "input_tokens": inp, "cache_creation_input_tokens": cw, "cache_read_input_tokens": cr, "output_tokens": out}}}


def codex_records(specs):
    """specs: [(response_id, timestamp, total_tokens)]; thread totals are the running sums, as Codex writes them."""
    running = {f: 0 for f in atu.CODEX_FIELDS}
    rows = []
    for resp, ts, total in specs:
        usage = {"input_tokens": total - 10, "cached_input_tokens": total - 20, "output_tokens": 10, "reasoning_output_tokens": 2, "total_tokens": total}
        running = {f: running[f] + usage[f] for f in atu.CODEX_FIELDS}
        rows.append({"type": "token_usage_record", "timestamp": ts, "payload": {"response_id": resp, "usage": usage, "thread_token_usage": dict(running)}})
    return rows


class ClaudeUsage(unittest.TestCase):
    def write(self, rows):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
        tmp.write("\n".join(json.dumps(r) for r in rows) + "\nnot json\n")
        tmp.close()
        self.addCleanup(Path(tmp.name).unlink)
        return Path(tmp.name)

    def test_repeated_lines_count_once_with_final_usage(self):
        log = self.write([
            claude_line("m1", "2026-09-20T10:00:00Z", inp=5, cw=100, cr=1000, out=3),
            claude_line("m1", "2026-09-20T10:00:01Z", inp=5, cw=100, cr=1000, out=40),
            {"type": "user", "timestamp": "2026-09-20T10:00:02Z", "message": {"content": "hi"}},
        ])
        groups = atu.claude_usage([log])
        self.assertEqual(list(groups), ["counted claude-x"])
        g = groups["counted claude-x"]
        self.assertEqual((g["responses"], g["output_tokens"], g["total"]), (1, 40, 1145))

    def test_a_response_touching_a_window_belongs_to_that_window_only(self):
        log = self.write([
            claude_line("m1", "2026-09-20T09:59:59Z", cr=10),
            claude_line("m1", "2026-09-20T10:00:05Z", cr=10, out=1),
            claude_line("m2", "2026-09-20T11:00:00Z", cr=20),
            claude_line("m3", "2026-09-20T12:30:00Z", cr=40),
        ])
        groups = atu.claude_usage([log], until="2026-09-20T12:00:00Z", windows={"unrelated": ("2026-09-20T10:00:00Z", "2026-09-20T10:30:00Z")})
        self.assertEqual(groups["unrelated"]["total"], 11)
        self.assertEqual(groups["counted claude-x"]["total"], 20)
        self.assertEqual(groups["after until"]["total"], 40)
        self.assertEqual(sum(g["responses"] for g in groups.values()), 3)

    def test_subagent_logs_with_the_same_message_ids_are_kept_apart(self):
        a = self.write([claude_line("m1", "2026-09-20T10:00:00Z", cr=10)])
        b = self.write([claude_line("m1", "2026-09-20T10:00:00Z", cr=7)])
        self.assertEqual(atu.claude_usage([a, b])["counted claude-x"]["total"], 17)


class CodexUsage(unittest.TestCase):
    def write(self, rows):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
        tmp.write("\n".join(json.dumps(r) for r in rows) + "\n")
        tmp.close()
        self.addCleanup(Path(tmp.name).unlink)
        return Path(tmp.name)

    def test_records_sum_to_the_thread_total_and_split_by_window(self):
        records = codex_records([("r1", "2026-09-20T09:10:00Z", 100), ("r2", "2026-09-20T10:10:00Z", 50), ("r3", "2026-09-20T11:10:00Z", 25)])
        counter = {"type": "event_msg", "timestamp": "2026-09-20T10:10:01Z", "payload": {"type": "token_count", "info": {"total_token_usage": {"total_tokens": 120}}}}
        log = self.write([{"type": "turn_context", "timestamp": "2026-09-20T09:00:00Z", "payload": {"model": "gpt-x"}}, *records[:2], counter, records[2]])
        out = atu.codex_usage(log, windows={"unrelated": ("2026-09-20T10:00:00Z", "2026-09-20T10:30:00Z")})
        self.assertTrue(out["matches_thread_total"])
        self.assertEqual(out["groups"]["counted gpt-x"]["total_tokens"], 125)
        self.assertEqual(out["groups"]["unrelated"]["total_tokens"], 50)
        self.assertEqual(atu.codex_usage(log, until="2026-09-20T11:00:00Z")["groups"]["after until"]["total_tokens"], 25)

    def test_a_missing_response_shows_up_as_a_thread_total_mismatch(self):
        records = codex_records([("r1", "2026-09-20T09:10:00Z", 100), ("r2", "2026-09-20T10:10:00Z", 50)])
        log = self.write([{"type": "turn_context", "timestamp": "2026-09-20T09:00:00Z", "payload": {"model": "gpt-x"}}, records[1]])
        self.assertFalse(atu.codex_usage(log)["matches_thread_total"])

    def test_window_argument_parses(self):
        self.assertEqual(atu.window("lunch=2026-09-20T12:00:00Z..2026-09-20T13:00:00Z"),
                         ("lunch", ("2026-09-20T12:00:00Z", "2026-09-20T13:00:00Z")))


if __name__ == "__main__":
    unittest.main()
