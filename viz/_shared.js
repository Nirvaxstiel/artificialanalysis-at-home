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
