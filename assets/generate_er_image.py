"""Generates ER diagram as PNG + SVG using matplotlib (offline, no mermaid.ink)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Colors
INK="#121417"
LINE="#D6CFC2"
BG="#FDFCF9"
CARD="#FFFFFF"
ACCENT="#C85A3A"
SAGE="#1E6B5A"

fig, ax = plt.subplots(figsize=(14, 9))
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)
ax.set_xlim(0, 14)
ax.set_ylim(0, 9)
ax.axis("off")

def draw_table(x, y, w, h, title, fields, accent=ACCENT, is_mining=False):
    # card
    rect = patches.FancyBboxPatch((x,y), w, h, boxstyle="round,pad=0.04,rounding_size=0.12", facecolor=CARD, edgecolor=LINE, linewidth=1.2)
    ax.add_patch(rect)
    # header
    hdr = patches.FancyBboxPatch((x,y+h-0.55), w, 0.55, boxstyle="round,pad=0.04,rounding_size=0.12", facecolor=accent if not is_mining else SAGE, edgecolor=accent if not is_mining else SAGE)
    ax.add_patch(hdr)
    # fix bottom corners of header (overlay white rect)
    ax.add_patch(patches.Rectangle((x,y+h-0.55), w, 0.12, facecolor=accent if not is_mining else SAGE, edgecolor="none", zorder=3))
    ax.text(x+w/2, y+h-0.27, title, ha="center", va="center", fontsize=7.5, fontweight=800, color="white", fontfamily="monospace", zorder=4)
    # fields
    for i, (fname, ftype) in enumerate(fields):
        yy = y+h-0.85 - i*0.28
        # pk/fk markers
        is_pk = "PK" in ftype
        is_fk = "FK" in ftype
        color = INK if is_pk else "#5B616E" if is_fk else "#2B2F36"
        weight = 700 if is_pk else 600 if is_fk else 400
        ax.text(x+0.14, yy, fname, ha="left", va="center", fontsize=5.8, fontweight=weight, color=color, fontfamily="monospace")
        ax.text(x+w-0.12, yy, ftype.replace(" PK","").replace(" FK",""), ha="right", va="center", fontsize=4.7, color="#8B92A3", fontfamily="monospace")
        if i < len(fields)-1:
            ax.plot([x+0.1, x+w-0.1], [yy-0.14, yy-0.14], color="#F0EBE3", lw=0.6)

# ── RAW tables (top row) ──
draw_table(0.3, 5.6, 2.6, 2.1, "customers", [("customer_id","TEXT PK"),("country","TEXT"),("first_seen","TEXT"),("last_seen","TEXT")])
draw_table(3.3, 5.6, 2.8, 2.9, "products", [("product_id","TEXT PK"),("description","TEXT"),("category","TEXT"),("unit_price","REAL")])
draw_table(6.6, 5.6, 2.9, 2.6, "transactions", [("transaction_id","TEXT PK"),("customer_id","TEXT FK"),("invoice_date","TEXT"),("country","TEXT")])
draw_table(10.0, 5.6, 3.1, 2.9, "transaction_items", [("id","INT PK"),("transaction_id","TEXT FK"),("product_id","TEXT FK"),("quantity","INT"),("unit_price","REAL"),("line_total","REAL gen")])

# ── Mining tables (bottom row) ──
draw_table(0.3, 1.8, 2.6, 2.6, "mining_runs", [("run_id","TEXT PK"),("run_type","TEXT"),("created_at","TEXT"),("params_json","TEXT"),("notes","TEXT")], is_mining=True)
draw_table(3.3, 1.1, 2.8, 3.3, "frequent_itemsets", [("id","INT PK"),("run_id","TEXT FK"),("itemset","TEXT json"),("itemset_size","INT"),("support","REAL")], is_mining=True)
draw_table(6.55, 1.1, 3.15, 3.3, "association_rules", [("id","INT PK"),("run_id","TEXT FK"),("antecedent","TEXT json"),("consequent","TEXT json"),("support","REAL"),("confidence","REAL"),("lift","REAL"),("leverage","REAL")], is_mining=True)
draw_table(10.15, 1.8, 2.7, 2.6, "customer_clusters", [("id","INT PK"),("run_id","TEXT FK"),("cluster_label","INT"),("size","INT"),("avg_recency","REAL"),("avg_monetary","REAL"),("centroid_json","TEXT")], is_mining=True)

# Extra mining tables second bottom row — cluster_assignments, outliers
# place them to not overlap: we'll shift outliers lower
draw_table(0.3, 0.25, 3.0, 3.3, "cluster_assignments", [("id","INT PK"),("run_id","TEXT FK"),("customer_id","TEXT FK"),("cluster_label","INT"),("distance","REAL"),("rfm_r/f/m","REAL×3")], is_mining=True)
draw_table(10.15, 0.25, 2.7, 2.6, "outliers", [("id","INT PK"),("run_id","TEXT FK"),("transaction_id","TEXT FK"),("anomaly_score","REAL"),("is_outlier","INT"),("reason_json","TEXT")], is_mining=True)

def arrow(x1,y1,x2,y2, label=""):
    ax.annotate("", xy=(x2,y2), xytext=(x1,y1), arrowprops=dict(arrowstyle="->", color="#9A9EA8", lw=1.1, shrinkA=2, shrinkB=2, connectionstyle="arc3,rad=0.04"))
    if label:
        mx,my=(x1+x2)/2, (y1+y2)/2
        ax.text(mx, my+0.08, label, ha="center", va="center", fontsize=4.2, color="#7A7F8A", fontfamily="monospace", bbox=dict(boxstyle="round,pad=0.12", facecolor="white", edgecolor="#E8E2D9", lw=0.6))

# FK arrows — raw
arrow(1.6, 5.6, 7.2, 7.7)  # customers -> transactions
ax.text(4.2, 6.35, "places 1—∞", ha="center", va="center", fontsize=4.5, color="#7A7F8A", fontfamily="monospace", bbox=dict(boxstyle="round,pad=0.12", facecolor="white", edgecolor="#E8E2D9"))
arrow(7.75, 5.6, 10.2, 5.6)  # transactions -> items (horizontal)
arrow(5.1, 5.6, 10.2, 5.4)   # products -> items (diagonal)
ax.text(7.6, 5.05, "contains / appears in", ha="center", fontsize=4.2, color="#7A7F8A", fontfamily="monospace")

# Mining: runs -> all mining tables
arrow(1.6, 1.8, 3.5, 2.8)
arrow(2.1, 1.8, 6.7, 2.8)
arrow(1.6, 1.8, 10.3, 3.5)
arrow(1.0, 1.8, 1.2, 1.5)  # runs -> cluster_assignments (loop)
arrow(1.6, 1.8, 10.3, 1.5) # runs -> outliers

# clusters -> assignments
arrow(11.2, 1.8, 2.2, 0.9)
# customers -> assignments
arrow(1.3, 5.6, 1.3, 3.55)
# transactions -> outliers
arrow(7.8, 5.6, 11.1, 2.8)

# Titles & legend
ax.text(7, 8.65, "Visual Analytics Platform — Relational Schema", ha="center", va="center", fontsize=12, fontweight=800, color=INK, fontfamily="serif")
ax.text(7, 8.32, "RAW schema (terracotta) stores operational data  ·  MINING schema (sage) stores append-only analytical results, traceable by mining_runs(run_id)  ·  SQLite / Postgres", ha="center", va="center", fontsize=6, color="#5B616E")
# legend
ax.add_patch(patches.FancyBboxPatch((0.3, 8.75), 0.22, 0.16, boxstyle="round,pad=0.02,rounding_size=0.04", facecolor=ACCENT, edgecolor=ACCENT))
ax.text(0.58, 8.83, "RAW", ha="left", va="center", fontsize=5, fontweight=700, color="#5B616E", fontfamily="monospace")
ax.add_patch(patches.FancyBboxPatch((1.1, 8.75), 0.22, 0.16, boxstyle="round,pad=0.02,rounding_size=0.04", facecolor=SAGE, edgecolor=SAGE))
ax.text(1.36, 8.83, "MINING", ha="left", va="center", fontsize=5, fontweight=700, color="#5B616E", fontfamily="monospace")
ax.text(13.7, 0.12, "PK = primary key  ·  FK = foreign key  ·  every mining result row references mining_runs(run_id) — reruns are append-only, never destructive", ha="right", va="center", fontsize=4.2, color="#9AA0B2", fontstyle="italic")

plt.tight_layout(pad=0.7)
plt.savefig("assets/er_diagram.png", dpi=220, bbox_inches="tight", facecolor=BG)
plt.savefig("assets/er_diagram.svg", bbox_inches="tight", facecolor=BG)
print("Saved assets/er_diagram.png + .svg")
