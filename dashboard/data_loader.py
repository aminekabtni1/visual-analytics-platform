import pathlib, json, sqlite3
import pandas as pd

import sys
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from database.db import get_connection, get_db_path

def conn():
    return get_connection()

def latest_run(run_type: str):
    c = conn()
    row = c.execute("SELECT run_id FROM mining_runs WHERE run_type=? ORDER BY created_at DESC LIMIT 1",(run_type,)).fetchone()
    c.close()
    return row["run_id"] if row else None

def list_runs():
    c = conn()
    rows = c.execute("SELECT run_id, run_type, created_at, params_json FROM mining_runs ORDER BY created_at DESC").fetchall()
    c.close()
    return rows

def get_products():
    c = conn()
    df = pd.read_sql_query("SELECT * FROM products", c)
    c.close()
    return df

def get_transactions(limit=None, where_clause="", params=()):
    c = conn()
    q = f"SELECT t.transaction_id, t.customer_id, t.invoice_date, t.country, COUNT(ti.product_id) as n_items, SUM(ti.quantity*ti.unit_price) as total_value FROM transactions t JOIN transaction_items ti ON ti.transaction_id=t.transaction_id {where_clause} GROUP BY t.transaction_id ORDER BY t.invoice_date DESC"
    if limit:
        q += f" LIMIT {int(limit)}"
    df = pd.read_sql_query(q, c, params=params)
    c.close()
    return df

def get_raw_overview(filters=None):
    """filters: dict with date_start, date_end, category, country"""
    c = conn()
    # build query
    cats = ""
    params=[]
    if filters and filters.get("category"):
        cats = " AND p.category=?"
        params.append(filters["category"])
    if filters and filters.get("country"):
        cats += " AND t.country=?"
        params.append(filters["country"])
    # date filter on invoice_date string
    date_filter=""
    if filters and filters.get("date_start"):
        date_filter += " AND date(t.invoice_date) >= date(?)"
        params.append(filters["date_start"])
    if filters and filters.get("date_end"):
        date_filter += " AND date(t.invoice_date) <= date(?)"
        params.append(filters["date_end"])

    q = f"""
    SELECT t.transaction_id, t.customer_id, t.invoice_date, t.country,
           p.category, ti.product_id, p.description, ti.quantity, ti.unit_price, ti.quantity*ti.unit_price as line_total
    FROM transactions t
    JOIN transaction_items ti ON ti.transaction_id=t.transaction_id
    JOIN products p ON p.product_id=ti.product_id
    WHERE 1=1 {cats} {date_filter}
    ORDER BY t.invoice_date DESC LIMIT 5000
    """
    df = pd.read_sql_query(q, c, params=params)
    c.close()
    if not df.empty:
        df["invoice_date"] = pd.to_datetime(df["invoice_date"])
    return df

def get_rules(run_id=None):
    if not run_id:
        run_id = latest_run("association")
    if not run_id:
        return pd.DataFrame()
    c = conn()
    df = pd.read_sql_query("SELECT * FROM association_rules WHERE run_id=? ORDER BY lift DESC", c, params=(run_id,))
    c.close()
    # parse json arrays
    if not df.empty:
        df["antecedent_parsed"] = df["antecedent"].apply(json.loads)
        df["consequent_parsed"] = df["consequent"].apply(json.loads)
        df["antecedent_str"] = df["antecedent_parsed"].apply(lambda x: ", ".join(x))
        df["consequent_str"] = df["consequent_parsed"].apply(lambda x: ", ".join(x))
        df["rule_label"] = df["antecedent_str"] + " → " + df["consequent_str"]
    return df

def get_frequent(run_id=None):
    if not run_id:
        run_id = latest_run("association")
    if not run_id:
        return pd.DataFrame()
    c = conn()
    df = pd.read_sql_query("SELECT * FROM frequent_itemsets WHERE run_id=? ORDER BY support DESC", c, params=(run_id,))
    c.close()
    return df

def get_clusters(run_id=None):
    if not run_id:
        run_id = latest_run("clustering")
    if not run_id:
        return pd.DataFrame(), pd.DataFrame()
    c = conn()
    clusters = pd.read_sql_query("SELECT * FROM customer_clusters WHERE run_id=? ORDER BY cluster_label", c, params=(run_id,))
    assigns = pd.read_sql_query("SELECT * FROM cluster_assignments WHERE run_id=?", c, params=(run_id,))
    c.close()
    return clusters, assigns

def get_outliers(run_id=None):
    if not run_id:
        run_id = latest_run("outlier")
    if not run_id:
        return pd.DataFrame()
    c = conn()
    # join with transaction totals
    q = """
    SELECT o.*, t.customer_id, t.invoice_date,
           (SELECT SUM(quantity*unit_price) FROM transaction_items WHERE transaction_id=o.transaction_id) as total_value,
           (SELECT COUNT(*) FROM transaction_items WHERE transaction_id=o.transaction_id) as n_items,
           (SELECT SUM(quantity) FROM transaction_items WHERE transaction_id=o.transaction_id) as total_qty
    FROM outliers o JOIN transactions t ON t.transaction_id=o.transaction_id
    WHERE o.run_id=?
    ORDER BY o.anomaly_score ASC
    """
    df = pd.read_sql_query(q, c, params=(run_id,))
    c.close()
    if not df.empty:
        df["invoice_date"] = pd.to_datetime(df["invoice_date"])
        df["reason_parsed"] = df["reason_json"].apply(lambda x: json.loads(x) if x else {})
    return df

def get_product_history(product_id):
    c = conn()
    df = pd.read_sql_query("""
    SELECT t.transaction_id, t.invoice_date, t.customer_id, ti.quantity, ti.unit_price, ti.quantity*ti.unit_price as line_total
    FROM transaction_items ti JOIN transactions t ON t.transaction_id=ti.transaction_id
    WHERE ti.product_id=? ORDER BY t.invoice_date DESC LIMIT 100
    """, c, params=(product_id,))
    c.close()
    return df

def get_cluster_product_affinity(run_id=None):
    if not run_id:
        run_id = latest_run("clustering")
    if not run_id:
        return pd.DataFrame()
    c = conn()
    # For each cluster, top products by purchase frequency among its customers
    q = """
    SELECT ca.cluster_label, ti.product_id, p.description, p.category, COUNT(*) as purchases, SUM(ti.quantity) as total_qty
    FROM cluster_assignments ca
    JOIN transactions t ON t.customer_id=ca.customer_id
    JOIN transaction_items ti ON ti.transaction_id=t.transaction_id
    JOIN products p ON p.product_id=ti.product_id
    WHERE ca.run_id=?
    GROUP BY ca.cluster_label, ti.product_id
    ORDER BY ca.cluster_label, purchases DESC
    """
    df = pd.read_sql_query(q, c, params=(run_id,))
    c.close()
    return df

def get_customer_rfm(customer_id=None):
    c = conn()
    if customer_id:
        df = pd.read_sql_query("SELECT * FROM cluster_assignments WHERE customer_id=? ORDER BY cluster_label", c, params=(customer_id,))
    else:
        df = pd.read_sql_query("SELECT * FROM cluster_assignments LIMIT 1", c)
    c.close()
    return df
