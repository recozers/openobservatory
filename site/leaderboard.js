/* Token leaderboard: renders site/data/leaderboard.json, which .github/scripts/donations.cjs builds from merged pull
   requests. Names and agent text come from contributors, so everything is written with textContent. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.OOLeaderboard = api;
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  function formatTokens(n) {
    return new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 2 }).format(n);
  }

  function formatUsd(n, complete = true) {
    if (n === null || n === undefined || !Number.isFinite(Number(n))) return '–';
    const s = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(Number(n));
    return complete ? s : `at least ${s}`;
  }

  function summary(data) {
    const t = (data && data.totals) || { tokens: 0, contributions: 0, donors: 0 };
    if (!t.contributions) return 'No donated sessions with a token count have been merged yet. The first one takes the top spot.';
    const plural = (n, word) => `${n.toLocaleString('en-GB')} ${word}${n === 1 ? '' : 's'}`;
    const worth = t.usd ? `, worth ${formatUsd(t.usd, t.usd_complete !== false)} at API list prices,` : '';
    return `${formatTokens(t.tokens)} tokens${worth} from ${plural(t.donors, 'donor')} across ${plural(t.contributions, 'contribution')}.`;
  }

  function el(doc, tag, text, attrs) {
    const node = doc.createElement(tag);
    if (text !== undefined && text !== null) node.textContent = String(text);
    for (const [k, v] of Object.entries(attrs || {})) node.setAttribute(k, v);
    return node;
  }

  function safeUrl(url, prefix) {
    return typeof url === 'string' && url.startsWith(prefix) ? url : null;
  }

  function render(doc, data) {
    doc.getElementById('totals').textContent = summary(data);
    const body = doc.getElementById('rows');
    body.textContent = '';
    const donors = (data && data.donors) || [];
    doc.getElementById('board').hidden = donors.length === 0;
    for (const d of donors) {
      const tr = el(doc, 'tr');
      tr.appendChild(el(doc, 'td', d.rank));
      const who = el(doc, 'td');
      const profile = safeUrl(d.profile, 'https://github.com/');
      who.appendChild(profile ? el(doc, 'a', d.name, { href: profile, target: '_blank', rel: 'noopener' }) : el(doc, 'span', d.name));
      for (const a of d.agents || []) {
        const value = a.usd ? ` · ${formatUsd(a.usd, a.usd_complete !== false)}` : '';
        who.appendChild(el(doc, 'div', `${a.name}: ${formatTokens(a.tokens)}${value}`, { class: 'agent' }));
      }
      tr.appendChild(who);
      tr.appendChild(el(doc, 'td', formatTokens(d.tokens), { title: `${Number(d.tokens).toLocaleString('en-GB')} tokens`, class: 'num' }));
      tr.appendChild(el(doc, 'td', formatUsd(d.usd, d.usd_complete !== false), { title: 'what these tokens would cost at API list prices', class: 'num' }));
      const work = el(doc, 'td');
      for (const c of d.contributions || []) {
        const url = safeUrl(c.url, 'https://github.com/recozers/openobservatory/');
        const name = c.pr ? (c.item ? `${c.item} (#${c.pr})` : `#${c.pr}`) : (c.label || 'Contribution');
        const line = el(doc, 'div', null, { class: 'contribution' });
        line.appendChild(url ? el(doc, 'a', name, { href: url, target: '_blank', rel: 'noopener' }) : el(doc, 'span', name));
        const value = c.usd === null || c.usd === undefined ? '' : `, ${formatUsd(c.usd)}`;
        line.appendChild(doc.createTextNode(` · ${formatTokens(c.tokens)}${value}${c.agent && d.agents && d.agents.length > 1 ? `, ${c.agent}` : ''}`));
        work.appendChild(line);
      }
      tr.appendChild(work);
      tr.appendChild(el(doc, 'td', String(d.last || '').slice(0, 10)));
      body.appendChild(tr);
    }
    return donors.length;
  }

  async function start(doc, fetchImpl) {
    try {
      const res = await fetchImpl(`data/leaderboard.json?v=${Date.now()}`);
      if (!res.ok) throw new Error(String(res.status));
      render(doc, await res.json());
    } catch (err) {
      doc.getElementById('totals').textContent = 'The leaderboard could not be loaded. Try again in a moment.';
    }
  }

  if (typeof document !== 'undefined' && typeof window !== 'undefined' && typeof window.fetch === 'function') {
    const go = () => start(document, window.fetch.bind(window));
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', go);
    else go();
  }

  return { formatTokens, formatUsd, summary, render, start };
});
