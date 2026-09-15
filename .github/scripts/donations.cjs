// Token leaderboard. When a pull request is merged, .github/workflows/donations.yml runs `record` from main: it reads the
// pull request's Donation section, updates the ledger data/donations.csv, and rebuilds site/data/leaderboard.json.
// Token counts are reported by donors and cannot be verified; merging is the only check. The job never runs code from a
// pull request. After editing the ledger by hand, run `node .github/scripts/donations.cjs rebuild`.
'use strict';
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const claims = require('../../site/claims.js');

const ROOT = path.resolve(__dirname, '../..');
const LEDGER = path.join(ROOT, 'data', 'donations.csv');
const BOARD = path.join(ROOT, 'site', 'data', 'leaderboard.json');
const FIELDS = ['pr', 'merged_at', 'donor', 'anonymous', 'item', 'tokens', 'agent'];
const MARK = '<!-- open-observatory-donation-bot -->';
const MAX_TOKENS = 10e9;  // larger reports are treated as typos and left for a maintainer
const REPO_URL = 'https://github.com/recozers/openobservatory';

// "1,250,000", "1 250 000", "1.25M", "850k", "~2 million" give whole numbers of tokens; anything else gives null.
function parseTokens(text) {
  const m = /^\s*(?:~|about|approx(?:imately|\.)?)?\s*(\d+(?:[.,\s]\d+)*)\s*(k|thousand|m|mn|million|b|bn|billion)?\b/i.exec(String(text || ''));
  if (!m) return null;
  let number = m[1].replace(/\s/g, '');
  if (/^\d{1,3}(,\d{3})+(\.\d+)?$/.test(number)) number = number.replace(/,/g, '');
  else if (/^\d+,\d+$/.test(number) && m[2]) number = number.replace(',', '.');
  else if (/,/.test(number)) return null;
  const unit = (m[2] || '').toLowerCase();
  const scale = unit.startsWith('k') || unit === 'thousand' ? 1e3 : unit.startsWith('m') ? 1e6 : unit.startsWith('b') ? 1e9 : 1;
  const tokens = Math.round(parseFloat(number) * scale);
  return Number.isFinite(tokens) && tokens > 0 && tokens <= MAX_TOKENS ? tokens : null;
}

function cleanText(text, max = 80) {
  const plain = String(text || '').replace(/<[^>]*>/g, ' ').replace(/[*_`#[\]]/g, '').replace(/\s+/g, ' ').trim();
  return plain.length > max ? `${plain.slice(0, max - 1)}…` : plain;
}

// The Donation section of a pull request body, with the template's HTML comments removed first so that its examples are
// never read as answers.
function parseDonation(body) {
  const text = String(body || '').replace(/<!--[\s\S]*?-->/g, '');
  const section = /^##\s+Donation\s*$([\s\S]*?)(?=^##\s|(?![\s\S]))/im.exec(text);
  if (!section) return { found: false, tokens: null, agent: '', anonymous: false, tokensText: '' };
  const field = label => {
    const m = new RegExp(`\\*\\*${label}:?\\*\\*:?[ \\t]*(.*)$`, 'im').exec(section[1]);
    return m ? m[1].trim() : '';
  };
  const tokensText = field('Tokens used');
  return { found: true, tokens: parseTokens(tokensText), tokensText: cleanText(tokensText, 40), agent: cleanText(field('Agent and model')),
    anonymous: /\banonym/i.test(field('List me as')) };
}

function pseudonym(login) {
  return `anonymous-${crypto.createHash('sha256').update(String(login).toLowerCase()).digest('hex').slice(0, 8)}`;
}

// ---------------------------------------------------------------- ledger

function parseCsv(text) {
  const rows = [];
  let row = [], field = '', quoted = false;
  const s = String(text || '');
  for (let i = 0; i < s.length; i += 1) {
    const ch = s[i];
    if (quoted) {
      if (ch === '"' && s[i + 1] === '"') { field += '"'; i += 1; }
      else if (ch === '"') quoted = false;
      else field += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ',') { row.push(field); field = ''; }
    else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && s[i + 1] === '\n') i += 1;
      row.push(field); field = '';
      if (row.some(v => v !== '')) rows.push(row);
      row = [];
    } else field += ch;
  }
  if (field !== '' || row.length) { row.push(field); if (row.some(v => v !== '')) rows.push(row); }
  const [header, ...data] = rows;
  return header ? data.map(r => Object.fromEntries(header.map((h, i) => [h, r[i] ?? '']))) : [];
}

function toCsv(rows) {
  const cell = v => (/[",\n\r]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v));
  return [FIELDS.join(','), ...rows.map(r => FIELDS.map(f => cell(r[f] ?? '')).join(','))].join('\n') + '\n';
}

function ledgerRow(pr, donation) {
  return { pr: String(pr.number), merged_at: pr.merged_at, donor: donation.anonymous ? pseudonym(pr.user.login) : pr.user.login,
    anonymous: donation.anonymous ? 'true' : 'false', item: (claims.parseClaimTitle(pr.title) || {}).id || '',
    tokens: String(donation.tokens), agent: donation.agent };
}

function upsert(rows, row) {
  return [...rows.filter(r => r.pr !== row.pr), row]
    .sort((a, b) => a.merged_at.localeCompare(b.merged_at) || Number(a.pr) - Number(b.pr));
}

// Donors ranked by reported tokens, then by sessions, then by who donated first. Equal tokens and sessions share a rank.
function buildLeaderboard(rows) {
  const byDonor = new Map();
  for (const r of rows) {
    const tokens = Number(r.tokens);
    if (!Number.isFinite(tokens) || tokens <= 0) continue;
    const d = byDonor.get(r.donor) || { key: r.donor, anonymous: r.anonymous === 'true', tokens: 0, sessions: 0, contributions: [], agents: [],
      first: r.merged_at, last: r.merged_at };
    d.tokens += tokens;
    d.sessions += 1;
    d.contributions.push({ pr: Number(r.pr), item: r.item || null, tokens, merged_at: r.merged_at, url: `${REPO_URL}/pull/${r.pr}` });
    if (r.agent && !d.agents.includes(r.agent)) d.agents.push(r.agent);
    if (r.merged_at < d.first) d.first = r.merged_at;
    if (r.merged_at > d.last) d.last = r.merged_at;
    byDonor.set(r.donor, d);
  }
  const donors = [...byDonor.values()].sort((a, b) => b.tokens - a.tokens || b.sessions - a.sessions || a.first.localeCompare(b.first));
  let rank = 0;
  donors.forEach((d, i) => {
    const prev = donors[i - 1];
    rank = prev && prev.tokens === d.tokens && prev.sessions === d.sessions ? rank : i + 1;
    d.rank = rank;
  });
  return {
    updated: rows.length ? rows.map(r => r.merged_at).sort().slice(-1)[0] : null,
    totals: { tokens: donors.reduce((s, d) => s + d.tokens, 0), sessions: donors.reduce((s, d) => s + d.sessions, 0), donors: donors.length },
    donors: donors.map(d => ({ rank: d.rank, name: d.anonymous ? 'Anonymous donor' : d.key, anonymous: d.anonymous,
      profile: d.anonymous ? null : `https://github.com/${d.key}`, tokens: d.tokens, sessions: d.sessions,
      contributions: d.contributions.sort((a, b) => a.merged_at.localeCompare(b.merged_at)), agents: d.agents, first: d.first, last: d.last })),
  };
}

function readLedger() { return fs.existsSync(LEDGER) ? parseCsv(fs.readFileSync(LEDGER, 'utf8')) : []; }

function writeAll(rows) {
  fs.mkdirSync(path.dirname(LEDGER), { recursive: true });
  fs.writeFileSync(LEDGER, toCsv(rows));
  fs.writeFileSync(BOARD, `${JSON.stringify(buildLeaderboard(rows), null, 2)}\n`);
}

// ---------------------------------------------------------------- workflow steps

function formatExact(n) { return Number(n).toLocaleString('en-GB'); }

// Pure: what to record and say for one pull request.
function decide(pr, donation, existing) {
  if (!pr.merged_at) return { row: null, comment: '' };
  const claim = claims.parseClaimTitle(pr.title);
  if (!donation.found) {
    return { row: null, comment: claim ? `${MARK}\n**No Donation section, so nothing was added to the [token leaderboard](https://openobservatory.info/leaderboard.html).** To be counted, add the Donation section from the pull request template to this description and ask a maintainer to run the Donations workflow with this pull request's number.` : '' };
  }
  if (donation.tokens === null) {
    return { row: null, comment: donation.tokensText
      ? `${MARK}\n**The token count "${donation.tokensText}" could not be read, so nothing was recorded.** Write it as a number such as 1,250,000 or 1.25M, then ask a maintainer to run the Donations workflow with this pull request's number.`
      : '' };
  }
  const row = ledgerRow(pr, donation);
  const before = existing.find(r => r.pr === row.pr);
  const same = before && FIELDS.every(f => String(before[f]) === String(row[f]));
  const who = donation.anonymous ? 'an anonymous donor' : `@${pr.user.login}`;
  return { row: same ? null : row,
    comment: `${MARK}\n**Recorded on the [token leaderboard](https://openobservatory.info/leaderboard.html): ${formatExact(donation.tokens)} tokens from ${who}${row.item ? ` for ${row.item}` : ''}.** Token counts are reported by donors and are not verified.` };
}

async function record({ github, context, core }) {
  const { owner, repo } = context.repo;
  const number = Number(context.payload.pull_request ? context.payload.pull_request.number : (context.payload.inputs || {}).pr);
  if (!Number.isInteger(number) || number <= 0) { core.setFailed('No pull request number'); return; }
  const { data: pr } = await github.rest.pulls.get({ owner, repo, pull_number: number });
  if (!pr.merged_at) { core.info(`#${number} is not merged; nothing to record`); return; }
  if (pr.user.type === 'Bot') { core.info(`#${number} was opened by a bot; skipped`); return; }
  const rows = readLedger();
  const outcome = decide(pr, parseDonation(pr.body), rows);
  if (outcome.row) writeAll(upsert(rows, outcome.row));
  core.setOutput('changed', outcome.row ? 'true' : 'false');
  core.setOutput('pr', String(number));
  core.setOutput('comment', outcome.comment);
  core.info(outcome.row ? `#${number}: recorded ${outcome.row.tokens} tokens` : `#${number}: ledger unchanged`);
}

async function comment({ github, context, pr, body }) {
  const { owner, repo } = context.repo;
  const comments = await github.paginate(github.rest.issues.listComments, { owner, repo, issue_number: pr, per_page: 100 });
  const mine = comments.find(c => c.user && c.user.type === 'Bot' && String(c.body || '').startsWith(MARK));
  if (!mine) await github.rest.issues.createComment({ owner, repo, issue_number: pr, body });
  else if (mine.body !== body) await github.rest.issues.updateComment({ owner, repo, comment_id: mine.id, body });
}

module.exports = { MARK, FIELDS, parseTokens, parseDonation, pseudonym, parseCsv, toCsv, ledgerRow, upsert, buildLeaderboard, decide, record, comment, readLedger, writeAll };

if (require.main === module) {
  if (process.argv[2] !== 'rebuild') { console.error('usage: node .github/scripts/donations.cjs rebuild'); process.exit(2); }
  const rows = readLedger();
  writeAll(rows);
  console.log(`rebuilt site/data/leaderboard.json from ${rows.length} ledger rows`);
}
