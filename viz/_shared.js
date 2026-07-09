// Color palette, tooltip wiring, label placement. Single source of truth; loaded before viz scripts.

(function() {

const CREATOR_COLORS = {
  "OpenAI":        "#f5f5f0",
  "Anthropic":     "#D97757",
  "Google":        "#4285F4",
  "DeepSeek":      "#536dfe",
  "Meta":          "#1877f2",
  "xAI":           "#9e9e9e",
  "MiniMax":       "#b6ff3c",
  "NVIDIA":        "#76b900",
  "Alibaba":       "#ff6a00",
  "Amazon":        "#ff9900",
  "Kimi":          "#00e5ff",
  "Z AI":          "#a855f7",
  "Xiaomi":        "#ff5722",
  "Mistral":       "#e040fb",
  "Upstage":       "#ffd740",
  "StepFun":       "#69f0ae",
  "LG AI Research":"#448aff",
  "Nous Research": "#ff6e40",
  "Perplexity":    "#b388ff",
  "Inception":     "#18ffff",
  "Reka AI":       "#ff80ab",
  "Nex AGI":       "#ccff90",
  "Tencent":       "#84ffff",
  "Arcee AI":      "#ffd180",
};
const CREATOR_BORDER = { "Mistral": "#f5f5f0", "OpenAI": "#333", "xAI": "#f5f5f0" };

// window.__legendFilter = { dim, val } | null
window.__legendFilter = null;
window.__filterSubscribers = new Set();
window.__filterMode = 'dim';

window.__modelOpacity = function(m) {
  const lf = window.__legendFilter;
  if (!lf) return 1;
  if (lf.dim === 'creator') {
    if (m.creator === lf.val) return 1;
    return window.__filterMode === 'hide' ? 0 : 0.12;
  }
  if (lf.dim === 'reasoning') {
    const buckets = { none: m.reasoning_tax_pct != null && m.reasoning_tax_pct < 1,
      low: m.reasoning_tax_pct != null && m.reasoning_tax_pct >= 1 && m.reasoning_tax_pct < 20,
      mid: m.reasoning_tax_pct != null && m.reasoning_tax_pct >= 20 && m.reasoning_tax_pct < 50,
      high: m.reasoning_tax_pct != null && m.reasoning_tax_pct >= 50 };
    const myBucket = m.reasoning_tax_pct == null ? null : Object.keys(buckets).find(k => buckets[k]);
    return myBucket === lf.val ? 1 : 0.12;
  }
  return 1;
};

window.__setLegendFilter = function(dim, val) {
  const same = window.__legendFilter && window.__legendFilter.dim === dim && window.__legendFilter.val === val;
  window.__legendFilter = same ? null : { dim, val };
  document.querySelectorAll('.lg-fi').forEach(el => {
    el.classList.toggle('active',
      window.__legendFilter && el.dataset.lgDim === window.__legendFilter.dim && el.dataset.lgVal === window.__legendFilter.val);
  });
  window.__filterSubscribers.forEach(fn => fn(window.__legendFilter));
};

window.__clearLegendFilter = function() {
  window.__legendFilter = null;
  document.querySelectorAll('.lg-fi').forEach(el => el.classList.remove('active'));
  window.__filterSubscribers.forEach(fn => fn(null));
};

window.__renderCreatorLegend = function() {
  const el = window.__creatorLegendEl || document.getElementById('creator-legend');
  if (!el) return;
  window.__creatorLegendEl = el;
  const models = window.MODELS || [];
  const creators = [...new Set(models.map(m => m.creator).filter(Boolean))].sort();
  const isAllActive = !window.__legendFilter;
  const fm = window.__filterMode || 'dim';
  const toggleHtml = `<span class=\"lg-mode\" style=\"margin-left:auto;display:inline-flex;align-items:center;gap:6px;color:#888;font-size:9px;text-transform:uppercase;letter-spacing:0.05em;\">` +
    `<span style=\"color:var(--muted);font-weight:700;\">FILTER:</span>` +
    `<button class=\"lg-mode-btn ${fm==='dim'?'active':''}\" data-mode=\"dim\" style=\"background:transparent;border:1px solid ${fm==='dim'?'var(--neon)':'#444'};color:${fm==='dim'?'var(--neon)':'#888'};padding:2px 6px;cursor:pointer;font-family:monospace;font-size:9px;\">dim</button>` +
    `<button class=\"lg-mode-btn ${fm==='hide'?'active':''}\" data-mode=\"hide\" style=\"background:transparent;border:1px solid ${fm==='hide'?'var(--neon)':'#444'};color:${fm==='hide'?'var(--neon)':'#888'};padding:2px 6px;cursor:pointer;font-family:monospace;font-size:9px;\">hide out</button>` +
    `</span>`;
  el.innerHTML = '<span class=\"lg-fi' + (isAllActive ? ' active' : '') + '\" data-lg-dim=\"\" data-lg-val=\"\">ALL</span>'
    + creators.map(c => {
        const active = window.__legendFilter && window.__legendFilter.dim === 'creator' && window.__legendFilter.val === c;
        const color = (window.CREATOR_COLORS || {})[c] || '#888';
        return `<span class=\"lg-fi${active ? ' active' : ''}\" data-lg-dim=\"creator\" data-lg-val=\"${c}\"><span class=\"cr-fs\" style=\"background:${color}\"></span>${c}</span>`;
      }).join('')
    + toggleHtml;
  const newEl = el.cloneNode(true);
  el.parentNode.replaceChild(newEl, el);
  window.__creatorLegendEl = newEl;
  newEl.addEventListener('click', e => {
    const modeBtn = e.target.closest('.lg-mode-btn');
    if (modeBtn) {
      window.__filterMode = modeBtn.dataset.mode;
      window.__filterSubscribers.forEach(fn => fn(null));
      window.__renderCreatorLegend();
      return;
    }
    const item = e.target.closest('.lg-fi');
    if (!item) return;
    const dim = item.dataset.lgDim;
    if (!dim) { window.__clearLegendFilter(); return; }
    window.__setLegendFilter(dim, item.dataset.lgVal);
  });
};

window.CREATOR_COLORS = CREATOR_COLORS;
window.CREATOR_BORDER = CREATOR_BORDER;

function wireTooltips(container, data, selectors) {
  const tt = document.getElementById('tooltip');
  if (!tt) return;
  const modelBySlug = Object.fromEntries((data || []).map(m => [m.slug, m]));
  container.querySelectorAll(selectors).forEach(el => {
    el.addEventListener('mouseenter', function() {
      if (this.style.display === 'none' || this.style.opacity === '0') {
        tt.style.display = 'none';
        return;
      }
      const m = modelBySlug[this.dataset.slug];
      if (!m) return;
      tt.innerHTML = window.buildTooltip ? window.buildTooltip(m) : m.name;
      tt.style.display = 'block';
    });
    el.addEventListener('mousemove', function(e) {
      if (this.style.display === 'none' || this.style.opacity === '0') {
        tt.style.display = 'none';
        return;
      }
      const w = tt.offsetWidth, h = tt.offsetHeight;
      const vw = window.innerWidth, vh = window.innerHeight;
      let x = e.clientX + 16, y = e.clientY + 16;
      if (x + w > vw - 8) x = e.clientX - w - 16;
      if (y + h > vh - 8) y = e.clientY - h - 16;
      if (y < 8) y = 8;
      if (x < 8) x = 8;
      tt.style.left = x + 'px';
      tt.style.top  = y + 'px';
    });
    el.addEventListener('mouseleave', function() {
      tt.style.display = 'none';
    });
  });
}

// Returns { x, y, anchor }. Clamps to viewBox if opts.W/H provided.
function placeLabel(cx, cy, r, text, occupied, opts) {
  opts = opts || {};
  const gap = opts.gap || 4;
  const h = opts.h || 11;
  const charW = opts.charW || 5.5;
  const W = opts.W;
  const H = opts.H;

  const approxW = text.length * charW;
  const candidates = [
    { x: cx, y: cy - r - gap - h, anchor: 'middle' },
    { x: cx, y: cy + r + gap + 9, anchor: 'middle' },
    { x: cx + r + gap + 2, y: cy + 3, anchor: 'start' },
    { x: cx - r - gap - 2, y: cy + 3, anchor: 'end' },
  ];

  let placed = null;
  for (const c of candidates) {
    const lx = c.anchor === 'middle' ? c.x - approxW/2
      : c.anchor === 'end' ? c.x - approxW : c.x;
    const rect = { x: lx, y: c.y - h, w: approxW, h: h + 2 };
    const collides = occupied.some(p =>
      !(rect.x + rect.w + 2 < p.x || rect.x > p.x + p.w + 2
        || rect.y + rect.h < p.y || rect.y > p.y + p.h)
    );
    if (!collides) { placed = c; occupied.push(rect); break; }
  }

  // Fallback — place above
  if (!placed) {
    placed = { x: cx, y: cy - r - gap - h, anchor: 'middle' };
    const lx = placed.x - approxW/2;
    occupied.push({ x: lx, y: placed.y - h, w: approxW, h: h + 2 });
  }

  // Clamp to viewBox (only if W/H provided)
  if (W != null && H != null) {
    if (placed.anchor === 'middle') {
      placed.x = Math.max(approxW/2 + 5, Math.min(W - approxW/2 - 5, placed.x));
    } else if (placed.anchor === 'start') {
      placed.x = Math.max(5, Math.min(W - approxW - 5, placed.x));
    } else {
      placed.x = Math.max(approxW + 5, Math.min(W - 5, placed.x));
    }
    placed.y = Math.max(h + 5, Math.min(H - 5, placed.y));
  }

  return placed;
}

function fmtV(v) {
  if (v == null) return '\u2014';
  if (Math.abs(v) >= 100) return v.toFixed(0);
  if (Math.abs(v) >= 1) return v.toFixed(1);
  if (Math.abs(v) >= 0.01) return v.toFixed(2);
  return v.toExponential(2);
}

function renderEmptyState(container, message) {
  container.innerHTML = `<div style="padding:60px 20px;text-align:center;color:#888;font-family:monospace;font-size:13px;border:1px dashed #333;margin:20px 0;">
    <div style="color:var(--neon,#b6ff3c);font-weight:700;margin-bottom:10px;">// NO DATA</div>
    <div style="font-size:11px;line-height:1.6;">${message}</div>
  </div>`;
}

function renderCoverageNote(container, shown, total, missingFields) {
  if (shown === total) return '';
  const pct = Math.round(shown / total * 100);
  return `<div style="font-family:monospace;font-size:11px;color:#888;text-align:center;padding:8px;margin-top:8px;"><span style="color:var(--neon2,#6a6);opacity:0.5;">//</span> Showing ${shown}/${total} models <span style="color:#555;">(${pct}%)</span> — requires <span style="color:#999;">${missingFields}</span></div>`;
}

function applyLegendFilter(container, models) {
  if (!window.__legendFilter) return;
  const slugOpacity = {};
  models.forEach(m => { slugOpacity[m.slug] = window.__modelOpacity(m); });
  const hideMode = window.__filterMode === 'hide';
  container.querySelectorAll('[data-slug]').forEach(el => {
    const op = slugOpacity[el.dataset.slug];
    if (op !== undefined && op < 1) {
      if (hideMode && op === 0) {
        el.style.display = 'none';
      } else {
        el.style.opacity = op;
      }
    }
  });
}

window.VIZ_HELPERS = { wireTooltips, placeLabel, renderEmptyState, renderCoverageNote, applyLegendFilter, fmtV };

window.buildTooltip = function(m) {
  const iq = m.intel ?? 0;
  const cost = m.cost_per_task;
  const tok = m.tokens_m;
  const iqPerK = cost > 0 ? (iq / cost * 1000).toFixed(0) : '\u2014';
  const reasoningPct = m.reasoning_tax_pct != null ? m.reasoning_tax_pct + '%' : '\u2014';
  let html = `<div class=\"tt-name\">${m.name}</div>
    <div class=\"tt-creator\">${m.creator} &middot; ${m.slug}</div>
    <div class=\"tt-row\"><span class=\"k\">IQ</span><span class=\"v neon\">${iq}</span></div>
    <div class=\"tt-row\"><span class=\"k\">$ / TASK</span><span class=\"v\">${cost != null ? '$' + cost.toFixed(2) : '\u2014'}</span></div>
    <div class=\"tt-row\"><span class=\"k\">OUTPUT TOK (M)</span><span class=\"v\">${tok ?? '\u2014'}</span></div>
    <div class=\"tt-row\"><span class=\"k\">$ / M TOK</span><span class=\"v\">${m.out_price ?? '\u2014'}</span></div>
    <div class=\"tt-row\"><span class=\"k\">SPEED t/s</span><span class=\"v\">${m.speed_tps ?? '\u2014'}</span></div>
    <div class=\"tt-row\"><span class=\"k\">IQ / $1K</span><span class=\"v neon\">${iqPerK}</span></div>
    <div class=\"tt-row\"><span class=\"k\">$ / IQ PT</span><span class=\"v\">$${(cost/iq).toFixed(2)}</span></div>
    <div class=\"tt-row\"><span class=\"k\">REASONING TAX</span><span class=\"v\">${reasoningPct}</span></div>
    <div class=\"tt-row\"><span class=\"k\">USEFUL $</span><span class=\"v\">$${m.useful_cost != null ? m.useful_cost.toFixed(2) : '\u2014'}</span></div>
    <div class=\"tt-row\"><span class=\"k\">ARCHETYPE</span><span class=\"v\">${m.archetype}</span></div>
    <div class=\"tt-row\"><span class=\"k\">PARETO</span><span class=\"v\">${m.pareto_optimal ? 'YES' : 'no'}</span></div>`;

  // Additional cross-source data
  const cross = [];
  if (m.livebench_average != null) {
    cross.push(`LiveBench avg: ${m.livebench_average.toFixed(1)}`);
    if (m.livebench_coding != null) cross.push(`  Coding: ${m.livebench_coding.toFixed(1)}`);
    if (m.livebench_reasoning != null) cross.push(`  Reasoning: ${m.livebench_reasoning.toFixed(1)}`);
  }
  if (m.arena_code_elo != null) cross.push(`Arena Code Elo: ${m.arena_code_elo}`);
  if (m.arena_text_elo != null) cross.push(`Arena Text Elo: ${m.arena_text_elo}`);
  if (m.openrouter_inp_price_per_m != null) {
    cross.push(`OR Input: $${m.openrouter_inp_price_per_m}/Mtok`);
    cross.push(`OR Output: $${m.openrouter_out_price_per_m}/Mtok`);
  }
  if (m.openllm_average != null) cross.push(`OpenLLM avg: ${m.openllm_average.toFixed(1)}`);
  if (m.params_b != null) cross.push(`Params: ${m.params_b}B`);
  if (m.context_window != null) cross.push(`Context: ${m.context_window >= 1000000 ? (m.context_window/1000000).toFixed(1) + 'M' : (m.context_window/1000).toFixed(0) + 'K'}`);
  if (m.co2_kg != null) cross.push(`CO₂: ${m.co2_kg}kg`);

  if (cross.length > 0) {
    html += `<div class=\"tt-seg\">${cross.join('<br>')}</div>`;
  }

  return html;
};

window.SKU_PATTERNS = [
  { keyword: 'oss',     suffix: ' OSS',   pattern: '(^|-)oss(-|$)' },
  { keyword: 'mini',    suffix: ' Mini',  pattern: '(^|-)mini(-|$)' },
  { keyword: 'nano',    suffix: ' Nano',  pattern: '(^|-)nano(-|$)' },
  { keyword: 'flash',   suffix: ' Flash', pattern: '(^|-)flash(-|$)' },
  { keyword: 'codex',   suffix: ' Code',  pattern: '(^|-)codex(-|$)' },
  { keyword: '-code',   suffix: ' Code',  pattern: '-code$' },
];

window.RADAR_AXES = [
  { key: 'avgIQ',       label: 'IQ',         angle: -Math.PI / 2 },
  { key: 'avgSpeed',    label: 'SPEED',      angle: -Math.PI / 2 + 2 * Math.PI / 6 },
  { key: 'tokenEff',    label: 'TOKEN EFF',  angle: -Math.PI / 2 + 4 * Math.PI / 6 },
  { key: 'avgCacheEff', label: 'CACHE EFF',  angle: -Math.PI / 2 + 6 * Math.PI / 6 },
  { key: 'costEff',     label: 'COST EFF',   angle: -Math.PI / 2 + 8 * Math.PI / 6 },
  { key: 'avgCtx',      label: 'CTX',        angle: -Math.PI / 2 + 10 * Math.PI / 6 },
];

window.COST_SEGMENTS = {
  aa: [
    { key: 'input_usd',       label: 'INPUT',              color: '#4a4a4a' },
    { key: 'cache_hit_usd',   label: 'CACHED INPUT',        color: '#1a6b5a' },
    { key: 'cache_write_usd', label: 'CACHE WRITE',         color: '#2a9d7a' },
    { key: 'answer_usd',      label: 'ANSWER',             color: '#b6ff3c' },
    { key: 'reasoning_usd',   label: 'REASONING',          color: '#ff3366' },
  ],
  ext: [
    { key: 'input_usd',       label: 'INPUT (UNCACHED)',    color: '#4a4a4a' },
    { key: 'cache_hit_usd',   label: 'CACHED INPUT',        color: '#1a6b5a' },
    { key: 'cache_write_usd', label: 'CACHE WRITE',         color: '#2a9d7a' },
    { key: 'answer_usd',      label: 'ANSWER',              color: '#b6ff3c' },
    { key: 'reasoning_usd',   label: 'REASONING',           color: '#ff3366' },
  ],
};
window.FIELD_LABELS = {
  intel:                'IQ',
  cost_per_task:        '$ / TASK',
  tokens_m:             'TOK (M)',
  speed_tps:            'SPEED t/s',
  inp_price:            'INPUT $/M',
  out_price:            'OUTPUT $/M',
  reasoning_tax_pct:    'RSN TAX %',
  livebench_average:    'LB AVG',
  arena_code_elo:       'CODE ELO',
  openrouter_inp_price_per_m: 'OR IN $/M',
  params_b:             'PARAMS B',
  cache_hit_price:      'CACHE $/M',
};

// Observed cache hit rates — Dirac.run / OpenRouter
window.CACHE_HIT_RATES = {
  "deepseek-v4-flash":   0.861,
  "deepseek-v4-pro":     0.879,
  "claude-sonnet-4-6-adaptive": 0.899,
  "claude-sonnet-4-6":   0.899,
  "claude-4-5-sonnet-thinking": 0.784,
  "claude-4-5-haiku-reasoning": 0.70,
  "claude-opus-4-8":     0.79,
  "claude-opus-4-7":     0.78,
  "claude-opus-4-6-adaptive": 0.77,
  "claude-sonnet-5":     0.80,
  "gpt-5-5-low":         0.553,
  "gpt-5-5-medium":      0.553,
  "gpt-5-5-high":        0.553,
  "gpt-5-5-xhigh":       0.553,
  "gpt-5-5":             0.553,
  "gpt-5-4-mini":        0.50,
  "gpt-5-4-nano":        0.50,
  "gpt-oss-20b":         0.30,
  "gpt-oss-120b":        0.30,
  "grok-4-3":            0.478,
  "gemini-3-1-pro-preview": 0.30,
  "gemini-3-5-flash":    0.30,
  "minimax-m2-7":        0.656,
  "minimax-m3":          0.75,
  "mimo-v2-5-pro":       0.747,
  "kimi-k2-6":           0.848,
  "kimi-k2-7-code":      0.848,
  "glm-5-2":             0.661,
  "qwen3-5-397b-a17b":   0.20,
  "qwen3-7-max":         0.20,
  "nova-2-0-pro-reasoning-medium": 0.20,
  "nemotron-3-ultra-550b-a55b": 0.10,
  "nemotron-3-super-120b-a12b": 0.10,
  "mistral-medium-3-5":  0.40,
};

})()
