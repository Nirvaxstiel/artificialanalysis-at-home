// viz/04-provider-archetypes.js
// Small-multiples radar chart: 4 metrics per creator (IQ, cost, speed, tokens)

(function() {
  const CREATOR_COLORS = window.CREATOR_COLORS || {};

  function render(container, data) {
    const models = data.filter(m =>
      m.intel != null && m.cost_per_task != null && m.cost_per_task > 0
      && m.speed_tps != null && m.tokens_m != null && m.tokens_m > 0
    );

    // Group by creator
    const byCreator = {};
    for (const m of models) {
      if (!byCreator[m.creator]) byCreator[m.creator] = [];
      byCreator[m.creator].push(m);
    }

    // Build creator archetypes: average metrics per creator
    const archetypes = [];
    for (const [creator, ms] of Object.entries(byCreator)) {
      const avgIQ = ms.reduce((s, m) => s + m.intel, 0) / ms.length;
      const avgCost = ms.reduce((s, m) => s + m.cost_per_task, 0) / ms.length;
      const avgSpeed = ms.reduce((s, m) => s + m.speed_tps, 0) / ms.length;
      const avgTokens = ms.reduce((s, m) => s + m.tokens_m, 0) / ms.length;
      const costEff = 1 / avgCost;          // higher = better
      const verbEff = 1 / avgTokens;         // higher = better (fewer tokens)
      archetypes.push({ creator, avgIQ, avgCost, avgSpeed, avgTokens, costEff, verbEff, count: ms.length });
    }

    // Sort by avg IQ descending
    archetypes.sort((a, b) => b.avgIQ - a.avgIQ);

    // Global min/max for normalization across creators (for each raw metric)
    const allIQ = archetypes.map(a => a.avgIQ);
    const allCostEff = archetypes.map(a => a.costEff);
    const allSpeed = archetypes.map(a => a.avgSpeed);
    const allVerbEff = archetypes.map(a => a.verbEff);

    const mn = arr => Math.min(...arr);
    const mx = arr => Math.max(...arr);
    const norm = (v, lo, hi) => hi === lo ? 0.5 : (v - lo) / (hi - lo);

    const iqLo = mn(allIQ), iqHi = mx(allIQ);
    const ceLo = mn(allCostEff), ceHi = mx(allCostEff);
    const spLo = mn(allSpeed), spHi = mx(allSpeed);
    const veLo = mn(allVerbEff), veHi = mx(allVerbEff);

    // Axes definition: 4 axes at 0°, 90°, 180°, 270° (top, right, bottom, left)
    const AXES = [
      { label: 'IQ',           angle: -Math.PI / 2 },  // top
      { label: 'COST EFF',     angle: 0 },              // right
      { label: 'SPEED',        angle: Math.PI / 2 },    // bottom
      { label: 'VERBOSITY',    angle: Math.PI },        // left
    ];

    const R = 80;       // radar radius
    const CX = 130;     // center x within each panel (wider viewBox for label room)
    const CY = 130;     // center y within each panel
    const COLS = 4;

    // CSS
    let html = `<style>
      .radar-grid {
        display: grid;
        grid-template-columns: repeat(${COLS}, 1fr);
        gap: 0;
      }
      .radar-panel {
        background: var(--panel, #111);
        border: 1px solid var(--border, #f5f5f0);
        padding: 12px;
        text-align: center;
        position: relative;
        box-shadow: 4px 4px 0 rgba(182,255,60,0.25);
      }
      .radar-panel .creator-name {
        font-size: 12px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--fg, #f5f5f0);
        margin-bottom: 4px;
      }
      .radar-panel .radar-stats {
        font-size: 10px;
        color: var(--muted, #888);
        margin-top: 4px;
        line-height: 1.4;
      }
      .radar-panel .radar-stats .val {
        color: var(--neon, #b6ff3c);
        font-weight: 700;
      }
      .radar-axis-label {
        font-size: 8px;
        fill: var(--muted, #888);
        font-family: 'IBM Plex Mono', 'JetBrains Mono', monospace;
        font-weight: 700;
        text-transform: uppercase;
      }
      .radar-grid-line {
        fill: none;
        stroke: rgba(245,245,240,0.08);
        stroke-width: 0.5;
      }
      .radar-axis-line {
        stroke: rgba(245,245,240,0.12);
        stroke-width: 0.5;
      }
    </style>`;

    html += '<div class="radar-grid">';

    for (const a of archetypes) {
      const values = [
        norm(a.avgIQ, iqLo, iqHi),
        norm(a.costEff, ceLo, ceHi),
        norm(a.avgSpeed, spLo, spHi),
        norm(a.verbEff, veLo, veHi),
      ];

      // Build radar SVG
      let svg = `<svg viewBox="0 0 ${CX * 2} ${CY * 2}">`;

      // Grid rings (0.25, 0.5, 0.75, 1.0)
      for (const frac of [0.25, 0.5, 0.75, 1.0]) {
        const pts = AXES.map(ax => {
          const x = CX + Math.cos(ax.angle) * R * frac;
          const y = CY + Math.sin(ax.angle) * R * frac;
          return `${x},${y}`;
        }).join(' ');
        svg += `<polygon class="radar-grid-line" points="${pts}"/>`;
      }

      // Axis lines
      for (const ax of AXES) {
        const ex = CX + Math.cos(ax.angle) * R;
        const ey = CY + Math.sin(ax.angle) * R;
        svg += `<line class="radar-axis-line" x1="${CX}" y1="${CY}" x2="${ex}" y2="${ey}"/>`;
      }

      // Data polygon
      const dataPts = AXES.map((ax, i) => {
        const v = values[i];
        const x = CX + Math.cos(ax.angle) * R * v;
        const y = CY + Math.sin(ax.angle) * R * v;
        return `${x},${y}`;
      }).join(' ');

      const color = CREATOR_COLORS[a.creator] || '#888';
      svg += `<polygon points="${dataPts}" fill="${color}" fill-opacity="0.25" stroke="${color}" stroke-width="1.5"/>`;

      // Data points (dots)
      for (let i = 0; i < AXES.length; i++) {
        const v = values[i];
        const x = CX + Math.cos(AXES[i].angle) * R * v;
        const y = CY + Math.sin(AXES[i].angle) * R * v;
        svg += `<circle cx="${x}" cy="${y}" r="3" fill="${color}" stroke="#000" stroke-width="1"/>`;
      }

      // Axis labels
      for (let i = 0; i < AXES.length; i++) {
        const ax = AXES[i];
        const lx = CX + Math.cos(ax.angle) * (R + 10);
        const ly = CY + Math.sin(ax.angle) * (R + 10);
        let anchor = 'middle';
        if (ax.angle === 0) anchor = 'start';
        else if (ax.angle === Math.PI) anchor = 'end';
        let dy = '0.35em';
        if (ax.angle === -Math.PI / 2) dy = '0';
        if (ax.angle === Math.PI / 2) dy = '1em';
        svg += `<text class="radar-axis-label" x="${lx}" y="${ly}" text-anchor="${anchor}" dy="${dy}">${ax.label}</text>`;
      }

      svg += '</svg>';

      html += `
        <div class="radar-panel">
          <div class="creator-name" style="color:${color}">${a.creator}</div>
          ${svg}
          <div class="radar-stats">
            IQ <span class="val">${a.avgIQ.toFixed(1)}</span> · 
            $/task <span class="val">$${a.avgCost.toFixed(3)}</span> · 
            <span class="val">${a.count}</span> model${a.count > 1 ? 's' : ''}
          </div>
        </div>`;
    }

    html += '</div>';

    container.innerHTML = html;

    // Legend
    const legendEl = container.parentElement.querySelector('.viz-legend');
    if (legendEl) {
      let leg = '<strong style="color:var(--neon);">AXES</strong> ';
      leg += '<span class="item">// IQ</span> ';
      leg += '<span class="item">// COST EFF (1/cost)</span> ';
      leg += '<span class="item">// SPEED (tok/s)</span> ';
      leg += '<span class="item">// VERBOSITY (1/tokens)</span> ';
      leg += '<span class="size">// SORTED BY AVG IQ DESC · NORMALIZED PER-AXIS</span>';
      legendEl.innerHTML = leg;
    }
  }

  window.VIZ_REGISTRY = window.VIZ_REGISTRY || [];
  window.VIZ_REGISTRY.push({
    id: '03',
    name: 'Provider Archetypes',
    subtitle: 'Radar grid: IQ × Cost × Speed × Verbosity',
    render
  });
})();
