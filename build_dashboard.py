import json, os

DATA_DIR = os.path.dirname(os.path.abspath(__file__)) + '/data'

with open(f'{DATA_DIR}/all_dme.json') as f:
    raw = json.load(f)

categories = raw['categories']
data = raw['data']

# Build enriched category data
cat_data = {}
for cat_name, codes in categories.items():
    entries = []
    for code in codes:
        if code not in data:
            continue
        d = data[code]
        detail = d['detail']
        ts = d['timeseries']
        provs = d['providers']
        entries.append({
            'code': code,
            'description': detail.get('description',''),
            'total_paid': detail.get('total_paid') or 0,
            'total_claims': detail.get('total_claims') or 0,
            'unique_beneficiaries': detail.get('unique_beneficiaries') or 0,
            'unique_providers': detail.get('unique_providers') or 0,
            'avg_per_claim': detail.get('avg_per_claim') or 0,
            'timeseries': ts,
            'top_providers': provs[:10] if provs else [],
        })
    entries.sort(key=lambda x: x['total_paid'], reverse=True)
    cat_data[cat_name] = entries

# Compute all-category totals per category
cat_summary = {}
for cat_name, entries in cat_data.items():
    cat_summary[cat_name] = {
        'total_paid': sum(e['total_paid'] for e in entries),
        'total_claims': sum(e['total_claims'] for e in entries),
        'total_beneficiaries': sum(e['unique_beneficiaries'] for e in entries),
        'total_providers': len(set(p['npi'] for e in entries for p in e['top_providers'] if 'npi' in p)),
        'code_count': len(entries),
    }

# Build timeseries aggregates by year per category
from collections import defaultdict
cat_timeseries = {}
for cat_name, entries in cat_data.items():
    by_year = defaultdict(float)
    for e in entries:
        for row in e['timeseries']:
            yr = row.get('year') or row.get('service_year') or (row.get('month','')[:4] if row.get('month') else None)
            paid = row.get('total_paid') or 0
            if yr:
                by_year[int(yr)] += paid
    if by_year:
        years = sorted(by_year.keys())
        cat_timeseries[cat_name] = {
            'years': years,
            'paid': [by_year[y] for y in years]
        }

js_data = json.dumps({
    'categories': cat_data,
    'cat_summary': cat_summary,
    'cat_timeseries': cat_timeseries,
}, separators=(',',':'))

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Medicaid DME & Supply Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {{
    --bg: #0f1117;
    --surface: #1a1d27;
    --surface2: #242838;
    --border: #2e3248;
    --accent: #6366f1;
    --accent2: #818cf8;
    --green: #10b981;
    --yellow: #f59e0b;
    --red: #ef4444;
    --text: #e2e8f0;
    --muted: #94a3b8;
    --inco: #8b5cf6;
    --osto: #06b6d4;
    --wound: #f97316;
    --resp: #3b82f6;
    --diab: #10b981;
    --other: #ec4899;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 14px; }}
  header {{ background: var(--surface); border-bottom: 1px solid var(--border); padding: 16px 24px; display: flex; align-items: center; gap: 16px; }}
  header h1 {{ font-size: 20px; font-weight: 700; color: #fff; }}
  header p {{ color: var(--muted); font-size: 13px; }}
  .badge {{ background: var(--accent); color: #fff; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }}

  .tabs {{ display: flex; gap: 4px; padding: 16px 24px 0; overflow-x: auto; }}
  .tab {{ padding: 8px 16px; border-radius: 8px 8px 0 0; cursor: pointer; font-weight: 600; font-size: 13px; color: var(--muted); background: var(--surface); border: 1px solid var(--border); border-bottom: none; transition: all .15s; white-space: nowrap; }}
  .tab:hover {{ color: var(--text); }}
  .tab.active {{ color: #fff; border-bottom: none; }}
  .tab[data-cat="Incontinence & Urinary"].active {{ background: var(--inco); border-color: var(--inco); }}
  .tab[data-cat="Ostomy"].active {{ background: var(--osto); border-color: var(--osto); }}
  .tab[data-cat="Wound Care"].active {{ background: var(--wound); border-color: var(--wound); }}
  .tab[data-cat="Respiratory"].active {{ background: var(--resp); border-color: var(--resp); }}
  .tab[data-cat="Diabetes"].active {{ background: var(--diab); border-color: var(--diab); }}
  .tab[data-cat="Other DME/Supply"].active {{ background: var(--other); border-color: var(--other); }}

  .panel {{ display: none; padding: 20px 24px 40px; }}
  .panel.active {{ display: block; }}

  .kpi-row {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 20px; }}
  .kpi {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 16px; }}
  .kpi .label {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: .5px; margin-bottom: 6px; }}
  .kpi .value {{ font-size: 24px; font-weight: 700; color: #fff; }}
  .kpi .sub {{ font-size: 11px; color: var(--muted); margin-top: 2px; }}

  .charts-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }}
  @media(max-width:900px){{ .charts-row{{ grid-template-columns: 1fr; }} }}
  .chart-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 18px; }}
  .chart-card h3 {{ font-size: 13px; font-weight: 600; color: var(--muted); margin-bottom: 14px; text-transform: uppercase; letter-spacing: .5px; }}
  .chart-wrap {{ position: relative; }}

  .table-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; margin-bottom: 20px; overflow: hidden; }}
  .table-card h3 {{ font-size: 13px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: .5px; padding: 16px 18px 12px; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ background: var(--surface2); color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .4px; padding: 10px 14px; text-align: left; font-weight: 600; cursor: pointer; user-select: none; white-space: nowrap; }}
  th:hover {{ color: var(--text); }}
  th .sort-arrow {{ margin-left: 4px; opacity: .4; }}
  th.sorted .sort-arrow {{ opacity: 1; color: var(--accent2); }}
  td {{ padding: 10px 14px; border-bottom: 1px solid var(--border); color: var(--text); font-size: 13px; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: rgba(255,255,255,.03); }}
  .code-chip {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-family: monospace; font-size: 12px; font-weight: 700; background: var(--surface2); color: var(--accent2); }}
  .bar-cell {{ display: flex; align-items: center; gap: 8px; }}
  .bar-track {{ flex: 1; background: var(--surface2); border-radius: 3px; height: 6px; min-width: 60px; max-width: 150px; }}
  .bar-fill {{ height: 6px; border-radius: 3px; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; }}

  .prov-section {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; margin-top: 16px; overflow: hidden; }}
  .prov-section h3 {{ font-size: 13px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: .5px; padding: 14px 18px 10px; border-bottom: 1px solid var(--border); }}
  .prov-select {{ display: flex; gap: 8px; padding: 10px 18px; flex-wrap: wrap; border-bottom: 1px solid var(--border); }}
  .prov-btn {{ padding: 5px 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--surface2); color: var(--muted); cursor: pointer; font-size: 12px; transition: all .15s; }}
  .prov-btn:hover, .prov-btn.active {{ border-color: var(--accent); color: #fff; background: rgba(99,102,241,.2); }}

  .note {{ font-size: 12px; color: var(--muted); padding: 8px 18px 14px; }}
</style>
</head>
<body>
<header>
  <div>
    <h1>Medicaid DME &amp; Supply Dashboard</h1>
    <p>HHS Medicaid Provider Spending · 2018–2024 · Source: medicaidopendata.org</p>
  </div>
  <span class="badge">All States</span>
</header>

<div class="tabs" id="tabs"></div>
<div id="panels"></div>

<script>
const RAW = {js_data};

const CAT_COLORS = {{
  'Incontinence & Urinary': '#8b5cf6',
  'Ostomy':                  '#06b6d4',
  'Wound Care':              '#f97316',
  'Respiratory':             '#3b82f6',
  'Diabetes':                '#10b981',
  'Other DME/Supply':        '#ec4899',
}};

const CHART_PALETTE = [
  '#6366f1','#8b5cf6','#06b6d4','#10b981',
  '#f59e0b','#f97316','#ef4444','#ec4899',
  '#3b82f6','#a78bfa','#34d399','#fbbf24',
];

function fmt(n) {{
  if (!n) return '$0';
  if (n >= 1e9) return '$' + (n/1e9).toFixed(2) + 'B';
  if (n >= 1e6) return '$' + (n/1e6).toFixed(1) + 'M';
  if (n >= 1e3) return '$' + (n/1e3).toFixed(0) + 'K';
  return '$' + n.toFixed(0);
}}
function fmtN(n) {{
  if (!n) return '0';
  if (n >= 1e9) return (n/1e9).toFixed(2)+'B';
  if (n >= 1e6) return (n/1e6).toFixed(1)+'M';
  if (n >= 1e3) return (n/1e3).toFixed(0)+'K';
  return n.toString();
}}
function pct(v, max) {{ return max > 0 ? Math.min(100, (v/max)*100) : 0; }}

let charts = {{}};

function buildPanel(catName, entries, summary, tsData, color) {{
  const maxPaid = Math.max(...entries.map(e=>e.total_paid));

  // KPI row
  const kpiHtml = `
    <div class="kpi-row">
      <div class="kpi"><div class="label">Total Paid</div><div class="value">${{fmt(summary.total_paid)}}</div><div class="sub">2018–2024</div></div>
      <div class="kpi"><div class="label">Total Claims</div><div class="value">${{fmtN(summary.total_claims)}}</div><div class="sub">cumulative</div></div>
      <div class="kpi"><div class="label">HCPCS Codes</div><div class="value">${{summary.code_count}}</div><div class="sub">in this category</div></div>
    </div>`;

  // Top 12 by paid for bar chart
  const topCodes = entries.slice(0,12);
  const barChartId = 'bar_' + catName.replace(/[^a-z]/gi,'_');
  const tsChartId  = 'ts_'  + catName.replace(/[^a-z]/gi,'_');

  // Provider section
  const topEntry = entries[0];
  const provSelectHtml = entries.slice(0,8).map((e,i) =>
    `<button class="prov-btn${{i===0?' active':''}}" onclick="showProviders('${{catName}}','${{e.code}}')" id="pbtn_${{e.code}}">${{e.code}}</button>`
  ).join('');

  const panelDiv = document.createElement('div');
  panelDiv.className = 'panel';
  panelDiv.dataset.cat = catName;
  panelDiv.innerHTML = kpiHtml + `
    <div class="charts-row">
      <div class="chart-card">
        <h3>Top Codes by Total Paid</h3>
        <div class="chart-wrap"><canvas id="${{barChartId}}" height="260"></canvas></div>
      </div>
      <div class="chart-card">
        <h3>Annual Spending Trend ($)</h3>
        <div class="chart-wrap"><canvas id="${{tsChartId}}" height="260"></canvas></div>
      </div>
    </div>
    <div class="table-card">
      <h3>
        All HCPCS Codes
        <span style="font-size:11px;font-weight:400;color:var(--muted)">Click row to see top providers</span>
      </h3>
      ${{buildTable(entries, maxPaid, catName, color)}}
    </div>
    <div class="prov-section" id="prov_${{catName.replace(/[^a-z]/gi,'_')}}">
      <h3>Top Providers</h3>
      <div class="prov-select">${{provSelectHtml}}</div>
      <div id="provtable_${{catName.replace(/[^a-z]/gi,'_')}}"></div>
      <div class="note">Showing top 10 providers for selected code · Data: 2018–2024 · Source: medicaidopendata.org</div>
    </div>`;

  document.getElementById('panels').appendChild(panelDiv);

  // Schedule chart creation
  setTimeout(() => {{
    // Bar chart
    const barCtx = document.getElementById(barChartId);
    if (barCtx) {{
      if (charts[barChartId]) charts[barChartId].destroy();
      charts[barChartId] = new Chart(barCtx, {{
        type: 'bar',
        data: {{
          labels: topCodes.map(e => e.code),
          datasets: [{{ label: 'Total Paid', data: topCodes.map(e=>e.total_paid),
            backgroundColor: color + 'cc', borderColor: color, borderWidth: 1,
            borderRadius: 4 }}]
        }},
        options: {{
          responsive: true, indexAxis: 'y',
          plugins: {{ legend: {{ display: false }}, tooltip: {{
            callbacks: {{ label: ctx => ' ' + fmt(ctx.raw) }}
          }}}},
          scales: {{
            x: {{ grid: {{ color: '#2e3248' }}, ticks: {{ color: '#94a3b8', callback: v => fmt(v) }} }},
            y: {{ grid: {{ display: false }}, ticks: {{ color: '#e2e8f0', font: {{family:'monospace',weight:'bold'}} }} }}
          }}
        }}
      }});
    }}

    // Timeseries chart
    const tsCtx = document.getElementById(tsChartId);
    if (tsCtx && tsData) {{
      if (charts[tsChartId]) charts[tsChartId].destroy();

      // Build per-code timeseries for top 5 codes — data uses monthly 'month' field
      const top5 = entries.slice(0,5);
      // Helper: get year from row (supports 'year', 'service_year', or 'month' like "2018-01")
      const getYear = r => r.year || r.service_year || (r.month ? parseInt(r.month.substring(0,4)) : null);
      const allYears = [...new Set(top5.flatMap(e => e.timeseries.map(r => getYear(r)).filter(Boolean)))].sort();

      const datasets = top5.map((e, i) => {{
        const byYear = {{}};
        e.timeseries.forEach(r => {{
          const yr = getYear(r);
          if (yr) byYear[yr] = (byYear[yr] || 0) + (r.total_paid || 0);
        }});
        return {{
          label: e.code,
          data: allYears.map(y => byYear[y] || 0),
          borderColor: CHART_PALETTE[i],
          backgroundColor: CHART_PALETTE[i]+'33',
          fill: false, tension: 0.3, pointRadius: 4,
        }};
      }});

      charts[tsChartId] = new Chart(tsCtx, {{
        type: 'line',
        data: {{ labels: allYears.map(String), datasets }},
        options: {{
          responsive: true,
          plugins: {{
            legend: {{ labels: {{ color: '#94a3b8', font: {{size:11}}, boxWidth: 12 }} }},
            tooltip: {{ callbacks: {{ label: ctx => ctx.dataset.label + ': ' + fmt(ctx.raw) }} }}
          }},
          scales: {{
            x: {{ grid: {{ color: '#2e3248' }}, ticks: {{ color: '#94a3b8' }} }},
            y: {{ grid: {{ color: '#2e3248' }}, ticks: {{ color: '#94a3b8', callback: v => fmt(v) }} }}
          }}
        }}
      }});
    }}

    // Show default provider table
    if (entries[0]) showProviders(catName, entries[0].code);
  }}, 0);
}}

function buildTable(entries, maxPaid, catName, color) {{
  const rows = entries.map(e => `
    <tr onclick="showProviders('${{catName}}','${{e.code}}');highlightRow(this,'${{e.code}}')" style="cursor:pointer" id="row_${{e.code}}">
      <td><span class="code-chip">${{e.code}}</span></td>
      <td>${{e.description}}</td>
      <td class="num">${{fmt(e.total_paid)}}</td>
      <td class="num">${{fmtN(e.total_claims)}}</td>
      <td class="num">${{fmtN(e.unique_beneficiaries)}}</td>
      <td class="num">${{e.unique_providers?.toLocaleString() || '—'}}</td>
      <td class="num">${{e.avg_per_claim ? fmt(e.avg_per_claim) : '—'}}</td>
      <td>
        <div class="bar-cell">
          <div class="bar-track"><div class="bar-fill" style="width:${{pct(e.total_paid,maxPaid).toFixed(1)}}%;background:${{color}}"></div></div>
        </div>
      </td>
    </tr>`).join('');

  return `<table>
    <thead><tr>
      <th>Code</th><th>Description</th>
      <th class="num sorted">Total Paid <span class="sort-arrow">↓</span></th>
      <th class="num">Claims</th>
      <th class="num">Beneficiaries</th>
      <th class="num">Providers</th>
      <th class="num">$/Claim</th>
      <th>Share</th>
    </tr></thead>
    <tbody>${{rows}}</tbody>
  </table>`;
}}

function highlightRow(tr, code) {{
  tr.closest('table').querySelectorAll('tr').forEach(r => r.style.background = '');
  tr.style.background = 'rgba(99,102,241,.12)';
}}

function showProviders(catName, code) {{
  const safeCat = catName.replace(/[^a-z]/gi,'_');
  const entries = RAW.categories[catName];
  const entry = entries.find(e=>e.code===code);
  const container = document.getElementById('provtable_'+safeCat);
  if (!entry || !container) return;

  // Update active button
  document.querySelectorAll(`#prov_${{safeCat}} .prov-btn`).forEach(b=>b.classList.remove('active'));
  const btn = document.getElementById('pbtn_'+code);
  if (btn) btn.classList.add('active');

  const provs = entry.top_providers;
  if (!provs || !provs.length) {{
    container.innerHTML = '<p style="padding:14px 18px;color:var(--muted)">No provider data available.</p>';
    return;
  }}

  const maxPaid = Math.max(...provs.map(p=>p.total_paid||0));
  const rows = provs.map(p => `
    <tr>
      <td>${{p.provider_name||p.name||'—'}}</td>
      <td>${{p.provider_city||p.city||'—'}}, ${{p.provider_state||p.state||''}}</td>
      <td class="num">${{fmt(p.total_paid)}}</td>
      <td class="num">${{fmtN(p.total_claims||p.claim_count)}}</td>
      <td class="num">${{p.avg_per_claim ? fmt(p.avg_per_claim) : '—'}}</td>
      <td>
        <div class="bar-cell">
          <div class="bar-track" style="max-width:100px"><div class="bar-fill" style="width:${{pct(p.total_paid,maxPaid).toFixed(1)}}%;background:#6366f1"></div></div>
        </div>
      </td>
    </tr>`).join('');

  container.innerHTML = `
    <table>
      <thead><tr>
        <th>Provider</th><th>Location</th>
        <th class="num sorted">Total Paid <span class="sort-arrow">↓</span></th>
        <th class="num">Claims</th>
        <th class="num">$/Claim</th>
        <th>Share</th>
      </tr></thead>
      <tbody>${{rows}}</tbody>
    </table>`;
}}

// Initialize
const tabsEl = document.getElementById('tabs');
const catNames = Object.keys(RAW.categories);

catNames.forEach((cat, i) => {{
  const tab = document.createElement('div');
  tab.className = 'tab' + (i===0?' active':'');
  tab.dataset.cat = cat;
  const s = RAW.cat_summary[cat];
  tab.textContent = cat;
  tab.onclick = () => {{
    document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
    tab.classList.add('active');
    document.querySelector(`.panel[data-cat="${{cat}}"]`).classList.add('active');
  }};
  tabsEl.appendChild(tab);

  buildPanel(cat, RAW.categories[cat], RAW.cat_summary[cat], RAW.cat_timeseries[cat], CAT_COLORS[cat]||'#6366f1');
}});

// Activate first panel
if (catNames[0]) {{
  document.querySelector(`.panel[data-cat="${{catNames[0]}}"]`).classList.add('active');
}}
</script>
</body>
</html>"""

out = os.path.dirname(os.path.abspath(__file__)) + '/dashboard.html'
with open(out, 'w') as f:
    f.write(html)

print(f'Dashboard written to {out}')
