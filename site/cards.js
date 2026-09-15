/* Open Observatory list: one card per site, in words. Data: data/status.json (from build_status.py). */
(async function () {
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const fmt = (v, d = 0) => (v === null || v === undefined || Number.isNaN(v)) ? "—" : Number(v).toFixed(d);
  const data = await (await fetch("data/status.json", { cache: "no-cache" })).json();
  document.getElementById("build-note").textContent = `Built ${String(data.generated || "").slice(0, 10)}.`;
  const all = data.sites;
  const isHub = s => /_hub$/.test(s.site_id) && !s.series.some(p => p.y);
  const kinds = {
    measured: { label: "Measured: reported electricity or calibrated NOx", sw: "sw-comb", rank: 0 },
    derived: { label: "Derived from published water use", sw: "sw-der", rank: 1 },
    detected: { label: "Detected activity; load not measured", sw: "sw-det", rank: 2 },
    presumed: { label: "Presumed from documented capacity", sw: "sw-doc", rank: 3 },
    construction: { label: "Construction / unknown", sw: "sw-build", rank: 4 }
  };
  const kind = s => Object.hasOwn(kinds, s.evidence_kind) ? s.evidence_kind : "construction";

  function spark(s) {
    const pts = s.series.filter(p => p.y !== null && p.y !== undefined && p.x);
    if (!pts.length) return "";
    const W = 400, H = 80, L = 34, R = 6, T = 8, B = 18, iw = W - L - R, ih = H - T - B;
    const maxv = Math.max(1, ...pts.map(p => p.y + (p.se || 0)));
    const minv = Math.min(0, ...pts.map(p => p.y - (p.se || 0)));
    const n = s.series.length, bw = iw / n;
    const y = v => T + ih - ((v - minv) / (maxv - minv)) * ih;
    let g = `<line x1="${L}" y1="${y(0)}" x2="${W - R}" y2="${y(0)}" stroke="#bbb"/><text x="${L - 3}" y="${T + 8}" font-size="9" text-anchor="end" fill="#666">${fmt(maxv, 0)}</text>`;
    s.series.forEach((p, i) => {
      if (p.y === null || p.y === undefined) return;
      const x = L + i * bw;
      const color = s.key === "generator_watch" ? (p.y > 100 && p.y > 2 * p.se ? "#dd6b20" : "#a0aec0") : s.key === "nox" ? (p.y > 500 ? "#c53030" : p.y > 150 ? "#dd6b20" : "#a0aec0") : s.key === "roofs" ? "#2f855a" : "#2b6cb0";
      g += `<rect x="${x + 1}" y="${Math.min(y(p.y), y(0))}" width="${Math.max(bw - 2, 1)}" height="${Math.max(Math.abs(y(0) - y(p.y)), 0.5)}" fill="${color}"><title>${esc(p.x)}: ${fmt(p.y, 0)}${p.se ? ` ± ${fmt(p.se, 0)}` : ""}</title></rect>`;
      if (p.se) g += `<line x1="${x + bw / 2}" y1="${y(p.y - p.se)}" x2="${x + bw / 2}" y2="${y(p.y + p.se)}" stroke="#555" stroke-width="1"/>`;
    });
    const step = Math.max(1, Math.round(n / 6));
    s.series.forEach((p, i) => { if (i % step === 0) g += `<text x="${L + i * bw + bw / 2}" y="${H - 5}" font-size="9" text-anchor="middle" fill="#666">${esc(p.x)}</text>`; });
    return `<svg class="spark" viewBox="0 0 ${W} ${H}">${g}</svg><div class="small">${esc(s.series_label)}${s.recent ? ` · ${esc(s.recent)}` : ""}</div>`;
  }

  function card(s) {
    const evidence = kinds[kind(s)];
    return `<div class="card" data-evidence-kind="${kind(s)}">
      <h2>${esc(s.name)}</h2>
      <div class="meta">${esc(s.operator)} · ${esc(s.country)}${s.polygons_low ? " · polygons are low-confidence" : ""}</div>
      <div class="evidence"><span class="sw ${evidence.sw}" aria-hidden="true"></span>${evidence.label}</div>
      <div class="lines">
        <div>Built</div><div>${esc(s.built)}</div>
        <div>Running</div><div>${esc(s.running)}</div>
        <div>Load</div><div>${esc(s.load)}</div>
        <div>Confidence</div><div><span class="conf ${esc(s.confidence)}">${esc(s.confidence)}</span></div>
      </div>
      ${spark(s)}
      ${s.sources?.length ? `<div class="small">Sources: ${s.sources.map(r => `<a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.label)}</a>`).join(" · ")}</div>` : ""}
      <div class="how"><b>How we know:</b> ${s.how.map(esc).join("; ") || "no evidence yet"}</div>
      ${s.findings && s.findings.n ? `<div class="how"><b>From requests for work:</b> ${s.findings.n} finding${s.findings.n === 1 ? "" : "s"} (${s.findings.requests.map(esc).join(", ")}), <a href="map.html#${esc(s.site_id)}">read them</a></div>` : ""}
      <div style="margin-top:6px"><a href="map.html#${esc(s.site_id)}">quarterly detail</a></div>
    </div>`;
  }

  function render() {
    const sort = document.getElementById("sort").value, hide = document.getElementById("hide-hubs").checked;
    const selected = document.getElementById("evidence").value;
    let rows = all.filter(s => !(hide && isHub(s)) && (selected === "all" || kind(s) === selected));
    if (sort === "default") rows.sort((a, b) => kinds[kind(a)].rank - kinds[kind(b)].rank || (b.est_mid ?? b.est_hi ?? 0) - (a.est_mid ?? a.est_hi ?? 0) || a.name.localeCompare(b.name));
    if (sort === "name") rows = [...rows].sort((a, b) => a.name.localeCompare(b.name));
    if (sort === "country") rows = [...rows].sort((a, b) => (a.country + a.name).localeCompare(b.country + b.name));
    document.getElementById("result-count").textContent = `${rows.length} of ${all.length} sites shown${hide ? " · approximate hub centroids hidden" : ""}.`;
    document.getElementById("cards").innerHTML = rows.length ? rows.map(card).join("") : '<p class="empty">No sites match these filters. Choose another evidence kind or show approximate hub centroids.</p>';
  }
  document.getElementById("evidence").addEventListener("change", render);
  document.getElementById("sort").addEventListener("change", render);
  document.getElementById("hide-hubs").addEventListener("change", render);
  render();
})();
