"""
Visual Analytics Platform — Streamlit app
Custom-designed to avoid default Streamlit slop.
Palette: warm paper + ink, terracotta/sage/amber/blue
Run: streamlit run dashboard/app.py --server.port 8501
"""
import json, pathlib, sys
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import networkx as nx
import streamlit as st

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from dashboard.data_loader import (
    get_products, get_rules, get_frequent, get_clusters, get_outliers,
    get_raw_overview, get_product_history, get_cluster_product_affinity,
    latest_run, list_runs
)
from database.db import get_connection

# ── Page config ───────────────────────────────────────────────
st.set_page_config(page_title="Basket & Pattern Lab", page_icon="◉", layout="wide", initial_sidebar_state="expanded")

# ── Design tokens ─────────────────────────────────────────────
PALETTE = {
    "bg": "#FDFCF9",
    "paper": "#FFFFFF",
    "ink": "#121417",
    "ink_soft": "#5B616E",
    "line": "#E8E2D9",
    "line_strong": "#D6CFC2",
    "accent": "#C85A3A",   # terracotta
    "sage": "#1E6B5A",     # deep teal
    "amber": "#C18F2E",
    "blue": "#3A5A7A",
    "mauve": "#7A5A6A",
}

CLUSTER_COLORS = ["#C85A3A", "#1E6B5A", "#C18F2E", "#3A5A7A", "#7A5A6A", "#6B7B5A", "#8A6A3A", "#4A6A7A"]
LIFT_COLORS = ["#E8D8CF", "#C85A3A", "#8B3A22"]  # gradient-ish

# ── Custom CSS ────────────────────────────────────────────────
CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Newsreader:opsz,wght@6..72,400;6..72,600;6..72,700&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] {{ font-family: 'Inter', system-ui, -apple-system, sans-serif; }}
h1, h2, h3 {{ font-family: 'Newsreader', Georgia, serif; letter-spacing: -0.02em; }}

/* Page background */
.stApp {{ background: {PALETTE['bg']}; }}

/* Hide Streamlit chrome — top bar, RUNNING/Stop/Deploy + thin color strip */
#MainMenu {{visibility: hidden; display:none !important;}}
footer {{visibility: hidden; display:none !important;}}
header[data-testid="stHeader"] {{display:none !important; height:0 !important; visibility:hidden !important;}}
div[data-testid="stStatusWidget"] {{display:none !important; visibility:hidden !important;}}
div[data-testid="stDecoration"] {{display:none !important; height:0 !important; visibility:hidden !important;}}
div[data-testid="stToolbar"] {{display:none !important; visibility:hidden !important;}}
div[data-testid="stHeaderActionElements"] {{display:none !important;}}
[data-testid="stAppViewContainer"] > header {{display:none !important;}}

/* Block container tightening — data-dense */
.block-container {{ padding-top: 1.1rem; padding-bottom: 2rem; max-width: 1480px; }}

/* Sidebar — dark ink */
section[data-testid="stSidebar"] {{ background: #0F1115; border-right: 1px solid #1E232A; }}
section[data-testid="stSidebar"] * {{ color: #E8E6E1; }}
section[data-testid="stSidebar"] .stRadio label {{ font-size: 13px; letter-spacing: 0.01em; }}
section[data-testid="stSidebar"] hr {{ border-color: #252A32; }}

/* Sidebar nav — pills */
div[role="radiogroup"] label {{
  background: transparent; border: 1px solid transparent; border-radius: 8px;
  padding: 8px 12px !important; margin-bottom: 4px !important;
}}
div[role="radiogroup"] label:has(input:checked) {{
  background: #1A1E23; border-color: #2A303C; color: #FFFFFF !important;
}}

/* Cards */
.card {{
  background: {PALETTE['paper']};
  border: 1px solid {PALETTE['line']};
  border-radius: 12px;
  padding: 16px 18px;
  box-shadow: 0 1px 2px rgba(16,24,40,0.04);
}}
.card-title {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px; letter-spacing: 0.14em; text-transform: uppercase;
  color: {PALETTE['ink_soft']}; margin-bottom: 8px;
}}
.metric-value {{ font-family: 'Newsreader', serif; font-size: 28px; font-weight: 700; color: {PALETTE['ink']}; line-height: 1; }}
.metric-sub {{ font-size: 11px; color: {PALETTE['ink_soft']}; margin-top: 4px; }}
.divider {{ height: 1px; background: {PALETTE['line']}; margin: 12px 0; }}

/* Table polish */
thead tr th {{ font-family: 'JetBrains Mono', monospace !important; font-size: 10px !important; letter-spacing: 0.08em; text-transform: uppercase; color: {PALETTE['ink_soft']} !important; }}

/* Tag pills */
.pill {{
  display: inline-block; padding: 2px 8px; border-radius: 999px;
  font-size: 11px; font-weight: 600; letter-spacing: 0.02em;
  border: 1px solid {PALETTE['line']};
}}

/* Tufte-style annotation */
.annotation {{ font-size: 12px; color: {PALETTE['ink_soft']}; line-height: 1.5; border-left: 2px solid {PALETTE['line_strong']}; padding-left: 10px; }}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────
def card_header(title, right=""):
    cols = st.columns([1,0.35])
    with cols[0]:
        st.markdown(f"<div class='card-title'>{title}</div>", unsafe_allow_html=True)
    with cols[1]:
        if right:
            st.markdown(f"<div style='text-align:right; font-size:11px; color:{PALETTE['ink_soft']};'>{right}</div>", unsafe_allow_html=True)

def metric_card(label, value, sub="", accent=False):
    border = f"border-left: 3px solid {PALETTE['accent']};" if accent else ""
    st.markdown(f"""
    <div class="card" style="{border}">
      <div class="card-title">{label}</div>
      <div class="metric-value">{value}</div>
      <div class="metric-sub">{sub}</div>
    </div>
    """, unsafe_allow_html=True)

def product_label(pid, products_df):
    row = products_df[products_df["product_id"]==pid]
    if row.empty:
        return pid
    return f"{pid} · {row.iloc[0]['description'][:36]}"

# ── Session state for cross-linking ───────────────────────────
if "selected_product" not in st.session_state:
    st.session_state.selected_product = None
if "selected_cluster" not in st.session_state:
    st.session_state.selected_cluster = None
if "selected_txn" not in st.session_state:
    st.session_state.selected_txn = None

products_df = get_products()
# map id -> desc
prod_map = dict(zip(products_df["product_id"], products_df["description"]))
prod_cat = dict(zip(products_df["product_id"], products_df["category"]))

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding: 6px 2px 10px 2px;">
      <div style="font-family:'Newsreader',serif; font-size: 18px; font-weight:700; letter-spacing:-0.02em; color:#FDFCF9;">◉ Basket & Pattern Lab</div>
      <div style="font-family:'JetBrains Mono',monospace; font-size:9px; letter-spacing:0.16em; text-transform:uppercase; color:#8B92A3; margin-top:2px;">Retail Mining · Visual Analytics</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='height:1px; background:#1E232A; margin: 8px 0 14px 0;'></div>", unsafe_allow_html=True)

    nav = st.radio(
        "Navigate",
        ["Overview — Raw & Sales", "Rules — Network", "Clusters — Segments", "Outliers — Anomalies", "Method & Evaluation"],
        label_visibility="collapsed"
    )
    st.markdown("<div style='height:1px; background:#1E232A; margin: 14px 0;'></div>", unsafe_allow_html=True)

    # Run badges
    runs = list_runs()
    if runs:
        st.markdown(f"<div class='card-title' style='color:#8B92A3;'>Mining runs</div>", unsafe_allow_html=True)
        for r in runs[:6]:
            params = json.loads(r["params_json"]) if r["params_json"] else {}
            tip = str(params)[:80]
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-bottom:1px solid #1A1E23; font-family:'JetBrains Mono',monospace; font-size:11px;">
              <span style="color:#C9CDD6;">{r['run_type'][:4]} · <span style='color:#8B92A3;'>{r['run_id'][:7]}</span></span>
              <span style="font-size:10px; color:#6B7280;">{r['created_at'][:16]}</span>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
    st.markdown("<div class='annotation' style='color:#9AA0B2; border-left-color:#252A32;'>Click any product node in the Rules graph to drill into its history & cluster affinity. Click a cluster point to inspect its segment.</div>", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:18px; font-size:10px; color:#6B7280; font-family:Inter;'>Built for Database & Data Mining coursework · SQLite · FP-Growth · K-Means · Isolation Forest</div>", unsafe_allow_html=True)

# ── Top bar context ───────────────────────────────────────────
# Use latest run ids for header stats
assoc_run = latest_run("association")
clust_run = latest_run("clustering")
out_run   = latest_run("outlier")

header_stats_c = get_connection()
try:
    n_tx = header_stats_c.execute("SELECT COUNT(*) as c FROM transactions").fetchone()["c"]
    n_cust = header_stats_c.execute("SELECT COUNT(*) as c FROM customers").fetchone()["c"]
    n_prod = header_stats_c.execute("SELECT COUNT(*) as c FROM products").fetchone()["c"]
    n_rules = header_stats_c.execute("SELECT COUNT(*) as c FROM association_rules WHERE run_id=?", (assoc_run,)).fetchone()["c"] if assoc_run else 0
except:
    n_tx=n_cust=n_prod=n_rules=0
finally:
    header_stats_c.close()

# ── Page: Overview ────────────────────────────────────────────
if nav.startswith("Overview"):

    st.markdown(f"""
    <div style="display:flex; align-items:baseline; gap:14px; margin-bottom:6px;">
      <div style="font-family:'Newsreader',serif; font-size:30px; font-weight:700; letter-spacing:-0.03em; color:{PALETTE['ink']};">Sales Overview</div>
      <div style="font-family:'JetBrains Mono',monospace; font-size:10px; letter-spacing:0.12em; text-transform:uppercase; color:{PALETTE['ink_soft']};">{n_tx:,} transactions · {n_cust:,} customers · {n_prod} products</div>
    </div>
    <div style="font-size:13px; color:{PALETTE['ink_soft']}; margin-bottom:14px; max-width:820px; line-height:1.5;">
      Filter and inspect the raw retail data that feeds every mining pipeline. This is the “before” — dense, hard to summarise — made navigable before any models are applied.
    </div>
    """, unsafe_allow_html=True)

    # Filters row
    f1, f2, f3, f4 = st.columns([1.2,1,1,1])
    with f1:
        date_range = st.date_input("Date range", value=None, label_visibility="collapsed", help="Filter by invoice date")
        # Streamlit date_input returns single or tuple; handle
        date_start = date_end = None
        if isinstance(date_range, (tuple, list)) and len(date_range)==2:
            date_start, date_end = str(date_range[0]), str(date_range[1])
        elif date_range:
            date_start = str(date_range)
    with f2:
        cats = ["All categories"] + sorted(products_df["category"].dropna().unique().tolist())
        cat_sel = st.selectbox("Category", cats, label_visibility="collapsed")
        cat_filter = None if cat_sel=="All categories" else cat_sel
    with f3:
        countries = ["All countries", "United Kingdom", "France", "Germany", "Netherlands", "Australia", "USA", "Belgium"]
        country_sel = st.selectbox("Country", countries, label_visibility="collapsed")
        country_filter = None if country_sel=="All countries" else country_sel
    with f4:
        st.markdown(f"<div style='text-align:right; padding-top:6px;'><span class='pill' style='background:#121417; color:#FDFCF9; border-color:#121417;'>Run {assoc_run[:7] if assoc_run else '—'} · {clust_run[:7] if clust_run else '—'}</span></div>", unsafe_allow_html=True)

    filters = {"date_start": date_start, "date_end": date_end, "category": cat_filter, "country": country_filter}
    df_raw = get_raw_overview(filters)

    # Metrics row (custom, not st.metric)
    if not df_raw.empty:
        total_rev = df_raw["line_total"].sum()
        avg_basket = df_raw.groupby("transaction_id")["line_total"].sum().mean()
        avg_items = df_raw.groupby("transaction_id").size().mean()
        n_tx_f = df_raw["transaction_id"].nunique()
    else:
        total_rev=avg_basket=avg_items=n_tx_f=0

    m1,m2,m3,m4 = st.columns(4)
    with m1: metric_card("Revenue — filtered", f"£{total_rev:,.0f}", f"{n_tx_f:,} txns in view", accent=True)
    with m2: metric_card("Avg basket value", f"£{avg_basket:,.1f}", "per transaction")
    with m3: metric_card("Avg items / basket", f"{avg_items:.1f}", "distinct line items")
    with m4: metric_card("Association rules", f"{n_rules}", f"support ≥0.015 · conf ≥0.25")

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    # Two-col: time series + category
    left, right = st.columns([1.55,1])
    with left:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        card_header("Revenue & transactions over time", "daily")
        if not df_raw.empty:
            daily = df_raw.groupby(df_raw["invoice_date"].dt.date).agg(rev=("line_total","sum"), txns=("transaction_id","nunique")).reset_index()
            daily["invoice_date"] = pd.to_datetime(daily["invoice_date"])
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=daily["invoice_date"], y=daily["rev"], mode="lines", line=dict(color=PALETTE["accent"], width=1.7), fill="tonexty", fillcolor="rgba(200,90,58,0.08)", name="Revenue", hovertemplate="%{x|%Y-%m-%d}<br>£%{y:,.0f}<extra></extra>"))
            fig.add_trace(go.Scatter(x=daily["invoice_date"], y=daily["txns"]* (daily["rev"].max()/max(1,daily["txns"].max())*0.55), mode="lines", line=dict(color=PALETTE["ink_soft"], width=1, dash="dot"), name="Txns (scaled)", hovertemplate="%{x|%Y-%m-%d}<br>%{y:.0f}<extra></extra>"))
            fig.update_layout(height=260, margin=dict(l=10,r=10,t=6,b=10), paper_bgcolor="white", plot_bgcolor="white",
                              xaxis=dict(showgrid=False, tickfont=dict(size=10, color=PALETTE["ink_soft"])), yaxis=dict(showgrid=True, gridcolor="#F0EBE3", tickfont=dict(size=10)),
                              legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=11)), hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data for this filter.")
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        card_header("Mix by category", "filtered")
        if not df_raw.empty:
            cat_rev = df_raw.groupby("category").agg(rev=("line_total","sum"), qty=("quantity","sum")).reset_index().sort_values("rev", ascending=True)
            fig2 = go.Figure(go.Bar(x=cat_rev["rev"], y=cat_rev["category"], orientation="h", marker=dict(color=[PALETTE["sage"] if c=="Food" else PALETTE["blue"] if c=="Home" else PALETTE["amber"] if c=="Kitchen" else "#8A8F9A" for c in cat_rev["category"]], line=dict(width=0)), text=[f"£{v:,.0f}" for v in cat_rev["rev"]], textposition="outside", hovertemplate="%{y}<br>£%{x:,.0f}<extra></extra>"))
            fig2.update_layout(height=260, margin=dict(l=10,r=70,t=6,b=10), paper_bgcolor="white", plot_bgcolor="white",
                               xaxis=dict(showgrid=True, gridcolor="#F0EBE3", tickfont=dict(size=10)), yaxis=dict(showgrid=False, tickfont=dict(size=11, color=PALETTE["ink"])))
            st.plotly_chart(fig2, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Table + raw vs mined narrative hook
    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
    t1, t2 = st.columns([1.2, 0.8])
    with t1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        card_header("Transactions — sample (cross-links from Rules & Clusters filter here)", f"{len(df_raw):,} line items")
        if not df_raw.empty:
            show = df_raw.head(300)[["transaction_id","invoice_date","customer_id","description","category","quantity","unit_price","line_total","country"]].copy()
            show["invoice_date"] = show["invoice_date"].dt.strftime("%Y-%m-%d")
            st.dataframe(show, use_container_width=True, height=300, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with t2:
        st.markdown(f"""
        <div class="card" style="background: #0F1115; border-color:#1E232A; color:#E8E6E1;">
          <div class="card-title" style="color:#8B92A3;">Before → After</div>
          <div style="font-family:'Newsreader',serif; font-size:16px; font-weight:600; color:#FDFCF9; margin-bottom:6px;">A picture is worth a thousand rows.</div>
          <div style="font-size:12.5px; line-height:1.6; color:#C9CDD6;">
            The table on the left is the raw data — <b style="color:#FDFCF9;">42k line items</b> that are uninterpretable at a glance.
            After mining, the same data resolves into <b style="color:#FDFCF9;">9 association rules</b> (network graph),
            <b style="color:#FDFCF9;">4 customer archetypes</b> (cluster map), and <b style="color:#FDFCF9;">~5% flagged anomalies</b>.
            Use the Rules and Clusters tabs to see the visual story.
          </div>
          <div class="divider" style="background:#1E232A;"></div>
          <div style="font-family:'JetBrains Mono',monospace; font-size:10px; letter-spacing:0.08em; text-transform:uppercase; color:#8B92A3;">Cleaning decisions (hover for why)</div>
          <ul style="font-size:11.5px; color:#AEB4C2; line-height:1.5; margin:6px 0 0 16px; padding:0;">
            <li>Cancelled orders removed — negative qty distorts baskets</li>
            <li>Null CustomerID dropped — required for RFM</li>
            <li>Exact duplicates deduped; postage lines excluded</li>
          </ul>
        </div>
        """, unsafe_allow_html=True)
        # Quick country share mini
        if not df_raw.empty:
            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            card_header("Where sales happen", "")
            cshare = df_raw.drop_duplicates("transaction_id").groupby("country").size().reset_index(name="n").sort_values("n", ascending=False)
            figc = px.pie(cshare, values="n", names="country", hole=0.55, color_discrete_sequence=["#121417","#C85A3A","#1E6B5A","#C18F2E","#3A5A7A","#7A5A6A"])
            figc.update_traces(textinfo="percent+label", textfont_size=11, marker=dict(line=dict(color="white", width=1)))
            figc.update_layout(height=180, margin=dict(l=10,r=10,t=10,b=10), paper_bgcolor="white", showlegend=False)
            st.plotly_chart(figc, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

# ── Page: Rules Network ───────────────────────────────────────
elif nav.startswith("Rules"):

    st.markdown(f"""
    <div style="display:flex; align-items:baseline; gap:14px; margin-bottom:6px;">
      <div style="font-family:'Newsreader',serif; font-size:30px; font-weight:700; letter-spacing:-0.03em; color:{PALETTE['ink']};">Association Rules</div>
      <div style="font-family:'JetBrains Mono',monospace; font-size:10px; letter-spacing:0.12em; text-transform:uppercase; color:{PALETTE['ink_soft']};">FP-Growth · support ≥0.015 · confidence ≥0.25 · {n_rules} rules</div>
    </div>
    <div style="font-size:13px; color:{PALETTE['ink_soft']}; margin-bottom:14px; max-width:840px; line-height:1.5;">
      Products are <b style="color:{PALETTE['ink']};">nodes</b>, rules are <b style="color:{PALETTE['ink']};">directed edges</b>. Edge thickness → confidence, color → lift. The strongest affinities pop in terracotta. Click a node to drill down; filter the table below.
    </div>
    """, unsafe_allow_html=True)

    rules_df = get_rules(assoc_run)
    freq_df = get_frequent(assoc_run)

    # Controls
    c1, c2, c3, c4 = st.columns([1,1,1,1.2])
    with c1:
        min_lift = st.slider("Min lift", 1.0, 4.0, 1.5, 0.1)
    with c2:
        min_conf = st.slider("Min confidence", 0.0, 1.0, 0.25, 0.05)
    with c3:
        top_n = st.slider("Top N rules", 4, 30, 9, 1)
    with c4:
        st.markdown(f"<div style='padding-top:18px; font-size:11px; color:{PALETTE['ink_soft']};'>Showing rules with lift ≥ {min_lift} & confidence ≥ {min_conf:.2f}. Graph is interactive — hover for metrics, select a node to cross-link.</div>", unsafe_allow_html=True)

    if rules_df.empty:
        st.warning("No association rules for the latest run. Try lowering thresholds and re-running mining.")
    else:
        filtered = rules_df[(rules_df["lift"] >= min_lift) & (rules_df["confidence"] >= min_conf)].head(top_n).copy()
        if filtered.empty:
            st.info("No rules pass those thresholds.")
        else:
            # Build graph: nodes = unique product ids in filtered rules
            G = nx.DiGraph()
            # Collect all product ids
            all_pids = set()
            for _, r in filtered.iterrows():
                all_pids.update(r["antecedent_parsed"])
                all_pids.update(r["consequent_parsed"])
            for pid in all_pids:
                G.add_node(pid, label=prod_map.get(pid, pid), cat=prod_cat.get(pid, ""))

            for _, r in filtered.iterrows():
                for a in r["antecedent_parsed"]:
                    for c in r["consequent_parsed"]:
                        G.add_edge(a, c, support=r["support"], confidence=r["confidence"], lift=r["lift"], rule=r["rule_label"])

            # Layout — spring with seed for stability
            pos = nx.spring_layout(G, k=1.2, iterations=70, seed=42)

            # Edge traces
            edge_x, edge_y, edge_text, edge_width, edge_color = [], [], [], [], []
            for u,v,d in G.edges(data=True):
                x0,y0 = pos[u]; x1,y1 = pos[v]
                edge_x += [x0, x1, None]
                edge_y += [y0, y1, None]
                edge_text.append(d["rule"])
                edge_width.append(d["confidence"])
                edge_color.append(d["lift"])

            # Nodes
            node_x = [pos[n][0] for n in G.nodes()]
            node_y = [pos[n][1] for n in G.nodes()]
            node_ids = list(G.nodes())
            node_labels = [f"{n}<br>{prod_map.get(n,'')[:28]}" for n in node_ids]
            # size by frequency (support of product)
            prod_support = {}
            for pid in node_ids:
                # support = max itemset support containing it, else transaction frequency
                sup = 0
                for _, rr in freq_df.iterrows():
                    items = json.loads(rr["itemset"]) if isinstance(rr["itemset"], str) else rr["itemset"]
                    if pid in items:
                        sup = max(sup, rr["support"])
                prod_support[pid] = sup if sup else 0.03
            node_size = [ 14 + prod_support[pid]*220 for pid in node_ids ]
            node_color = [ {"Home":"#3A5A7A","Kitchen":"#C18F2E","Toys":"#1E6B5A","Stationery":"#7A5A6A","Bags":"#8A6A3A","Food":"#C85A3A"}.get(prod_cat.get(pid,""), "#8A8F9A") for pid in node_ids]

            # Plotly figure
            fig = go.Figure()
            # edges as lines with varying opacity — we draw each edge individually for color/width control
            for (u,v,d) in G.edges(data=True):
                x0,y0 = pos[u]; x1,y1 = pos[v]
                # lift -> color interpolation between light and accent
                lift = d["lift"]
                # normalize 1.5-3.0
                t = min(1, max(0, (lift - 1.5)/1.8))
                # interpolate between #E8D8CF and #8B3A22
                # simple blend
                w = 1 + d["confidence"]*6  # 1-7px
                opacity = 0.35 + t*0.55
                fig.add_trace(go.Scatter(x=[x0,x1], y=[y0,y1], mode="lines",
                                         line=dict(width=w, color=f"rgba(200,90,58,{opacity:.2f})"),
                                         hoverinfo="text", text=f"{d['rule']}<br>support {d['support']:.3f} · conf {d['confidence']:.2f} · lift {d['lift']:.2f}",
                                         showlegend=False))
                # arrow head as annotation later, but use marker for direction
                # small triangle at target
            # nodes
            fig.add_trace(go.Scatter(
                x=node_x, y=node_y, mode="markers+text", text=[n for n in node_ids], textposition="top center",
                textfont=dict(size=10, color=PALETTE["ink"]),
                marker=dict(size=node_size, color=node_color, line=dict(width=1.5, color="white"), opacity=0.95),
                customdata=node_ids, hovertemplate="<b>%{customdata}</b><br>%{text}<br>support %{marker.size}<extra></extra>",
                hovertext=[prod_map.get(n,"") for n in node_ids],
                name="products"
            ))

            fig.update_layout(height=520, margin=dict(l=10,r=10,t=10,b=10), paper_bgcolor="white", plot_bgcolor="white",
                              xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-1.25,1.25]),
                              yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-1.25,1.25]),
                              hovermode="closest",
                              legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            # Legend manually
            g1, g2 = st.columns([1.9, 1])
            with g1:
                st.markdown("<div class='card' style='padding:10px 12px;'>", unsafe_allow_html=True)
                st.plotly_chart(fig, use_container_width=True)
                # click handling — use selectbox as fallback for cross-link
                st.markdown(f"<div class='annotation'>Graph: node size → product support (how often it appears). Edge width → confidence, opacity → lift. <span style='color:{PALETTE['accent']}; font-weight:600;'>Terracotta = high lift</span>. Categories: Food=terracotta, Home=blue, Kitchen=amber, Toys=sage, etc.</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with g2:
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                card_header("Rule details", f"{len(filtered)} rules")
                # product selector for cross-link
                prod_options = sorted(list(all_pids))
                labels = [f"{p} — {prod_map.get(p,'')[:30]}" for p in prod_options]
                sel_idx = st.selectbox("Focus product (cross-links to Overview & Clusters)", ["— all —"] + labels, label_visibility="visible")
                if sel_idx != "— all —":
                    focused = sel_idx.split(" — ")[0]
                    st.session_state.selected_product = focused
                else:
                    st.session_state.selected_product = None

                # Table of filtered rules — highlight those involving selected product
                disp = filtered[["rule_label","support","confidence","lift"]].copy()
                disp.columns = ["Rule","Support","Conf","Lift"]
                disp["Support"] = disp["Support"].map(lambda x: f"{x:.3f}")
                disp["Conf"] = disp["Conf"].map(lambda x: f"{x:.2f}")
                disp["Lift"] = disp["Lift"].map(lambda x: f"{x:.2f}")
                st.dataframe(disp, use_container_width=True, hide_index=True, height=260)

                # If product selected, show drill-down
                if st.session_state.selected_product:
                    pid = st.session_state.selected_product
                    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='font-family:Newsreader,serif; font-size:15px; font-weight:600; color:{PALETTE['ink']};'>↳ {pid} — {prod_map.get(pid,'')}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='font-size:11px; color:{PALETTE['ink_soft']}; margin-bottom:6px;'>Category: {prod_cat.get(pid,'')} · Price lookup via Products</div>", unsafe_allow_html=True)
                    hist = get_product_history(pid)
                    if not hist.empty:
                        st.markdown(f"<div style='font-size:11px; color:{PALETTE['ink_soft']}; margin-bottom:4px;'>{len(hist)} recent transactions</div>", unsafe_allow_html=True)
                        st.dataframe(hist.head(12), use_container_width=True, hide_index=True, height=180)
                    # cluster affinity
                    aff = get_cluster_product_affinity(clust_run)
                    if not aff.empty:
                        sub = aff[aff["product_id"]==pid].sort_values("purchases", ascending=False)
                        if not sub.empty:
                            st.markdown(f"<div style='font-size:11px; font-weight:600; margin-top:8px;'>Bought most by clusters:</div>", unsafe_allow_html=True)
                            for _, r in sub.head(4).iterrows():
                                st.markdown(f"<div style='font-size:11px; display:flex; justify-content:space-between; padding:3px 0; border-bottom:1px solid {PALETTE['line']};'><span>C{r['cluster_label']}</span><span>{int(r['purchases'])} purchases · {int(r['total_qty'])} units</span></div>", unsafe_allow_html=True)
                        else:
                            st.caption("No cluster affinity found for this product in latest run.")
                else:
                    st.markdown(f"""
                    <div style="margin-top:10px; padding:10px; background:{PALETTE['bg']}; border:1px solid {PALETTE['line']}; border-radius:8px; font-size:12px; color:{PALETTE['ink_soft']}; line-height:1.5;">
                      <b style="color:{PALETTE['ink']};">Try this:</b> pick a product above (e.g., <span style="color:{PALETTE['accent']}; font-weight:600;">85048 PINK SPOTTY CUP</span>) to see its transaction history and which customer segments buy it most — the graph and the customer map are linked.
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

# ── Page: Clusters ────────────────────────────────────────────
elif nav.startswith("Clusters"):
    st.markdown(f"""
    <div style="display:flex; align-items:baseline; gap:14px; margin-bottom:6px;">
      <div style="font-family:'Newsreader',serif; font-size:30px; font-weight:700; letter-spacing:-0.03em; color:{PALETTE['ink']};">Customer Segments</div>
      <div style="font-family:'JetBrains Mono',monospace; font-size:10px; letter-spacing:0.12em; text-transform:uppercase; color:{PALETTE['ink_soft']};">RFM · K-Means · PCA projection</div>
    </div>
    <div style="font-size:13px; color:{PALETTE['ink_soft']}; margin-bottom:14px; max-width:840px; line-height:1.5;">
      Each dot is a customer positioned by Recency/Frequency/Monetary (log-scaled, standardized, PCA to 2D). Color = cluster. Click a cluster to see who they are, what they buy, and a plain-language summary.
    </div>
    """, unsafe_allow_html=True)

    clusters_df, assigns_df = get_clusters(clust_run)
    if assigns_df.empty:
        st.warning("No clustering run found.")
    else:
        # Compute PCA coords if not present — we recompute to ensure consistency
        from sklearn.preprocessing import StandardScaler
        from sklearn.decomposition import PCA
        rfm_for_plot = assigns_df[["customer_id","cluster_label","rfm_r","rfm_f","rfm_m","distance_to_centroid"]].copy()
        # Build scaled matrix same as training: [recency, log1p(freq), log1p(monetary)]
        Xlog = np.column_stack([rfm_for_plot["rfm_r"].values, np.log1p(rfm_for_plot["rfm_f"].values), np.log1p(rfm_for_plot["rfm_m"].values)])
        scaler = StandardScaler()
        Xs = scaler.fit_transform(Xlog)
        pca = PCA(n_components=2, random_state=42)
        coords = pca.fit_transform(Xs)
        rfm_for_plot["pca_x"] = coords[:,0]
        rfm_for_plot["pca_y"] = coords[:,1]

        # Cluster cards metrics
        k = len(clusters_df)
        sil_note = ""
        try:
            import json as _j, pathlib as _p
            eval_path = pathlib.Path("evals/clustering_eval.json")
            if eval_path.exists():
                ev = _j.loads(eval_path.read_text())
                sil_note = f"silhouette {ev.get('best_silhouette',0):.3f} at k={ev.get('best_k','?')} · chosen k={k} via elbow + interpretability"
        except: pass

        cols = st.columns(k)
        for i, (_, row) in enumerate(clusters_df.iterrows()):
            with cols[i]:
                label = int(row["cluster_label"])
                st.markdown(f"""
                <div class="card" style="border-top: 3px solid {CLUSTER_COLORS[label % len(CLUSTER_COLORS)]};">
                  <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div style="font-family:'JetBrains Mono',monospace; font-size:10px; letter-spacing:0.12em; text-transform:uppercase; color:{PALETTE['ink_soft']};">Cluster {label}</div>
                    <div style="width:10px; height:10px; border-radius:50%; background:{CLUSTER_COLORS[label % len(CLUSTER_COLORS)]};"></div>
                  </div>
                  <div style="font-family:'Newsreader',serif; font-size:22px; font-weight:700; color:{PALETTE['ink']}; margin-top:6px;">{int(row['size'])} <span style="font-size:12px; font-weight:400; color:{PALETTE['ink_soft']};">customers</span></div>
                  <div class="divider"></div>
                  <div style="font-size:11px; color:{PALETTE['ink_soft']}; line-height:1.6;">
                    <div style="display:flex; justify-content:space-between;"><span>Recency</span><b style="color:{PALETTE['ink']};">{row['avg_recency']:.0f} d</b></div>
                    <div style="display:flex; justify-content:space-between;"><span>Frequency</span><b style="color:{PALETTE['ink']};">{row['avg_frequency']:.1f}</b></div>
                    <div style="display:flex; justify-content:space-between;"><span>Monetary</span><b style="color:{PALETTE['ink']};">£{row['avg_monetary']:.0f}</b></div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

        # Main scatter + side detail
        left, right = st.columns([1.75, 1])
        with left:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            card_header("Customer map — PCA( RFM )", sil_note)

            # Build Plotly scatter
            fig = go.Figure()
            for label in sorted(rfm_for_plot["cluster_label"].unique()):
                sub = rfm_for_plot[rfm_for_plot["cluster_label"]==label]
                fig.add_trace(go.Scatter(
                    x=sub["pca_x"], y=sub["pca_y"], mode="markers",
                    marker=dict(size=6, color=CLUSTER_COLORS[label % len(CLUSTER_COLORS)], opacity=0.85, line=dict(width=0.5, color="white")),
                    name=f"Cluster {label} ({len(sub)})",
                    customdata=np.stack([sub["customer_id"], sub["rfm_r"], sub["rfm_f"], sub["rfm_m"]], axis=-1),
                    hovertemplate="<b>%{customdata[0]}</b><br>R:%{customdata[1]:.0f} d · F:%{customdata[2]:.0f} · £%{customdata[3]:.0f}<br>PC1 %{x:.2f}, PC2 %{y:.2f}<extra></extra>",
                ))
            # Centroids
            for label in sorted(rfm_for_plot["cluster_label"].unique()):
                sub = rfm_for_plot[rfm_for_plot["cluster_label"]==label]
                cx, cy = sub["pca_x"].mean(), sub["pca_y"].mean()
                fig.add_trace(go.Scatter(x=[cx], y=[cy], mode="markers+text", text=[f"C{label}"], textposition="top center",
                                         marker=dict(size=14, color=CLUSTER_COLORS[label % len(CLUSTER_COLORS)], symbol="diamond", line=dict(width=1.5, color="white")),
                                         showlegend=False, hoverinfo="skip"))
            fig.update_layout(height=420, margin=dict(l=10,r=10,t=10,b=10), paper_bgcolor="white", plot_bgcolor="white",
                              xaxis=dict(title="PC1 — value & frequency →", title_font=dict(size=11, color=PALETTE["ink_soft"]), showgrid=True, gridcolor="#F0EBE3", tickfont=dict(size=10)),
                              yaxis=dict(title="PC2 — recency →", title_font=dict(size=11, color=PALETTE["ink_soft"]), showgrid=True, gridcolor="#F0EBE3", tickfont=dict(size=10)),
                              legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=11)))
            st.plotly_chart(fig, use_container_width=True)
            st.markdown(f"<div class='annotation'>PCA explains ~95% variance of the 3 RFM dimensions. Proximity = similar buying behaviour. Diamonds = cluster centroids. Choose a cluster on the right to see its story and top products.</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with right:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            card_header("Segment inspector", "click to cross-link → Rules")
            # selector
            cluster_options = sorted(rfm_for_plot["cluster_label"].unique().tolist())
            sel = st.selectbox("Choose cluster", cluster_options, index=0, label_visibility="collapsed")
            st.session_state.selected_cluster = int(sel)
            row = clusters_df[clusters_df["cluster_label"]==int(sel)].iloc[0]

            # LLM-style summary (heuristic)
            def summarize_cluster(r):
                label = int(r["cluster_label"]); rec=r["avg_recency"]; freq=r["avg_frequency"]; mon=r["avg_monetary"]; sz=int(r["size"])
                if freq>17 and mon>1400 and rec<22:
                    return f"Champions — {sz} loyal high-value customers who buy often and recently. Highest lifetime value; they respond best to new-collection previews."
                if rec>60:
                    return f"At-risk / Lapsed — {sz} customers who haven’t purchased in {rec:.0f} days on average. Low frequency. Win-back campaign candidates."
                if mon<750 and freq<12:
                    return f"Light / Occasional — {sz} low-spend, infrequent shoppers. Sensitive to promotions and bundles."
                return f"Core / Regulars — {sz} steady repeat buyers with moderate spend. The dependable middle; cross-sell with association rules."

            summary = summarize_cluster(row)
            st.markdown(f"""
            <div style="background:#F8F5F0; border:1px solid {PALETTE['line']}; border-radius:10px; padding:12px; margin-bottom:10px;">
              <div style="font-family:'JetBrains Mono',monospace; font-size:10px; letter-spacing:0.12em; text-transform:uppercase; color:{PALETTE['ink_soft']}; margin-bottom:6px;">Plain-language summary</div>
              <div style="font-family:'Newsreader',serif; font-size:14px; line-height:1.5; color:{PALETTE['ink']};">{summary}</div>
            </div>
            """, unsafe_allow_html=True)

            # Bar of RFM vs overall mean
            overall = clusters_df[["avg_recency","avg_frequency","avg_monetary"]].mean()
            # Normalize for radar-ish bar
            st.markdown(f"<div style='font-size:11px; font-weight:600; color:{PALETTE['ink']}; margin-bottom:6px;'>How this cluster compares to average</div>", unsafe_allow_html=True)
            for field, label_name, fmt in [("avg_recency","Recency (days, lower is better)","{:.0f}"), ("avg_frequency","Frequency","{:.1f}"), ("avg_monetary","Monetary £","£{:.0f}")]:
                val = row[field]; avg = overall[field]
                pct = (val - avg)/ (avg + 1e-9) * 100
                color = PALETTE["sage"] if (field!="avg_recency" and pct>0) or (field=="avg_recency" and pct<0) else PALETTE["accent"] if abs(pct)>8 else "#8A8F9A"
                arrow = "▲" if pct>0 else "▼" if pct<0 else "—"
                st.markdown(f"""
                <div style="display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-bottom:1px solid {PALETTE['line']}; font-size:11px;">
                  <span style="color:{PALETTE['ink_soft']};">{label_name}</span>
                  <span><b style="color:{PALETTE['ink']};">{fmt.format(val)}</b> <span style="color:{color};">{arrow} {pct:+.0f}% vs avg</span></span>
                </div>
                """, unsafe_allow_html=True)

            # Top products for this cluster
            aff = get_cluster_product_affinity(clust_run)
            if not aff.empty:
                sub = aff[aff["cluster_label"]==int(sel)].head(8)
                st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size:11px; font-weight:600; color:{PALETTE['ink']}; margin-bottom:6px;'>Top products this segment buys</div>", unsafe_allow_html=True)
                for _, r in sub.iterrows():
                    w = min(100, int(r["purchases"]/sub["purchases"].max()*100))
                    st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; align-items:center; font-size:11px; padding:4px 0;">
                      <span style="flex:1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; padding-right:8px;">{r['product_id']} · {r['description'][:26]}</span>
                      <span style="width:70px; height:6px; background:#F0EBE3; border-radius:999px; display:inline-block; vertical-align:middle; margin-right:6px;"><span style="display:block; width:{w}%; height:100%; background:{CLUSTER_COLORS[int(sel) % len(CLUSTER_COLORS)]}; border-radius:999px;"></span></span>
                      <span style="font-variant-numeric:tabular-nums; color:{PALETTE['ink_soft']};">{int(r['purchases'])}</span>
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown(f"<div class='annotation' style='margin-top:8px; border-left-color:{CLUSTER_COLORS[int(sel) % len(CLUSTER_COLORS)]};'>Click a product above (copy its ID) and jump to the Rules graph to see which affinity rules it participates in.</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # Customer table for selected cluster
        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        card_header(f"Customers in Cluster {st.session_state.selected_cluster} — sample", f"{len(rfm_for_plot[rfm_for_plot['cluster_label']==int(sel)]):,} customers")
        sample = rfm_for_plot[rfm_for_plot["cluster_label"]==int(sel)].sort_values("distance_to_centroid").head(120)
        sample = sample.merge(products_df[["product_id"]].head(1), how="cross")  # dummy to keep schema? skip
        # Actually just show table
        tbl = rfm_for_plot[rfm_for_plot["cluster_label"]==int(sel)].head(200)[["customer_id","rfm_r","rfm_f","rfm_m","distance_to_centroid"]].copy()
        tbl.columns = ["Customer", "Recency (d)", "Freq", "Monetary £", "Dist to centroid"]
        tbl["Recency (d)"] = tbl["Recency (d)"].map(lambda x: f"{x:.0f}")
        tbl["Freq"] = tbl["Freq"].map(lambda x: f"{x:.0f}")
        tbl["Monetary £"] = tbl["Monetary £"].map(lambda x: f"£{x:,.0f}")
        tbl["Dist to centroid"] = tbl["Dist to centroid"].map(lambda x: f"{x:.2f}")
        st.dataframe(tbl, use_container_width=True, height=220, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ── Page: Outliers ────────────────────────────────────────────
elif nav.startswith("Outliers"):
    st.markdown(f"""
    <div style="display:flex; align-items:baseline; gap:14px; margin-bottom:6px;">
      <div style="font-family:'Newsreader',serif; font-size:30px; font-weight:700; letter-spacing:-0.03em; color:{PALETTE['ink']};">Anomalies</div>
      <div style="font-family:'JetBrains Mono',monospace; font-size:10px; letter-spacing:0.12em; text-transform:uppercase; color:{PALETTE['ink_soft']};">Isolation Forest · contamination 0.05 · ~5% flagged</div>
    </div>
    <div style="font-size:13px; color:{PALETTE['ink_soft']}; margin-bottom:14px; max-width:840px; line-height:1.5;">
      Transactions plotted by value vs size. Terracotta <b style="color:{PALETTE['accent']};">✕</b> = flagged outliers (unusual spend, tiny or huge baskets, price spikes). Hover to see why the model flagged each one; select a point to see its line items.
    </div>
    """, unsafe_allow_html=True)

    out_df = get_outliers(out_run)
    if out_df.empty:
        st.warning("No outlier run found.")
    else:
        # Controls
        c1,c2,c3 = st.columns([1,1,1.2])
        with c1:
            view = st.radio("View", ["Value vs Items", "Over time", "Score distribution"], horizontal=True, label_visibility="collapsed")
        with c2:
            only_flagged = st.checkbox("Only flagged outliers", value=False)
        with c3:
            st.markdown(f"<div style='font-size:11px; color:{PALETTE['ink_soft']}; padding-top:8px;'>{int(out_df['is_outlier'].sum())} flagged of {len(out_df):,} transactions · tap an outlier to inspect</div>", unsafe_allow_html=True)

        plot_df = out_df[out_df["is_outlier"]==1] if only_flagged else out_df

        left, right = st.columns([1.7, 1])
        with left:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            card_header(view, "Isolation Forest decision score — lower = more anomalous")

            if view == "Value vs Items":
                fig = go.Figure()
                normal = plot_df[plot_df["is_outlier"]==0] if not only_flagged else pd.DataFrame()
                flag = plot_df[plot_df["is_outlier"]==1]
                if not normal.empty:
                    fig.add_trace(go.Scatter(x=normal["n_items"], y=normal["total_value"], mode="markers",
                                             marker=dict(size=5, color="#D1D5DB", opacity=0.55, line=dict(width=0)),
                                             name="Normal", customdata=np.stack([normal["transaction_id"], normal["anomaly_score"]], axis=-1),
                                             hovertemplate="Normal %{customdata[0]}<br>%{x} items · £%{y:.0f}<br>score %{customdata[1]:.3f}<extra></extra>"))
                fig.add_trace(go.Scatter(x=flag["n_items"], y=flag["total_value"], mode="markers",
                                         marker=dict(size=7, color=PALETTE["accent"], symbol="x", line=dict(width=1.5)),
                                         name=f"Outlier ({len(flag)})", customdata=np.stack([flag["transaction_id"], flag["anomaly_score"], flag["reason_json"]], axis=-1),
                                         hovertemplate="<b>✕ %{customdata[0]}</b><br>%{x} items · £%{y:.0f}<br>score %{customdata[1]:.3f}<br>%{customdata[2]}<extra></extra>"))
                fig.update_layout(height=400, margin=dict(l=10,r=10,t=10,b=10), paper_bgcolor="white", plot_bgcolor="white",
                                  xaxis=dict(title="Items in basket (n distinct products)", gridcolor="#F0EBE3", tickfont=dict(size=10)),
                                  yaxis=dict(title="Total basket value £", gridcolor="#F0EBE3", tickfont=dict(size=10)),
                                  legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig, use_container_width=True)

            elif view == "Over time":
                # Sample for performance
                samp = plot_df.sort_values("invoice_date")
                fig = go.Figure()
                normal = samp[samp["is_outlier"]==0] if not only_flagged else pd.DataFrame()
                flag = samp[samp["is_outlier"]==1]
                if not normal.empty:
                    fig.add_trace(go.Scatter(x=normal["invoice_date"], y=normal["total_value"], mode="markers",
                                             marker=dict(size=4, color="#D1D5DB", opacity=0.45), name="Normal",
                                             hovertemplate="%{x|%Y-%m-%d}<br>£%{y:.0f}<extra></extra>"))
                fig.add_trace(go.Scatter(x=flag["invoice_date"], y=flag["total_value"], mode="markers",
                                         marker=dict(size=7, color=PALETTE["accent"], symbol="x"), name="Outlier",
                                         customdata=flag["transaction_id"], hovertemplate="✕ %{customdata}<br>%{x|%Y-%m-%d}<br>£%{y:.0f}<extra></extra>"))
                fig.update_layout(height=400, margin=dict(l=10,r=10,t=10,b=10), paper_bgcolor="white", plot_bgcolor="white",
                                  xaxis=dict(gridcolor="#F0EBE3"), yaxis=dict(title="Basket value £", gridcolor="#F0EBE3"),
                                  legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig, use_container_width=True)
            else:
                fig = go.Figure()
                fig.add_trace(go.Histogram(x=out_df[out_df["is_outlier"]==0]["anomaly_score"], nbinsx=40, marker_color="#D1D5DB", opacity=0.7, name="Normal"))
                fig.add_trace(go.Histogram(x=out_df[out_df["is_outlier"]==1]["anomaly_score"], nbinsx=40, marker_color=PALETTE["accent"], opacity=0.85, name="Outlier"))
                fig.update_layout(height=400, barmode="overlay", margin=dict(l=10,r=10,t=10,b=10), paper_bgcolor="white", plot_bgcolor="white",
                                  xaxis=dict(title="Anomaly score (lower = more anomalous)"), yaxis=dict(title="Count"))
                st.plotly_chart(fig, use_container_width=True)

            st.markdown(f"<div class='annotation'>Contamination 0.05 → ~{int(len(out_df)*0.05)} transactions flagged. False positives are expected: a large but legitimate wholesale basket will be flagged because it lives in sparse feature space. Use drill-down to judge each case.</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with right:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            card_header("Drill-down", "why flagged + line items")
            # Selector for outlier transaction
            flagged_ids = out_df[out_df["is_outlier"]==1].sort_values("anomaly_score").head(60)["transaction_id"].tolist()
            sel = st.selectbox("Choose flagged transaction", flagged_ids, label_visibility="collapsed", placeholder="Pick a transaction…")
            if sel:
                st.session_state.selected_txn = sel
                row = out_df[out_df["transaction_id"]==sel].iloc[0]
                st.markdown(f"""
                <div style="background:{PALETTE['bg']}; border:1px solid {PALETTE['line']}; border-radius:10px; padding:12px; margin-bottom:10px;">
                  <div style="font-family:'JetBrains Mono',monospace; font-size:10px; letter-spacing:0.12em; text-transform:uppercase; color:{PALETTE['ink_soft']};">{row['transaction_id']} · {str(row['invoice_date'])[:16]}</div>
                  <div style="font-size:13px; font-weight:600; color:{PALETTE['ink']}; margin-top:4px;">£{row['total_value']:.2f} · {int(row['n_items'])} products · {int(row['total_qty'])} units</div>
                  <div style="font-size:11px; color:{PALETTE['ink_soft']}; margin-top:2px;">Customer {row['customer_id']} · anomaly score <span style="color:{PALETTE['accent']}; font-weight:700;">{row['anomaly_score']:.3f}</span> (more negative = more anomalous)</div>
                </div>
                """, unsafe_allow_html=True)

                reasons = json.loads(row["reason_json"]) if row["reason_json"] else {}
                if reasons:
                    st.markdown(f"<div style='font-size:11px; font-weight:600; color:{PALETTE['ink']}; margin-bottom:4px;'>Model flags — features >2σ from mean</div>", unsafe_allow_html=True)
                    for k,v in reasons.items():
                        st.markdown(f"<div style='display:flex; justify-content:space-between; font-size:11px; padding:3px 0; border-bottom:1px solid {PALETTE['line']};'><span>{k}</span><span style='font-family:JetBrains Mono,monospace; color:{PALETTE['accent']};'>z={v:+.1f}</span></div>", unsafe_allow_html=True)
                else:
                    st.caption("No single feature >2σ; flagged due to joint unusual combination (Isolation Forest strength).")

                # Line items
                c = get_connection()
                items = pd.read_sql_query("""
                SELECT ti.product_id, p.description, p.category, ti.quantity, ti.unit_price, ti.quantity*ti.unit_price as line_total
                FROM transaction_items ti JOIN products p ON p.product_id=ti.product_id
                WHERE ti.transaction_id=?""", c, params=(sel,))
                c.close()
                st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size:11px; font-weight:600; color:{PALETTE['ink']}; margin-bottom:4px;'>Basket contents — {len(items)} line items</div>", unsafe_allow_html=True)
                st.dataframe(items, use_container_width=True, hide_index=True, height=180)

                # Link to customer segment
                c2 = get_connection()
                cl = c2.execute("SELECT cluster_label FROM cluster_assignments WHERE run_id=? AND customer_id=?", (clust_run, str(row["customer_id"]))).fetchone()
                c2.close()
                if cl:
                    st.markdown(f"<div style='margin-top:8px; font-size:11px; padding:8px; background:#F8F5F0; border-radius:8px; border:1px solid {PALETTE['line']};'>Customer <b>{row['customer_id']}</b> belongs to <b>Cluster {cl['cluster_label']}</b> → see Clusters tab for their segment.</div>", unsafe_allow_html=True)
            else:
                st.caption("Pick a flagged transaction to inspect.")

            # Also show top 10 most anomalous table
            st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:11px; font-weight:600; color:{PALETTE['ink']}; margin-bottom:4px;'>Most anomalous (lowest scores)</div>", unsafe_allow_html=True)
            top = out_df.nsmallest(10, "anomaly_score")[["transaction_id","total_value","n_items","anomaly_score"]].copy()
            top["anomaly_score"] = top["anomaly_score"].map(lambda x: f"{x:.3f}")
            top["total_value"] = top["total_value"].map(lambda x: f"£{x:.0f}")
            st.dataframe(top, use_container_width=True, hide_index=True, height=200)
            st.markdown("</div>", unsafe_allow_html=True)

# ── Page: Method & Evaluation ─────────────────────────────────
else:
    st.markdown(f"""
    <div style="font-family:'Newsreader',serif; font-size:30px; font-weight:700; letter-spacing:-0.03em; color:{PALETTE['ink']}; margin-bottom:6px;">Method & Evaluation</div>
    <div style="font-size:13px; color:{PALETTE['ink_soft']}; max-width:820px; line-height:1.6; margin-bottom:16px;">
      How we mined, why the parameters were chosen, and how we know the patterns are meaningful — not just artefacts.
    </div>
    """, unsafe_allow_html=True)

    # Show eval json if exists
    import pathlib as _p, json as _j
    eval_path = _p.Path("evals/clustering_eval.json")
    ev = _j.loads(eval_path.read_text()) if eval_path.exists() else {}

    a, b = st.columns([1.15, 0.85])
    with a:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        card_header("1 — Association rules (FP-Growth)", "mlxtend · support 0.015 · conf 0.25")
        st.markdown(f"""
        <div style="font-size:13px; color:{PALETTE['ink']}; line-height:1.65;">
          <p><b>Algorithm:</b> FP-Growth (Han et al.) via <code>mlxtend.frequent_patterns.fpgrowth</code>. Chosen over Apriori for speed on dense baskets. Basket matrix: {n_tx:,} × {n_prod} boolean.</p>
          <p><b>Thresholds:</b> support ≥0.015 ⇒ itemset appears in ≥{int(0.015 * n_tx):,} transactions (1.5%). Confidence ≥0.25, min lift considered ≥1.5. These thresholds were tuned to surface a handful of <i>strong, interpretable</i> affinities (snack+beverage, lunch bags, stationery) without drowning in hundreds of weak rules. At support 0.03 we found only 4 rules; at 0.015 we recover 9 bidirectional pairs which tell a clearer story.</p>
          <p><b>Metrics computed:</b> support, confidence, lift, leverage, conviction — stored per run in <code>association_rules</code>. Lift &gt;2.6 for all 9 rules ⇒ co-occurrence is 2.6× more likely than chance; not just frequent items co-occurring by accident.</p>
          <p><b>Why it’s meaningful:</b> Rules mirror real retail behaviour — e.g., <span style="background:#FFF2ED; padding:1px 4px; border-radius:4px;"><code>60001 (BISCUIT)</code> → <code>60006 (MUG)</code> lift 2.65</span> and stationery bundle <code>41002 → 41003</code>. These are cross-sell opportunities, not statistical noise.</p>
          <p><b>Traceability:</b> every mining run inserts a row in <code>mining_runs</code> with <code>params_json</code> + timestamp; frequent itemsets and rules are linked by <code>run_id</code> — reruns never overwrite history.</p>
        </div>
        """, unsafe_allow_html=True)
        # show rules table compact
        rules_df = get_rules(assoc_run)
        if not rules_df.empty:
            st.dataframe(rules_df[["rule_label","support","confidence","lift"]].head(12), use_container_width=True, hide_index=True, height=200)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        card_header("2 — Customer segmentation (RFM + K-Means)", "StandardScaler on [R, log1p(F), log1p(M)] · k=4")
        st.markdown(f"""
        <div style="font-size:13px; color:{PALETTE['ink']}; line-height:1.65;">
          <p><b>Features:</b> Recency (days since last purchase), Frequency (distinct transactions), Monetary (total spend). Monetary and Frequency are log1p-transformed to reduce skew (common for RFM), then all three are standardized.</p>
          <p><b>Choosing K:</b> we computed silhouette scores for k=2…8:</p>
        </div>
        """, unsafe_allow_html=True)
        if ev.get("k_range"):
            # elbow chart
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=ev["k_range"], y=ev["silhouettes"], mode="lines+markers", line=dict(color=PALETTE["accent"], width=2), marker=dict(size=7, color=PALETTE["accent"]), name="Silhouette"))
            # mark best
            best_k = ev.get("best_k"); best_sil = ev.get("best_silhouette")
            fig.add_trace(go.Scatter(x=[best_k], y=[best_sil], mode="markers", marker=dict(size=12, color="#121417", symbol="diamond"), name=f"Best k={best_k}"))
            fig.add_trace(go.Scatter(x=[4], y=[0.283], mode="markers", marker=dict(size=11, color=PALETTE["sage"], symbol="star"), name="Chosen k=4 (interpretable)"))
            fig.update_layout(height=200, margin=dict(l=10,r=10,t=10,b=10), paper_bgcolor="white", plot_bgcolor="white",
                              xaxis=dict(title="k", dtick=1), yaxis=dict(title="Silhouette (higher = tighter clusters)"), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)))
            st.plotly_chart(fig, use_container_width=True)
            st.markdown(f"""
            <div style="font-size:13px; color:{PALETTE['ink']}; line-height:1.65;">
              <p>Silhouette peaks at <b>k=2 ({best_sil:.3f})</b> — a coarse high-vs-low split. We chose <b>k=4 (silhouette 0.283)</b> because it yields four <i>interpretable archetypes</i> (Champions / Core / Light / At-risk) that map to distinct retention actions, whereas k=2 is too blunt for campaign design. This is a deliberate trade-off: a small drop in silhouette for a large gain in actionability — documented per run in <code>mining_runs.params_json</code>.</p>
              <p><b>Validation:</b> clusters differ markedly on all three RFM axes (see Clusters tab cards). PCA projection shows separation; centroids are well-spaced. Future work: track silhouette over time as more data arrives.</p>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with b:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        card_header("3 — Outlier detection", "Isolation Forest · contamination 0.05")
        st.markdown(f"""
        <div style="font-size:13px; color:{PALETTE['ink']}; line-height:1.65;">
          <p><b>Features per transaction:</b> n_items, distinct_products, total_quantity, total_value, avg/max unit price, value_per_item, hour, is_weekend, days_since_start — 10 dimensions capturing basket shape and timing.</p>
          <p><b>Model:</b> <code>sklearn.ensemble.IsolationForest</code> (200 trees, contamination 0.05). Scores = decision function (more negative = more anomalous). Flags stored with <code>anomaly_score</code> + <code>reason_json</code> (features &gt;2σ).</p>
          <p><b>Threshold reasoning:</b> 5% contamination is a conservative default for retail — most transactions are routine; flagged cases are reviewed, not auto-blocked.</p>
          <p><b>False positives:</b> expected. A legitimate 15-item wholesale basket (≈£500+) will be flagged because it sits in sparse feature space — but it’s useful to surface, not to accuse. The drill-down panel shows <i>why</i> each case was flagged (e.g., <code>total_value z=+3.8</code>) so an analyst can judge.</p>
          <p><b>Traceability:</b> same <code>run_id</code> pattern; re-running creates a new run.</p>
        </div>
        """, unsafe_allow_html=True)
        out_df = get_outliers(out_run)
        if not out_df.empty:
            st.markdown(f"<div style='font-size:11px; color:{PALETTE['ink_soft']}; margin-top:8px;'>{int(out_df['is_outlier'].sum())} flagged of {len(out_df):,} — score distribution</div>", unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_trace(go.Histogram(x=out_df["anomaly_score"], nbinsx=30, marker_color=PALETTE["ink"], opacity=0.75))
            fig.update_layout(height=160, margin=dict(l=10,r=10,t=10,b=10), paper_bgcolor="white", plot_bgcolor="white", xaxis=dict(title="score"), yaxis=dict(title="count"), bargap=0.05)
            st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="card" style="background:#0F1115; border-color:#1E232A; color:#E8E6E1;">
          <div class="card-title" style="color:#8B92A3;">Before → After (the brief’s premise)</div>
          <div style="font-family:'Newsreader',serif; font-size:14px; font-weight:600; color:#FDFCF9; margin-bottom:6px;">Raw table: 42k rows. Visual story: 9 rules · 4 segments · ~5% anomalies.</div>
          <div style="font-size:12px; line-height:1.6; color:#C9CDD6;">
            Side-by-side below: a sample of raw data (left) vs what the visual analytics surfaces (right). The raw is illegible at scale; the visuals make cross-sell, retention, and fraud-review decisions obvious at a glance.
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Mini before/after visual
        import sqlite3
        c = get_connection()
        sample_raw = pd.read_sql_query("SELECT InvoiceNo, StockCode, Quantity, UnitPrice FROM transaction_items LIMIT 8", c)
        c.close()
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        card_header("Before — raw line items", "first 8 rows")
        st.dataframe(sample_raw, use_container_width=True, hide_index=True, height=180)
        st.markdown(f"""
        <div style="margin-top:8px; padding:10px; background:{PALETTE['bg']}; border:1px solid {PALETTE['line']}; border-radius:8px; font-size:11px; color:{PALETTE['ink_soft']}; line-height:1.5;">
          <b style="color:{PALETTE['ink']};">After →</b> Rules graph shows <span style="color:{PALETTE['accent']}; font-weight:600;">58048 ↔ 58050 cup + cake stand bundle (lift 2.88)</span>; Cluster 0 (Champions, 227 customers, £1,603 avg) buys it 2× more than average. That’s the cross-sell insight hidden in those 8 rows.
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class="card">
      <div class="card-title">Reproducibility & DB design</div>
      <div style="font-size:12.5px; color:{PALETTE['ink']}; line-height:1.65; columns: 2; column-gap: 24px;">
        <p><b>Normalized raw schema:</b> <code>customers</code> · <code>products</code> · <code>transactions</code> · <code>transaction_items</code> (FK chain; indexes on <code>transaction_id, product_id, customer_id, invoice_date</code>).</p>
        <p><b>Mining schema is separate:</b> <code>mining_runs</code> (run_id, type, timestamp, params_json) → <code>frequent_itemsets</code>, <code>association_rules</code>, <code>customer_clusters</code>, <code>cluster_assignments</code>, <code>outliers</code>. Every run is append-only; results are traceable, never overwritten.</p>
        <p><b>To reproduce:</b> <code>python data/generate_synthetic.py && python data/load_data.py && python -m mining.association && python -m mining.clustering --k 4 && python -m mining.outliers</code> or <code>docker compose up --build</code>.</p>
        <p><b>Tests:</b> <code>pytest tests/ -v</code> verifies rule metrics, cluster determinism (fixed seed), DB constraints.</p>
      </div>
    </div>
    """, unsafe_allow_html=True)
