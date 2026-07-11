// Black-box contract tests for viz/data-table.js pure transforms.
// Node-only, no jsdom, no DOM. Loads the real file (shimmed window), asserts
// buildRows / applySort / matchesSearch input->output contracts. No impl spying.

const fs = require('fs');
const path = require('path');

function loadViz(file) {
  const win = { VIZ_DEFAULTS: { dataTable: { view: 'model', sort: { key: 'intel', dir: 'desc' } } } };
  const src = fs.readFileSync(path.join(__dirname, '..', 'viz', file), 'utf8');
  // eslint-disable-next-line no-new-func
  new Function('window', src)(win);
  return win;
}

const { DATA_TABLE } = loadViz('data-table.js');
const { VIEWS, applySort, matchesSearch } = DATA_TABLE;

let pass = 0, fail = 0;
function check(name, cond) {
  if (cond) { pass++; } else { fail++; console.log('FAIL:', name); }
}

// ── buildRows: each view derives its row shape from raw models ──
const models = [
  { creator: 'OpenAI', name: 'gpt-x', slug: 'gpt-x', intel: 100, cost_per_task: 2,
    tokens_m: 1, speed_tps: 50, out_price: 10, reasoning_tax_pct: 30,
    livebench_average: 90, arena_code_elo: 1400, openrouter_inp_price_per_m: 5,
    params_b: 0.2, type: 'chat', livebench_coding: 88, livebench_reasoning: 91 },
  { creator: 'Anthropic', name: 'claude-y', slug: 'claude-y', intel: 95, cost_per_task: 3,
    tokens_m: 2, speed_tps: 40, out_price: 12, reasoning_tax_pct: 10,
    livebench_average: 85, arena_code_elo: 1350, openrouter_inp_price_per_m: 6,
    params_b: 0.4, type: 'reasoning', livebench_coding: 84, livebench_reasoning: 87 },
];

const providerRows = VIEWS.provider.buildRows(models);
check('provider rollup row per creator', providerRows.length === 2);
check('provider rollup aggregates count', providerRows.every(r => r.count === 1));
check('provider rollup avgIQ averaged', Math.abs(providerRows[0].avgIQ - 100) < 1e-9);

const modelRows = VIEWS.model.buildRows(models);
check('model view passes through', modelRows.length === 2 && modelRows[0].slug === 'gpt-x');

const lbRows = VIEWS.livebench.buildRows(models);
check('livebench view passes through', lbRows.length === 2);

const effRows = VIEWS.efficiency.buildRows(models);
check('efficiency view passes through', effRows.length === 2);

// ── applySort: desc/asc + null handling + multi-column ──
const unsorted = [
  { intel: 10, cost_per_task: 1 },
  { intel: 30, cost_per_task: 5 },
  { intel: 20, cost_per_task: 3 },
];
const desc = applySort(unsorted, [{ key: 'intel', dir: 'desc' }]);
check('applySort desc', desc[0].intel === 30 && desc[2].intel === 10);

const asc = applySort(unsorted, [{ key: 'intel', dir: 'asc' }]);
check('applySort asc', asc[0].intel === 10 && asc[2].intel === 30);

const withNulls = [
  { intel: 50, cost_per_task: 1 },
  { intel: null, cost_per_task: 2 },
  { intel: 20, cost_per_task: 3 },
];
const nullLastDesc = applySort(withNulls, [{ key: 'intel', dir: 'desc' }]);
check('applySort desc puts null first', nullLastDesc[0].intel === null);

const nullFirstAsc = applySort(withNulls, [{ key: 'intel', dir: 'asc' }]);
check('applySort asc puts null last', nullFirstAsc[2].intel === null);

// iqPerK special key derives intel/cost ratio; null intel sorts first in desc
const byIqPerK = applySort(
  [
    { intel: 100, cost_per_task: 50 },  // 2000
    { intel: 100, cost_per_task: 10 },  // 10000
    { intel: null, cost_per_task: 1 },
  ],
  [{ key: 'iqPerK', dir: 'desc' }]
);
check('applySort iqPerK derived order', byIqPerK[1].intel === 100 && byIqPerK[1].cost_per_task === 10 && byIqPerK[2].intel === 100 && byIqPerK[2].cost_per_task === 50);

// multi-column: sort by cost asc, then intel desc
const multi = applySort(
  [
    { cost_per_task: 1, intel: 10 },
    { cost_per_task: 1, intel: 30 },
    { cost_per_task: 2, intel: 5 },
  ],
  [{ key: 'cost_per_task', dir: 'asc' }, { key: 'intel', dir: 'desc' }]
);
check('applySort multi-column', multi[0].intel === 30 && multi[1].intel === 10 && multi[2].intel === 5);

// ── matchesSearch: name / creator / slug, case-insensitive ──
const m = { name: 'GPT-Four', creator: 'OpenAI', slug: 'gpt-4' };
check('matchesSearch name', matchesSearch(m, 'gpt'));
check('matchesSearch creator', matchesSearch(m, 'open'));
check('matchesSearch slug', matchesSearch(m, '4'));
check('matchesSearch case-insensitive', matchesSearch(m, 'OPENAI'));
check('matchesSearch empty matches all', matchesSearch(m, ''));
check('matchesSearch miss', !matchesSearch(m, 'claude'));

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
