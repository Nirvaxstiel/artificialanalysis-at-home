// Sortable data table — multi-column sort, search, 6 views:
//   Model Detail / AA Indexes / Provider Rollup / LiveBench / Cost Efficiency / Provider Data
//
// Shared table infrastructure (buildShell, patchControls, patchTable, sort, search)
// used by all views. Provider Data view adds a provider selector that only appears
// when that view is active — same wiring pattern as view buttons, no duplicate code.

(function() {
  const CREATOR_COLORS = window.CREATOR_COLORS || {};

  // ── Column + View definitions ────────────────────────────────────────────
  // Each view: { label, cols: [{key,label,render(row,idx),cls?}], buildRows(data,opts),
  //              defaultSort: [{key,dir}], options?: { build(data), label, key } }
  // opts passed to buildRows: { view, [optionKey]: selectedOption }

  const VIEWS = {
    model: {
      label: 'Model Detail',
      defaultSort: [{ key: 'intel', dir: 'desc' }],
      buildRows: data => data.map(m => ({ ...m, providers: (m.dirac_cache_hit_rates || []).length })),
      cols: [
        { key: 'name', label: 'NAME', render: r => r.name, cls: 'name-cell' },
        { key: 'creator', label: 'CREATOR', render: r =>
          `<span class="dot dot-sm" style="background:${window.creatorColor(r.creator)}"></span>${r.creator ?? '—'}` },
        { key: 'intel', label: 'IQ', render: r => r.intel ?? '—', cls: 'num' },
        { key: 'context_window', label: 'CTX', render: r =>
          r.context_window != null ? window.VIZ_NUM.fmtCount(r.context_window) : '—', cls: 'num' },
        { key: 'cost_per_task', label: '$ / TASK', render: r =>
          r.cost_per_task != null ? window.VIZ_NUM.fmtUSD(r.cost_per_task) : '—', cls: 'num' },

        { key: 'speed_tps', label: 'SPEED t/s', render: r =>
          r.speed_tps != null ? window.VIZ_NUM.fmtCompact(r.speed_tps, { decimals: 0 }) : '—', cls: 'num' },
        { key: 'out_price', label: '$ / M TOK', render: r =>
          r.out_price != null ? window.VIZ_NUM.fmtUSD(r.out_price) : '—', cls: 'num' },

        { key: 'reasoning_tax_pct', label: 'RSN TAX %', render: r =>
          r.reasoning_tax_pct != null ? r.reasoning_tax_pct.toFixed(0) + '%' : '—', cls: 'num' },
        { key: 'livebench_average', label: 'LB AVG', render: r =>
          r.livebench_average != null ? r.livebench_average.toFixed(1) : '—', cls: 'num' },
        { key: 'arena_code_elo', label: 'CODE ELO', render: r => r.arena_code_elo ?? '—', cls: 'num' },
        { key: 'openrouter_inp_price_per_m', label: 'OR IN $/M', render: r =>
          r.openrouter_inp_price_per_m != null ? window.VIZ_NUM.fmtUSD(r.openrouter_inp_price_per_m) : '—', cls: 'num' },
        { key: 'params_b', label: 'PARAMS B', render: r =>
          r.params_b != null ? r.params_b.toFixed(0) : '—', cls: 'num' },
        { key: 'providers', label: 'PROV', render: r =>
          r.providers ? r.providers : '—', cls: 'num' },
        { key: 'cache_hit_rate_max', label: 'BEST HIT %', render: r =>
          r.cache_hit_rate_max != null ? r.cache_hit_rate_max.toFixed(1) + '%' : '—', cls: 'num' },
        { key: 'type', label: 'TYPE', render: r => r.type ?? '—' },
      ],
    },
    aaIndexes: {
      label: 'AA Indexes',
      defaultSort: [{ key: 'intel', dir: 'desc' }],
      buildRows: data => data,
      cols: [
        { key: 'name', label: 'NAME', render: r => r.name, cls: 'name-cell' },
        { key: 'creator', label: 'CREATOR', render: r =>
          `<span class="dot dot-sm" style="background:${window.creatorColor(r.creator)}"></span>${r.creator ?? '—'}` },
        { key: 'intel', label: 'INTEL', render: r => r.intel ?? '—', cls: 'num' },
        { key: 'aa_finance_accounting_index', label: 'FIN & ACCT', render: r =>
          r.aa_finance_accounting_index != null ? r.aa_finance_accounting_index.toFixed(1) : '—', cls: 'num' },
        { key: 'aa_analyst_agent_pass_5', label: 'ANALYST pass⁵', render: r =>
          r.aa_analyst_agent_pass_5 != null ? (r.aa_analyst_agent_pass_5 * 100).toFixed(1) + '%' : '—', cls: 'num' },
        { key: 'aa_briefcase_elo', label: 'BRIEFCASE ELO', render: r =>
          r.aa_briefcase_elo != null ? r.aa_briefcase_elo.toFixed(1) : '—', cls: 'num' },
        { key: 'aa_gdpval_elo', label: 'GDPVAL ELO', render: r =>
          r.aa_gdpval_elo != null ? r.aa_gdpval_elo.toFixed(1) : '—', cls: 'num' },
        { key: 'aa_omniscience_index', label: 'OMNISCIENCE', render: r =>
          r.aa_omniscience_index != null ? r.aa_omniscience_index.toFixed(1) : '—', cls: 'num' },
        { key: 'aa_time_per_task', label: 'TIME / TASK', render: r =>
          r.aa_time_per_task != null ? r.aa_time_per_task.toFixed(2) + 's' : '—', cls: 'num' },
      ],
    },
    provider: {
      label: 'Provider Rollup',
      defaultSort: [{ key: 'avgIQ', dir: 'desc' }],
      buildRows(data) {
        const rollup = {};
        for (const m of data) {
          const creator = m.creator ?? 'Unattributed';
          if (!rollup[creator]) rollup[creator] = { count: 0, iq: [], cost: [] };
          rollup[creator].count++;
          if (m.intel != null) rollup[creator].iq.push(m.intel);
          if (m.cost_per_task != null) rollup[creator].cost.push(m.cost_per_task);
        }
        const avg = arr => arr.length ? arr.reduce((a,b)=>a+b,0) / arr.length : null;
        return Object.entries(rollup).map(([creator, d]) => ({
          creator, count: d.count,
          avgIQ: avg(d.iq), avgCost: avg(d.cost),
        }));
      },
      cols: [
        { key: 'creator', label: 'CREATOR', render: (r, c) =>
          `<span class="dot dot-lg" style="background:${window.creatorColor(r.creator)}"></span>${r.creator ?? '—'}` },
        { key: 'count', label: '# MODELS', render: r => r.count, cls: 'num' },
        { key: 'avgIQ', label: 'AVG IQ', render: r => r.avgIQ != null ? r.avgIQ.toFixed(1) : '—', cls: 'num' },
        { key: 'avgCost', label: 'AVG $ / TASK', render: r =>
          r.avgCost != null ? window.VIZ_NUM.fmtUSD(r.avgCost) : '—', cls: 'num' },

      ],
    },
    livebench: {
      label: 'LiveBench',
      defaultSort: [{ key: 'livebench_average', dir: 'desc' }],
      buildRows: data => data,
      cols: [
        { key: 'name', label: 'NAME', render: r => r.name },
        { key: 'creator', label: 'CREATOR', render: r =>
          `<span class="dot dot-sm" style="background:${window.creatorColor(r.creator)}"></span>${r.creator ?? '—'}` },
        { key: 'livebench_average', label: 'AVG', render: r =>
          r.livebench_average != null ? r.livebench_average.toFixed(1) : '—', cls: 'num' },
        { key: 'livebench_coding', label: 'CODING', render: r =>
          r.livebench_coding != null ? r.livebench_coding.toFixed(1) : '—', cls: 'num' },
        { key: 'livebench_reasoning', label: 'REASON', render: r =>
          r.livebench_reasoning != null ? r.livebench_reasoning.toFixed(1) : '—', cls: 'num' },
        { key: 'livebench_mathematics', label: 'MATH', render: r =>
          r.livebench_mathematics != null ? r.livebench_mathematics.toFixed(1) : '—', cls: 'num' },
        { key: 'livebench_language', label: 'LANG', render: r =>
          r.livebench_language != null ? r.livebench_language.toFixed(1) : '—', cls: 'num' },
        { key: 'livebench_data_analysis', label: 'DATA', render: r =>
          r.livebench_data_analysis != null ? r.livebench_data_analysis.toFixed(1) : '—', cls: 'num' },
        { key: 'livebench_agentic_coding', label: 'AGENT', render: r =>
          r.livebench_agentic_coding != null ? r.livebench_agentic_coding.toFixed(1) : '—', cls: 'num' },
        { key: 'livebench_if', label: 'IF', render: r =>
          r.livebench_if != null ? r.livebench_if.toFixed(1) : '—', cls: 'num' },
      ],
    },
    efficiency: {
      label: 'Cost Efficiency',
      defaultSort: [{ key: 'cost_per_iq', dir: 'asc' }],
      buildRows: data => data.map(model => {
        const costPerIq = model.cost_per_task > 0 && model.intel > 0
          ? model.cost_per_task / model.intel
          : null;
        const provenance = { ...(model.provenance || {}) };
        if (costPerIq != null) provenance.cost_per_iq = 'derived';
        return { ...model, cost_per_iq: costPerIq, provenance };
      }),
      cols: [
        { key: 'name', label: 'NAME', render: r => r.name, cls: 'name-cell' },
        { key: 'creator', label: 'CREATOR', render: r =>
          `<span class="dot dot-sm" style="background:${window.creatorColor(r.creator)}"></span>${r.creator ?? '—'}` },
        { key: 'intel', label: 'IQ', render: r => r.intel ?? '—', cls: 'num' },
        { key: 'cost_per_task', label: '$ / TASK', render: r =>
          r.cost_per_task != null ? window.VIZ_NUM.fmtUSD(r.cost_per_task) : '—', cls: 'num' },
        { key: 'cost_per_iq', label: '$ / IQ PT†', render: r =>
          r.cost_per_iq != null ? `<span title="Derived from AA cost/task and intel">${window.VIZ_NUM.fmtUSD(r.cost_per_iq)}</span>` : '—', cls: 'num' },
        { key: 'reasoning_tax_pct', label: 'RSN SHARE %', render: r =>
          r.reasoning_tax_pct != null ? r.reasoning_tax_pct.toFixed(0) + '%' : '—', cls: 'num' },
        { key: 'speed_tps', label: 'SPEED t/s', render: r =>
          r.speed_tps != null ? window.VIZ_NUM.fmtCompact(r.speed_tps, { decimals: 0 }) : '—', cls: 'num' },
      ],
    },
    providerData: {
      label: 'Provider Data',
      defaultSort: [{ key: 'hit_rate', dir: 'desc' }],
      // buildRows needs opts.provider — set when providerData view is active
      buildRows(data, opts) {
        const provider = opts?.provider;
        if (!provider) return [];
        const rows = [];
        for (const m of data) {
          if (!m.dirac_cache_hit_rates) continue;
          const entry = m.dirac_cache_hit_rates.find(r => r.provider === provider);
          if (!entry) continue;
          rows.push({
            slug: m.slug,
            name: m.name,
            creator: m.creator,
            hit_rate: entry.cache_hit_rate,
            eff_input_price: entry.eff_input_price,
            eff_output_price: entry.eff_output_price,
            max_hit: m.cache_hit_rate_max,
          });
        }
        return rows;
      },
      cols: [
        { key: 'slug', label: 'MODEL', render: r =>
          `<span class="dot dot-sm" style="background:${window.creatorColor(r.creator)}"></span>${r.slug}` },
        { key: 'creator', label: 'CREATOR', render: r => r.creator || '—' },
        { key: 'hit_rate', label: 'CACHE HIT %', render: r =>
          r.hit_rate != null ? r.hit_rate.toFixed(1) + '%' : '—', cls: 'num' },
        { key: 'eff_input_price', label: 'EFF IN $/M', render: r =>
          r.eff_input_price != null ? window.VIZ_NUM.fmtUSD(r.eff_input_price) : '—', cls: 'num' },
        { key: 'eff_output_price', label: 'EFF OUT $/M', render: r =>
          r.eff_output_price != null ? window.VIZ_NUM.fmtUSD(r.eff_output_price) : '—', cls: 'num' },
        { key: 'max_hit', label: 'MAX (ALL PROV)', render: r =>
          r.max_hit != null ? r.max_hit.toFixed(1) + '%' : '—', cls: 'num' },
      ],
      // Provider selector — only shown when providerData view is active
      options: {
        key: 'provider',
        label: 'CACHE PROVIDER',
        build(data) {
          const counts = {};
          for (const m of data) {
            if (m.dirac_cache_hit_rates) {
              for (const r of m.dirac_cache_hit_rates) {
                counts[r.provider] = (counts[r.provider] || 0) + 1;
              }
            }
          }
          return Object.entries(counts)
            .sort((a, b) => b[1] - a[1])
            .map(([name, count]) => ({ name, count }));
        },
      },
    },
  };

  const VIEW_KEYS = Object.keys(VIEWS);

  // ── Shared sort (multi-column with shift+click) ──────────────────────────
  function applySort(rows, sortSpec) {
    if (!sortSpec || sortSpec.length === 0) return rows;
    const sorted = [...rows];
    sorted.sort((a, b) => {
      for (const { key, dir } of sortSpec) {
        let va = a[key], vb = b[key];

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

  // ── Shared search ─────────────────────────────────────────────────────────
  // Each view declares which fields to search. Defaults to name/creator/slug.
  const SEARCH_FIELDS = {
    model: ['name', 'creator', 'slug'],
    aaIndexes: ['name', 'creator', 'slug'],
    provider: ['creator'],
    livebench: ['name', 'creator'],
    efficiency: ['name', 'creator'],
    providerData: ['slug', 'name', 'creator'],
  };

  function matchesSearch(row, search, fields) {
    if (!search) return true;
    const q = search.toLowerCase();
    for (const f of fields) {
      const val = row[f];
      if (val != null && String(val).toLowerCase().includes(q)) return true;
    }
    return false;
  }

  // ── Shared shell builder ──────────────────────────────────────────────────
  // Builds: view buttons + optional option selector (e.g. provider buttons) +
  //         search box + table header. Called once per view activation.
  function buildShell(container, view, viewKey, data) {
    let html = '<div class="dt-controls">';

    // View toggle buttons (all views)
    html += '<div class="dt-view-btns" style="display:flex;gap:4px;">';
    for (const vk of VIEW_KEYS) {
      const active = vk === viewKey ? ' active' : '';
      html += `<button class="dt-view-btn${active}" data-view="${vk}">${VIEWS[vk].label}</button>`;
    }
    html += '</div>';

    // Optional option selector (e.g. provider buttons for providerData view)
    const viewDef = VIEWS[viewKey];
    let defaultOpt = '';
    if (viewDef.options) {
      const opts = viewDef.options.build(data);
      defaultOpt = opts[0]?.name || '';
      html += `<div class="dt-opt-btns" data-opt-key="${viewDef.options.key}"` +
      ` style="display:flex;gap:4px;flex-wrap:wrap;margin-top:6px;">`;
      for (const o of opts) {
        const active = o.name === defaultOpt ? ' active' : '';
        html += `<button class="dt-opt-btn${active}" data-opt="${o.name}">${o.name}` +
          ` <span class="dt-opt-count">(${o.count})</span></button>`;
      }
      html += '</div>';
    }

    // Search box
    html += window.VIZ_HELPERS.searchBox({ placeholder: 'Search …', rowStyle: 'margin-top:6px;' });

    html += '</div>';

    // Table
    html += '<div class="dt-scroll" style="overflow-x:auto;">';
    html += '<table class="dt-table"><thead><tr>';
    for (let i = 0; i < view.cols.length; i++) {
      const col = view.cols[i];
      html += `<th class="${col.cls || ''}" data-col="${col.key}" data-idx="${i}">${col.label}</th>`;
    }
    html += '</tr></thead><tbody></tbody></table>';
    html += '</div>';

    container.innerHTML = html;
    container.__view = viewKey;
    container.__sort = view.defaultSort ? [...view.defaultSort] : [];
    container.__search = '';
    if (viewDef.options) {
      container.__opt = defaultOpt;
    } else {
      container.__opt = null;
    }

    // Wire view buttons
    container.querySelectorAll('.dt-view-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const newView = btn.dataset.view;
        container.__view = newView;
        const newViewDef = VIEWS[newView];
        container.__sort = newViewDef.defaultSort ? [...newViewDef.defaultSort] : [];
        container.__search = '';
        // Reset option selector when switching views
        if (newViewDef.options) {
          const opts = newViewDef.options.build(data);
          container.__opt = opts[0]?.name || null;
        } else {
          container.__opt = null;
        }
        render(container, data);
      });
    });

    // Wire option buttons (provider selector)
    container.querySelectorAll('.dt-opt-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        container.__opt = btn.dataset.opt;
        container.querySelectorAll('.dt-opt-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        render(container, data);
      });
    });

    // Wire header sort clicks
    container.querySelectorAll('th[data-col]').forEach(th => {
      th.addEventListener('click', e => {
        const key = th.dataset.col;
        const shift = e.shiftKey;
        let newSort = container.__sort ? [...container.__sort] : [];
        if (shift) {
          const existing = newSort.find(s => s.key === key);
          if (existing) { existing.dir = existing.dir === 'asc' ? 'desc' : 'asc'; }
          else { newSort.push({ key, dir: 'desc' }); }
        } else {
          const existing = newSort.find(s => s.key === key);
          if (existing && newSort.length === 1) { existing.dir = existing.dir === 'asc' ? 'desc' : 'asc'; }
          else { newSort = [{ key, dir: 'desc' }]; }
        }
        container.__sort = newSort;
        render(container, data);
      });
    });

    // Wire search
    const searchInput = container.querySelector('.viz-search');
    if (searchInput) {
      searchInput.addEventListener('input', () => {
        container.__search = searchInput.value;
        render(container, data);
      });
    }
  }

  // ── Shared control patching ──────────────────────────────────────────────
  function patchControls(container, view, viewKey, sortSpec, filteredCount, total) {
    const count = container.querySelector('.viz-search-count');
    if (count) count.textContent = `${filteredCount} / ${total}`;

    // View buttons
    container.querySelectorAll('.dt-view-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.view === viewKey);
    });

    // Option buttons (provider selector) — only if active view has options
    const optKey = view.options ? view.options.key : null;
    if (optKey) {
      container.querySelectorAll('.dt-opt-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.opt === container.__opt);
      });
    }

    // Sort indicators on headers
    container.querySelectorAll('th[data-col]').forEach(th => {
      const key = th.dataset.col;
      const active = sortSpec.some(s => s.key === key);
      th.classList.toggle('sorted', active);
      const ind = getSortIndicator(sortSpec, key);
      const label = view.cols.find(c => c.key === key);
      if (th.firstChild) th.childNodes[0].nodeValue = `${label ? label.label : key} `;
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

  // ── Shared table row rendering ───────────────────────────────────────────
  function patchTable(container, view, sortSpec, sorted) {
    const tbody = container.querySelector('.dt-table tbody');
    if (!tbody) return;
    let html = '';
    for (let i = 0; i < sorted.length; i++) {
      const r = sorted[i];
      const dimmed = window.__legendFilter && window.__modelOpacity(r) < 1;
      const hidden = window.__filterMode === 'hide' && window.__modelOpacity(r) === 0;
      html += `<tr data-slug="${r.slug || ''}" style="${hidden ? 'display:none' : dimmed ? 'opacity:0.15' : ''}">`;
      for (let j = 0; j < view.cols.length; j++) {
        const col = view.cols[j];
        const val = col.render(r, i);
        html += `<td class="${col.cls || ''}">${val}</td>`;
      }
      html += '</tr>';
    }
    tbody.innerHTML = html;
  }

  // ── Main render ───────────────────────────────────────────────────────────
  function render(container, data) {
    const viewKey = container.__view || window.VIZ_DEFAULTS.dataTable.view || 'model';
    const view = VIEWS[viewKey];
    if (!view) return;

    const sortSpec = container.__sort || (view.defaultSort ? [...view.defaultSort] : []);
    const search = container.__search || '';
    const opts = { view: viewKey };
    if (view.options && container.__opt) opts[view.options.key] = container.__opt;

    const rows = view.buildRows(data, opts);
    const fields = SEARCH_FIELDS[viewKey] || ['name', 'creator', 'slug'];
    const filtered = search ? rows.filter(r => matchesSearch(r, search, fields)) : rows;
    const sorted = applySort(filtered, sortSpec);

    if (container.__builtFor !== viewKey) {
      buildShell(container, view, viewKey, data);
      container.__builtFor = viewKey;
    }
    patchControls(container, view, viewKey, sortSpec, sorted.length, rows.length);
    patchTable(container, view, sortSpec, sorted);
  }

  window.VIZ_REGISTRY = window.VIZ_REGISTRY || [];
  window.VIZ_REGISTRY.push({
    id: 'data-table',
    name: 'Data Tables',
    subtitle: 'Model Detail · AA Indexes · Provider Rollup · LiveBench · Cost Efficiency · Provider Data (cache hit rates)',
    render,
  });

  window.DATA_TABLE = { VIEWS, applySort, matchesSearch };
})();
