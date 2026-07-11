// JS domain model — typed wrappers + helpers mirroring data/_domain.py
// Loads after processed.js, before viz scripts. Enables typed model access.

(function () {

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

class ProjectionRow {
  /** Wrap a raw model dict from PROCESSED_DATA into a typed domain object.
   *  Copies all raw properties so `row.intel`, `row.cost_per_task` work directly.
   *  Adds computed getters for derived concepts shared across viz scripts. */
  constructor(raw) {
    Object.assign(this, raw);
  }

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

  /** Load raw PROCESSED_DATA into typed MODELS. Returns Result<ProjectionRow[]>.
   *  On a missing/invalid payload, returns Err (data not loaded yet or wrong shape). */
  static load(raw) {
    if (Array.isArray(raw)) {
      return window.Result.ok(raw.map(r => new ProjectionRow(r)));
    }
    return window.Result.err('PROCESSED_DATA is not an array');
  }

  /** Enums exposed as static properties for convenience. */
  static get Archetype() { return Archetype; }
  static get ModelType() { return ModelType; }
  static get SourceKey() { return SourceKey; }
}

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

/** Normalize whatever PROCESSED_DATA holds into a Result<ProjectionRow[]>.
 *  Handles the { meta, models } payload shape (unwrap .models) and the raw array
 *  shape directly. Skips DOM — pure load boundary, testable in node. */
function loadModels(payload) {
  let raw = payload;
  if (!Array.isArray(raw)) {
    if (raw && Array.isArray(raw.models)) {
      raw = raw.models;
    } else {
      return window.Result.err('PROCESSED_DATA missing or wrong shape');
    }
  }
  return ProjectionRow.load(raw);
}

// Expose domain API on window

window.Archetype = Archetype;
window.ModelType = ModelType;
window.SourceKey = SourceKey;
window.ProjectionRow = ProjectionRow;
window.bucketByReasoning = bucketByReasoning;
window.reasoningColor = reasoningColor;
window.REASONING_COLORS = REASONING_COLORS;
window.loadProjectionModels = loadModels;

const _wrapped = loadModels(window.PROCESSED_DATA);
if (_wrapped.isOk()) {
  window.MODELS = _wrapped.unwrap();
}

})();
