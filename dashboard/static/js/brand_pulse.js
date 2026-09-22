(() => {
  const platformNames = { google: 'Google', instagram: 'Instagram', reddit: 'Reddit', tiktok: 'TikTok', web: 'Web' };
  const palette = { google: '#4f74d4', instagram: '#c65a8c', reddit: '#df684a', tiktok: '#2a3130', web: '#ad8731' };
  const state = { active: new Set(Object.keys(platformNames)) };
  const $ = id => document.getElementById(id);
  const iso = d => d.toISOString().slice(0, 10);
  const addDays = (d, days) => { const next = new Date(d); next.setDate(next.getDate() + days); return next; };
  const number = value => new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(Math.round(value || 0));
  const shortNumber = value => value >= 1000000 ? `${(value / 1000000).toFixed(1)}M` : value >= 1000 ? `${(value / 1000).toFixed(1)}K` : number(value);
  const prettyDate = value => new Date(`${value.slice(0, 10)}T12:00:00`).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  const apiQuery = () => new URLSearchParams({ from: $('fromDate').value, to: $('toDate').value, compare: $('comparison').value, platforms: [...state.active].join(',') }).toString();

  function initDates() {
    const end = new Date();
    $('toDate').value = iso(end);
    $('fromDate').value = iso(addDays(end, -29));
  }

  function renderPlatforms() {
    const root = $('platforms');
    root.replaceChildren();
    Object.entries(platformNames).forEach(([id, label]) => {
      const button = document.createElement('button');
      button.type = 'button'; button.className = `source-chip ${state.active.has(id) ? 'active' : ''}`;
      button.textContent = label; button.setAttribute('aria-pressed', state.active.has(id));
      button.addEventListener('click', () => {
        if (state.active.has(id) && state.active.size > 1) state.active.delete(id); else state.active.add(id);
        renderPlatforms(); refresh();
      });
      root.append(button);
    });
  }

  function setDelta(id, value, label) {
    const root = $(id);
    root.className = '';
    if (value === null || value === undefined) { root.textContent = `No comparison data for ${label}`; return; }
    const direction = value > 0.3 ? 'up' : value < -0.3 ? 'down' : '';
    root.className = direction;
    root.textContent = `${value > 0 ? '↑' : value < 0 ? '↓' : '↔'} ${Math.abs(value).toFixed(1)}% vs ${label}`;
  }

  function renderSummary(payload) {
    const { metrics, changes, comparison, freshness } = payload;
    const labels = { previous: 'last comparable period', week: 'last completed week', month: 'last completed month', quarter: 'last completed quarter', year: 'last year' };
    $('searchValue').textContent = metrics.search_interest ? number(metrics.search_interest) : '—';
    $('mentionsValue').textContent = number(metrics.mentions);
    $('reachValue').textContent = metrics.reach ? shortNumber(metrics.reach) : '—';
    $('sentimentValue').textContent = metrics.mentions ? `${Math.round(metrics.positive_share)}%` : '—';
    setDelta('searchChange', changes.search_interest, labels[comparison.type]);
    setDelta('mentionsChange', changes.mentions, labels[comparison.type]);
    setDelta('reachChange', changes.reach, labels[comparison.type]);
    setDelta('sentimentChange', changes.positive_share, labels[comparison.type]);
    const complete = freshness.filter(item => item.status === 'success');
    const latest = complete.map(item => item.latest_available_at).filter(Boolean).sort().at(-1);
    $('freshnessLabel').textContent = latest ? `Latest source data: ${prettyDate(latest)}` : complete.length ? 'Collection completed; source data date unavailable' : 'No source is connected yet';
    $('coverageNote').textContent = complete.length
      ? `${complete.length} source${complete.length === 1 ? '' : 's'} connected · comparing ${prettyDate(comparison.from)} – ${prettyDate(comparison.to)}`
      : 'Connect a source and run the daily collection to replace this empty state with real data.';
    renderFreshness(freshness);
  }

  function renderFreshness(rows) {
    const root = $('sourceFreshness'); root.replaceChildren();
    if (!rows.length) { root.textContent = 'No collection has run yet.'; return; }
    rows.forEach(item => {
      const row = document.createElement('div'); row.className = 'fresh-row';
      const left = document.createElement('span'); left.textContent = platformNames[item.platform] || item.platform;
      const right = document.createElement('b'); right.className = `status-${item.status || 'failed'}`;
      right.textContent = item.status === 'success' ? `Checked ${prettyDate(item.last_success_at)}` : item.status === 'skipped' ? 'Needs connection' : 'Needs attention';
      row.append(left, right); root.append(row);
    });
  }

  function renderBreakdown(rows) {
    const root = $('sourceBreakdown'); root.replaceChildren();
    const total = rows.reduce((sum, row) => sum + row.mentions, 0);
    if (!total) { root.textContent = 'No public mentions have been collected for this period.'; return; }
    rows.forEach(row => {
      const percent = Math.round(row.mentions / total * 100);
      const container = document.createElement('div'); container.className = 'source-row';
      const label = document.createElement('span'); label.textContent = platformNames[row.platform] || row.platform;
      const bar = document.createElement('div'); bar.className = 'bar'; const fill = document.createElement('i'); fill.style.width = `${percent}%`; fill.style.background = palette[row.platform] || '#087d77'; bar.append(fill);
      const value = document.createElement('b'); value.textContent = `${percent}%`;
      container.append(label, bar, value); root.append(container);
    });
  }

  function svgNode(name, attributes = {}) {
    const node = document.createElementNS('http://www.w3.org/2000/svg', name);
    Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value));
    return node;
  }

  function renderChart(rows) {
    const svg = $('trendChart'); svg.replaceChildren();
    $('chartEmpty').hidden = rows.length > 0;
    if (!rows.length) return;
    const width = Math.max(320, Math.round(svg.getBoundingClientRect().width || 700)); const height = 290;
    const margin = { top: 18, right: 15, bottom: 34, left: 39 }; const plotWidth = width - margin.left - margin.right; const plotHeight = height - margin.top - margin.bottom;
    const maxSearch = Math.max(1, ...rows.map(row => row.search_interest || 0)); const maxMentions = Math.max(1, ...rows.map(row => row.mentions || 0));
    const x = index => margin.left + (index / Math.max(1, rows.length - 1)) * plotWidth;
    const ySearch = value => margin.top + (1 - value / maxSearch) * plotHeight;
    const yMentions = value => margin.top + (1 - value / maxMentions) * plotHeight;
    svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
    [0, .25, .5, .75, 1].forEach(fraction => {
      const y = margin.top + plotHeight * fraction; svg.append(svgNode('line', { x1: margin.left, x2: width - margin.right, y1: y, y2: y, stroke: '#e4ebe6', 'stroke-width': '1' }));
      const label = svgNode('text', { x: margin.left - 8, y: y + 4, 'text-anchor': 'end', fill: '#718080', 'font-size': '10' }); label.textContent = Math.round(maxSearch * (1 - fraction)); svg.append(label);
    });
    const path = (metric, scale) => rows.map((row, index) => `${index ? 'L' : 'M'}${x(index).toFixed(1)},${scale(row[metric] || 0).toFixed(1)}`).join(' ');
    svg.append(svgNode('path', { d: path('search_interest', ySearch), fill: 'none', stroke: '#087d77', 'stroke-width': '2.5', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }));
    svg.append(svgNode('path', { d: path('mentions', yMentions), fill: 'none', stroke: '#d9684c', 'stroke-width': '2.5', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }));
    const ticks = width < 500 ? 3 : 5;
    Array.from({ length: ticks }, (_, index) => Math.round(index * (rows.length - 1) / Math.max(1, ticks - 1))).forEach(index => {
      const label = svgNode('text', { x: x(index), y: height - 11, 'text-anchor': 'middle', fill: '#718080', 'font-size': '10' }); label.textContent = new Date(`${rows[index].date}T12:00:00`).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }); svg.append(label);
    });
    const searchTitle = svgNode('text', { x: margin.left, y: 11, fill: '#718080', 'font-size': '10' }); searchTitle.textContent = 'Search'; svg.append(searchTitle);
    const mentionTitle = svgNode('text', { x: width - margin.right, y: 11, 'text-anchor': 'end', fill: '#718080', 'font-size': '10' }); mentionTitle.textContent = 'Mentions'; svg.append(mentionTitle);
  }

  function renderMentions(rows) {
    const body = $('mentionsTable'); body.replaceChildren();
    if (!rows.length) { const row = document.createElement('tr'), cell = document.createElement('td'); cell.colSpan = 5; cell.className = 'empty-table'; cell.textContent = 'No public conversations found for this period.'; row.append(cell); body.append(row); return; }
    rows.forEach(item => {
      const row = document.createElement('tr');
      const conversation = document.createElement('td'); conversation.className = 'conversation';
      if (/^https:\/\//i.test(item.source_url || '')) { const link = document.createElement('a'); link.href = item.source_url; link.target = '_blank'; link.rel = 'noopener noreferrer'; link.textContent = item.title || 'View public source'; conversation.append(link); }
      else conversation.textContent = item.title || 'Untitled public mention';
      const source = document.createElement('td'); source.className = 'source-name'; source.textContent = platformNames[item.platform] || item.platform;
      const engagement = document.createElement('td'); engagement.className = 'number'; engagement.textContent = number(item.engagement_count);
      const sentiment = document.createElement('td'); sentiment.className = `number sentiment-${item.sentiment || 'neutral'}`; sentiment.textContent = item.sentiment || 'Neutral';
      const published = document.createElement('td'); published.className = 'number sentiment-neutral'; published.textContent = prettyDate(item.published_at);
      row.append(conversation, source, engagement, sentiment, published); body.append(row);
    });
  }

  async function refresh() {
    const query = apiQuery();
    try {
      const [summary, trend, platforms, mentions] = await Promise.all([
        fetch(`/api/brand-pulse/summary?${query}`).then(response => response.json()),
        fetch(`/api/brand-pulse/trend?${query}`).then(response => response.json()),
        fetch(`/api/brand-pulse/platforms?${query}`).then(response => response.json()),
        fetch(`/api/brand-pulse/mentions?${query}`).then(response => response.json()),
      ]);
      renderSummary(summary); renderChart(trend.rows || []); renderBreakdown(platforms.rows || []); renderMentions(mentions.rows || []);
    } catch (error) {
      $('coverageNote').textContent = 'The dashboard could not reach its private data service. Please try again or check the deployment.';
      $('mentionsTable').innerHTML = '<tr><td colspan="5" class="empty-table">Data service unavailable.</td></tr>';
      console.error('Brand Pulse data error', error);
    }
  }

  initDates(); renderPlatforms();
  $('fromDate').addEventListener('change', refresh); $('toDate').addEventListener('change', refresh); $('comparison').addEventListener('change', refresh);
  document.querySelectorAll('[data-days]').forEach(button => button.addEventListener('click', () => {
    const end = new Date(`${$('toDate').value}T12:00:00`); $('fromDate').value = iso(addDays(end, -Number(button.dataset.days) + 1));
    document.querySelectorAll('[data-days]').forEach(item => item.classList.toggle('active', item === button)); refresh();
  }));
  window.addEventListener('resize', () => refresh());
  refresh();
})();
