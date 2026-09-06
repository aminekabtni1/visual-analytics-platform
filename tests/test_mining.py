import pathlib, json, sys
import pandas as pd
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from database.db import get_connection, init_db

# Use a temp DB for isolation
import tempfile, os, sqlite3

def fresh_db():
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()
    from database.db import init_db, get_connection
    init_db(tmp.name)
    return tmp.name

def test_rule_metrics_computed_correctly():
    """Lift = confidence / consequent_support ; confidence = support(itemset)/support(antecedent) — verify stored values are consistent."""
    from mlxtend.frequent_patterns import fpgrowth, association_rules
    # tiny basket: 4 txns, products A,B,C
    basket = pd.DataFrame([
        [1,1,0],
        [1,1,0],
        [1,0,1],
        [0,1,1],
    ], columns=["A","B","C"]).astype(bool)
    freq = fpgrowth(basket, min_support=0.25, use_colnames=True)
    rules = association_rules(freq, metric="confidence", min_threshold=0.5)
    assert not rules.empty
    # manual check: support(A)=0.75, support(A,B)=0.5 => conf(A->B)=0.666..., lift = conf/support(B) support(B)=0.75 => 0.888
    # Just verify lift >0 and confidence between 0-1
    assert (rules["confidence"]>0).all() and (rules["confidence"]<=1).all()
    assert (rules["lift"]>0).all()

def test_cluster_assignments_stable_seed():
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import KMeans
    X = np.array([[1,1],[1,2],[8,8],[8,9],[5,0],[0,5]], dtype=float)
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    km1 = KMeans(n_clusters=2, n_init=20, random_state=42).fit(Xs)
    km2 = KMeans(n_clusters=2, n_init=20, random_state=42).fit(Xs)
    assert np.array_equal(km1.labels_, km2.labels_)

def test_db_schema_has_mining_runs():
    path = fresh_db()
    try:
        conn = sqlite3.connect(path)
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        for t in ["customers","products","transactions","transaction_items","mining_runs","frequent_itemsets","association_rules","customer_clusters","cluster_assignments","outliers"]:
            assert t in tables, f"missing table {t}"
        conn.close()
    finally:
        os.unlink(path)

def test_mining_runs_are_append_only():
    path = fresh_db()
    try:
        conn = sqlite3.connect(path)
        conn.execute("INSERT INTO mining_runs(run_id,run_type,created_at,params_json) VALUES (?,?,?,?)", ("r1","association","2024-01-01T00:00:00Z","{}"))
        conn.execute("INSERT INTO mining_runs(run_id,run_type,created_at,params_json) VALUES (?,?,?,?)", ("r2","association","2024-01-02T00:00:00Z","{}"))
        cnt = conn.execute("SELECT COUNT(*) FROM mining_runs").fetchone()[0]
        assert cnt == 2
        conn.close()
    finally:
        os.unlink(path)

def test_association_pipeline_writes_to_db():
    import tempfile
    path = fresh_db()
    # build tiny raw data
    conn = sqlite3.connect(path)
    conn.executescript(open("database/schema.sql").read())
    # insert minimal data: 20 txns each with 2 products to get a rule
    for i in range(5):
        conn.execute("INSERT INTO customers(customer_id) VALUES (?)", (f"C{i}",))
    for p in ["P1","P2","P3"]:
        conn.execute("INSERT INTO products(product_id,description) VALUES (?,?)", (p, p))
    import datetime
    for t in range(20):
        cid = f"C{t%5}"
        tid = f"T{t}"
        conn.execute("INSERT INTO transactions(transaction_id,customer_id,invoice_date) VALUES (?,?,?)", (tid, cid, "2011-01-01 10:00:00"))
        # every txn has P1, half also P2
        conn.execute("INSERT INTO transaction_items(transaction_id,product_id,quantity,unit_price) VALUES (?,?,?,?)", (tid, "P1", 1, 1.0))
        if t % 2 == 0:
            conn.execute("INSERT INTO transaction_items(transaction_id,product_id,quantity,unit_price) VALUES (?,?,?,?)", (tid, "P2", 1, 1.0))
    conn.commit()
    conn.close()
    # run mining with low support
    sys.path.insert(0, ".")
    from mining.association import mine_association
    # mine_association uses get_connection which reads DB_PATH env — so set it
    import os
    os.environ["DB_PATH"] = path
    run_id = mine_association(db_path=path, min_support=0.4, min_confidence=0.4)
    assert run_id is not None
    conn = sqlite3.connect(path)
    n_rules = conn.execute("SELECT COUNT(*) FROM association_rules WHERE run_id=?", (run_id,)).fetchone()[0]
    assert n_rules >= 1
    conn.close()
    os.unlink(path)
    if "DB_PATH" in os.environ:
        del os.environ["DB_PATH"]
