"""Load + validate the Olist backbone from a manual download.

Accepts either a zip (any *.zip in data/raw/) or the extracted CSVs directly in
data/raw/. Validates against schema.OLIST_TABLES, parses datetimes, and reports
row counts, date coverage, and the structured<->unstructured join health that our
whole thesis depends on (share of orders that carry review text).

Run:  python -m show_its_work.data.olist --validate
"""
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

import pandas as pd

from .schema import OLIST_TABLES

RAW = Path(__file__).resolve().parents[3] / "data" / "raw"


def _ensure_extracted(raw: Path = RAW) -> None:
    """If CSVs aren't present but a zip is, extract it in place."""
    have_csv = any((raw / f"{t}.csv").exists() for t in OLIST_TABLES)
    if have_csv:
        return
    zips = sorted(raw.glob("*.zip"))
    if not zips:
        return
    with zipfile.ZipFile(zips[0]) as zf:
        zf.extractall(raw)
    print(f"  extracted {zips[0].name}")


def load(raw: Path = RAW) -> dict[str, pd.DataFrame]:
    """Load all 9 tables as DataFrames with datetimes parsed. Raises if missing."""
    _ensure_extracted(raw)
    tables: dict[str, pd.DataFrame] = {}
    missing = []
    for stem, spec in OLIST_TABLES.items():
        fp = raw / f"{stem}.csv"
        if not fp.exists():
            missing.append(stem)
            continue
        df = pd.read_csv(fp)
        for col in spec["dates"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        tables[stem] = df
    if missing:
        raise FileNotFoundError(
            "Missing Olist tables in data/raw/: "
            + ", ".join(missing)
            + "\n  -> see data/README.md (manual download)."
        )
    return tables


def validate(raw: Path = RAW) -> bool:
    """Human-readable validation report. Returns True if the backbone is usable."""
    print(f"Looking in: {raw}")
    try:
        tables = load(raw)
    except FileNotFoundError as e:
        print("\n[not ready]\n" + str(e))
        return False

    ok = True
    print("\n%-38s %10s  %s" % ("table", "rows", "required cols"))
    print("-" * 72)
    for stem, spec in OLIST_TABLES.items():
        df = tables[stem]
        have = set(df.columns)
        missing_cols = [c for c in spec["required"] if c not in have]
        flag = "OK" if not missing_cols else f"MISSING {missing_cols}"
        if missing_cols:
            ok = False
        print("%-38s %10d  %s" % (stem, len(df), flag))

    # date coverage on the spine
    orders = tables["olist_orders_dataset"]
    lo, hi = orders["order_purchase_timestamp"].min(), orders["order_purchase_timestamp"].max()
    print(f"\norders span: {lo:%Y-%m-%d} -> {hi:%Y-%m-%d}  ({len(orders):,} orders)")

    # the join our whole thesis rests on: orders <-> review text
    reviews = tables["olist_order_reviews_dataset"]
    if "review_comment_message" in reviews.columns:
        with_text = reviews["review_comment_message"].notna().sum()
    else:
        with_text = 0
    orders_reviewed = reviews["order_id"].nunique()
    print(f"reviews: {len(reviews):,}  | orders reviewed: {orders_reviewed:,} "
          f"({orders_reviewed / len(orders):.0%} of orders) | "
          f"with free-text: {with_text:,}")
    print("\n[ready]" if ok else "\n[schema problems — see MISSING above]")
    return ok


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Load/validate the Olist backbone.")
    ap.add_argument("--validate", action="store_true", help="print a validation report")
    args = ap.parse_args(argv)
    if args.validate or True:  # default action is validate
        return 0 if validate() else 1


if __name__ == "__main__":
    sys.exit(main())


def to_orders_fact(tables: dict) -> "pd.DataFrame":
    """Map the 9 real Olist tables into the canonical `orders_fact` schema (synth.COLUMNS)
    so downstream tools are source-agnostic. Order-items are aggregated to order grain."""
    import numpy as np
    o = tables["olist_orders_dataset"].copy()
    items = tables["olist_order_items_dataset"]
    cust = tables["olist_customers_dataset"]
    rev = tables["olist_order_reviews_dataset"]
    prod = tables["olist_products_dataset"]
    tr = tables["product_category_name_translation"]

    # order-grain aggregation of items: revenue + a representative seller/product
    agg = items.groupby("order_id").agg(
        price=("price", "sum"), freight_value=("freight_value", "sum"),
        seller_id=("seller_id", "first"), product_id=("product_id", "first")).reset_index()
    cat = prod.merge(tr, on="product_category_name", how="left")[["product_id", "product_category_name_english"]]
    agg = agg.merge(cat, on="product_id", how="left")
    df = o.merge(agg, on="order_id", how="inner")
    df = df.merge(cust[["customer_id", "customer_unique_id", "customer_state"]], on="customer_id", how="left")
    r1 = rev.sort_values("review_creation_date").groupby("order_id").first().reset_index()
    df = df.merge(r1[["order_id", "review_score", "review_creation_date", "review_comment_message"]],
                  on="order_id", how="left")

    df["promised_days"] = (df["order_estimated_delivery_date"] - df["order_purchase_timestamp"]).dt.days
    df["actual_days"] = (df["order_delivered_customer_date"] - df["order_purchase_timestamp"]).dt.days
    df["on_time"] = df["order_delivered_customer_date"] <= df["order_estimated_delivery_date"]
    out = pd.DataFrame({
        "order_id": df["order_id"], "order_purchase_date": df["order_purchase_timestamp"],
        "order_status": df["order_status"], "seller_id": df["seller_id"],
        "category": df["product_category_name_english"].fillna("unknown"),
        "region": df["customer_state"], "price": df["price"], "freight_value": df["freight_value"],
        "promised_days": df["promised_days"], "actual_days": df["actual_days"],
        "on_time": df["on_time"].fillna(False), "delivered": df["order_status"].eq("delivered"),
        "review_score": df["review_score"], "review_creation_date": df["review_creation_date"],
        "review_text": df["review_comment_message"], "customer_unique_id": df["customer_unique_id"],
    })
    return out.reset_index(drop=True)
