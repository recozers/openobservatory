# Token accounting for the leaderboard

The [token leaderboard](https://openobservatory.info/leaderboard.html) has two kinds of row. Donated sessions report their
own token counts in a merged pull request's Donation section, and nobody can verify those. The rows labelled "Building
Open Observatory" are the tokens Stuart's own agent sessions used to build the project. They were counted on 15 September
2026 from the agents' local session logs with `tools/agent_token_usage.py`. The logs are private and stay on Stuart's
machine, so only the method and the results are published here.

## Results

| Row | Agent and model | Model responses | Period (UTC) | Tokens |
|---|---|---|---|---|
| Building Open Observatory | Claude Code with Claude Fable 5.1 | 593 | 12 Sep 18:56 to 13 Sep 23:17 | 253,162,894 |
| Building Open Observatory | Codex with gpt-6-astra | 558 | 13 Sep 13:14 to 14 Sep 11:53 | 81,551,994 |
| Building Open Observatory | Claude Code with Claude Opus 5 | 279 | 14 Sep 10:46 to 15 Sep 12:37 | 152,579,428 |
| RFW-07, pull request 15 | Claude Code with Claude Opus 5 | 48 | 14 Sep 15:16 to 16:10 | 18,895,938 |
| **All four** | | **1,478** | | **506,190,254** |

Most of these tokens are cache reads. Each model call re-reads the conversation so far, so a long session re-reads the same
context many times.

| Agent | Uncached input | Cache writes | Cache reads | Output |
|---|---|---|---|---|
| Claude Code, build, both models | 14,420 | 5,821,530 | 398,173,603 | 1,732,769 |
| Claude Code, RFW-07 | 96 | 194,709 | 18,578,006 | 123,127 |
| Codex, build | 2,856,260 | 0 recorded | 78,356,096 | 339,638, of which 80,078 reasoning |

## What was counted

- **Claude Code:** the one session that built the project in this repository's parent folder, plus its four subagents.
  Claude Code writes a transcript line per content block, each repeating its response's usage, so responses are deduplicated
  by message id. A response's tokens are uncached input, cache writes, cache reads and output.
- **Codex:** the one Codex session that worked in the same folder, as "Astra", on the briefs in `docs/ASTRA_TODO.md` and
  `docs/PHASE2_TODO.md`. Codex records the usage of every model response; those records add up exactly to the session's
  thread total, which is used here. The running counter Codex shows during a session ends lower, at 80,035,718; it falls
  behind the per-response records 47 minutes into the session and stays behind.

## What was left out

- **RFW-07.** The claim and the work on it, 48 responses and 18,895,938 tokens, are a separate row through pull request 15.
  Any response with a transcript line inside those windows counts there and not in the build, so no response is in both.
- **Unrelated work.** Adding a node to Stuart's personal website used 14 responses and 7,619,108 tokens in the same session.
- **Later work.** Responses from 15 September 12:39:59 UTC on, when these totals were requested, are not counted.
- **Not in the logs.** The first thermal prototype was built in a Claude Code cloud session whose usage is not in these local
  logs, and any calls an agent makes without writing them to its transcript are not counted.

## Reproducing the counts

On the machine with the logs:

```sh
L=~/.claude/projects/-Users-stuartbladon-Documents-Duke-Duke2025-Meridian
python tools/agent_token_usage.py claude "$L"/c86b0055-6aad-4703-9bda-9b4946f14ec7.jsonl "$L"/c86b0055-6aad-4703-9bda-9b4946f14ec7/subagents/*.jsonl \
  --until 2026-09-15T12:39:59.836Z \
  --window rfw07_claim=2026-09-14T15:15:15.518Z..2026-09-14T15:23:25.684Z \
  --window rfw07_work=2026-09-14T15:33:34.393Z..2026-09-14T16:10:18.562Z \
  --window personal_website=2026-09-15T12:13:23.043Z..2026-09-15T12:21:13.515Z
python tools/agent_token_usage.py codex ~/.codex/sessions/2026/09/13/rollout-2026-09-13T14-14-37-01a09ae7-ca82-7672-9e42-711591290c92.jsonl
```

The rows are in `data/donations.csv`. After editing them, run `node .github/scripts/donations.cjs rebuild`.
