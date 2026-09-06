"""
Customer Segmentation — RFM + K-Means, with elbow/silhouette justification.
Writes customer_clusters + cluster_assignments.

Usage: python -m mining.clustering [--k 4] [--auto-k]
"""
import argparse, json, pathlib, sys
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from database.db import get_connection, init_db
from mining.utils import new_run_id, now_iso, jdump

def compute_rfm(conn):
    q = """
    SELECT t.customer_id, t.invoice_date, ti.quantity, ti.unit_price
    FROM transactions t JOIN transaction_items ti ON ti.transaction_id = t.transaction_id
    """
    df = pd.read_sql_query(q, conn)
    df["invoice_date"] = pd.to_datetime(df["invoice_date"])
    df["line_total"] = df["quantity"] * df["unit_price"]
    max_date = df["invoice_date"].max() + pd.Timedelta(days=1)
    rfm = df.groupby("customer_id").agg(
        last_date=("invoice_date","max"),
        frequency=("invoice_date", lambda x: x.nunique()),  # number of distinct transactions
        monetary=("line_total","sum"),
    ).reset_index()
    rfm["recency"] = (max_date - rfm["last_date"]).dt.days
    rfm = rfm[["customer_id","recency","frequency","monetary"]]
    return rfm, max_date

def choose_k(X_scaled, k_range=range(2,9)):
    inertias=[]
    silhouettes=[]
    for k in k_range:
        km = KMeans(n_clusters=k, n_init=20, random_state=42)
        labels = km.fit_predict(X_scaled)
        inertias.append(km.inertia_)
        sil = silhouette_score(X_scaled, labels) if k>1 else 0
        silhouettes.append(sil)
    # pick k with max silhouette (with preference for parsimony: if within 0.02, pick smaller k)
    best_idx = int(np.argmax(silhouettes))
    best_k = list(k_range)[best_idx]
    return best_k, inertias, silhouettes

def run_clustering(db_path=None, k=None, auto_k=False):
    init_db(db_path)
    conn = get_connection(db_path)
    rfm, max_date = compute_rfm(conn)
    print(f"RFM computed for {len(rfm)} customers (reference date {max_date.date()})")
    print(rfm.describe().to_string())

    scaler = StandardScaler()
    X = rfm[["recency","frequency","monetary"]].values
    # log transform monetary & frequency to reduce skew (common for RFM)
    # Use log1p for stability
    X_log = np.column_stack([rfm["recency"].values, np.log1p(rfm["frequency"].values), np.log1p(rfm["monetary"].values)])
    X_scaled = scaler.fit_transform(X_log)

    if auto_k or k is None:
        k_range = range(2,9)
        best_k, inertias, sils = choose_k(X_scaled, k_range)
        print("k vs silhouette:", list(zip(list(k_range), [round(s,3) for s in sils])))
        print(f"Auto-selected k={best_k} (max silhouette {max(sils):.3f})")
        if k is None:
            k = best_k
        # save elbow data for evals
        eval_path = pathlib.Path(__file__).parent.parent / "evals" / "clustering_eval.json"
        eval_path.parent.mkdir(exist_ok=True)
        eval_path.write_text(json.dumps({"k_range": list(k_range), "inertias": inertias, "silhouettes": sils, "best_k": best_k, "best_silhouette": max(sils)}, indent=2))

    # Final fit
    km = KMeans(n_clusters=k, n_init=30, random_state=42)
    labels = km.fit_predict(X_scaled)
    sil = silhouette_score(X_scaled, labels)
    print(f"Final KMeans k={k} silhouette={sil:.3f}")

    # PCA 2D for dashboard
    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(X_scaled)
    rfm["cluster"] = labels
    rfm["pca_x"] = coords[:,0]
    rfm["pca_y"] = coords[:,1]
    rfm["distance"] = np.linalg.norm(X_scaled - km.cluster_centers_[labels], axis=1)

    # Per-cluster stats
    cluster_stats = rfm.groupby("cluster").agg(
        size=("customer_id","count"),
        avg_recency=("recency","mean"),
        avg_frequency=("frequency","mean"),
        avg_monetary=("monetary","mean"),
    ).reset_index()

    # Describe clusters in words
    run_id = new_run_id()
    params = {"k": k, "silhouette": float(sil), "reference_date": str(max_date), "scaler": "StandardScaler on [recency, log1p(freq), log1p(monetary)]"}
    conn.execute("INSERT INTO mining_runs(run_id,run_type,created_at,params_json,notes) VALUES (?,?,?,?,?)",
                 (run_id, "clustering", now_iso(), json.dumps(params), f"KMeans k={k} silhouette={sil:.3f}"))

    centroids_original_scale = scaler.inverse_transform(km.cluster_centers_)
    # inverse log1p for freq/monetary centroids for readability
    for _, row in cluster_stats.iterrows():
        label = int(row["cluster"])
        centroid = km.cluster_centers_[label].tolist()
        # centroids in log space: convert back for display
        conn.execute("""INSERT INTO customer_clusters(run_id,cluster_label,size,avg_recency,avg_frequency,avg_monetary,centroid_json)
                        VALUES (?,?,?,?,?,?,?)""",
                     (run_id, label, int(row["size"]), float(row["avg_recency"]), float(row["avg_frequency"]), float(row["avg_monetary"]), json.dumps(centroid)))
    for _, row in rfm.iterrows():
        conn.execute("""INSERT INTO cluster_assignments(run_id,customer_id,cluster_label,distance_to_centroid,rfm_r,rfm_f,rfm_m)
                        VALUES (?,?,?,?,?,?,?)""",
                     (run_id, str(row["customer_id"]), int(row["cluster"]), float(row["distance"]), float(row["recency"]), float(row["frequency"]), float(row["monetary"])))
    conn.commit()

    # Save PCA coords for quick dashboard load (optional)
    pca_path = pathlib.Path(__file__).parent.parent / "data" / "processed" / "pca_coords.csv"
    pca_path.parent.mkdir(parents=True, exist_ok=True)
    rfm[["customer_id","cluster","pca_x","pca_y"]].to_csv(pca_path, index=False)

    conn.close()
    print(f"Run {run_id} stored. Cluster sizes:\n{cluster_stats.to_string(index=False)}")
    return run_id, sil

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=str, default=None)
    ap.add_argument("--k", type=int, default=None)
    ap.add_argument("--auto-k", action="store_true")
    args = ap.parse_args()
    run_clustering(db_path=args.db, k=args.k, auto_k=args.auto_k)
