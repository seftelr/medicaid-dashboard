# Medicaid DME & Supply Dashboard

Interactive reporting dashboard for Medicaid DME and supply HCPCS codes (2018–2024).

**Data source:** [HHS Medicaid Provider Spending](https://www.medicaidopendata.org/) — $1.09T in Medicaid spending

## Categories
- **Incontinence & Urinary** — T45xx, A435x, A455x series ($8.18B, 48 codes)
- **Diabetes** — A4224, A4239, A4253, A9276, etc. ($1.46B, 15 codes)
- **Respiratory** — Nebulizers, CPAP, tracheostomy, oxygen ($500M+, 21 codes)
- **Wound Care** — Collagen, alginate, hydrogel, negative pressure dressings
- **Ostomy** — Pouches, barriers, irrigation sets
- **Other DME/Supply** — Miscellaneous supplies and accessories

## Features
- KPI summary cards per category
- Top codes bar chart
- Year-over-year spending trend (2018–2024)
- Full sortable HCPCS code table with relative share bars
- Top 10 providers per code (click to switch)

## Usage

### View dashboard
Open `dashboard.html` directly in a browser, or serve locally:
```bash
python3 -m http.server 8787
# then open http://localhost:8787/dashboard.html
```

### Refresh data
```bash
python3 fetch_data.py      # re-downloads from medicaidopendata.org API
python3 build_dashboard.py # regenerates dashboard.html from data/all_dme.json
```

## Files
| File | Description |
|------|-------------|
| `dashboard.html` | Self-contained HTML dashboard (Chart.js, no build step) |
| `fetch_data.py` | Downloads HCPCS detail, timeseries, and provider data via API |
| `build_dashboard.py` | Generates `dashboard.html` from `data/all_dme.json` |
| `data/all_dme.json` | Downloaded data (122 codes, 2018–2024) |
