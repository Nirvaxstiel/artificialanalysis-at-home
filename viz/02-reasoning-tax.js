// viz/02-reasoning-tax.js
// Horizontal stacked bar chart: per-task cost breakdown by token type
// Shows the "reasoning tax" — how much of each task dollar goes to thinking vs useful output.
// Supports toggling between AA-derived cache data and external (OpenRouter/Dirac.run) cache hit rates.

(function() {
  const CREATOR_COLORS = window.CREATOR_COLORS || {};

  // Cost segment data (from aa_cost_breakdown.json)
  // Added slug for cache-rate cross-reference
  const COST_DATA = [
    { slug: "gpt-oss-20b",        name: "gpt-oss-20b (high)",                    creator: "OpenAI",    total_cost_per_task_usd: 0.02, answer_usd: 0.0, reasoning_usd: 0.0, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.02 },
    { slug: "deepseek-v4-flash",   name: "DeepSeek V4 Flash (max)",               creator: "DeepSeek",  total_cost_per_task_usd: 0.02, answer_usd: 0.0, reasoning_usd: 0.02, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.0 },
    { slug: "mimo-v2-5-pro",       name: "MiMo-V2.5-Pro (max)",                   creator: "Xiaomi",    total_cost_per_task_usd: 0.03, answer_usd: 0.0, reasoning_usd: 0.0, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.03 },
    { slug: "deepseek-v4-pro",     name: "DeepSeek V4 Pro (max)",                  creator: "DeepSeek",  total_cost_per_task_usd: 0.04, answer_usd: 0.0, reasoning_usd: 0.04, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.0 },
    { slug: "gpt-oss-120b",       name: "gpt-oss-120b (high)",                   creator: "OpenAI",    total_cost_per_task_usd: 0.06, answer_usd: 0.0, reasoning_usd: 0.0, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.06 },
    { slug: "minimax-m2-7",        name: "MiniMax-M2.7",                          creator: "MiniMax",   total_cost_per_task_usd: 0.07, answer_usd: 0.05, reasoning_usd: 0.0, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.02 },
    { slug: "minimax-m3",          name: "MiniMax-M3",                            creator: "MiniMax",   total_cost_per_task_usd: 0.12, answer_usd: 0.07, reasoning_usd: 0.04, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.01 },
    { slug: "grok-4-3",            name: "Grok 4.3 (high)",                       creator: "xAI",       total_cost_per_task_usd: 0.16, answer_usd: 0.13, reasoning_usd: 0.0, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.03 },
    { slug: "nova-2-0-pro-preview", name: "Nova 2.0 Pro Preview (medium)",         creator: "Amazon",    total_cost_per_task_usd: 0.17, answer_usd: 0.05, reasoning_usd: 0.10, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.02 },
    { slug: "kimi-k2-7-code",     name: "Kimi K2.7 Code",                        creator: "Kimi",      total_cost_per_task_usd: 0.18, answer_usd: 0.15, reasoning_usd: 0.0, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.03 },
    { slug: "gpt-5-5-low",        name: "GPT-5.5 (low)",                         creator: "OpenAI",    total_cost_per_task_usd: 0.22, answer_usd: 0.10, reasoning_usd: 0.08, cache_write_usd: 0.0, cache_hit_usd: 0.02, input_usd: 0.02 },
    { slug: "claude-4-5-haiku",   name: "Claude 4.5 Haiku",                      creator: "Anthropic", total_cost_per_task_usd: 0.24, answer_usd: 0.05, reasoning_usd: 0.15, cache_write_usd: 0.02, cache_hit_usd: 0.0, input_usd: 0.02 },
    { slug: "nemotron-3-ultra",   name: "Nemotron 3 Ultra",                      creator: "NVIDIA",    total_cost_per_task_usd: 0.24, answer_usd: 0.0, reasoning_usd: 0.0, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.24 },
    { slug: "nvidia-nemotron-3-super", name: "NVIDIA Nemotron 3 Super",           creator: "NVIDIA",    total_cost_per_task_usd: 0.25, answer_usd: 0.0, reasoning_usd: 0.0, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.25 },
    { slug: "gemini-3-1-pro-preview", name: "Gemini 3.1 Pro Preview",             creator: "Google",    total_cost_per_task_usd: 0.29, answer_usd: 0.18, reasoning_usd: 0.05, cache_write_usd: 0.04, cache_hit_usd: 0.0, input_usd: 0.02 },
    { slug: "kimi-k2-6",           name: "Kimi K2.6",                             creator: "Kimi",      total_cost_per_task_usd: 0.31, answer_usd: 0.18, reasoning_usd: 0.08, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.05 },
    { slug: "qwen3-5-397b",       name: "Qwen3.5 397B A17B",                     creator: "Alibaba",   total_cost_per_task_usd: 0.33, answer_usd: 0.0, reasoning_usd: 0.0, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.33 },
    { slug: "claude-4-5-sonnet",  name: "Claude 4.5 Sonnet",                     creator: "Anthropic", total_cost_per_task_usd: 0.41, answer_usd: 0.15, reasoning_usd: 0.18, cache_write_usd: 0.05, cache_hit_usd: 0.0, input_usd: 0.03 },
    { slug: "gpt-5-5-medium",     name: "GPT-5.5 (medium)",                      creator: "OpenAI",    total_cost_per_task_usd: 0.42, answer_usd: 0.10, reasoning_usd: 0.22, cache_write_usd: 0.0, cache_hit_usd: 0.08, input_usd: 0.02 },
    { slug: "glm-5-2",            name: "GLM-5.2 (max)",                         creator: "Z AI",      total_cost_per_task_usd: 0.48, answer_usd: 0.0, reasoning_usd: 0.48, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.0 },
    { slug: "gemini-3-5-flash",   name: "Gemini 3.5 Flash",                      creator: "Google",    total_cost_per_task_usd: 0.59, answer_usd: 0.30, reasoning_usd: 0.20, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.09 },
    { slug: "gpt-5-5-high",       name: "GPT-5.5 (high)",                        creator: "OpenAI",    total_cost_per_task_usd: 0.69, answer_usd: 0.15, reasoning_usd: 0.40, cache_write_usd: 0.0, cache_hit_usd: 0.12, input_usd: 0.02 },
    { slug: "gpt-5-5-xhigh",     name: "GPT-5.5 (xhigh)",                       creator: "OpenAI",    total_cost_per_task_usd: 1.03, answer_usd: 0.20, reasoning_usd: 0.65, cache_write_usd: 0.0, cache_hit_usd: 0.15, input_usd: 0.03 },
    { slug: "qwen3-7-max",        name: "Qwen3.7 Max",                           creator: "Alibaba",   total_cost_per_task_usd: 1.06, answer_usd: 0.0, reasoning_usd: 1.06, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.0 },
    { slug: "claude-sonnet-4-6",  name: "Claude Sonnet 4.6 (max)",               creator: "Anthropic", total_cost_per_task_usd: 1.14, answer_usd: 0.30, reasoning_usd: 0.50, cache_write_usd: 0.20, cache_hit_usd: 0.0, input_usd: 0.14 },
    { slug: "mistral-medium-3-5", name: "Mistral Medium 3.5",                    creator: "Mistral",   total_cost_per_task_usd: 1.20, answer_usd: 0.0, reasoning_usd: 1.20, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.0 },
    { slug: "claude-opus-4-8",    name: "Claude Opus 4.8 (max)",                 creator: "Anthropic", total_cost_per_task_usd: 1.80, answer_usd: 0.50, reasoning_usd: 0.80, cache_write_usd: 0.30, cache_hit_usd: 0.0, input_usd: 0.20 },
    { slug: "claude-sonnet-5",    name: "Claude Sonnet 5 (max)",                 creator: "Anthropic", total_cost_per_task_usd: 2.29, answer_usd: 0.60, reasoning_usd: 1.00, cache_write_usd: 0.45, cache_hit_usd: 0.0, input_usd: 0.24 }
  ];

  // ===================== CACHE HIT RATES (External) =====================
  // Sources: Dirac.run (OpenRouter observed rates) + OpenRouter API pricing
  // These are observed cache hit rates for INPUT (KV-cache) tokens.
  // Rates map to model slugs. Provider-level fallbacks used where model-specific data unavailable.
  const CACHE_HIT_RATES = {
    // DeepSeek (official API, S-tier): 86-88%
    "deepseek-v4-flash":   0.861,
    "deepseek-v4-pro":     0.879,
    // Anthropic (official API, high): 78-90%
    "claude-sonnet-4-6":   0.899,
    "claude-4-5-sonnet":   0.784,
    "claude-4-5-haiku":    0.70,
    "claude-opus-4-8":     0.79,
    "claude-sonnet-5":     0.80,
    // OpenAI: ~55% (GPT-5.1 Chat observed)
    "gpt-5-5-low":         0.553,
    "gpt-5-5-medium":      0.553,
    "gpt-5-5-high":        0.553,
    "gpt-5-5-xhigh":       0.553,
    "gpt-oss-20b":         0.30,   // varies by provider
    "gpt-oss-120b":        0.30,
    // xAI Grok: ~48%
    "grok-4-3":            0.478,
    // Google (Vertex/AI Studio): 5-37%, typically low
    "gemini-3-1-pro-preview": 0.30,
    "gemini-3-5-flash":    0.30,
    // Chinese labs (high cache rates)
    "minimax-m2-7":        0.656,
    "minimax-m3":          0.75,
    "mimo-v2-5-pro":       0.747,
    "kimi-k2-6":           0.848,
    "kimi-k2-7-code":      0.848,
    "glm-5-2":             0.661,
    "qwen3-5-397b":        0.20,
    "qwen3-7-max":         0.20,
    // Others
    "nova-2-0-pro-preview": 0.20,
    "nemotron-3-ultra":    0.10,
    "nvidia-nemotron-3-super": 0.10,
    "mistral-medium-3-5":  0.40
  };

  // Default cache price ratio: cached input ~10% of regular input price (OpenRouter typical)
  const CACHE_PRICE_RATIO = 0.1;

  // Segment definitions — order: left to right
  // External mode merges cache_write into cache_hit and re-labels to clarify INPUT caching
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

  // Apply external cache hit rates to a copy of COST_DATA
  function applyExternalCache(models) {
    return models.map(m => {
      const out = { ...m };
      const rate = CACHE_HIT_RATES[m.slug];
      if (rate == null) return out; // no external data, keep AA values

      // Total input spend across all input categories
      const totalInput = (m.input_usd || 0) + (m.cache_hit_usd || 0) + (m.cache_write_usd || 0);
      if (totalInput <= 0) return out;

      // Redistribute input cost preserving the original total:
      // totalInput = uncachedCost + cachedCost
      //            = (1-rate)*T_full + rate*T_full*discount
      //            = T_full * (1 - rate*(1 - discount))
      // ∴ T_full = totalInput / (1 - rate*(1 - discount))
      const denom = 1 - rate * (1 - CACHE_PRICE_RATIO);
      const totalInputAtFullPrice = totalInput / denom;

      let uncachedCost = Math.round((1 - rate) * totalInputAtFullPrice * 1e6) / 1e6;
      let cachedCost = Math.round(rate * totalInputAtFullPrice * CACHE_PRICE_RATIO * 1e6) / 1e6;

      // Absorb rounding drift into the larger segment so total stays exact
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

  // Format small dollar values with adequate precision
  function fmtTooltipVal(v) {
    if (v == null || v === 0) return '$0.00';
    if (v >= 0.01) return '$' + v.toFixed(2);
    if (v >= 1e-06) return '$' + v.toFixed(6);
    return '$' + v.toExponential(2);
  }

  function render(container, allData) {
    // Read current cache source preference from container state
    const cacheSource = container.__cacheSource || 'aa';

    // Build model list with appropriate cache data
    let models;
    const segments = cacheSource === 'external' ? SEGMENTS_EXT : SEGMENTS_AA;
    if (cacheSource === 'external') {
      models = applyExternalCache([...COST_DATA]);
    } else {
      models = [...COST_DATA];
    }

    // Sort cheapest first (top of chart)
    models.sort((a, b) => a.total_cost_per_task_usd - b.total_cost_per_task_usd);

    const barH = 22;
    const barGap = 4;
    const nameColW = 220;
    const rightPad = 60;
    const M = { top: 40, right: rightPad, bottom: 40, left: nameColW };
    const W = 1100;
    const innerW = W - M.left - M.right;
    const H = M.top + models.length * (barH + barGap) + M.bottom;

    // Log-scale x axis (range ~0.01 to ~3)
    const xMin = 0.01, xMax = 3;
    const logMin = Math.log10(xMin), logMax = Math.log10(xMax);
    const xScale = v => {
      if (v <= 0) return M.left;
      const px = M.left + (Math.log10(v) - logMin) / (logMax - logMin) * innerW;
      return Math.max(M.left, px);
    };

    let html = '';

    // ============ CONTROLS ============
    html += `<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;flex-wrap:wrap;">`;
    html += `<span style="color:var(--muted,#888);font-size:10px;text-transform:uppercase;letter-spacing:0.08em;font-weight:700;">Cache source:</span>`;
    html += `<button class="cache-toggle-btn ${cacheSource==='aa'?'active':''}" data-source="aa">AA Index</button>`;
    html += `<button class="cache-toggle-btn ${cacheSource==='external'?'active':''}" data-source="external">OpenRouter/Dirac.run</button>`;
    if (cacheSource === 'external') {
      html += `<span style="color:var(--neon2,#00e5ff);font-size:9px;font-weight:400;">// using observed cache hit rates</span>`;
    }
    html += `<span style="color:#666;font-size:8px;margin-left:auto;text-transform:none;letter-spacing:0;">CACHE = KV-cache for INPUT tokens only</span>`;
    html += `</div>`;

    // ============ SVG ============
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

      // Model name on the left
      svg += `<text x="${M.left - 10}" y="${y + barH / 2 + 4}" text-anchor="end" fill="#f5f5f0" font-size="11" font-family="monospace" font-weight="700" paint-order="stroke" stroke="#0a0a0a" stroke-width="3">${m.name}</text>`;

      // Draw stacked segments (left to right)
      let cumX = 0;
      for (const seg of segments) {
        const val = m[seg.key] || 0;
        if (val <= 0) continue;
        const x1 = xScale(cumX);
        const x2 = xScale(cumX + val);
        const segW = x2 - x1;
        cumX += val;

        // Skip if too narrow to see
        if (segW < 0.5) continue;

        svg += `<rect x="${x1}" y="${y}" width="${segW}" height="${barH}" fill="${seg.color}" stroke="#0a0a0a" stroke-width="1"/>`;

        // Inside label: $ amount + % if space allows
        if (segW > 30) {
          const pct = ((val / total) * 100).toFixed(0);
          const valLabel = val >= 0.01 ? `$${val.toFixed(2)}` : `$${val.toFixed(3)}`;
          const text = segW > 55 ? `${valLabel} ${pct}%` : valLabel;
          const textColor = seg.key === 'answer_usd' ? '#0a0a0a' : '#f5f5f0';
          svg += `<text x="${x1 + segW / 2}" y="${y + barH / 2 + 4}" text-anchor="middle" fill="${textColor}" font-size="9" font-family="monospace" font-weight="700">${text}</text>`;
        }
      }

      // Total cost on the right
      const totalX = xScale(total);
      const totalLabel = total >= 0.01 ? `$${total.toFixed(2)}` : `$${total.toFixed(3)}`;
      svg += `<text x="${totalX + 6}" y="${y + barH / 2 + 4}" text-anchor="start" fill="#f5f5f0" font-size="10" font-family="monospace" font-weight="700">${totalLabel}</text>`;

      // External mode: show cache hit rate annotation
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
          // Show cache hit rate in tooltip when external
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
      leg += `<span class="size">// EXTERNAL CACHE RATES (OpenRouter/Dirac.run) · HOVER FOR DETAILS</span>`;
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
