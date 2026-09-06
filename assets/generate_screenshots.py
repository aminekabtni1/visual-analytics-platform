"""Generate placeholder dashboard screenshots from real data (so README has images even without manual capture)."""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from database.db import get_connection

OUT = pathlib.Path(__file__).parent / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

# common style
BG="#FDFCF9"; INK="#121417"; LINE="#E8E2D9"; ACCENT="#C85A3A"; SAGE="#1E6B5A"; BLUE="#3A5A7A"

# 1 — overview: daily revenue
c = get_connection()
df = pd.read_sql_query("SELECT t.invoice_date, ti.quantity*ti.unit_price as rev FROM transactions t JOIN transaction_items ti ON ti.transaction_id=t.transaction_id", c)
c.close()
df["invoice_date"] = pd.to_datetime(df["invoice_date"])
daily = df.groupby(df["invoice_date"].dt.date)["rev"].sum().reset_index()
daily["invoice_date"] = pd.to_datetime(daily["invoice_date"])

fig, ax = plt.subplots(figsize=(10, 4.2))
fig.patch.set_facecolor(BG); ax.set_facecolor("white")
ax.plot(daily["invoice_date"], daily["rev"], color=ACCENT, lw=1.6)
ax.fill_between(daily["invoice_date"], daily["rev"], color=ACCENT, alpha=0.08)
ax.set_title("Overview — Revenue over time  (synthetic screenshot from real DB data)", fontsize=10, fontweight=700, color=INK, loc="left", pad=12)
ax.set_ylabel("Revenue £", fontsize=8, color="#5B616E")
ax.grid(axis="y", color="#F0EBE3", lw=0.6)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.spines["bottom"].set_color(LINE); ax.spines["left"].set_color(LINE)
fig.tight_layout()
fig.savefig(OUT/"01_overview.png", dpi=180, bbox_inches="tight", facecolor=BG)
print("saved 01_overview.png")

# 2 — rules network mock (use real rules)
from dashboard.data_loader import get_rules
rules = get_rules()
# simple: bar of lift
if not rules.empty:
    top = rules.head(6)
    fig, ax = plt.subplots(figsize=(10, 4.2))
    fig.patch.set_facecolor(BG); ax.set_facecolor("white")
    y = top["rule_label"]
    x = top["lift"]
    colors = [ACCENT if v>2.7 else SAGE if v>2 else BLUE for v in x]
    ax.barh(y, x, color=colors, edgecolor="white", height=0.55)
    ax.set_title("Rules — Lift (top 6 association rules, real DB)", fontsize=10, fontweight=700, color=INK, loc="left")
    ax.set_xlabel("Lift (× more likely than chance)", fontsize=8, color="#5B616E")
    for i, v in enumerate(x):
        ax.text(v+0.04, i, f"{v:.2f}", va="center", fontsize=7, color=INK)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT/"02_rules.png", dpi=180, bbox_inches="tight", facecolor=BG)
    print("saved 02_rules.png")

# 3 — clusters scatter (real PCA)
from dashboard.data_loader import get_clusters
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import numpy as np
clusters, assigns = get_clusters()
if not assigns.empty:
    Xlog = np.column_stack([assigns["rfm_r"].values, np.log1p(assigns["rfm_f"].values), np.log1p(assigns["rfm_m"].values)])
    Xs = StandardScaler().fit_transform(Xlog)
    coords = PCA(n_components=2, random_state=42).fit_transform(Xs)
    fig, ax = plt.subplots(figsize=(10, 4.5))
    fig.patch.set_facecolor(BG); ax.set_facecolor("white")
    colors = ["#C85A3A","#1E6B5A","#C18F2E","#3A5A7A"]
    for lab in sorted(assigns["cluster_label"].unique()):
        mask = assigns["cluster_label"]==lab
        ax.scatter(coords[mask,0], coords[mask,1], s=14, color=colors[lab % len(colors)], alpha=0.78, label=f"Cluster {lab} ({mask.sum()})", edgecolor="white", linewidth=0.4)
    ax.set_title("Clusters — PCA of RFM (real DB, K=4)", fontsize=10, fontweight=700, color=INK, loc="left")
    ax.set_xlabel("PC1 → value & frequency", fontsize=8, color="#5B616E")
    ax.set_ylabel("PC2 → recency", fontsize=8, color="#5B616E")
    ax.grid(color="#F0EBE3", lw=0.5, alpha=0.7)
    ax.legend(frameon=True, facecolor="white", edgecolor=LINE, fontsize=7, loc="upper right")
    fig.tight_layout()
    fig.savefig(OUT/"03_clusters.png", dpi=180, bbox_inches="tight", facecolor=BG)
    print("saved 03_clusters.png")

# 4 — outliers
from dashboard.data_loader import get_outliers, latest_run
out = get_outliers(latest_run("outlier"))
if not out.empty:
    fig, ax = plt.subplots(figsize=(10, 4.2))
    fig.patch.set_facecolor(BG); ax.set_facecolor("white")
    normal = out[out["is_outlier"]==0].sample(n=min(2000, len(out[out["is_outlier"]==0])), random_state=42)
    flagged = out[out["is_outlier"]==1]
    ax.scatter(normal["n_items"], normal["total_value"], s=10, color="#D1D5DB", alpha=0.5, label="Normal")
    ax.scatter(flagged["n_items"], flagged["total_value"], s=22, color=ACCENT, marker="x", label=f"Outlier ({len(flagged)})")
    ax.set_title("Outliers — Value vs Items (Isolation Forest, real DB)", fontsize=10, fontweight=700, color=INK, loc="left")
    ax.set_xlabel("Items in basket", fontsize=8, color="#5B616E")
    ax.set_ylabel("Total value £", fontsize=8, color="#5B616E")
    ax.grid(color="#F0EBE3", lw=0.5)
    ax.legend(frameon=True, facecolor="white", edgecolor=LINE, fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT/"04_outliers.png", dpi=180, bbox_inches="tight", facecolor=BG)
    print("saved 04_outliers.png")

print("All screenshots saved to", OUT)
