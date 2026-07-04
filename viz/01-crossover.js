// viz/01-crossover.js
// Merger of 01 (bubble) + 03 (pareto frontier x reasoning tax).
// Single scatter: toggle coloring between creator / reasoning-tax.
// Always draws pareto frontier.

(function() {
  const CREATOR_COLORS = window.CREATOR_COLORS;
  const CREATOR_BORDER = window.CREATOR_BORDER || {};
  const { wireTooltips, placeLabel } = window.VIZ_HELPERS || {};

  const REASONING_COLORS = {
    low:  '#b6ff3c',
    mid:  '#ff6a00',
    high: '#ff3366',
    none: '#888888'
  };

  function reasoningColor(pct) {
    if (pct == null) return REASONING_COLORS.none;
    if (pct < 20) return REASONING_COLORS.low;
    if (pct <= 50) return REASONING_COLORS.mid;
    return REASONING_COLORS.high;
  }

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

    // Read coloring mode from container state (default=creator)
    const colorMode = container.__colorMode || 'creator';

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

    // Pareto frontier — collect & sort pareto_optimal models by cost ascending
    const paretoModels = data
      .filter(m => m.pareto_optimal && m.cost_per_task != null && m.intel != null)
      .sort((a, b) => a.cost_per_task - b.cost_per_task);

    if (paretoModels.length > 1) {
      const pts_pareto = paretoModels.map(m => `${xScale(m.cost_per_task)},${yScale(m.intel)}`).join(' ');
      svg += `<polyline points="${pts_pareto}" fill="none" stroke="#fff" stroke-width="1.5" stroke-dasharray="6 4" stroke-opacity="0.7"/>`;
    }

    // Diamond markers on pareto vertices
    for (const m of paretoModels) {
      const cx = xScale(m.cost_per_task);
      const cy = yScale(m.intel);
      const s = 4;
      const diamond = `${cx},${cy - s} ${cx + s},${cy} ${cx},${cy + s} ${cx - s},${cy}`;
      svg += `<polygon points="${diamond}" fill="#fff" fill-opacity="0.9" stroke="#000" stroke-width="1"/>`;
    }

    // Points
    for (const m of pts) {
      const cx = xScale(m.cost_per_task);
      const cy = yScale(m.intel);
      const r = rScale(m.tokens_m);
      let fill, stroke, opacity;
      if (colorMode === 'reasoning') {
        fill = reasoningColor(m.reasoning_tax_pct);
        stroke = '#000';
        opacity = 0.75;
      } else {
        fill = CREATOR_COLORS[m.creator] || "#888";
        stroke = CREATOR_BORDER[m.creator] || "#000";
        opacity = 0.7;
      }
      svg += `<circle class="point" data-slug="${m.slug}" cx="${cx}" cy="${cy}" r="${r}" fill="${fill}" fill-opacity="${opacity}" stroke="${stroke}" stroke-width="1.5"></circle>`;
    }

    // Labels — only on pareto-optimal models to reduce clutter
    const labelPositions = [];
    for (const m of paretoModels) {
      const cx = xScale(m.cost_per_task);
      const cy = yScale(m.intel);
      const r = rScale(m.tokens_m);
      const placed = placeLabel(cx, cy, r, m.name, labelPositions, {});
      if (!placed) continue;
      const cleanName = m.name.replace(/\s*\((xhigh|high|medium|low|with fallback|max)\)\s*/i, '');
      svg += `<text class="label" x="${placed.x}" y="${placed.y}" text-anchor="${placed.anchor}" font-size="9" font-weight="700" fill="#f5f5f0" stroke="#000" stroke-width="2.5" paint-order="stroke" data-slug="${m.slug}">${cleanName}</text>`;
    }

    // Legend — bottom-right: depends on color mode
    const legendW = 260, legendH = colorMode === 'reasoning' ? 90 : 45;
    const legendX = W - M.right - legendW - 4;
    const legendY = H - M.bottom - legendH - 4;
    let legend = `<g transform="translate(${legendX},${legendY})">`;
    legend += `<rect x="0" y="0" width="${legendW}" height="${legendH}" fill="#111" stroke="#444" stroke-width="1" rx="0"/>`;

    if (colorMode === 'reasoning') {
      legend += `<text x="10" y="16" fill="var(--neon,#b6ff3c)" font-size="10" font-weight="800" font-family="monospace">REASONING TAX %</text>`;
      legend += `<rect x="10" y="24" width="12" height="12" fill="${REASONING_COLORS.low}" stroke="#000" stroke-width="1"/>`;
      legend += `<text x="28" y="34" fill="#ccc" font-size="9" font-family="monospace">&lt;20%</text>`;
      legend += `<rect x="10" y="40" width="12" height="12" fill="${REASONING_COLORS.mid}" stroke="#000" stroke-width="1"/>`;
      legend += `<text x="28" y="50" fill="#ccc" font-size="9" font-family="monospace">20–50%</text>`;
      legend += `<rect x="10" y="56" width="12" height="12" fill="${REASONING_COLORS.high}" stroke="#000" stroke-width="1"/>`;
      legend += `<text x="28" y="66" fill="#ccc" font-size="9" font-family="monospace">&gt;50%</text>`;
      legend += `<rect x="130" y="24" width="12" height="12" fill="${REASONING_COLORS.none}" stroke="#000" stroke-width="1"/>`;
      legend += `<text x="148" y="34" fill="#ccc" font-size="9" font-family="monospace">No data</text>`;
    } else {
      // Creator legend — top creators only
      const topCreators = [...new Set(pts.map(p => p.creator))].sort();
      legend += `<text x="10" y="18" fill="var(--neon,#b6ff3c)" font-size="9" font-weight="800" font-family="monospace">CREATOR COLOR</text>`;
      let ly = 30;
      for (const c of topCreators) {
        const color = CREATOR_COLORS[c] || "#888";
        legend += `<rect x="10" y="${ly}" width="10" height="10" fill="${color}" stroke="#f5f5f0" stroke-width="1"/>`;
        legend += `<text x="26" y="${ly + 9}" fill="#ccc" font-size="8" font-family="monospace">${c}</text>`;
        ly += 14;
        if (ly > legendH - 6) break;
      }
    }
    legend += `<line x1="130" y1="${legendH - 26}" x2="170" y2="${legendH - 26}" stroke="#fff" stroke-width="1.5" stroke-dasharray="4 3"/>`;
    legend += `<text x="178" y="${legendH - 22}" fill="#ccc" font-size="9" font-family="monospace">Pareto frontier</text>`;

    // Color mode indicator
    legend += `<text x="10" y="${legendH - 6}" fill="#888" font-size="7" font-family="monospace">Color: ${colorMode.toUpperCase()}</text>`;
    legend += `</g>`;

    container.innerHTML = `<svg viewBox="0 0 ${W} ${H}">${svg}${legend}</svg>`;

    // Wire tooltips
    wireTooltips(container, data, '.point, .label');

    // Wire color-mode toggle
    _wireToggle(container, data);
  }

  function _wireToggle(container, data) {
    // Remove any existing toggle UI (it's a sibling, not inside container)
    const parent = container.parentElement;
    const existing = parent && parent.querySelector('.color-toggle-row');
    if (existing) existing.remove();

    const div = document.createElement('div');
    div.className = 'color-toggle-row';
    div.style.cssText = 'display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap;';

    div.innerHTML = `
      <span style="color:var(--muted,#888);font-size:10px;text-transform:uppercase;letter-spacing:0.08em;font-weight:700;">Color by:</span>
      <button class="color-toggle-btn ${container.__colorMode === 'creator' ? 'active' : ''}" data-mode="creator">Creator</button>
      <button class="color-toggle-btn ${container.__colorMode === 'reasoning' ? 'active' : ''}" data-mode="reasoning">Reasoning Tax %</button>
      <span style="color:#666;font-size:8px;margin-left:auto;">BUBBLE SIZE = OUTPUT TOKENS (M) · HOVER FOR DETAILS</span>
    `;

    if (parent) parent.insertBefore(div, container);

    div.querySelectorAll('.color-toggle-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        container.__colorMode = btn.dataset.mode;
        render(container, data);
      });
    });
  }

  window.VIZ_REGISTRY = window.VIZ_REGISTRY || [];
  window.VIZ_REGISTRY.push({
    id: '01',
    name: 'The Crossover',
    subtitle: 'IQ × Cost × Output Tokens — toggle coloring',
    render
  });
})();
