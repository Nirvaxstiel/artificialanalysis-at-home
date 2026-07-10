// Merger of 01 (bubble) + 03 (pareto frontier x reasoning tax). Axes from any source.

(function() {
  const CREATOR_COLORS = window.CREATOR_COLORS;
  const CREATOR_BORDER = window.CREATOR_BORDER || {};
  const { wireTooltips, placeLabel } = window.VIZ_HELPERS || {};

  const AXES = {
    quality: [
      { key: 'intel', label: 'AA Intel Index', unit: '' },
      { key: 'livebench_average', label: 'LiveBench Avg', unit: '' },
      { key: 'livebench_coding', label: 'LiveBench Coding', unit: '' },
      { key: 'livebench_reasoning', label: 'LiveBench Reasoning', unit: '' },
      { key: 'livebench_mathematics', label: 'LiveBench Math', unit: '' },
      { key: 'livebench_language', label: 'LiveBench Language', unit: '' },
      { key: 'arena_code_elo', label: 'Arena Code Elo', unit: '' },
      { key: 'arena_text_elo', label: 'Arena Text Elo', unit: '' },
      { key: 'openllm_average', label: 'OpenLLM Avg', unit: '' },
    ],
    cost: [
      { key: 'inp_price', label: 'AA Input $/Mtok', unit: 'USD', log: true },
      { key: 'cost_per_task', label: 'AA Cost / Task', unit: 'USD', log: true },
      { key: 'out_price', label: 'AA Output $/Mtok', unit: 'USD', log: true },
      { key: 'openrouter_inp_price_per_m', label: 'OR Input $/Mtok', unit: 'USD', log: true },
      { key: 'openrouter_out_price_per_m', label: 'OR Output $/Mtok', unit: 'USD', log: true },
    ],
    size: [
      { key: 'tokens_m', label: 'Output Tokens', unit: 'M' },
      { key: 'params_b', label: 'Params', unit: 'B' },
      { key: 'context_window', label: 'Context Window', unit: '' },
      { key: 'arena_code_votes', label: 'Arena Code Votes', unit: '' },
      { key: 'arena_text_votes', label: 'Arena Text Votes', unit: '' },
    ],
  };

  const REASONING_COLORS = {
    low:  '#b6ff3c',
    mid:  '#ff6a00',
    high: '#ff3366',
    none: '#888888'
  };

  function reasoningColor(pct) {
    if (pct == null) return REASONING_COLORS.none;
    if (pct < 20) return REASONING_COLORS.low;
    if (pct <= 50) return REASONING_COLORS.mid;
    return REASONING_COLORS.high;
  }
  function reasoningBucket(pct) {
    if (pct == null) return 'none';
    if (pct < 20) return 'low';
    if (pct <= 50) return 'mid';
    return 'high';
  }

  function computePareto(pts, costKey, qualityKey) {
    const sorted = pts
      .filter(m => m[costKey] != null && m[costKey] > 0 && m[qualityKey] != null)
      .sort((a, b) => a[costKey] - b[costKey]);
    if (sorted.length < 2) return sorted;
    const frontier = [];
    let maxQ = -Infinity;
    for (const m of sorted) {
      if (m[qualityKey] > maxQ) {
        frontier.push(m);
        maxQ = m[qualityKey] + 1e-9;
      }
    }
    return frontier;
  }

  function fmtV(v) {
    if (v == null) return '—';
    if (Math.abs(v) >= 100) return v.toFixed(0);
    if (Math.abs(v) >= 1) return v.toFixed(1);
    if (Math.abs(v) >= 0.01) return v.toFixed(2);
    if (Math.abs(v) >= 1e-6) return v.toFixed(4);
    return v.toExponential(2);
  }

  function niceTicks(min, max, n, isLog) {
    if (isLog) {
      // 1-2-5 pattern per decade
      const ticks = [];
      let d = Math.pow(10, Math.floor(Math.log10(min)));
      while (d <= max * 1.05) {
        for (const m of [1, 2, 5]) {
          const v = d * m;
          if (v >= min * 0.9 && v <= max * 1.1) ticks.push(v);
        }
        d *= 10;
      }
      return ticks.length > 1 ? ticks : [min, max];
    }
    const range = max - min || 1;
    const step = range / n;
    const mag = Math.pow(10, Math.floor(Math.log10(step)));
    let nice;
    const r = step / mag;
    if (r <= 1.5) nice = mag;
    else if (r <= 3) nice = 2 * mag;
    else if (r <= 7) nice = 5 * mag;
    else nice = 10 * mag;
    const start = Math.ceil(min / nice) * nice;
    const ticks = [];
    for (let v = start; v <= max * 1.05 + nice; v += nice) {
      if (v >= min && v <= max) ticks.push(v);
    }
    return ticks.length > 1 ? ticks : [min, max];
  }

  function render(container, data) {
    const W = 1100; const H = 600;
    const M = { top: 50, right: 30, bottom: 50, left: 70 };
    const innerW = W - M.left - M.right;
    const innerH = H - M.top - M.bottom;

    const qualityKey = container.__qualityAxis || window.VIZ_DEFAULTS.crossover.qualityAxis;
    const costKey = container.__costAxis || window.VIZ_DEFAULTS.crossover.costAxis;
    const sizeKey = container.__sizeAxis || window.VIZ_DEFAULTS.crossover.sizeAxis;
    const colorMode = container.__colorMode || window.VIZ_DEFAULTS.crossover.colorMode;

    const qCfg = AXES.quality.find(a => a.key === qualityKey) || { key: qualityKey, label: qualityKey, unit: '' };
    const cCfg = AXES.cost.find(a => a.key === costKey) || { key: costKey, label: costKey, unit: 'USD', log: false };
    const sCfg = AXES.size.find(a => a.key === sizeKey) || { key: sizeKey, label: sizeKey, unit: '' };

    const pts = data.filter(m =>
      m[qualityKey] != null && m[costKey] != null && m[costKey] > 0
    );

    if (pts.length === 0) {
      container.innerHTML = `<div style="padding:60px;color:#666;font-family:monospace;text-align:center;">No models with data for selected axis combination</div>`;
      _wireAxisUI(container, data);
      _wireToggle(container, data);
      return;
    }

    const costVals = pts.map(m => m[costKey]);
    const qualVals = pts.map(m => m[qualityKey]);
    const sizeVals = pts.map(m => m[sizeKey]);

    const minCost = Math.min(...costVals);
    const maxCost = Math.max(...costVals);
    const minQual = Math.min(...qualVals);
    const maxQual = Math.max(...qualVals);
    const minSize = Math.min(...sizeVals);
    const maxSize = Math.max(...sizeVals);

    // Pareto frontier (dynamic)
    const paretoModels = computePareto(pts, costKey, qualityKey);

    // Scales
    const useLog = cCfg.log !== false;
    let xScale, yScale, rScale;

    if (useLog) {
      const logMin = Math.log10(minCost), logMax = Math.log10(maxCost);
      xScale = v => M.left + (Math.log10(Math.max(v, 1e-12)) - logMin) / (logMax - logMin) * innerW;
    } else {
      xScale = v => M.left + (v - minCost) / (maxCost - minCost) * innerW;
    }
    yScale = v => M.top + (1 - (v - minQual) / (maxQual - minQual)) * innerH;
    {
      const d = maxSize - minSize || 1;
      if (!isFinite(minSize) || !isFinite(maxSize)) {
        rScale = () => 8;  // size axis fully null → uniform radius
      } else {
        rScale = t => 4 + Math.sqrt((t - minSize) / d) * 22;
      }
    }

    const costTicks = niceTicks(minCost, maxCost, 7, useLog);
    const qualTicks = niceTicks(minQual, maxQual, 8, false);

    // Median lines for quadrant ref
    const midCost = pts.sort((a,b) => a[costKey] - b[costKey])[Math.floor(pts.length/2)][costKey];
    const midQual = pts.sort((a,b) => a[qualityKey] - b[qualityKey])[Math.floor(pts.length/2)][qualityKey];

    let svg = '';

    // Quadrant box (low cost + high quality)
    const quadX = useLog ? xScale(minCost) : xScale(minCost);
    const quadW = xScale(midCost) - quadX;
    const quadY = yScale(midQual);
    const quadH = yScale(maxQual) - yScale(midQual);
    if (quadW > 5 && quadH > 5) {
      svg += `<rect x="${quadX}" y="${quadY}" width="${quadW}" height="${quadH}" fill="rgba(182,255,60,0.04)" stroke="rgba(182,255,60,0.25)" stroke-dasharray="3 3"/>`;
    }

    // Median crosshairs
    svg += `<line x1="${xScale(midCost)}" y1="${M.top}" x2="${xScale(midCost)}" y2="${H - M.bottom}" stroke="#444" stroke-width="1" stroke-dasharray="2 4"/>`;
    svg += `<line x1="${M.left}" y1="${yScale(midQual)}" x2="${W - M.right}" y2="${yScale(midQual)}" stroke="#444" stroke-width="1" stroke-dasharray="2 4"/>`;
    svg += `<text x="${xScale(midCost)}" y="${M.top - 6}" text-anchor="middle" fill="#555" font-size="9" font-family="monospace">median cost</text>`;
    svg += `<text x="${M.left - 4}" y="${yScale(midQual) - 4}" text-anchor="end" fill="#555" font-size="9" font-family="monospace">median quality</text>`;

    // Grid
    for (const t of costTicks) svg += `<line class="grid" x1="${xScale(t)}" y1="${M.top}" x2="${xScale(t)}" y2="${H - M.bottom}"/>`;
    for (const t of qualTicks) svg += `<line class="grid" x1="${M.left}" y1="${yScale(t)}" x2="${W - M.right}" y2="${yScale(t)}"/>`;

    // Axes
    svg += '<g class="axis">';
    for (const t of costTicks) {
      svg += `<text x="${xScale(t)}" y="${H - M.bottom + 18}" text-anchor="middle" fill="#f5f5f0" font-size="11" font-family="monospace">${fmtV(t)}</text>`;
      svg += `<line x1="${xScale(t)}" y1="${H - M.bottom}" x2="${xScale(t)}" y2="${H - M.bottom + 4}" stroke="#f5f5f0"/>`;
    }
    for (const t of qualTicks) {
      svg += `<text x="${M.left - 8}" y="${yScale(t) + 4}" text-anchor="end" fill="#f5f5f0" font-size="11" font-family="monospace">${fmtV(t)}</text>`;
      svg += `<line x1="${M.left - 4}" y1="${yScale(t)}" x2="${M.left}" y2="${yScale(t)}" stroke="#f5f5f0"/>`;
    }
    const costLabel = `${cCfg.label}${useLog ? ' (log)' : ''}`;
    svg += `<text x="${W/2}" y="${H - 6}" text-anchor="middle" font-weight="800" font-size="12" fill="#f5f5f0" font-family="monospace">${costLabel}</text>`;
    svg += `<text x="16" y="${H/2}" text-anchor="middle" font-weight="800" font-size="12" fill="#f5f5f0" font-family="monospace" transform="rotate(-90 16 ${H/2})">${qCfg.label}</text>`;
    svg += '</g>';

    // Pareto frontier
    if (paretoModels.length > 1) {
      const ps = paretoModels.map(m => `${xScale(m[costKey])},${yScale(m[qualityKey])}`).join(' ');
      svg += `<polyline points="${ps}" fill="none" stroke="#fff" stroke-width="1.5" stroke-dasharray="6 4" stroke-opacity="0.7"/>`;
      for (const m of paretoModels) {
        const cx = xScale(m[costKey]), cy = yScale(m[qualityKey]);
        svg += `<polygon points="${cx},${cy-4} ${cx+4},${cy} ${cx},${cy+4} ${cx-4},${cy}" fill="#fff" fill-opacity="0.9" stroke="#000" stroke-width="1"/>`;
      }
    }

    // Points
    for (const m of pts) {
      const fo = window.__modelOpacity(m);
      if (fo === 0) continue;
      const so = fo;
      const cx = xScale(m[costKey]), cy = yScale(m[qualityKey]), r = rScale(m[sizeKey]);
      let fill, stroke;
      if (colorMode === 'reasoning') {
        fill = reasoningColor(m.reasoning_tax_pct);
        stroke = '#000';
      } else {
        fill = window.creatorColor(m.creator);
        stroke = CREATOR_BORDER[m.creator] || "#000";
      }
      svg += `<circle class="point" data-slug="${m.slug}" cx="${cx}" cy="${cy}" r="${Math.max(r, 3)}" fill="${fill}" fill-opacity="${fo}" stroke="${stroke}" stroke-width="1.5" stroke-opacity="${so}"></circle>`;
      // Invisible hit-target for overlapping nodes
      svg += `<circle class="point" data-slug="${m.slug}" cx="${cx}" cy="${cy}" r="${Math.max(r + 5, 8)}" fill="transparent" stroke="none" style="pointer-events:all"></circle>`;
    }

    // Labels on pareto models only
    const labelPositions = [];
    for (const m of paretoModels) {
      const cx = xScale(m[costKey]), cy = yScale(m[qualityKey]), r = rScale(m[sizeKey]);
      const placed = placeLabel(cx, cy, r, m.name, labelPositions, { W, H });
      if (!placed) continue;
      const cleanName = m.name.replace(/\s*\((xhigh|high|medium|low|with fallback|max)\)\s*/i, '');
      const shortLabel = cleanName.length > 22 ? cleanName.slice(0, 20) + '…' : cleanName;
      let lo = window.__modelOpacity(m);
      if (lo === 0) continue;
      svg += `<text class="label" x="${placed.x}" y="${placed.y}" text-anchor="${placed.anchor}" font-size="9" font-weight="700" fill="#f5f5f0" stroke="#000" stroke-width="2.5" paint-order="stroke" opacity="${lo}" data-slug="${m.slug}">${shortLabel}</text>`;
    }

    container.innerHTML = `<svg viewBox="0 0 ${W} ${H}">${svg}</svg>`;

    // Click-to-filter via generic legend filter (creator + reasoning)
    container.querySelectorAll('.leg-cr, .leg-rg').forEach(el => {
      el.addEventListener('click', () => window.__setLegendFilter(el.dataset.lgDim, el.dataset.lgVal));
    });

    wireTooltips(container, data, '.point, .label');
    _wireAxisUI(container, data);
    _wireToggle(container, data);
  }

  function _createAxisPicker(opts) {
    const { options, value, label, onChange } = opts;

    // --- Trigger button ---
    const wrap = document.createElement('span');
    wrap.style.cssText = 'position:relative;display:inline-block;';

    const labelSpan = document.createElement('span');
    labelSpan.textContent = label;
    labelSpan.style.cssText = 'color:#888;font-size:10px;text-transform:uppercase;letter-spacing:0.08em;font-weight:700;margin-right:4px;';

    const trigger = document.createElement('button');
    const curOpt = options.find(o => o.key === value);
    trigger.textContent = (curOpt ? curOpt.label : '—') + '  ▼';
    trigger.dataset.value = value;
    trigger.style.cssText =
      'background:#0a0a0a;color:#f5f5f0;border:2px solid #444;padding:3px 10px 3px 8px;'
      + 'font-family:monospace;font-size:11px;cursor:pointer;text-align:left;'
      + 'white-space:nowrap;outline:none;';
    trigger.addEventListener('mouseenter', () => { trigger.style.borderColor = '#666'; });
    trigger.addEventListener('mouseleave', () => {
      if (!wrap.__open) trigger.style.borderColor = '#444';
    });

    // --- Popup ---
    const popup = document.createElement('div');
    popup.style.cssText =
      'display:none;position:absolute;top:100%;left:0;z-index:300;'
      + 'background:#161616;border:2px solid rgba(182,255,60,0.4);'
      + 'min-width:200px;max-height:260px;flex-direction:column;';

    // Filter input
    const filter = document.createElement('input');
    filter.type = 'text';
    filter.placeholder = 'Filter...';
    filter.autocomplete = 'off';
    filter.spellcheck = false;
    filter.style.cssText =
      'background:#0a0a0a;color:#f5f5f0;border:none;border-bottom:1px solid #333;'
      + 'padding:6px 8px;font-family:monospace;font-size:11px;outline:none;width:100%;box-sizing:border-box;';

    // List container
    const list = document.createElement('div');
    list.style.cssText = 'overflow-y:auto;flex:1;';

    let curVal = value;
    let open = false;

    function renderList(q) {
      const ql = (q || '').toLowerCase();
      const filtered = options.filter(o =>
        o.label.toLowerCase().includes(ql) || o.key.toLowerCase().includes(ql)
      );
      list.innerHTML = '';
      if (filtered.length === 0) {
        const ni = document.createElement('div');
        ni.textContent = '∅ no matches';
        ni.style.cssText = 'padding:10px;color:#666;font-size:10px;text-align:center;font-family:monospace;';
        list.appendChild(ni);
        return;
      }
      for (const opt of filtered) {
        const item = document.createElement('div');
        item.textContent = opt.label;
        item.dataset.value = opt.key;
        item.style.cssText =
          'padding:5px 8px;cursor:pointer;font-family:monospace;font-size:11px;color:#ccc;'
          + 'border-bottom:1px solid #1a1a1a;';
        if (opt.key === curVal) {
          item.style.background = '#1a1a1a';
          item.style.color = '#b6ff3c';
          item.style.fontWeight = '700';
        }
        item.addEventListener('mouseenter', () => {
          if (opt.key !== curVal) item.style.background = '#222';
        });
        item.addEventListener('mouseleave', () => {
          if (opt.key !== curVal) item.style.background = 'transparent';
        });
        item.addEventListener('mousedown', e => {
          e.preventDefault();
          curVal = opt.key;
          trigger.textContent = opt.label + '  ▼';
          trigger.dataset.value = opt.key;
          close();
          if (onChange) onChange(opt.key);
        });
        list.appendChild(item);
      }
    }

    function openPopup() {
      open = true;
      wrap.__open = true;
      trigger.style.borderColor = 'rgba(182,255,60,0.5)';
      popup.style.display = 'flex';
      filter.value = '';
      renderList('');
      filter.focus();
    }

    function close() {
      open = false;
      wrap.__open = false;
      trigger.style.borderColor = '#444';
      popup.style.display = 'none';
    }

    trigger.addEventListener('click', e => {
      e.stopPropagation();
      if (open) close();
      else openPopup();
    });

    filter.addEventListener('input', () => renderList(filter.value));
    filter.addEventListener('keydown', e => {
      const items = list.querySelectorAll('[data-value]');
      if (items.length === 0) return;
      let idx = Array.from(items).findIndex(el => el.dataset.value === curVal);
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        idx = Math.min(idx + 1, items.length - 1);
        items[idx].scrollIntoView({ block: 'nearest' });
        curVal = items[idx].dataset.value;
        renderList(filter.value);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        idx = Math.max(idx - 1, 0);
        items[idx].scrollIntoView({ block: 'nearest' });
        curVal = items[idx].dataset.value;
        renderList(filter.value);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const match = Array.from(items).find(el => el.dataset.value === curVal);
        if (match) {
          curVal = match.dataset.value;
          const m = options.find(o => o.key === curVal);
          if (m) trigger.textContent = m.label + '  ▼';
          trigger.dataset.value = curVal;
          close();
          if (onChange) onChange(curVal);
        }
      } else if (e.key === 'Escape') {
        close();
      }
    });

    // Close on outside click
    document.addEventListener('mousedown', e => {
      if (open && !wrap.contains(e.target)) close();
    }, { passive: true });

    wrap.appendChild(labelSpan);
    wrap.appendChild(trigger);
    wrap.appendChild(popup);
    popup.appendChild(filter);
    popup.appendChild(list);
    return wrap;
  }

  function _wireAxisUI(container, data) {
    const parent = container.parentElement;
    const existing = parent && parent.querySelector('.axis-picker-row');
    if (existing) existing.remove();

    const qualityKey = container.__qualityAxis || window.VIZ_DEFAULTS.crossover.qualityAxis;
    const costKey = container.__costAxis || window.VIZ_DEFAULTS.crossover.costAxis;
    const sizeKey = container.__sizeAxis || window.VIZ_DEFAULTS.crossover.sizeAxis;

    const row = document.createElement('div');
    row.className = 'axis-picker-row';
    row.style.cssText = 'display:flex;align-items:center;gap:6px;margin-bottom:6px;flex-wrap:wrap;';

    function onAnyChange() {
      container.__qualityAxis = row.querySelector('[data-picker="quality"] button').dataset.value;
      container.__costAxis = row.querySelector('[data-picker="cost"] button').dataset.value;
      container.__sizeAxis = row.querySelector('[data-picker="size"] button').dataset.value;
      render(container, data);
    }

    const costPicker = _createAxisPicker({ options: AXES.cost, value: costKey, label: 'X', onChange: onAnyChange });
    costPicker.dataset.picker = 'cost';
    row.appendChild(costPicker);

    const cross = document.createElement('span');
    cross.textContent = '×';
    cross.style.cssText = 'color:#666;font-size:13px;font-weight:800;';
    row.appendChild(cross);

    const qualityPicker = _createAxisPicker({ options: AXES.quality, value: qualityKey, label: 'Y', onChange: onAnyChange });
    qualityPicker.dataset.picker = 'quality';
    row.appendChild(qualityPicker);

    const sizePicker = _createAxisPicker({ options: AXES.size, value: sizeKey, label: 'Size:', onChange: onAnyChange });
    sizePicker.dataset.picker = 'size';
    row.appendChild(sizePicker);

    if (parent) parent.insertBefore(row, container);
  }

  function _wireToggle(container, data) {
    const parent = container.parentElement;
    const existing = parent && parent.querySelector('.color-toggle-row');
    if (existing) existing.remove();

    const colorMode = container.__colorMode || window.VIZ_DEFAULTS.crossover.colorMode;

    const div = document.createElement('div');
    div.className = 'color-toggle-row';
    div.style.cssText = 'display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap;';

    const sizeLabel = (AXES.size.find(a => a.key === (container.__sizeAxis || window.VIZ_DEFAULTS.crossover.sizeAxis)) || {}).label || 'Size';
    div.innerHTML = `
      <span style="color:var(--muted,#888);font-size:10px;text-transform:uppercase;letter-spacing:0.08em;font-weight:700;">Color:</span>
      <button class="color-toggle-btn ${colorMode==='creator'?'active':''}" data-mode="creator">Creator</button>
      <button class="color-toggle-btn ${colorMode==='reasoning'?'active':''}" data-mode="reasoning">Reasoning Tax %</button>
      <span style="color:#666;font-size:8px;margin-left:auto;">BUBBLE SIZE = ${sizeLabel} · HOVER FOR DETAILS</span>
    `;

    if (parent) parent.insertBefore(div, container);

    div.querySelectorAll('.color-toggle-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        container.__colorMode = btn.dataset.mode;
        render(container, data);
      });
    });
  }

  window.VIZ_REGISTRY = window.VIZ_REGISTRY || [];
  window.VIZ_REGISTRY.push({
    id: 'crossover',
    name: 'The Crossover',
    subtitle: 'Pick axes from any source — IQ, LiveBench, Arena Elo, OpenRouter pricing, and more',
    render
  });
})();
