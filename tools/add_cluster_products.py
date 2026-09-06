import json, pathlib, sys
sys.path.insert(0, '.')
from database.db import get_connection
from dashboard.data_loader import latest_run, get_cluster_product_affinity
import pandas as pd
conn = get_connection()
clust_run = latest_run("clustering")
aff = get_cluster_product_affinity(clust_run)
# aff has cluster_label, product_id, description, category, purchases, total_qty
# keep top 8 per cluster
out = {}
for label, grp in aff.groupby('cluster_label'):
    out[str(label)] = grp.head(8).to_dict(orient='records')
pathlib.Path("api/data").mkdir(parents=True, exist_ok=True)
import json as j
open("api/data/cluster_products.json","w",encoding="utf-8").write(j.dumps(out, ensure_ascii=False))
print("cluster_products dumped", len(out))
# also dump outliers with customer cluster mapping?
# Add customer cluster map for outlier drill-down (customer -> cluster)
import sqlite3
assigns = pd.read_sql_query("SELECT customer_id, cluster_label FROM cluster_assignments WHERE run_id=?", conn, params=(clust_run,))
m = dict(zip(assigns['customer_id'], assigns['cluster_label']))
open("api/data/customer_cluster.json","w",encoding="utf-8").write(j.dumps(m, ensure_ascii=False))
print("customer_cluster", len(m))
conn.close()
for f in pathlib.Path("api/data").glob("*.json"):
    print(f.name, round(f.stat().st_size/1024,1))
