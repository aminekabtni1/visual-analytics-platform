"""
Load & clean raw CSV into normalized SQLite DB.
Cleaning decisions documented in cleaning_report.json and printed.

Usage: python data/load_data.py [--raw data/raw/online_retail.csv] [--db data/market_basket.db]
"""
import argparse, json, pathlib, re
import pandas as pd
import numpy as np

import sys
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from database.db import init_db, get_connection

ROOT = pathlib.Path(__file__).parent
DEFAULT_RAW = ROOT / "raw" / "online_retail.csv"
DEFAULT_DB = ROOT.parent / "data" / "market_basket.db"  # actually data/market_basket.db
DEFAULT_REPORT = ROOT / "processed" / "cleaning_report.json"

def parse_date(s):
    for fmt in ("%m/%d/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M:%S", "%Y-%m-%d"):
        try:
            return pd.to_datetime(s, format=fmt)
        except: continue
    return pd.to_datetime(s, errors="coerce")

def load_and_clean(raw_path: pathlib.Path, db_path: pathlib.Path):
    df = pd.read_csv(raw_path, dtype={"InvoiceNo": str, "StockCode": str, "CustomerID": str}, encoding="utf-8", on_bad_lines="skip")
    raw_rows = len(df)
    decisions = []
    counts = {"raw_rows": raw_rows}

    # 1. Strip whitespace
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).str.strip().replace({"nan": np.nan, "None": np.nan, "": np.nan})

    # 2. Remove exact duplicate rows
    before = len(df)
    df = df.drop_duplicates()
    decisions.append(f"Removed {before - len(df)} exact duplicate rows (identical InvoiceNo+StockCode+Quantity+price).")
    counts["dupes_removed"] = before - len(df)

    # 3. Cancelled orders: InvoiceNo starting with C and Quantity <0
    before = len(df)
    cancelled_mask = df["InvoiceNo"].astype(str).str.startswith("C")
    # Keep a count but remove them from main transactional analysis
    n_cancelled = cancelled_mask.sum()
    df = df[~cancelled_mask].copy()
    decisions.append(f"Removed {n_cancelled} rows with cancelled InvoiceNo (prefix 'C'). Cancelled orders are excluded from mining to avoid negative quantities distorting basket analysis; they could be analysed separately for return-pattern mining.")
    counts["cancelled_removed"] = int(n_cancelled)

    # 4. Null CustomerID — drop for customer-level mining but keep transaction if needed?
    # For this project we drop rows with null CustomerID since RFM & clustering require customer identity.
    before = len(df)
    n_null_cust = df["CustomerID"].isna().sum()
    df = df.dropna(subset=["CustomerID"])
    decisions.append(f"Removed {before - len(df)} rows with null/empty CustomerID ({n_null_cust} nulls). These rows cannot be attributed to a customer for RFM/clustering; they are excluded. Alternative would be to assign an 'UNKNOWN' customer, but that would pollute cluster statistics.")
    counts["null_customer_removed"] = int(n_null_cust)

    # 5. StockCode cleansing: remove non-product codes (e.g. AMAZON, POST, DOT, gift)
    before = len(df)
    non_product_pattern = re.compile(r"^(AMAZON|POST|DOT|gift|GIFT|M|DCGS)", re.I)
    # Keep only codes matching mostly digits/letters 5-ish; also StockCode like '85123A' is valid (UCI has it). So we filter known junk.
    junk_mask = df["StockCode"].astype(str).str.match(non_product_pattern, na=False)
    df = df[~junk_mask]
    decisions.append(f"Removed {before - len(df)} rows with non-product StockCodes (AMAZON/POST/DOT etc.) — these are postage/adjustment line items, not real products, and would inflate frequent itemsets with a ubiquitous 'POST' item.")
    counts["junk_stockcode_removed"] = int(before - len(df))

    # 6. Quantity / UnitPrice sanity
    before = len(df)
    bad_qty = (df["Quantity"] <= 0)
    bad_price = (df["UnitPrice"] <= 0)
    df = df[~(bad_qty | bad_price)]
    decisions.append(f"Removed {before - len(df)} rows with Quantity<=0 or UnitPrice<=0 (after canc. removal these are data errors).")
    counts["bad_qty_price_removed"] = int(before - len(df))

    # 7. Parse dates
    df["InvoiceDate_parsed"] = df["InvoiceDate"].apply(parse_date)
    n_bad_dates = df["InvoiceDate_parsed"].isna().sum()
    before = len(df)
    df = df.dropna(subset=["InvoiceDate_parsed"])
    if n_bad_dates:
        decisions.append(f"Removed {n_bad_dates} rows with unparseable InvoiceDate.")
    counts["bad_dates_removed"] = int(n_bad_dates)

    # 8. Deduplicate (InvoiceNo, StockCode) — sum quantities if same product appears twice in one invoice
    before = len(df)
    # Aggregate duplicates: sum quantity, keep first description/price/date/customer/country
    agg = df.groupby(["InvoiceNo","StockCode"], as_index=False).agg(
        Description=("Description","first"),
        Quantity=("Quantity","sum"),
        InvoiceDate=("InvoiceDate","first"),
        InvoiceDate_parsed=("InvoiceDate_parsed","first"),
        UnitPrice=("UnitPrice","first"),
        CustomerID=("CustomerID","first"),
        Country=("Country","first"),
    )
    if len(agg) < before:
        decisions.append(f"Aggregated {before - len(agg)} duplicate (InvoiceNo,StockCode) pairs by summing Quantity (e.g., same product added twice to same basket).")
    df = agg
    counts["deduped_pairs"] = int(before - len(df))
    counts["clean_rows"] = len(df)

    # 9. Derive category: use description heuristics if not present
    # If Description contains keywords -> category, else existing
    def infer_cat(desc):
        d = str(desc).lower()
        if any(k in d for k in ["cup","cake","bowl","heart","frame","ceramic","glass","star"]): return "Home"
        if any(k in d for k in ["mug","lunch bag","tea set","colander","jam"]): return "Kitchen"
        if any(k in d for k in ["toy","teddy","puzzle","doll","spaceboy","jumbo bag"]): return "Toys"
        if any(k in d for k in ["pencil","wrap","card","craft","sticker","notebook"]): return "Stationery"
        if any(k in d for k in ["bag","bunting","hottie","tote"]): return "Bags"
        if any(k in d for k in ["chocolate","biscuit","popcorn","tea","coffee","sugar","milk","cake stand"]): return "Food"
        return "Misc"
    df["Category"] = df["Description"].apply(infer_cat)

    # Stats for report
    counts["n_customers"] = int(df["CustomerID"].nunique())
    counts["n_products"] = int(df["StockCode"].nunique())
    counts["n_transactions"] = int(df["InvoiceNo"].nunique())
    counts["date_min"] = str(df["InvoiceDate_parsed"].min())
    counts["date_max"] = str(df["InvoiceDate_parsed"].max())

    # ── Write to DB ──
    init_db(db_path)
    conn = get_connection(db_path)
    cur = conn.cursor()
    # Clear raw tables (allow re-run)
    cur.execute("DELETE FROM transaction_items")
    cur.execute("DELETE FROM transactions")
    cur.execute("DELETE FROM products")
    cur.execute("DELETE FROM customers")

    # customers
    cust_grp = df.groupby("CustomerID").agg(
        country=("Country","first"),
        first_seen=("InvoiceDate_parsed","min"),
        last_seen=("InvoiceDate_parsed","max"),
    ).reset_index()
    for _, r in cust_grp.iterrows():
        cur.execute("INSERT INTO customers(customer_id,country,first_seen,last_seen) VALUES (?,?,?,?)",
                    (str(r["CustomerID"]), str(r["country"]), str(r["first_seen"]), str(r["last_seen"])))
    # products
    prod_grp = df.groupby("StockCode").agg(Description=("Description","first"), Category=("Category","first"), UnitPrice=("UnitPrice","median")).reset_index()
    for _, r in prod_grp.iterrows():
        cur.execute("INSERT INTO products(product_id,description,category,unit_price) VALUES (?,?,?,?)",
                    (str(r["StockCode"]), str(r["Description"]), str(r["Category"]), float(r["UnitPrice"])))
    # transactions
    tx_grp = df.groupby("InvoiceNo").agg(CustomerID=("CustomerID","first"), InvoiceDate_parsed=("InvoiceDate_parsed","first"), Country=("Country","first")).reset_index()
    for _, r in tx_grp.iterrows():
        cur.execute("INSERT INTO transactions(transaction_id,customer_id,invoice_date,country) VALUES (?,?,?,?)",
                    (str(r["InvoiceNo"]), str(r["CustomerID"]), str(r["InvoiceDate_parsed"]), str(r["Country"])))
    # items
    for _, r in df.iterrows():
        cur.execute("INSERT INTO transaction_items(transaction_id,product_id,quantity,unit_price) VALUES (?,?,?,?)",
                    (str(r["InvoiceNo"]), str(r["StockCode"]), int(r["Quantity"]), float(r["UnitPrice"])))
    conn.commit()
    conn.close()

    report = {"counts": counts, "cleaning_decisions": decisions}
    DEFAULT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_REPORT.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    print(f"\nLoaded into {db_path}")
    return report

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=str, default=str(DEFAULT_RAW))
    ap.add_argument("--db", type=str, default=str(DEFAULT_DB))
    args = ap.parse_args()
    load_and_clean(pathlib.Path(args.raw), pathlib.Path(args.db))
