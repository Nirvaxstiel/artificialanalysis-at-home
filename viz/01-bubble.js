// viz/01-bubble.js
// Reference implementation: Intelligence × Cost per Task × Output Tokens
// This is the "crossover" chart that started the project.

(function() {
  const CREATOR_COLORS = window.CREATOR_COLORS;
  const CREATOR_BORDER = window.CREATOR_BORDER || {};
  const { wireTooltips, placeLabel } = window.VIZ_HELPERS || {};

  function render(container, data) {
    const W = 1100; const H = 600;
    const M = { top: 30, right: 30, bottom: 50, left: 60 };
    const innerW = W - M.left - M.right;
    const innerH = H - M.top - M.bottom;

    const pts = data.filter(m => m.cost_per_task != null && m.cost_per_task > 0
      && m.tokens_m != null && m.intel != null);

    const minCost = 0.02, maxCost = 7.0;
    const minIQ = 10, maxIQ = 80;
    const minTok = 30, maxTok = 320;

    const xScale = c => M.left + (Math.log10(c) - Math.log10(minCost)) / (Math.log10(maxCost) - Math.log10(minCost)) * innerW;
    const yScale = i => M.top + (1 - (i - minIQ) / (maxIQ - minIQ)) * innerH;
    const rScale = t => 4 + Math.sqrt(Math.max(0, (t - minTok) / (maxTok - minTok))) * 22;

    const costTicks = [0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 3];
    const iqTicks = [10, 20, 30, 40, 50, 60, 70, 80];

    let svg = '';
    // Green quadrant
    svg += `<rect x="${xScale(0.02)}" y="${M.top}" width="${xScale(0.5) - xScale(0.02)}" height="${yScale(50) - M.top}" fill="rgba(182,255,60,0.05)" stroke="rgba(182,255,60,0.3)" stroke-dasharray="3 3"/>`;
    svg += `<text x="${xScale(0.04)}" y="${M.top + 16}" fill="#b6ff3c" font-size="10" font-family="monospace">// GREEN QUADRANT: high IQ + low cost</text>`;

    // Grid
    for (const t of costTicks) svg += `<line class="grid" x1="${xScale(t)}" y1="${M.top}" x2="${xScale(t)}" y2="${H - M.bottom}"/>`;
    for (const t of iqTicks) svg += `<line class="grid" x1="${M.left}" y1="${yScale(t)}" x2="${W - M.right}" y2="${yScale(t)}"/>`;

    // Axes
    svg += `<g class="axis">`;
    for (const t of costTicks) {
      svg += `<text x="${xScale(t)}" y="${H - M.bottom + 18}" text-anchor="middle">$${t}</text>`;
      svg += `<line x1="${xScale(t)}" y1="${H - M.bottom}" x2="${xScale(t)}" y2="${H - M.bottom + 4}"/>`;
    }
    for (const t of iqTicks) {
      svg += `<text x="${M.left - 8}" y="${yScale(t) + 3}" text-anchor="end">${t}</text>`;
      svg += `<line x1="${M.left - 4}" y1="${yScale(t)}" x2="${M.left}" y2="${yScale(t)}"/>`;
    }
    svg += `<text x="${W/2}" y="${H - 8}" text-anchor="middle" font-weight="800" font-size="12">COST PER TASK (USD, log)</text>`;
    svg += `<text x="14" y="${H/2}" text-anchor="middle" font-weight="800" font-size="12" transform="rotate(-90 14 ${H/2})">INTELLIGENCE INDEX</text>`;
    svg += `</g>`;

    // Points
    for (const m of pts) {
      const cx = xScale(m.cost_per_task);
      const cy = yScale(m.intel);
      const r = rScale(m.tokens_m);
      const fill = CREATOR_COLORS[m.creator] || "#888";
      const stroke = CREATOR_BORDER[m.creator] || "#000";
      svg += `<circle class="point" data-slug="${m.slug}" cx="${cx}" cy="${cy}" r="${r}" fill="${fill}" fill-opacity="0.7" stroke="${stroke}" stroke-width="1.5"></circle>`;
    }

    // Labels with collision avoidance
    const sortedByY = [...pts].sort((a, b) => yScale(a.intel) - yScale(b.intel));
    const labelPositions = [];
    for (const m of sortedByY) {
      const cx = xScale(m.cost_per_task);
      const cy = yScale(m.intel);
      const r = rScale(m.tokens_m);
      const placed = placeLabel(cx, cy, r, m.name, labelPositions, { W, H });
      if (!placed) continue;
      svg += `<text class="label" x="${placed.x}" y="${placed.y}" text-anchor="${placed.anchor}" font-size="9" font-weight="700" fill="#f5f5f0" stroke="#000" stroke-width="2.5" paint-order="stroke" data-slug="${m.slug}">${m.name}</text>`;
    }

    container.innerHTML = `<svg viewBox="0 0 ${W} ${H}">${svg}</svg>`;

    // Wire tooltips
    wireTooltips(container, data, '.point, .label');

    // Legend
    const creators = [...new Set(pts.map(p => p.creator))].sort();
    let leg = '<strong style="color:var(--neon);">CREATOR</strong> ';
    for (const c of creators) {
      const color = CREATOR_COLORS[c] || "#888";
      leg += `<span class="item"><span class="dot" style="background:${color}"></span>${c}</span>`;
    }
    leg += `<span class="size">// BUBBLE SIZE = OUTPUT TOKENS (M) · HOVER FOR DETAILS</span>`;
    const legendEl = container.parentElement.querySelector('.viz-legend');
    if (legendEl) legendEl.innerHTML = leg;
  }

  window.VIZ_REGISTRY = window.VIZ_REGISTRY || [];
  window.VIZ_REGISTRY.push({
    id: '01',
    name: 'The Crossover',
    subtitle: 'IQ × Cost × Output Tokens',
    render
  });
})();
