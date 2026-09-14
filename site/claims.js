/* Claims on requests for work, read from open pull requests.
   The requests page loads this file to mark claimed items live, and the claim bot (.github/scripts/claims.cjs) requires
   it, so both parse titles and decide who holds a claim the same way. Pull request titles are untrusted text: the page
   writes them with textContent only. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.OOClaims = api;
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  const REPO = 'recozers/openobservatory';
  const LAPSE_HOURS = 72;
  const LABELS = { claim: 'claim', duplicate: 'duplicate claim', lapsed: 'lapsed claim' };

  // "[RFW-07] Short title" gives {id: 'RFW-07', ...}; anything else gives null.
  function parseClaimTitle(title) {
    const m = /^\s*\[(RFW|T|PAID)-(\d{1,3})\]\s*(.*)$/i.exec(String(title || ''));
    if (!m) return null;
    const prefix = m[1].toUpperCase();
    return { id: `${prefix}-${String(parseInt(m[2], 10)).padStart(2, '0')}`, prefix, rest: m[3].trim() };
  }

  // True for titles that seem to attempt a claim but do not parse, such as "RFW-07: title" or "[RFW 7] title".
  function looksLikeClaim(title) {
    const t = String(title || '');
    return !parseClaimTitle(t) && /(\bRFW[\s-]?\d|\bPAID[\s-]?\d|\[\s*T[\s-]?\d)/i.test(t);
  }

  // Rows of the request, theory and paid-request tables in REQUESTS_FOR_WORK.md. Only request tables have a Status column.
  function parseRequests(markdown) {
    const items = {};
    for (const line of String(markdown || '').split('\n')) {
      const m = /^\|\s*\[((?:RFW|T|PAID)-\d+)\]\(#([^)]+)\)\s*\|(.*)\|\s*$/.exec(line);
      if (!m) continue;
      const cells = m[3].split('|').map(c => c.trim());
      const id = m[1];
      const status = id.startsWith('RFW-') ? cells[cells.length - 1] : null;
      const reserved = status && /^reserved:\s*(.+)$/i.exec(status);
      items[id] = { id, anchor: m[2], title: cells[0], status, reservedFor: reserved ? reserved[1].trim() : null };
    }
    return items;
  }

  // prs: [{number, title, draft, created_at, head_ref, last_commit_at}]. Returns {number: assessment} for claim-like titles.
  // The earliest open pull request for an item holds the claim. A draft lapses after 72 hours without a new commit; a pull
  // request marked ready for review never lapses. A reserved item can only be claimed from the named agent's branches.
  function assess(prs, requests, now) {
    const out = {};
    const groups = {};
    for (const pr of prs || []) {
      const claim = parseClaimTitle(pr.title);
      if (!claim) {
        if (looksLikeClaim(pr.title)) out[pr.number] = { malformed: true };
        continue;
      }
      const item = requests[claim.id];
      const a = { id: claim.id, known: Boolean(item), holder: false, duplicateOf: null, lapsed: false, reservedFor: null };
      out[pr.number] = a;
      if (!item) continue;
      if (item.reservedFor) {
        const prefix = item.reservedFor.toLowerCase().replace(/[^a-z0-9]+/g, '-') + '/';
        if (!String(pr.head_ref || '').toLowerCase().startsWith(prefix)) { a.reservedFor = item.reservedFor; continue; }
      }
      const last = Date.parse(pr.last_commit_at || pr.created_at);
      a.lapsed = Boolean(pr.draft) && Number.isFinite(last) && now - last > LAPSE_HOURS * 3600e3;
      (groups[claim.id] = groups[claim.id] || []).push(pr);
    }
    for (const group of Object.values(groups)) {
      group.sort((x, y) => Date.parse(x.created_at) - Date.parse(y.created_at) || x.number - y.number);
      const holder = group.find(pr => !out[pr.number].lapsed);
      for (const pr of group) {
        if (holder && pr.number === holder.number) out[pr.number].holder = true;
        else if (holder && !out[pr.number].lapsed) out[pr.number].duplicateOf = holder.number;
      }
    }
    return out;
  }

  // For the page: which item each open pull request holds, trusting the bot's labels for lapsed and duplicate claims.
  function liveClaims(pulls) {
    const held = {};
    for (const pr of pulls || []) {
      const claim = parseClaimTitle(pr && pr.title);
      if (!claim) continue;
      const labels = (pr.labels || []).map(l => (typeof l === 'string' ? l : l && l.name));
      if (labels.includes(LABELS.lapsed) || labels.includes(LABELS.duplicate)) continue;
      const url = String(pr.html_url || '');
      if (!url.startsWith(`https://github.com/${REPO}/pull/`)) continue;
      const prev = held[claim.id];
      if (!prev || Date.parse(pr.created_at) < Date.parse(prev.created_at)) {
        held[claim.id] = { id: claim.id, number: pr.number, url, draft: Boolean(pr.draft), created_at: pr.created_at };
      }
    }
    return held;
  }

  function badge(doc, claim) {
    const a = doc.createElement('a');
    a.className = 'claim-badge';
    a.href = claim.url;
    a.textContent = `claimed in #${claim.number}${claim.draft ? '' : ', in review'}`;
    return a;
  }

  // Marks each held item in its table row and on its section heading. Returns the number of items marked.
  function annotate(doc, held) {
    let marked = 0;
    for (const claim of Object.values(held)) {
      const prefix = `${claim.id.toLowerCase()}-`;
      const link = doc.querySelector(`td a[href^="#${prefix}"]`);
      const heading = doc.querySelector(`h4[id^="${prefix}"]`);
      if (!link && !heading) continue;
      if (link) {
        const row = link.closest('tr');
        const table = link.closest('table');
        const headers = table ? Array.from(table.querySelectorAll('th')).map(th => th.textContent.trim()) : [];
        const cells = row ? row.querySelectorAll('td') : [];
        const statusCell = cells[headers.indexOf('Status')];
        if (statusCell) { statusCell.textContent = ''; statusCell.appendChild(badge(doc, claim)); }
        else { link.parentNode.appendChild(doc.createTextNode(' ')); link.parentNode.appendChild(badge(doc, claim)); }
      }
      if (heading) { heading.appendChild(doc.createTextNode(' ')); heading.appendChild(badge(doc, claim)); }
      marked += 1;
    }
    return marked;
  }

  async function start(doc, fetchImpl) {
    const note = doc.getElementById('live-claims');
    if (!note) return;
    try {
      const res = await fetchImpl(`https://api.github.com/repos/${REPO}/pulls?state=open&per_page=100`,
        { headers: { Accept: 'application/vnd.github+json' } });
      if (!res.ok) throw new Error(`GitHub API returned ${res.status}`);
      const n = annotate(doc, liveClaims(await res.json()));
      note.textContent = n === 0
        ? 'No item is claimed right now. Claims are read live from open pull requests.'
        : `${n} ${n === 1 ? 'item is' : 'items are'} claimed right now and marked below. Claims are read live from open pull requests.`;
    } catch (err) {
      note.textContent = "Live claims could not be loaded from GitHub. Search open pull requests for an item's ID before you claim it.";
    }
    note.hidden = false;
  }

  if (typeof document !== 'undefined' && typeof window !== 'undefined' && typeof window.fetch === 'function') {
    const go = () => start(document, window.fetch.bind(window));
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', go);
    else go();
  }

  return { REPO, LAPSE_HOURS, LABELS, parseClaimTitle, looksLikeClaim, parseRequests, assess, liveClaims, annotate, start };
});
