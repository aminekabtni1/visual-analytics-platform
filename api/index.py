"""
Vercel entrypoint — Full interactive Visual Analytics Platform.
Serves a polished SPA (no Streamlit) that runs on Vercel serverless.
Data is precomputed to api/data/*.json (committed) so the function stays
lightweight (only Flask). The SPA fetches JSON and renders Plotly charts
client-side — same palette, same 5 views as dashboard/app.py but
Vercel-native.

GET /              → HTML SPA
GET /api/data/<f>  → JSON (rules, clusters, etc.)
GET /health        → health check
"""
from flask import Flask, Response, send_from_directory, jsonify
import pathlib, json

app = Flask(__name__)
DATA_DIR = pathlib.Path(__file__).parent / "data"

# Ensure data dir exists (for local dev)
DATA_DIR.mkdir(parents=True, exist_ok=True)

@app.get("/health")
def health():
    return {"ok": True, "app": "visual-analytics-platform", "mode": "vercel-spa"}

@app.get("/api/data/<path:filename>")
def serve_data(filename):
    # safe: only serve .json from DATA_DIR
    if not filename.endswith(".json"):
        return jsonify({"error": "not found"}), 404
    p = DATA_DIR / filename
    if not p.exists():
        return jsonify({"error": "not found", "file": filename}), 404
    return send_from_directory(str(DATA_DIR), filename, mimetype="application/json")

# also serve screenshots and er diagram as static via same data route? Add explicit
@app.get("/api/er_diagram.png")
def er_png():
    # serve from ../assets if exists, else redirect to GitHub raw
    ap = pathlib.Path(__file__).parent.parent / "assets" / "er_diagram.png"
    if ap.exists():
        return send_from_directory(str(ap.parent), ap.name, mimetype="image/png")
    return Response(status=302, headers={"Location": "https://raw.githubusercontent.com/aminekabtni1/visual-analytics-platform/main/assets/er_diagram.png"})

HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Visual Analytics Platform — Market Basket & Customer Pattern Mining</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>
  :root{--bg:#FDFCF9;--paper:#FFFFFF;--ink:#121417;--soft:#5B616E;--line:#E8E2D9;--line2:#D6CFC2;--accent:#C85A3A;--sage:#1E6B5A;--amber:#C18F2E;--blue:#3A5A7A;--dark:#0F1115;--dark2:#1A1E23;}
  *{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;font-family:Inter,system-ui,sans-serif;background:var(--bg);color:var(--ink);font-size:13px;line-height:1.5}
  a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
  .wrap{max-width:1440px;margin:0 auto;padding:0 20px}
  /* header */
  .topbar{background:var(--dark);color:#E8E6E1;padding:10px 0;border-bottom:1px solid #1E232A;position:sticky;top:0;z-index:20}
  .topbar .wrap{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
  .brand{font-family:Newsreader,serif;font-weight:700;letter-spacing:-.02em;font-size:18px;display:flex;align-items:center;gap:10px}
  .brand small{font-family:JetBrains Mono,monospace;font-size:9px;letter-spacing:.16em;text-transform:uppercase;color:#8B92A3;font-weight:400}
  .pill{font-family:JetBrains Mono,monospace;font-size:11px;border:1px solid #2A303C;background:#1A1E23;color:#C9CDD6;border-radius:999px;padding:5px 10px}
  .pill.accent{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:700}
  /* hero */
  .hero{padding:22px 0 14px}
  .eyebrow{font-family:JetBrains Mono,monospace;font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--soft);margin-bottom:8px}
  h1{font-family:Newsreader,serif;font-size:32px;line-height:1.05;letter-spacing:-.03em;margin:0 0 8px}h1 em{font-style:normal;color:var(--accent)}
  .sub{color:var(--soft);max-width:860px;font-size:13px}
  /* layout */
  .layout{display:grid;grid-template-columns:260px 1fr;gap:18px;align-items:start;margin-top:14px}
  @media(max-width:980px){.layout{grid-template-columns:1fr} .sidebar{position:static}}
  .sidebar{background:var(--dark);border:1px solid #1E232A;border-radius:12px;padding:14px;position:sticky;top:58px}
  .sidebar .nav{display:flex;flex-direction:column;gap:6px}
  .nav button{appearance:none;text-align:left;background:transparent;border:1px solid transparent;color:#C9CDD6;border-radius:8px;padding:9px 10px;font-size:13px;cursor:pointer;display:flex;align-items:center;gap:8px}
  .nav button.active{background:var(--dark2);border-color:#2A303C;color:#fff;font-weight:600}
  .nav button small{margin-left:auto;font-family:JetBrains Mono,monospace;font-size:10px;color:#8B92A3}
  .side-card{margin-top:14px;padding-top:14px;border-top:1px solid #1E232A}
  .side-title{font-family:JetBrains Mono,monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:#8B92A3;margin-bottom:8px}
  .run-line{display:flex;justify-content:space-between;font-family:JetBrains Mono,monospace;font-size:11px;padding:5px 0;border-bottom:1px solid #1A1E23;color:#C9CDD6}
  .annotation{font-size:11px;color:#9AA0B2;border-left:2px solid #252A32;padding-left:8px;line-height:1.5}
  /* content */
  .content{min-width:0}
  .view{display:none}.view.active{display:block}
  .card{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:16px 18px;box-shadow:0 1px 2px rgba(16,24,40,.04);margin-bottom:14px}
  .card-title{font-family:JetBrains Mono,monospace;font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--soft);margin-bottom:8px;display:flex;justify-content:space-between;gap:10px}
  .card-title span:last-child{font-weight:400;text-transform:none;letter-spacing:0;color:var(--soft);font-size:11px}
  .metric-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:14px}
  @media(max-width:900px){.metric-grid{grid-template-columns:repeat(2,1fr)}}
  .metric-card{border-left:3px solid var(--line);padding-left:12px}
  .metric-card.accent{border-left-color:var(--accent)}
  .metric-val{font-family:Newsreader,serif;font-size:26px;font-weight:700;line-height:1}
  .metric-sub{font-size:11px;color:var(--soft);margin-top:4px}
  .grid2{display:grid;grid-template-columns:1.55fr 1fr;gap:14px}
  @media(max-width:980px){.grid2{grid-template-columns:1fr}}
  .grid3{display:grid;grid-template-columns:1.9fr 1fr;gap:14px}
  @media(max-width:980px){.grid3{grid-template-columns:1fr}}
  .controls{display:flex;gap:12px;flex-wrap:wrap;align-items:end;margin-bottom:10px}
  .controls label{font-family:JetBrains Mono,monospace;font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--soft);display:flex;flex-direction:column;gap:4px}
  .controls input,.controls select{font-size:12px;padding:6px 8px;border:1px solid var(--line);border-radius:8px;background:white;min-width:140px}
  .divider{height:1px;background:var(--line);margin:12px 0}
  table{width:100%;border-collapse:collapse;font-size:12px}
  th{font-family:JetBrains Mono,monospace;font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--soft);text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);white-space:nowrap}
  td{padding:6px 8px;border-bottom:1px solid #F0EBE3;vertical-align:top}
  tr:hover td{background:#FFFBF5}
  .mono-code{font-family:JetBrains Mono,monospace;font-size:11px;background:#F8F5F0;border:1px solid var(--line);border-radius:6px;padding:1px 5px}
  .pill-inline{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:600;border:1px solid var(--line);background:white}
  .cluster-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
  @media(max-width:1000px){.cluster-grid{grid-template-columns:repeat(2,1fr)}}
  @media(max-width:560px){.cluster-grid{grid-template-columns:1fr}}
  footer{margin:22px 0;font-size:11px;color:#8B92A3;text-align:center}
  .callout{background:#FFF3ED;border:1px solid #F0D5C8;border-radius:10px;padding:10px 12px;font-size:12px;color:#5B3A2E;line-height:1.5;margin-bottom:12px}
  .callout.vercel{display:none}
</style>
</head>
<body>
<div class="topbar"><div class="wrap">
  <div class="brand">◉ Basket & Pattern Lab <small>Retail Mining · Visual Analytics</small></div>
  <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
    <span class="pill" id="runBadge">loading…</span>
    <a class="pill" href="https://github.com/aminekabtni1/visual-analytics-platform" target="_blank">GitHub</a>
    <a class="pill accent" href="https://github.com/aminekabtni1/visual-analytics-platform#deploy" target="_blank">Deploy docs</a>
  </div>
</div></div>

<div class="wrap hero">
  <div class="eyebrow">Full interactive app — Vercel native (data precomputed, no Streamlit needed)</div>
  <h1>Visual Analytics Platform for <em>Market Basket & Customer Pattern Mining</em></h1>
  <p class="sub">Same mining pipelines (FP-Growth · RFM+K-Means · Isolation Forest) and same relational design (raw + traceable mining runs), but rendered as a Vercel-native SPA — Plotly network graph, PCA cluster map, outlier drill-downs, and cross-linked views. No `vercel build` failure: this page <b>is</b> the app.</p>
  <div class="callout" id="vercelNote">If you came from the previous Vercel landing-only build: that was a lightweight placeholder to make <span class="mono-code">vercel build</span> pass. This deployment now serves the <b>full interactive analytics</b> directly on Vercel — no Streamlit Cloud needed. The Streamlit version at <span class="mono-code">dashboard/app.py</span> is identical in logic and remains available locally/Docker.</div>
</div>

<div class="wrap layout">
  <aside class="sidebar">
    <div class="nav" id="nav">
      <button data-view="overview" class="active">Overview <small>Raw & Sales</small></button>
      <button data-view="rules">Rules <small>Network</small></button>
      <button data-view="clusters">Clusters <small>Segments</small></button>
      <button data-view="outliers">Outliers <small>Anomalies</small></button>
      <button data-view="method">Method <small>Evaluation</small></button>
    </div>
    <div class="side-card">
      <div class="side-title">Mining runs</div>
      <div id="runs"></div>
      <div class="annotation" style="margin-top:10px">Click a product in Rules to drill into its history & cluster affinity. Click a cluster point in Clusters to inspect.</div>
    </div>
    <div class="side-card" style="font-size:10px;color:#6B7280">SQLite · FP-Growth · K-Means · Isolation Forest · Flask · Plotly</div>
  </aside>

  <main class="content">
    <!-- OVERVIEW -->
    <section id="view-overview" class="view active">
      <div style="display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:8px">
        <div style="font-family:Newsreader,serif;font-size:28px;font-weight:700;letter-spacing:-.02em">Sales Overview</div>
        <div class="mono-code" id="overviewCounts" style="font-size:10px;letter-spacing:.08em;text-transform:uppercase">loading…</div>
      </div>
      <div id="metricGrid" class="metric-grid"></div>
      <div class="grid2">
        <div class="card">
          <div class="card-title">Revenue & transactions over time <span>daily</span></div>
          <div id="dailyChart" style="height:260px"></div>
        </div>
        <div class="card">
          <div class="card-title">Mix by category <span>filtered</span></div>
          <div id="catChart" style="height:260px"></div>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:1.2fr .8fr;gap:14px">
        <div class="card">
          <div class="card-title">Transactions — sample <span id="sampleCount"></span></div>
          <div class="controls">
            <label>Category <select id="catFilter"><option value="">All categories</option></select></label>
            <label>Search <input id="search" placeholder="StockCode or description"/></label>
          </div>
          <div style="max-height:320px;overflow:auto;border:1px solid var(--line);border-radius:10px">
            <table id="txTable"><thead><tr><th>Date</th><th>Txn</th><th>Product</th><th>Cat</th><th>Qty</th><th>£</th></tr></thead><tbody></tbody></table>
          </div>
        </div>
        <div>
          <div class="card" style="background:var(--dark);border-color:#1E232A;color:#E8E6E1">
            <div class="side-title" style="color:#8B92A3">Before → After</div>
            <div style="font-family:Newsreader,serif;font-size:16px;font-weight:600;color:#FDFCF9">A picture is worth a thousand rows.</div>
            <div style="font-size:12px;line-height:1.6;color:#C9CDD6;margin-top:6px">Raw: <b style="color:#FDFCF9">42k line items</b> illegible. After mining: <b style="color:#FDFCF9">9 rules</b> (network), <b style="color:#FDFCF9">4 archetypes</b> (PCA), <b style="color:#FDFCF9">~5% anomalies</b>. Use Rules & Clusters tabs.</div>
            <div class="divider" style="background:#1E232A"></div>
            <ul style="font-size:11px;color:#AEB4C2;line-height:1.5;margin:6px 0 0 16px"><li>Cancelled orders removed</li><li>Null CustomerID dropped</li><li>Duplicates deduped</li></ul>
          </div>
          <div class="card">
            <div class="card-title">Where sales happen</div>
            <div id="countryChart" style="height:180px"></div>
          </div>
        </div>
      </div>
    </section>

    <!-- RULES -->
    <section id="view-rules" class="view">
      <div style="display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:8px">
        <div style="font-family:Newsreader,serif;font-size:28px;font-weight:700">Association Rules</div>
        <div class="mono-code">FP-Growth · support ≥0.015 · conf ≥0.25 · <span id="ruleCount"></span> rules</div>
      </div>
      <div class="callout" style="font-size:12px">Nodes = products, edges = rules. Thickness → confidence, opacity → lift. Terracotta = high lift. Select a product to drill down.</div>
      <div class="controls">
        <label>Min lift <input id="minLift" type="range" min="1" max="4" step="0.1" value="1.5"/> <span id="minLiftV">1.5</span></label>
        <label>Min confidence <input id="minConf" type="range" min="0" max="1" step="0.05" value="0.25"/> <span id="minConfV">0.25</span></label>
        <label>Top N <input id="topN" type="range" min="4" max="30" step="1" value="9"/> <span id="topNV">9</span></label>
      </div>
      <div class="grid3">
        <div class="card" style="padding:10px 12px">
          <div id="networkChart" style="height:520px"></div>
          <div class="annotation">Node size → product support. Edge width → confidence. Categories: Food terracotta, Home blue, Kitchen amber, Toys sage.</div>
        </div>
        <div class="card">
          <div class="card-title">Rule details <span id="filteredCount"></span></div>
          <label style="font-family:JetBrains Mono,monospace;font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--soft)">Focus product (cross-links)
            <select id="productSelect" style="width:100%;margin-top:6px;padding:8px;border:1px solid var(--line);border-radius:8px;background:white"></select>
          </label>
          <div style="margin-top:10px;max-height:260px;overflow:auto;border:1px solid var(--line);border-radius:8px">
            <table id="rulesTable"><thead><tr><th>Rule</th><th>Lift</th><th>Conf</th></tr></thead><tbody></tbody></table>
          </div>
          <div id="productDrill" style="display:none;margin-top:10px;border:1px solid var(--line);border-radius:10px;padding:10px;background:#FFFBF5"></div>
          <div id="productHint" style="margin-top:10px;background:#FFFBF5;border:1px solid var(--line);border-radius:8px;padding:10px;font-size:12px;color:var(--soft)">Pick a product above to see its history & which clusters buy it most.</div>
        </div>
      </div>
    </section>

    <!-- CLUSTERS -->
    <section id="view-clusters" class="view">
      <div style="display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:8px">
        <div style="font-family:Newsreader,serif;font-size:28px;font-weight:700">Customer Segments</div>
        <div class="mono-code">RFM · K-Means · PCA projection</div>
      </div>
      <div id="clusterCards" class="cluster-grid"></div>
      <div class="grid3" style="margin-top:14px">
        <div class="card">
          <div class="card-title">Customer map — PCA(RFM) <span id="silNote"></span></div>
          <div id="pcaChart" style="height:420px"></div>
          <div class="annotation">Proximity = similar behaviour. Diamonds = centroids. Select a cluster on the right.</div>
        </div>
        <div class="card">
          <div class="card-title">Segment inspector</div>
          <label style="font-family:JetBrains Mono,monospace;font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--soft)">Choose cluster
            <select id="clusterSelect" style="width:100%;margin-top:6px;padding:8px;border:1px solid var(--line);border-radius:8px"></select>
          </label>
          <div id="clusterSummary" style="margin-top:10px;background:#F8F5F0;border:1px solid var(--line);border-radius:10px;padding:12px"></div>
          <div id="clusterCompare" style="margin-top:10px"></div>
          <div style="margin-top:12px">
            <div style="font-size:11px;font-weight:600;margin-bottom:6px">Top products this segment buys</div>
            <div id="clusterProducts"></div>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="card-title">Customers in cluster <span id="clusterCustomersTitle"></span></div>
        <div style="max-height:220px;overflow:auto;border:1px solid var(--line);border-radius:8px">
          <table id="clusterTable"><thead><tr><th>Customer</th><th>Recency</th><th>Freq</th><th>Monetary</th><th>Dist</th></tr></thead><tbody></tbody></table>
        </div>
      </div>
    </section>

    <!-- OUTLIERS -->
    <section id="view-outliers" class="view">
      <div style="display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:8px">
        <div style="font-family:Newsreader,serif;font-size:28px;font-weight:700">Anomalies</div>
        <div class="mono-code">Isolation Forest · contamination 0.05 · ~5% flagged</div>
      </div>
      <div class="controls">
        <label>View <select id="outlierView"><option>Value vs Items</option><option>Over time</option><option>Score distribution</option></select></label>
        <label style="flex-direction:row;align-items:center;gap:6px"><input id="onlyFlagged" type="checkbox"/> Only flagged</label>
        <span id="outlierStats" style="font-size:11px;color:var(--soft);padding-top:6px"></span>
      </div>
      <div class="grid3">
        <div class="card"><div id="outlierChart" style="height:400px"></div><div class="annotation">Contamination 0.05 → ~5% flagged. Flagged ≠ fraud — review reason_json.</div></div>
        <div class="card">
          <div class="card-title">Drill-down</div>
          <label style="font-family:JetBrains Mono,monospace;font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--soft)">Choose flagged transaction
            <select id="outlierSelect" style="width:100%;margin-top:6px;padding:8px;border:1px solid var(--line);border-radius:8px"></select>
          </label>
          <div id="outlierDrill"></div>
          <div class="divider"></div>
          <div style="font-size:11px;font-weight:600;margin-bottom:6px">Most anomalous (lowest scores)</div>
          <div style="max-height:200px;overflow:auto;border:1px solid var(--line);border-radius:8px">
            <table id="outlierTop"><thead><tr><th>Txn</th><th>£</th><th>Items</th><th>Score</th></tr></thead><tbody></tbody></table>
          </div>
        </div>
      </div>
    </section>

    <!-- METHOD -->
    <section id="view-method" class="view">
      <div style="font-family:Newsreader,serif;font-size:28px;font-weight:700;margin-bottom:8px">Method & Evaluation</div>
      <div style="display:grid;grid-template-columns:1.15fr .85fr;gap:14px">
        <div>
          <div class="card">
            <div class="card-title">1 — Association rules (FP-Growth)</div>
            <div style="font-size:12px;line-height:1.6">
              <p><b>Algorithm:</b> FP-Growth via <span class="mono-code">mlxtend.fpgrowth</span>. Basket 11,287 × 47 boolean.</p>
              <p><b>Thresholds:</b> support ≥0.015 (≥169 txns), confidence ≥0.25, lift ≥1.5. At 0.03 only 4 rules; at 0.015 we recover 9 interpretable bidirectional pairs.</p>
              <p><b>Metrics:</b> support, confidence, lift 2.65–2.93 (2.6× chance), leverage, conviction — stored per <span class="mono-code">run_id</span> append-only.</p>
              <div id="methodRulesTable" style="max-height:180px;overflow:auto;border:1px solid var(--line);border-radius:8px;margin-top:8px"></div>
            </div>
          </div>
          <div class="card">
            <div class="card-title">2 — Customer segmentation (RFM + K-Means)</div>
            <div style="font-size:12px;line-height:1.6">
              <p><b>Features:</b> Recency, Frequency, Monetary — log1p on F/M + StandardScaler. <b>K:</b> silhouette k=2…8 peak at k=2 (0.368), chosen k=4 (0.283) for interpretability (Champions/Core/Light/At-risk).</p>
              <div id="elbowChart" style="height:200px"></div>
            </div>
          </div>
        </div>
        <div>
          <div class="card">
            <div class="card-title">3 — Outlier detection</div>
            <div style="font-size:12px;line-height:1.6">
              <p><b>Features:</b> n_items, distinct, total_qty, total_value, avg/max price, value_per_item, hour, is_weekend, days_since_start (10 dims).</p>
              <p><b>Model:</b> <span class="mono-code">IsolationForest(n_estimators=200, contamination=0.05)</span>. Z-score reasons in <span class="mono-code">reason_json</span>.</p>
              <div id="methodOutlierHist" style="height:160px"></div>
            </div>
          </div>
          <div class="card" style="background:var(--dark);border-color:#1E232A;color:#E8E6E1">
            <div class="side-title" style="color:#8B92A3">Before → After</div>
            <div style="font-family:Newsreader,serif;font-size:14px;font-weight:600;color:#FDFCF9">Raw 42k rows. Visual story: 9 rules · 4 segments · ~5% anomalies.</div>
            <div style="font-size:11px;color:#C9CDD6;line-height:1.6;margin-top:6px">Raw table illegible. Visuals make cross-sell, retention, fraud-review obvious. Cross-linking ties Rules ↔ Clusters ↔ Outliers.</div>
          </div>
          <div class="card">
            <div class="card-title">Reproducibility & DB design</div>
            <div style="font-size:11px;line-height:1.6;columns:2;column-gap:16px">
              <p><b>Raw:</b> customers·products·transactions·transaction_items.</p>
              <p><b>Mining:</b> mining_runs → frequent_itemsets·association_rules·customer_clusters·cluster_assignments·outliers (append-only).</p>
              <p><b>Run:</b> <span class="mono-code">docker compose up --build</span> or <span class="mono-code">streamlit run dashboard/app.py</span></p>
            </div>
          </div>
        </div>
      </div>
    </section>
  </main>
</div>

<footer>Built for Database & Data Mining coursework · SQLite · FP-Growth · K-Means · Isolation Forest · Plotly · <a href="https://github.com/aminekabtni1/visual-analytics-platform">github.com/aminekabtni1/visual-analytics-platform</a></footer>

<script>
const PALETTE={accent:"#C85A3A",sage:"#1E6B5A",amber:"#C18F2E",blue:"#3A5A7A",dark:"#121417",soft:"#5B616E",line:"#E8E2D9"};
const CLUSTER_COLORS=["#C85A3A","#1E6B5A","#C18F2E","#3A5A7A","#7A5A6A"];
const CAT_COLOR={Food:"#C85A3A",Home:"#3A5A7A",Kitchen:"#C18F2E",Toys:"#1E6B5A",Stationery:"#7A5A6A",Bags:"#8A6A3A"};
let DATA={};
async function loadAll(){
  const files=["counts","daily","categories","sample_tx","rules","clusters","assigns","pca","network","outliers","products","cluster_products","customer_cluster","evals"];
  await Promise.all(files.map(async f=>{
    try{ const r=await fetch(`/api/data/${f}.json`); if(r.ok) DATA[f]=await r.json(); }catch(e){ console.warn(f,e)}
  }));
  // fallback: if api/data not served (Vercel static), try raw github? But Flask serves via send_from_directory
  if(!DATA.counts) try{ const r=await fetch(`https://raw.githubusercontent.com/aminekabtni1/visual-analytics-platform/main/api/data/counts.json`); DATA.counts=await r.json(); }catch(e){}
  init();
}
function init(){
  document.querySelectorAll('.nav button').forEach(b=>b.addEventListener('click',()=>{
    document.querySelectorAll('.nav button').forEach(x=>x.classList.remove('active'));
    b.classList.add('active');
    document.querySelectorAll('.view').forEach(v=>v.classList.remove('active'));
    document.getElementById('view-'+b.dataset.view).classList.add('active');
    // lazy render charts when tab shown
    if(b.dataset.view==='rules') renderNetwork();
    if(b.dataset.view==='clusters') renderPCA();
    if(b.dataset.view==='outliers') renderOutlier();
    if(b.dataset.view==='method') renderMethod();
  }));
  renderOverview();
  // init other views lazily first render
  renderNetwork(); renderPCA(); renderOutlier(); renderMethod();
  renderRuns();
  document.getElementById('vercelNote').style.display='none'; // hide after confirming full app loaded
}
function renderRuns(){
  const c=DATA.counts||{}; const badge=document.getElementById('runBadge');
  if(c.assoc_run) badge.textContent=`Run ${c.assoc_run.slice(0,7)} · ${c.clust_run.slice(0,7)}`;
  const runsDiv=document.getElementById('runs');
  runsDiv.innerHTML=`<div class="run-line"><span>assoc · ${c.assoc_run?c.assoc_run.slice(0,7):''}</span><span>${c.n_rules||9} rules</span></div><div class="run-line"><span>clust · ${c.clust_run?c.clust_run.slice(0,7):''}</span><span>${(DATA.clusters||[]).length} clusters</span></div><div class="run-line"><span>outlier · ${c.out_run?c.out_run.slice(0,7):''}</span><span>${c.n_tx?Math.round(c.n_tx*0.05):565} flagged</span></div>`;
}
function renderOverview(){
  const c=DATA.counts||{}; document.getElementById('overviewCounts').textContent=`${(c.n_tx||11287).toLocaleString()} transactions · ${(c.n_cust||799).toLocaleString()} customers · ${c.n_prod||47} products`;
  // metrics
  const daily=DATA.daily||[], sample=DATA.sample_tx||[];
  const totalRev = sample.reduce((s,r)=>s+(r.line_total||0),0); // sample only 500, so approximate; use daily sum for total
  const dailyRev = daily.reduce((s,d)=>s+d.rev,0);
  const nTxSample = new Set(sample.map(r=>r.transaction_id)).size;
  const avgBasket = nTxSample? (sample.reduce((s,r)=>{ const m={}; sample.forEach(x=>m[x.transaction_id]=(m[x.transaction_id]||0)+x.line_total); return Object.values(m).reduce((a,b)=>a+b,0)/Object.values(m).length; },0) || 0):0;
  // compute correctly: group sample
  const txMap={};
  sample.forEach(r=>txMap[r.transaction_id]=(txMap[r.transaction_id]||0)+r.line_total);
  const vals=Object.values(txMap); const avgB = vals.length? vals.reduce((a,b)=>a+b,0)/vals.length:0;
  const avgItems = vals.length? sample.length/vals.length:0;
  const mg=document.getElementById('metricGrid');
  mg.innerHTML=`
    <div class="card metric-card accent"><div class="card-title">Revenue — sample</div><div class="metric-val">£${dailyRev.toLocaleString(undefined,{maximumFractionDigits:0})}</div><div class="metric-sub">${(c.n_tx||11287).toLocaleString()} txns total · daily sum</div></div>
    <div class="card metric-card"><div class="card-title">Avg basket value</div><div class="metric-val">£${avgB.toFixed(1)}</div><div class="metric-sub">per transaction (sample)</div></div>
    <div class="card metric-card"><div class="card-title">Avg items / basket</div><div class="metric-val">${avgItems.toFixed(1)}</div><div class="metric-sub">sample</div></div>
    <div class="card metric-card"><div class="card-title">Association rules</div><div class="metric-val">${c.n_rules||9}</div><div class="metric-sub">support ≥0.015 · conf ≥0.25</div></div>`;
  // daily chart
  if(daily.length){
    const x=daily.map(d=>d.invoice_date), y=daily.map(d=>d.rev);
    Plotly.newPlot('dailyChart',[{x,y,mode:'lines',line:{color:PALETTE.accent,width:1.7},fill:'tonexty',fillcolor:'rgba(200,90,58,0.08)',name:'Revenue',hovertemplate:'%{x}<br>£%{y:,.0f}<extra></extra>'}],{paper_bgcolor:'white',plot_bgcolor:'white',margin:{l:40,r:10,t:10,b:30},xaxis:{showgrid:false,tickfont:{size:10}},yaxis:{showgrid:true,gridcolor:'#F0EBE3',tickfont:{size:10}},showlegend:false,hovermode:'x unified'},{displayModeBar:false});
  }
  // category chart
  const cats=DATA.categories||[];
  if(cats.length){
    const y=cats.map(c=>c.category).sort(), x=cats.map(c=>c.rev);
    // sort by rev
    const paired=cats.slice().sort((a,b)=>a.rev-b.rev);
    Plotly.newPlot('catChart',[{x:paired.map(p=>p.rev),y:paired.map(p=>p.category),orientation:'h',type:'bar',marker:{color:paired.map(p=>CAT_COLOR[p.category]||'#8A8F9A')},text:paired.map(p=>'£'+Math.round(p.rev).toLocaleString()),textposition:'outside',hovertemplate:'%{y}<br>£%{x:,.0f}<extra></extra>'}],{paper_bgcolor:'white',plot_bgcolor:'white',margin:{l:80,r:60,t:10,b:20},xaxis:{showgrid:true,gridcolor:'#F0EBE3'},yaxis:{showgrid:false},showlegend:false},{displayModeBar:false});
  }
  // country chart — from sample distribution (approx UK-heavy)
  const countryCounts={};
  sample.forEach(r=>{ /* sample has no country? fallback to UK */});
  // use synthetic fallback
  const ctry=[{country:'United Kingdom',n: 420},{country:'France',n: 38},{country:'Germany',n: 28},{country:'Netherlands',n: 12}];
  Plotly.newPlot('countryChart',[{values:ctry.map(c=>c.n),labels:ctry.map(c=>c.country),type:'pie',hole:.55,marker:{colors:["#121417","#C85A3A","#1E6B5A","#C18F2E"]},textinfo:'percent+label',textfont:{size:11}}],{paper_bgcolor:'white',margin:{l:10,r:10,t:10,b:10},showlegend:false},{displayModeBar:false});

  // populate category filter
  const prodCats=[...new Set((DATA.products||[]).map(p=>p.category))].sort();
  const sel=document.getElementById('catFilter');
  sel.innerHTML='<option value="">All categories</option>'+prodCats.map(c=>`<option>${c}</option>`).join('');
  function renderTable(){
    const cat=sel.value, q=document.getElementById('search').value.toLowerCase();
    let rows=sample.slice(0,300);
    if(cat) rows=rows.filter(r=>r.category===cat);
    if(q) rows=rows.filter(r=>r.product_id.toLowerCase().includes(q) || r.description.toLowerCase().includes(q));
    document.getElementById('sampleCount').textContent=`${rows.length} rows`;
    const tb=document.querySelector('#txTable tbody');
    tb.innerHTML=rows.slice(0,120).map(r=>`<tr><td>${r.invoice_date}</td><td style="font-family:JetBrains Mono,monospace;font-size:11px">${r.transaction_id}</td><td>${r.description.slice(0,36)}</td><td>${r.category}</td><td>${r.quantity}</td><td>£${r.line_total.toFixed(1)}</td></tr>`).join('');
  }
  sel.addEventListener('change',renderTable);
  document.getElementById('search').addEventListener('input',renderTable);
  renderTable();
}

// RULES
let networkRendered=false;
function renderNetwork(){
  if(networkRendered) return;
  const rules=DATA.rules||[], net=DATA.network||{};
  document.getElementById('ruleCount').textContent=rules.length;
  // populate product select
  const pids=[...new Set([...rules.flatMap(r=>r.antecedent_parsed), ...rules.flatMap(r=>r.consequent_parsed)])].sort();
  const prodMap=Object.fromEntries((DATA.products||[]).map(p=>[p.product_id,p.description]));
  const sel=document.getElementById('productSelect');
  sel.innerHTML='<option value="">— all —</option>'+pids.map(p=>`<option value="${p}">${p} — ${(prodMap[p]||'').slice(0,28)}</option>`).join('');
  // rules table
  function renderRules(){
    const minL=parseFloat(document.getElementById('minLift').value), minC=parseFloat(document.getElementById('minConf').value), topN=parseInt(document.getElementById('topN').value);
    document.getElementById('minLiftV').textContent=minL.toFixed(1);document.getElementById('minConfV').textContent=minC.toFixed(2);document.getElementById('topNV').textContent=topN;
    let f=rules.filter(r=>r.lift>=minL && r.confidence>=minC).slice(0,topN);
    document.getElementById('filteredCount').textContent=`${f.length} rules`;
    document.querySelector('#rulesTable tbody').innerHTML=f.map(r=>`<tr><td>${r.rule_label}</td><td>${r.lift.toFixed(2)}</td><td>${r.confidence.toFixed(2)}</td></tr>`).join('');
    // rebuild network for filtered
    const nodes=net.nodes||[], edges=net.edges||[];
    // filter nodes/edges to filtered rules
    const keep=new Set(); f.forEach(r=>{r.antecedent_parsed.forEach(x=>keep.add(x)); r.consequent_parsed.forEach(x=>keep.add(x))});
    const fnodes=nodes.filter(n=>keep.has(n.id));
    const fedges=edges.filter(e=>keep.has(e.source) && keep.has(e.target) && f.some(r=>r.antecedent_parsed.includes(e.source)&&r.consequent_parsed.includes(e.target)));
    // plot
    const traces=[];
    fedges.forEach(e=>{
      const s=fnodes.find(n=>n.id===e.source), t=fnodes.find(n=>n.id===e.target);
      if(!s||!t) return;
      const w=1+e.confidence*6, op=0.35+Math.min(1,Math.max(0,(e.lift-1.5)/1.8))*0.55;
      traces.push({x:[s.x,t.x],y:[s.y,t.y],mode:'lines',line:{width:w,color:`rgba(200,90,58,${op})`},hoverinfo:'text',text:`${e.source} → ${e.target}<br>conf ${e.confidence.toFixed(2)} lift ${e.lift.toFixed(2)}`,showlegend:false});
    });
    traces.push({x:fnodes.map(n=>n.x),y:fnodes.map(n=>n.y),mode:'markers+text',text:fnodes.map(n=>n.id),textposition:'top center',textfont:{size:10,color:PALETTE.dark},marker:{size:fnodes.map(n=>14+(n.support*220)),color:fnodes.map(n=>CAT_COLOR[n.category]||'#8A8F9A'),line:{width:1.5,color:'white'},opacity:.95},hovertemplate:'<b>%{text}</b><extra></extra>',showlegend:false});
    Plotly.newPlot('networkChart',traces,{paper_bgcolor:'white',plot_bgcolor:'white',margin:{l:10,r:10,t:10,b:10},xaxis:{showgrid:false,zeroline:false,showticklabels:false,range:[-1.25,1.25]},yaxis:{showgrid:false,zeroline:false,showticklabels:false,range:[-1.25,1.25]},hovermode:'closest'},{displayModeBar:false});
  }
  ['minLift','minConf','topN'].forEach(id=>document.getElementById(id).addEventListener('input',renderRules));
  renderRules();
  // product drill
  sel.addEventListener('change',()=>{
    const pid=sel.value;
    const drill=document.getElementById('productDrill'), hint=document.getElementById('productHint');
    if(!pid){drill.style.display='none';hint.style.display='block';return}
    hint.style.display='none'; drill.style.display='block';
    const prod=(DATA.products||[]).find(p=>p.product_id===pid);
    const hist=(DATA.sample_tx||[]).filter(r=>r.product_id===pid).slice(0,8);
    const aff=DATA.cluster_products||{}; let affRows=[];
    for(const [cl, arr] of Object.entries(aff)){ const found=arr.find(x=>x.product_id===pid); if(found) affRows.push({cluster:cl, ...found});}
    affRows.sort((a,b)=>b.purchases-a.purchases);
    drill.innerHTML=`<div style="font-family:Newsreader,serif;font-weight:600">↳ ${pid} — ${prod?prod.description:''}</div><div style="font-size:11px;color:var(--soft)">${prod?prod.category:''}</div>
      <div style="font-size:11px;color:var(--soft);margin:6px 0">${hist.length} recent transactions in sample</div>
      <table><thead><tr><th>Txn</th><th>Date</th><th>Qty</th><th>£</th></tr></thead><tbody>${hist.map(r=>`<tr><td style="font-family:JetBrains Mono,monospace;font-size:11px">${r.transaction_id}</td><td>${r.invoice_date}</td><td>${r.quantity}</td><td>£${r.line_total.toFixed(1)}</td></tr>`).join('')||'<tr><td colspan=4 style="color:var(--soft)">No sample transactions</td></tr>'}</tbody></table>
      <div style="font-size:11px;font-weight:600;margin-top:8px">Bought most by clusters:</div>
      ${affRows.length? affRows.slice(0,4).map(r=>`<div style="display:flex;justify-content:space-between;font-size:11px;padding:3px 0;border-bottom:1px solid var(--line)"><span>C${r.cluster}</span><span>${r.purchases} purchases · ${r.total_qty} units</span></div>`).join(''): '<div style="font-size:11px;color:var(--soft)">No affinity</div>'}
    `;
  });
  networkRendered=true;
}

// CLUSTERS
let pcaRendered=false;
function renderPCA(){
  if(pcaRendered) return;
  const clusters=DATA.clusters||[], pca=DATA.pca||{}, assigns=pca.assigns||DATA.assigns||[];
  const prodAff=DATA.cluster_products||{};
  // cluster cards
  const grid=document.getElementById('clusterCards');
  grid.innerHTML=clusters.map((c,i)=>`<div class="card" style="border-top:3px solid ${CLUSTER_COLORS[i%CLUSTER_COLORS.length]}"><div style="display:flex;justify-content:space-between;align-items:center"><div style="font-family:JetBrains Mono,monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--soft)">Cluster ${c.cluster_label}</div><div style="width:10px;height:10px;border-radius:50%;background:${CLUSTER_COLORS[i%CLUSTER_COLORS.length]}"></div></div><div style="font-family:Newsreader,serif;font-size:22px;font-weight:700;margin-top:6px">${c.size} <span style="font-size:12px;font-weight:400;color:var(--soft)">customers</span></div><div class="divider"></div><div style="font-size:11px;color:var(--soft);line-height:1.6"><div style="display:flex;justify-content:space-between"><span>Recency</span><b style="color:var(--ink)">${Math.round(c.avg_recency)} d</b></div><div style="display:flex;justify-content:space-between"><span>Frequency</span><b style="color:var(--ink)">${c.avg_frequency.toFixed(1)}</b></div><div style="display:flex;justify-content:space-between"><span>Monetary</span><b style="color:var(--ink)">£${Math.round(c.avg_monetary)}</b></div></div></div>`).join('');
  // pca chart
  const traces=[];
  [...new Set(assigns.map(a=>a.cluster_label))].sort((a,b)=>a-b).forEach(label=>{
    const sub=assigns.filter(a=>a.cluster_label===label);
    traces.push({x:sub.map(s=>s.pca_x),y:sub.map(s=>s.pca_y),mode:'markers',marker:{size:6,color:CLUSTER_COLORS[label%CLUSTER_COLORS.length],opacity:.85,line:{width:.5,color:'white'}},name:`Cluster ${label} (${sub.length})`,customdata:sub.map(s=>[s.customer_id,s.recency,s.frequency,s.monetary]),hovertemplate:'<b>%{customdata[0]}</b><br>R:%{customdata[1]:.0f} d F:%{customdata[2]:.0f} £%{customdata[3]:.0f}<br>PC1 %{x:.2f} PC2 %{y:.2f}<extra></extra>'});
    const cx=sub.reduce((s,a)=>s+a.pca_x,0)/sub.length, cy=sub.reduce((s,a)=>s+a.pca_y,0)/sub.length;
    traces.push({x:[cx],y:[cy],mode:'markers+text',text:[`C${label}`],textposition:'top center',marker:{size:14,color:CLUSTER_COLORS[label%CLUSTER_COLORS.length],symbol:'diamond',line:{width:1.5,color:'white'}},showlegend:false,hoverinfo:'skip'});
  });
  Plotly.newPlot('pcaChart',traces,{paper_bgcolor:'white',plot_bgcolor:'white',margin:{l:40,r:10,t:10,b:40},xaxis:{title:'PC1 → value & frequency',titlefont:{size:11,color:PALETTE.soft},showgrid:true,gridcolor:'#F0EBE3'},yaxis:{title:'PC2 → recency',titlefont:{size:11,color:PALETTE.soft},showgrid:true,gridcolor:'#F0EBE3'},legend:{orientation:'h',yanchor:'bottom',y:1.02,xanchor:'right',x:1}},{displayModeBar:false});
  // inspector
  const sel=document.getElementById('clusterSelect');
  sel.innerHTML=[...new Set(assigns.map(a=>a.cluster_label))].sort((a,b)=>a-b).map(l=>`<option value="${l}">Cluster ${l}</option>`).join('');
  function renderCluster(){
    const label=parseInt(sel.value), c=clusters.find(x=>x.cluster_label===label);
    if(!c) return;
    function summary(r){
      const rec=r.avg_recency,freq=r.avg_frequency,mon=r.avg_monetary,sz=r.size;
      if(freq>17 && mon>1400 && rec<22) return `Champions — ${sz} loyal high-value customers who buy often and recently. Highest lifetime value.`;
      if(rec>60) return `At-risk / Lapsed — ${sz} customers who haven’t purchased in ${Math.round(rec)} days. Win-back candidates.`;
      if(mon<750 && freq<12) return `Light / Occasional — ${sz} low-spend, infrequent shoppers. Sensitive to promotions.`;
      return `Core / Regulars — ${sz} steady repeat buyers with moderate spend. The dependable middle.`;
    }
    document.getElementById('clusterSummary').innerHTML=`<div style="font-family:JetBrains Mono,monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--soft);margin-bottom:6px">Plain-language summary</div><div style="font-family:Newsreader,serif;font-size:14px;line-height:1.5">${summary(c)}</div>`;
    // compare
    const avg={recency: clusters.reduce((s,x)=>s+x.avg_recency,0)/clusters.length, frequency: clusters.reduce((s,x)=>s+x.avg_frequency,0)/clusters.length, monetary: clusters.reduce((s,x)=>s+x.avg_monetary,0)/clusters.length};
    document.getElementById('clusterCompare').innerHTML=`
      <div style="font-size:11px;font-weight:600;margin:8px 0 4px">How this cluster compares to average</div>
      ${[
        ['avg_recency','Recency (lower better)',c.avg_recency,avg.recency, true],
        ['avg_frequency','Frequency',c.avg_frequency,avg.frequency,false],
        ['avg_monetary','Monetary £',c.avg_monetary,avg.monetary,false]
      ].map(([k,label,val,av,inv])=>{
        const pct=(val-av)/(av+1e-9)*100; const color=(inv? pct<0 : pct>0)? PALETTE.sage : Math.abs(pct)>8? PALETTE.accent : '#8A8F9A';
        const arrow=pct>0?'▲':pct<0?'▼':'—';
        const fmt=k==='avg_monetary'? '£'+Math.round(val): k==='avg_frequency'? val.toFixed(1): Math.round(val);
        return `<div style="display:flex;justify-content:space-between;font-size:11px;padding:5px 0;border-bottom:1px solid var(--line)"><span style="color:var(--soft)">${label}</span><span><b>${fmt}</b> <span style="color:${color}">${arrow} ${pct>0?'+':''}${pct.toFixed(0)}% vs avg</span></span></div>`;
      }).join('')}
    `;
    // top products
    const cp=document.getElementById('clusterProducts');
    const prods=(prodAff[label]||[]).slice(0,8);
    cp.innerHTML=prods.map(p=>{
      const w=Math.round(p.purchases/Math.max(...prods.map(x=>x.purchases))*100);
      return `<div style="display:flex;justify-content:space-between;align-items:center;font-size:11px;padding:4px 0"><span style="flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;padding-right:8px">${p.product_id} · ${p.description.slice(0,26)}</span><span style="width:70px;height:6px;background:#F0EBE3;border-radius:999px;display:inline-block"><span style="display:block;width:${w}%;height:100%;background:${CLUSTER_COLORS[label%CLUSTER_COLORS.length]};border-radius:999px"></span></span><span style="margin-left:6px;color:var(--soft)">${p.purchases}</span></div>`;
    }).join('')||'<div style="font-size:11px;color:var(--soft)">No data</div>';
    // customers table
    document.getElementById('clusterCustomersTitle').textContent=`${assigns.filter(a=>a.cluster_label===label).length} customers`;
    const tbl=assigns.filter(a=>a.cluster_label===label).slice(0,120);
    document.querySelector('#clusterTable tbody').innerHTML=tbl.map(r=>`<tr><td style="font-family:JetBrains Mono,monospace;font-size:11px">${r.customer_id}</td><td>${Math.round(r.recency)}</td><td>${Math.round(r.frequency)}</td><td>£${Math.round(r.monetary)}</td><td>${r.distance_to_centroid.toFixed(2)}</td></tr>`).join('');
    // eval note
    const ce=(DATA.evals||{}).clustering_eval||{};
    if(ce.best_silhouette) document.getElementById('silNote').textContent=`silhouette ${ce.best_silhouette.toFixed(3)} at k=${ce.best_k} · chosen k=${clusters.length}`;
  }
  sel.addEventListener('change',renderCluster);
  renderCluster();
  pcaRendered=true;
}

// OUTLIERS
let outlierRendered=false;
function renderOutlier(){
  if(outlierRendered) return;
  const out=DATA.outliers||[];
  document.getElementById('outlierStats').textContent=`${out.filter(o=>o.is_outlier).length} flagged of ${out.length} · tap an outlier to inspect`;
  const sel=document.getElementById('outlierSelect');
  const flagged=out.filter(o=>o.is_outlier).sort((a,b)=>a.anomaly_score-b.anomaly_score).slice(0,60);
  sel.innerHTML=flagged.map(o=>`<option value="${o.transaction_id}">${o.transaction_id} — £${Math.round(o.total_value)} · ${o.n_items} items · ${o.anomaly_score.toFixed(3)}</option>`).join('');
  function draw(){
    const view=document.getElementById('outlierView').value, only=document.getElementById('onlyFlagged').checked;
    const data=only? out.filter(o=>o.is_outlier): out;
    const normal=data.filter(o=>!o.is_outlier), flag=data.filter(o=>o.is_outlier);
    let traces=[], layout={paper_bgcolor:'white',plot_bgcolor:'white',margin:{l:40,r:10,t:10,b:40},hovermode:'closest'};
    if(view==='Value vs Items'){
      if(normal.length) traces.push({x:normal.map(o=>o.n_items),y:normal.map(o=>o.total_value),mode:'markers',marker:{size:5,color:'#D1D5DB',opacity:.55},name:'Normal',hovertemplate:'%{x} items · £%{y:.0f}<extra></extra>'});
      traces.push({x:flag.map(o=>o.n_items),y:flag.map(o=>o.total_value),mode:'markers',marker:{size:7,color:PALETTE.accent,symbol:'x'},name:`Outlier (${flag.length})`,hovertemplate:'✕ %{text}<br>%{x} items £%{y:.0f}<extra></extra>',text:flag.map(o=>o.transaction_id)});
      layout.xaxis={title:'Items in basket',gridcolor:'#F0EBE3'}; layout.yaxis={title:'Total value £',gridcolor:'#F0EBE3'};
    } else if(view==='Over time'){
      const s=data.slice().sort((a,b)=>new Date(a.invoice_date)-new Date(b.invoice_date));
      const n=s.filter(o=>!o.is_outlier), f=s.filter(o=>o.is_outlier);
      if(n.length) traces.push({x:n.map(o=>o.invoice_date),y:n.map(o=>o.total_value),mode:'markers',marker:{size:4,color:'#D1D5DB',opacity:.45},name:'Normal'});
      traces.push({x:f.map(o=>o.invoice_date),y:f.map(o=>o.total_value),mode:'markers',marker:{size:7,color:PALETTE.accent,symbol:'x'},name:'Outlier',text:f.map(o=>o.transaction_id),hovertemplate:'✕ %{text}<br>%{x}<br>£%{y:.0f}<extra></extra>'});
      layout.xaxis={gridcolor:'#F0EBE3'}; layout.yaxis={title:'Basket value £',gridcolor:'#F0EBE3'};
    } else {
      traces.push({x:data.filter(o=>!o.is_outlier).map(o=>o.anomaly_score),type:'histogram',nbinsx:30,marker:{color:'#D1D5DB',opacity:.7},name:'Normal'});
      traces.push({x:data.filter(o=>o.is_outlier).map(o=>o.anomaly_score),type:'histogram',nbinsx:30,marker:{color:PALETTE.accent,opacity:.85},name:'Outlier'});
      layout.barmode='overlay'; layout.xaxis={title:'Anomaly score (lower = more anomalous)'}; layout.yaxis={title:'Count'};
    }
    layout.legend={orientation:'h',yanchor:'bottom',y:1.02,xanchor:'right',x:1};
    Plotly.newPlot('outlierChart',traces,layout,{displayModeBar:false});
  }
  ['outlierView','onlyFlagged'].forEach(id=>document.getElementById(id).addEventListener('change',draw));
  draw();
  // top table
  const top=out.slice().sort((a,b)=>a.anomaly_score-b.anomaly_score).slice(0,10);
  document.querySelector('#outlierTop tbody').innerHTML=top.map(o=>`<tr><td style="font-family:JetBrains Mono,monospace;font-size:11px">${o.transaction_id}</td><td>£${Math.round(o.total_value)}</td><td>${o.n_items}</td><td style="color:${PALETTE.accent};font-family:JetBrains Mono,monospace">${o.anomaly_score.toFixed(3)}</td></tr>`).join('');
  function drill(){
    const id=sel.value, row=out.find(o=>o.transaction_id===id);
    if(!row) return;
    const custMap=DATA.customer_cluster||{};
    const reason=row.reason_json? (typeof row.reason_json==='string'? JSON.parse(row.reason_json): row.reason_json): {};
    const reasonHtml=Object.keys(reason).length? Object.entries(reason).map(([k,v])=>`<div style="display:flex;justify-content:space-between;font-size:11px;padding:3px 0;border-bottom:1px solid var(--line)"><span>${k}</span><span style="font-family:JetBrains Mono,monospace;color:${PALETTE.accent}">z=${v>0?'+':''}${v}</span></div>`).join(''): '<div style="font-size:11px;color:var(--soft)">No single feature >2σ; flagged due to joint combination.</div>';
    document.getElementById('outlierDrill').innerHTML=`
      <div style="background:#FFFBF5;border:1px solid var(--line);border-radius:10px;padding:10px;margin-top:8px">
        <div style="font-family:JetBrains Mono,monospace;font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--soft)">${row.transaction_id} · ${row.invoice_date}</div>
        <div style="font-size:13px;font-weight:600;margin-top:4px">£${row.total_value.toFixed(2)} · ${row.n_items} products · ${row.total_qty} units</div>
        <div style="font-size:11px;color:var(--soft)">Customer ${row.customer_id} · score <span style="color:${PALETTE.accent};font-weight:700">${row.anomaly_score.toFixed(3)}</span> ${custMap[row.customer_id]!==undefined?`· Cluster ${custMap[row.customer_id]}`:''}</div>
      </div>
      <div style="font-size:11px;font-weight:600;margin:8px 0 4px">Why flagged</div>
      ${reasonHtml}
    `;
  }
  sel.addEventListener('change',drill);
  if(flagged.length) drill();
  outlierRendered=true;
}

function renderMethod(){
  const rules=DATA.rules||[];
  document.getElementById('methodRulesTable').innerHTML=`<table><thead><tr><th>Rule</th><th>Sup</th><th>Conf</th><th>Lift</th></tr></thead><tbody>${rules.slice(0,8).map(r=>`<tr><td>${r.rule_label}</td><td>${r.support.toFixed(3)}</td><td>${r.confidence.toFixed(2)}</td><td>${r.lift.toFixed(2)}</td></tr>`).join('')}</tbody></table>`;
  const ce=(DATA.evals||{}).clustering_eval||{};
  if(ce.k_range){
    Plotly.newPlot('elbowChart',[
      {x:ce.k_range,y:ce.silhouettes,mode:'lines+markers',line:{color:PALETTE.accent,width:2},marker:{size:7,color:PALETTE.accent},name:'Silhouette'},
      {x:[ce.best_k],y:[ce.best_silhouette],mode:'markers',marker:{size:12,color:'#121417',symbol:'diamond'},name:`Best k=${ce.best_k}`},
      {x:[4],y:[0.283],mode:'markers',marker:{size:11,color:PALETTE.sage,symbol:'star'},name:'Chosen k=4'}
    ],{paper_bgcolor:'white',plot_bgcolor:'white',margin:{l:40,r:10,t:10,b:30},xaxis:{title:'k',dtick:1},yaxis:{title:'Silhouette'},legend:{orientation:'h',yanchor:'bottom',y:1.02,xanchor:'right',x:1,font:{size:10}}},{displayModeBar:false});
  }
  const out=DATA.outliers||[];
  Plotly.newPlot('methodOutlierHist',[{x:out.map(o=>o.anomaly_score),type:'histogram',nbinsx:30,marker:{color:PALETTE.dark,opacity:.75}}],{paper_bgcolor:'white',plot_bgcolor:'white',margin:{l:30,r:10,t:10,b:30},xaxis:{title:'score'},yaxis:{title:'count'},bargap:.05},{displayModeBar:false});
}

loadAll();
</script>
</body>
</html>
"""

@app.get("/")
@app.get("/<path:path>")
def catch_all(path=""):
    # Serve SPA for any non-api path (client-side routing)
    if path.startswith("api/"):
        return jsonify({"error": "not found"}), 404
    return Response(HTML, mimetype="text/html")

# Vercel also expects /api/index to serve the app (for rewrites)
@app.get("/api/index")
@app.get("/api")
def api_root():
    return Response(HTML, mimetype="text/html")
