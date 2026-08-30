"""Canonical Olist schema — the expected 9 tables and their key columns.

Used to validate a manual download before anything downstream trusts it. Column
lists are the *required* columns we depend on, not necessarily every column.
"""
from __future__ import annotations

# table stem -> (required columns, datetime columns)
OLIST_TABLES: dict[str, dict] = {
    "olist_customers_dataset": {
        "required": ["customer_id", "customer_unique_id",
                     "customer_zip_code_prefix", "customer_city", "customer_state"],
        "dates": [],
    },
    "olist_geolocation_dataset": {
        "required": ["geolocation_zip_code_prefix", "geolocation_lat",
                     "geolocation_lng", "geolocation_state"],
        "dates": [],
    },
    "olist_order_items_dataset": {
        "required": ["order_id", "order_item_id", "product_id", "seller_id",
                     "shipping_limit_date", "price", "freight_value"],
        "dates": ["shipping_limit_date"],
    },
    "olist_order_payments_dataset": {
        "required": ["order_id", "payment_sequential", "payment_type",
                     "payment_installments", "payment_value"],
        "dates": [],
    },
    "olist_order_reviews_dataset": {
        "required": ["review_id", "order_id", "review_score",
                     "review_creation_date", "review_answer_timestamp"],
        "dates": ["review_creation_date", "review_answer_timestamp"],
    },
    "olist_orders_dataset": {
        "required": ["order_id", "customer_id", "order_status",
                     "order_purchase_timestamp", "order_approved_at",
                     "order_delivered_carrier_date", "order_delivered_customer_date",
                     "order_estimated_delivery_date"],
        "dates": ["order_purchase_timestamp", "order_approved_at",
                  "order_delivered_carrier_date", "order_delivered_customer_date",
                  "order_estimated_delivery_date"],
    },
    "olist_products_dataset": {
        "required": ["product_id", "product_category_name"],
        "dates": [],
    },
    "olist_sellers_dataset": {
        "required": ["seller_id", "seller_zip_code_prefix",
                     "seller_city", "seller_state"],
        "dates": [],
    },
    "product_category_name_translation": {
        "required": ["product_category_name", "product_category_name_english"],
        "dates": [],
    },
}

# South-region states used by the row-level entitlement demo (personas.yaml)
SOUTH_STATES = {"SP", "PR", "SC", "RS"}
