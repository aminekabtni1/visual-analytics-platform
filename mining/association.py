"""
Association Rule Mining — FP-Growth via mlxtend.
Writes FrequentItemsets + AssociationRules into mining_runs tables.

Usage:
  python -m mining.association --min-support 0.02 --min-confidence 0.3
  python -m mining.association --min-support 0.015 --min-threshold 0.25 --metric lift
"""
import argparse, json, pathlib, sys
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from database.db import get_connection, init_db
from mining.utils import new_run_id, now_iso, jdump

try:
    from mlxtend.frequent_patterns import fpgrowth, association_rules
    HAS_MLXTEND = True
except ImportError:
    HAS_MLXTEND = False

def mine_association(db_path=None, min_support=0.02, min_confidence=0.3, metric="confidence", min_threshold=None):
    if not HAS_MLXTEND:
        raise ImportError("mlxtend not installed. pip install mlxtend")
    if min_threshold is None:
        min_threshold = min_confidence
    init_db(db_path)
    conn = get_connection(db_path)
    # Build basket matrix: rows=transactions, cols=products, 1/0
    q = """
    SELECT transaction_id, product_id FROM transaction_items
    """
    df = pd.read_sql_query(q, conn)
    if df.empty:
        raise ValueError("No transaction_items found")
    # basket
    basket = pd.crosstab(df["transaction_id"], df["product_id"]).astype(bool)
    # For small support thresholds, filter to products appearing at least a few times to keep matrix small
    # but keep all 47 products (small)
    print(f"Basket shape: {basket.shape}  (txns x products)")

    frequent = fpgrowth(basket, min_support=min_support, use_colnames=True)
    frequent["itemset_str"] = frequent["itemsets"].apply(lambda s: sorted(list(s)))
    print(f"Frequent itemsets: {len(frequent)}  (min_support={min_support})")
    if frequent.empty:
        print("No frequent itemsets found — try lowering min_support")
        conn.close()
        return None

    rules = association_rules(frequent, metric=metric, min_threshold=min_threshold)
    print(f"Rules: {len(rules)}  (metric={metric} >= {min_threshold})")
    # Sort by lift descending
    if not rules.empty:
        rules = rules.sort_values("lift", ascending=False).reset_index(drop=True)

    run_id = new_run_id()
    params = {"min_support": min_support, "metric": metric, "min_threshold": min_threshold, "min_confidence": min_confidence}
    conn.execute("INSERT INTO mining_runs(run_id,run_type,created_at,params_json,notes) VALUES (?,?,?,?,?)",
                 (run_id, "association", now_iso(), json.dumps(params), f"FP-Growth: {len(frequent)} itemsets, {len(rules)} rules"))
    # frequent_itemsets
    for _, row in frequent.iterrows():
        itemset = jdump(row["itemset_str"])
        conn.execute("INSERT INTO frequent_itemsets(run_id,itemset,itemset_size,support) VALUES (?,?,?,?)",
                     (run_id, itemset, len(row["itemset_str"]), float(row["support"])))
    # rules
    for _, row in rules.iterrows():
        ant = jdump(sorted(list(row["antecedents"])))
        cons = jdump(sorted(list(row["consequents"])))
        conn.execute("""INSERT INTO association_rules(run_id,antecedent,consequent,support,confidence,lift,leverage,conviction)
                        VALUES (?,?,?,?,?,?,?,?)""",
                     (run_id, ant, cons, float(row["support"]), float(row["confidence"]), float(row["lift"]),
                      float(row.get("leverage", 0)), float(row.get("conviction", 0)) if row.get("conviction") != float("inf") else 0))
    conn.commit()
    conn.close()
    print(f"Run {run_id} stored.")
    # also print top 5 rules
    if not rules.empty:
        print(rules[["antecedents","consequents","support","confidence","lift"]].head(10).to_string())
    return run_id

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=str, default=None)
    ap.add_argument("--min-support", type=float, default=0.02)
    ap.add_argument("--min-confidence", type=float, default=0.3)
    ap.add_argument("--metric", type=str, default="confidence")
    ap.add_argument("--min-threshold", type=float, default=None)
    args = ap.parse_args()
    mine_association(db_path=args.db, min_support=args.min_support, min_confidence=args.min_confidence, metric=args.metric, min_threshold=args.min_threshold)
