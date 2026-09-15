/* Findings from merged requests for work: one renderer for the quarterly detail, the research view and the findings page.
   Data: data/evidence.json, written by tools/evidence.py when build_status.py runs. */
(function (root) {
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const REPO = "https://github.com/recozers/openobservatory";
  const ANSWERS = ["where", "built", "capacity", "running", "utilisation", "workload", "sources"];
  const LABEL = { where: "Where", built: "Built", capacity: "Capacity", running: "Running", utilisation: "Utilisation", workload: "Workload", sources: "Sources" };

  function bySubject(data) {
    const out = {};
    ((data && data.findings) || []).forEach(f => { (out[f.subject] = out[f.subject] || []).push(f); });
    return out;
  }

  // base: path from the page to the site root ("" or "../"); withSubject: name the site, country or "All sites";
  // withRequest: false where a heading already names the request
  function item(f, base = "", withSubject = false, withRequest = true) {
    const subject = !withSubject ? "" : f.subject_type === "site" ? `<a href="${esc(base)}map.html#${esc(f.subject)}">${esc(f.subject_name)}</a> · ` : `${esc(f.subject_name)} · `;
    const period = f.period ? ` · ${esc(String(f.period).replace("..", " to "))}` : "";
    const pr = Number.isInteger(f.pull_request) ? ` · <a href="${REPO}/pull/${f.pull_request}" target="_blank" rel="noopener">pull request ${f.pull_request}</a>` : "";
    return `<li class="finding" data-answers="${esc(f.answers)}">` +
      `<div class="finding-meta">${subject}${withRequest ? `<a href="${esc(base)}requests.html#${esc(f.request_anchor)}" title="${esc(f.request_title)}">${esc(f.request)}</a> · ` : ""}` +
      `<span class="conf ${esc(f.confidence)}">${esc(f.confidence)} confidence</span>${f.verdict ? ` <span class="badge">${esc(f.verdict)}</span>` : ""}${period}</div>` +
      `<div class="finding-text">${esc(f.finding)}</div>` +
      (f.detail ? `<div class="small">${esc(f.detail)}</div>` : "") +
      `<div class="small">Source: <a href="${esc(f.source_url)}" target="_blank" rel="noopener">${esc(f.source_label)}</a>${pr}${f.recorded ? ` · recorded ${esc(f.recorded)}` : ""}</div></li>`;
  }

  function section(list, base = "") {
    if (!list || !list.length) return "";
    const groups = ANSWERS.map(a => [a, list.filter(f => f.answers === a)]).filter(g => g[1].length);
    return `<div class="section findings"><h3>Findings from requests for work</h3>` +
      `<div class="small">${list.length} finding${list.length === 1 ? "" : "s"} from merged contributions. They do not change the load estimate. <a href="${esc(base)}findings.html">All findings</a></div>` +
      groups.map(([a, fs]) => `<h4>${LABEL[a]}</h4><ul class="findings-list">${fs.map(f => item(f, base)).join("")}</ul>`).join("") + `</div>`;
  }

  root.OOFindings = { ANSWERS, LABEL, esc, bySubject, item, section };
})(typeof window !== "undefined" ? window : globalThis);
