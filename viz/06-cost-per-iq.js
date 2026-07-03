// viz/06-cost-per-iq.js
// Vertical bar chart ranking all models by cost per IQ point

(function() {
  const CREATOR_COLORS = {
    "OpenAI":     "#f5f5f0",
    "Google":     "#4285F4",
    "Anthropic":  "#D97757",
    "DeepSeek":   "#536dfe",
    "MiniMax":    "#b6ff3c",
    "xAI":        "#9e9e9e",
    "NVIDIA":     "#76b900",
    "Kimi":       "#00e5ff",
    "Alibaba":    "#ff6a00",
    "Z AI":       "#a855f7",
    "Xiaomi":     "#ff5722",
    "Amazon":     "#ff9900",
    "Mistral":    "#000000",
    "Meta":       "#1877f2"
  };
  const CREATOR_BORDER = { "Mistral": "#f5f5f0" };

  function render(container, data) {
    const W = 1200, H = 650;
    const M = { top: 40, right: 30, bottom: 140, left: 80 };
    const innerW = W - M.left - M.right;
    const innerH = H - M.top - M.bottom;

    // Filter to models with valid data
    const pts = data.filter(m => m.cost_per_task != null && m.intel != null && m.cost_per_task > 0);

    // Compute cost per IQ point and sort ascending
    const models = pts.map(m => ({
      ...m,
      cost_per_iq: m.cost_per_task / m.intel
    })).sort((a, b) => a.cost_per_iq - b.cost_per_iq);

    if (models.length === 0) {
      container.innerHTML = '<p style="color:var(--muted);font-family:monospace;padding:40px;text-align:center">// NO DATA WITH BOTH cost_per_task AND intel</p>';
      return;
    }

    // Log-scale Y axis
    const minVal = models[0].cost_per_iq;
    const maxVal = models[models.length - 1].cost_per_iq;
    const logMin = Math.floor(Math.log10(minVal) * 10) / 10;
    const logMax = Math.ceil(Math.log10(maxVal) * 10) / 10;

    const yScale = v => {
      if (v <= 0) return innerH;
      const logV = Math.log10(v);
      return innerH - ((logV - logMin) / (logMax - logMin)) * innerH;
    };

    const barW = Math.max(8, Math.min(28, (innerW - models.length * 2) / models.length));
    const gap = Math.max(2, (innerW - barW * models.length) / (models.length + 1));

    // Median
    const sortedCosts = models.map(m => m.cost_per_iq).sort((a, b) => a - b);
    const median = sortedCosts.length % 2 === 0
      ? (sortedCosts[sortedCosts.length / 2 - 1] + sortedCosts[sortedCosts.length / 2]) / 2
      : sortedCosts[Math.floor(sortedCosts.length / 2)];

    const medianY = yScale(median);

    // Y-axis log ticks
    const yTicks = [];
    for (let e = Math.floor(logMin); e <= Math.ceil(logMax); e++) {
      for (const m of [1, 2, 5]) {
        const val = m * Math.pow(10, e);
        if (Math.log10(val) >= logMin && Math.log10(val) <= logMax) {
          yTicks.push(val);
        }
      }
    }

    let svg = '';

    // Grid lines
    for (const t of yTicks) {
      const y = yScale(t);
      svg += `<line class="grid" x1="${M.left}" y1="${y}" x2="${W - M.right}" y2="${y}"/>`;
    }

    // Bars
    const modelBySlug = Object.fromEntries(data.map(m => [m.slug, m]));
    models.forEach((m, i) => {
      const x = M.left + gap + i * (barW + gap);
      const y = yScale(m.cost_per_iq);
      const h = innerH - y;
      const fill = CREATOR_COLORS[m.creator] || "#888";
      const stroke = CREATOR_BORDER[m.creator] || "#000";

      svg += `<rect class="bar" data-slug="${m.slug}" x="${x}" y="${y}" width="${barW}" height="${h}" fill="${fill}" fill-opacity="0.8" stroke="${stroke}" stroke-width="1"/>`;

      // Value label on top
      const label = '$' + m.cost_per_iq.toFixed(4);
      svg += `<text class="val-label" data-slug="${m.slug}" x="${x + barW / 2}" y="${y - 4}" text-anchor="middle" font-size="8" font-weight="700" fill="#f5f5f0" stroke="#000" stroke-width="2.5" paint-order="stroke">${label}</text>`;

      // X-axis model name (rotated)
      const cleanName = m.name.replace(/\s*\((xhigh|high|medium|low|with fallback|max)\)\s*/i, '');
      svg += `<text x="${x + barW / 2}" y="${innerH + 12}" text-anchor="end" font-size="9" font-weight="600" fill="var(--fg, #f5f5f0)" transform="rotate(-45 ${x + barW / 2} ${innerH + 12})">${cleanName}</text>`;

      // Creator color dot below name
      svg += `<circle cx="${x + barW / 2}" cy="${innerH + 8}" r="2" fill="${fill}"/>`;
    });

    // Median reference line
    svg += `<line x1="${M.left}" y1="${medianY}" x2="${W - M.right}" y2="${medianY}" stroke="var(--neon2, #b6ff3c)" stroke-width="1.5" stroke-dasharray="6 4"/>`;
    svg += `<text x="${W - M.right + 4}" y="${medianY + 3}" font-size="9" font-weight="700" fill="var(--neon2, #b6ff3c)" font-family="monospace">// MEDIAN: $${median.toFixed(4)}</text>`;

    // Best value label (cheapest bar)
    const cheapest = models[0];
    const cheapestX = M.left + gap;
    const cheapestY = yScale(cheapest.cost_per_iq);
    svg += `<text x="${cheapestX + barW / 2}" y="${cheapestY - 16}" text-anchor="middle" font-size="9" font-weight="800" fill="var(--neon, #b6ff3c)" font-family="monospace">// BEST VALUE</text>`;

    // Most expensive label
    const mostExpensive = models[models.length - 1];
    const expensiveX = M.left + gap + (models.length - 1) * (barW + gap);
    const expensiveY = yScale(mostExpensive.cost_per_iq);
    svg += `<text x="${expensiveX + barW / 2}" y="${expensiveY - 16}" text-anchor="middle" font-size="8" font-weight="800" fill="#D97757" font-family="monospace">// MOST EXPENSIVE PER IQ</text>`;

    // Y-axis ticks
    svg += `<g class="axis">`;
    for (const t of yTicks) {
      const y = yScale(t);
      let label;
      if (t >= 0.01) label = '$' + t.toFixed(2);
      else label = '$' + t.toFixed(4);
      svg += `<text x="${M.left - 8}" y="${y + 3}" text-anchor="end" font-size="9">${label}</text>`;
      svg += `<line x1="${M.left - 4}" y1="${y}" x2="${M.left}" y2="${y}"/>`;
    }
    svg += `<text x="16" y="${M.top + innerH / 2}" text-anchor="middle" font-weight="800" font-size="12" font-family="monospace" transform="rotate(-90 16 ${M.top + innerH / 2})">COST PER IQ POINT (USD, LOG)</text>`;
    svg += `<text x="${M.left + innerW / 2}" y="${H - 8}" text-anchor="middle" font-weight="800" font-size="12" font-family="monospace">MODEL (SORTED BY COST EFFICIENCY →)</text>`;
    svg += `</g>`;

    // Title
    svg += `<text x="${M.left}" y="${M.top - 14}" font-size="14" font-weight="800" fill="var(--neon, #b6ff3c)" font-family="monospace">COST PER IQ POINT — RANKED</text>`;

    container.innerHTML = `<svg viewBox="0 0 ${W} ${H}">${svg}</svg>`;

    // Wire tooltips
    const tt = window.getTooltipEl();
    container.querySelectorAll('.bar, .val-label').forEach(el => {
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

    // Legend
    const creators = [...new Set(models.map(p => p.creator))].sort();
    let leg = '<strong style="color:var(--neon);">CREATOR</strong> ';
    for (const c of creators) {
      const color = CREATOR_COLORS[c] || "#888";
      leg += `<span class="item"><span class="dot" style="background:${color}"></span>${c}</span>`;
    }
    leg += `<span class="size">// Y-AXIS = COST / IQ POINT (LOG SCALE) · HOVER FOR DETAILS</span>`;
    const legendEl = container.parentElement.querySelector('.viz-legend');
    if (legendEl) legendEl.innerHTML = leg;
  }

  window.VIZ_REGISTRY = window.VIZ_REGISTRY || [];
  window.VIZ_REGISTRY.push({
    id: '06',
    name: 'Cost per IQ Point',
    subtitle: 'How much you pay per intelligence unit',
    render
  });
})();
