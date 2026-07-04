// viz/02-reasoning-tax.js
// Horizontal stacked bar chart: per-task cost breakdown by token type
// Shows the "reasoning tax" — how much of each task dollar goes to thinking vs useful output.
// Supports toggling between AA-derived cache data and external (OpenRouter/Dirac.run) cache hit rates.
// Now reads cost segments from processed.json instead of hardcoded data.

(function() {
  const CREATOR_COLORS = window.CREATOR_COLORS || {};

  // ===================== CACHE HIT RATES (External) =====================
  // Sources: Dirac.run (OpenRouter observed rates) + OpenRouter API pricing
  // These are observed cache hit rates for INPUT (KV-cache) tokens.
  const CACHE_HIT_RATES = {
    "deepseek-v4-flash":   0.861,
    "deepseek-v4-pro":     0.879,
    "claude-sonnet-4.6-adaptive":   0.899,
    "claude-4.5-sonnet-thinking":   0.784,
    "claude-4.5-haiku-reasoning":   0.70,
    "claude-opus-4.8":     0.79,
    "claude-sonnet-5":     0.80,
    "gpt-5.5-low":         0.553,
    "gpt-5.5-medium":      0.553,
    "gpt-5.5-high":        0.553,
    "gpt-5.5-xhigh":       0.553,
    "gpt-oss-20b":         0.30,
    "gpt-oss-120b":        0.30,
    "grok-4.3":            0.478,
    "gemini-3.1-pro-preview": 0.30,
    "gemini-3.5-flash":    0.30,
    "minimax-m2.7":        0.656,
    "minimax-m3":          0.75,
    "mimo-v2.5-pro":       0.747,
    "kimi-k2.6":           0.848,
    "kimi-k2.7-code":      0.848,
    "glm-5.2":             0.661,
    "qwen3.5-397b-a17b":   0.20,
    "qwen3.7-max":         0.20,
    "nova-2.0-pro-reasoning-medium": 0.20,
    "nemotron-3-ultra-550b-a55b": 0.10,
    "nemotron-3-super-120b-a12b": 0.10,
    "mistral-medium-3.5":  0.40
  };

  const CACHE_PRICE_RATIO = 0.1;

  const SEGMENTS_AA = [
    { key: 'input_usd',       label: 'INPUT',              color: '#4a4a4a' },
    { key: 'cache_hit_usd',   label: 'INPUT CACHE (HIT)',  color: '#1a6b5a' },
    { key: 'cache_write_usd', label: 'INPUT CACHE (MISS)', color: '#2a9d7a' },
    { key: 'answer_usd',      label: 'ANSWER',             color: '#b6ff3c' },
    { key: 'reasoning_usd',   label: 'REASONING',          color: '#ff3366' }
  ];

  const SEGMENTS_EXT = [
    { key: 'input_usd',       label: 'INPUT (UNCACHED)',    color: '#4a4a4a' },
    { key: 'cache_hit_usd',   label: 'INPUT CACHE (HIT)',   color: '#1a6b5a' },
    { key: 'cache_write_usd', label: 'INPUT CACHE (MISS)',  color: '#2a9d7a' },
    { key: 'answer_usd',      label: 'ANSWER',              color: '#b6ff3c' },
    { key: 'reasoning_usd',   label: 'REASONING',           color: '#ff3366' }
  ];

  // Build COST_DATA from processed.json — models with cost_seg_total
  function buildCostData(data) {
    return data
      .filter(m => m.cost_seg_total != null && m.cost_seg_total > 0)
      .map(m => ({
        slug: m.slug,
        name: m.name,
        creator: m.creator,
        total_cost_per_task_usd: m.cost_seg_total,
        answer_usd: m.cost_seg_answer || 0,
        reasoning_usd: m.cost_seg_reasoning || 0,
        cache_write_usd: m.cost_seg_cache_write || 0,
        cache_hit_usd: m.cost_seg_cache_hit || 0,
        input_usd: m.cost_seg_input || 0
      }));
  }

  function applyExternalCache(models) {
    return models.map(m => {
      const out = { ...m };
      const rate = CACHE_HIT_RATES[m.slug];
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
    const cacheSource = container.__cacheSource || 'aa';

    let models = buildCostData(allData);
    const segments = cacheSource === 'external' ? SEGMENTS_EXT : SEGMENTS_AA;
    if (cacheSource === 'external') {
      models = applyExternalCache(models);
    }

    // Sort cheapest first
    models.sort((a, b) => a.total_cost_per_task_usd - b.total_cost_per_task_usd);

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
      html += `<span style="color:var(--neon2,#00e5ff);font-size:9px;font-weight:400;">// using observed cache hit rates</span>`;
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
    svg += `<text x="${M.left + innerW / 2}" y="${M.top - 20}" text-anchor="middle" fill="#f5f5f0" font-size="14" font-weight="800" font-family="monospace">// REASONING TAX: WHERE YOUR DOLLAR GOES</text>`;

    // Draw bars
    for (let i = 0; i < models.length; i++) {
      const m = models[i];
      const y = M.top + i * (barH + barGap);
      const total = m.total_cost_per_task_usd;
      if (total <= 0) continue;

      svg += `<text x="${M.left - 10}" y="${y + barH / 2 + 4}" text-anchor="end" fill="#f5f5f0" font-size="11" font-family="monospace" font-weight="700" paint-order="stroke" stroke="#0a0a0a" stroke-width="3">${m.name}</text>`;

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
          const text = segW > 55 ? `${valLabel} ${pct}%` : valLabel;
          const textColor = seg.key === 'answer_usd' ? '#0a0a0a' : '#f5f5f0';
          svg += `<text x="${x1 + segW / 2}" y="${y + barH / 2 + 4}" text-anchor="middle" fill="${textColor}" font-size="9" font-family="monospace" font-weight="700">${text}</text>`;
        }
      }

      const totalX = xScale(total);
      const totalLabel = total >= 0.01 ? `$${total.toFixed(2)}` : `$${total.toFixed(3)}`;
      svg += `<text x="${totalX + 6}" y="${y + barH / 2 + 4}" text-anchor="start" fill="#f5f5f0" font-size="10" font-family="monospace" font-weight="700">${totalLabel}</text>`;

      if (cacheSource === 'external' && CACHE_HIT_RATES[m.slug] != null) {
        const pct = (CACHE_HIT_RATES[m.slug] * 100).toFixed(0);
        svg += `<text x="${totalX + 6}" y="${y + barH / 2 - 6}" text-anchor="start" fill="#00e5ff" font-size="7" font-family="monospace" font-weight="400" opacity="0.7">hit ${pct}%</text>`;
      }
    }

    html += `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;">${svg}</svg>`;

    container.innerHTML = html;

    // Wire toggle buttons
    container.querySelectorAll('.cache-toggle-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        container.__cacheSource = btn.dataset.source;
        render(container, allData);
      });
    });

    // Wire tooltips
    const tt = window.getTooltipEl ? window.getTooltipEl() : null;
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
          if (cacheSource === 'external' && CACHE_HIT_RATES[m.slug] != null) {
            const hr = (CACHE_HIT_RATES[m.slug] * 100).toFixed(1);
            tooltipHtml += `<div style="border-top:1px solid #333;margin-top:4px;padding-top:4px;">`;
            tooltipHtml += `<div style="display:flex;justify-content:space-between;"><span style="color:#00e5ff;">Token cache hit rate</span><span style="color:#00e5ff;font-weight:700;">${hr}%</span></div>`;
            tooltipHtml += `<div style="color:#666;font-size:9px;margin-top:2px;">cached tokens billed at ${(CACHE_PRICE_RATIO * 100).toFixed(0)}× discount</div>`;
            tooltipHtml += `</div>`;
          }
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

    // Legend
    let leg = '<strong style="color:var(--neon);">TOKEN TYPE</strong> ';
    for (const seg of segments) {
      leg += `<span class="item"><span class="dot" style="background:${seg.color}"></span>${seg.label}</span>`;
    }
    if (cacheSource === 'external') {
      leg += `<span class="size">// EXTERNAL CACHE RATES (OpenRouter/Dirac.run) · HOVER FOR BREAKDOWN</span>`;
    } else {
      leg += `<span class="size">// AA-DERIVED CACHE DATA · TOGGLE ABOVE FOR EXTERNAL RATES · HOVER FOR BREAKDOWN</span>`;
    }
    const legendEl = container.parentElement ? container.parentElement.querySelector('.viz-legend') : null;
    if (legendEl) legendEl.innerHTML = leg;
  }

  window.VIZ_REGISTRY = window.VIZ_REGISTRY || [];
  window.VIZ_REGISTRY.push({
    id: '02',
    name: 'The Reasoning Tax',
    subtitle: 'Per-task cost breakdown by token type',
    render
  });
})();
