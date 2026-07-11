// Black-box contract tests for the JS data layer (viz/_domain.js).
// Node-only, no jsdom, no DOM. Loads REAL data/processed.js as a payload and
// asserts the load boundary (loadProjectionModels) returns a well-formed
// Result<ProjectionRow[]> plus correct domain helpers. No impl spying.

const fs = require('fs');
const path = require('path');
const { ok, err, fromFn } = require('../viz/_result.js');

// Load the real generated artifact (it does `window.PROCESSED_DATA = [...]`).
// We shim `window` so requiring processed.js populates it, then pass the
// real payload into loadProjectionModels — pure input->output.
const REASONING_HIGH = '#ff3366';

const realProcessed = (function () {
  const win = {};
  const file = path.join(__dirname, '..', 'data', 'processed.js');
  const src = fs.readFileSync(file, 'utf8');
  // eslint-disable-next-line no-new-func
  const fn = new Function('window', src);
  fn(win);
  return win.PROCESSED_DATA;
})();

const domain = (function () {
  // _domain.js attaches everything to `window`; shim it with Result present.
  const win = {};
  win.Result = { ok, err, fromFn };
  const src = fs.readFileSync(path.join(__dirname, '..', 'viz', '_domain.js'), 'utf8');
  // eslint-disable-next-line no-new-func
  new Function('window', src)(win);
  return win;
})();

let pass = 0, fail = 0;
function check(name, cond) {
  if (cond) { pass++; } else { fail++; console.log('FAIL:', name); }
}

// ── Load boundary: real payload → Ok with typed rows ──
const r = domain.loadProjectionModels(realProcessed);
check('real payload is Ok', r.isOk());
check('real payload unwraps to array', Array.isArray(r.unwrap()) && r.unwrap().length > 0);
const models = r.unwrap();
check('rows are ProjectionRow instances', models.every(m => m instanceof domain.ProjectionRow));
check('first row has raw props copied', models[0].hasOwnProperty('slug') || models[0].hasOwnProperty('intel'));

// ── raw array shape → Ok ──
const arr = [{ slug: 'x', intel: 50 }, { slug: 'y', intel: 60 }];
const rArr = domain.loadProjectionModels(arr);
check('raw array is Ok', rArr.isOk() && rArr.unwrap().length === 2);
check('raw array rows typed', rArr.unwrap()[0] instanceof domain.ProjectionRow);

// ── { meta, models } shape → unwrap .models → Ok ──
const wrapped = { meta: { n: 1 }, models: [{ slug: 'z', intel: 70 }] };
const rWrap = domain.loadProjectionModels(wrapped);
check('{meta,models} unwrapped to Ok', rWrap.isOk() && rWrap.unwrap()[0].slug === 'z');

// ── bad payload → Err ──
check('null payload is Err', domain.loadProjectionModels(null).isErr());
check('non-array non-object is Err', domain.loadProjectionModels(42).isErr());
check('object without .models is Err', domain.loadProjectionModels({ foo: 1 }).isErr());

// ── computed getters ──
const sample = domain.loadProjectionModels([
  { slug: 'a', intel: 100, cost_per_task: 2.5, type: 'reasoning', reasoning_tax_pct: 30,
    pareto_optimal: true, has_breakdown: false, context_window: 200000, creator: 'X' }
]).unwrap()[0];
check('hasIntel', sample.hasIntel === true);
check('hasCost', sample.hasCost === true);
check('isReasoning', sample.isReasoning === true);
check('isParetoOptimal', sample.isParetoOptimal === true);
check('hasBreakdown false', sample.hasBreakdown === false);
check('hasContext', sample.hasContext === true);
check('reasoningBucket mid (30%)', sample.reasoningBucket === 'mid');
check('reasoningColor resolves', typeof sample.reasoningColor === 'string' && sample.reasoningColor.length > 0);

// ── pure helpers (no DOM, fallible-free) ──
check('bucketByReasoning null→none', domain.bucketByReasoning(null) === 'none');
check('bucketByReasoning 10→low', domain.bucketByReasoning(10) === 'low');
check('bucketByReasoning 50→mid', domain.bucketByReasoning(50) === 'mid');
check('bucketByReasoning 80→high', domain.bucketByReasoning(80) === 'high');
check('reasoningColor red for high', domain.reasoningColor(80) === REASONING_HIGH);

// ── paretoFrontier ──
const frontier = domain.ProjectionRow.paretoFrontier(
  [
    { cost: 1, intel: 10 },
    { cost: 2, intel: 5 },
    { cost: 3, intel: 20 },
  ],
  'cost', 'intel'
);
check('paretoFrontier count', frontier.length === 2);
check('paretoFrontier picks best intel per cost', frontier[0].intel === 10 && frontier[1].intel === 20);

// ── enums exposed ──
check('Archetype.FRONTIER', domain.Archetype.FRONTIER === 'frontier');
check('ModelType.REASONING', domain.ModelType.REASONING === 'reasoning');
check('SourceKey.AA', domain.SourceKey.AA === 'aa');

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
