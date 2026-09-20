// Black-box contract tests for viz/cost-breakdown.js pure transforms.
// Node-only, no jsdom, no DOM. Loads the real file (shimmed window), asserts
// buildCostData / providerOptions / providerView / axisFor input->output.
// No impl spying — input shape in, derived shape out.

const fs = require('fs');
const path = require('path');

function loadViz(file) {
  const win = {
    COST_SEGMENTS: {
      aa: [
        { key: 'input_usd', label: 'INPUT' },
        { key: 'cache_hit_usd', label: 'CACHED INPUT' },
        { key: 'cache_write_usd', label: 'CACHE WRITE' },
        { key: 'answer_usd', label: 'ANSWER' },
        { key: 'reasoning_usd', label: 'REASONING' },
      ],
    },
  };
  const src = fs.readFileSync(path.join(__dirname, '..', 'viz', file), 'utf8');
  // eslint-disable-next-line no-new-func
  new Function('window', src)(win);
  return win;
}

const { COST_BREAKDOWN } = loadViz('cost-breakdown.js');
const { buildCostData, providerOptions, providerView, providerTaskRow, axisFor } = COST_BREAKDOWN;

let pass = 0, fail = 0;
function check(name, cond) {
  if (cond) { pass++; } else { fail++; console.log('FAIL:', name); }
}
const near = (a, b) => Math.abs(a - b) < 1e-9;

const raw = [
  { slug: 'gpt-x', name: 'GPT X', creator: 'OpenAI', cost_seg_total: 1.5,
    cost_seg_answer: 1.0, cost_seg_reasoning: 0.5, cost_seg_input: 0.3,
    cost_seg_cache_hit: 0.2, cost_seg_cache_write: 0.1,
    inp_price: 5, out_price: 10,
    dirac_cache_hit_rates: [
      { provider: 'DeepInfra', cache_hit_rate: 80, eff_input_price: 2.5, eff_output_price: 5 },
      { provider: 'Together', cache_hit_rate: 50, eff_input_price: 6, eff_output_price: 12 },
    ] },
  { slug: 'no-seg', name: 'No Seg', creator: 'X', cost_seg_total: null,
    inp_price: 1, out_price: 2,
    dirac_cache_hit_rates: [{ provider: 'DeepInfra', cache_hit_rate: 60, eff_input_price: 0.5, eff_output_price: 1.5 }] },
  { slug: 'zero', name: 'Zero', creator: 'Y', cost_seg_total: 0 },
  { slug: 'unpriced', name: 'Unpriced', creator: 'Z', cost_seg_total: null,
    dirac_cache_hit_rates: [{ provider: 'DeepInfra', cache_hit_rate: 40, eff_input_price: null, eff_output_price: null }] },
];

// ── buildCostData: only rows with cost_seg_total > 0, missing segments default 0 ──
const built = buildCostData(raw);
check('buildCostData keeps only cost_seg_total>0', built.length === 1);
check('buildCostData maps total', near(built[0].total_cost_per_task_usd, 1.5));
check('buildCostData maps every segment', near(built[0].input_usd, 0.3) && near(built[0].cache_hit_usd, 0.2) &&
  near(built[0].cache_write_usd, 0.1) && near(built[0].answer_usd, 1.0) && near(built[0].reasoning_usd, 0.5));
check('buildCostData defaults absent segments to 0',
  buildCostData([{ slug: 'm', name: 'M', creator: 'X', cost_seg_total: 2, cost_seg_answer: 2 }])[0].cache_write_usd === 0);

// ── providerOptions: providers with usable eff rates, ordered by coverage ──
const opts = providerOptions(raw);
check('providerOptions orders providers by coverage', opts.length === 2 && opts[0].name === 'DeepInfra' && opts[1].name === 'Together');
check('providerOptions counts entries with eff rates', opts[0].count === 2 && opts[1].count === 1);
check('providerOptions ignores entries without eff rates', opts.every(o => o.name !== 'unpriced'));

// ── providerTaskRow: reprices AA segments by provider eff rate / AA list rate ──
const task = providerTaskRow(built[0], raw[0], raw[0].dirac_cache_hit_rates[0]);
check('providerTaskRow input ratio', near(task.rIn, 0.5));
check('providerTaskRow output ratio', near(task.rOut, 0.5));
check('providerTaskRow scales input side only', near(task.input_usd, 0.15) && near(task.cache_hit_usd, 0.1) &&
  near(task.cache_write_usd, 0.05));
check('providerTaskRow scales output side only', near(task.answer_usd, 0.5) && near(task.reasoning_usd, 0.25));
check('providerTaskRow total is the scaled sum', near(task.total_cost_per_task_usd, 1.05));
check('providerTaskRow carries observed hit rate', task.hit_rate === 80);
check('providerTaskRow refuses a model with no list price',
  providerTaskRow(built[0], { inp_price: 0, out_price: 0 }, raw[0].dirac_cache_hit_rates[0]) === null);
check('providerTaskRow refuses an entry with no eff rates',
  providerTaskRow(built[0], raw[0], { eff_input_price: null, eff_output_price: 2 }) === null);

// ── providerView: models with AA per-task cost → taskRows, rest → rateRows ──
const view = providerView(raw, 'DeepInfra');
check('providerView routes segment models to taskRows', view.taskRows.length === 1 && view.taskRows[0].slug === 'gpt-x');
check('providerView routes segment-less models to rateRows', view.rateRows.length === 1 && view.rateRows[0].slug === 'no-seg');
check('providerView excludes models the provider does not serve', !view.taskRows.concat(view.rateRows).some(r => r.slug === 'zero'));
check('providerView drops entries without eff rates', !view.rateRows.some(r => r.slug === 'unpriced'));
check('rate row total is 1M input + 1M output at eff rates', near(view.rateRows[0].total_cost_per_task_usd, 2));
check('providerView for another provider is empty on segments',
  providerView(raw, 'Together').taskRows.length === 1 && providerView(raw, 'Together').rateRows.length === 0);
check('providerView for an unknown provider is empty',
  providerView(raw, 'Nope').taskRows.length === 0 && providerView(raw, 'Nope').rateRows.length === 0);

// ── axisFor: log ticks bracketing the data ──
const ticks = axisFor([0.04, 1.2, 0.6]);
check('axisFor brackets max', ticks[ticks.length - 1] >= 1.2);
check('axisFor brackets min', ticks[0] <= 0.04);
check('axisFor ticks ascend', ticks.every((t, i) => i === 0 || t > ticks[i - 1]));
check('axisFor falls back to AA ticks with no positive values', axisFor([0, null]).length > 0);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);