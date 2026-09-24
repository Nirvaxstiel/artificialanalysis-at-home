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
    speed_tps: 50, out_price: 10, reasoning_tax_pct: 30,
    aa_finance_accounting_index: 61.4, aa_analyst_agent_pass_5: 0.575,
    aa_briefcase_elo: 1400, aa_gdpval_elo: 1350, aa_omniscience_index: -5,
    aa_time_per_task: 35.5, livebench_average: 90, arena_code_elo: 1400,
    openrouter_inp_price_per_m: 5, params_b: 0.2, type: 'chat',
    livebench_coding: 88, livebench_reasoning: 91, provenance: { intel: 'sourced' } },
  { creator: 'Anthropic', name: 'claude-y', slug: 'claude-y', intel: 95, cost_per_task: 3,
    speed_tps: 40, out_price: 12, reasoning_tax_pct: 10,
    aa_finance_accounting_index: 58.2, aa_analyst_agent_pass_5: 0.5,
    aa_briefcase_elo: 1350, aa_gdpval_elo: 1400, aa_omniscience_index: 2,
    aa_time_per_task: 42, livebench_average: 85, arena_code_elo: 1350,
    openrouter_inp_price_per_m: 6, params_b: 0.4, type: 'reasoning',
    livebench_coding: 84, livebench_reasoning: 87, provenance: { intel: 'sourced' } },
];

const providerRows = VIEWS.provider.buildRows(models);
check('provider rollup row per creator', providerRows.length === 2);
check('provider rollup aggregates count', providerRows.every(r => r.count === 1));
check('provider rollup avgIQ averaged', Math.abs(providerRows[0].avgIQ - 100) < 1e-9);

const modelRows = VIEWS.model.buildRows(models);
check('model view passes through', modelRows.length === 2 && modelRows[0].slug === 'gpt-x');

const lbRows = VIEWS.livebench.buildRows(models);
check('livebench view passes through', lbRows.length === 2);

const aaRows = VIEWS.aaIndexes.buildRows(models);
check('AA indexes view passes through current export metrics',
  aaRows.length === 2 && aaRows[0].aa_finance_accounting_index === 61.4
  && aaRows[0].aa_analyst_agent_pass_5 === 0.575);

const effRows = VIEWS.efficiency.buildRows(models);
check('efficiency view derives cost per IQ point from source inputs',
  Math.abs(effRows[0].cost_per_iq - 0.02) < 1e-12);
check('efficiency view marks derived field provenance', effRows[0].provenance.cost_per_iq === 'derived');

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

const byCostPerIq = applySort(
  [
    { cost_per_iq: 0.5 },
    { cost_per_iq: 0.02 },
    { cost_per_iq: null },
  ],
  [{ key: 'cost_per_iq', dir: 'asc' }]
);
check('applySort derived cost-per-IQ asc with nulls last',
  byCostPerIq[0].cost_per_iq === 0.02
  && byCostPerIq[1].cost_per_iq === 0.5
  && byCostPerIq[2].cost_per_iq === null);

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
const F = ['name', 'creator', 'slug'];
check('matchesSearch name', matchesSearch(m, 'gpt', F));
check('matchesSearch creator', matchesSearch(m, 'open', F));
check('matchesSearch slug', matchesSearch(m, '4', F));
check('matchesSearch case-insensitive', matchesSearch(m, 'OPENAI', F));
check('matchesSearch empty matches all', matchesSearch(m, '', F));
check('matchesSearch miss', !matchesSearch(m, 'claude', F));

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
