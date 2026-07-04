// viz/05-speed-cost.js
// Speed-adjusted cost: cost-per-wall-clock-second vs Intelligence Index
// The "is this model worth waiting for?" chart.

(function() {
  const CREATOR_COLORS = window.CREATOR_COLORS;
  const CREATOR_BORDER = window.CREATOR_BORDER || {};
  const { wireTooltips, placeLabel } = window.VIZ_HELPERS || {};

  // Sweet-spot models: fast + cheap + smart (low cost_per_wallsec, high intel)
  const SWEET_SPOT_SLUGS = new Set([
    "deepseek-v4-pro",
    "deepseek-v4-flash",
    "minimax-m3",
    "kimi-k2.6",
    "glm-5.2",
    "mimo-v2.5-pro"
  ]);

  function render(container, data) {
    const W = 1100; const H = 600;
    const M = { top: 30, right: 30, bottom: 50, left: 60 };
    const innerW = W - M.left - M.right;
    const innerH = H - M.top - M.bottom;

    // Filter to models with cost_per_wallsec data
    const pts = data.filter(m => m.cost_per_wallsec != null && m.cost_per_wallsec > 0
      && m.tokens_m != null && m.intel != null);

    // Scales
    const minWallSec = 5e-9, maxWallSec = 1e-5;  // log range for X
    const minIQ = 10, maxIQ = 80;
    const minTok = 30, maxTok = 320;

    const xScale = c => M.left + (Math.log10(c) - Math.log10(minWallSec)) / (Math.log10(maxWallSec) - Math.log10(minWallSec)) * innerW;
    const yScale = i => M.top + (1 - (i - minIQ) / (maxIQ - minIQ)) * innerH;
    const rScale = t => 4 + Math.sqrt((t - minTok) / (maxTok - minTok)) * 22;

    // Grid ticks
    const wallSecTicks = [1e-08, 1e-07, 1e-06, 1e-05];
    const iqTicks = [10, 20, 30, 40, 50, 60, 70, 80];

    let svg = '';

    // Sweet-spot quadrant: low cost + high IQ (left of $1e-06, above IQ 40)
    const qLeft = xScale(minWallSec);
    const qRight = xScale(1e-06);
    const qTop = yScale(80);
    const qBottom = yScale(40);
    svg += `<rect x="${qLeft}" y="${qTop}" width="${qRight - qLeft}" height="${qBottom - qTop}" fill="rgba(182,255,60,0.04)" stroke="rgba(182,255,60,0.25)" stroke-dasharray="4 4"/>`;
    svg += `<text x="${qLeft + 6}" y="${qTop + 14}" fill="#b6ff3c" font-size="10" font-family="monospace">// SWEET SPOT: fast + cheap + smart</text>`;

    // Grid lines (dashed, subtle)
    for (const t of wallSecTicks) {
      const x = xScale(t);
      svg += `<line class="grid" x1="${x}" y1="${M.top}" x2="${x}" y2="${H - M.bottom}" stroke="#333" stroke-dasharray="2 4"/>`;
    }
    for (const t of iqTicks) {
      const y = yScale(t);
      svg += `<line class="grid" x1="${M.left}" y1="${y}" x2="${W - M.right}" y2="${y}" stroke="#333" stroke-dasharray="2 4"/>`;
    }

    // Reference line at $1e-06/sec (micro-dollar threshold)
    const refX = xScale(1e-06);
    svg += `<line x1="${refX}" y1="${M.top}" x2="${refX}" y2="${H - M.bottom}" stroke="#ff3333" stroke-width="1.5" stroke-dasharray="6 3"/>`;
    svg += `<text x="${refX + 4}" y="${M.top + 12}" fill="#ff3333" font-size="9" font-family="monospace" font-weight="700">$0.000001/sec threshold</text>`;

    // Axes
    svg += `<g class="axis">`;
    for (const t of wallSecTicks) {
      const x = xScale(t);
      // No scientific notation — use full decimal
      let label;
      if (t >= 1) label = '$' + t.toFixed(2);
      else if (t >= 0.01) label = '$' + t.toFixed(4);
      else if (t >= 1e-06) label = '$' + t.toFixed(6);
      else if (t >= 1e-08) label = '$' + t.toFixed(8);
      else label = '$' + t.toExponential(2);
      svg += `<text x="${x}" y="${H - M.bottom + 18}" text-anchor="middle" fill="#888" font-size="10">${label}</text>`;
      svg += `<line x1="${x}" y1="${H - M.bottom}" x2="${x}" y2="${H - M.bottom + 4}" stroke="#888"/>`;
    }
    for (const t of iqTicks) {
      svg += `<text x="${M.left - 8}" y="${yScale(t) + 3}" text-anchor="end" fill="#888" font-size="10">${t}</text>`;
      svg += `<line x1="${M.left - 4}" y1="${yScale(t)}" x2="${M.left}" y2="${yScale(t)}" stroke="#888"/>`;
    }
    svg += `<text x="${W/2}" y="${H - 8}" text-anchor="middle" font-weight="800" font-size="12" fill="#f5f5f0">COST PER WALL-CLOCK SECOND ($/sec, log)</text>`;
    svg += `<text x="14" y="${H/2}" text-anchor="middle" font-weight="800" font-size="12" fill="#f5f5f0" transform="rotate(-90 14 ${H/2})">INTELLIGENCE INDEX</text>`;
    svg += `</g>`;

    // Data points
    for (const m of pts) {
      const cx = xScale(m.cost_per_wallsec);
      const cy = yScale(m.intel);
      const r = rScale(m.tokens_m);
      const fill = CREATOR_COLORS[m.creator] || "#888";
      const stroke = CREATOR_BORDER[m.creator] || "#000";
      svg += `<circle class="point" data-slug="${m.slug}" cx="${cx}" cy="${cy}" r="${r}" fill="${fill}" fill-opacity="0.7" stroke="${stroke}" stroke-width="1.5"></circle>`;
    }

    // Annotation labels on sweet-spot models with collision avoidance
    const sweetPts = pts.filter(m => SWEET_SPOT_SLUGS.has(m.slug));
    const sortedByY = [...sweetPts].sort((a, b) => yScale(a.intel) - yScale(b.intel));
    const labelPositions = [];

    for (const m of sortedByY) {
      const cx = xScale(m.cost_per_wallsec);
      const cy = yScale(m.intel);
      const r = rScale(m.tokens_m);
      const placed = placeLabel(cx, cy, r, m.name, labelPositions, {});
      if (!placed) continue;
      const cleanName = m.name.replace(/\s*\((xhigh|high|medium|low|with fallback|max)\)\s*/i, '').trim();
      svg += `<text class="label" x="${placed.x}" y="${placed.y}" text-anchor="${placed.anchor}" font-size="9" font-weight="700" fill="#b6ff3c" stroke="#000" stroke-width="2.5" paint-order="stroke" data-slug="${m.slug}">${cleanName}</text>`;
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
    leg += `<span class="size">// BUBBLE SIZE = OUTPUT TOKENS (M) · SWEET SPOT = FAST + CHEAP + SMART</span>`;
    const legendEl = container.parentElement.querySelector('.viz-legend');
    if (legendEl) legendEl.innerHTML = leg;
  }

  window.VIZ_REGISTRY = window.VIZ_REGISTRY || [];
  window.VIZ_REGISTRY.push({
    id: '04',
    name: 'Speed-Adjusted Cost',
    subtitle: 'Cost per wall-clock second × IQ',
    render
  });
})();
