// Cost per task with cache hit adjustment (AA segments / OpenRouter/Dirac.run external rates)

(function() {
  const CREATOR_COLORS = window.CREATOR_COLORS || {};

  function getCacheHitRate(slug) {
    const rates = window.CACHE_HIT_RATES || {};
    if (rates[slug] != null) return rates[slug];
    // Try dot variant
    const dotSlug = slug.replace(/-/g, '.');
    if (rates[dotSlug] != null) return rates[dotSlug];
    return null;
  }

  const CACHE_PRICE_RATIO = 0.1;

  const SEGMENTS_AA = (window.COST_SEGMENTS || {}).aa || [];
  const SEGMENTS_EXT = (window.COST_SEGMENTS || {}).ext || [];

  function buildCostData(data) {
    return data
      .filter(m => m.cost_seg_total != null && m.cost_seg_total > 0)
      .map(m => {
        const cache_hit_usd = m.cost_seg_cache_hit || 0;
        const input_usd = m.cost_seg_input || 0;
        const cache_write_usd = m.cost_seg_cache_write || 0;
        // AA does NOT provide cache hit rate — the cost_seg fields show what was charged,
        // but not what % of input was cached. Hit rate only from external sources.
        const cache_hit_rate = null;
        return {
          slug: m.slug,
          name: m.name,
          creator: m.creator,
          total_cost_per_task_usd: m.cost_seg_total,
          answer_usd: m.cost_seg_answer || 0,
          reasoning_usd: m.cost_seg_reasoning || 0,
          cache_write_usd: cache_write_usd,
          cache_hit_usd: cache_hit_usd,
          input_usd: input_usd,
          cache_hit_rate: cache_hit_rate,
        };
      });
  }

  function applyExternalCache(models) {
    return models.map(m => {
      const out = { ...m };
      const rate = getCacheHitRate(m.slug);
      if (rate == null) return out;

      const totalInput = (m.input_usd || 0) + (m.cache_hit_usd || 0) + (m.cache_write_usd || 0);
      if (totalInput <= 0) return out;

      const denom = 1 - rate * (1 - CACHE_PRICE_RATIO);
      const totalInputAtFullPrice = totalInput / denom;

      let uncachedCost = Math.round((1 - rate) * totalInputAtFullPrice * 1e6) / 1e6;
      let cachedCost = Math.round(rate * totalInputAtFullPrice * CACHE_PRICE_RATIO * 1e6) / 1e6;

      const newInputTotal = uncachedCost + cachedCost;
      if (newInputTotal !== totalInput) {
        const diff = Math.round((totalInput - newInputTotal) * 1e6) / 1e6;
        if (uncachedCost >= cachedCost) uncachedCost += diff;
        else cachedCost += diff;
      }

      out.input_usd = uncachedCost;
      out.cache_hit_usd = cachedCost;
      out.cache_write_usd = 0;

      return out;
    });
  }

  function fmtTooltipVal(v) {
    if (v == null || v === 0) return '$0.00';
    if (v >= 0.01) return '$' + v.toFixed(2);
    if (v >= 1e-06) return '$' + v.toFixed(6);
    return '$' + v.toExponential(2);
  }

  function render(container, allData) {
    const cacheSource = container.__cacheSource || window.VIZ_DEFAULTS.costBreakdown.cacheSource;

    let models = buildCostData(allData);
    const segments = cacheSource === 'external' ? SEGMENTS_EXT : SEGMENTS_AA;
    if (cacheSource === 'external') {
      models = applyExternalCache(models);
    }

    // Sort cheapest first
    models.sort((a, b) => a.total_cost_per_task_usd - b.total_cost_per_task_usd);

    // Apply legend filter at the data level — only when hiding
    if (window.__legendFilter && window.__legendFilter.dim === 'creator'
        && window.__filterMode === 'hide') {
      const before = models.length;
      models = models.filter(m => m.creator === window.__legendFilter.val);
      if (models.length === 0) {
        const sel = window.__legendFilter.val;
        const emptyCreators = [...new Set(allData.filter(m => m.cost_seg_total).map(m => m.creator))].sort();
        window.VIZ_HELPERS.renderEmptyState(container,
          `No cost breakdown data for <b>${sel}</b>. ` +
          `${before} model${before === 1 ? '' : 's'} matched the filter, but none have cost segments.<br><br>` +
          `<b>Available:</b> ${emptyCreators.join(', ') || 'none'}`);
        return;
      }
    }

    const barH = 22;
    const barGap = 4;
    const nameColW = 220;
    const rightPad = 60;
    const M = { top: 40, right: rightPad, bottom: 40, left: nameColW };
    const W = 1100;
    const innerW = W - M.left - M.right;
    const H = M.top + models.length * (barH + barGap) + M.bottom;

    const xMin = 0.01, xMax = 3;
    const logMin = Math.log10(xMin), logMax = Math.log10(xMax);
    const xScale = v => {
      if (v <= 0) return M.left;
      const px = M.left + (Math.log10(v) - logMin) / (logMax - logMin) * innerW;
      return Math.max(M.left, px);
    };

    let html = '';

    // Controls
    html += `<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;flex-wrap:wrap;">`;
    html += `<span style="color:var(--muted,#888);font-size:10px;text-transform:uppercase;letter-spacing:0.08em;font-weight:700;">Cache source:</span>`;
    html += `<button class="cache-toggle-btn ${cacheSource==='aa'?'active':''}" data-source="aa">AA Index</button>`;
    html += `<button class="cache-toggle-btn ${cacheSource==='external'?'active':''}" data-source="external">OpenRouter/Dirac.run</button>`;
    if (cacheSource === 'external') {
      const withCacheTotal = models.reduce((s, m) => s + m.total_cost_per_task_usd, 0);
      const noCacheTotal = models.reduce((s, m) => {
        if ((m.input_usd || 0) + (m.cache_hit_usd || 0) <= 0) return s + m.total_cost_per_task_usd;
        return s + (m.total_cost_per_task_usd - m.answer_usd - m.reasoning_usd);
      }, 0);
      const savings = noCacheTotal - withCacheTotal;
      const savingsPct = noCacheTotal > 0 ? (savings / noCacheTotal * 100) : 0;
      html += `<span style="color:var(--neon2,#00e5ff);font-size:9px;font-weight:400;">// observed cache hit rates · ~$${savings.toFixed(2)} saved (${savingsPct.toFixed(0)}% vs no cache) · total $${withCacheTotal.toFixed(2)}</span>`;
    } else {
      const total = models.reduce((s, m) => s + m.total_cost_per_task_usd, 0);
      html += `<span style="color:var(--muted,#888);font-size:9px;font-weight:400;">// AA segments only · total $${total.toFixed(2)} · hit rate N/A (not in AA data)</span>`;
    }
    html += `<span style="color:#666;font-size:8px;margin-left:auto;text-transform:none;letter-spacing:0;">CACHE = KV-cache for INPUT tokens only</span>`;
    html += `</div>`;

    // SVG
    let svg = '';

    // Grid lines
    const ticks = [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 3];
    svg += '<g class="grid-lines">';
    for (const t of ticks) {
      const x = xScale(t);
      svg += `<line x1="${x}" y1="${M.top - 5}" x2="${x}" y2="${H - M.bottom}" stroke="#333" stroke-width="1"/>`;
    }
    svg += '</g>';

    // X-axis labels
    svg += '<g class="axis">';
    for (const t of ticks) {
      const x = xScale(t);
      svg += `<text x="${x}" y="${H - M.bottom + 18}" text-anchor="middle" fill="#888" font-size="10" font-family="monospace">$${t}</text>`;
      svg += `<line x1="${x}" y1="${H - M.bottom}" x2="${x}" y2="${H - M.bottom + 4}" stroke="#888" stroke-width="1"/>`;
    }
    svg += `<text x="${M.left + innerW / 2}" y="${H - 6}" text-anchor="middle" fill="#f5f5f0" font-size="12" font-weight="800" font-family="monospace">COST PER TASK (USD, log)</text>`;
    svg += '</g>';

    // Title
    svg += `<text x="${M.left + innerW / 2}" y="${M.top - 20}" text-anchor="middle" fill="#f5f5f0" font-size="14" font-weight="800" font-family="monospace">// COST BREAKDOWN: WHERE YOUR DOLLAR GOES</text>`;

    // Draw bars
    for (let i = 0; i < models.length; i++) {
      const m = models[i];
      const y = M.top + i * (barH + barGap);
      const total = m.total_cost_per_task_usd;
      if (total <= 0) continue;

      svg += `<g data-slug="${m.slug}">`;

      svg += `<text x="${M.left - 10}" y="${y + barH / 2 + 4}" text-anchor="end" fill="#f5f5f0" font-size="11" font-family="monospace" font-weight="700" paint-order="stroke" stroke="#0a0a0a" stroke-width="3">${m.name.length > 28 ? m.name.slice(0, 26) + '…' : m.name}</text>`;

      let cumX = 0;
      for (const seg of segments) {
        const val = m[seg.key] || 0;
        if (val <= 0) continue;
        const x1 = xScale(cumX);
        const x2 = xScale(cumX + val);
        const segW = x2 - x1;
        cumX += val;

        if (segW < 0.5) continue;

        svg += `<rect x="${x1}" y="${y}" width="${segW}" height="${barH}" fill="${seg.color}" stroke="#0a0a0a" stroke-width="1"/>`;

        if (segW > 30) {
          const pct = ((val / total) * 100).toFixed(0);
          const valLabel = val >= 0.01 ? `$${val.toFixed(2)}` : `$${val.toFixed(3)}`;
          const showPct = segments.filter(s => (m[s.key] || 0) > 0).length > 1;
          const text = showPct && segW > 55 ? `${valLabel} ${pct}%` : valLabel;
          const textColor = seg.key === 'answer_usd' ? '#0a0a0a' : '#f5f5f0';
          svg += `<text x="${x1 + segW / 2}" y="${y + barH / 2 + 4}" text-anchor="middle" fill="${textColor}" font-size="9" font-family="monospace" font-weight="700">${text}</text>`;
        }
      }

      const totalX = xScale(total);
      const totalLabel = total >= 0.01 ? `$${total.toFixed(2)}` : `$${total.toFixed(3)}`;
      svg += `<text x="${totalX + 6}" y="${y + barH / 2 + 4}" text-anchor="start" fill="#f5f5f0" font-size="10" font-family="monospace" font-weight="700">${totalLabel}</text>`;

      // Cache hit rate
      let hitRate = null;
      if (cacheSource === 'external' && getCacheHitRate(m.slug) != null) {
        hitRate = getCacheHitRate(m.slug);
      } else if (m.cache_hit_rate != null) {
        hitRate = m.cache_hit_rate;
      }
      const hitLabel = hitRate != null ? `hit ${(hitRate * 100).toFixed(0)}%` : 'hit: N/A';
      const hitColor = hitRate != null ? '#00e5ff' : '#666';
      svg += `<text x="${totalX + 6}" y="${y + barH / 2 - 6}" text-anchor="start" fill="${hitColor}" font-size="7" font-family="monospace" font-weight="400" opacity="0.7">${hitLabel}</text>`;
      svg += `</g>`;
    }

    html += `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;">${svg}</svg>`;
    html += window.VIZ_HELPERS.renderCoverageNote(container, models.length, allData.length, 'cost_seg_total');

    container.innerHTML = html;

    // Apply legend filter opacity
    window.VIZ_HELPERS.applyLegendFilter(container, models);

    // Wire toggle buttons
    container.querySelectorAll('.cache-toggle-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        container.__cacheSource = btn.dataset.source;
        render(container, allData);
      });
    });

    // Wire tooltips
    const tt = document.getElementById('tooltip');
    if (tt) {
      const svgEl = container.querySelector('svg');
      if (svgEl) {
        svgEl.addEventListener('mousemove', e => {
          const rect = svgEl.getBoundingClientRect();
          const svgY = (e.clientY - rect.top) / rect.height * H;
          const idx = Math.floor((svgY - M.top) / (barH + barGap));
          if (idx < 0 || idx >= models.length) { tt.style.display = 'none'; return; }
          const m = models[idx];

          let tooltipHtml = `<div style="font-family:monospace;font-size:11px;color:#f5f5f0;">`;
          tooltipHtml += `<div style="font-weight:800;font-size:13px;margin-bottom:4px;">${m.name}</div>`;
          tooltipHtml += `<div style="color:#888;margin-bottom:6px;">${m.creator}</div>`;
          for (const seg of segments) {
            const val = m[seg.key] || 0;
            if (val <= 0) continue;
            const pct = ((val / (m.total_cost_per_task_usd || 1)) * 100).toFixed(1);
            tooltipHtml += `<div style="display:flex;justify-content:space-between;gap:12px;">`;
            tooltipHtml += `<span><span style="display:inline-block;width:8px;height:8px;background:${seg.color};margin-right:4px;"></span>${seg.label}</span>`;
            tooltipHtml += `<span style="color:${seg.color};font-weight:700;">${fmtTooltipVal(val)} <span style="color:#888;">(${pct}%)</span></span>`;
            tooltipHtml += `</div>`;
          }
          // Cache hit rate
          let hitRate = null;
          if (cacheSource === 'external' && getCacheHitRate(m.slug) != null) {
            hitRate = getCacheHitRate(m.slug);
          } else if (m.cache_hit_rate != null) {
            hitRate = m.cache_hit_rate;
          }
          tooltipHtml += `<div style="border-top:1px solid #333;margin-top:4px;padding-top:4px;">`;
          if (hitRate != null) {
            const hr = (hitRate * 100).toFixed(1);
            tooltipHtml += `<div style="display:flex;justify-content:space-between;"><span style="color:#00e5ff;">Cache hit rate</span><span style="color:#00e5ff;font-weight:700;">${hr}%</span></div>`;
            if (cacheSource === 'external') {
              tooltipHtml += `<div style="color:#666;font-size:9px;margin-top:2px;">cached tokens billed at ${(CACHE_PRICE_RATIO * 100).toFixed(0)}× discount</div>`;
            } else {
              tooltipHtml += `<div style="color:#666;font-size:9px;margin-top:2px;">derived from cost segments</div>`;
            }
          } else {
            tooltipHtml += `<div style="display:flex;justify-content:space-between;"><span style="color:#888;">Cache hit rate</span><span style="color:#888;">N/A</span></div>`;
            tooltipHtml += `<div style="color:#666;font-size:9px;margin-top:2px;">not derivable from cost segments</div>`;
          }
          tooltipHtml += `</div>`;
          tooltipHtml += `<div style="border-top:1px solid #333;margin-top:4px;padding-top:4px;font-weight:800;">TOTAL: $${m.total_cost_per_task_usd.toFixed(2)}</div>`;
          const reasoningPct = ((m.reasoning_usd / m.total_cost_per_task_usd) * 100).toFixed(0);
          if (m.reasoning_usd > 0) {
            tooltipHtml += `<div style="color:#ff3366;margin-top:2px;">Reasoning tax: ${reasoningPct}%</div>`;
          }
          tooltipHtml += `</div>`;

          tt.innerHTML = tooltipHtml;
          tt.style.display = 'block';
          const x = e.clientX + 16, y = e.clientY + 16;
          const tw = tt.offsetWidth, th = tt.offsetHeight;
          tt.style.left = (x + tw > window.innerWidth ? e.clientX - tw - 16 : x) + 'px';
          tt.style.top = (y + th > window.innerHeight ? e.clientY - th - 16 : y) + 'px';
        });
        svgEl.addEventListener('mouseleave', () => { tt.style.display = 'none'; });
      }
    }
  }

  window.VIZ_REGISTRY = window.VIZ_REGISTRY || [];
  window.VIZ_REGISTRY.push({
    id: 'cost-breakdown',
    name: 'Cost Breakdown',
    subtitle: 'Per-task cost split by token type (input / cached / answer / reasoning)',
    render
  });

  window.COST_BREAKDOWN = { buildCostData, applyExternalCache, getCacheHitRate };
})();
