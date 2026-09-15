/* Findings page: every finding from merged requests for work, grouped by request. Data: data/evidence.json. */
(async function () {
  const F = window.OOFindings, esc = F.esc;
  const groups = document.getElementById("groups"), count = document.getElementById("count");
  const requestSelect = document.getElementById("request"), answersSelect = document.getElementById("answers");
  let data;
  try { data = await (await fetch("data/evidence.json", { cache: "no-cache" })).json(); }
  catch (e) { count.textContent = "The findings could not be loaded."; return; }
  const all = data.findings || [], requests = data.requests || {};
  const ids = [...new Set(all.map(f => f.request))];
  requestSelect.innerHTML = `<option value="all">All requests</option>` + ids.map(id => `<option value="${esc(id)}">${esc(id)} ${esc((requests[id] || {}).title)}</option>`).join("");
  answersSelect.innerHTML = `<option value="all">All questions</option>` + F.ANSWERS.filter(a => all.some(f => f.answers === a)).map(a => `<option value="${a}">${F.LABEL[a]}</option>`).join("");
  const hash = decodeURIComponent(location.hash.slice(1));
  if (ids.includes(hash)) requestSelect.value = hash;

  function render() {
    const rows = all.filter(f => (requestSelect.value === "all" || f.request === requestSelect.value) && (answersSelect.value === "all" || f.answers === answersSelect.value));
    const sites = new Set(rows.filter(f => f.subject_type === "site").map(f => f.subject)).size;
    count.textContent = `${rows.length} of ${all.length} findings shown, on ${sites} site${sites === 1 ? "" : "s"} and the wider picture.`;
    groups.innerHTML = rows.length ? ids.filter(id => rows.some(f => f.request === id)).map(id => {
      const fs = rows.filter(f => f.request === id), r = requests[id] || {};
      return `<h2 id="${esc(id)}"><a href="requests.html#${esc(r.anchor)}">${esc(id)}</a> ${esc(r.title)} <span class="small">${fs.length}</span></h2>` +
        `<ul class="findings-list">${fs.map(f => F.item(f, "", true, false)).join("")}</ul>`;
    }).join("") : `<p class="empty">No findings match these filters.</p>`;
  }
  requestSelect.addEventListener("change", () => { history.replaceState(null, "", requestSelect.value === "all" ? " " : `#${requestSelect.value}`); render(); });
  answersSelect.addEventListener("change", render);
  render();
})();
