// Sortable data table — multi-column sort, search, 4 views (Provider Rollup / Model Detail / LiveBench / Cost Efficiency)

(function() {
  const CREATOR_COLORS = window.CREATOR_COLORS || {};

  const VIEWS = {
    provider: {
      label: 'Provider Rollup',
      defaultSort: [{ key: 'avgIQ', dir: 'desc' }],
      buildRows(data) {
        const rollup = {};
        for (const m of data) {
          if (!rollup[m.creator]) rollup[m.creator] = { count: 0, iq: [], cost: [], tokens: [] };
          rollup[m.creator].count++;
          if (m.intel != null) rollup[m.creator].iq.push(m.intel);
          if (m.cost_per_task != null) rollup[m.creator].cost.push(m.cost_per_task);
          if (m.tokens_m != null) rollup[m.creator].tokens.push(m.tokens_m);
        }
        const avg = arr => arr.length ? arr.reduce((a,b)=>a+b,0) / arr.length : null;
        return Object.entries(rollup).map(([creator, d]) => ({
          creator, count: d.count,
          avgIQ: avg(d.iq), avgCost: avg(d.cost), avgTokens: avg(d.tokens),
        }));
      },
      cols: [
        { key: 'creator', label: 'CREATOR', render: (r, c) =>
          `<span class="dot dot-lg" style="background:${window.creatorColor(r.creator)}"></span>${r.creator}` },
        { key: 'count', label: '# MODELS', render: r => r.count, cls: 'num' },
        { key: 'avgIQ', label: 'AVG IQ', render: r => r.avgIQ != null ? r.avgIQ.toFixed(1) : '—', cls: 'num' },
        { key: 'avgCost', label: 'AVG $ / TASK', render: r => r.avgCost != null ? window.VIZ_NUM.fmtUSD(r.avgCost) : '—', cls: 'num' },
        { key: 'avgTokens', label: 'AVG TOK (M)', render: r => r.avgTokens != null ? window.VIZ_NUM.fmtCount(r.avgTokens * 1e6, { decimals: 0 }) : '—', cls: 'num' },
        { key: 'iqPerK', label: 'IQ / $1K', render: r => {
          const v = r.avgIQ != null && r.avgCost != null ? (r.avgIQ / r.avgCost * 1000) : null;
          return v != null ? `<span style="color:var(--neon);font-weight:800;">${v.toFixed(1)}</span>` : '—';
        }, cls: 'num' },
      ],
    },
    model: {
      label: 'Model Detail',
      defaultSort: [{ key: 'intel', dir: 'desc' }],
      buildRows: data => data,
      cols: [
        { key: 'name', label: 'NAME', render: r => r.name, cls: 'name-cell' },
        { key: 'creator', label: 'CREATOR', render: r =>
          `<span class="dot dot-sm" style="background:${window.creatorColor(r.creator)}"></span>${r.creator}` },
        { key: 'intel', label: 'IQ', render: r => r.intel ?? '—', cls: 'num' },
        { key: 'context_window', label: 'CTX', render: r => r.context_window != null
          ? window.VIZ_NUM.fmtCount(r.context_window) : '—', cls: 'num' },
        { key: 'cost_per_task', label: '$ / TASK', render: r => r.cost_per_task != null ? window.VIZ_NUM.fmtUSD(r.cost_per_task) : '—', cls: 'num' },
        { key: 'tokens_m', label: 'TOK (M)', render: r => r.tokens_m != null ? window.VIZ_NUM.fmtCount(r.tokens_m * 1e6, { decimals: 0 }) : '—', cls: 'num' },
        { key: 'speed_tps', label: 'SPEED t/s', render: r => r.speed_tps != null ? window.VIZ_NUM.fmtCompact(r.speed_tps, { decimals: 0 }) : '—', cls: 'num' },
        { key: 'out_price', label: '$ / M TOK', render: r => r.out_price != null ? window.VIZ_NUM.fmtUSD(r.out_price) : '—', cls: 'num' },
        { key: 'iqPerK', label: 'IQ / $1K', render: r => {
          if (r.intel == null || r.cost_per_task == null) return '—';
          return `<span style="color:var(--neon);font-weight:800;">${(r.intel / r.cost_per_task * 1000).toFixed(1)}</span>`;
        }, cls: 'num' },
        { key: 'reasoning_tax_pct', label: 'RSN TAX %', render: r => r.reasoning_tax_pct != null ? window.VIZ_NUM.fmtPct(r.reasoning_tax_pct) : '—', cls: 'num' },
        { key: 'livebench_average', label: 'LB AVG', render: r => r.livebench_average != null ? r.livebench_average.toFixed(1) : '—', cls: 'num' },
        { key: 'arena_code_elo', label: 'CODE ELO', render: r => r.arena_code_elo ?? '—', cls: 'num' },
        { key: 'openrouter_inp_price_per_m', label: 'OR IN $/M', render: r => r.openrouter_inp_price_per_m != null ? window.VIZ_NUM.fmtUSD(r.openrouter_inp_price_per_m) : '—', cls: 'num' },
        { key: 'params_b', label: 'PARAMS B', render: r => r.params_b != null ? r.params_b.toFixed(0) : '—', cls: 'num' },
        { key: 'type', label: 'TYPE', render: r => r.type ?? '—' },
      ],
    },
    livebench: {
      label: 'LiveBench',
      defaultSort: [{ key: 'livebench_average', dir: 'desc' }],
      buildRows: data => data,
      cols: [
        { key: 'name', label: 'NAME', render: r => r.name },
        { key: 'creator', label: 'CREATOR', render: r =>
          `<span class="dot dot-sm" style="background:${window.creatorColor(r.creator)}"></span>${r.creator}` },
        { key: 'livebench_average', label: 'AVG', render: r => r.livebench_average != null ? r.livebench_average.toFixed(1) : '—', cls: 'num' },
        { key: 'livebench_coding', label: 'CODING', render: r => r.livebench_coding != null ? r.livebench_coding.toFixed(1) : '—', cls: 'num' },
        { key: 'livebench_reasoning', label: 'REASON', render: r => r.livebench_reasoning != null ? r.livebench_reasoning.toFixed(1) : '—', cls: 'num' },
        { key: 'livebench_mathematics', label: 'MATH', render: r => r.livebench_mathematics != null ? r.livebench_mathematics.toFixed(1) : '—', cls: 'num' },
        { key: 'livebench_language', label: 'LANG', render: r => r.livebench_language != null ? r.livebench_language.toFixed(1) : '—', cls: 'num' },
        { key: 'livebench_data_analysis', label: 'DATA', render: r => r.livebench_data_analysis != null ? r.livebench_data_analysis.toFixed(1) : '—', cls: 'num' },
        { key: 'livebench_agentic_coding', label: 'AGENT', render: r => r.livebench_agentic_coding != null ? r.livebench_agentic_coding.toFixed(1) : '—', cls: 'num' },
        { key: 'livebench_if', label: 'IF', render: r => r.livebench_if != null ? r.livebench_if.toFixed(1) : '—', cls: 'num' },
      ],
    },
    efficiency: {
      label: 'Cost Efficiency',
      defaultSort: [{ key: 'iqPerK', dir: 'desc' }],
      buildRows: data => data,
      cols: [
        { key: 'name', label: 'NAME', render: r => r.name, cls: 'name-cell' },
        { key: 'creator', label: 'CREATOR', render: r =>
          `<span class="dot dot-sm" style="background:${window.creatorColor(r.creator)}"></span>${r.creator}` },
        { key: 'intel', label: 'IQ', render: r => r.intel ?? '—', cls: 'num' },
        { key: 'cost_per_task', label: '$ / TASK', render: r => r.cost_per_task != null ? window.VIZ_NUM.fmtUSD(r.cost_per_task) : '—', cls: 'num' },
        { key: 'iqPerK', label: 'IQ / $1K', render: r => {
          if (r.intel == null || r.cost_per_task == null) return '—';
          return `<span style="color:var(--neon);font-weight:800;">${(r.intel / r.cost_per_task * 1000).toFixed(1)}</span>`;
        }, cls: 'num' },
        { key: 'costRatio', label: '$ / IQ PT', render: r => {
          if (r.intel == null || r.intel === 0 || r.cost_per_task == null) return '—';
          return window.VIZ_NUM.fmtUSD(r.cost_per_task / r.intel);
        }, cls: 'num' },
        { key: 'iq_per_mtokdollar', label: 'IQ / $MTOK', render: r => r.iq_per_mtokdollar != null ? r.iq_per_mtokdollar.toFixed(1) : '—', cls: 'num' },
        { key: 'useful_cost', label: 'USEFUL $', render: r => r.useful_cost != null ? window.VIZ_NUM.fmtUSD(r.useful_cost) : '—', cls: 'num' },
        { key: 'reasoning_tax_pct', label: 'RSN TAX %', render: r => r.reasoning_tax_pct != null ? window.VIZ_NUM.fmtPct(r.reasoning_tax_pct) : '—', cls: 'num' },
      ],
    },
  };

  const VIEW_KEYS = Object.keys(VIEWS);

  function applySort(rows, sortSpec) {
    if (!sortSpec || sortSpec.length === 0) return rows;
    const sorted = [...rows];
    sorted.sort((a, b) => {
      for (const { key, dir } of sortSpec) {
        let va = a[key], vb = b[key];
        if (key === 'iqPerK') {
          va = (a.intel != null && a.cost_per_task != null) ? a.intel / a.cost_per_task * 1000 : null;
          vb = (b.intel != null && b.cost_per_task != null) ? b.intel / b.cost_per_task * 1000 : null;
        }
        if (key === 'costRatio') {
          va = (a.intel != null && a.intel > 0 && a.cost_per_task != null) ? a.cost_per_task / a.intel : null;
          vb = (b.intel != null && b.intel > 0 && b.cost_per_task != null) ? b.cost_per_task / b.intel : null;
        }
        if (va == null && vb == null) continue;
        if (va == null) return dir === 'asc' ? 1 : -1;
        if (vb == null) return dir === 'asc' ? -1 : 1;
        if (va < vb) return dir === 'asc' ? -1 : 1;
        if (va > vb) return dir === 'asc' ? 1 : -1;
      }
      return 0;
    });
    return sorted;
  }

  function getSortIndicator(sortSpec, key) {
    const idx = sortSpec.findIndex(s => s.key === key);
    if (idx === -1) return '';
    const dir = sortSpec[idx].dir;
    const arrow = dir === 'asc' ? '▲' : '▼';
    return sortSpec.length > 1 ? `${arrow}${idx + 1}` : arrow;
  }

  function matchesSearch(m, search) {
    if (!search) return true;
    const q = search.toLowerCase();
    return (m.name && m.name.toLowerCase().includes(q))
        || (m.creator && m.creator.toLowerCase().includes(q))
        || (m.slug && m.slug.includes(q));
  }

  function render(container, data) {
    const viewKey = container.__view || window.VIZ_DEFAULTS.dataTable.view;
    const view = VIEWS[viewKey];
    if (!view) return;

    const sortSpec = container.__sort || (view.defaultSort && [...view.defaultSort]) || window.VIZ_DEFAULTS.dataTable.sort;
    const search = container.__search || '';

    const rows = view.buildRows(data);
    const filtered = search ? rows.filter(m => matchesSearch(m, search)) : rows;
    const sorted = applySort(filtered, sortSpec);

    if (container.__builtFor !== viewKey) {
      buildShell(container, view, viewKey, data);
      container.__builtFor = viewKey;
    }
    patchControls(container, view, viewKey, sortSpec, filtered.length, data.length);
    patchTable(container, view, sortSpec, sorted, container.__highlight);
  }

  function buildShell(container, view, viewKey, data) {
    let html = `<div class="dt-controls">`;
    html += `<div class="dt-view-btns" style="display:flex;gap:4px;">`;
    for (const vk of VIEW_KEYS) {
      const active = vk === viewKey ? ' active' : '';
      html += `<button class="dt-view-btn${active}" data-view="${vk}">${VIEWS[vk].label}</button>`;
    }
    html += `</div>`;
    html += `<div class="dt-search-row" style="display:flex;align-items:center;gap:8px;margin-top:6px;">`;
    html += `<input class="dt-search" type="text" placeholder="Search name / creator / slug …" style="flex:1;">`;
    html += `<span class="dt-count" style="color:#666;font-size:10px;font-family:monospace;"></span>`;
    html += `</div>`;
    html += `</div>`;
    html += `<div class="dt-scroll" style="overflow-x:auto;">`;
    html += `<table class="dt-table"><thead><tr>`;
    for (let i = 0; i < view.cols.length; i++) {
      const col = view.cols[i];
      html += `<th class="${col.cls || ''}" data-col="${col.key}" data-idx="${i}">${col.label}</th>`;
    }
    html += `</tr></thead><tbody></tbody></table></div>`;
    container.innerHTML = html;

    container.querySelectorAll('th[data-col]').forEach(th => {
      th.addEventListener('click', e => {
        const key = th.dataset.col;
        const shift = e.shiftKey;
        let newSort = container.__sort ? [...container.__sort] : [];
        if (shift) {
          const existing = newSort.find(s => s.key === key);
          if (existing) {
            existing.dir = existing.dir === 'asc' ? 'desc' : 'asc';
          } else {
            newSort.push({ key, dir: 'desc' });
          }
        } else {
          const existing = newSort.find(s => s.key === key);
          if (existing && newSort.length === 1) {
            existing.dir = existing.dir === 'asc' ? 'desc' : 'asc';
          } else {
            newSort = [{ key, dir: 'desc' }];
          }
        }
        container.__sort = newSort;
        render(container, data);
      });
    });

    container.querySelectorAll('.dt-view-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        container.__view = btn.dataset.view;
        container.__sort = VIEWS[container.__view].defaultSort
          ? [...VIEWS[container.__view].defaultSort]
          : [];
        container.__search = '';
        render(container, data);
      });
    });

    const searchInput = container.querySelector('.dt-search');
    if (searchInput) {
      searchInput.addEventListener('input', () => {
        container.__search = searchInput.value;
        render(container, data);
      });
    }
  }

  function patchControls(container, view, viewKey, sortSpec, filteredCount, total) {
    const count = container.querySelector('.dt-count');
    if (count) count.textContent = `${filteredCount} / ${total}`;
    container.querySelectorAll('.dt-view-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.view === viewKey);
    });
    container.querySelectorAll('th[data-col]').forEach(th => {
      const key = th.dataset.col;
      const active = sortSpec.some(s => s.key === key);
      th.classList.toggle('sorted', active);
      const ind = getSortIndicator(sortSpec, key);
      const label = view.cols.find(c => c.key === key);
      th.firstChild ? (th.childNodes[0].nodeValue = `${label ? label.label : key} `) : null;
      const existing = th.querySelector('.sort-indicator');
      if (existing) existing.remove();
      if (ind) {
        const span = document.createElement('span');
        span.className = 'sort-indicator';
        span.textContent = ind;
        th.appendChild(span);
      }
    });
  }

  function patchTable(container, view, sortSpec, sorted, highlight) {
    const tbody = container.querySelector('.dt-table tbody');
    if (!tbody) return;
    let html = '';
    for (let i = 0; i < sorted.length; i++) {
      const r = sorted[i];
      const hl = highlight && r.slug === highlight;
      const dimmed = window.__legendFilter && window.__modelOpacity(r) < 1;
      const hidden = window.__filterMode === 'hide' && window.__modelOpacity(r) === 0;
      html += `<tr class="${hl ? 'hl' : ''}" data-slug="${r.slug}" style="${hidden ? 'display:none' : dimmed ? 'opacity:0.15' : ''}">`;
      for (let j = 0; j < view.cols.length; j++) {
        const col = view.cols[j];
        const val = col.render(r, i);
        html += `<td class="${col.cls || ''}">${val}</td>`;
      }
      html += `</tr>`;
    }
    tbody.innerHTML = html;
  }

  window.VIZ_REGISTRY = window.VIZ_REGISTRY || [];
  window.VIZ_REGISTRY.push({
    id: 'data-table',
    name: 'Data Tables',
    subtitle: 'Sortable multi-view tables — multi-column sort with shift+click',
    render
  });

  window.DATA_TABLE = { VIEWS, applySort, matchesSearch };
})();
