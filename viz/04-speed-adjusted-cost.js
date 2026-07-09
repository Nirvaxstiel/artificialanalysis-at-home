// Speed-adjusted cost: cost-per-wall-clock-second vs Intelligence Index

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

    const pts = data.filter(m => m.cost_per_wallsec != null && m.cost_per_wallsec > 0
      && m.tokens_m != null && m.intel != null);

    if (pts.length === 0) {
      window.VIZ_HELPERS.renderEmptyState(container,
        `No models with speed-adjusted cost data. This view needs <code>cost_per_wallsec</code> + <code>tokens_m</code> + <code>intel</code>.`);
      return;
    }

    // Dynamic axis range from data
    const vals = pts.map(m => m.cost_per_wallsec);
    const minWallSec = Math.pow(10, Math.floor(Math.log10(Math.min(...vals))));
    const maxWallSec = Math.pow(10, Math.ceil(Math.log10(Math.max(...vals))));
    const minIQ = Math.floor(Math.min(...pts.map(m => m.intel)) / 10) * 10;
    const maxIQ = Math.ceil(Math.max(...pts.map(m => m.intel)) / 10) * 10;
    const minTok = Math.max(10, Math.floor(Math.min(...pts.map(m => m.tokens_m)) / 10) * 10);
    const maxTok = Math.ceil(Math.max(...pts.map(m => m.tokens_m)) / 10) * 10;

    const xScale = c => M.left + (Math.log10(c) - Math.log10(minWallSec)) / (Math.log10(maxWallSec) - Math.log10(minWallSec)) * innerW;
    const yScale = i => M.top + (1 - (i - minIQ) / (maxIQ - minIQ)) * innerH;
    const rScale = t => 4 + Math.sqrt((t - minTok) / (maxTok - minTok)) * 22;

    // Generate wall-sec tick marks (log10 steps)
    const wallSecTicks = [];
    for (let p = Math.log10(minWallSec); p <= Math.log10(maxWallSec); p += 1) {
      wallSecTicks.push(Math.pow(10, p));
    }
    const iqTicks = [];
    for (let i = minIQ; i <= maxIQ; i += 10) {
      iqTicks.push(i);
    }

    let svg = '';

    // Sweet-spot: bottom-left quadrant (cheapest + smartest)
    const qMidX = xScale(Math.pow(10, (Math.log10(minWallSec) + Math.log10(maxWallSec)) / 2));
    const qMidY = yScale((minIQ + maxIQ) / 2);
    svg += `<rect x="${M.left}" y="${M.top}" width="${qMidX - M.left}" height="${qMidY - M.top}" fill="rgba(182,255,60,0.04)" stroke="rgba(182,255,60,0.25)" stroke-dasharray="4 4"/>`;
    svg += `<text x="${M.left + 6}" y="${M.top + 14}" fill="#b6ff3c" font-size="10" font-family="monospace">// SWEET SPOT: fast + cheap + smart</text>`;

    for (const t of wallSecTicks) {
      const x = xScale(t);
      svg += `<line class="grid" x1="${x}" y1="${M.top}" x2="${x}" y2="${H - M.bottom}" stroke="#333" stroke-dasharray="2 4"/>`;
    }
    for (const t of iqTicks) {
      const y = yScale(t);
      svg += `<line class="grid" x1="${M.left}" y1="${y}" x2="${W - M.right}" y2="${y}" stroke="#333" stroke-dasharray="2 4"/>`;
    }

    // Reference line at $1e-06/sec (micro-dollar threshold)
    // Axes
    svg += `<g class="axis">`;
    for (const t of wallSecTicks) {
      const x = xScale(t);
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

    for (const m of pts) {
      const cx = xScale(m.cost_per_wallsec);
      const cy = yScale(m.intel);
      const r = rScale(m.tokens_m);
      const fill = CREATOR_COLORS[m.creator] || "#888";
      const stroke = CREATOR_BORDER[m.creator] || "#000";
      svg += `<circle class="point" data-slug="${m.slug}" cx="${cx}" cy="${cy}" r="${r}" fill="${fill}" fill-opacity="0.7" stroke="${stroke}" stroke-width="1.5"></circle>`;
      svg += `<circle class="point" data-slug="${m.slug}" cx="${cx}" cy="${cy}" r="${Math.max(r + 5, 8)}" fill="transparent" stroke="none" style="pointer-events:all"></circle>`;
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

    container.innerHTML = `<svg viewBox="0 0 ${W} ${H}">${svg}</svg>` + window.VIZ_HELPERS.renderCoverageNote(container, pts.length, data.length, 'cost_per_wallsec + intel + tokens_m');

    if (window.__legendFilter) {
      const slugOpacity = {};
      data.forEach(m => { slugOpacity[m.slug] = window.__modelOpacity(m); });
      const hideMode = window.__filterMode === 'hide';
      container.querySelectorAll('[data-slug]').forEach(el => {
        const op = slugOpacity[el.dataset.slug];
        if (op !== undefined && op < 1) {
          if (hideMode && op === 0) {
            el.style.display = 'none';
          } else {
            el.style.opacity = op;
          }
        }
      });
    }

    wireTooltips(container, data, '.point, .label');

    const creators = [...new Set(pts.map(p => p.creator))].sort();
    let leg = '<strong style="color:var(--neon);">CREATOR</strong> ';
    for (const c of creators) {
      const color = CREATOR_COLORS[c] || "#888";
      leg += `<span class="item"><span class="dot" style="background:${color}"></span>${c}</span>`;
    }
    leg += `<span class="size">// BUBBLE SIZE = OUTPUT TOKENS (M) · SWEET SPOT = FAST + CHEAP + SMART</span>`;
    const legendEl = container.parentElement.querySelector('.viz-legend');
    if (legendEl) legendEl.innerHTML = '';
  }

  window.VIZ_REGISTRY = window.VIZ_REGISTRY || [];
  window.VIZ_REGISTRY.push({
    id: '04',
    name: 'Speed-Adjusted Cost',
    subtitle: 'Cost per wall-clock second × IQ',
    render
  });
})();
