import json, pathlib, pandas as pd, numpy as np, sys
sys.path.insert(0, '.')
from database.db import get_connection
from dashboard.data_loader import latest_run
import json as j
import networkx as nx
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

conn = get_connection()
assoc_run = latest_run("association")
clust_run = latest_run("clustering")
out_run   = latest_run("outlier")
print(f"runs assoc={assoc_run} clust={clust_run} out={out_run}")

# rules + frequent
rules = pd.read_sql_query('SELECT r.* FROM association_rules r WHERE r.run_id=? ORDER BY r.lift DESC', conn, params=(assoc_run,))
frequent = pd.read_sql_query('SELECT f.* FROM frequent_itemsets f WHERE f.run_id=? ORDER BY f.support DESC', conn, params=(assoc_run,))
clusters = pd.read_sql_query('SELECT c.* FROM customer_clusters c WHERE c.run_id=? ORDER BY c.cluster_label', conn, params=(clust_run,))
assigns = pd.read_sql_query('SELECT ca.customer_id, ca.cluster_label, ca.distance_to_centroid, ca.rfm_r as recency, ca.rfm_f as frequency, ca.rfm_m as monetary FROM cluster_assignments ca WHERE ca.run_id=?', conn, params=(clust_run,))
products = pd.read_sql_query('SELECT * FROM products', conn)
prod_map = dict(zip(products['product_id'], products['description']))
prod_cat = dict(zip(products['product_id'], products['category']))
# build pca
Xlog = np.column_stack([assigns['recency'].values, np.log1p(assigns['frequency'].values), np.log1p(assigns['monetary'].values)])
Xs = StandardScaler().fit_transform(Xlog)
coords = PCA(n_components=2, random_state=42).fit_transform(Xs)
assigns['pca_x'] = coords[:,0]
assigns['pca_y'] = coords[:,1]

# network positions for rules
rules['antecedent_parsed'] = rules['antecedent'].apply(lambda x: j.loads(x) if isinstance(x,str) else x)
rules['consequent_parsed'] = rules['consequent'].apply(lambda x: j.loads(x) if isinstance(x,str) else x)
rules['antecedent_str'] = rules['antecedent_parsed'].apply(lambda x: ", ".join(x))
rules['consequent_str'] = rules['consequent_parsed'].apply(lambda x: ", ".join(x))
rules['rule_label'] = rules['antecedent_str'] + " \u2192 " + rules['consequent_str']
# build graph for all rules (top 9)
G = nx.DiGraph()
all_pids=set()
for _, r in rules.iterrows():
    all_pids.update(r['antecedent_parsed'])
    all_pids.update(r['consequent_parsed'])
for pid in all_pids:
    G.add_node(pid)
for _, r in rules.iterrows():
    for a in r['antecedent_parsed']:
        for c in r['consequent_parsed']:
            G.add_edge(a,c, support=float(r['support']), confidence=float(r['confidence']), lift=float(r['lift']))
pos = nx.spring_layout(G, k=1.2, iterations=70, seed=42)
# frequent support map
freq_map={}
for _, rr in frequent.iterrows():
    items = j.loads(rr['itemset']) if isinstance(rr['itemset'], str) else rr['itemset']
    for pid in items:
        freq_map[pid]=max(freq_map.get(pid,0), float(rr['support']))
nodes=[]
for pid in G.nodes():
    x,y = pos[pid]
    nodes.append({"id": pid, "x": float(x), "y": float(y), "label": prod_map.get(pid,pid)[:36], "category": prod_cat.get(pid,""), "support": freq_map.get(pid,0.03)})
edges=[]
for u,v,d in G.edges(data=True):
    edges.append({"source": u, "target": v, "support": d['support'], "confidence": d['confidence'], "lift": d['lift']})
network = {"nodes": nodes, "edges": edges}

# outliers sample for frontend (limit 600 for size)
outliers = pd.read_sql_query('SELECT o.transaction_id, o.anomaly_score, o.is_outlier, o.reason_json, t.customer_id, t.invoice_date, (SELECT SUM(quantity*unit_price) FROM transaction_items WHERE transaction_id=o.transaction_id) as total_value, (SELECT COUNT(*) FROM transaction_items WHERE transaction_id=o.transaction_id) as n_items, (SELECT SUM(quantity) FROM transaction_items WHERE transaction_id=o.transaction_id) as total_qty FROM outliers o JOIN transactions t ON t.transaction_id=o.transaction_id WHERE o.run_id=? ORDER BY o.anomaly_score ASC LIMIT 800', conn, params=(out_run,))
outliers['invoice_date'] = pd.to_datetime(outliers['invoice_date']).dt.strftime('%Y-%m-%d %H:%M')
# keep only needed for plot + top 600
outliers_small = outliers.head(600).copy()
outliers_small['reason_parsed'] = outliers_small['reason_json'].apply(lambda x: j.loads(x) if isinstance(x,str) and x else {})

# daily / categories / sample
tx = pd.read_sql_query('SELECT t.invoice_date, ti.quantity*ti.unit_price as rev, p.category FROM transactions t JOIN transaction_items ti ON ti.transaction_id=t.transaction_id JOIN products p ON p.product_id=ti.product_id', conn)
tx['invoice_date'] = pd.to_datetime(tx['invoice_date'])
daily = tx.groupby(tx['invoice_date'].dt.date).agg(rev=('rev','sum'), txns=('rev','count')).reset_index()
daily['invoice_date'] = daily['invoice_date'].astype(str)
cat = tx.groupby('category').agg(rev=('rev','sum')).reset_index()
sample = pd.read_sql_query('SELECT t.transaction_id, t.customer_id, t.invoice_date, p.category, ti.product_id, p.description, ti.quantity, ti.unit_price, ti.quantity*ti.unit_price as line_total FROM transactions t JOIN transaction_items ti ON ti.transaction_id=t.transaction_id JOIN products p ON p.product_id=ti.product_id ORDER BY t.invoice_date DESC LIMIT 400', conn)
sample['invoice_date'] = pd.to_datetime(sample['invoice_date']).dt.strftime('%Y-%m-%d')
# counts
counts = {
    "n_tx": int(pd.read_sql_query("SELECT COUNT(*) as c FROM transactions", conn).iloc[0]['c']),
    "n_cust": int(pd.read_sql_query("SELECT COUNT(*) as c FROM customers", conn).iloc[0]['c']),
    "n_prod": int(pd.read_sql_query("SELECT COUNT(*) as c FROM products", conn).iloc[0]['c']),
    "n_rules": len(rules),
    "assoc_run": assoc_run,
    "clust_run": clust_run,
    "out_run": out_run,
}
# eval
import pathlib as P
eval_path = P.Path("evals/eval_summary.json")
evals = j.loads(eval_path.read_text()) if eval_path.exists() else {}
ce_path = P.Path("evals/clustering_eval.json")
ce = j.loads(ce_path.read_text()) if ce_path.exists() else {}

conn.close()
outdir = pathlib.Path("api/data")
outdir.mkdir(parents=True, exist_ok=True)
# dump
open(outdir/"rules.json","w",encoding="utf-8").write(j.dumps(rules.to_dict(orient="records"), ensure_ascii=False))
open(outdir/"clusters.json","w",encoding="utf-8").write(j.dumps(clusters.to_dict(orient="records"), ensure_ascii=False))
open(outdir/"assigns.json","w",encoding="utf-8").write(j.dumps(assigns.to_dict(orient="records"), ensure_ascii=False))
open(outdir/"outliers.json","w",encoding="utf-8").write(j.dumps(outliers_small.to_dict(orient="records"), ensure_ascii=False, default=str))
open(outdir/"products.json","w",encoding="utf-8").write(j.dumps(products.to_dict(orient="records"), ensure_ascii=False))
open(outdir/"network.json","w",encoding="utf-8").write(j.dumps(network, ensure_ascii=False))
open(outdir/"counts.json","w",encoding="utf-8").write(j.dumps(counts, ensure_ascii=False))
open(outdir/"pca.json","w",encoding="utf-8").write(j.dumps({"assigns": assigns.to_dict(orient="records"), "clusters": clusters.to_dict(orient="records")}, ensure_ascii=False))
open(outdir/"daily.json","w",encoding="utf-8").write(daily.to_json(orient="records"))
open(outdir/"categories.json","w",encoding="utf-8").write(cat.to_json(orient="records"))
open(outdir/"sample_tx.json","w",encoding="utf-8").write(sample.to_json(orient="records"))
open(outdir/"evals.json","w",encoding="utf-8").write(j.dumps({"eval_summary": evals, "clustering_eval": ce}, ensure_ascii=False))
print("dumped full api/data")
for f in sorted(outdir.glob("*.json")):
    print(f.name, round(f.stat().st_size/1024,1), "KB")
