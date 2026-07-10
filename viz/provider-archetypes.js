// Small-multiples radar chart: 5 metrics per creator (IQ, speed, token eff, cache eff, cost eff)

(function() {
  const CREATOR_COLORS = window.CREATOR_COLORS || {};

  function render(container, data) {
    const models = data.filter(m =>
      m.intel != null && m.cost_per_task != null && m.cost_per_task > 0
      && m.speed_tps != null
    );

    if (models.length === 0) {
      window.VIZ_HELPERS.renderEmptyState(container,
        `No models with archetype data. This view needs <code>intel</code> + <code>cost_per_task</code> + <code>speed_tps</code>.`);
      return;
    }

    // Group by creator, split into SKU variants
    const SKU_PATTERNS = window.SKU_PATTERNS || [];
    const byCreator = {};
    for (const m of models) {
      const slug = m.slug.toLowerCase();
      let suffix = '';
      for (const p of SKU_PATTERNS) {
        if (new RegExp(p.pattern).test(slug)) { suffix = p.suffix; break; }
      }
      const key = m.creator + suffix;
      if (!byCreator[key]) byCreator[key] = [];
      byCreator[key].push(m);
    }

    // Build creator archetypes: average normalized scores per creator
    const archetypes = [];
    for (const [creator, ms] of Object.entries(byCreator)) {
      const avgIQ = ms.reduce((s, m) => s + (m.radar_intel ?? 0), 0) / ms.length;
      const avgSpeed = ms.reduce((s, m) => s + (m.radar_speed ?? 0), 0) / ms.length;
      const avgCacheEff = ms.reduce((s, m) => s + (m.radar_cache_eff ?? 0), 0) / ms.length;
      const avgCostEff = ms.reduce((s, m) => s + (m.radar_cost_eff ?? 0), 0) / ms.length;
      const ctxVals = ms.map(m => m.radar_ctx).filter(v => v != null);
      const avgCtx = ctxVals.length ? ctxVals.reduce((s, v) => s + v, 0) / ctxVals.length : null;

      // Raw averages for stats display
      const rawCost = ms.reduce((s, m) => s + m.cost_per_task, 0) / ms.length;
      const rawIQ = ms.reduce((s, m) => s + m.intel, 0) / ms.length;
      const rawSpeed = ms.reduce((s, m) => s + m.speed_tps, 0) / ms.length;
      const rawCtxVals = ms.map(m => m.context_window).filter(v => v != null);
      const rawCtx = rawCtxVals.length ? Math.round(rawCtxVals.reduce((s, v) => s + v, 0) / rawCtxVals.length) : null;
      const rawCacheHit = ms.filter(m => m.cache_hit_price != null && m.inp_price != null && m.inp_price > 0);
      const rawCacheEff = rawCacheHit.length
        ? rawCacheHit.reduce((s, m) => s + (1 - m.cache_hit_price / m.inp_price), 0) / rawCacheHit.length : 0;

      archetypes.push({ creator, avgIQ, avgSpeed, avgCacheEff, avgCostEff, avgCtx,
                        rawIQ, rawCost, rawSpeed, rawCtx, rawCacheEff, count: ms.length });
    }

    // Sort alphabetically — keeps OSS variants next to parent
    archetypes.sort((a, b) => a.creator.localeCompare(b.creator));

    // Collect raw apex values for axis labels
    const allIQ = archetypes.map(a => a.rawIQ);
    const allSpeed = archetypes.map(a => a.rawSpeed);
    const allCacheEff = archetypes.map(a => a.rawCacheEff);
    const allCostEff = archetypes.map(a => a.avgCostEff);
    const allCtx = archetypes.map(a => a.rawCtx).filter(v => v != null);
    const iqHi = Math.max(...allIQ);
    const spHi = Math.max(...allSpeed);
    const caHi = Math.max(...allCacheEff);
    const ceScoreHi = Math.max(...allCostEff);  // best normalized cost-eff (1.0) → apex shows score
    const ctxHi = Math.max(...allCtx) || 0;

    const RADAR_AXES = window.RADAR_AXES || [];

    const R = 80;       // radar radius
    const CX = 130;     // center x within each panel
    const CY = 130;     // center y within each panel
    const COLS = 4;

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
        a.avgIQ,
        a.avgSpeed,
        a.avgCacheEff,
        a.avgCostEff,
        a.avgCtx ?? 0,
      ];

      let svg = `<svg viewBox="0 0 ${CX * 2} ${CY * 2}">`;

      // Grid rings
      for (const frac of [0.25, 0.5, 0.75, 1.0]) {
        const pts = RADAR_AXES.map(ax => {
          const x = CX + Math.cos(ax.angle) * R * frac;
          const y = CY + Math.sin(ax.angle) * R * frac;
          return `${x},${y}`;
        }).join(' ');
        svg += `<polygon class="radar-grid-line" points="${pts}"/>`;
      }

      for (const ax of RADAR_AXES) {
        const ex = CX + Math.cos(ax.angle) * R;
        const ey = CY + Math.sin(ax.angle) * R;
        svg += `<line class="radar-axis-line" x1="${CX}" y1="${CY}" x2="${ex}" y2="${ey}"/>`;
      }

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

      for (let i = 0; i < RADAR_AXES.length; i++) {
        const v = values[i];
        const x = CX + Math.cos(RADAR_AXES[i].angle) * R * v;
        const y = CY + Math.sin(RADAR_AXES[i].angle) * R * v;
        svg += `<circle cx="${x}" cy="${y}" r="3" fill="${color}" stroke="#000" stroke-width="1"/>`;
      }

      // Axis labels — show the apex value at each axis (edge = peak is
      // implicit). Cost axis shows the normalized efficiency SCORE (0-100,
      // bigger = cheaper = better), matching the "higher = better" direction of
      // the other axes. The real $/task lives in the panel stats below.
      const apexVals = [iqHi, spHi, caHi, ceScoreHi, ctxHi];
      const fmtApex = (key, val) => {
        const N = window.VIZ_NUM;
        if (val == null) return N.DASH;
        if (key === 'avgIQ') return N.fmtCompact(val, { decimals: 0 });
        if (key === 'avgSpeed') return N.fmtCompact(val, { decimals: 0 }) + '/s';
        if (key === 'avgCacheEff') return N.fmtPct(val);
        if (key === 'costEff') return (val * 100).toFixed(0);  // normalized score 0-100
        if (key === 'avgCtx') return N.fmtCount(val);
        return N.fmtCompact(val);
      };
      for (let i = 0; i < RADAR_AXES.length; i++) {
        const ax = RADAR_AXES[i];
        const lx = CX + Math.cos(ax.angle) * (R + 10);
        const ly = CY + Math.sin(ax.angle) * (R + 10);
        let anchor = 'middle';
        if (ax.angle === 0) anchor = 'start';
        if (ax.angle === Math.PI) anchor = 'end';
        let dy = '0.35em';
        if (ax.angle === -Math.PI / 2) dy = '0';
        if (ax.angle === Math.PI / 2) dy = '1em';
        svg += `<text class="radar-axis-label" x="${lx}" y="${ly}" text-anchor="${anchor}" dy="${dy}">${ax.label} <tspan fill="#666" font-size="7">${fmtApex(ax.key, apexVals[i])}</tspan></text>`;
      }
      svg += '</svg>';

      const fmtRaw = (key, val) => {
        const N = window.VIZ_NUM;
        if (val == null) return N.DASH;
        if (key === 'avgIQ') return val.toFixed(1);
        if (key === 'avgSpeed') return N.fmtCompact(val, { decimals: 0 }) + ' t/s';
        if (key === 'avgCacheEff') return N.fmtPct(val);
        if (key === 'costEff') return N.fmtUSD(val) + '/task';
        if (key === 'avgCtx') return N.fmtCount(val);
        return N.fmtCompact(val);
      };

      let statsHtml = RADAR_AXES.map(ax => {
        const rawKey = { avgIQ: 'rawIQ', avgSpeed: 'rawSpeed', avgCacheEff: 'rawCacheEff',
                         costEff: 'rawCost', avgCtx: 'rawCtx' }[ax.key] || ax.key;
        let val = fmtRaw(ax.key, a[rawKey]);
        if (ax.key === 'costEff') val += ` <span style="color:#666">(${(a.avgCostEff * 100).toFixed(0)} eff)</span>`;
        return `${ax.label} <span class="val">${val}</span>`;
      }).join(' · ');
      statsHtml += ` · <span class="val">${a.count}</span> model${a.count > 1 ? 's' : ''}`;

      html += `
        <div class="radar-panel" data-creator="${a.creator}" style="${window.__legendFilter && window.__legendFilter.dim === 'creator' && window.__legendFilter.val !== a.creator ? (window.__filterMode === 'hide' ? 'display:none' : 'opacity:0.15') : ''}">
          <div class="creator-name" style="color:${color}">${a.creator}</div>
          ${svg}
          <div class="radar-stats">${statsHtml}</div>
        </div>`;
    }

    html += '</div>';

    container.innerHTML = html + window.VIZ_HELPERS.renderCoverageNote(container, models.length, data.length, 'cost_per_task + intel + speed');

    // Clear legend (redundant with chart header)
    const legendEl = container.parentElement.querySelector('.viz-legend');
    if (legendEl) legendEl.innerHTML = '';
  }

  window.VIZ_REGISTRY = window.VIZ_REGISTRY || [];
  window.VIZ_REGISTRY.push({
    id: 'provider-archetypes',
    name: 'Provider Archetypes',
    subtitle: `Radar grid: ${(window.RADAR_AXES || []).map(a => a.label).join(' \u00d7 ')}`,
    render
  });
})();
