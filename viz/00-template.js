// viz/00-template.js
// Copy this file, rename, and fill in render().

(function() {
  function render(container, data) {
    // Filter data to what you need
    const pts = data.filter(m => m.cost_per_task != null && m.cost_per_task > 0);

    // Build SVG (reference: bubble chart in dashboard.html)
    const W = 1100, H = 600;
    const M = { top: 30, right: 30, bottom: 50, left: 60 };

    let svg = `<svg viewBox="0 0 ${W} ${H}">`;
    // ... your axes, points, labels here ...
    svg += `</svg>`;

    container.innerHTML = svg;
  }

  window.VIZ_REGISTRY = window.VIZ_REGISTRY || [];
  window.VIZ_REGISTRY.push({
    id: '',  // hidden — template/deletable
    name: 'Template (delete me)',
    subtitle: 'Reference template for new vizes',
    render
  });
})();
