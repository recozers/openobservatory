const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const donations = require('../.github/scripts/donations.cjs');
const board = require('../site/leaderboard.js');

const template = fs.readFileSync(path.join(__dirname, '../.github/pull_request_template.md'), 'utf8');
const fill = (tokens, agent = 'Claude Code with Claude Opus 5', listAs = 'username') => template
  .replace(/(\*\*Tokens used:\*\*)[^\n]*/, `$1 ${tokens}`)
  .replace(/(\*\*Agent and model:\*\*)[^\n]*/, `$1 ${agent}`)
  .replace(/(\*\*List me as:\*\*)[^\n]*/, `$1 ${listAs}`);
const pr = (number, body, extra = {}) => ({ number, title: `[RFW-0${number % 9 + 1}] work`, body, merged_at: `2026-09-${String(10 + number).padStart(2, '0')}T12:00:00Z`,
  user: { login: `donor${number}`, type: 'User' }, ...extra });

test('token counts parse in the usual forms and reject ambiguous or absurd ones', () => {
  const cases = { '1,250,000': 1250000, '1 250 000': 1250000, '1.25M': 1250000, '850k': 850000, '~2 million': 2000000,
    'about 3.5m tokens': 3500000, '1,5M': 1500000, '2.4 billion': 2400000000 };
  for (const [text, want] of Object.entries(cases)) assert.equal(donations.parseTokens(text), want, text);
  for (const text of ['', 'abc', 'lots', '20B', '1,25,000', '-5']) assert.equal(donations.parseTokens(text), null, text);
});

test('the untouched template records nothing, because its examples sit inside comments', () => {
  const parsed = donations.parseDonation(template);
  assert.equal(parsed.found, true);
  assert.equal(parsed.tokens, null);
  assert.equal(parsed.anonymous, false);
  assert.equal(donations.decide(pr(1, template), parsed, []).comment, '');
});

test('a filled Donation section gives tokens, agent and the listing choice', () => {
  const parsed = donations.parseDonation(fill('1.25M', '<b>Codex</b> with *GPT-5*', 'anonymous please'));
  assert.deepEqual([parsed.tokens, parsed.agent, parsed.anonymous], [1250000, 'Codex with GPT-5', true]);
});

test('merging records a row once, comments, and anonymous donors are pseudonymous', () => {
  const merged = pr(3, fill('2,000,000'));
  const first = donations.decide(merged, donations.parseDonation(merged.body), []);
  assert.equal(first.row.donor, 'donor3');
  assert.equal(first.row.item, 'RFW-04');
  assert.match(first.comment, /2,000,000 tokens from @donor3 for RFW-04/);
  const again = donations.decide(merged, donations.parseDonation(merged.body), [first.row]);
  assert.equal(again.row, null, 'recording the same pull request twice changes nothing');
  const hidden = pr(4, fill('1M', 'Codex', 'anonymous'));
  const anon = donations.decide(hidden, donations.parseDonation(hidden.body), []).row;
  assert.match(anon.donor, /^anonymous-[0-9a-f]{8}$/);
  assert.equal(anon.donor, donations.pseudonym('DONOR4'));
  assert.ok(!JSON.stringify(donations.buildLeaderboard([anon])).includes('donor4'));
});

test('unmerged pull requests, missing sections and unreadable counts record nothing', () => {
  assert.equal(donations.decide({ ...pr(5, fill('1M')), merged_at: null }, donations.parseDonation(fill('1M')), []).row, null);
  const bare = donations.decide(pr(6, 'No template here'), donations.parseDonation('No template here'), []);
  assert.equal(bare.row, null);
  assert.match(bare.comment, /No Donation section/);
  const typo = donations.decide(pr(7, fill('a lot')), donations.parseDonation(fill('a lot')), []);
  assert.equal(typo.row, null);
  assert.match(typo.comment, /could not be read/);
});

test('the leaderboard ranks by tokens, then sessions, then who came first, and ties share a rank', () => {
  const row = (n, donor, tokens, day) => ({ pr: String(n), merged_at: `2026-09-${day}T00:00:00Z`, donor, anonymous: 'false', item: '', tokens: String(tokens), agent: 'A' });
  const rows = [row(1, 'ada', 500, '10'), row(2, 'bob', 900, '11'), row(3, 'ada', 400, '12'), row(4, 'cy', 900, '13'), row(5, 'dee', 900, '09')];
  const out = donations.buildLeaderboard(rows);
  assert.deepEqual(out.donors.map(d => [d.name, d.rank, d.tokens, d.sessions]),
    [['ada', 1, 900, 2], ['dee', 2, 900, 1], ['bob', 2, 900, 1], ['cy', 2, 900, 1]]);
  assert.deepEqual(out.totals, { tokens: 3600, sessions: 5, donors: 4 });
  assert.equal(out.updated, '2026-09-13T00:00:00Z');
});

test('the ledger round-trips through CSV, quoting awkward agent names', () => {
  const rows = [{ pr: '9', merged_at: '2026-09-20T00:00:00Z', donor: 'eve', anonymous: 'false', item: 'T-05', tokens: '42000', agent: 'Agent "X", v2' }];
  assert.deepEqual(donations.parseCsv(donations.toCsv(rows)), rows);
  const updated = donations.upsert(rows, { ...rows[0], tokens: '50000' });
  assert.equal(updated.length, 1);
  assert.equal(updated[0].tokens, '50000');
});

test('the committed leaderboard matches the committed ledger', () => {
  const ledger = donations.parseCsv(fs.readFileSync(path.join(__dirname, '../data/donations.csv'), 'utf8'));
  const committed = JSON.parse(fs.readFileSync(path.join(__dirname, '../site/data/leaderboard.json'), 'utf8'));
  assert.deepEqual(committed, donations.buildLeaderboard(ledger), 'run node .github/scripts/donations.cjs rebuild');
});

test('the page renders rows with text only, and says so when the board is empty', () => {
  const made = [];
  const node = tag => { const n = { tag, children: [], attrs: {}, hidden: false, _text: '',
    set textContent(v) { this._text = v; this.children = []; }, get textContent() { return this._text + this.children.map(c => c.textContent || c.text || '').join(''); },
    appendChild(c) { this.children.push(c); return c; }, setAttribute(k, v) { this.attrs[k] = v; } }; made.push(n); return n; };
  const els = { totals: node('p'), rows: node('tbody'), board: node('div') };
  const doc = { getElementById: id => els[id], createElement: node, createTextNode: text => ({ text }) };
  assert.equal(board.render(doc, { totals: { tokens: 0, sessions: 0, donors: 0 }, donors: [] }), 0);
  assert.match(els.totals.textContent, /No donated sessions/);
  assert.equal(els.board.hidden, true);
  const data = donations.buildLeaderboard([{ pr: '15', merged_at: '2026-09-14T16:34:46Z', donor: '<img src=x onerror=alert(1)>', anonymous: 'false', item: 'RFW-07', tokens: '1250000', agent: 'Claude Code' }]);
  data.donors[0].profile = 'javascript:alert(1)';
  assert.equal(board.render(doc, data), 1);
  assert.equal(els.board.hidden, false);
  const row = els.rows.children[0];
  assert.equal(row.children[1].children[0].tag, 'span', 'a profile link that is not on github.com is not a link');
  assert.equal(row.children[1].children[0].textContent, '<img src=x onerror=alert(1)>');
  assert.equal(row.children[2].textContent, '1.25M');
  assert.equal(row.children[4].children[0].attrs.href, 'https://github.com/recozers/openobservatory/pull/15');
  assert.equal(row.children[4].children[0].textContent, 'RFW-07 (#15)');
  assert.match(els.totals.textContent, /1\.25M tokens donated across 1 merged session by 1 donor/);
});
