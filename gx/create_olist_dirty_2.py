"""Create gx/data/olist_dirty_2.db — a "more broken" copy of olist.db.

Same bug TYPES as olist_dirty (deleted customers, truncated seller_ids,
NULL categories) but with HIGHER counts. Used to test that the agents
generalize beyond the specific row counts they were demoed against —
they should detect the new (larger) failures and report the new counts
in the postmortem.

Counts (vs olist_dirty in parens):
  • olist_customers       — 15,000 deleted     (vs 7,955)
  • olist_order_items     — 12,000 truncated   (vs 5,632)
  • olist_products        —  2,500 NULL cats   (vs 988)

Run:
    python gx/create_olist_dirty_2.py
"""
import shutil
import sqlite3
from pathlib import Path

import random

GX_DIR = Path(__file__).parent
DATA = GX_DIR / "data"
SOURCE = DATA / "olist.db"
TARGET = DATA / "olist_dirty_2.db"

assert SOURCE.exists(), f"Missing {SOURCE} — scp from studio-a:~/code/datahub-static-assets/datasets/olist-ecommerce/"

print(f"Copying {SOURCE} → {TARGET}")
shutil.copy(SOURCE, TARGET)

conn = sqlite3.connect(str(TARGET))
cur = conn.cursor()

# Use a different seed than the kit (which uses 42) so we hit different rows
rng = random.Random(2026)


def all_ids(table: str, col: str) -> list:
    return [r[0] for r in cur.execute(f"SELECT {col} FROM {table}").fetchall()]


# ─── Issue 1: delete 15,000 customers (kit deleted ~7,955) ─────────────────
cust_ids = all_ids("olist_customers", "customer_id")
print(f"olist_customers: {len(cust_ids)} rows before")
victims = rng.sample(cust_ids, 15_000)
placeholders = ",".join(["?"] * len(victims))
cur.execute(f"DELETE FROM olist_customers WHERE customer_id IN ({placeholders})", victims)
print(f"olist_customers: deleted 15,000 → expect {len(cust_ids) - 15_000} remaining")


# ─── Issue 2: truncate 12,000 seller_ids in order_items (kit truncated ~5,632) ─
item_rowids = [r[0] for r in cur.execute("SELECT rowid FROM olist_order_items").fetchall()]
print(f"olist_order_items: {len(item_rowids)} rows before")
victims = rng.sample(item_rowids, 12_000)
for vid in victims:
    cur.execute(
        "UPDATE olist_order_items "
        "SET seller_id = SUBSTR(seller_id, 1, LENGTH(seller_id)-1) "
        "WHERE rowid = ?",
        (vid,),
    )
print("olist_order_items: truncated 12,000 seller_ids by 1 char")


# ─── Issue 3: NULL 2,500 product categories (kit nulled ~988) ──────────────
prod_ids = all_ids("olist_products", "product_id")
print(f"olist_products: {len(prod_ids)} rows before")
victims = rng.sample(prod_ids, 2_500)
placeholders = ",".join(["?"] * len(victims))
cur.execute(
    f"UPDATE olist_products SET product_category_name = NULL WHERE product_id IN ({placeholders})",
    victims,
)
print("olist_products: nulled 2,500 product_category_name values")


conn.commit()

# ─── Verify the bugs are present ────────────────────────────────────────────
print()
print("─── Verification ───")
cur.execute("SELECT COUNT(*) FROM olist_customers")
print(f"  olist_customers row count:                  {cur.fetchone()[0]:>7,}  (expect 84,441)")
cur.execute("SELECT COUNT(*) FROM olist_order_items WHERE LENGTH(seller_id) != 32")
print(f"  olist_order_items truncated seller_ids:     {cur.fetchone()[0]:>7,}  (expect 12,000)")
cur.execute("SELECT COUNT(*) FROM olist_products WHERE product_category_name IS NULL")
print(f"  olist_products NULL category_name:          {cur.fetchone()[0]:>7,}  (expect 2,500)")
cur.execute("SELECT COUNT(*) FROM olist_order_items")
print(f"  olist_order_items total rows:               {cur.fetchone()[0]:>7,}  (unchanged)")
cur.execute("SELECT COUNT(*) FROM olist_products")
print(f"  olist_products total rows:                  {cur.fetchone()[0]:>7,}  (unchanged)")

conn.close()
print(f"\n✅ {TARGET}")
