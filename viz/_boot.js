// Tab navigation, lazy render, banner stats, legend wiring.
// Boot orchestrated via the shared Pipeline().then().run() idiom (mirrors
// data/_pipeline.Pipeline) so the flow is unambiguous: load models -> build
// shell -> render first viz -> wire interactive concerns. render() internals
// in each viz file are untouched.

(function () {

const { ok, err } = window.Result;

function bootstrapModels(ctx) {
  const loaded = window.loadProjectionModels(window.PROCESSED_DATA);
  if (loaded.isErr()) {
    return err(`model load failed: ${loaded.error}`);
  }
  ctx.models = loaded.unwrap();
  ctx.registry = window.VIZ_REGISTRY.slice();
  return ok(ctx);
}

function injectHeaderMeta(ctx) {
  const metaEl = document.getElementById('header-meta');
  if (metaEl) {
    const creators = new Set(ctx.models.map(m => m.creator).filter(Boolean));
    metaEl.textContent += ` · ${ctx.models.length} MODELS · ${creators.size} CREATORS`;
  }
  return ok(ctx);
}

function buildShell(ctx) {
  const tabsEl = document.getElementById('tabs');
  tabsEl.innerHTML = ctx.registry.map((v, i) => `
    <button data-viz="${v.id}" class="${i === 0 ? 'active' : ''}">
      <span class="num">${i + 1}</span> ${v.name}
      <span class="sub">${v.subtitle}</span>
    </button>
  `).join('');

  const panelsEl = document.getElementById('panels');
  panelsEl.innerHTML = ctx.registry.map((v, i) => `
    <div class="viz-panel ${i === 0 ? 'active' : ''}" data-viz="${v.id}">
      <div class="chart">
        <div class="chart-head">
          <h2>${i + 1} <span class="cmt">//</span> ${v.name}</h2>
          <span class="src"><span class="cmt">//</span> ${v.subtitle}</span>
        </div>
        <div class="viz-mount" id="mount-${v.id}"></div>
        <div class="viz-legend"></div>
      </div>
    </div>
  `).join('');
  return ok(ctx);
}

function renderFirst(ctx) {
  const v = ctx.registry[0];
  if (!v) return ok(ctx);
  const mount = document.getElementById(`mount-${v.id}`);
  v.render(mount, ctx.models);
  return ok(ctx);
}

function wireTabs(ctx) {
  const tabsEl = document.getElementById('tabs');
  const rendered = new Set([ctx.registry[0].id]);
  tabsEl.addEventListener('click', e => {
    const btn = e.target.closest('button[data-viz]');
    if (!btn) return;
    const id = btn.dataset.viz;
    document.querySelectorAll('nav.tabs button').forEach(b => b.classList.toggle('active', b.dataset.viz === id));
    document.querySelectorAll('.viz-panel').forEach(p => p.classList.toggle('active', p.dataset.viz === id));
    if (!rendered.has(id)) {
      const v = ctx.registry.find(r => r.id === id);
      if (v) { v.render(document.getElementById(`mount-${id}`), ctx.models); rendered.add(id); }
    }
    window.__renderCreatorLegend();
  });
  return ok(ctx);
}

function wireFilterSync(ctx) {
  window.__filterSubscribers.add(function onFilter() {
    const btn = document.querySelector('nav.tabs button.active');
    if (!btn) return;
    const id = btn.dataset.viz;
    const v = ctx.registry.find(r => r.id === id);
    if (!v) return;
    v.render(document.getElementById(`mount-${id}`), ctx.models);
  });
  return ok(ctx);
}

function renderBannerStats(ctx) {
  const data = ctx.models;
  const byIntel = [...data].filter(m => m.intel != null).sort((a, b) => b.intel - a.intel);
  const byCost = [...data].filter(m => m.cost_per_task != null).sort((a, b) => a.cost_per_task - b.cost_per_task);
  const byValue = [...data]
    .filter(m => m.intel != null && m.cost_per_task != null && m.cost_per_task > 0)
    .sort((a, b) => (b.intel / b.cost_per_task) - (a.intel / a.cost_per_task));
  const champ = byIntel[0], cheapest = byCost[0], bestValue = byValue[0];

  function setStat(sel, model, slug, view, sortKey, sortDir) {
    const el = document.querySelector(sel);
    if (!el) return;
    const valEl = el.querySelector('.val');
    if (valEl) valEl.innerHTML = model.creator.split('/')[0] + ' <span>' + model.slug + '</span>';
    el.dataset.slug = slug;
    el.dataset.view = view;
    el.dataset.sortKey = sortKey;
    el.dataset.sortDir = sortDir;
  }
  setStat('[data-metric="champion"]', champ, champ.slug, 'model', 'intel', 'desc');
  setStat('[data-metric="cheapest"]', cheapest, cheapest.slug, 'model', 'cost_per_task', 'asc');
  setStat('[data-metric="value"]', bestValue, bestValue.slug, 'model', 'iqPerK', 'desc');
  return ok(ctx);
}

function renderParetoCount(ctx) {
  const data = ctx.models;
  let count = 0;
  let maxQ = -Infinity;
  const sorted = [...data].filter(m => m.hasCost && m.hasIntel)
    .sort((a, b) => a.cost_per_task - b.cost_per_task);
  for (const m of sorted) {
    if (m.intel > maxQ) { count++; maxQ = m.intel + 1e-9; }
  }
  document.getElementById('pareto-count').textContent = count;
  document.getElementById('total-count').textContent = data.length;
  return ok(ctx);
}

function wireBannerNavigation(ctx) {
  const data = ctx.models;
  const registry = ctx.registry;
  const dtId = registry.find(r => r.name === 'Data Tables')?.id || 'data-table';
  window.navigateTable = function (view, sortKey, sortDir, highlight) {
    const mount = document.getElementById(`mount-${dtId}`);
    if (!mount) return;
    mount.__view = view;
    mount.__sort = [{ key: sortKey, dir: sortDir }];
    mount.__highlight = highlight;
    const btn = document.querySelector(`nav.tabs button[data-viz="${dtId}"]`);
    if (btn) btn.click();
    const v = registry.find(r => r.id === dtId);
    if (v) v.render(mount, data);
    requestAnimationFrame(() => {
      const row = mount.querySelector('tr.hl');
      if (row) {
        row.scrollIntoView({ behavior: 'smooth', block: 'center' });
      } else {
        const panel = mount.closest('.viz-panel');
        if (panel) panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  };

  document.querySelectorAll('.strip > div[data-metric]').forEach(el => {
    el.addEventListener('click', () => {
      const { slug, view, sortKey, sortDir } = el.dataset;
      if (slug) window.navigateTable(view || 'model', sortKey || 'intel', sortDir || 'desc', slug);
    });
  });
  return ok(ctx);
}

function renderRepoLinks(ctx) {
  const repoEl = document.getElementById('repo-links');
  if (repoEl) {
    const gh = 'Nirvaxstiel/artificialanalysis-at-home';
    const cb = 'Nirvaxstiel/artificialanalysis-at-home';
    const ghIcon = '<svg class="repo-icon" viewBox="0 0 16 16" width="13" height="13" fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>';
    const cbIcon = '<svg class="repo-icon" viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M11.99 0C5.37 0 0 5.37 0 12s5.37 12 11.99 12C18.63 24 24 18.63 24 12S18.63 0 11.99 0zm-2.3 5.5l8.85 5.42-8.85 5.42V5.5z"/></svg>';
    repoEl.innerHTML = `<a href="https://github.com/${gh}" target="_blank">${ghIcon} <span class="cmt">//</span> github</a> <a href="https://codeberg.org/${cb}" target="_blank">${cbIcon} <span class="cmt">//</span> codeberg</a>`;
  }
  return ok(ctx);
}

function validateSchema(ctx) {
  const REQUIRED_KEYS = ['slug', 'name', 'creator', 'intel', 'cost_per_task', 'speed_tps', 'context_window'];
  const models = ctx.models;
  if (!Array.isArray(models) || models.length === 0) {
    return err('schema: PROCESSED_DATA has no models');
  }
  const first = models[0];
  const missing = REQUIRED_KEYS.filter(k => !(k in first));
  if (missing.length) {
    return err(`schema: missing required fields [${missing.join(', ')}] — ProjectionRow contract drifted from the Python build`);
  }
  const badTypes = models.filter(m =>
    (m.slug != null && typeof m.slug !== 'string') ||
    (m.intel != null && typeof m.intel !== 'number') ||
    (m.cost_per_task != null && typeof m.cost_per_task !== 'number')
  );
  if (badTypes.length) {
    return err(`schema: ${badTypes.length} model(s) have wrong types for slug/intel/cost_per_task`);
  }
  return ok(ctx);
}

function showSchemaError(message) {
  const el = document.getElementById('schema-error');
  if (el) {
    el.textContent = message;
    el.style.display = 'block';
  }
}

function boot() {
  if (!window.PROCESSED_DATA || !window.VIZ_REGISTRY) {
    return setTimeout(boot, 50);
  }
  const pipeline = window.Result.Pipeline({})
    .then('bootstrap_models', bootstrapModels)
    .then('validate_schema', validateSchema)
    .then('header_meta', injectHeaderMeta)
    .then('build_shell', buildShell)
    .then('render_first', renderFirst)
    .then('wire_tabs', wireTabs)
    .then('wire_filter_sync', wireFilterSync)
    .then('banner_stats', renderBannerStats)
    .then('pareto_count', renderParetoCount)
    .then('banner_nav', wireBannerNavigation)
    .then('repo_links', renderRepoLinks);
  pipeline.run();
  if (pipeline.ctx._failed_step) {
    console.error(`Viz boot failed at '${pipeline.ctx._failed_step}': ${pipeline.ctx._error}`);
    showSchemaError(`Boot stopped at '${pipeline.ctx._failed_step}': ${pipeline.ctx._error}`);
  }
}

boot();

})();
