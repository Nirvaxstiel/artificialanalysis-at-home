// viz/04-provider-archetypes.js
// Small-multiples radar chart: 4 metrics per creator (IQ, cost, speed, tokens)

(function() {
  const CREATOR_COLORS = window.CREATOR_COLORS || {};

  function render(container, data) {
    const models = data.filter(m =>
      m.intel != null && m.cost_per_task != null && m.cost_per_task > 0
      && m.speed_tps != null && m.tokens_m != null && m.tokens_m > 0
    );

    // Group by creator, split into SKU variants
    const SKU_PATTERNS = window.SKU_PATTERNS || [];
    const byCreator = {};
    for (const m of models) {
      const slug = m.slug.toLowerCase();
      let suffix = '';
      for (const p of SKU_PATTERNS) {
        if (slug.includes(p.keyword)) { suffix = p.suffix; break; }
      }
      const key = m.creator + suffix;
      if (!byCreator[key]) byCreator[key] = [];
      byCreator[key].push(m);
    }

    // Build creator archetypes: average metrics per creator
    const archetypes = [];
    for (const [creator, ms] of Object.entries(byCreator)) {
      const avgIQ = ms.reduce((s, m) => s + m.intel, 0) / ms.length;
      const avgCost = ms.reduce((s, m) => s + m.cost_per_task, 0) / ms.length;
      const avgSpeed = ms.reduce((s, m) => s + m.speed_tps, 0) / ms.length;
      const avgTokens = ms.reduce((s, m) => s + m.tokens_m, 0) / ms.length;
      const costEff = 1 / avgCost;
      const tokenEff = 1 / avgTokens;    // higher = fewer tokens = more efficient
      // Cache efficiency: how much cheaper cached prompts are vs input
      const withCache = ms.filter(m => m.cache_hit_price != null && m.inp_price != null && m.inp_price > 0);
      const avgCacheEff = withCache.length ? withCache.reduce((s, m) => s + (1 - m.cache_hit_price / m.inp_price), 0) / withCache.length : 0;
      archetypes.push({ creator, avgIQ, avgCost, avgSpeed, avgTokens, costEff, tokenEff, avgCacheEff, count: ms.length });
    }

    // Sort alphabetically — keeps OSS variants next to parent
    archetypes.sort((a, b) => a.creator.localeCompare(b.creator));

    // Global min/max for normalization
    const allIQ = archetypes.map(a => a.avgIQ);
    const allCostEff = archetypes.map(a => a.costEff);
    const allSpeed = archetypes.map(a => a.avgSpeed);
    const allTokenEff = archetypes.map(a => a.tokenEff);
    const allCacheEff = archetypes.map(a => a.avgCacheEff);

    const mn = arr => 0;               // always start from 0
    const mx = arr => Math.max(...arr);
    const norm = (v, lo, hi) => hi === lo ? 0.5 : (v - lo) / (hi - lo);

    const iqLo = mn(allIQ), iqHi = mx(allIQ);
    const ceLo = mn(allCostEff), ceHi = mx(allCostEff);
    const spLo = mn(allSpeed), spHi = mx(allSpeed);
    const teLo = mn(allTokenEff), teHi = mx(allTokenEff);
    const caLo = mn(allCacheEff), caHi = mx(allCacheEff);

    const RADAR_AXES = window.RADAR_AXES || [];

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

    html += `<div style="font-size:10px;color:#888;font-family:monospace;margin-bottom:12px;padding:8px;border:1px dashed #333;">`;
    html += `<span style="color:#b6ff3c;font-weight:700">AXES</span> `;
    const axisLabels = (window.RADAR_AXES || []).map(a => a.label);
    html += axisLabels.map(l => `<span class="item">// ${l}</span>`).join(' ');
    html += `<span class="size" style="margin-left:12px">// SORTED ALPHABETICALLY · NORMALIZED 0–MAX</span>`;
    html += `</div>`;
    html += '<div class="radar-grid">';

    for (const a of archetypes) {
      const values = [
        norm(a.avgIQ, iqLo, iqHi),
        norm(a.avgSpeed, spLo, spHi),
        norm(a.tokenEff, teLo, teHi),
        norm(a.avgCacheEff, caLo, caHi),
        norm(a.costEff, ceLo, ceHi),
      ];

      // Build radar SVG
      let svg = `<svg viewBox="0 0 ${CX * 2} ${CY * 2}">`;

      // Grid rings (0.25, 0.5, 0.75, 1.0)
      for (const frac of [0.25, 0.5, 0.75, 1.0]) {
        const pts = RADAR_AXES.map(ax => {
          const x = CX + Math.cos(ax.angle) * R * frac;
          const y = CY + Math.sin(ax.angle) * R * frac;
          return `${x},${y}`;
        }).join(' ');
        svg += `<polygon class="radar-grid-line" points="${pts}"/>`;
      }

      // Axis lines
      for (const ax of RADAR_AXES) {
        const ex = CX + Math.cos(ax.angle) * R;
        const ey = CY + Math.sin(ax.angle) * R;
        svg += `<line class="radar-axis-line" x1="${CX}" y1="${CY}" x2="${ex}" y2="${ey}"/>`;
      }

      // Data polygon
      const dataPts = RADAR_AXES.map((ax, i) => {
        const v = values[i];
        const x = CX + Math.cos(ax.angle) * R * v;
        const y = CY + Math.sin(ax.angle) * R * v;
        return `${x},${y}`;
      }).join(' ');

      const skuSuffixes = (window.SKU_PATTERNS || []).map(p => p.suffix.trim()).join('|');
      const baseCreator = a.creator.replace(new RegExp(` (${skuSuffixes})$`), '');
      const color = (window.CREATOR_COLORS || {})[baseCreator] || '#888';
      svg += `<polygon points="${dataPts}" fill="${color}" fill-opacity="0.25" stroke="${color}" stroke-width="1.5"/>`;

      // Data points (dots)
      for (let i = 0; i < RADAR_AXES.length; i++) {
        const v = values[i];
        const x = CX + Math.cos(RADAR_AXES[i].angle) * R * v;
        const y = CY + Math.sin(RADAR_AXES[i].angle) * R * v;
        svg += `<circle cx="${x}" cy="${y}" r="3" fill="${color}" stroke="#000" stroke-width="1"/>`;
      }

      // Axis labels
      for (let i = 0; i < RADAR_AXES.length; i++) {
        const ax = RADAR_AXES[i];
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
        <div class="radar-panel" data-creator="${a.creator}" style="${window.__legendFilter && window.__legendFilter.dim === 'creator' && window.__legendFilter.val !== a.creator ? 'opacity:0.15' : ''}">
          <div class="creator-name" style="color:${color}">${a.creator}</div>
          ${svg}
          <div class="radar-stats">
            IQ <span class="val">${a.avgIQ.toFixed(1)}</span> ·
            $/task <span class="val">$${a.avgCost.toFixed(3)}</span> ·
            <span class="val">${a.avgSpeed.toFixed(0)}</span> t/s ·
            cache <span class="val">${(a.avgCacheEff * 100).toFixed(0)}%</span> ·
            <span class="val">${a.count}</span> model${a.count > 1 ? 's' : ''}
          </div>
        </div>`;
    }

    html += '</div>';

    container.innerHTML = html;

    // Clear legend (redundant with chart header)
    const legendEl = container.parentElement.querySelector('.viz-legend');
    if (legendEl) legendEl.innerHTML = '';
  }

  window.VIZ_REGISTRY = window.VIZ_REGISTRY || [];
  window.VIZ_REGISTRY.push({
    id: '03',
    name: 'Provider Archetypes',
    subtitle: `Radar grid: ${(window.RADAR_AXES || []).map(a => a.label).join(' × ')}`,
    render
  });
})();
