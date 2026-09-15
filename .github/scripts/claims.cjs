// Claim bot for requests for work. .github/workflows/claims.yml runs it from main with permission to label and comment on
// pull requests, so it reads pull request metadata through the API only and never checks out or runs contributed code.
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const claims = require('../../site/claims.js');

const MARK = '<!-- open-observatory-claim-bot -->';
const { LABELS } = claims;
const LABEL_STYLE = {
  [LABELS.claim]: ['0e8a16', 'Holds the claim on a request for work'],
  [LABELS.duplicate]: ['d93f0b', 'Another open pull request already holds this claim, or the item is reserved'],
  [LABELS.lapsed]: ['fbca04', 'Draft claim with no new commit for 72 hours; the item is open again'],
};
const FOOTER = '\n\n<sub>Kept up to date by the claims workflow, which reads pull request titles, labels and commit dates only. See CONTRIBUTING.md.</sub>';

// Pure: the labels to add and remove and the bot comment for every open pull request whose title is, or tries to be, a claim.
function plan(prs, requests, now) {
  const assessed = claims.assess(prs, requests, now);
  const managed = Object.values(LABELS);
  const actions = [];
  for (const pr of prs) {
    const a = assessed[pr.number];
    if (!a) continue;
    const want = new Set();
    let message;
    if (a.malformed) {
      message = '**This title looks like a claim but does not follow the format.** Start the title with the ID in square brackets, for example `[RFW-07] Short title`, so the claim is recorded.';
    } else if (!a.known) {
      message = `**${a.id} is not an item in REQUESTS_FOR_WORK.md on main.** Check the ID on https://openobservatory.info/requests.html and fix the title.`;
    } else if (a.reservedFor) {
      want.add(LABELS.duplicate);
      message = `**${a.id} is reserved for ${a.reservedFor}.** Reserved items are being worked on by the project's own agents. Pick another open item, or ask in this pull request if you think the reservation is stale.`;
    } else if (a.lapsed) {
      want.add(LABELS.lapsed);
      message = `**The claim on ${a.id} has lapsed.** This draft has had no new commit for ${claims.LAPSE_HOURS} hours, so the item is open to others. Push a commit to renew the claim if nobody else has taken it.`;
    } else if (a.duplicateOf) {
      want.add(LABELS.duplicate);
      message = `**${a.id} is already claimed in #${a.duplicateOf}.** That pull request was opened first. Coordinate there or pick another open item. If #${a.duplicateOf} closes or lapses, this pull request takes over the claim automatically.`;
    } else if (a.holder) {
      want.add(LABELS.claim);
      message = pr.draft
        ? `**Claim recorded: ${a.id}.** This pull request holds the claim. While it is a draft, the claim lapses after ${claims.LAPSE_HOURS} hours without a new commit. When you hand off, fill in the Handoff and Donation sections and mark it ready for review. The Donation section's token count goes on the [leaderboard](https://openobservatory.info/leaderboard.html) once the pull request is merged.`
        : `**${a.id} is ready for review.** This pull request holds the claim, and claims no longer lapse once they are ready for review.`;
    }
    const have = new Set(pr.labels || []);
    actions.push({
      number: pr.number,
      add: [...want].filter(l => !have.has(l)),
      remove: managed.filter(l => have.has(l) && !want.has(l)),
      message: `${MARK}\n${message}${FOOTER}`,
    });
  }
  return actions;
}

function latestCommitDate(commits, now) {
  let latest = null;
  for (const c of commits || []) {
    const t = Date.parse((c.commit && (c.commit.committer || c.commit.author) || {}).date);
    if (Number.isFinite(t) && t <= now && (latest === null || t > latest)) latest = t;
  }
  return latest === null ? null : new Date(latest).toISOString();
}

async function run({ github, context, core }) {
  const { owner, repo } = context.repo;
  const now = Date.now();
  const root = process.env.GITHUB_WORKSPACE || path.resolve(__dirname, '../..');
  const requests = claims.parseRequests(fs.readFileSync(path.join(root, 'REQUESTS_FOR_WORK.md'), 'utf8'));
  const pulls = await github.paginate(github.rest.pulls.list, { owner, repo, state: 'open', per_page: 100 });
  const prs = [];
  for (const p of pulls) {
    const pr = { number: p.number, title: p.title, draft: p.draft, created_at: p.created_at, head_ref: p.head.ref,
      labels: p.labels.map(l => l.name), last_commit_at: null };
    if (claims.parseClaimTitle(p.title)) {
      const commits = await github.paginate(github.rest.pulls.listCommits, { owner, repo, pull_number: p.number, per_page: 100 });
      pr.last_commit_at = latestCommitDate(commits, now);
    }
    prs.push(pr);
  }
  const actions = plan(prs, requests, now);
  if (actions.some(a => a.add.length)) {
    for (const [name, [color, description]] of Object.entries(LABEL_STYLE)) {
      try { await github.rest.issues.createLabel({ owner, repo, name, color, description }); }
      catch (err) { if (err.status !== 422) throw err; }
    }
  }
  for (const act of actions) {
    if (act.add.length) await github.rest.issues.addLabels({ owner, repo, issue_number: act.number, labels: act.add });
    for (const name of act.remove) {
      try { await github.rest.issues.removeLabel({ owner, repo, issue_number: act.number, name }); }
      catch (err) { if (err.status !== 404) throw err; }
    }
    const comments = await github.paginate(github.rest.issues.listComments, { owner, repo, issue_number: act.number, per_page: 100 });
    const mine = comments.find(c => c.user && c.user.type === 'Bot' && String(c.body || '').startsWith(MARK));
    if (!mine) await github.rest.issues.createComment({ owner, repo, issue_number: act.number, body: act.message });
    else if (mine.body !== act.message) await github.rest.issues.updateComment({ owner, repo, comment_id: mine.id, body: act.message });
    core.info(`#${act.number}: add [${act.add.join(', ')}] remove [${act.remove.join(', ')}]`);
  }
  core.info(`${prs.length} open pull requests, ${actions.length} claim-like`);
}

module.exports = { MARK, plan, latestCommitDate, run };
