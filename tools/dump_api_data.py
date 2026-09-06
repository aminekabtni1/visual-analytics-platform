import json, pathlib, pandas as pd
from database.db import get_connection
import pathlib as P
conn = get_connection()
# latest run ids
import sys as _sys
_sys.path.insert(0, '.')
from dashboard.data_loader import latest_run as _latest
assoc_run = _latest("association")
clust_run = _latest("clustering")
out_run   = _latest("outlier")
print(f"latest assoc {assoc_run} clust {clust_run} out {out_run}")
rules = pd.read_sql_query('SELECT r.* FROM association_rules r WHERE r.run_id=? ORDER BY r.lift DESC', conn, params=(assoc_run,))
frequent = pd.read_sql_query('SELECT f.* FROM frequent_itemsets f WHERE f.run_id=? ORDER BY f.support DESC', conn, params=(assoc_run,))
clusters = pd.read_sql_query('SELECT c.* FROM customer_clusters c WHERE c.run_id=? ORDER BY c.cluster_label', conn, params=(clust_run,))
assigns = pd.read_sql_query('SELECT ca.customer_id, ca.cluster_label, ca.distance_to_centroid, ca.rfm_r as recency, ca.rfm_f as frequency, ca.rfm_m as monetary FROM cluster_assignments ca WHERE ca.run_id=?', conn, params=(clust_run,))
outliers = pd.read_sql_query('SELECT o.transaction_id, o.anomaly_score, o.is_outlier, o.reason_json, t.customer_id, t.invoice_date, (SELECT SUM(quantity*unit_price) FROM transaction_items WHERE transaction_id=o.transaction_id) as total_value, (SELECT COUNT(*) FROM transaction_items WHERE transaction_id=o.transaction_id) as n_items, (SELECT SUM(quantity) FROM transaction_items WHERE transaction_id=o.transaction_id) as total_qty FROM outliers o JOIN transactions t ON t.transaction_id=o.transaction_id WHERE o.run_id=? ORDER BY o.anomaly_score ASC LIMIT 2000', conn, params=(out_run,))
products = pd.read_sql_query('SELECT * FROM products', conn)
tx = pd.read_sql_query('SELECT t.invoice_date, ti.quantity*ti.unit_price as rev, p.category FROM transactions t JOIN transaction_items ti ON ti.transaction_id=t.transaction_id JOIN products p ON p.product_id=ti.product_id', conn)
print('rules', len(rules), 'clusters', len(clusters), 'assigns', len(assigns), 'outliers', len(outliers), 'products', len(products), 'tx rows', len(tx))
conn.close()
outdir = pathlib.Path("api/data")
outdir.mkdir(parents=True, exist_ok=True)
import json as j
# rules: parse antecedent/consequent for frontend
rules['antecedent_parsed'] = rules['antecedent'].apply(lambda x: j.loads(x) if isinstance(x,str) else x)
rules['consequent_parsed'] = rules['consequent'].apply(lambda x: j.loads(x) if isinstance(x,str) else x)
rules['antecedent_str'] = rules['antecedent_parsed'].apply(lambda x: ", ".join(x))
rules['consequent_str'] = rules['consequent_parsed'].apply(lambda x: ", ".join(x))
rules['rule_label'] = rules['antecedent_str'] + " → " + rules['consequent_str']
open(outdir/"rules.json","w",encoding="utf-8").write(j.dumps(rules.to_dict(orient="records"), ensure_ascii=False))
open(outdir/"clusters.json","w",encoding="utf-8").write(j.dumps(clusters.to_dict(orient="records"), ensure_ascii=False))
open(outdir/"assigns.json","w",encoding="utf-8").write(j.dumps(assigns.to_dict(orient="records"), ensure_ascii=False))
open(outdir/"outliers.json","w",encoding="utf-8").write(j.dumps(outliers.to_dict(orient="records"), ensure_ascii=False, default=str))
open(outdir/"products.json","w",encoding="utf-8").write(j.dumps(products.to_dict(orient="records"), ensure_ascii=False))
# overview aggregates
tx['invoice_date'] = pd.to_datetime(tx['invoice_date'])
daily = tx.groupby(tx['invoice_date'].dt.date).agg(rev=('rev','sum'), txns=('rev','count')).reset_index()
daily['invoice_date'] = daily['invoice_date'].astype(str)
daily.to_json(outdir/"daily.json", orient="records")
cat = tx.groupby('category').agg(rev=('rev','sum')).reset_index()
cat.to_json(outdir/"categories.json", orient="records")
sample = pd.read_sql_query('SELECT t.transaction_id, t.customer_id, t.invoice_date, p.category, ti.product_id, p.description, ti.quantity, ti.unit_price, ti.quantity*ti.unit_price as line_total FROM transactions t JOIN transaction_items ti ON ti.transaction_id=t.transaction_id JOIN products p ON p.product_id=ti.product_id ORDER BY t.invoice_date DESC LIMIT 500', get_connection())
sample['invoice_date'] = pd.to_datetime(sample['invoice_date']).dt.strftime('%Y-%m-%d')
sample.to_json(outdir/"sample_tx.json", orient="records")
print("dumped to", outdir.resolve())
for f in outdir.glob("*.json"):
    print(f.name, f.stat().st_size)
