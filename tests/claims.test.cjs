const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const claims = require('../site/claims.js');
const bot = require('../.github/scripts/claims.cjs');

// The claim rules are tested against a fixed table, so editing a status in REQUESTS_FOR_WORK.md cannot break them.
const FIXTURE = [
  '| ID | Request | Answers | Size | Keys | Status |',
  '|---|---|---|---|---|---|',
  '| [RFW-07](#rfw-07-chindatas-per-data-centre-table) | Chindata table | Capacity | S | none | open: table done; EDGAR search remains |',
  '| [RFW-12](#rfw-12-dedicated-plants) | Dedicated plants | Utilisation | M | none | reserved: Astra |',
  '| ID | Theory | Answers | Resolution if it works | Region | Keys |',
  '| [T-05](#t-05-transformer-heat) | Transformer heat | Workload | Hourly | US | EE |',
  '| [PAID-03](#paid-03-thermal-imagery) | Thermal imagery | Workload | US | 1 campus |',
].join('\n');
const requests = claims.parseRequests(FIXTURE);
const real = claims.parseRequests(fs.readFileSync(path.join(__dirname, '../REQUESTS_FOR_WORK.md'), 'utf8'));
const HOUR = 3600e3;
const NOW = Date.parse('2026-09-20T12:00:00Z');
const iso = hoursAgo => new Date(NOW - hoursAgo * HOUR).toISOString();
const pr = (number, title, extra = {}) => ({ number, title, draft: true, created_at: iso(10), head_ref: `rfw/${number}`,
  last_commit_at: iso(1), labels: [], ...extra });
const byNumber = actions => Object.fromEntries(actions.map(a => [a.number, a]));

test('claim titles parse to a padded ID, and near misses are caught', () => {
  assert.equal(claims.parseClaimTitle('[RFW-07] Chindata table').id, 'RFW-07');
  assert.equal(claims.parseClaimTitle(' [rfw-7] lower case').id, 'RFW-07');
  assert.equal(claims.parseClaimTitle('[T-05] Transformer heat').id, 'T-05');
  assert.equal(claims.parseClaimTitle('[PAID-3] Thermal imagery').id, 'PAID-03');
  assert.equal(claims.parseClaimTitle('RFW-07: no brackets'), null);
  assert.equal(claims.looksLikeClaim('RFW-07: no brackets'), true);
  assert.equal(claims.looksLikeClaim('[T 5] missing hyphen'), true);
  assert.equal(claims.looksLikeClaim('B7: add initial generator watches and monthly NOx screening'), false);
  assert.equal(claims.looksLikeClaim('Serve the site at https://openobservatory.info'), false);
});

test('request tables give each item its anchor, status and any reservation', () => {
  assert.deepEqual(Object.keys(requests), ['RFW-07', 'RFW-12', 'T-05', 'PAID-03']);
  assert.equal(requests['RFW-07'].status, 'open: table done; EDGAR search remains');
  assert.equal(requests['RFW-07'].reservedFor, null);
  assert.match(requests['RFW-07'].anchor, /^rfw-07-/);
  assert.equal(requests['RFW-12'].reservedFor, 'Astra');
  assert.equal(requests['T-05'].status, null);
});

test('every table row in REQUESTS_FOR_WORK.md is readable', () => {
  const ids = Object.keys(real);
  assert.ok(ids.filter(id => id.startsWith('RFW-')).length >= 33);
  assert.ok(ids.some(id => id.startsWith('T-')) && ids.some(id => id.startsWith('PAID-')));
  assert.ok(ids.every(id => real[id].anchor.startsWith(`${id.toLowerCase()}-`)));
  assert.ok(ids.filter(id => id.startsWith('RFW-')).every(id => real[id].status), 'every request has a status');
});

test('the earliest open pull request holds a claim and later ones are duplicates', () => {
  const prs = [pr(20, '[RFW-07] second', { created_at: iso(5) }), pr(15, '[RFW-07] first', { created_at: iso(30) })];
  const actions = byNumber(bot.plan(prs, requests, NOW));
  assert.deepEqual(actions[15].add, ['claim']);
  assert.deepEqual(actions[20].add, ['duplicate claim']);
  assert.match(actions[20].message, /already claimed in #15/);
  assert.ok(actions[15].message.startsWith(bot.MARK));
});

test('a draft lapses after 72 hours without a commit and the next pull request takes over', () => {
  const prs = [pr(15, '[RFW-07] stale', { created_at: iso(100), last_commit_at: iso(73), labels: ['claim'] }),
    pr(20, '[RFW-07] active', { created_at: iso(5), labels: ['duplicate claim'] })];
  const actions = byNumber(bot.plan(prs, requests, NOW));
  assert.deepEqual(actions[15].add, ['lapsed claim']);
  assert.deepEqual(actions[15].remove, ['claim']);
  assert.deepEqual(actions[20].add, ['claim']);
  assert.deepEqual(actions[20].remove, ['duplicate claim']);
});

test('a pull request ready for review never lapses, and a new commit renews a lapsed draft', () => {
  const ready = bot.plan([pr(15, '[RFW-07] delivered', { draft: false, last_commit_at: iso(500) })], requests, NOW);
  assert.deepEqual(ready[0].add, ['claim']);
  const renewed = bot.plan([pr(15, '[RFW-07] back', { last_commit_at: iso(2), labels: ['lapsed claim'] })], requests, NOW);
  assert.deepEqual(renewed[0].add, ['claim']);
  assert.deepEqual(renewed[0].remove, ['lapsed claim']);
});

test('reserved items can only be claimed from the reserving agent\'s branches', () => {
  const outside = bot.plan([pr(30, '[RFW-12] plants', { head_ref: 'rfw/12-plants' })], requests, NOW);
  assert.deepEqual(outside[0].add, ['duplicate claim']);
  assert.match(outside[0].message, /reserved for Astra/);
  const astra = bot.plan([pr(31, '[RFW-12] plants', { head_ref: 'astra/b8' })], requests, NOW);
  assert.deepEqual(astra[0].add, ['claim']);
});

test('unknown IDs and malformed titles get guidance but no labels; other pull requests are ignored', () => {
  const actions = byNumber(bot.plan([pr(40, '[RFW-99] nope'), pr(41, 'RFW-07 without brackets'), pr(42, 'Fix a typo')], requests, NOW));
  assert.match(actions[40].message, /RFW-99 is not an item/);
  assert.deepEqual(actions[40].add, []);
  assert.match(actions[41].message, /does not follow the format/);
  assert.equal(actions[42], undefined);
});

test('commit dates in the future are ignored when finding the latest commit', () => {
  const commits = [{ commit: { committer: { date: iso(80) } } }, { commit: { committer: { date: iso(-50) } } }, { commit: { author: { date: iso(3) } } }];
  assert.equal(bot.latestCommitDate(commits, NOW), iso(3));
  assert.equal(bot.latestCommitDate([], NOW), null);
});

test('the page trusts bot labels, keeps the earliest claim and rejects links outside the repository', () => {
  const base = { html_url: 'https://github.com/recozers/openobservatory/pull/15', draft: true, labels: [] };
  const held = claims.liveClaims([
    { ...base, number: 15, title: '[RFW-07] first', created_at: iso(30) },
    { ...base, number: 20, title: '[RFW-07] second', created_at: iso(5), html_url: 'https://github.com/recozers/openobservatory/pull/20' },
    { ...base, number: 21, title: '[RFW-08] lapsed', created_at: iso(5), labels: [{ name: 'lapsed claim' }] },
    { ...base, number: 22, title: '[RFW-09] elsewhere', created_at: iso(5), html_url: 'https://example.com/pull/22' },
  ]);
  assert.deepEqual(Object.keys(held), ['RFW-07']);
  assert.equal(held['RFW-07'].number, 15);
});

test('the page marks the status cell and heading of a claimed item', () => {
  const made = [];
  const el = (tag, props = {}) => { const e = { tag, children: [], textContent: '', ...props,
    appendChild(c) { this.children.push(c); return c; } }; made.push(e); return e; };
  const statusCell = el('td', { textContent: 'open' });
  const heading = el('h4');
  const table = el('table', { querySelectorAll: () => ['ID', 'Request', 'Answers', 'Size', 'Keys', 'Status'].map(t => ({ textContent: t })) });
  const row = { querySelectorAll: () => [el('td'), el('td'), el('td'), el('td'), el('td'), statusCell] };
  const link = { closest: sel => (sel === 'tr' ? row : table), parentNode: el('td') };
  const doc = {
    querySelector: sel => (sel === 'td a[href^="#rfw-07-"]' ? link : sel === 'h4[id^="rfw-07-"]' ? heading : null),
    createElement: tag => el(tag), createTextNode: text => ({ text }),
  };
  const n = claims.annotate(doc, { 'RFW-07': { id: 'RFW-07', number: 15, url: 'https://github.com/recozers/openobservatory/pull/15', draft: true } });
  assert.equal(n, 1);
  assert.equal(statusCell.children[0].textContent, 'claimed in #15');
  assert.equal(statusCell.children[0].href, 'https://github.com/recozers/openobservatory/pull/15');
  assert.equal(heading.children[1].textContent, 'claimed in #15');
});
