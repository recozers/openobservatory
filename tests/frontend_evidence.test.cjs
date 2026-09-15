const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = name => fs.readFileSync(path.join(__dirname, '../site', name), 'utf8');
const fixture = (kind, i = 0) => ({ site_id: kind, name: kind, evidence_kind: kind, operator: 'Example', country: 'US',
  lat: 30 + i, lon: -100 + i * 40, series: [], how: [], est_hi: 100, est_mid: 50, running: 'unknown', confidence: 'low' });
const elements = () => Object.fromEntries(['sort', 'hide-hubs', 'evidence', 'cards', 'result-count', 'build-note', 'legend', 'chk-tiles', 'panel', 'panel-body', 'panel-close'].map(id => [id, {
  value: id === 'sort' ? 'default' : 'all', checked: true, offsetHeight: 180, listeners: {},
  addEventListener(event, fn) { this.listeners[event] = fn; }
}]));
const runtime = (sites, els) => ({ document: { getElementById: id => els[id] },
  fetch: async () => ({ json: async () => ({ sites, generated: '2026-09-14' }) }) });

test('list filters all kinds, composes with hub filter and preserves sorting', async () => {
  const kinds = ['construction', 'presumed', 'detected', 'derived', 'measured'];
  const sites = kinds.map(fixture);
  sites.push({ ...fixture('measured'), site_id: 'example_hub', name: 'Hidden hub' });
  const els = elements();
  await vm.runInNewContext(source('cards.js'), runtime(sites, els));
  assert.match(els['result-count'].textContent, /^5 of 6/);
  assert.ok(els.cards.innerHTML.indexOf('data-evidence-kind="measured"') < els.cards.innerHTML.indexOf('data-evidence-kind="presumed"'));
  for (const kind of kinds) {
    els.evidence.value = kind; els.evidence.listeners.change();
    assert.deepEqual([...els.cards.innerHTML.matchAll(/data-evidence-kind="(\w+)"/g)].map(m => m[1]), [kind]);
  }
  els.evidence.value = 'measured'; els['hide-hubs'].checked = false; els['hide-hubs'].listeners.change();
  assert.match(els['result-count'].textContent, /^2 of 6/);
  els.sort.value = 'name'; els.sort.listeners.change();
  assert.ok(els.cards.innerHTML.indexOf('Hidden hub') < els.cards.innerHTML.indexOf('<h2>measured'));
});

test('cards count findings from requests for work and link to the quarterly detail', async () => {
  const els = elements();
  await vm.runInNewContext(source('cards.js'), runtime([{ ...fixture('construction'), findings: { n: 2, requests: ['RFW-01', 'RFW-03'] } }, fixture('presumed', 1)], els));
  assert.match(els.cards.innerHTML, /2 findings \(RFW-01, RFW-03\), <a href="map\.html#construction">read them<\/a>/);
  assert.equal((els.cards.innerHTML.match(/From requests for work/g) || []).length, 1);
});

test('empty results and unknown kinds remain explicit and escaped', async () => {
  const els = elements();
  await vm.runInNewContext(source('cards.js'), runtime([{ ...fixture(null), name: '<script>alert(1)</script>' }], els));
  assert.match(els.cards.innerHTML, /data-evidence-kind="construction"/);
  assert.ok(!els.cards.innerHTML.includes('<script>'));
  els.evidence.value = 'measured'; els.evidence.listeners.change();
  assert.match(els.cards.innerHTML, /No sites match/);
  assert.match(els['result-count'].textContent, /^0 of 1/);
});

async function mapRuntime(sites, hash = '', legendPosition = 'absolute') {
  const els = elements();
  let map;
  class Map {
    constructor(options) { map = this; this.options = options; this.events = {}; this.fits = []; this.flights = []; }
    addControl() {} addSource(id, source) { this.source = source; } addLayer() {}
    on(name, ...args) { this.events[name] = args.at(-1); }
    fitBounds(bounds, options) { this.fits.push({ bounds, options }); }
    getZoom() { return 1; } flyTo(options) { this.flights.push(options); }
  }
  class Bounds { constructor() { this.points = []; } extend(point) { this.points.push(point); } }
  const context = { ...runtime(sites, els), maplibregl: { Map, LngLatBounds: Bounds, NavigationControl: class {}, Popup: class {} },
    getComputedStyle: () => ({ position: legendPosition }),
    location: { hash }, history: { replaceState() {} }, window: { addEventListener() {} }, setInterval() { return 1; }, clearInterval() {} };
  await vm.runInNewContext(source('mapmin.js'), context);
  map.events.load(); map.events.idle();
  return map;
}

test('default map fits every displayed coordinate once and reserves legend space', async () => {
  const sites = ['measured', 'derived', 'detected', 'presumed', 'construction'].map(fixture);
  sites.push({ ...fixture('bad'), lat: null }, { ...fixture('hub'), site_id: 'example_hub' });
  const map = await mapRuntime(sites);
  assert.equal(map.fits.length, 1);
  assert.deepEqual(JSON.parse(JSON.stringify(map.fits[0].bounds.points)), sites.slice(0, 5).map(s => [s.lon, s.lat]));
  assert.equal(map.fits[0].options.padding.bottom, 228);
  assert.equal(map.fits[0].options.duration, 0);
  assert.equal(map.fits[0].options.maxZoom, 5);
  assert.equal(new Set(map.source.data.features.map(f => f.properties.color)).size, 5);
  assert.equal((await mapRuntime(sites, '', 'static')).fits[0].options.padding.bottom, 32);
});

test('deep link keeps selected view; invalid hash and empty inventory are safe', async () => {
  const selected = await mapRuntime([fixture('measured')], '#measured');
  assert.equal(selected.fits.length, 0);
  assert.equal(selected.flights.length, 1);
  assert.equal((await mapRuntime([fixture('measured')], '#missing')).fits.length, 1);
  assert.equal((await mapRuntime([])).fits.length, 0);
});

test('generator watch renders signed bars and contained uncertainty without a false orange bar', async () => {
  const s = { ...fixture('construction'), key: 'generator_watch',
    series: [{ x: '2026-01', y: -300, se: 100 }, { x: '2026-02', y: 150, se: 100 }],
    sources: [{label: 'Permit', url: 'https://example.org/permit'}] };
  const els = elements();
  await vm.runInNewContext(source('cards.js'), runtime([s], els));
  assert.match(els.cards.innerHTML, /2026-01: -300/);
  assert.match(els.cards.innerHTML, /href="https:\/\/example.org\/permit"/);
  const svg = els.cards.innerHTML.match(/<svg[\s\S]*?<\/svg>/)[0];
  assert.ok(!svg.includes('#dd6b20'));
  for (const m of svg.matchAll(/\by[12]?="([\d.-]+)"/g)) assert.ok(+m[1] >= 0 && +m[1] <= 80);
  const heights = [...svg.matchAll(/\bheight="([\d.]+)"/g)].map(m => +m[1]);
  assert.ok(heights.every(h => h > 1));
});
