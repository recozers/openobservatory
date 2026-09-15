# Contributing to Open Observatory

Use Python 3.11 and a virtual environment. Install `requirements.txt`; copy `.env.example` to `.env` only for live data extraction. Never commit credentials, `.env`, `secrets/`, or Earth Engine caches.

## Add a site

1. Add a stable `site_id` to `data/sites.csv`, coordinates with their quality, operator, country, source URL and explanatory notes. Use tier **U** and leave capacity blank when no attributable number exists. A hub centroid is not a campus.
2. Add `data/polygons/<site_id>.geojson`. Each hall needs a unique `name`, `ptype: hall`, `confidence` and `digitised_from`; retain its source URL and state any geometry repairs. Do not infer that every large industrial roof is a data hall. Planned footprints require independent dating and must not be labelled existing roofs after a non-detection.
3. Add dated, sourced rows to `data/capacity_timeline.csv`. State the basis and units. A1 means regulatory filing or measurement; A2 means a sourced company/utility statement (Epoch estimates are explicitly qualified); B is imagery inference; U is unknown. Facility supply, IT capacity, annual consumption and actual operating load are different quantities. Never turn kVA/MVA into IT MW, sum overlapping facility and IT estimates, or treat a forecast as an observed load.
4. With Earth Engine configured, extract roof evidence using `tools/s2_roof_timeline.py`. Run one site per process, cache results under `data/cache/`, and use `caffeinate -i` on macOS for long jobs. Preserve negative results and unresolved dates. The Epoch importer and its validator are described in README.
5. Rebuild and inspect the public page:

```sh
export OBS_FILE=data/observations_all.csv
export REJ_FILE=data/rejections_all.csv
export RESULTS_DIR=results_gee
python build_site.py
python build_timeline_data.py
python build_status.py
python -m unittest discover -s tests -v
python tools/serve_site.py   # http://localhost:8000, caching disabled
```

Open the changed site at desktop and narrow phone widths. Check source links, unknowns, date bounds, and that a roof-only estimate has no midpoint. Run `python tools/validate_epoch.py` for inventory changes. Use `python tools/refresh.py --dry-run` to validate saved evidence without Earth Engine.

## Donated agent sessions

Open work is listed in `REQUESTS_FOR_WORK.md` and at https://openobservatory.info/requests.html, which marks claimed items
live from open pull requests.

1. **Check.** Pick an open item and search open pull requests for its ID.
2. **Claim.** Fork the repository and open a draft pull request straight away. An empty commit is enough to open it:

   ```sh
   git checkout -b rfw/07-short-name
   git commit --allow-empty -m "Claim RFW-07"
   git push -u origin rfw/07-short-name
   ```

   Title the pull request `[RFW-07] Short title`. Theories use `[T-NN]` and the preparation of a paid request `[PAID-NN]`.
   Fill in the template's Claim and Plan sections.
3. **Work.** Push commits as you go. Each push renews the claim.
4. **Hand off.** Fill in the Handoff section, run the checks in the template, add a dated entry to `docs/LOG.md`, and mark
   the pull request ready for review. Stuart reviews and merges. To appear on the token leaderboard, fill in the Donation
   section too, as [Token leaderboard](#token-leaderboard) describes.
5. **Release.** If you stop without delivering, say where you stopped in the pull request and close it.

The claims workflow keeps claims honest. It runs on every pull request event and once a day:

- The earliest open pull request for an item holds the claim and gets the `claim` label. Later ones get `duplicate claim`
  and take over automatically if the holder closes or lapses.
- A draft with no new commit for 72 hours gets `lapsed claim`, and the item is open again. A new commit renews it if no
  one else has claimed the item. A pull request marked ready for review never lapses.
- An item whose status is `reserved: <agent>` can only be claimed from that agent's branches, such as `astra/`.
- It posts one comment per pull request and keeps it up to date. It reads titles, labels and commit dates only and never
  runs code from a pull request.

The tests workflow runs the Python and Node tests and rebuilds the site data on every pull request, including those from
forks. Agents never place orders, sign licences or handle payment. To add or change a request, edit
`REQUESTS_FOR_WORK.md` and run `python tools/build_requests_page.py`; a test fails if `site/requests.html` is stale. To
propose an item without writing it yourself, open an issue with the proposal form.

## Token leaderboard

[openobservatory.info/leaderboard.html](https://openobservatory.info/leaderboard.html) counts the tokens that build Open
Observatory: donated sessions, once their pull request is merged, and the maintainers' own sessions.

### Getting listed

Fill in the pull request template's Donation section before you mark the pull request ready for review:

- **Tokens used:** the total for the work in this pull request, measured as below. You can add a breakdown in brackets
  after the number, for example `1,250,000 (1,200,000 cache reads, 40,000 cache writes, 10,000 output)`.
- **Agent and model:** for example `Claude Code with Claude Opus 5` or `Codex with gpt-5-codex`.
- **List me as:** `username`, or `anonymous` to hide your GitHub username on the board. The pull request itself stays public.

When the pull request is merged, the donations workflow reads the section from `main`. It adds a row to
`data/donations.csv`, rebuilds `site/data/leaderboard.json`, redeploys the site and comments with what it recorded. If it
cannot read the count, it says so in a comment and records nothing. Editing the section after the merge changes nothing
until a maintainer records the pull request again.

### Measuring tokens

Count every token the model processed for the work in the pull request: uncached input, cache writes, cache reads and
output. Cache reads are usually most of the total, because every call re-reads the conversation so far. The build rows
include them, so include yours. Leave out work in the same session that is not part of the pull request, and never count
the same tokens in two pull requests.

If your agent keeps local session logs, `tools/agent_token_usage.py` counts them the same way the build rows were counted.
Times are UTC.

```sh
# Claude Code keeps sessions in ~/.claude/projects/<folder>/<session>.jsonl, and subagents in <session>/subagents/.
python tools/agent_token_usage.py claude ~/.claude/projects/<folder>/<session>.jsonl ~/.claude/projects/<folder>/<session>/subagents/*.jsonl \
  --until 2026-09-20T18:00:00Z --window unrelated=2026-09-20T15:00:00Z..2026-09-20T15:30:00Z

# Codex keeps sessions in ~/.codex/sessions/<year>/<month>/<day>/rollout-<id>.jsonl.
python tools/agent_token_usage.py codex ~/.codex/sessions/2026/09/20/rollout-<id>.jsonl --until 2026-09-20T18:00:00Z
```

- **Which number to report.** The script puts every model response in one group. Report the sum of the `counted` groups:
  `total` for Claude Code and `total_tokens` for Codex.
- **Leaving work out.** `--until` leaves out everything from the time you finished. Each `--window` puts a stretch of
  unrelated work in its own group, so it stays out of the `counted` groups. A response that touches a window belongs to
  that window.
- **Codex.** `total_tokens` is input, cached input included, plus output. The script adds up Codex's per-response records,
  which can come to more than the running counter Codex shows on screen. `matches_thread_total` confirms they equal the
  thread total Codex stores.
- **Other agents.** Use the usage their logs or dashboard report, and say in brackets what the number includes.

### What the numbers mean

- Counts are self-reported and cannot be verified. Merging means a maintainer reviewed the work, not the count, and a
  maintainer may ask how you measured it.
- The rows labelled "Building Open Observatory" were measured from the maintainers' own session logs with the same script.
  `docs/token_accounting.md` gives the method, the exclusions and the breakdown.

### For maintainers

- To record a pull request again after its Donation section is corrected, run the Donations workflow by hand with the pull
  request's number, from the Actions tab or with `gh workflow run donations.yml -f pr=NN`.
- Rows with no pull request, such as build tokens, go straight into `data/donations.csv` with a `label` and a `url` that
  explains the count. Then run `node .github/scripts/donations.cjs rebuild`; a test fails if the leaderboard does not
  match the ledger.

## Work and review

Start `astra/<task-id>`, `claude/<task-id>` or, for donated sessions, `rfw/<NN>-short-name` from current `main`. Keep changes reviewable and avoid files the other agent is actively changing; record necessary shared-file changes in `docs/LOG.md`. Update the relevant status in `docs/ASTRA_TODO.md` and append a dated log entry with results and limitations.

Open a pull request with what changed, validation counts, uncertain labels or geometry decisions, and the first files a reviewer should read. Stuart merges; do not merge or force-push `main`. For dependent PRs, identify their base and merge order.

Every public number must trace to a free public source, a repository script and an attributable polygon with stated confidence. The one exception is training-run records that AI labs supply in confidence: they may train the workload model under the conditions in README's provenance rule, stay in the git-ignored `data/private/`, and are never given to donated sessions. Negative findings remain visible. Thermal roof temperature is not a validated utilisation measurement; nearby power-plant emissions are not a campus's electricity consumption.
