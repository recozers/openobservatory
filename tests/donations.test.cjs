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

test('the leaderboard ranks by tokens, then contributions, then who came first, and ties share a rank', () => {
  const row = (n, donor, tokens, day) => ({ pr: String(n), merged_at: `2026-09-${day}T00:00:00Z`, donor, anonymous: 'false', item: '', tokens: String(tokens), agent: 'A', label: '', url: '' });
  const rows = [row(1, 'ada', 500, '10'), row(2, 'bob', 900, '11'), row(3, 'ada', 400, '12'), row(4, 'cy', 900, '13'), row(5, 'dee', 900, '09')];
  const out = donations.buildLeaderboard(rows);
  assert.deepEqual(out.donors.map(d => [d.name, d.rank, d.tokens, d.contributions.length]),
    [['ada', 1, 900, 2], ['dee', 2, 900, 1], ['bob', 2, 900, 1], ['cy', 2, 900, 1]]);
  assert.deepEqual(out.totals, { tokens: 3600, contributions: 5, donors: 4, usd: 0, usd_complete: false });
  assert.equal(out.updated, '2026-09-13T00:00:00Z');
});

test('maintainer rows without a pull request keep their label and link, and agents get subtotals', () => {
  const doc = 'https://github.com/recozers/openobservatory/blob/main/docs/token_accounting.md';
  const rows = [
    { pr: '', merged_at: '2026-09-13T00:00:00Z', donor: 'max', anonymous: 'false', item: '', tokens: '300', agent: 'Codex', label: 'Building Open Observatory', url: doc, usd: '3.004' },
    { pr: '15', merged_at: '2026-09-14T00:00:00Z', donor: 'max', anonymous: 'false', item: 'RFW-07', tokens: '100', agent: 'Claude Code', label: '', url: '', usd: '1.5' },
    { pr: '', merged_at: '2026-09-15T00:00:00Z', donor: 'max', anonymous: 'false', item: '', tokens: '200', agent: 'Claude Code', label: 'Building Open Observatory', url: doc, usd: '1.25' },
  ];
  const board = donations.buildLeaderboard(rows);
  const [max] = board.donors;
  assert.equal(max.tokens, 600);
  assert.equal(max.usd, 5.75);
  assert.deepEqual(board.totals, { tokens: 600, contributions: 3, donors: 1, usd: 5.75, usd_complete: true });
  assert.deepEqual(max.agents, [{ name: 'Claude Code', tokens: 300, usd: 2.75, usd_complete: true }, { name: 'Codex', tokens: 300, usd: 3, usd_complete: true }]);
  assert.deepEqual(max.contributions.map(c => [c.pr, c.label, c.url]), [[null, 'Building Open Observatory', doc],
    [15, null, 'https://github.com/recozers/openobservatory/pull/15'], [null, 'Building Open Observatory', doc]]);
  const merged = donations.upsert(rows, { ...rows[1], tokens: '150' });
  assert.equal(merged.length, 3, 'recording a pull request again leaves maintainer rows alone');
});

test('the ledger round-trips through CSV, quoting awkward agent names', () => {
  const rows = [{ pr: '9', merged_at: '2026-09-20T00:00:00Z', donor: 'eve', anonymous: 'false', item: 'T-05', tokens: '42000', agent: 'Agent "X", v2', label: '', url: '',
    input_tokens: '1000', cache_write_tokens: '1000', cache_read_tokens: '39000', output_tokens: '1000', usd: '0.1' }];
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
  assert.equal(board.render(doc, { totals: { tokens: 0, contributions: 0, donors: 0 }, donors: [] }), 0);
  assert.match(els.totals.textContent, /No donated sessions/);
  assert.equal(els.board.hidden, true);
  const data = donations.buildLeaderboard([{ pr: '15', merged_at: '2026-09-14T16:34:46Z', donor: '<img src=x onerror=alert(1)>', anonymous: 'false', item: 'RFW-07', tokens: '1250000', agent: 'Claude Code', label: '', url: '', usd: '12.5' },
    { pr: '', merged_at: '2026-09-13T00:00:00Z', donor: '<img src=x onerror=alert(1)>', anonymous: 'false', item: '', tokens: '750000', agent: 'Codex', label: 'Building Open Observatory', url: 'https://evil.example/x', usd: '' }]);
  data.donors[0].profile = 'javascript:alert(1)';
  assert.equal(board.render(doc, data), 1);
  assert.equal(els.board.hidden, false);
  const row = els.rows.children[0];
  assert.equal(row.children[1].children[0].tag, 'span', 'a profile link that is not on github.com is not a link');
  assert.equal(row.children[1].children[0].textContent, '<img src=x onerror=alert(1)>');
  assert.equal(row.children[2].textContent, '2M');
  assert.equal(row.children[3].textContent, 'at least $12.50', 'a donor with an unpriced contribution shows a lower bound');
  const [build, pr15] = row.children[4].children;
  assert.equal(build.children[0].tag, 'span', 'a link outside the repository is shown as text');
  assert.equal(build.children[0].textContent, 'Building Open Observatory');
  assert.equal(pr15.children[0].attrs.href, 'https://github.com/recozers/openobservatory/pull/15');
  assert.equal(pr15.children[0].textContent, 'RFW-07 (#15)');
  assert.match(row.children[1].textContent, /Claude Code: 1\.25M · \$12\.50/);
  assert.match(pr15.textContent, /RFW-07 \(#15\) · 1\.25M, \$12\.50/);
  assert.match(els.totals.textContent, /2M tokens, worth at least \$12\.50 at API list prices, from 1 donor across 2 contributions/);
});

test('a token breakdown is read from the Donation line and priced at the model\'s list rates', () => {
  const line = '6,753,386 (6,268,161 cache reads, 414,418 cache writes, 1,190 uncached input, 69,617 output; 40 responses)';
  const parts = donations.parseBreakdown(line, 6753386);
  assert.deepEqual(parts, { input_tokens: 1190, cache_write_tokens: 414418, cache_read_tokens: 6268161, output_tokens: 69617 });
  const pricing = [{ model_id: 'claude-fable-5-1', names: 'Claude Fable 5.1;claude-fable-5-1', tier: 'standard', input_per_mtok: '10',
    cache_write_5m_per_mtok: '12.50', cache_write_1h_per_mtok: '20', cache_read_per_mtok: '0.25', output_per_mtok: '50' }];
  assert.equal(donations.priceBreakdown('Claude Code with Claude Fable 5.1', parts, pricing), 13.3482);
  assert.equal(donations.priceBreakdown('Some Other Agent', parts, pricing), null, 'unknown models get no price');
  assert.equal(donations.parseBreakdown('1.25M', 1250000), null, 'a bare total has no breakdown');
  assert.equal(donations.parseBreakdown('100 (10 cache reads, 10 cache writes, 10 uncached input, 10 output)', 100), null, 'parts must add up');
  const codex = donations.parseBreakdown('81,551,994 (2,856,260 uncached input, 78,356,096 cached input, 0 cache writes, 339,638 output)', 81551994);
  assert.equal(codex.cache_read_tokens, 78356096);
});

test('the bot says what a merge is worth, or why it has no dollar value', () => {
  const priced = pr(8, fill('6,753,386 (6,268,161 cache reads, 414,418 cache writes, 1,190 uncached input, 69,617 output)', 'Claude Code with Claude Fable 5.1'));
  const outcome = donations.decide(priced, donations.parseDonation(priced.body), []);
  assert.equal(outcome.row.cache_read_tokens, '6268161');
  assert.equal(outcome.row.usd, '13.3482');
  assert.match(outcome.comment, /worth \$13\.35 at API list prices/);
  const bare = pr(9, fill('1.25M'));
  const plain = donations.decide(bare, donations.parseDonation(bare.body), []);
  assert.equal(plain.row.usd, '');
  assert.match(plain.comment, /No dollar value was recorded/);
});

test('every ledger row with a breakdown adds up to its total', () => {
  for (const r of donations.readLedger()) {
    if (!r.input_tokens) continue;
    const sum = ['input_tokens', 'cache_write_tokens', 'cache_read_tokens', 'output_tokens'].reduce((s, f) => s + Number(r[f]), 0);
    assert.equal(sum, Number(r.tokens), `row ${r.pr || r.label} ${r.agent}`);
    assert.ok(Number(r.usd) > 0, `row ${r.pr || r.label} has a dollar value`);
  }
});

