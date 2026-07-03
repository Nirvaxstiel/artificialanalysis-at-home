// viz/02-reasoning-tax.js
// Horizontal stacked bar chart: per-task cost breakdown by token type
// Shows the "reasoning tax" — how much of each task dollar goes to thinking vs useful output.

(function() {
  const CREATOR_COLORS = window.CREATOR_COLORS || {};

  // Cost segment data (from aa_cost_breakdown.json)
  const COST_DATA = [
    { name: "gpt-oss-20b (high)", creator: "OpenAI", total_cost_per_task_usd: 0.02, answer_usd: 0.0, reasoning_usd: 0.0, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.02 },
    { name: "DeepSeek V4 Flash (max)", creator: "DeepSeek", total_cost_per_task_usd: 0.02, answer_usd: 0.0, reasoning_usd: 0.02, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.0 },
    { name: "MiMo-V2.5-Pro (max)", creator: "Xiaomi", total_cost_per_task_usd: 0.03, answer_usd: 0.0, reasoning_usd: 0.0, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.03 },
    { name: "DeepSeek V4 Pro (max)", creator: "DeepSeek", total_cost_per_task_usd: 0.04, answer_usd: 0.0, reasoning_usd: 0.04, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.0 },
    { name: "gpt-oss-120b (high)", creator: "OpenAI", total_cost_per_task_usd: 0.06, answer_usd: 0.0, reasoning_usd: 0.0, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.06 },
    { name: "MiniMax-M2.7", creator: "MiniMax", total_cost_per_task_usd: 0.07, answer_usd: 0.05, reasoning_usd: 0.0, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.02 },
    { name: "MiniMax-M3", creator: "MiniMax", total_cost_per_task_usd: 0.12, answer_usd: 0.07, reasoning_usd: 0.04, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.01 },
    { name: "Grok 4.3 (high)", creator: "xAI", total_cost_per_task_usd: 0.16, answer_usd: 0.13, reasoning_usd: 0.0, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.03 },
    { name: "Nova 2.0 Pro Preview (medium)", creator: "Amazon", total_cost_per_task_usd: 0.17, answer_usd: 0.05, reasoning_usd: 0.10, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.02 },
    { name: "Kimi K2.7 Code", creator: "Kimi", total_cost_per_task_usd: 0.18, answer_usd: 0.15, reasoning_usd: 0.0, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.03 },
    { name: "GPT-5.5 (low)", creator: "OpenAI", total_cost_per_task_usd: 0.22, answer_usd: 0.10, reasoning_usd: 0.08, cache_write_usd: 0.0, cache_hit_usd: 0.02, input_usd: 0.02 },
    { name: "Claude 4.5 Haiku", creator: "Anthropic", total_cost_per_task_usd: 0.24, answer_usd: 0.05, reasoning_usd: 0.15, cache_write_usd: 0.02, cache_hit_usd: 0.0, input_usd: 0.02 },
    { name: "Nemotron 3 Ultra", creator: "NVIDIA", total_cost_per_task_usd: 0.24, answer_usd: 0.0, reasoning_usd: 0.0, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.24 },
    { name: "NVIDIA Nemotron 3 Super", creator: "NVIDIA", total_cost_per_task_usd: 0.25, answer_usd: 0.0, reasoning_usd: 0.0, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.25 },
    { name: "Gemini 3.1 Pro Preview", creator: "Google", total_cost_per_task_usd: 0.29, answer_usd: 0.18, reasoning_usd: 0.05, cache_write_usd: 0.04, cache_hit_usd: 0.0, input_usd: 0.02 },
    { name: "Kimi K2.6", creator: "Kimi", total_cost_per_task_usd: 0.31, answer_usd: 0.18, reasoning_usd: 0.08, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.05 },
    { name: "Qwen3.5 397B A17B", creator: "Alibaba", total_cost_per_task_usd: 0.33, answer_usd: 0.0, reasoning_usd: 0.0, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.33 },
    { name: "Claude 4.5 Sonnet", creator: "Anthropic", total_cost_per_task_usd: 0.41, answer_usd: 0.15, reasoning_usd: 0.18, cache_write_usd: 0.05, cache_hit_usd: 0.0, input_usd: 0.03 },
    { name: "GPT-5.5 (medium)", creator: "OpenAI", total_cost_per_task_usd: 0.42, answer_usd: 0.10, reasoning_usd: 0.22, cache_write_usd: 0.0, cache_hit_usd: 0.08, input_usd: 0.02 },
    { name: "GLM-5.2 (max)", creator: "Z AI", total_cost_per_task_usd: 0.48, answer_usd: 0.0, reasoning_usd: 0.48, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.0 },
    { name: "Gemini 3.5 Flash", creator: "Google", total_cost_per_task_usd: 0.59, answer_usd: 0.30, reasoning_usd: 0.20, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.09 },
    { name: "GPT-5.5 (high)", creator: "OpenAI", total_cost_per_task_usd: 0.69, answer_usd: 0.15, reasoning_usd: 0.40, cache_write_usd: 0.0, cache_hit_usd: 0.12, input_usd: 0.02 },
    { name: "GPT-5.5 (xhigh)", creator: "OpenAI", total_cost_per_task_usd: 1.03, answer_usd: 0.20, reasoning_usd: 0.65, cache_write_usd: 0.0, cache_hit_usd: 0.15, input_usd: 0.03 },
    { name: "Qwen3.7 Max", creator: "Alibaba", total_cost_per_task_usd: 1.06, answer_usd: 0.0, reasoning_usd: 1.06, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.0 },
    { name: "Claude Sonnet 4.6 (max)", creator: "Anthropic", total_cost_per_task_usd: 1.14, answer_usd: 0.30, reasoning_usd: 0.50, cache_write_usd: 0.20, cache_hit_usd: 0.0, input_usd: 0.14 },
    { name: "Mistral Medium 3.5", creator: "Mistral", total_cost_per_task_usd: 1.20, answer_usd: 0.0, reasoning_usd: 1.20, cache_write_usd: 0.0, cache_hit_usd: 0.0, input_usd: 0.0 },
    { name: "Claude Opus 4.8 (max)", creator: "Anthropic", total_cost_per_task_usd: 1.80, answer_usd: 0.50, reasoning_usd: 0.80, cache_write_usd: 0.30, cache_hit_usd: 0.0, input_usd: 0.20 },
    { name: "Claude Sonnet 5 (max)", creator: "Anthropic", total_cost_per_task_usd: 2.29, answer_usd: 0.60, reasoning_usd: 1.00, cache_write_usd: 0.45, cache_hit_usd: 0.0, input_usd: 0.24 }
  ];

  // Segment order: left to right (INPUT → CACHE HIT → CACHE WRITE → ANSWER → REASONING)
  const SEGMENTS = [
    { key: 'input_usd',       label: 'INPUT',       color: '#4a4a4a' },
    { key: 'cache_hit_usd',   label: 'CACHE HIT',   color: '#1a6b5a' },
    { key: 'cache_write_usd', label: 'CACHE WRITE', color: '#2a9d7a' },
    { key: 'answer_usd',      label: 'ANSWER',       color: '#b6ff3c' },
    { key: 'reasoning_usd',   label: 'REASONING',    color: '#ff3366' }
  ];

  function render(container, allData) {
    // Build slug→model lookup from processed.json for tooltip data
    const modelBySlug = {};
    for (const m of (allData || [])) modelBySlug[m.slug] = m;

    // Sort cheapest first (top of chart)
    const models = [...COST_DATA].sort((a, b) => a.total_cost_per_task_usd - b.total_cost_per_task_usd);

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
      return M.left + (Math.log10(v) - logMin) / (logMax - logMin) * innerW;
    };

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
      for (const seg of SEGMENTS) {
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
    }

    container.innerHTML = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;">${svg}</svg>`;

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

          let html = `<div style="font-family:monospace;font-size:11px;color:#f5f5f0;">`;
          html += `<div style="font-weight:800;font-size:13px;margin-bottom:4px;">${m.name}</div>`;
          html += `<div style="color:#888;margin-bottom:6px;">${m.creator}</div>`;
          for (const seg of SEGMENTS) {
            const val = m[seg.key] || 0;
            const pct = ((val / m.total_cost_per_task_usd) * 100).toFixed(1);
            html += `<div style="display:flex;justify-content:space-between;gap:12px;">`;
            html += `<span><span style="display:inline-block;width:8px;height:8px;background:${seg.color};margin-right:4px;"></span>${seg.label}</span>`;
            html += `<span style="color:${seg.color};font-weight:700;">$${val.toFixed(2)} <span style="color:#888;">(${pct}%)</span></span>`;
            html += `</div>`;
          }
          html += `<div style="border-top:1px solid #333;margin-top:4px;padding-top:4px;font-weight:800;">TOTAL: $${m.total_cost_per_task_usd.toFixed(2)}</div>`;
          const reasoningPct = ((m.reasoning_usd / m.total_cost_per_task_usd) * 100).toFixed(0);
          if (m.reasoning_usd > 0) {
            html += `<div style="color:#ff3366;margin-top:2px;">Reasoning tax: ${reasoningPct}%</div>`;
          }
          html += `</div>`;

          tt.innerHTML = html;
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
    for (const seg of SEGMENTS) {
      leg += `<span class="item"><span class="dot" style="background:${seg.color}"></span>${seg.label}</span>`;
    }
    leg += `<span class="size">// SORTED BY TOTAL COST (CHEAPEST TOP) · HOVER FOR BREAKDOWN</span>`;
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
