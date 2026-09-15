// Token leaderboard. When a pull request is merged, .github/workflows/donations.yml runs `record` from main: it reads the
// pull request's Donation section, updates the ledger data/donations.csv, and rebuilds site/data/leaderboard.json.
// Token counts are reported by donors and cannot be verified; merging is the only check. The job never runs code from a
// pull request. Maintainers can also add rows with no pull request, such as the tokens used to build the project, with a
// label and a URL explaining the count. After editing the ledger by hand, run `node .github/scripts/donations.cjs rebuild`.
'use strict';
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const claims = require('../../site/claims.js');

const ROOT = path.resolve(__dirname, '../..');
const LEDGER = path.join(ROOT, 'data', 'donations.csv');
const BOARD = path.join(ROOT, 'site', 'data', 'leaderboard.json');
const FIELDS = ['pr', 'merged_at', 'donor', 'anonymous', 'item', 'tokens', 'agent', 'label', 'url',
  'input_tokens', 'cache_write_tokens', 'cache_read_tokens', 'output_tokens', 'usd'];
const PRICING = path.join(ROOT, 'data', 'api_pricing.csv');
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

// "1,250,000 (1,200,000 cache reads, 40,000 cache writes, 0 uncached input, 10,000 output)" gives the four parts. They are
// kept only if all four are there and add up to the total.
function parseBreakdown(text, total) {
  const s = String(text || '');
  const part = label => {
    const m = new RegExp(`(\\d[\\d,\\s]*?)\\s*(?:${label})`, 'i').exec(s);
    return m ? parseInt(m[1].replace(/[,\\s]/g, ''), 10) : null;
  };
  const parts = { input_tokens: part('uncached input|(?<!cached )input\\b'), cache_write_tokens: part('cache[- ]writes?'),
    cache_read_tokens: part('cache[- ]reads?|cached input'), output_tokens: part('output') };
  if (Object.values(parts).some(v => v === null || !Number.isFinite(v))) return null;
  const sum = Object.values(parts).reduce((a, b) => a + b, 0);
  return total && Math.abs(sum - total) <= Math.max(1, total * 0.001) ? parts : null;
}

function readPricing(file = PRICING) {
  return fs.existsSync(file) ? parseCsv(fs.readFileSync(file, 'utf8')) : [];
}

// Dollars at API list prices, standard tier, from the breakdown. Claude Code writes one-hour caches, so cache writes are
// priced at the one-hour rate; a donor's report does not say which lifetime was used.
function priceBreakdown(agent, parts, pricing = readPricing()) {
  if (!parts) return null;
  const text = String(agent || '').toLowerCase();
  const rate = pricing.find(r => r.tier === 'standard' && String(r.names || '').split(';').some(n => n && text.includes(n.toLowerCase())));
  if (!rate) return null;
  const usd = (parts.input_tokens * Number(rate.input_per_mtok) + parts.cache_write_tokens * Number(rate.cache_write_1h_per_mtok)
    + parts.cache_read_tokens * Number(rate.cache_read_per_mtok) + parts.output_tokens * Number(rate.output_per_mtok)) / 1e6;
  return Math.round(usd * 1e4) / 1e4;
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
  const tokens = parseTokens(tokensText);
  return { found: true, tokens, tokensText: cleanText(tokensText, 40), agent: cleanText(field('Agent and model')),
    anonymous: /\banonym/i.test(field('List me as')), breakdown: parseBreakdown(tokensText, tokens) };
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

function ledgerRow(pr, donation, pricing = readPricing()) {
  const parts = donation.breakdown || null;
  const usd = priceBreakdown(donation.agent, parts, pricing);
  return { pr: String(pr.number), merged_at: pr.merged_at, donor: donation.anonymous ? pseudonym(pr.user.login) : pr.user.login,
    anonymous: donation.anonymous ? 'true' : 'false', item: (claims.parseClaimTitle(pr.title) || {}).id || '',
    tokens: String(donation.tokens), agent: donation.agent, label: '', url: '',
    input_tokens: parts ? String(parts.input_tokens) : '', cache_write_tokens: parts ? String(parts.cache_write_tokens) : '',
    cache_read_tokens: parts ? String(parts.cache_read_tokens) : '', output_tokens: parts ? String(parts.output_tokens) : '',
    usd: usd === null ? '' : String(usd) };
}

function upsert(rows, row) {
  return [...rows.filter(r => r.pr !== row.pr), row]
    .sort((a, b) => a.merged_at.localeCompare(b.merged_at) || Number(a.pr) - Number(b.pr));
}

// Donors ranked by tokens, then by number of contributions, then by who contributed first; equal tokens and contribution
// counts share a rank. A contribution is a merged pull request or a maintainer-added row with a label and a URL.
function buildLeaderboard(rows) {
  const byDonor = new Map();
  for (const r of rows) {
    const tokens = Number(r.tokens);
    if (!Number.isFinite(tokens) || tokens <= 0) continue;
    const d = byDonor.get(r.donor) || { key: r.donor, anonymous: r.anonymous === 'true', tokens: 0, usd: 0, usdMissing: 0, contributions: [],
      agents: new Map(), first: r.merged_at, last: r.merged_at };
    d.tokens += tokens;
    const usd = r.usd === '' || r.usd === undefined ? null : Number(r.usd);
    if (usd === null || !Number.isFinite(usd)) d.usdMissing += 1; else d.usd += usd;
    const pr = r.pr ? Number(r.pr) : null;
    d.contributions.push({ pr, item: r.item || null, label: r.label || null, tokens, usd: Number.isFinite(usd) ? usd : null, merged_at: r.merged_at,
      url: pr ? `${REPO_URL}/pull/${pr}` : (r.url || null), agent: r.agent || null });
    if (r.agent) {
      const a = d.agents.get(r.agent) || { tokens: 0, usd: 0, usdMissing: 0 };
      a.tokens += tokens;
      if (Number.isFinite(usd)) a.usd += usd; else a.usdMissing += 1;
      d.agents.set(r.agent, a);
    }
    if (r.merged_at < d.first) d.first = r.merged_at;
    if (r.merged_at > d.last) d.last = r.merged_at;
    byDonor.set(r.donor, d);
  }
  const donors = [...byDonor.values()].sort((a, b) => b.tokens - a.tokens || b.contributions.length - a.contributions.length || a.first.localeCompare(b.first));
  let rank = 0;
  donors.forEach((d, i) => {
    const prev = donors[i - 1];
    rank = prev && prev.tokens === d.tokens && prev.contributions.length === d.contributions.length ? rank : i + 1;
    d.rank = rank;
  });
  return {
    updated: rows.length ? rows.map(r => r.merged_at).sort().slice(-1)[0] : null,
    totals: { tokens: donors.reduce((s, d) => s + d.tokens, 0), contributions: donors.reduce((s, d) => s + d.contributions.length, 0), donors: donors.length,
      usd: roundCents(donors.reduce((s, d) => s + d.usd, 0)), usd_complete: donors.every(d => d.usdMissing === 0) },
    donors: donors.map(d => ({ rank: d.rank, name: d.anonymous ? 'Anonymous donor' : d.key, anonymous: d.anonymous,
      profile: d.anonymous ? null : `https://github.com/${d.key}`, tokens: d.tokens, usd: roundCents(d.usd), usd_complete: d.usdMissing === 0,
      contributions: d.contributions.sort((a, b) => a.merged_at.localeCompare(b.merged_at) || (a.pr || 0) - (b.pr || 0))
        .map(c => ({ ...c, usd: c.usd === null ? null : roundCents(c.usd) })),
      agents: [...d.agents.entries()].map(([name, a]) => ({ name, tokens: a.tokens, usd: roundCents(a.usd), usd_complete: a.usdMissing === 0 }))
        .sort((a, b) => b.tokens - a.tokens || a.name.localeCompare(b.name)),
      first: d.first, last: d.last })),
  };
}

function roundCents(x) { return Math.round(Number(x) * 100) / 100; }

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
    comment: `${MARK}\n**Recorded on the [token leaderboard](https://openobservatory.info/leaderboard.html): ${formatExact(donation.tokens)} tokens from ${who}${row.item ? ` for ${row.item}` : ''}${row.usd ? `, worth $${Number(row.usd).toFixed(2)} at API list prices` : ''}.** Token counts are reported by donors and are not verified.${row.usd ? '' : ' No dollar value was recorded: that needs the model in "Agent and model" and a breakdown after the total (cache reads, cache writes, uncached input, output), as CONTRIBUTING.md shows.'}` };
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

module.exports = { MARK, FIELDS, parseBreakdown, priceBreakdown, readPricing, parseTokens, parseDonation, pseudonym, parseCsv, toCsv, ledgerRow, upsert, buildLeaderboard, decide, record, comment, readLedger, writeAll };

if (require.main === module) {
  if (process.argv[2] !== 'rebuild') { console.error('usage: node .github/scripts/donations.cjs rebuild'); process.exit(2); }
  const rows = readLedger();
  writeAll(rows);
  console.log(`rebuilt site/data/leaderboard.json from ${rows.length} ledger rows`);
}
