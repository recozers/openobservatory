<!--
Claiming an item? Start the title with its ID, for example "[RFW-07] Short title". Theories use [T-NN] and the preparation
of a paid request [PAID-NN]. Open the pull request as a draft: a draft with no new commit for 72 hours lapses. Other
changes need no ID. Delete the sections that do not apply.
-->

## Claim

- **Item:** <!-- link to the item on https://openobservatory.info/requests.html -->
- **Checked:** no open pull request already claims this ID
- **Credentials needed:** <!-- none, Earth Engine, EPA or Earthdata -->

## Plan

<!-- A few lines: what you will do, in what order, and where you will stop if time runs out. -->

## Handoff

<!-- Fill this in, then mark the pull request ready for review. A negative result with numbers is a full delivery. -->

- **What changed:**
- **Validation numbers:**
- **What remains uncertain:**
- **Where I stopped:**
- **Files a reviewer should read first:**

## Donation

<!-- Counted on the token leaderboard, https://openobservatory.info/leaderboard.html, when this pull request is merged.
Counts are self-reported. Leave this section out if you do not want to be listed. -->

- **Tokens used:** <!-- the session's total as your agent reports it, for example 1,250,000 or 1.25M -->
- **Agent and model:** <!-- for example Claude Code with Claude Opus 5 -->
- **List me as:** username <!-- or anonymous -->

## Checklist

- [ ] `python -m unittest discover -s tests`
- [ ] `node --test tests/*.test.cjs`
- [ ] `python tools/refresh.py --dry-run`
- [ ] Every new number has a free public source URL and a script that reproduces it
- [ ] Negative results are recorded, not dropped
- [ ] A dated entry in `docs/LOG.md`
- [ ] No keys, `.env`, `secrets/` or `data/private/` files
