"""Auto-bootstrap DB on fresh clone (Streamlit Cloud). If DB is missing or empty, regenerate synthetic data + load + mine."""
import pathlib, sys
import sqlite3

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from database.db import get_db_path, get_connection, init_db

def is_db_ready() -> bool:
    p = get_db_path()
    if not p.exists():
        return False
    try:
        conn = get_connection()
        # check tables exist and have data
        tx = conn.execute("SELECT COUNT(*) as c FROM transactions").fetchone()["c"]
        mining = conn.execute("SELECT COUNT(*) as c FROM mining_runs").fetchone()["c"]
        conn.close()
        return tx > 100 and mining >= 3
    except Exception:
        return False

def bootstrap():
    if is_db_ready():
        return False  # no bootstrap needed
    print("Bootstrap: DB missing or empty — regenerating synthetic data + running mining pipelines...", flush=True)
    try:
        # Use subprocess to avoid circular imports and ensure clean env
        import subprocess
        py = sys.executable
        # 1. Generate synthetic (offline, no download needed)
        subprocess.run([py, str(ROOT / "data" / "generate_synthetic.py")], check=False)
        # 2. Load into DB
        subprocess.run([py, str(ROOT / "data" / "load_data.py")], check=False)
        # 3. Mine
        subprocess.run([py, "-m", "mining.association", "--min-support", "0.015", "--min-confidence", "0.25"], check=False)
        subprocess.run([py, "-m", "mining.clustering", "--k", "4"], check=False)
        subprocess.run([py, "-m", "mining.outliers", "--contamination", "0.05"], check=False)
        # 4. Evals
        subprocess.run([py, str(ROOT / "evals" / "generate_eval.py")], check=False)
        print("Bootstrap: done.", flush=True)
        return True
    except Exception as e:
        print(f"Bootstrap failed: {e}", flush=True)
        return False
