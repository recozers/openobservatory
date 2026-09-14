/* Open Observatory quarterly detail: map + per-site load band with its evidence. Everything is precomputed into
   data/sites.json (inventory, provenance), data/status.json (evidence kind, plain-language status) and
   data/timeline/<site>.json (quarterly bands, evidence). */
(async function () {
  const fmt = (v, d = 0) => (v === null || v === undefined || Number.isNaN(v)) ? "—" : Number(v).toFixed(d);
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const nc = { cache: "no-cache" };
  const data = await (await fetch("data/sites.json", nc)).json();
  let index = {};
  try { index = await (await fetch("data/timeline/index.json", nc)).json(); } catch (e) { index = {}; }
  let status = {};
  try { (await (await fetch("data/status.json", nc)).json()).sites.forEach(x => { status[x.site_id] = x; }); } catch (e) { status = {}; }
  const sites = data.sites.filter(s => !String(s.site_id).startsWith("ctrl_"));
  document.getElementById("build-note").textContent = `${sites.length} sites · built ${String(data.generated || "").slice(0, 10)}`;

  // evidence kind comes from build_status.py so this page, the landing map and the list agree
  const klass = s => (status[s.site_id] || {}).evidence_kind || "construction";
  const COLOR = { measured: "#c05621", derived: "#f6ad55", detected: "#d69e2e", presumed: "#2b6cb0", construction: "#ffffff" };
  const STROKE = { measured: "#ffffff", derived: "#c05621", detected: "#ffffff", presumed: "#ffffff", construction: "#9a9a95" };
  const KIND_LABEL = { measured: "measured: operator-reported electricity or on-site fuel burning seen from orbit", derived: "derived: annual load from published water use (uncertain ×2)",
    detected: "detected: combustion or energisation signal; load not measured", presumed: "presumed: documented capacity × utilisation prior", construction: "construction, unknown or unconfirmed" };
  const capLabel = b => /water_derived/.test(b || "") ? "water-derived average" : /measured_annual/.test(b || "") && !/hpl/.test(b || "") ? "operator-reported average" : "documented capacity";
  const radius = s => { const ix = index[s.site_id] || {}; const m = ix.est_mid || ((ix.est_lo || 0) + (ix.est_hi || 0)) / 2; return Math.min(22, 5 + 9 * Math.sqrt((m || 0) / 500)); };
  const bandText = s => { const ix = index[s.site_id]; if (!ix) return "no timeline"; return ix.est_hi > 0 ? `${fmt(ix.est_lo, 0)}–${fmt(ix.est_hi, 0)} MW` : "0 MW"; };

  // ---- map
  const style = {
    version: 8,
    sources: {
      countries: { type: "geojson", data: "vendor/ne_110m_admin_0_countries.geojson" },
      osm: { type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256, attribution: "© OpenStreetMap contributors", maxzoom: 19 },
    },
    layers: [
      { id: "bg", type: "background", paint: { "background-color": "#dfe9f0" } },
      { id: "land", type: "fill", source: "countries", paint: { "fill-color": "#f3f1ea" } },
      { id: "borders", type: "line", source: "countries", paint: { "line-color": "#c9c5b8", "line-width": 0.6 } },
      { id: "osm", type: "raster", source: "osm", paint: { "raster-opacity": 0.9 }, layout: { visibility: "visible" } },
    ],
  };
  const map = new maplibregl.Map({ container: "map", style, center: [10, 30], zoom: 1.4, attributionControl: true, maxZoom: 17 });
  map.addControl(new maplibregl.NavigationControl(), "top-left");
  document.getElementById("chk-tiles").addEventListener("change", e => map.setLayoutProperty("osm", "visibility", e.target.checked ? "visible" : "none"));

  const fc = { type: "FeatureCollection", features: sites.map(s => ({ type: "Feature", geometry: { type: "Point", coordinates: [s.lon, s.lat] },
    properties: { site_id: s.site_id, name: s.name, color: COLOR[klass(s)], stroke: STROKE[klass(s)], r: radius(s), band: bandText(s) } })) };
  let layersAdded = false;
  function ensureLayers() {
    if (layersAdded) return;  // a pending/unreachable tile source keeps isStyleLoaded() false forever; just try and retry
    layersAdded = true;
    try {
    map.addSource("sites", { type: "geojson", data: fc });
    map.addLayer({ id: "pts", type: "circle", source: "sites", paint: { "circle-radius": ["get", "r"], "circle-color": ["get", "color"], "circle-stroke-color": ["get", "stroke"], "circle-stroke-width": 2, "circle-opacity": 0.92 } });
    const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 10 });
    map.on("mousemove", "pts", e => { map.getCanvas().style.cursor = "pointer"; const p = e.features[0].properties; popup.setLngLat(e.features[0].geometry.coordinates).setHTML(`<b>${esc(p.name)}</b><br>${esc(p.band)}`).addTo(map); });
    map.on("mouseleave", "pts", () => { map.getCanvas().style.cursor = ""; popup.remove(); });
    map.on("click", "pts", e => openSite(e.features[0].properties.site_id));
    } catch (e) { layersAdded = false; return;  /* style not ready yet: the poll retries */ }
    const h = location.hash.replace("#", "");
    if (h && sites.some(s => s.site_id === h)) openSite(h);
  }
  map.on("load", ensureLayers); map.on("idle", ensureLayers);
  const poll = setInterval(() => { ensureLayers(); if (layersAdded) clearInterval(poll); }, 250);
  window.addEventListener("hashchange", () => { const h = location.hash.replace("#", ""); if (h && sites.some(s => s.site_id === h)) openSite(h); });
  window.__dc = { map, sites, openSite: id => openSite(id) };

  // ---- panel
  const panel = document.getElementById("panel"), body = document.getElementById("panel-body");
  document.getElementById("panel-close").onclick = () => { panel.hidden = true; history.replaceState(null, "", " "); };
  const tlCache = {};
  async function openSite(id) {
    const s = sites.find(x => x.site_id === id);
    if (!s) return;
    location.hash = id; panel.hidden = false;
    map.flyTo({ center: [s.lon, s.lat], zoom: Math.max(map.getZoom(), 4), speed: 1.2 });
    if (!(id in tlCache)) { try { tlCache[id] = await (await fetch(`data/timeline/${id}.json`, nc)).json(); } catch (e) { tlCache[id] = null; } }
    renderPanel(s, tlCache[id]);
  }

  function renderPanel(s, t) {
    const k = klass(s), st = status[s.site_id] || {};
    const tierLabel = { A1: "capacity: regulatory filing or measurement", A2: "capacity: company or utility statement", B: "capacity: inferred from imagery", U: "capacity unknown" }[s.capacity_tier] || "";
    let html = `<h2>${esc(s.name)}</h2><div class="meta">${esc(s.operator)} · ${esc(s.country)} · ${fmt(s.lat, 4)}, ${fmt(s.lon, 4)}</div>`;
    html += `<div class="badges"><span class="badge kind-${esc(k)}">${esc(KIND_LABEL[k] || k)}</span>` +
      (tierLabel ? `<span class="badge">${esc(tierLabel)}</span>` : ``) + (s.polygons && s.polygons.some(p => p.confidence === "low") ? `<span class="badge warn">low-confidence polygons</span>` : ``) +
      (!s.polygons || !s.polygons.length ? `<span class="badge n">no polygons</span>` : ``) + `</div>` +
      (st.running ? `<div class="kv"><div>built</div><div>${esc(st.built)}</div><div>running</div><div>${esc(st.running)}</div><div>load</div><div>${esc(st.load)}</div></div>` : ``);
    html += `<div id="load-section"></div>`;
    html += `<div class="section"><h3>Sources</h3><div class="kv">` +
      `<div>documented capacity</div><div>${s.capacity_mw === null || s.capacity_mw === undefined ? "unknown" : `${fmt(s.capacity_mw, 0)} MW (${esc(s.capacity_basis)})`}</div>` +
      `<div>source</div><div>${esc(s.capacity_source || "—")}${s.capacity_url ? ` <a href="${esc(s.capacity_url)}" target="_blank" rel="noopener">link</a>` : ""}</div>` +
      (s.nox_ef_note ? `<div>NO₂ note</div><div class="small">${esc(s.nox_ef_note)}</div>` : ``) + `</div>` +
      (s.capacity_timeline && s.capacity_timeline.length ? `<table><tr><th>from</th><th>to</th><th>MW</th><th>basis</th><th>tier</th></tr>` + s.capacity_timeline.map(r => `<tr><td>${esc(r.valid_from)}</td><td>${esc(r.valid_to || "—")}</td><td class="num">${fmt(r.capacity_mw, 1)}</td><td>${esc(r.basis)}</td><td>${esc(r.tier)}</td></tr>`).join("") + `</table>` : ``) +
      `<div class="small" style="margin-top:6px"><a href="research/index.html#${esc(s.site_id)}">research view</a>: thermal time series, polygons, frames.</div></div>`;
    body.innerHTML = html;
    renderLoad(s.site_id, t);
    renderWater(t);
  }

  function renderLoad(id, t) {
    const el = document.getElementById("load-section");
    if (!t || !t.quarters || !t.quarters.length) { el.innerHTML = `<div class="section"><h3>Estimated load per quarter</h3><div class="small">No timeline for this site yet.</div></div>`; return; }
    const Q = t.quarters, last = Q[Q.length - 1];
    const hasPlant = Q.some(q => q.campd);
    const maxv = Math.max(1, ...Q.map(q => Math.max(q.est_hi || 0, q.cap_doc_mw || 0)));
    const W = 430, H = 210 + (hasPlant ? 12 : 0), L = 44, R = 8, T = 10, B = 68 + (hasPlant ? 12 : 0), iw = W - L - R, ih = H - T - B, bw = iw / Q.length;
    const y = v => T + ih - (v / maxv) * ih;
    let g = `<line x1="${L}" y1="${y(0)}" x2="${W - R}" y2="${y(0)}" stroke="#999"/>`;
    for (const tick of [0.5, 1].map(f => f * maxv)) g += `<line x1="${L}" y1="${y(tick)}" x2="${W - R}" y2="${y(tick)}" stroke="#eee"/><text x="${L - 4}" y="${y(tick) + 4}" font-size="10" text-anchor="end" fill="#666">${fmt(tick, 0)}</text>`;
    const yb = T + ih + 8;
    Q.forEach((q, i) => {
      const x = L + i * bw;
      if (q.est_hi > 0) g += `<rect x="${x + 1}" y="${y(q.est_hi)}" width="${Math.max(bw - 2, 1)}" height="${Math.max(y(q.est_lo) - y(q.est_hi), 1)}" fill="#bcd4ee"><title>${esc(q.q)}: ${fmt(q.est_lo, 0)}–${fmt(q.est_hi, 0)} MW\n${esc(q.basis)}</title></rect>` +
        (q.est_mid === null || q.est_mid === undefined ? `` : `<line x1="${x + 1}" y1="${y(q.est_mid)}" x2="${x + bw - 1}" y2="${y(q.est_mid)}" stroke="#2b6cb0" stroke-width="2"/>`);
      if (q.cap_doc_mw !== null && q.cap_doc_mw !== undefined) g += `<line x1="${x}" y1="${y(q.cap_doc_mw)}" x2="${x + bw}" y2="${y(q.cap_doc_mw)}" stroke="#1d1d1b" stroke-width="1.5" stroke-dasharray="3 2"><title>${esc(capLabel(q.cap_basis))}: ${fmt(q.cap_doc_mw, 0)} MW (${esc(q.cap_tier)}, ${esc(q.cap_basis)})</title></line>`;
      if (q.no2) { const z = q.no2.z; const c = z === null ? "#ddd" : z > 2 ? "#c53030" : z > 1 ? "#dd6b20" : "#a0aec0"; g += `<rect x="${x + 1}" y="${yb}" width="${Math.max(bw - 2, 1)}" height="7" fill="${c}"><title>${esc(q.q)} NO₂ plume excess ${fmt(q.no2.excess, 2)} (z ${fmt(z, 1)}, n=${q.no2.n})</title></rect>`; }
      if (q.night) { const v = q.night.mean; const c = v > 1 ? "#c53030" : v > 0.5 ? "#dd6b20" : v < -0.5 ? "#2b6cb0" : "#a0aec0"; g += `<rect x="${x + 1}" y="${yb + 9}" width="${Math.max(bw - 2, 1)}" height="7" fill="${c}"><title>${esc(q.q)} night roof ΔT ${fmt(v, 2)} ± ${fmt(q.night.se, 2)} K (n=${q.night.n})</title></rect>`; }
      if (q.halls_roofed) g += `<rect x="${x + 1}" y="${yb + 18}" width="${Math.max(bw - 2, 1)}" height="7" fill="${q.fitted_ha > 0 ? "#2f855a" : "#9ae6b4"}"><title>${esc(q.q)} roofs on: ${q.halls_roofed}/${q.halls_total} halls, ${fmt(q.built_ha, 1)} ha (fitted-out ${fmt(q.fitted_ha, 1)} ha)</title></rect>`;
      if (q.no2_flux) { const v = q.no2_flux.nox_kgh; const c = v > 500 ? "#c53030" : v > 150 ? "#dd6b20" : v > 50 ? "#f6ad55" : "#a0aec0"; g += `<rect x="${x + 1}" y="${yb + 27}" width="${Math.max(bw - 2, 1)}" height="7" fill="${c}"><title>${esc(q.q)} NOx flux ${fmt(v, 0)} ± ${fmt(q.no2_flux.nox_se, 0)} kg/h (${q.no2_flux.n_days} days)</title></rect>`; }
      if (q.campd) { const detail = q.campd.plants.map(p => `${p.name}: ${fmt(p.gross_avg_mw, 0)} MW gross average; ${p.complete ? (p.eligible ? "verified allocation" : "evidence only, not campus load") : "incomplete reporting"}`).join("; "); g += `<rect x="${x + 1}" y="${yb + 36}" width="${Math.max(bw - 2, 1)}" height="7" fill="${q.campd.basis === "dedicated_plant_measured" ? "#c53030" : "#a0aec0"}"><title>${esc(q.q)} CAMPD ${esc(detail)}</title></rect>`; }
      if (i % Math.max(1, Math.round(Q.length / 8)) === 0) g += `<text x="${x + bw / 2}" y="${H - 4}" font-size="9.5" text-anchor="middle" fill="#666">${esc(q.q)}</text>`;
    });
    g += `<text x="${W - R}" y="${yb + 6}" font-size="8.5" text-anchor="end" fill="#666">NO₂</text><text x="${W - R}" y="${yb + 15}" font-size="8.5" text-anchor="end" fill="#666">night ΔT</text><text x="${W - R}" y="${yb + 24}" font-size="8.5" text-anchor="end" fill="#666">roofs</text><text x="${W - R}" y="${yb + 33}" font-size="8.5" text-anchor="end" fill="#666">NOx flux</text>`;
    if (hasPlant) g += `<text x="${W - R}" y="${yb + 42}" font-size="8.5" text-anchor="end" fill="#666">CAMPD</text>`;
    const latestPlant = [...Q].reverse().find(q => q.campd);
    const plantNote = latestPlant ? `<div class="callout small"><b>EPA plant records (${esc(latestPlant.q)})</b>: ${latestPlant.campd.plants.map(p => `<a href="${esc(p.source_url)}" target="_blank" rel="noopener">${esc(p.name)}</a>: ${fmt(p.gross_avg_mw, 0)} MW gross average. ${p.eligible ? "Verified allocated output; IT equivalent assumes PUE and excludes unmeasured losses." : "Evidence only; no verified campus allocation."}`).join(" ")} Missing later quarters are unreported, not zero. Hover over the CAMPD strip for earlier values.</div>` : "";
    const rows = Q.slice(-8).reverse().map(q => `<tr><td>${esc(q.q)}</td><td class="num">${q.est_hi > 0 ? `${fmt(q.est_lo, 0)}–${fmt(q.est_hi, 0)}` : "0"}</td><td class="num">${q.cap_doc_mw === null || q.cap_doc_mw === undefined ? "—" : fmt(q.cap_doc_mw, 0)}</td><td class="num">${q.halls_roofed}/${q.halls_total}</td>` +
      `<td class="num">${q.no2 ? `${fmt(q.no2.excess, 1)}${q.no2.z !== null ? ` (z ${fmt(q.no2.z, 1)})` : ""}` : "—"}</td><td class="num">${q.no2_flux ? fmt(q.no2_flux.nox_kgh, 0) : "—"}</td><td class="num">${q.night ? `${fmt(q.night.mean, 2)}` : "—"}</td></tr>`).join("");
    el.innerHTML = `<div class="section"><h3>Estimated load per quarter</h3>` +
      `<div class="big">${last.est_hi > 0 ? `${fmt(last.est_lo, 0)}–${fmt(last.est_hi, 0)} MW` : /^(not estimated|generator watch)/.test(last.basis || "") ? "not estimated" : "0 MW"} <span class="small">(${esc(last.q)}${last.est_mid === null || last.est_mid === undefined ? "" : `, mid ${fmt(last.est_mid, 0)} MW`})</span></div>` +
      `<div class="small">${esc(last.basis)}.</div>` +
      `<svg class="chart" viewBox="0 0 ${W} ${H}" style="height:${H}px">${g}</svg>` +
      `<div class="small">Band = estimated load; dashed = the figure in force (documented capacity, or an operator-reported or water-derived annual average). Strips: NO₂ plume excess vs pre-change baseline (red = combustion active), night roof ΔT, roofs on (dark green = fitted out), calibrated NOx flux. Hover for values.</div>` +
      plantNote +
      `<table><tr><th>quarter</th><th>est. MW</th><th>figure MW</th><th>roofs</th><th>NO₂ z</th><th>NOx kg/h</th><th>night ΔT</th></tr>${rows}</table>` +
      `<div class="callout small">${esc(t.caveat)}</div></div>`;
  }

  function renderWater(t) {
    const water = (t && t.water_monthly) || [];
    const deliveries = water.filter(r => r.preferred).sort((a, b) => a.month.localeCompare(b.month));
    if (!deliveries.length) return;
    const first = deliveries[0], last = deliveries[deliveries.length - 1];
    const monthIndex = m => Number(m.slice(0, 4)) * 12 + Number(m.slice(5, 7)) - 1;
    const n = monthIndex(last.month) - monthIndex(first.month) + 1;
    const W = 430, H = 105, L = 35, R = 8, T = 12, B = 22, ih = H - T - B, bw = (W - L - R) / n;
    const top = Math.max(1, ...deliveries.map(r => r.volume_ml || 0));
    const y = v => T + ih - v / top * ih;
    let g = `<line x1="${L}" x2="${W - R}" y1="${y(0)}" y2="${y(0)}" stroke="#999"/><text x="${L - 4}" y="${T + 8}" text-anchor="end" font-size="9">${fmt(top, 0)}</text>`;
    deliveries.forEach(r => {
      const x = L + (monthIndex(r.month) - monthIndex(first.month)) * bw;
      if (r.volume_ml !== null) g += `<rect x="${x}" y="${y(r.volume_ml)}" width="${Math.max(bw - 0.6, 0.2)}" height="${Math.max(y(0) - y(r.volume_ml), 1)}" fill="#287e92"><title>${esc(r.month)} municipal delivery: ${fmt(r.volume_ml, 2)} ML (${esc(r.method)}); water evidence, not electricity use</title></rect>`;
      if (r.month.endsWith("-01") && Number(r.month.slice(0, 4)) % 2 === 0) g += `<text x="${x}" y="${H - 5}" font-size="9">${esc(r.month.slice(0, 4))}</text>`;
    });
    const at = (month, metric) => water.find(r => r.month === month && r.metric === metric);
    const cell = (month, metric) => { const r = at(month, metric); return r ? fmt(r.volume_ml, 2) : "—"; };
    const rows = deliveries.slice(-12).reverse().map(r => `<tr><td>${esc(r.month)}</td><td class="num">${fmt(r.volume_ml, 2)}</td><td class="num">${cell(r.month, "campus_purchase")}</td><td class="num">${cell(r.month, "irrigation_transfer_out")}</td><td class="num">${cell(r.month, "river_return")}</td></tr>`).join("");
    document.getElementById("load-section").insertAdjacentHTML("beforeend", `<div class="section"><h3>Water use, monthly</h3><div class="small">Municipal deliveries in megalitres (ML), ${esc(first.month)}–${esc(last.month)}. Latest: ${fmt(last.volume_ml, 2)} ML. Hover for each month.</div><svg class="chart" viewBox="0 0 ${W} ${H}" style="height:${H}px">${g}</svg><p class="small"><a href="${esc(first.source_url)}" target="_blank" rel="noopener">City delivery records</a> · <a href="${esc((water.find(r => r.metric === "campus_purchase") || first).source_url)}" target="_blank" rel="noopener">Customer purchases and returns</a></p><div class="callout small">Water deliveries are not electricity use or net consumption. The city and customer meters differ in some months; they are shown separately and never added together. The source flags meter problems and chiller cleaning in 2020, and a corrected city reading in 2021. Records after ${esc(last.month)} are unavailable, not zero.</div><details><summary>Latest 12 months — all values in ML</summary><table><tr><th>month</th><th>city delivery</th><th>customer purchase</th><th>irrigation out</th><th>river return</th></tr>${rows}</table><div class="small">— means unreported. Return flows do not cover all years or all discharges; no net-consumption estimate is made. The 2022 irrigation series is calculated by the reporting entity.</div></details></div>`);
  }

  // ---- methods
  const modal = document.getElementById("modal"), mbody = document.getElementById("modal-body");
  document.getElementById("modal-close").onclick = () => modal.hidden = true;
  modal.addEventListener("click", e => { if (e.target === modal) modal.hidden = true; });
  document.getElementById("btn-methods").onclick = () => { mbody.innerHTML = methodsHtml(); modal.hidden = false; };
  function methodsHtml() {
    return `<h2>How the numbers are made</h2>
<p>All inputs are free public data: Sentinel-2 (10 m optical), Sentinel-5P TROPOMI (NO₂), ECOSTRESS and Landsat (thermal), ERA5 weather, OpenStreetMap footprints, EPA hourly emissions and eGRID, Epoch AI's data-centre tables. Every number traces to a script in the repository and a polygon with a stated confidence.</p>
<h3>Estimated load</h3>
<p><b>Operator-reported electricity</b> where the operator publishes a campus's annual consumption (Meta, 18 campuses; ORNL Frontier): the year's average load, ±10 %, carried forward at ±30 % until a newer figure appears.</p>
<p><b>Water-derived annual load</b> where an operator publishes per-campus water use but not electricity (Google, 12 campuses): water consumed ÷ the operator's own implied WUE. Checked against Meta's metered electricity, the middle half of mature campuses fall within 0.6–1.6× and individual campuses range from 0.35× to about 3×, so the band is 0.5×–2× and some campuses will fall outside it.</p>
<p><b>NO₂-derived on-site generation</b> where a site burns its own fuel: the NOx emission rate from wind-rotated TROPOMI plumes, calibrated against EPA hourly NOx at the overpass hours of five coal plants, divided by the permit's emission-factor range. It shows when on-site generation starts and how quarterly output changes: quarterly NOx carries about ±20 % statistical uncertainty, single months ±20–50 %, and megawatts are uncertain by 2–3× because turbine emission factors vary. One campus is measured this way (Colossus 2). Of 31 campuses without known on-site generation tested, none showed a plume at 2.5σ, and neither did 62 control points.</p>
<p><b>Documented capacity × a utilisation prior</b> everywhere else: cloud campuses 0.2–0.6 (calibrated on Meta's reported loads against their grid connections), supercomputers 0.4–0.9, AI-training campuses 0.5–1.0 (uncalibrated).</p>
<p><b>Roofs alone give only an upper bound</b> (roofed area × a density prior). No midpoint is shown without an activity signal.</p>
<h3>Evidence strips</h3>
<p>NO₂ plume excess downwind minus upwind against the site's pre-change baseline; night-time roof temperature anomaly (ECOSTRESS); roofs on and fitted out from Sentinel-2 brightness; calibrated NOx flux. Adjacent power plants near the Chinese hubs are shown as an activity index only.</p>
<h3>What is not claimed</h3>
<p>Load or utilisation from thermal: at night, roof temperature showed no step at documented load changes (Rainier +0.06 ± 0.24 K at 1,078 MW; Abilene +0.13 ± 0.47 K at 522 MW); daytime steps coincide with roofing and fit-out and cannot be separated from them. Twelve data centres and nine ordinary roofs were compared. Load at grid-fed sites: not observable from orbit. New structures found by the Sentinel-1 radar scan (the Chinese hub entries named "radar structure") are hall-like by a classifier score, dated by radar, and unconfirmed as data centres.</p>
<p class="small">Details, negative results and code: <code>docs/overnight_report_2026-09-13.md</code>, <code>docs/MVP.md</code>, and the <a href="research/index.html">research view</a>.</p>`;
  }
})();
