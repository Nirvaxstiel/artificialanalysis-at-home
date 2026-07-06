// viz/_shared.js
// Shared helpers — color palette, tooltip wiring, label placement.
// Single source of truth; loaded before viz scripts.

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

// ============================================================
// Legend Filter — generic shared filter state for all views
// Single source of truth: window.__legendFilter = { dim, val } | null
// ============================================================
window.__legendFilter = null;
window.__filterSubscribers = new Set();

// Shared opacity helper — vizzes call this per model
window.__modelOpacity = function(m) {
  const lf = window.__legendFilter;
  if (!lf) return 1;
  if (lf.dim === 'creator') return m.creator === lf.val ? 1 : 0.12;
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
  // Update HTML .lg-fi highlights
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
  const src = window.PROCESSED_DATA;
  const models = Array.isArray(src) ? src : (src && src.models ? src.models : []);
  const creators = [...new Set(models.map(m => m.creator).filter(Boolean))].sort();
  const isAllActive = !window.__legendFilter;
  el.innerHTML = '<span class="lg-fi' + (isAllActive ? ' active' : '') + '" data-lg-dim="" data-lg-val="">ALL</span>'
    + creators.map(c => {
        const active = window.__legendFilter && window.__legendFilter.dim === 'creator' && window.__legendFilter.val === c;
        const color = (window.CREATOR_COLORS || {})[c] || '#888';
        return `<span class="lg-fi${active ? ' active' : ''}" data-lg-dim="creator" data-lg-val="${c}"><span class="cr-fs" style="background:${color}"></span>${c}</span>`;
      }).join('');
  // Re-bind click — clone to drop old listeners
  const newEl = el.cloneNode(true);
  el.parentNode.replaceChild(newEl, el);
  window.__creatorLegendEl = newEl;
  newEl.addEventListener('click', e => {
    const item = e.target.closest('.lg-fi');
    if (!item) return;
    const dim = item.dataset.lgDim;
    if (!dim) { window.__clearLegendFilter(); return; }
    window.__setLegendFilter(dim, item.dataset.lgVal);
  });
};

window.CREATOR_COLORS = CREATOR_COLORS;
window.CREATOR_BORDER = CREATOR_BORDER;

// ============================================================
// Tooltip wiring — attach mousemove handlers to SVG elements
// ============================================================
function wireTooltips(container, data, selectors) {
  const tt = document.getElementById('tooltip');
  if (!tt) return;
  const modelBySlug = Object.fromEntries((data || []).map(m => [m.slug, m]));
  container.querySelectorAll(selectors).forEach(el => {
    el.addEventListener('mouseenter', function() {
      const m = modelBySlug[this.dataset.slug];
      if (!m) return;
      tt.innerHTML = window.buildTooltip ? window.buildTooltip(m) : m.name;
      tt.style.display = 'block';
    });
    el.addEventListener('mousemove', function(e) {
      const w = tt.offsetWidth, h = tt.offsetHeight;
      const vw = window.innerWidth, vh = window.innerHeight;
      let x = e.clientX + 16, y = e.clientY + 16;
      // Flip left if overflows right
      if (x + w > vw - 8) x = e.clientX - w - 16;
      // Flip up if overflows bottom
      if (y + h > vh - 8) y = e.clientY - h - 16;
      // Clamp top
      if (y < 8) y = 8;
      // Clamp left
      if (x < 8) x = 8;
      tt.style.left = x + 'px';
      tt.style.top  = y + 'px';
    });
    el.addEventListener('mouseleave', function() {
      tt.style.display = 'none';
    });
  });
}

// ============================================================
// Label placement — collision avoidance for bubble labels
// Returns { x, y, anchor }. Pass opts.W/H to clamp to viewBox.
// ============================================================
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

window.VIZ_HELPERS = { wireTooltips, placeLabel };

// ============================================================
// Shared config — single source of truth for labels and patterns
// ============================================================

// SKU split patterns: slug keyword → suffix label
// Use word boundary / dash separator to avoid false positives (e.g. "minimax" matching "mini")
window.SKU_PATTERNS = [
  { keyword: 'oss',     suffix: ' OSS',   pattern: '(^|-)oss(-|$)' },
  { keyword: 'mini',    suffix: ' Mini',  pattern: '(^|-)mini(-|$)' },
  { keyword: 'nano',    suffix: ' Nano',  pattern: '(^|-)nano(-|$)' },
  { keyword: 'flash',   suffix: ' Flash', pattern: '(^|-)flash(-|$)' },
  { keyword: 'codex',   suffix: ' Code',  pattern: '(^|-)codex(-|$)' },
  { keyword: '-code',   suffix: ' Code',  pattern: '-code$' },
];

// Radar axis definitions for provider archetypes
window.RADAR_AXES = [
  { key: 'avgIQ',       label: 'IQ',         angle: -Math.PI / 2 },
  { key: 'avgSpeed',    label: 'SPEED',      angle: -Math.PI / 2 + 2 * Math.PI / 5 },
  { key: 'tokenEff',    label: 'TOKEN EFF',  angle: -Math.PI / 2 + 4 * Math.PI / 5 },
  { key: 'avgCacheEff', label: 'CACHE EFF',  angle: -Math.PI / 2 + 6 * Math.PI / 5 },
  { key: 'costEff',     label: 'COST EFF',   angle: -Math.PI / 2 + 8 * Math.PI / 5 },
];

// Cost segment definitions for reasoning-tax viz
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

// Cache hit rates (observed from Dirac.run / OpenRouter)
// Keys are model slugs. Lookup tries both hyphen and dot variants.
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
