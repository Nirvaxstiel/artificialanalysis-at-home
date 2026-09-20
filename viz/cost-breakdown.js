(function() {
  const AA_SEGMENTS = (window.COST_SEGMENTS || {}).aa || [];
  const RATE_SEGMENTS = [
    { key: 'eff_input_usd',  label: 'INPUT (eff $/M)',  color: '#4a4a4a' },
    { key: 'eff_output_usd', label: 'OUTPUT (eff $/M)', color: '#b6ff3c' },
  ];

  const AA_TICKS = [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 3];
  const TICK_LADDER = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000];

  const GEO = { barH: 22, barGap: 4, nameColW: 220, rightPad: 70, W: 1100, top: 40, bottom: 40 };

  function fmtMoney(v) {
    if (v == null || v === 0) return '$0.00';
    if (v >= 0.01) return '$' + v.toFixed(2);
    if (v >= 1e-06) return '$' + v.toFixed(6);
    return '$' + v.toExponential(2);
  }

  function providerEntries(m) {
    return m.dirac_cache_hit_rates || [];
  }

  function providerEntry(m, provider) {
    return providerEntries(m).find(r => r.provider === provider) || null;
  }

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
        input_usd: m.cost_seg_input || 0,
      }));
  }

  function providerOptions(data) {
    const counts = {};
    for (const m of data) {
      for (const e of providerEntries(m)) {
        if (e.eff_input_price == null || e.eff_output_price == null) continue;
        counts[e.provider] = (counts[e.provider] || 0) + 1;
      }
    }
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .map(([name, count]) => ({ name, count }));
  }

  function providerTaskRow(base, model, entry) {
    if (!(model.inp_price > 0) || !(model.out_price > 0)) return null;
    if (entry.eff_input_price == null || entry.eff_output_price == null) return null;
    const rIn = entry.eff_input_price / model.inp_price;
    const rOut = entry.eff_output_price / model.out_price;
    const input_usd = base.input_usd * rIn;
    const cache_hit_usd = base.cache_hit_usd * rIn;
    const cache_write_usd = base.cache_write_usd * rIn;
    const answer_usd = base.answer_usd * rOut;
    const reasoning_usd = base.reasoning_usd * rOut;
    return {
      slug: base.slug, name: base.name, creator: base.creator,
      hit_rate: entry.cache_hit_rate,
      rIn, rOut, eff_in: entry.eff_input_price, eff_out: entry.eff_output_price,
      list_in: model.inp_price, list_out: model.out_price,
      input_usd, cache_hit_usd, cache_write_usd, answer_usd, reasoning_usd,
      total_cost_per_task_usd: input_usd + cache_hit_usd + cache_write_usd + answer_usd + reasoning_usd,
    };
  }

  function providerRateRow(model, entry) {
    if (entry.eff_input_price == null || entry.eff_output_price == null) return null;
    return {
      slug: model.slug, name: model.name, creator: model.creator,
      hit_rate: entry.cache_hit_rate,
      eff_input_usd: entry.eff_input_price,
      eff_output_usd: entry.eff_output_price,
      list_in: model.inp_price, list_out: model.out_price,
      total_cost_per_task_usd: entry.eff_input_price + entry.eff_output_price,
    };
  }

  function providerView(data, provider) {
    const taskRows = [], rateRows = [];
    const bases = new Map(buildCostData(data).map(r => [r.slug, r]));
    for (const m of data) {
      const entry = providerEntry(m, provider);
      if (!entry) continue;
      const base = bases.get(m.slug);
      const taskRow = base ? providerTaskRow(base, m, entry) : null;
      if (taskRow) { taskRows.push(taskRow); continue; }
      const rateRow = providerRateRow(m, entry);
      if (rateRow) rateRows.push(rateRow);
    }
    taskRows.sort((a, b) => a.total_cost_per_task_usd - b.total_cost_per_task_usd);
    rateRows.sort((a, b) => a.total_cost_per_task_usd - b.total_cost_per_task_usd);
    return { taskRows, rateRows };
  }

  function axisFor(values) {
    const pos = values.filter(v => v > 0);
    if (!pos.length) return AA_TICKS;
    const lo = Math.min(...pos), hi = Math.max(...pos);
    const startIdx = TICK_LADDER.findIndex(t => t >= lo * 0.75);
    const endIdx = TICK_LADDER.findIndex(t => t >= hi);
    const ticks = TICK_LADDER.slice(Math.max(0, startIdx - 1), endIdx === -1 ? TICK_LADDER.length : endIdx + 1);
    return ticks.length >= 2 ? ticks : AA_TICKS;
  }

  function scaleFor(ticks) {
    const left = GEO.nameColW;
    const innerW = GEO.W - GEO.nameColW - GEO.rightPad;
    const logMin = Math.log10(ticks[0]);
    const logMax = Math.log10(ticks[ticks.length - 1]);
    return v => {
      if (!(v > 0)) return left;
      const px = left + (Math.log10(v) - logMin) / (logMax - logMin) * innerW;
      return Math.min(left + innerW, Math.max(left, px));
    };
  }

  function axisLabel(t) {
    if (t >= 1) return '$' + t;
    return '$' + t.toFixed(t < 0.01 ? 3 : 2);
  }

  function barsSvg(rows, segments, ticks, title, axisTitle) {
    const { barH, barGap, nameColW, W, top, bottom } = GEO;
    const xScale = scaleFor(ticks);
    const H = top + rows.length * (barH + barGap) + bottom;
    const midX = nameColW + (W - nameColW - GEO.rightPad) / 2;
    let svg = '<g class="grid-lines">';

    for (const t of ticks) {
      const x = xScale(t);
      svg += `<line x1="${x}" y1="${top - 5}" x2="${x}" y2="${H - bottom}" stroke="#333" stroke-width="1"/>`;
    }
    svg += '</g><g class="axis">';
    for (const t of ticks) {
      const x = xScale(t);
      svg += `<text x="${x}" y="${H - bottom + 18}" text-anchor="middle" fill="#888" font-size="10" font-family="monospace">${axisLabel(t)}</text>`;
      svg += `<line x1="${x}" y1="${H - bottom}" x2="${x}" y2="${H - bottom + 4}" stroke="#888" stroke-width="1"/>`;
    }
    svg += `<text x="${midX}" y="${H - 6}" text-anchor="middle" fill="#f5f5f0" font-size="12" font-weight="800" font-family="monospace">${axisTitle}</text>`;
    svg += `<text x="${midX}" y="${top - 20}" text-anchor="middle" fill="#f5f5f0" font-size="14" font-weight="800" font-family="monospace">${title}</text>`;
    svg += '</g>';

    for (let i = 0; i < rows.length; i++) {
      const m = rows[i];
      const y = top + i * (barH + barGap);
      const total = m.total_cost_per_task_usd;
      const name = m.name.length > 28 ? m.name.slice(0, 26) + '…' : m.name;
      svg += `<g data-slug="${m.slug}">`;
      svg += `<text x="${nameColW - 10}" y="${y + barH / 2 + 4}" text-anchor="end" fill="#f5f5f0" font-size="11" font-family="monospace" font-weight="700" paint-order="stroke" stroke="#0a0a0a" stroke-width="3">${name}</text>`;
      if (!(total > 0)) { svg += '</g>'; continue; }

      const positive = segments.filter(s => (m[s.key] || 0) > 0);
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
          const text = positive.length > 1 && segW > 55 ? `${fmtMoney(val)} ${pct}%` : fmtMoney(val);
          const textColor = seg.color === '#b6ff3c' ? '#0a0a0a' : '#f5f5f0';
          svg += `<text x="${x1 + segW / 2}" y="${y + barH / 2 + 4}" text-anchor="middle" fill="${textColor}" font-size="9" font-family="monospace" font-weight="700">${text}</text>`;
        }
      }

      const totalX = xScale(total);
      svg += `<text x="${totalX + 6}" y="${y + barH / 2 + 4}" text-anchor="start" fill="#f5f5f0" font-size="10" font-family="monospace" font-weight="700">${fmtMoney(total)}</text>`;
      const hit = m.hit_rate != null ? `hit ${m.hit_rate.toFixed(1)}%` : 'hit N/A';
      svg += `<text x="${totalX + 6}" y="${y + barH / 2 - 6}" text-anchor="start" fill="${m.hit_rate != null ? '#00e5ff' : '#666'}" font-size="7" font-family="monospace" opacity="0.75">${hit}</text>`;
      svg += '</g>';
    }

    return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;">${svg}</svg>`;
  }

  function row2(label, value, color) {
    return `<div style="display:flex;justify-content:space-between;gap:12px;"><span style="color:${color || '#888'};">${label}</span><span style="color:${color || '#f5f5f0'};font-weight:700;">${value}</span></div>`;
  }

  function tooltipHtml(m, segments, extraRows) {
    const total = m.total_cost_per_task_usd || 1;
    let html = `<div style="font-family:monospace;font-size:11px;color:#f5f5f0;">`;
    html += `<div style="font-weight:800;font-size:13px;margin-bottom:4px;">${m.name}</div>`;
    html += `<div style="color:#888;margin-bottom:6px;">${m.creator}</div>`;
    for (const seg of segments) {
      const val = m[seg.key] || 0;
      if (val <= 0) continue;
      const pct = ((val / total) * 100).toFixed(1);
      html += `<div style="display:flex;justify-content:space-between;gap:12px;">`;
      html += `<span><span style="display:inline-block;width:8px;height:8px;background:${seg.color};margin-right:4px;"></span>${seg.label}</span>`;
      html += `<span style="color:${seg.color === '#b6ff3c' ? '#b6ff3c' : '#f5f5f0'};font-weight:700;">${fmtMoney(val)} <span style="color:#888;">(${pct}%)</span></span>`;
      html += `</div>`;
    }
    for (const row of extraRows) html += row;
    return html + '</div>';
  }

  function wireBarTooltip(svgEl, rows, contentFor) {
    const tt = document.getElementById('tooltip');
    if (!tt || !rows.length) return;
    const svgH = Number(svgEl.getAttribute('viewBox').split(' ')[3]);
    const step = GEO.barH + GEO.barGap;
    svgEl.addEventListener('mousemove', e => {
      const rect = svgEl.getBoundingClientRect();
      const svgY = (e.clientY - rect.top) / rect.height * svgH;
      const idx = Math.floor((svgY - GEO.top) / step);
      if (idx < 0 || idx >= rows.length) { tt.style.display = 'none'; return; }
      tt.innerHTML = contentFor(rows[idx]);
      tt.style.display = 'block';
      const x = e.clientX + 16, y = e.clientY + 16;
      const tw = tt.offsetWidth, th = tt.offsetHeight;
      tt.style.left = (x + tw > window.innerWidth ? e.clientX - tw - 16 : x) + 'px';
      tt.style.top = (y + th > window.innerHeight ? e.clientY - th - 16 : y) + 'px';
    });
    svgEl.addEventListener('mouseleave', () => { tt.style.display = 'none'; });
  }

  function emptyHtml(message) {
    return window.VIZ_HELPERS.emptyStateHtml(message);
  }

  function sourceBarHtml(source, options) {
    let html = `<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px;">`;
    html += `<span style="color:var(--muted,#888);font-size:10px;text-transform:uppercase;letter-spacing:0.08em;font-weight:700;">Cache source:</span>`;
    html += `<button class="cache-toggle-btn${source === 'aa' ? ' active' : ''}" data-source="aa">AA Index</button>`;
    html += `<div style="flex:1;min-width:220px;">${window.VIZ_HELPERS.searchBox({ placeholder: 'Filter providers…' })}</div>`;
    html += `</div>`;
    html += `<div class="cb-provider-chips" style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:8px;">`;
    for (const o of options) {
      const active = o.name === source ? ' active' : '';
      html += `<button class="cache-toggle-btn${active}" data-provider="${o.name}">${o.name} <span style="color:#666;">(${o.count})</span></button>`;
    }
    html += `</div>`;
    return html;
  }

  function applyProviderFilter(container) {
    const q = (container.__providerQuery || '').toLowerCase();
    let shown = 0, total = 0;
    container.querySelectorAll('.cb-provider-chips [data-provider]').forEach(chip => {
      total++;
      const match = !q || chip.dataset.provider.toLowerCase().includes(q);
      chip.style.display = match ? '' : 'none';
      if (match) shown++;
    });
    const count = container.querySelector('.viz-search-count');
    if (count) count.textContent = `${shown} / ${total}`;
  }

  function wireSourceBar(container, allData) {
    container.querySelectorAll('[data-source], [data-provider]').forEach(btn => {
      btn.addEventListener('click', () => {
        container.__cacheSource = btn.dataset.provider || btn.dataset.source;
        render(container, allData);
      });
    });
    const input = container.querySelector('.viz-search');
    if (input) {
      input.value = container.__providerQuery || '';
      input.addEventListener('input', function() {
        container.__providerQuery = this.value;
        applyProviderFilter(container);
      });
    }
    applyProviderFilter(container);
  }

  function visibleToLegend(rows) {
    if (!window.__legendFilter || window.__legendFilter.dim !== 'creator' || window.__filterMode !== 'hide') return rows;
    return rows.filter(m => m.creator === window.__legendFilter.val);
  }

  function aaBody(container, allData) {
    const models = visibleToLegend(buildCostData(allData)).sort((a, b) => a.total_cost_per_task_usd - b.total_cost_per_task_usd);
    const total = models.reduce((s, m) => s + m.total_cost_per_task_usd, 0);
    const note = `// AA cost segments only · total ${fmtMoney(total)} · AA publishes no cache hit rate`;

    if (!models.length) {
      const sel = window.__legendFilter ? window.__legendFilter.val : '';
      const available = [...new Set(allData.filter(m => m.cost_seg_total).map(m => m.creator))].sort();
      return {
        note,
        html: emptyHtml(`No cost breakdown data for <b>${sel}</b>.<br><br><b>Available:</b> ${available.join(', ') || 'none'}`),
        charts: [],
      };
    }

    return {
      note,
      html: barsSvg(models, AA_SEGMENTS, AA_TICKS, '// COST BREAKDOWN: WHERE YOUR DOLLAR GOES', 'COST PER TASK (USD, log)') +
        window.VIZ_HELPERS.renderCoverageNote(container, models.length, allData.length, 'cost_seg_total'),
      charts: [{
        rows: models,
        contentFor: m => tooltipHtml(m, AA_SEGMENTS, [
          row2('Cache hit rate', 'N/A (AA does not publish it)'),
          `<div style="border-top:1px solid #333;margin-top:4px;padding-top:4px;font-weight:800;">TOTAL: ${fmtMoney(m.total_cost_per_task_usd)}</div>`,
          m.reasoning_usd > 0 ? `<div style="color:#ff3366;margin-top:2px;">Reasoning tax: ${((m.reasoning_usd / (m.total_cost_per_task_usd || 1)) * 100).toFixed(0)}%</div>` : '',
        ]),
      }],
    };
  }

  function providerBody(allData, provider) {
    const { taskRows, rateRows } = providerView(allData, provider);
    const scaled = visibleToLegend(taskRows);
    const rated = visibleToLegend(rateRows);
    const priced = new Set([...taskRows, ...rateRows].map(r => r.slug));
    const unpriced = allData.filter(m => providerEntries(m).length && providerEntry(m, provider) && !priced.has(m.slug)).length;

    let html = '';
    const charts = [];
    if (scaled.length) {
      html += `<div style="color:var(--neon2,#00e5ff);font-size:9px;font-family:monospace;margin-bottom:6px;">` +
        `// ${provider}: AA per-task segments × ${provider} effective rate ÷ AA list rate — same workload, provider prices, cached/uncached split kept from AA</div>`;
      html += barsSvg(scaled, AA_SEGMENTS, axisFor(scaled.map(m => m.total_cost_per_task_usd)),
        `// COST PER TASK ON ${provider.toUpperCase()}`, 'COST PER TASK (USD, log) · SCALED');
      const total = scaled.reduce((s, m) => s + m.total_cost_per_task_usd, 0);
      charts.push({
        rows: scaled,
        contentFor: m => tooltipHtml(m, AA_SEGMENTS, [
          row2('Observed cache hit', m.hit_rate != null ? m.hit_rate.toFixed(1) + '%' : 'N/A', '#00e5ff'),
          row2('Input rate', `${fmtMoney(m.eff_in)}/M vs list ${fmtMoney(m.list_in)}/M (×${m.rIn.toFixed(2)})`),
          row2('Output rate', `${fmtMoney(m.eff_out)}/M vs list ${fmtMoney(m.list_out)}/M (×${m.rOut.toFixed(2)})`),
          `<div style="border-top:1px solid #333;margin-top:4px;padding-top:4px;font-weight:800;">TOTAL: ${fmtMoney(m.total_cost_per_task_usd)}</div>`,
          `<div style="color:#444;font-size:9px;margin-top:2px;">// ${provider} · ${scaled.length} model${scaled.length === 1 ? '' : 's'} · ${fmtMoney(total)}</div>`,
        ]),
      });
    }
    if (rated.length) {
      html += `<div style="color:#888;font-size:9px;font-family:monospace;margin:14px 0 6px;">` +
        `// ${provider}: ${rated.length} model${rated.length === 1 ? '' : 's'} with no AA per-task cost — effective $/M rates, NOT $/task</div>`;
      html += barsSvg(rated, RATE_SEGMENTS, axisFor(rated.map(m => m.total_cost_per_task_usd)),
        `// ${provider.toUpperCase()} EFFECTIVE RATES`, '1M INPUT + 1M OUTPUT (USD, log)');
      const total = rated.reduce((s, m) => s + m.total_cost_per_task_usd, 0);
      charts.push({
        rows: rated,
        contentFor: m => tooltipHtml(m, RATE_SEGMENTS, [
          row2('Observed cache hit', m.hit_rate != null ? m.hit_rate.toFixed(1) + '%' : 'N/A', '#00e5ff'),
          row2('AA list input', m.list_in != null ? fmtMoney(m.list_in) + '/M' : '—'),
          row2('AA list output', m.list_out != null ? fmtMoney(m.list_out) + '/M' : '—'),
          `<div style="border-top:1px solid #333;margin-top:4px;padding-top:4px;font-weight:800;">TOTAL: ${fmtMoney(m.total_cost_per_task_usd)} / 1M in + 1M out</div>`,
          `<div style="color:#666;font-size:9px;margin-top:2px;">observed effective rate · cache effect already inside the input rate</div>`,
          `<div style="color:#444;font-size:9px;margin-top:2px;">// ${provider} · ${rated.length} model${rated.length === 1 ? '' : 's'} · ${fmtMoney(total)}</div>`,
        ]),
      });
    }
    if (unpriced) {
      html += `<div style="font-family:monospace;font-size:11px;color:#888;text-align:center;padding:8px;">` +
        `<span style="color:var(--neon2,#6a6);opacity:0.5;">//</span> ${provider} also serves ${unpriced} model${unpriced === 1 ? '' : 's'} absent from AA pricing</div>`;
    }

    const note = `// ${provider} · observed cache hit rates from dirac.run (OpenRouter effective pricing)`;
    if (!html) {
      const sel = window.__legendFilter ? window.__legendFilter.val : '';
      const available = [...new Set([...taskRows, ...rateRows].map(r => r.creator))].sort();
      const message = available.length
        ? `No <b>${sel}</b> models on <b>${provider}</b>.<br><br><b>Available:</b> ${available.join(', ')}`
        : `<b>${provider}</b> serves no model with usable pricing data in this dataset.`;
      return { note, html: emptyHtml(message), charts: [] };
    }
    return { note, html, charts };
  }

  function render(container, allData) {
    const source = container.__cacheSource || window.VIZ_DEFAULTS.costBreakdown.cacheSource;
    const body = source === 'aa' ? aaBody(container, allData) : providerBody(allData, source);
    const options = providerOptions(allData);

    container.innerHTML = sourceBarHtml(source, options) + `<div style="color:#666;font-size:9px;font-family:monospace;margin-bottom:8px;">${body.note}</div>` + body.html;

    window.VIZ_HELPERS.applyLegendFilter(container, body.charts.flatMap(c => c.rows));
    const svgs = container.querySelectorAll('svg');
    body.charts.forEach((chart, i) => wireBarTooltip(svgs[i], chart.rows, chart.contentFor));
    wireSourceBar(container, allData);
  }

  window.VIZ_REGISTRY = window.VIZ_REGISTRY || [];
  window.VIZ_REGISTRY.push({
    id: 'cost-breakdown',
    name: 'Cost Breakdown',
    subtitle: 'Per-task cost split by token type (input / cached / answer / reasoning) · per-provider repricing',
    render
  });

  window.COST_BREAKDOWN = { buildCostData, providerOptions, providerView, providerTaskRow, providerRateRow, axisFor };
})();