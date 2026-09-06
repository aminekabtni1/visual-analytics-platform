"""
Vercel Python entrypoint.

Streamlit cannot run on Vercel's serverless Python runtime (it needs a
long-running Tornado server). This lightweight Flask landing page makes
`vercel build` succeed and gives visitors a polished project overview,
screenshots, and correct deploy instructions (Streamlit Cloud / Render).

The full interactive dashboard (Plotly + NetworkX + cross-linked views)
runs locally via `streamlit run dashboard/app.py` or on Streamlit Cloud.
"""
from flask import Flask, Response

app = Flask(__name__)

# Use raw GitHub URLs so images work without local static serving on Vercel
BASE = "https://raw.githubusercontent.com/aminekabtni1/visual-analytics-platform/main"
HTML = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Visual Analytics Platform — Market Basket & Customer Pattern Mining</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
  :root{{--bg:#FDFCF9;--paper:#FFFFFF;--ink:#121417;--soft:#5B616E;--line:#E8E2D9;--accent:#C85A3A;--sage:#1E6B5A;--amber:#C18F2E;--blue:#3A5A7A;--dark:#0F1115;}}
  *{{box-sizing:border-box}} body{{margin:0;font-family:Inter,system-ui,sans-serif;background:var(--bg);color:var(--ink);}}
  a{{color:var(--accent);text-decoration:none}} a:hover{{text-decoration:underline}}
  .wrap{{max-width:1120px;margin:0 auto;padding:0 22px}}
  /* header */
  .topbar{{background:var(--dark);color:#E8E6E1;padding:14px 0 13px;border-bottom:1px solid #1E232A;position:sticky;top:0;z-index:10}}
  .topbar .wrap{{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}}
  .brand{{font-family:Newsreader,serif;font-weight:700;letter-spacing:-.02em;font-size:17px}} .brand span{{color:#8B92A3;font-family:JetBrains Mono,monospace;font-size:9px;letter-spacing:.16em;text-transform:uppercase;margin-left:8px;vertical-align:middle}}
  .pill{{font-family:JetBrains Mono,monospace;font-size:11px;letter-spacing:.02em;border:1px solid #2A303C;background:#1A1E23;color:#C9CDD6;border-radius:999px;padding:6px 10px}}
  .pill.accent{{background:var(--accent);border-color:var(--accent);color:white;font-weight:700}}
  /* hero */
  .hero{{padding:34px 0 18px}} .eyebrow{{font-family:JetBrains Mono,monospace;font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--soft);margin-bottom:10px}}
  h1{{font-family:Newsreader,serif;font-size:38px;line-height:1.02;letter-spacing:-.03em;margin:0 0 10px}} h1 em{{font-style:normal;color:var(--accent)}}
  .sub{{font-size:15px;line-height:1.6;color:var(--soft);max-width:780px}}
  .cta{{display:flex;gap:10px;margin-top:18px;flex-wrap:wrap}}
  .btn{{font-size:13px;font-weight:600;border-radius:10px;padding:10px 14px;border:1px solid var(--line);display:inline-flex;align-items:center;gap:7px}}
  .btn.primary{{background:var(--ink);color:white;border-color:var(--ink)}} .btn.ghost{{background:var(--paper)}}
  .callout{{margin-top:16px;background:#FFF3ED;border:1px solid #F0D5C8;border-radius:12px;padding:12px 14px;font-size:12.5px;line-height:1.6;color:#5B3A2E}}
  .callout strong{{color:var(--accent)}}
  /* cards */
  .grid{{display:grid;grid-template-columns:1.15fr .85fr;gap:16px;margin-top:18px}} @media(max-width:900px){{.grid{{grid-template-columns:1fr}} h1{{font-size:30px}}}}
  .card{{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:16px 18px;box-shadow:0 1px 2px rgba(16,24,40,.04)}}
  .card-title{{font-family:JetBrains Mono,monospace;font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--soft);margin-bottom:8px}}
  .metric{{font-family:Newsreader,serif;font-size:26px;font-weight:700}} .mono{{font-family:JetBrains Mono,monospace;font-size:11px;color:var(--soft)}}
  .kvs{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:16px}} @media(max-width:700px){{.kvs{{grid-template-columns:repeat(2,1fr)}}}}
  /* shots */
  .shots{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px}} @media(max-width:900px){{.shots{{grid-template-columns:1fr}}}}
  .shot img{{width:100%;height:auto;border:1px solid var(--line);border-radius:10px;background:white}}
  .shot figcaption{{font-size:11px;color:var(--soft);margin-top:6px;line-height:1.5}}
  .er img{{width:100%;border:1px solid var(--line);border-radius:12px;background:white}}
  /* deploy steps */
  .steps{{counter-reset:step}} .steps li{{list-style:none;counter-increment:step;padding:10px 0 10px 36px;position:relative;border-bottom:1px solid #F0EBE3;font-size:13px;line-height:1.6}} .steps li:before{{content:counter(step);position:absolute;left:0;top:11px;width:24px;height:24px;border-radius:50%;background:var(--ink);color:white;font-family:JetBrains Mono,monospace;font-size:11px;font-weight:700;display:grid;place-items:center}}
  code{{font-family:JetBrains Mono,monospace;background:#F8F5F0;border:1px solid var(--line);border-radius:6px;padding:1px 5px;font-size:12px}}
  .annotation{{font-size:12px;color:var(--soft);border-left:2px solid #D6CFC2;padding-left:10px;line-height:1.5;margin-top:10px}}
  footer{{margin:26px 0 22px;font-size:11px;color:#8B92A3;text-align:center}}
</style>
</head>
<body>
<div class="topbar"><div class="wrap">
  <div class="brand">◉ Basket & Pattern Lab <span>Retail Mining · Visual Analytics</span></div>
  <div style="display:flex;gap:8px;flex-wrap:wrap">
    <a class="pill" href="https://github.com/aminekabtni1/visual-analytics-platform">GitHub</a>
    <span class="pill accent">Interactive app → Streamlit Cloud</span>
  </div>
</div></div>

<div class="wrap hero">
  <div class="eyebrow">Database · Data Mining · Visual Analytics — coursework & portfolio</div>
  <h1>Visual Analytics Platform for <em>Market Basket & Customer Pattern Mining</em></h1>
  <p class="sub">Applies FP-Growth, RFM+K-Means, and Isolation Forest to retail transactions, stores raw data <b>and</b> every mining run in a normalized relational DB, and makes the patterns genuinely comprehensible — interactive network graph, PCA cluster map, and outlier drill-downs, not tables of numbers.</p>

  <div class="cta">
    <a class="btn primary" href="https://share.streamlit.io/">↗ Deploy on Streamlit Cloud</a>
    <a class="btn ghost" href="https://github.com/aminekabtni1/visual-analytics-platform">View source →</a>
    <a class="btn ghost" href="https://github.com/aminekabtni1/visual-analytics-platform#setup--run">Local setup docs</a>
  </div>

  <div class="callout">
    <strong>Vercel note:</strong> Streamlit needs a long-running Python server — it cannot run on Vercel’s serverless Python runtime. This page is a lightweight landing that makes <code>vercel build</code> pass. The <b>full interactive dashboard</b> (Plotly network, PCA scatter, cross-linked drill-downs) runs on <a href="https://share.streamlit.io/">Streamlit Community Cloud</a>, Render, or Docker (<code>docker compose up --build</code> → <code>localhost:8501</code>). See deploy steps below.
  </div>

  <div class="kvs">
    <div class="card"><div class="card-title">Transactions</div><div class="metric">11,287</div><div class="mono">42,173 line items · 799 customers</div></div>
    <div class="card"><div class="card-title">Association rules</div><div class="metric">9</div><div class="mono">FP-Growth · support 0.015 · lift 2.65–2.93</div></div>
    <div class="card"><div class="card-title">Customer segments</div><div class="metric">4</div><div class="mono">RFM · K-Means · PCA projection</div></div>
    <div class="card"><div class="card-title">Flagged anomalies</div><div class="metric">~5%</div><div class="mono">Isolation Forest · 565 / 11k</div></div>
  </div>

  <div class="grid">
    <div class="card">
      <div class="card-title">Why the build failed — and the fix</div>
      <div style="font-size:13px;line-height:1.65">
        Vercel scans for <code>app.py</code> / <code>api/index.py</code> etc. Your original repo had only <code>dashboard/app.py</code> (a Streamlit entrypoint), so Vercel threw <code>Error: No python entrypoint found</code>. This landing page at <code>api/index.py</code> satisfies Vercel’s check and explains the Streamlit/Vercel mismatch. It does <b>not</b> replace the dashboard — deploy the dashboard where Streamlit is supported.
      </div>
      <div class="annotation">The dashboard’s Flask/Serverless port would require rewriting the React/Plotly layer and losing Streamlit’s session state & cross-linking — not worth it for a portfolio that already runs perfectly on Streamlit Cloud.</div>
    </div>
    <div class="card">
      <div class="card-title">Correct deploy targets</div>
      <ol class="steps" style="margin:0;padding:0">
        <li><b>Streamlit Cloud</b> — <code>share.streamlit.io → New app → aminekabtni1/visual-analytics-platform → dashboard/app.py</code></li>
        <li><b>Render / Railway / Fly.io</b> — connect GitHub; <code>Dockerfile</code> bakes data + mining runs, serves on <code>8501</code></li>
        <li><b>Local / Docker</b> — <code>pip install -r requirements.txt && streamlit run dashboard/app.py</code> or <code>docker compose up --build</code></li>
      </ol>
    </div>
  </div>

  <div class="card" style="margin-top:16px">
    <div class="card-title">Project screenshots (from real DB data)</div>
    <div class="shots">
      <figure class="shot"><img loading="lazy" src="{BASE}/assets/screenshots/01_overview.png" alt="Overview"/><figcaption><b>Overview — Raw & Sales.</b> Revenue & transactions over time + category mix. Filters drive every view.</figcaption></figure>
      <figure class="shot"><img loading="lazy" src="{BASE}/assets/screenshots/02_rules.png" alt="Rules"/><figcaption><b>Rules — Lift.</b> Network graph (nodes=products, edge width=confidence, color=lift) — primary view, table is secondary.</figcaption></figure>
      <figure class="shot"><img loading="lazy" src="{BASE}/assets/screenshots/03_clusters.png" alt="Clusters"/><figcaption><b>Clusters — PCA of RFM.</b> 4 archetypes (Champions/Core/Light/At-risk) with diamond centroids; plain-language summaries.</figcaption></figure>
      <figure class="shot"><img loading="lazy" src="{BASE}/assets/screenshots/04_outliers.png" alt="Outliers"/><figcaption><b>Outliers — Value vs Items.</b> Isolation Forest flags; drill-down shows <code>reason_json</code> z-scores.</figcaption></figure>
    </div>
  </div>

  <div class="card er" style="margin-top:16px">
    <div class="card-title">ER diagram — raw (terracotta) vs mining (sage), traceable by mining_runs(run_id)</div>
    <img loading="lazy" src="{BASE}/assets/er_diagram.png" alt="ER diagram"/>
    <div class="annotation">Mining schema is append-only; every rerun inserts a new <code>mining_runs</code> row — results are never overwritten. See <code>database/schema.sql</code>.</div>
  </div>

  <footer>Built for Database & Data Mining coursework · SQLite · FP-Growth · K-Means · Isolation Forest · Streamlit · Plotly · NetworkX · <a href="https://github.com/aminekabtni1/visual-analytics-platform">github.com/aminekabtni1/visual-analytics-platform</a></footer>
</div>
</body>
</html>
"""

@app.get("/")
@app.get("/<path:path>")
def catch_all(path=""):
    return Response(HTML, mimetype="text/html")

# Vercel also probes /api/index directly
@app.get("/api/index")
def api_index():
    return Response(HTML, mimetype="text/html")

# Health for Vercel
@app.get("/health")
def health():
    return {"ok": True, "app": "visual-analytics-platform", "note": "Streamlit dashboard runs on Streamlit Cloud / Render, not Vercel serverless"}
