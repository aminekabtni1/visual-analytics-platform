"""
Outlier Detection — Isolation Forest on transaction-level features.
Flags anomalous transactions and writes to outliers table.

Features per transaction:
  - n_items, total_quantity, total_value, avg_unit_price, distinct_products,
    days_since_first, is_weekend, hour (if available)

Usage: python -m mining.outliers [--contamination 0.05]
"""
import argparse, json, pathlib, sys
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from database.db import get_connection, init_db
from mining.utils import new_run_id, now_iso

def build_features(conn):
    q = """
    SELECT t.transaction_id, t.customer_id, t.invoice_date,
           ti.product_id, ti.quantity, ti.unit_price
    FROM transactions t JOIN transaction_items ti ON ti.transaction_id = t.transaction_id
    """
    df = pd.read_sql_query(q, conn)
    df["invoice_date"] = pd.to_datetime(df["invoice_date"])
    df["line_total"] = df["quantity"] * df["unit_price"]
    # Aggregate per transaction
    agg = df.groupby(["transaction_id","customer_id","invoice_date"], as_index=False).agg(
        n_items=("product_id","count"),
        distinct_products=("product_id","nunique"),
        total_quantity=("quantity","sum"),
        total_value=("line_total","sum"),
        avg_unit_price=("unit_price","mean"),
        max_unit_price=("unit_price","max"),
    )
    # Temporal features
    agg["hour"] = agg["invoice_date"].dt.hour
    agg["is_weekend"] = (agg["invoice_date"].dt.weekday >= 5).astype(int)
    # days since first transaction (tenure context)
    min_date = agg["invoice_date"].min()
    agg["days_since_start"] = (agg["invoice_date"] - min_date).dt.days
    # Value per item
    agg["value_per_item"] = agg["total_value"] / agg["n_items"].clip(lower=1)
    return agg, df

def run_outliers(db_path=None, contamination=0.05, random_state=42):
    init_db(db_path)
    conn = get_connection(db_path)
    feats, _ = build_features(conn)
    print(f"Transaction features: {feats.shape}")
    print(feats[["n_items","total_quantity","total_value","avg_unit_price"]].describe().to_string())

    feature_cols = ["n_items","distinct_products","total_quantity","total_value","avg_unit_price","max_unit_price","hour","is_weekend","value_per_item","days_since_start"]
    X = feats[feature_cols].fillna(0).values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    clf = IsolationForest(contamination=contamination, random_state=random_state, n_estimators=200)
    preds = clf.fit_predict(X_scaled)  # 1 normal, -1 outlier
    scores = clf.decision_function(X_scaled)  # higher = more normal
    # Also anomaly score (sklearn's score_samples inverted)
    anom = clf.score_samples(X_scaled)

    feats["anomaly_score"] = scores  # negative-ish = anomalous
    feats["is_outlier"] = (preds == -1).astype(int)
    feats["anomaly_score_raw"] = anom

    n_out = feats["is_outlier"].sum()
    print(f"Flagged {n_out} / {len(feats)} transactions as outliers (contamination={contamination})")
    print(feats[feats["is_outlier"]==1][["transaction_id","n_items","total_value","total_quantity","anomaly_score"]].head(10).to_string(index=False))

    run_id = new_run_id()
    params = {"contamination": contamination, "feature_cols": feature_cols, "model": "IsolationForest(n_estimators=200)", "random_state": random_state}
    conn.execute("INSERT INTO mining_runs(run_id,run_type,created_at,params_json,notes) VALUES (?,?,?,?,?)",
                 (run_id, "outlier", now_iso(), json.dumps(params), f"IsolationForest flagged {n_out} outliers"))

    for _, row in feats.iterrows():
        # reason: top contributing deviation — simple heuristic: features >2 std from mean
        reasons = {}
        for col in feature_cols:
            z = (row[col] - feats[col].mean()) / (feats[col].std() + 1e-9)
            if abs(z) > 2:
                reasons[col] = round(float(z),2)
        conn.execute("INSERT INTO outliers(run_id,transaction_id,anomaly_score,is_outlier,reason_json) VALUES (?,?,?,?,?)",
                     (run_id, str(row["transaction_id"]), float(row["anomaly_score"]), int(row["is_outlier"]), json.dumps(reasons)))
    conn.commit()
    conn.close()
    print(f"Run {run_id} stored.")
    return run_id

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=str, default=None)
    ap.add_argument("--contamination", type=float, default=0.05)
    args = ap.parse_args()
    run_outliers(db_path=args.db, contamination=args.contamination)
