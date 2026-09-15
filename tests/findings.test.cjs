const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const load = () => { const context = {}; vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../site/findings.js'), 'utf8'), context); return context.OOFindings; };
const finding = over => ({ subject: 'site_a', subject_type: 'site', subject_name: 'Site A', request: 'RFW-01', request_title: 'Confirm or reject',
  request_anchor: 'rfw-01-confirm-or-reject', answers: 'where', finding: 'Imagery review: unclear.', detail: '', verdict: 'unclear',
  confidence: 'low', period: '', source_url: 'https://github.com/recozers/openobservatory/blob/main/x.png', source_label: 'x.png',
  pull_request: 16, recorded: '2026-09-15', ...over });

test('a site with no findings gets no section', () => {
  const F = load();
  assert.equal(F.section(undefined), '');
  assert.equal(F.section([]), '');
});

test('findings are grouped by question in a fixed order, with request, source and pull request links', () => {
  const F = load();
  const html = F.section([finding({ answers: 'sources', finding: 'Dead link.', verdict: '' }), finding({}), finding({ answers: 'built', finding: 'Radar dates it.', verdict: '', period: '2024-07..2025-01', pull_request: null })]);
  assert.ok(html.indexOf('<h4>Where</h4>') < html.indexOf('<h4>Built</h4>'));
  assert.ok(html.indexOf('<h4>Built</h4>') < html.indexOf('<h4>Sources</h4>'));
  assert.match(html, /3 findings from merged contributions/);
  assert.match(html, /href="requests\.html#rfw-01-confirm-or-reject"/);
  assert.match(html, /href="https:\/\/github\.com\/recozers\/openobservatory\/pull\/16"/);
  assert.match(html, /2024-07 to 2025-01/);
  assert.equal((html.match(/pull request 16/g) || []).length, 2);
});

test('pages below the site root link back up, and the findings page names the subject', () => {
  const F = load();
  assert.match(F.section([finding({})], '../'), /href="\.\.\/requests\.html#/);
  assert.match(F.item(finding({}), '', true), /<a href="map\.html#site_a">Site A<\/a>/);
  assert.match(F.item(finding({ subject: 'global', subject_type: 'global', subject_name: 'All sites' }), '', true), /All sites · /);
});

test('contributed text is escaped', () => {
  const F = load();
  const html = F.section([finding({ finding: '<img src=x onerror=alert(1)>', detail: '"quoted" & <b>', source_label: '<script>' })]);
  assert.ok(!html.includes('<img') && !html.includes('<script>') && !html.includes('<b>'));
  assert.match(html, /&lt;img src=x onerror=alert\(1\)&gt;/);
});
