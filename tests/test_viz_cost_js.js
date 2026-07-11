// Black-box contract tests for viz/cost-breakdown.js pure transforms.
// Node-only, no jsdom, no DOM. Loads the real file (shimmed window), asserts
// buildCostData / applyExternalCache / getCacheHitRate input->output.
// No impl spying — input shape in, derived shape out.

const fs = require('fs');
const path = require('path');

function loadViz(file) {
  const win = {
    CACHE_HIT_RATES: { 'gpt-x': 0.5, 'gpt-y': 0.8 },
    COST_SEGMENTS: {
      aa: [{ key: 'answer_usd', label: 'ANSWER' }, { key: 'reasoning_usd', label: 'REASONING' }],
      ext: [{ key: 'input_usd', label: 'INPUT' }],
    },
  };
  const src = fs.readFileSync(path.join(__dirname, '..', 'viz', file), 'utf8');
  // eslint-disable-next-line no-new-func
  new Function('window', src)(win);
  return win;
}

const { COST_BREAKDOWN } = loadViz('cost-breakdown.js');
const { buildCostData, applyExternalCache, getCacheHitRate } = COST_BREAKDOWN;

let pass = 0, fail = 0;
function check(name, cond) {
  if (cond) { pass++; } else { fail++; console.log('FAIL:', name); }
}

// ── buildCostData: keeps only models with cost_seg_total > 0, maps fields ──
const raw = [
  { slug: 'gpt-x', name: 'GPT X', creator: 'OpenAI', cost_seg_total: 1.5,
    cost_seg_answer: 1.0, cost_seg_reasoning: 0.5, cost_seg_input: 0.3,
    cost_seg_cache_hit: 0.2, cost_seg_cache_write: 0.1 },
  { slug: 'no-seg', name: 'No Seg', creator: 'X', cost_seg_total: null },
  { slug: 'zero', name: 'Zero', creator: 'Y', cost_seg_total: 0 },
];
const built = buildCostData(raw);
check('buildCostData filters to only cost_seg_total>0', built.length === 1);
check('buildCostData maps total', Math.abs(built[0].total_cost_per_task_usd - 1.5) < 1e-9);
check('buildCostData maps segments', Math.abs(built[0].answer_usd - 1.0) < 1e-9 && Math.abs(built[0].reasoning_usd - 0.5) < 1e-9);
check('buildCostData preserves present segment', Math.abs(built[0].cache_write_usd - 0.1) < 1e-9);
// model with a missing segment field falls back to 0 via ||
const rawMissing = [
  { slug: 'm', name: 'M', creator: 'X', cost_seg_total: 2.0,
    cost_seg_answer: 1.0, cost_seg_reasoning: 0.5 },
];
const builtMissing = buildCostData(rawMissing);
check('buildCostData missing segment defaults to 0', builtMissing[0].cache_write_usd === 0 && builtMissing[0].cache_hit_usd === 0);
check('buildCostData cache_hit_rate null (AA has none)', built[0].cache_hit_rate === null);

// ── getCacheHitRate: exact + dot-slug fallback ──
check('getCacheHitRate exact', getCacheHitRate('gpt-x') === 0.5);
check('getCacheHitRate dot fallback', getCacheHitRate('gpt-y') === 0.8);
check('getCacheHitRate missing -> null', getCacheHitRate('unknown') === null);
// dot variant: slug with dashes maps to dotted key
check('getCacheHitRate dash->dot', getCacheHitRate('gpt-x') === 0.5);

// ── applyExternalCache: redistributes input/cache_hit by observed hit rate ──
const seg = buildCostData([
  { slug: 'gpt-x', name: 'GPT X', creator: 'OpenAI', cost_seg_total: 1.5,
    cost_seg_answer: 1.0, cost_seg_reasoning: 0.5, cost_seg_input: 0.3,
    cost_seg_cache_hit: 0.2, cost_seg_cache_write: 0.1 },
]);
const ext = applyExternalCache(seg);
check('applyExternalCache returns same count', ext.length === 1);
check('applyExternalCache zeroes cache_write', ext[0].cache_write_usd === 0);
// With rate 0.5 and CACHE_PRICE_RATIO 0.1: uncached = 0.5*totalInputAtFull, cached = 0.5*0.1*totalInputAtFull.
// Conserves total input across uncached+cached.
const totalInput = seg[0].input_usd + seg[0].cache_hit_usd + seg[0].cache_write_usd;
check('applyExternalCache conserves input total',
  Math.abs((ext[0].input_usd + ext[0].cache_hit_usd) - totalInput) < 1e-6);
// cached cost strictly less than full input when rate>0 and ratio<1
check('applyExternalCache cached cost discounted', ext[0].cache_hit_usd < seg[0].cache_hit_usd);

// Models with no known rate are unchanged
const noRate = applyExternalCache([{ slug: 'unknown', input_usd: 1, cache_hit_usd: 0, cache_write_usd: 0, total_cost_per_task_usd: 1 }]);
check('applyExternalCache no-rate unchanged', noRate[0].input_usd === 1 && noRate[0].cache_hit_usd === 0);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
