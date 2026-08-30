# Data

## 1. Backbone — Olist Brazilian E-Commerce (manual download)

1. Go to https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
2. Click **Download** (top right). You get `archive.zip` (~45 MB).
3. Drop it in **this folder** as `data/raw/olist.zip` (rename it), OR just extract the 9 CSVs into `data/raw/`.
4. From the repo root, validate:
   ```bash
   pip install -e .
   python -m show_its_work.data.olist --validate
   ```

Expected 9 tables (canonical Olist schema):
`olist_customers_dataset`, `olist_geolocation_dataset`, `olist_order_items_dataset`,
`olist_order_payments_dataset`, `olist_order_reviews_dataset`, `olist_orders_dataset`,
`olist_products_dataset`, `olist_sellers_dataset`, `product_category_name_translation`.

Why Olist: 100k orders (2016–2018) with **review text linked to orders by `order_id`** — a genuine
structured↔unstructured join. Gotchas: reviews are Portuguese; company names anonymised.

## 2. Injected anomalies (generated, not downloaded)
`python -m show_its_work.data.build` degrades a seller's delivery times, shifts a category price,
and **plants a decoy** — recording every planted cause as the answer key in `data/synthetic/ground_truth.json`.

## 3. Synthetic evidence trail
Support tickets / CRM notes / release logs referencing the planted causes, seeded with real
support-ticket vocabulary so it doesn't read as AI slop. Written to `data/synthetic/evidence/`.

> **Honesty:** anomalies are injected *for evaluation*. We never imply synthetic = real-world validation.
