/* DC Watch landing map: markers by evidence; click for the plain-language card. Data: data/status.json. */
(async function () {
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const fmt = (v, d = 0) => (v === null || v === undefined || Number.isNaN(v)) ? "—" : Number(v).toFixed(d);
  const data = await (await fetch("data/status.json", { cache: "no-cache" })).json();
  const sites = data.sites.filter(s => !(/_hub$/.test(s.site_id) && !s.series.some(p => p.y)) &&
    Number.isFinite(s.lon) && Number.isFinite(s.lat) && Math.abs(s.lon) <= 180 && Math.abs(s.lat) <= 90);
  const klass = s => s.evidence_kind || (s.combustion ? "measured" : (/^presumably|^yes/.test(s.running) ? "presumed" : "construction"));
  const COLOR = { measured: "#c05621", derived: "#f6ad55", detected: "#d69e2e", presumed: "#2b6cb0", construction: "#ffffff" };
  const STROKE = { measured: "#fff", derived: "#c05621", detected: "#fff", presumed: "#fff", construction: "#9a9a95" };
  const radius = s => Math.min(20, 5 + 8 * Math.sqrt((s.est_mid || s.est_hi / 2 || 0) / 500));

  const style = { version: 8, sources: {
      countries: { type: "geojson", data: "vendor/ne_110m_admin_0_countries.geojson" },
      osm: { type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256, attribution: "© OpenStreetMap contributors", maxzoom: 19 } },
    layers: [ { id: "bg", type: "background", paint: { "background-color": "#dfe9f0" } },
      { id: "land", type: "fill", source: "countries", paint: { "fill-color": "#f3f1ea" } },
      { id: "borders", type: "line", source: "countries", paint: { "line-color": "#c9c5b8", "line-width": 0.6 } },
      { id: "osm", type: "raster", source: "osm", paint: { "raster-opacity": 0.85 } } ] };
  const map = new maplibregl.Map({ container: "map", style, center: [20, 30], zoom: 1.5, minZoom: -2, attributionControl: true, maxZoom: 17 });
  function fitAll() {
    if (!sites.length) return;
    const bounds = new maplibregl.LngLatBounds();
    sites.forEach(s => bounds.extend([s.lon, s.lat]));
    const legend = document.getElementById("legend");
    const bottom = getComputedStyle(legend).position === "absolute" ? legend.offsetHeight + 48 : 32;
    map.fitBounds(bounds, { padding: { top: 32, right: 32, bottom, left: 32 }, maxZoom: 5, duration: 0 });
  }
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-left");
  document.getElementById("chk-tiles").addEventListener("change", e => map.setLayoutProperty("osm", "visibility", e.target.checked ? "visible" : "none"));
  const fc = { type: "FeatureCollection", features: sites.map(s => ({ type: "Feature", geometry: { type: "Point", coordinates: [s.lon, s.lat] },
    properties: { site_id: s.site_id, name: s.name, color: COLOR[klass(s)], stroke: STROKE[klass(s)], r: radius(s), running: s.running } })) };
  let added = false;
  function ensure() {
    if (added) return;
    added = true;
    try {
      map.addSource("sites", { type: "geojson", data: fc });
      map.addLayer({ id: "pts", type: "circle", source: "sites", paint: { "circle-radius": ["get", "r"], "circle-color": ["get", "color"], "circle-stroke-color": ["get", "stroke"], "circle-stroke-width": 2, "circle-opacity": 0.92 } });
    } catch (e) { added = false; return; }
    const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 10 });
    map.on("mousemove", "pts", e => { map.getCanvas().style.cursor = "pointer"; const p = e.features[0].properties; popup.setLngLat(e.features[0].geometry.coordinates).setHTML(`<b>${esc(p.name)}</b><br>${esc(p.running)}`).addTo(map); });
    map.on("mouseleave", "pts", () => { map.getCanvas().style.cursor = ""; popup.remove(); });
    map.on("click", "pts", e => openSite(e.features[0].properties.site_id));
    const h = location.hash.replace("#", "");
    if (h && sites.some(s => s.site_id === h)) openSite(h);
    else fitAll();
  }
  map.on("load", ensure); map.on("idle", ensure);
  const poll = setInterval(() => { ensure(); if (added) clearInterval(poll); }, 250);
  window.addEventListener("hashchange", () => { const h = location.hash.replace("#", ""); if (h && sites.some(s => s.site_id === h)) openSite(h); });
  window.__dc = { map, sites, openSite: id => openSite(id) };

  const panel = document.getElementById("panel"), body = document.getElementById("panel-body");
  document.getElementById("panel-close").onclick = () => { panel.hidden = true; history.replaceState(null, "", " "); };
  function spark(s) {
    const pts = s.series.filter(p => p.y !== null && p.y !== undefined);
    if (!pts.length) return "";
    const W = 380, H = 80, L = 32, R = 6, T = 8, B = 18, iw = W - L - R, ih = H - T - B, n = s.series.length, bw = iw / n;
    const maxv = Math.max(1, ...pts.map(p => p.y + (p.se || 0))), y = v => T + ih - (v / maxv) * ih;
    let g = `<line x1="${L}" y1="${y(0)}" x2="${W - R}" y2="${y(0)}" stroke="#bbb"/><text x="${L - 3}" y="${T + 8}" font-size="9" text-anchor="end" fill="#666">${fmt(maxv, 0)}</text>`;
    s.series.forEach((p, i) => { if (p.y === null || p.y === undefined) return; const x = L + i * bw;
      const c = s.key === "nox" ? (p.y > 500 ? "#c53030" : p.y > 150 ? "#dd6b20" : "#a0aec0") : s.key === "roofs" ? "#2f855a" : "#2b6cb0";
      g += `<rect x="${x + 1}" y="${y(Math.max(p.y, 0))}" width="${Math.max(bw - 2, 1)}" height="${Math.max(y(0) - y(Math.max(p.y, 0)), 0.5)}" fill="${c}"><title>${esc(p.x)}: ${fmt(p.y, 0)}${p.se ? ` ± ${fmt(p.se, 0)}` : ""}</title></rect>`;
      if (p.se) g += `<line x1="${x + bw / 2}" y1="${y(p.y - p.se)}" x2="${x + bw / 2}" y2="${y(p.y + p.se)}" stroke="#555"/>`; });
    const step = Math.max(1, Math.round(n / 5));
    s.series.forEach((p, i) => { if (i % step === 0) g += `<text x="${L + i * bw + bw / 2}" y="${H - 5}" font-size="9" text-anchor="middle" fill="#666">${esc(p.x)}</text>`; });
    return `<svg class="spark" viewBox="0 0 ${W} ${H}">${g}</svg><div class="small">${esc(s.series_label)}${s.recent ? ` · ${esc(s.recent)}` : ""}</div>`;
  }
  function openSite(id) {
    const s = sites.find(x => x.site_id === id); if (!s) return;
    location.hash = id; panel.hidden = false;
    map.flyTo({ center: [s.lon, s.lat], zoom: Math.max(map.getZoom(), 4.5), speed: 1.2 });
    body.innerHTML = `<h2>${esc(s.name)}</h2><div class="meta">${esc(s.operator)} · ${esc(s.country)}${s.polygons_low ? " · polygons low-confidence" : ""}</div>
      <div class="lines"><div>Built</div><div>${esc(s.built)}</div><div>Running</div><div>${esc(s.running)}</div><div>Load</div><div>${esc(s.load)}</div><div>Confidence</div><div><span class="conf ${esc(s.confidence)}">${esc(s.confidence)}</span></div></div>
      ${spark(s)}<div class="how"><b>How we know:</b> ${s.how.map(esc).join("; ") || "no evidence yet"}</div>
      <div style="margin-top:6px"><a href="map.html#${esc(s.site_id)}">quarterly detail</a> · <a href="list.html">all sites</a></div>`;
  }
})();
