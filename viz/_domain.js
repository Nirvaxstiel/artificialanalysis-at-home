// JS domain model — typed wrappers + helpers mirroring data/_domain.py
// Loads after processed.js, before viz scripts. Enables typed model access.

(function() {

// ═══════════════════════════════════════════════════
// Enums
// ═══════════════════════════════════════════════════

const Archetype = Object.freeze({
  FRONTIER: 'frontier',
  CHEAP: 'cheap',
  REASONING: 'reasoning',
  FAST: 'fast',
  COMPACT: 'compact',
  UNCATEGORIZED: 'uncategorized',
});

const ModelType = Object.freeze({
  CHAT: 'chat',
  REASONING: 'reasoning',
});

const SourceKey = Object.freeze({
  AA: 'aa',
  LIVEBENCH: 'livebench',
  ARENA_CODE: 'arena_code',
  ARENA_TEXT: 'arena_text',
  OPENLLM: 'openllm',
  OPENROUTER: 'openrouter',
});

// ═══════════════════════════════════════════════════
// Model wrapper
// ═══════════════════════════════════════════════════

class ProjectionRow {
  /** Wrap a raw model dict from PROCESSED_DATA into a typed domain object.
   *  Copies all raw properties so `row.intel`, `row.cost_per_task` work directly.
   *  Adds computed getters for derived concepts shared across viz scripts. */
  constructor(raw) {
    Object.assign(this, raw);
  }

  // ── Computed getters ──

  /** 'none' | 'low' | 'mid' | 'high' — reasoning tax tier. */
  get reasoningBucket() {
    return bucketByReasoning(this.reasoning_tax_pct);
  }

  /** CSS color string for reasoning bucket. */
  get reasoningColor() {
    return reasoningColorByBucket(this.reasoningBucket);
  }

  /** Convenience booleans. */
  get hasIntel() { return this.intel != null; }
  get hasCost() { return this.cost_per_task != null && this.cost_per_task > 0; }
  get isReasoning() { return this.type === ModelType.REASONING; }
  get isParetoOptimal() { return this.pareto_optimal === true; }
  get hasBreakdown() { return this.has_breakdown === true; }
  get contextWindow() { return this.context_window; }
  get hasContext() { return this.context_window != null; }

  // ── Static helpers ──

  /** Compute pareto frontier over a sorted cost → quality space.
   *  Returns filtered array (frontier models). Mutates by setting `pareto_optimal`. */
  static paretoFrontier(models, costKey, qualityKey) {
    const sorted = models
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

  /** Wrap raw PROCESSED_DATA array. Returns MODELS array. */
  static load(raw) {
    return Array.isArray(raw) ? raw.map(r => new ProjectionRow(r)) : [];
  }

  /** Enums exposed as static properties for convenience. */
  static get Archetype() { return Archetype; }
  static get ModelType() { return ModelType; }
  static get SourceKey() { return SourceKey; }
}

// ═══════════════════════════════════════════════════
// Standalone helpers (usable from viz scripts)
// ═══════════════════════════════════════════════════

const REASONING_COLORS = {
  none:  '#888888',
  low:   '#b6ff3c',
  mid:   '#ff6a00',
  high:  '#ff3366',
};

function bucketByReasoning(pct) {
  if (pct == null) return 'none';
  if (pct < 20) return 'low';
  if (pct <= 50) return 'mid';
  return 'high';
}

function reasoningColorByBucket(bucket) {
  return REASONING_COLORS[bucket] || REASONING_COLORS.none;
}

/** Map reasoning tax % → CSS color. */
function reasoningColor(pct) {
  return reasoningColorByBucket(bucketByReasoning(pct));
}

// ═══════════════════════════════════════════════════
// Auto-wrap on load
// ═══════════════════════════════════════════════════

(function wrapData() {
  if (!Array.isArray(window.PROCESSED_DATA)) {
    if (window.PROCESSED_DATA && Array.isArray(window.PROCESSED_DATA.models)) {
      // Handle { meta, models } payload shape
      window.PROCESSED_DATA = window.PROCESSED_DATA.models;
    } else {
      return; // data not loaded yet, _boot.js retries
    }
  }
  window.MODELS = ProjectionRow.load(window.PROCESSED_DATA);
})();

// ── Export to window ──

window.Archetype = Archetype;
window.ModelType = ModelType;
window.SourceKey = SourceKey;
window.ProjectionRow = ProjectionRow;
window.bucketByReasoning = bucketByReasoning;
window.reasoningColor = reasoningColor;
window.REASONING_COLORS = REASONING_COLORS;

})();
