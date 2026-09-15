/* Static frontend: everything is precomputed into data/sites.json and data/obs/<site>.json; findings from requests for
   work come from data/evidence.json and are drawn by ../findings.js. */
(async function () {
  const fmt = (v, d = 0) => (v === null || v === undefined || Number.isNaN(v)) ? "—" : Number(v).toFixed(d);
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const CASE_COLOR = { utilisation_identified: "#2b6cb0", q_only: "#dd6b20", unvalidated_transfer: "#805ad5", measured_not_identified: "#4a5568", no_data: "#ffffff" };
  const CASE_LABEL = { utilisation_identified: "utilisation identified", q_only: "Q̂ only — capacity not independently known", unvalidated_transfer: "unvalidated domain transfer",
    measured_not_identified: "ΔT measured, but Q̂ not identified (fitted slope indistinguishable from zero)", no_data: "no thermal observations in this build" };
  const BIN_RADIUS = { "no estimate": 5, "< 5 MW": 6, "5–15 MW": 8, "15–50 MW": 10, "50–150 MW": 13, "150–500 MW": 17, "> 500 MW": 22 };
  const FRAME_RADIUS = { "none": 5, "< 30 frames": 7, "30–100 frames": 10, "> 100 frames": 14 };
  const HALO_EXTRA = { "unbounded": 0, "narrow (< 2×)": 3, "moderate (2–4×)": 6, "wide (4–10×)": 10, "very wide (> 10×)": 16 };

  const data = await (await fetch("../data/sites.json", { cache: "no-cache" })).json();
  const sites = data.sites.filter(s => !String(s.site_id).startsWith("ctrl_"));  // control roofs stay in the data files but are not data centres
  const F = window.OOFindings;
  let findings = {};
  try { findings = F ? F.bySubject(await (await fetch("../data/evidence.json", { cache: "no-cache" })).json()) : {}; } catch (e) { findings = {}; }
  const model = data.model || {};
  document.getElementById("build-note").textContent = data.extract_meta && data.extract_meta.backend
    ? `thermal backend: ${data.extract_meta.backend} (${data.extract_meta.start} → ${data.extract_meta.end}), ${data.extract_meta.n_obs} observations, ${data.extract_meta.n_rej} rejections`
    : "no extraction metadata";
  document.getElementById("legend-bins").textContent = (data.q_bins || []).join(" · ");

  // ---- verdict banner
  const v = document.getElementById("verdict");
  if (model.kill_conditions) {
    const k = model.kill_conditions;
    const neg = k.verdict === "negative_result";
    v.hidden = false;
    v.className = "verdict " + (neg ? "negative" : "positive");
    const l = model.loso || {};
    const th = l.thermal || {};
    const thermalTxt = th.median_factor === null || th.median_factor === undefined ? `not identified in ${th.n_unidentified}/${th.n_sites} folds` : `${fmt(th.median_factor, 2)}× (${th.n_unidentified}/${th.n_sites} folds not identified)`;
    v.innerHTML = `<b>${neg ? "Negative result so far." : "Thermal channel shows information beyond geometry (on this small set)."}</b> ` +
      `Fit on <span class="num">${model.n_sites_tier_a}</span> Tier A sites / <span class="num">${model.n_frames_tier_a}</span> frames (${esc(model.ptype)} polygons). ` +
      `Slope of ΔT on capacity density: <span class="num">${fmt(model.slope && model.slope.value, 4)} ± ${fmt(model.slope && model.slope.se, 4)}</span> ${esc(model.slope && model.slope.units)}. ` +
      `Leave-one-site-out median factor error: thermal <span class="num">${thermalTxt}</span>, geometry baseline <span class="num">${fmt(l.geometry && l.geometry.median_factor, 2)}×</span>, constant <span class="num">${fmt(l.constant && l.constant.median_factor, 2)}×</span>. ` +
      `Kill 1 (LOSO not better than geometry): <b>${k.loso_not_better_than_geometry_baseline}</b>; kill 2 (weather explains more variance than capacity): <b>${k.met_explains_more_than_capacity}</b>. See “Model results”.`;
  } else if (model.status) {
    v.hidden = false; v.textContent = `Model status: ${model.status}`;
  }

  // ---- map
  const style = {
    version: 8,
    sources: {
      countries: { type: "geojson", data: "../vendor/ne_110m_admin_0_countries.geojson" },
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

  const fc = {
    type: "FeatureCollection",
    features: sites.map(s => ({
      type: "Feature", geometry: { type: "Point", coordinates: [s.lon, s.lat] },
      properties: { site_id: s.site_id, name: s.name, case: s.case, color: CASE_COLOR[s.case] || "#999",
        r: s.case === "measured_not_identified" ? (FRAME_RADIUS[s.frames_bin] || 5) : (BIN_RADIUS[s.q_bin] || 5),
        halo: s.case === "measured_not_identified" ? (FRAME_RADIUS[s.frames_bin] || 5) : (BIN_RADIUS[s.q_bin] || 5) + (HALO_EXTRA[s.interval_class] || 0),
        stroke: s.case === "no_data" ? "#8a8a85" : (s.case === "unvalidated_transfer" ? "#805ad5" : "#ffffff"),
        q: s.q_hat_mw === null || s.q_hat_mw === undefined
          ? (s.n_frames ? `not identified · mean ΔT ${fmt(s.mean_delta_t_k, 2)} K over ${s.n_frames} frames` : "no estimate")
          : `${fmt(s.q_hat_mw, 0)} MW (${fmt(s.q_lo_mw, 0)}–${fmt(s.q_hi_mw, 0)})` },
    })),
  };
  let layersAdded = false;
  function ensureLayers() {
    if (layersAdded || !map.isStyleLoaded()) return;
    layersAdded = true;
    try {
      map.addSource("sites", { type: "geojson", data: fc });
      map.addLayer({ id: "halo", type: "circle", source: "sites", paint: { "circle-radius": ["get", "halo"], "circle-color": ["get", "color"], "circle-opacity": 0.18, "circle-stroke-color": ["get", "color"], "circle-stroke-width": 1, "circle-stroke-opacity": 0.35 } });
      map.addLayer({ id: "pts", type: "circle", source: "sites", paint: { "circle-radius": ["get", "r"], "circle-color": ["get", "color"], "circle-stroke-color": ["get", "stroke"], "circle-stroke-width": 2 } });
      const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 10 });
      map.on("mousemove", "pts", e => {
        map.getCanvas().style.cursor = "pointer";
        const p = e.features[0].properties;
        popup.setLngLat(e.features[0].geometry.coordinates).setHTML(`<b>${esc(p.name)}</b><br>Q̂ ${esc(p.q)}<br><span style="color:#666">${esc(CASE_LABEL[p.case] || p.case)}</span>`).addTo(map);
      });
      map.on("mouseleave", "pts", () => { map.getCanvas().style.cursor = ""; popup.remove(); });
      map.on("click", "pts", e => openSite(e.features[0].properties.site_id));
    } catch (e) {
      console.error("layer setup failed", e);
      window.__dcErr = String(e);
    }
    // deep link
    const h = location.hash.replace("#", "");
    if (h && sites.some(s => s.site_id === h)) openSite(h);
  }
  // 'load'/'idle' can be delayed indefinitely while offline basemap tiles keep failing, so poll the
  // style state as well; ensureLayers is idempotent, so the layers are added exactly once either way.
  map.on("load", ensureLayers);
  map.on("idle", ensureLayers);
  const poll = setInterval(() => { ensureLayers(); if (layersAdded) clearInterval(poll); }, 250);
  window.addEventListener("hashchange", () => {
    const h = location.hash.replace("#", "");
    if (h && sites.some(s => s.site_id === h)) openSite(h);
  });
  window.__dc = { map, sites, openSite: id => openSite(id) };  // debugging / render checks

  // ---- site panel
  const panel = document.getElementById("panel"), body = document.getElementById("panel-body");
  document.getElementById("panel-close").onclick = () => { panel.hidden = true; history.replaceState(null, "", " "); };
  const obsCache = {};
  async function openSite(id) {
    const s = sites.find(x => x.site_id === id);
    if (!s) return;
    location.hash = id;
    panel.hidden = false;
    map.flyTo({ center: [s.lon, s.lat], zoom: Math.max(map.getZoom(), 4), speed: 1.2 });
    if (!obsCache[id]) { try { obsCache[id] = await (await fetch(`../data/obs/${id}.json`, { cache: "no-cache" })).json(); } catch (e) { obsCache[id] = { frames: [], rejections: [] }; } }
    renderPanel(s, obsCache[id]);
  }

  function renderPanel(s, obs) {
    const cls = { utilisation_identified: "u", q_only: "q", unvalidated_transfer: "t", measured_not_identified: "m", no_data: "n" }[s.case] || "n";
    const tierLabel = { A1: "Tier A1 — regulatory filing / independent measurement", A2: "Tier A2 — company or utility statement (design/grid figure)", B: "Tier B — inferred from imagery", U: "capacity unknown" }[s.capacity_tier] || s.capacity_tier;
    const pue0 = s.pue_assumed || 1.2;
    const capTotal = (pue) => s.capacity_mw === null || s.capacity_mw === undefined ? null : (["facility_design", "grid_connection"].includes(s.capacity_basis) ? s.capacity_mw : s.capacity_mw * pue);
    let html = `<h2>${esc(s.name)}</h2><div class="meta">${esc(s.operator)} · ${esc(s.country)} · ${fmt(s.lat, 4)}, ${fmt(s.lon, 4)} · cooling: ${esc(s.cooling_arch)}</div>`;
    html += `<div class="badges"><span class="badge ${cls}">${esc(CASE_LABEL[s.case])}</span><span class="badge">${esc(tierLabel)}</span>` +
      (s.in_training_set ? `<span class="badge">in Tier A fit</span>` : ``) +
      (s.thermal_backend === "gee" && !s.n_frames ? `<span class="badge warn">no thermal frames yet (post-2021 site)</span>` : ``) +
      (s.polygons.some(p => p.confidence === "low") ? `<span class="badge warn">low-confidence polygon</span>` : ``) +
      (s.coords_quality === "approximate" ? `<span class="badge warn">coordinates approximate (hub centroid)</span>` : ``) +
      (s.polygons.length === 0 ? `<span class="badge n">no polygons digitised</span>` : ``) + `</div>`;
    if (s.transfer_note) html += `<div class="callout ${s.case === "unvalidated_transfer" ? "red" : ""}">${esc(s.transfer_note)}</div>`;
    html += `<div id="load-section"></div>`;
    html += F ? F.section(findings[s.site_id], "../") : "";

    // Q̂ / U block
    html += `<div class="section"><h3>Implied heat rejection Q̂</h3>`;
    if (s.q_hat_mw !== null && s.q_hat_mw !== undefined) {
      html += `<div class="big">${fmt(s.q_hat_mw, 0)} MW <span class="small">(5–95 %: ${fmt(s.q_lo_mw, 0)} – ${fmt(s.q_hi_mw, 0)} MW; bin: ${esc(s.q_bin)}; interval ${esc(s.interval_class)})</span></div>` +
        `<div class="small">Q̂ ≈ implied IT-equivalent power × PUE. Implied IT-equivalent: ${fmt(s.it_hat_mw, 1)} MW (${fmt(s.it_lo_mw, 1)}–${fmt(s.it_hi_mw, 1)}). Mean ΔT over ${s.n_frames} frames: ${fmt(s.mean_delta_t_k, 2)} K (sd ${fmt(s.sd_delta_t_k, 2)} K), roof area ${fmt(s.area_ha, 1)} ha.</div>` +
        `<div class="controls"><label>assumed PUE <input type="number" id="pue" step="0.05" min="1" max="2.5" value="${pue0}"></label><span class="small" id="pue-note"></span></div>`;
      if (s.case === "utilisation_identified") {
        html += `<div id="u-block"></div>`;
      } else {
        html += `<div class="callout">Utilisation is <b>not identified</b> here: thermal data give a proxy for capacity × utilisation only. Without an independently documented capacity the two cannot be separated, so this site reports Q̂ only.</div>`;
      }
    } else if (s.case === "measured_not_identified") {
      html += `<div class="big">not identified</div><div class="small">Mean ΔT over ${s.n_frames} frames: <b>${fmt(s.mean_delta_t_k, 2)} K</b> (sd ${fmt(s.sd_delta_t_k, 2)} K), roof area ${fmt(s.area_ha, 1)} ha.</div>` +
        `<div class="callout red">The Tier A fit gives a ΔT–capacity slope that is indistinguishable from zero, so inverting this site's ΔT into a heat-rejection figure would produce an unbounded number. The measurement is shown; the estimate is not. See “Model results”.</div>`;
    } else {
      html += `<div class="small">No estimate. ${s.n_frames ? "Frames exist but the cross-site relation is not identified (see the overnight report in docs/)." : "No usable frames or no polygons yet."}</div>`;
    }
    html += `</div>`;

    // capacity provenance
    html += `<div class="section"><h3>Capacity provenance</h3><div class="kv">` +
      `<div>documented capacity</div><div>${s.capacity_mw === null || s.capacity_mw === undefined ? "unknown" : `${fmt(s.capacity_mw, 1)} MW (${esc(s.capacity_basis)})`}</div>` +
      `<div>tier</div><div>${esc(tierLabel)}</div>` +
      `<div>source</div><div>${esc(s.capacity_source || "—")}${s.capacity_url ? ` <a href="${esc(s.capacity_url)}" target="_blank" rel="noopener">link</a>` : ""}</div>` +
      `<div>in Epoch AI database</div><div>${esc(s.in_epoch_db || "unknown")}</div></div>`;
    if (s.capacity_timeline && s.capacity_timeline.length) {
      html += `<table><tr><th>from</th><th>to</th><th>MW</th><th>basis</th><th>tier</th></tr>` + s.capacity_timeline.map(t => `<tr><td>${esc(t.valid_from)}</td><td>${esc(t.valid_to || "—")}</td><td class="num">${fmt(t.capacity_mw, 1)}</td><td>${esc(t.basis)}</td><td>${esc(t.tier)}</td></tr>`).join("") + `</table>`;
    }
    html += `</div>`;

    // chart
    const ptypes = [...new Set(obs.frames.map(f => f.ptype))];
    html += `<div class="section"><h3>ΔT time series</h3>`;
    if (obs.frames.length) {
      html += `<div class="controls">` + ptypes.map(p => `<label><input type="checkbox" class="pt-chk" value="${esc(p)}" ${p === "hall" || ptypes.length === 1 ? "checked" : ""}> ${esc(p)}</label>`).join("") +
        `<label><input type="checkbox" id="met-ta"> air temp</label><label><input type="checkbox" id="met-wind"> wind</label><label><input type="checkbox" id="met-tw"> wet-bulb</label></div>` +
        `<svg class="chart" id="chart"></svg><div class="small">Each point is one acquisition (hover for date, sensor, pixel counts and ERA5 covariates). ΔT = polygon mean − background annulus mean, in K.</div>`;
    } else {
      html += `<div class="small">No accepted frames.</div>`;
    }
    html += `</div>`;

    // frames / rejections
    const rr = Object.entries(s.rejection_reasons || {}).map(([k, n]) => `${esc(k)}: ${n}`).join(", ");
    html += `<div class="section"><h3>Frames</h3><div class="kv"><div>acquisitions used</div><div class="num">${s.n_frames}</div><div>acquisitions rejected</div><div class="num">${s.n_rejected_frames} ${rr ? `<span class="small">(${rr})</span>` : ""}</div><div>observation window</div><div>${esc(s.obs_start)} → ${esc(s.obs_end)}</div></div></div>`;

    // polygons
    html += `<div class="section"><h3>Polygons</h3><table><tr><th>name</th><th>type</th><th>area (ha)</th><th>confidence</th><th>valid from</th></tr>` +
      s.polygons.map(p => `<tr><td>${esc(p.name)}</td><td>${esc(p.ptype)}</td><td class="num">${fmt(p.area_ha, 1)}</td><td>${esc(p.confidence)}</td><td>${esc(p.valid_from || "—")}</td></tr>`).join("") + `</table>` +
      s.polygons.filter(p => p.note).map(p => `<div class="small">${esc(p.name)}: ${esc(p.note)}</div>`).join("") + `</div>`;
    if (s.notes) html += `<div class="section"><h3>Notes</h3><div class="small">${esc(s.notes)}</div></div>`;
    body.innerHTML = html;
    renderLoad(s.site_id);

    // PUE leverage
    const pueInput = document.getElementById("pue");
    function updateU() {
      const pue = pueInput ? parseFloat(pueInput.value) || pue0 : pue0;
      const q = s.it_hat_mw * pue, qlo = s.it_lo_mw * pue, qhi = s.it_hi_mw * pue;
      const note = document.getElementById("pue-note");
      if (note) note.textContent = `→ Q̂ = ${fmt(q, 0)} MW (${fmt(qlo, 0)}–${fmt(qhi, 0)})`;
      const ub = document.getElementById("u-block");
      if (ub) {
        const ct = capTotal(pue);
        const u = ct ? q / ct : null, ulo = ct ? qlo / ct : null, uhi = ct ? qhi / ct : null;
        ub.innerHTML = `<div class="big">U = ${fmt(u, 2)} <span class="small">(${fmt(ulo, 2)} – ${fmt(uhi, 2)})</span></div>` +
          `<div class="small">U = Q̂ / (C × PUE) with C = ${fmt(s.capacity_mw, 1)} MW (${esc(s.capacity_basis)}${["facility_design", "grid_connection"].includes(s.capacity_basis) ? ", already a total figure so PUE cancels only on the Q̂ side" : ", an IT figure, so the PUE assumption cancels in U"}). Values far outside 0–1.2 mean the fitted relation, the polygon, or the documented capacity is wrong for this site — that is the point of showing it.</div>`;
      }
    }
    if (pueInput) { pueInput.addEventListener("input", updateU); updateU(); }

    // chart wiring
    const svg = document.getElementById("chart");
    if (svg) {
      const redraw = () => drawChart(svg, obs.frames, [...document.querySelectorAll(".pt-chk:checked")].map(e => e.value),
        { ta: document.getElementById("met-ta").checked, wind: document.getElementById("met-wind").checked, tw: document.getElementById("met-tw").checked });
      document.querySelectorAll(".pt-chk, #met-ta, #met-wind, #met-tw").forEach(e => e.addEventListener("change", redraw));
      redraw();
    }
  }

  // ---- estimated load per quarter (assumption-based; evidence shown alongside)
  const tlCache = {};
  async function renderLoad(id) {
    const el = document.getElementById("load-section");
    if (!el) return;
    if (!(id in tlCache)) { try { tlCache[id] = await (await fetch(`../data/timeline/${id}.json`, { cache: "no-cache" })).json(); } catch (e) { tlCache[id] = null; } }
    const t = tlCache[id];
    if (!t || !t.quarters || !t.quarters.length) { el.innerHTML = `<div class="section"><h3>Estimated load per quarter</h3><div class="small">No timeline built for this site yet.</div></div>`; return; }
    const Q = t.quarters, last = Q[Q.length - 1];
    const maxv = Math.max(1, ...Q.map(q => Math.max(q.est_hi || 0, q.cap_doc_mw || 0)));
    const W = 430, H = 210, L = 44, R = 8, T = 10, B = 68, iw = W - L - R, ih = H - T - B, bw = iw / Q.length;
    const y = v => T + ih - (v / maxv) * ih;
    let g = `<line x1="${L}" y1="${y(0)}" x2="${W - R}" y2="${y(0)}" stroke="#999"/>`;
    for (const tick of [0.5, 1].map(f => f * maxv)) g += `<line x1="${L}" y1="${y(tick)}" x2="${W - R}" y2="${y(tick)}" stroke="#eee"/><text x="${L - 4}" y="${y(tick) + 4}" font-size="10" text-anchor="end" fill="#666">${fmt(tick, 0)}</text>`;
    Q.forEach((q, i) => {
      const x = L + i * bw;
      if (q.est_hi > 0) g += `<rect x="${x + 1}" y="${y(q.est_hi)}" width="${Math.max(bw - 2, 1)}" height="${Math.max(y(q.est_lo) - y(q.est_hi), 1)}" fill="#bcd4ee"><title>${esc(q.q)}: estimated load ${fmt(q.est_lo, 0)}–${fmt(q.est_hi, 0)} MW (mid ${fmt(q.est_mid, 0)})\n${esc(q.basis)}</title></rect>` +
        (q.est_mid === null || q.est_mid === undefined ? `` : `<line x1="${x + 1}" y1="${y(q.est_mid)}" x2="${x + bw - 1}" y2="${y(q.est_mid)}" stroke="#2b6cb0" stroke-width="2"/>`);
      if (q.cap_doc_mw !== null && q.cap_doc_mw !== undefined) g += `<line x1="${x}" y1="${y(q.cap_doc_mw)}" x2="${x + bw}" y2="${y(q.cap_doc_mw)}" stroke="#1d1d1b" stroke-width="1.5" stroke-dasharray="3 2"><title>documented capacity in force: ${fmt(q.cap_doc_mw, 0)} MW (${esc(q.cap_tier)})</title></line>`;
      // evidence strips
      const yb = T + ih + 8;
      if (q.no2) { const z = q.no2.z; const c = z === null ? "#ddd" : z > 2 ? "#c53030" : z > 1 ? "#dd6b20" : "#a0aec0"; g += `<rect x="${x + 1}" y="${yb}" width="${Math.max(bw - 2, 1)}" height="7" fill="${c}"><title>${esc(q.q)} NO2 downwind excess ${fmt(q.no2.excess, 2)} (z vs pre-change ${fmt(z, 1)}, n=${q.no2.n})</title></rect>`; }
      if (q.night) { const v = q.night.mean; const c = v > 1 ? "#c53030" : v > 0.5 ? "#dd6b20" : v < -0.5 ? "#2b6cb0" : "#a0aec0"; g += `<rect x="${x + 1}" y="${yb + 9}" width="${Math.max(bw - 2, 1)}" height="7" fill="${c}"><title>${esc(q.q)} night roof ΔT ${fmt(v, 2)} K ± ${fmt(q.night.se, 2)} (n=${q.night.n})</title></rect>`; }
      if (q.no2_flux) { const v = q.no2_flux.nox_kgh; const c = v > 500 ? "#c53030" : v > 150 ? "#dd6b20" : v > 50 ? "#f6ad55" : "#a0aec0"; g += `<rect x="${x + 1}" y="${yb + 27}" width="${Math.max(bw - 2, 1)}" height="7" fill="${c}"><title>${esc(q.q)} NOx flux ${fmt(v, 0)} ± ${fmt(q.no2_flux.nox_se, 0)} kg/h (TROPOMI, calibrated; ${q.no2_flux.n_days} days)</title></rect>`; }
      if (q.halls_roofed) g += `<rect x="${x + 1}" y="${yb + 18}" width="${Math.max(bw - 2, 1)}" height="7" fill="${q.fitted_ha > 0 ? "#2f855a" : "#9ae6b4"}"><title>${esc(q.q)} roofs on: ${q.halls_roofed}/${q.halls_total} halls, ${fmt(q.built_ha, 1)} ha (fitted-out ${fmt(q.fitted_ha, 1)} ha)</title></rect>`;
      if (i % Math.max(1, Math.round(Q.length / 8)) === 0) g += `<text x="${x + bw / 2}" y="${H - 4}" font-size="9.5" text-anchor="middle" fill="#666">${esc(q.q)}</text>`;
    });
    const yb = T + ih + 8;
    g += `<text x="${W - R}" y="${yb + 6}" font-size="8.5" text-anchor="end" fill="#666">NO₂</text><text x="${W - R}" y="${yb + 15}" font-size="8.5" text-anchor="end" fill="#666">night ΔT</text><text x="${W - R}" y="${yb + 24}" font-size="8.5" text-anchor="end" fill="#666">roofs</text><text x="${W - R}" y="${yb + 33}" font-size="8.5" text-anchor="end" fill="#666">NOx flux</text>`;
    const rows = Q.slice(-8).reverse().map(q => `<tr><td>${esc(q.q)}</td><td class="num">${q.est_hi > 0 ? `${fmt(q.est_lo, 0)}–${fmt(q.est_hi, 0)}` : "0"}</td><td class="num">${q.cap_doc_mw === null || q.cap_doc_mw === undefined ? "—" : fmt(q.cap_doc_mw, 0)}</td><td class="num">${q.halls_roofed}/${q.halls_total}</td>` +
      `<td class="num">${q.no2 ? `${fmt(q.no2.excess, 1)}${q.no2.z !== null ? ` (z ${fmt(q.no2.z, 1)})` : ""}` : "—"}</td><td class="num">${q.night ? `${fmt(q.night.mean, 2)}±${fmt(q.night.se, 2)}` : "—"}</td><td class="num">${q.day ? fmt(q.day.mean, 2) : "—"}</td></tr>`).join("");
    el.innerHTML = `<div class="section"><h3>Estimated load per quarter</h3>` +
      `<div class="big">${last.est_hi > 0 ? `${fmt(last.est_lo, 0)}–${fmt(last.est_hi, 0)} MW` : "0 MW"} <span class="small">(${esc(last.q)}${last.est_mid === null || last.est_mid === undefined ? ", no midpoint: no operating evidence" : `, mid ${fmt(last.est_mid, 0)} MW`})</span></div>` +
      `<div class="small">${esc(last.basis)}. Density prior ${fmt(t.density_mw_per_ha, 1)} MW/ha (${esc(t.density_basis)}); hall roof area ${fmt(t.hall_area_ha, 1)} ha.</div>` +
      `<svg class="chart" viewBox="0 0 ${W} ${H}" style="height:${H}px">${g}</svg>` +
      `<div class="small">Bars: estimated load band (light) and mid estimate (blue); dashed: documented capacity in force. Strips: NO₂ plume excess vs pre-change baseline (red z&gt;2 = combustion active), night roof ΔT, roofs on (dark green = fitted-out ≥6 months). Hover for values.</div>` +
      `<table><tr><th>quarter</th><th>est. MW</th><th>doc. MW</th><th>roofs</th><th>NO₂ excess</th><th>night ΔT K</th><th>day ΔT K</th></tr>${rows}</table>` +
      `<div class="callout">${esc(t.caveat)}</div>` +
      `<div class="small">Evidence available: Sentinel-2 roofs ${t.s2_available ? "yes" : "no"}; NO₂ plume test ${t.no2_available ? "yes" : "no"}; ECOSTRESS night ${t.thermal_night_available ? "yes" : "no"}; Landsat day ${t.thermal_day_available ? "yes" : "no"}.</div></div>`;
  }

  // ---- SVG chart
  let tip = null;
  function drawChart(svg, frames, ptypes, met) {
    const W = svg.clientWidth || 420, H = 230, m = { l: 36, r: 36, t: 10, b: 28 };
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    const pts = frames.filter(f => ptypes.includes(f.ptype));
    const ts = pts.map(f => Date.parse(f.t));
    const allT = frames.map(f => Date.parse(f.t));
    const x0 = Math.min(...allT), x1 = Math.max(...allT);
    const ys = pts.map(f => f.dt);
    const y0 = Math.min(-1, ...ys) - 0.5, y1 = Math.max(1, ...ys) + 0.5;
    const X = t => m.l + (t - x0) / Math.max(1, x1 - x0) * (W - m.l - m.r);
    const Y = y => m.t + (y1 - y) / (y1 - y0) * (H - m.t - m.b);
    const col = { hall: "#2b6cb0", cooling: "#2f855a", substation: "#c05621" };
    let g = `<line x1="${m.l}" x2="${W - m.r}" y1="${Y(0)}" y2="${Y(0)}" stroke="#999" stroke-dasharray="3 3"/>`;
    // y axis ticks
    const step = (y1 - y0) > 12 ? 4 : (y1 - y0) > 6 ? 2 : 1;
    for (let y = Math.ceil(y0); y <= Math.floor(y1); y += step) g += `<text x="${m.l - 4}" y="${Y(y) + 4}" font-size="10" text-anchor="end" fill="#666">${y}</text><line x1="${m.l}" x2="${W - m.r}" y1="${Y(y)}" y2="${Y(y)}" stroke="#eee"/>`;
    g += `<text x="10" y="${m.t + 10}" font-size="10" fill="#666">ΔT (K)</text>`;
    // x axis years
    const yA = new Date(x0).getUTCFullYear(), yB = new Date(x1).getUTCFullYear();
    for (let y = yA; y <= yB + 1; y++) { const t = Date.UTC(y, 0, 1); if (t >= x0 && t <= x1) g += `<text x="${X(t)}" y="${H - 8}" font-size="10" text-anchor="middle" fill="#666">${y}</text><line x1="${X(t)}" x2="${X(t)}" y1="${m.t}" y2="${H - m.b}" stroke="#eee"/>`; }
    // met overlays (scaled to right axis)
    const metSeries = [];
    if (met.ta) metSeries.push({ key: "ta", label: "Ta °C", color: "#b83280" });
    if (met.wind) metSeries.push({ key: "wind", label: "wind m/s", color: "#2c7a7b" });
    if (met.tw) metSeries.push({ key: "tw", label: "Tw °C", color: "#975a16" });
    const uniq = [...new Map(frames.map(f => [f.t, f])).values()].sort((a, b) => Date.parse(a.t) - Date.parse(b.t));
    metSeries.forEach((ms, i) => {
      const vals = uniq.map(f => f[ms.key]).filter(v => v !== null && v !== undefined);
      if (!vals.length) return;
      const lo = Math.min(...vals), hi = Math.max(...vals);
      const Ym = v => m.t + (hi - v) / Math.max(1e-6, hi - lo) * (H - m.t - m.b);
      const path = uniq.filter(f => f[ms.key] !== null && f[ms.key] !== undefined).map((f, j) => `${j ? "L" : "M"}${X(Date.parse(f.t)).toFixed(1)},${Ym(f[ms.key]).toFixed(1)}`).join(" ");
      g += `<path d="${path}" fill="none" stroke="${ms.color}" stroke-width="1" opacity="0.7"/><text x="${W - m.r - 2}" y="${m.t + 10 + i * 11}" font-size="9" text-anchor="end" fill="${ms.color}">${ms.label}: ${lo.toFixed(0)} to ${hi.toFixed(0)} (right axis)</text>`;
    });
    pts.forEach((f, i) => { g += `<circle class="pt" data-i="${i}" cx="${X(ts[i]).toFixed(1)}" cy="${Y(f.dt).toFixed(1)}" r="3.2" fill="${col[f.ptype] || "#555"}" fill-opacity="0.85" stroke="#fff" stroke-width="0.6"/>`; });
    svg.innerHTML = g;
    svg.querySelectorAll(".pt").forEach(c => {
      c.addEventListener("mouseenter", e => {
        const f = pts[+c.dataset.i];
        if (!tip) { tip = document.createElement("div"); tip.className = "tip"; document.body.appendChild(tip); }
        tip.innerHTML = `<b>${f.t.slice(0, 16).replace("T", " ")} UTC</b> · ${esc(f.sensor)}<br>${esc(f.ptype)} (${esc(f.polygon)}): ΔT ${f.dt.toFixed(2)} K (roof ${f.t_poly} K, bg ${f.t_bg} K)<br>valid px ${f.n_valid_poly}/${f.n_total_poly}, bg px ${f.n_valid_bg}; cloud ${fmt(f.cloud, 0)} %; sun ${fmt(f.sun, 0)}°<br>ERA5: Ta ${fmt(f.ta, 1)} °C, Tw ${fmt(f.tw, 1)} °C, RH ${fmt(f.rh, 0)} %, wind ${fmt(f.wind, 1)} m/s${f.capacity_mw !== null && f.capacity_mw !== undefined ? `<br>documented capacity then: ${fmt(f.capacity_mw, 1)} MW` : ""}`;
        tip.style.left = (e.pageX + 12) + "px"; tip.style.top = (e.pageY + 12) + "px";
      });
      c.addEventListener("mousemove", e => { if (tip) { tip.style.left = (e.pageX + 12) + "px"; tip.style.top = (e.pageY + 12) + "px"; } });
      c.addEventListener("mouseleave", () => { if (tip) { tip.remove(); tip = null; } });
    });
  }

  // ---- modals
  const modal = document.getElementById("modal"), mbody = document.getElementById("modal-body");
  document.getElementById("modal-close").onclick = () => modal.hidden = true;
  modal.addEventListener("click", e => { if (e.target === modal) modal.hidden = true; });
  document.getElementById("btn-methods").onclick = () => { mbody.innerHTML = methodsHtml(); modal.hidden = false; };
  document.getElementById("btn-results").onclick = () => { mbody.innerHTML = resultsHtml(); modal.hidden = false; };

  function methodsHtml() {
    const l = model.loso || {}, k = model.kill_conditions || {}, vd = model.variance || {};
    return `<h2>Methods and caveats</h2>
<h3>What is measured</h3>
<p>For every usable satellite acquisition we compute <b>ΔT = mean brightness/surface temperature of a hand-digitised polygon (data-hall roofs, cooling plant, or substation) minus the mean of a background annulus 0.5–2 km away</b>, with the annulus restricted to the most common eligible land-cover classes (ESA WorldCover; water, built-up, wetland and snow excluded). Frames whose polygon or annulus has too few cloud-free pixels are rejected and counted, not dropped silently. ERA5 reanalysis (2 m air temperature, dew point, 10 m wind; derived wind speed, specific humidity and wet-bulb temperature) is joined at the acquisition time.</p>
<p><b>In this build the thermal source is Landsat 8 Collection 1 Level-1 band 10 brightness temperature (2013–2021) from Google Cloud's public archive</b>, not Collection 2 Level-2 surface temperature via Google Earth Engine as intended: the build environment had no Earth Engine credentials and no route to USGS, Planetary Computer or AppEEARS. Brightness temperature is not emissivity-corrected, so low-emissivity metal roofs read cooler than they are; because ΔT is a same-scene difference most atmospheric effects cancel, but the emissivity term is a per-site bias absorbed by the site random effect. All observations are at the fixed ~10:30 local Landsat overpass; there is no night-time or afternoon coverage (ECOSTRESS was unreachable). ERA5 (31 km) stands in for ERA5-Land (9 km).</p>
<h3>What is derived, and what is not identified</h3>
<p>Heat rejection scales roughly as <b>capacity × utilisation</b>. A thermal observation is a noisy proxy for that <b>product</b>. Capacity and utilisation are <b>not separately identified</b> from thermal data. The map therefore distinguishes: <span class="badge u">utilisation identified</span> only where capacity comes from an independent (Tier A) document, so that U = Q̂ / (C × PUE) can be formed; <span class="badge q">Q̂ only</span> where capacity is not independently known; <span class="badge t">unvalidated transfer</span> for Chinese sites not in the fit; <span class="badge m">ΔT measured, Q̂ not identified</span> when the fitted ΔT–capacity slope is indistinguishable from zero, so no heat figure can be inverted from the measurement (the state of every measured site in this build); and hollow markers for sites with no thermal observations yet.</p>
<h3>Model</h3>
<p>Mixed-effects regression on Tier A sites only: ΔT ~ capacity density (documented IT-equivalent MW per hectare of measured roof) + met covariates (${esc((model.met || []).join(", "))}) + cooling architecture (when identifiable) + (1 | site). A conditioned variant drops the covariates and uses only frames in a narrow window (clear, wind &lt; 3 m/s, 5–25 °C, solar elevation &lt; 40° as the closest available proxy for night). Validation is <b>leave-one-site-out only</b>; random splits would leak site identity.</p>
<h3>Baseline and kill conditions</h3>
<p>The intended baseline is capacity from cooling-equipment counts (Epoch AI's approach, roughly a factor 1.4× on IT power 80 % of the time). Unit counts need sub-metre imagery that was not available here, so the baseline implemented is geometry-only: log capacity regressed on log roof area (a <code>cooling_units</code> column in sites.csv switches to unit counts when supplied). The exercise stops with a negative result if (1) LOSO error does not beat that baseline, or (2) meteorological covariates explain more variance than capacity.</p>
<div class="callout ${k.verdict === "negative_result" ? "red" : ""}"><b>Current result:</b> slope of ΔT on capacity density ${fmt(model.slope && model.slope.value, 4)} ± ${fmt(model.slope && model.slope.se, 4)} ${esc(model.slope && model.slope.units)}; LOSO thermal inversion ${l.thermal && l.thermal.median_factor !== null && l.thermal.median_factor !== undefined ? `${fmt(l.thermal.median_factor, 2)}× (${l.thermal.n_unidentified}/${l.thermal.n_sites} folds not identified)` : `not identified in ${l.thermal ? l.thermal.n_unidentified : "?"}/${l.thermal ? l.thermal.n_sites : "?"} folds`} vs geometry ${fmt(l.geometry && l.geometry.median_factor, 2)}× vs constant ${fmt(l.constant && l.constant.median_factor, 2)}×; partial R² capacity ${fmt(vd.partial_r2_capacity, 3)} vs met ${fmt(vd.partial_r2_met, 3)}. Verdict: <b>${esc(k.verdict || "not run")}</b>.</div>
<h3>China</h3>
<p>A model trained on US/European/Japanese sites learns P(ΔT | capacity, utilisation ≈ high) because those facilities are demand-constrained. Many western Chinese hubs were built ahead of demand and run below saturation; the model will read their capacity low, and the bias is largest exactly at the stranded facilities of most interest. Two Chinese supercomputing centres with independently measured power (TOP500) are in the Tier A fit, which is the beginning of a Chinese label set; every other Chinese estimate is an unvalidated extrapolation and is labelled as such. No environmental-impact-assessment (环评) capacities could be retrieved from the build environment.</p>
<h3>Credits</h3><p class="small">${esc(data.credits)}</p>`;
  }

  function resultsHtml() {
    if (!model.status) return "<h2>Model results</h2><p>No model run.</p>";
    const rows = (model.loso_rows || []).filter(r => r.model === "all_frames");
    const mm = model.model || {};
    const coef = mm.params ? Object.entries(mm.params).map(([k, v]) => `<tr><td>${esc(k)}</td><td class="num">${fmt(v, 4)}</td><td class="num">${fmt(mm.bse && mm.bse[k], 4)}</td></tr>`).join("") : "";
    const l = model.loso || {}, lc = model.loso_conditioned || {}, vd = model.variance || {}, k = model.kill_conditions || {};
    const st = o => o ? `${fmt(o.median_factor, 2)}× (within 1.4×: ${fmt(100 * o.frac_within_1p4x, 0)} %, within 2×: ${fmt(100 * o.frac_within_2x, 0)} %, n=${o.n})` : "—";
    return `<h2>Model results (${esc(model.ptype)} polygons, capacity as ${esc(model.capacity_col)})</h2>
<p>Tier A: ${model.n_sites_tier_a} sites, ${model.n_frames_tier_a} frames. All sites with frames: ${model.n_sites_all} sites, ${model.n_frames_all} frames. Fit: ${esc(mm.kind)} (converged: ${mm.converged}); between-site SD ${fmt(mm.re_sd, 2)} K, residual SD ${fmt(mm.resid_sd, 2)} K.</p>
<p><b>Slope on capacity:</b> ${fmt(model.slope && model.slope.value, 4)} ± ${fmt(model.slope && model.slope.se, 4)} ${esc(model.slope && model.slope.units)} (|slope| &gt; 2 SE: ${model.slope && model.slope.significant_2se}).</p>
<p><b>Variance:</b> full-model R² ${fmt(vd.r2_full, 3)}; partial R² capacity ${fmt(vd.partial_r2_capacity, 3)}, met block ${fmt(vd.partial_r2_met, 3)}; capacity-only R² ${fmt(vd.r2_capacity_only, 3)}, met-only R² ${fmt(vd.r2_met_only, 3)}; between-site share of ΔT variance ${fmt(vd.between_site_share, 3)}.</p>
<p><b>Leave-one-site-out</b> (median factor error of implied capacity): all-frames model — thermal ${st(l.thermal)}; geometry baseline ${st(l.geometry)}; constant ${st(l.constant)}.<br>
Conditioned model (${model.n_frames_conditioned} frames, ${model.n_sites_conditioned} sites) — thermal ${st(lc.thermal)}; geometry ${st(lc.geometry)}; constant ${st(lc.constant)}.</p>
<p><b>Secondary learner:</b> ${esc(model.secondary && model.secondary.learner)}; LOSO median |log error| ${fmt(model.secondary && model.secondary.median_abs_log_err, 2)}.</p>
<div class="callout ${k.verdict === "negative_result" ? "red" : ""}">Kill 1 (LOSO not better than geometry baseline): <b>${k.loso_not_better_than_geometry_baseline}</b> · Kill 2 (met explains more than capacity): <b>${k.met_explains_more_than_capacity}</b> · verdict: <b>${esc(k.verdict)}</b></div>
<h3>Within-site capacity steps (Tier A sites whose documented capacity changed)</h3>
<p class="small">Roof albedo, emissivity and background are constant within a site, so this is the cleanest test of the heat term. Coefficient is K per MW of documented IT power, with met covariates in the regression.</p>
<table><tr><th>site</th><th>frames</th><th>K per MW</th><th>SE</th><th>p</th><th>period means</th></tr>${(model.within_site || []).map(w => `<tr><td>${esc(w.site_id)}</td><td class="num">${w.n_frames}</td><td class="num">${fmt(w.coef_k_per_mw, 4)}</td><td class="num">${fmt(w.se, 4)}</td><td class="num">${fmt(w.p_value, 3)}</td><td>${w.periods.map(p => `${fmt(p.it_mw, 1)} MW: ${p.mean_dt >= 0 ? "+" : ""}${fmt(p.mean_dt, 2)} K (n=${p.n})`).join("; ")}</td></tr>`).join("")}</table>
<h3>Per-site LOSO (all-frames model)</h3>
<table><tr><th>site</th><th>frames</th><th>documented IT MW</th><th>thermal LOSO MW (5–95 %)</th><th>fold slope ± SE</th><th>geometry MW</th><th>constant MW</th></tr>${rows.map(r => `<tr><td>${esc(r.site_id)}</td><td class="num">${r.n_frames}</td><td class="num">${fmt(r.truth_mw, 1)}</td><td class="num">${r.thermal_identified ? `${fmt(r.thermal_mw, 1)} (${fmt(r.thermal_lo_mw, 1)}–${fmt(r.thermal_hi_mw, 1)})` : `not identified (raw ${fmt(r.thermal_raw_mw, 0)})`}</td><td class="num">${fmt(r.slope, 4)} ± ${fmt(r.slope_se, 4)}</td><td class="num">${fmt(r.geometry_mw, 1)}</td><td class="num">${fmt(r.const_mw, 1)}</td></tr>`).join("")}</table>
<h3>Fixed-effect coefficients (all frames)</h3><table><tr><th>term</th><th>estimate</th><th>SE</th></tr>${coef}</table>`;
  }
})();
