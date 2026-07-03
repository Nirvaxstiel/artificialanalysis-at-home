// viz/03-pareto-reasoning.js
// Pareto frontier scatter: bubbles colored by reasoning tax %

(function() {
  const REASONING_COLORS = {
    low:  '#b6ff3c',  // <20%
    mid:  '#ff6a00',  // 20-50%
    high: '#ff3366',  // >50%
    none: '#888888'   // no data
  };

  function reasoningColor(pct) {
    if (pct == null) return REASONING_COLORS.none;
    if (pct < 20) return REASONING_COLORS.low;
    if (pct <= 50) return REASONING_COLORS.mid;
    return REASONING_COLORS.high;
  }

  function render(container, data) {
    const W = 1100, H = 600;
    const M = { top: 30, right: 30, bottom: 50, left: 60 };
    const innerW = W - M.left - M.right;
    const innerH = H - M.top - M.bottom;

    const pts = data.filter(m => m.cost_per_task != null && m.cost_per_task > 0
      && m.tokens_m != null && m.intel != null);

    const minCost = 0.02, maxCost = 3.0;
    const minIQ = 10, maxIQ = 80;
    const minTok = 30, maxTok = 320;

    const xScale = c => M.left + (Math.log10(c) - Math.log10(minCost)) / (Math.log10(maxCost) - Math.log10(minCost)) * innerW;
    const yScale = i => M.top + (1 - (i - minIQ) / (maxIQ - minIQ)) * innerH;
    const rScale = t => 4 + Math.sqrt((t - minTok) / (maxTok - minTok)) * 22;

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
      const s = 4; // half-size of diamond
      const diamond = `${cx},${cy - s} ${cx + s},${cy} ${cx},${cy + s} ${cx - s},${cy}`;
      svg += `<polygon points="${diamond}" fill="#fff" fill-opacity="0.9" stroke="#000" stroke-width="1"/>`;
    }

    // Points
    for (const m of pts) {
      const cx = xScale(m.cost_per_task);
      const cy = yScale(m.intel);
      const r = rScale(m.tokens_m);
      const fill = reasoningColor(m.reasoning_tax_pct);
      svg += `<circle class="point" data-slug="${m.slug}" cx="${cx}" cy="${cy}" r="${r}" fill="${fill}" fill-opacity="0.75" stroke="#000" stroke-width="1.5"></circle>`;
    }

    // Labels — only on pareto-optimal models to reduce clutter
    const labelPositions = [];
    const labelGap = 4;
    for (const m of paretoModels) {
      const cx = xScale(m.cost_per_task);
      const cy = yScale(m.intel);
      const r = rScale(m.tokens_m);
      const text = m.name;
      const approxW = text.length * 5.5;
      const h = 11;
      const candidates = [
        { x: cx, y: cy - r - labelGap - h, anchor: 'middle' },
        { x: cx, y: cy + r + labelGap + 9, anchor: 'middle' },
        { x: cx + r + labelGap + 2, y: cy + 3, anchor: 'start' },
        { x: cx - r - labelGap - 2, y: cy + 3, anchor: 'end' },
      ];
      let placed = null;
      for (const c of candidates) {
        const lx = c.anchor === 'middle' ? c.x - approxW/2 : c.anchor === 'end' ? c.x - approxW : c.x;
        const rect = { x: lx, y: c.y - h, w: approxW, h: h + 2 };
        const collides = labelPositions.some(p => !(rect.x + rect.w + 2 < p.x || rect.x > p.x + p.w + 2 || rect.y + rect.h < p.y || rect.y > p.y + p.h));
        if (!collides) { placed = c; labelPositions.push(rect); break; }
      }
      if (!placed) {
        placed = { x: cx, y: cy - r - labelGap - h, anchor: 'middle' };
      }
      const cleanName = text.replace(/\s*\((xhigh|high|medium|low|with fallback|max)\)\s*/i, '');
      svg += `<text class="label" x="${placed.x}" y="${placed.y}" text-anchor="${placed.anchor}" font-size="9" font-weight="700" fill="#f5f5f0" stroke="#000" stroke-width="2.5" paint-order="stroke" data-slug="${m.slug}">${cleanName}</text>`;
    }

    // Legend — bottom-right reasoning tax color scale
    const legendW = 260, legendH = 90;
    const legendX = W - M.right - legendW - 4;
    const legendY = H - M.bottom - legendH - 4;
    let legend = `<g transform="translate(${legendX},${legendY})">`;
    legend += `<rect x="0" y="0" width="${legendW}" height="${legendH}" fill="#111" stroke="#444" stroke-width="1" rx="0"/>`;
    legend += `<text x="10" y="16" fill="var(--neon,#b6ff3c)" font-size="10" font-weight="800" font-family="monospace">REASONING TAX %</text>`;
    legend += `<rect x="10" y="24" width="12" height="12" fill="${REASONING_COLORS.low}" stroke="#000" stroke-width="1"/>`;
    legend += `<text x="28" y="34" fill="#ccc" font-size="9" font-family="monospace">&lt;20%</text>`;
    legend += `<rect x="10" y="40" width="12" height="12" fill="${REASONING_COLORS.mid}" stroke="#000" stroke-width="1"/>`;
    legend += `<text x="28" y="50" fill="#ccc" font-size="9" font-family="monospace">20–50%</text>`;
    legend += `<rect x="10" y="56" width="12" height="12" fill="${REASONING_COLORS.high}" stroke="#000" stroke-width="1"/>`;
    legend += `<text x="28" y="66" fill="#ccc" font-size="9" font-family="monospace">&gt;50%</text>`;
    legend += `<rect x="130" y="24" width="12" height="12" fill="${REASONING_COLORS.none}" stroke="#000" stroke-width="1"/>`;
    legend += `<text x="148" y="34" fill="#ccc" font-size="9" font-family="monospace">No data</text>`;
    legend += `<line x1="130" y1="50" x2="170" y2="50" stroke="#fff" stroke-width="1.5" stroke-dasharray="4 3"/>`;
    legend += `<text x="178" y="54" fill="#ccc" font-size="9" font-family="monospace">Pareto frontier</text>`;
    legend += `</g>`;

    container.innerHTML = `<svg viewBox="0 0 ${W} ${H}">${svg}${legend}</svg>`;

    // Wire tooltips
    const tt = window.getTooltipEl();
    const modelBySlug = Object.fromEntries(data.map(m => [m.slug, m]));
    container.querySelectorAll('.point, .label').forEach(el => {
      el.addEventListener('mouseenter', e => {
        const m = modelBySlug[el.dataset.slug];
        if (!m) return;
        tt.innerHTML = window.buildTooltip(m);
        tt.style.display = 'block';
      });
      el.addEventListener('mousemove', e => {
        const x = e.clientX + 16, y = e.clientY + 16;
        const w = tt.offsetWidth, h = tt.offsetHeight;
        tt.style.left = (x + w > window.innerWidth ? e.clientX - w - 16 : x) + 'px';
        tt.style.top  = (y + h > window.innerHeight ? e.clientY - h - 16 : y) + 'px';
      });
      el.addEventListener('mouseleave', () => { tt.style.display = 'none'; });
    });
  }

  window.VIZ_REGISTRY = window.VIZ_REGISTRY || [];
  window.VIZ_REGISTRY.push({
    id: '03',
    name: 'Pareto Frontier × Reasoning Tax',
    subtitle: 'Cost-efficient models colored by thinking overhead',
    render
  });
})();
