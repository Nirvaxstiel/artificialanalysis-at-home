// viz/_shared.js
// Shared helpers — color palette, tooltip wiring, label placement.
// Single source of truth; loaded before viz scripts.

(function() {

const CREATOR_COLORS = {
  "OpenAI":     "#f5f5f0",
  "Google":     "#4285F4",
  "Anthropic":  "#D97757",
  "DeepSeek":   "#536dfe",
  "MiniMax":    "#b6ff3c",
  "xAI":        "#9e9e9e",
  "NVIDIA":     "#76b900",
  "Kimi":       "#00e5ff",
  "Alibaba":    "#ff6a00",
  "Z AI":       "#a855f7",
  "Xiaomi":     "#ff5722",
  "Amazon":     "#ff9900",
  "Mistral":    "#000000",
  "Meta":       "#1877f2"
};
const CREATOR_BORDER = { "Mistral": "#f5f5f0" };

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
      const x = e.clientX + 16, y = e.clientY + 16;
      const w = tt.offsetWidth, h = tt.offsetHeight;
      tt.style.left = (x + w > window.innerWidth ? e.clientX - w - 16 : x) + 'px';
      tt.style.top  = (y + h > window.innerHeight ? e.clientY - h - 16 : y) + 'px';
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

})();
