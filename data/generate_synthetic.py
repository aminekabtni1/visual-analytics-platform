"""
Synthetic retail dataset generator — mimics UCI Online Retail structure
but runs offline without downloading. Produces ~12k transactions over 12 months.

Covers realistic: cancellations, null CustomerIDs, duplicate lines, varied
basket sizes, country skew (UK-heavy like UCI), and StockCode categories.

Run: python data/generate_synthetic.py
Outputs:
  data/raw/online_retail.csv   (raw UCI-like)
  data/processed/cleaning_report.json
"""
import pathlib, random, json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

ROOT = pathlib.Path(__file__).parent
RAW = ROOT / "raw" / "online_retail.csv"
REPORT = ROOT / "processed" / "cleaning_report.json"
ROOT.mkdir(parents=True, exist_ok=True)
(ROOT/"raw").mkdir(exist_ok=True)
(ROOT/"processed").mkdir(exist_ok=True)

random.seed(42)
np.random.seed(42)

# Product catalogue — 55 products across 6 categories
CATALOGUE = [
    # Home & Decor
    ("85048","17609 PINK SPOTTY CUP","Home"),("85049","WHITE HANGING HEART T-LIGHT","Home"),
    ("85050","RED RETRO SPOT CAKE STAND","Home"),("85051","SET OF 3 CAKE TINS","Home"),
    ("85052","CERAMIC BOWL WITH LID","Home"),("85053","GLASS STAR FROSTED T-LIGHT","Home"),
    ("85054","WOODEN FRAME ANTIQUE WHITE","Home"),("85055","JINGLE BELLS CERAMIC BOWL","Home"),
    # Kitchen
    ("21001","VINTAGE TEA SET","Kitchen"),("21002","ENAMEL COLANDER SET","Kitchen"),
    ("21003","JAM MAKING SET PRINTED","Kitchen"),("21004","PACK OF 6 BIRDY GIFT TAGS","Kitchen"),
    ("21005","SPOTTY MUG SET OF 3","Kitchen"),("21006","LUNCH BAG RED RETROSPOT","Kitchen"),
    ("21007","LUNCH BAG WOODLAND","Kitchen"),("21008","FELTCRAFT PRINCESS KIT","Kitchen"),
    # Toys / Gifts
    ("30001","WOODEN TOY TRAIN SET","Toys"),("30002","DOLLY GIRL LUNCH BOX","Toys"),
    ("30003","SPACEBOY LUNCH BOX","Toys"),("30004","PLUSH TEDDY BEAR","Toys"),
    ("30005","MINI PUZZLE SET","Toys"),("30006","JUMBO BAG RED RETROSPOT","Toys"),
    ("30007","FELTCRAFT MINI KIT","Toys"),
    # Stationery
    ("41001","SET OF 12 COLOURED PENCILS","Stationery"),("41002","WRAP PINK POLKADOT","Stationery"),
    ("41003","GREETING CARD SET","Stationery"),("41004","CRAFT PAPER PACK","Stationery"),
    ("41005","STICKER SHEET PACK","Stationery"),("41006","NOTEBOOK A5 LINED","Stationery"),
    # Accessories / Bags
    ("52001","STRAWBERRY CHARLOTTE BAG","Bags"),("52002","RETRO SPOT TOTE","Bags"),
    ("52003","RED WOOLLY HOTTIE","Bags"),("52004","PARTY BUNTING","Bags"),
    ("52005","JUMBO BAG WOODLAND","Bags"),("52006","LUNCH BAG 3D HEARTS","Bags"),
    # Snacks / Food (for snack rule mining)
    ("60001","CHOCOLATE BISCUIT MIX","Food"),("60002","TEA INFUSER SET","Food"),
    ("60003","POPCORN HOLDER","Food"),("60004","SUGAR JAM BOWL","Food"),
    ("60005","BISCUIT TIN VINTAGE","Food"),("60006","COFFEE MUG LARGE","Food"),
    ("60007","MILK BOTTLE VINTAGE","Food"),("60008","CAKE STAND VICTORIAN","Food"),
    # Extra
    ("71001","HAND WARMER UNION JACK","Misc"),("71002","ALARM CLOCK BAKELIKE RED","Misc"),
    ("71003","CHARLOTTE BAG SUKI DESIGN","Misc"),("71004","REGENCY CAKESTAND 3 TIER","Misc"),
]

# Associated basket affinity rules to embed strong association signals
AFFINITIES = [
    (["85048","85050"], 0.35),  # cup + cake stand
    (["21006","21007"], 0.30),  # lunch bags together
    (["60001","60006"], 0.28),  # biscuit + mug
    (["30002","30003"], 0.25),  # lunch boxes together
    (["41002","41003"], 0.22),  # wrap + card
]

# Map product->price
PRICE_MAP = {code: round(random.uniform(1.5, 18.5),2) for code,_,_ in CATALOGUE}
# Fix some
PRICE_MAP["85048"]= 2.95; PRICE_MAP["85050"]= 8.50; PRICE_MAP["60001"]= 1.95

COUNTRIES = ["United Kingdom"]*78 + ["France"]*8 + ["Germany"]*6 + ["Netherlands"]*3 + ["Australia"]*2 + ["USA"]*2 + ["Belgium"]

START = datetime(2010,12,1)
END   = datetime(2011,11,30)

def rand_date():
    delta = (END - START).days
    d = START + timedelta(days=random.randint(0,delta), hours=random.randint(9,17), minutes=random.randint(0,59))
    # weekday pattern: fewer Sundays
    if d.weekday()==6 and random.random()<0.6:
        d += timedelta(days=1)
    return d

CUSTOMERS = [str(10000+i) for i in range(1, 800)]  # 799 customers

rows=[]
txn_id_counter = 500000

# Inject some duplicate StockCodes for same invoice (to test dedup)
for _ in range(12000):
    txn_id_counter += 1
    inv = str(txn_id_counter)
    is_cancelled = random.random() < 0.025
    if is_cancelled:
        inv = "C" + inv
    customer = random.choice(CUSTOMERS) if random.random() > 0.04 else ""  # 4% null
    country = random.choice(COUNTRIES)
    date = rand_date()
    # basket size: mostly 1-8 items
    n_items = int(np.random.choice([1,2,3,4,5,6,7,8,10,15], p=[0.18,0.22,0.18,0.13,0.09,0.06,0.05,0.04,0.03,0.02]))
    # pick products
    chosen = random.sample(CATALOGUE, k=min(n_items, len(CATALOGUE)))
    # maybe inject affinity bundle
    if random.random() < 0.18:
        bundle, _ = random.choice(AFFINITIES)
        for bcode in bundle:
            if bcode not in [c[0] for c in chosen]:
                # replace random
                chosen[random.randint(0,len(chosen)-1)] = next(x for x in CATALOGUE if x[0]==bcode)
    for code, desc, cat in chosen:
        qty = int(np.random.choice([1,1,1,2,2,3,4,6,12], p=[0.25,0.15,0.1,0.15,0.1,0.08,0.07,0.06,0.04]))
        if is_cancelled:
            qty = -qty
        price = PRICE_MAP[code]
        # occasional price jitter
        if random.random()<0.05:
            price = round(price * random.uniform(0.9,1.1),2)
        rows.append([inv, code, desc, qty, date.strftime("%m/%d/%Y %H:%M"), price, customer, country])

# Inject some exact duplicate rows (to test dedup handling)
dupes = random.sample(rows, 120)
rows.extend(dupes)

df = pd.DataFrame(rows, columns=["InvoiceNo","StockCode","Description","Quantity","InvoiceDate","UnitPrice","CustomerID","Country"])
# shuffle
df = df.sample(frac=1, random_state=42).reset_index(drop=True)
df.to_csv(RAW, index=False)
print(f"Wrote {len(df)} rows to {RAW}")
print(df.head(5).to_string())

# Build placeholder cleaning report (actual cleaning happens in load_data.py)
report = {"raw_rows": len(df), "note": "Run python data/load_data.py to clean and load into DB"}
REPORT.write_text(json.dumps(report, indent=2))
print(f"Cleaning report placeholder -> {REPORT}")
