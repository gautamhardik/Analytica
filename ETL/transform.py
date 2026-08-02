"""
Transformation Module
Contains all business transformation, cleaning, enrichment,
pre-aggregation, surrogate key lookups, and fact building functions.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import polars as pl
from ETL.config import get_logger
from ETL.exceptions import TransformationError

logger = get_logger("Transform")

def transform_geography(geolocation: pl.DataFrame) -> pl.DataFrame:
    """
    Transform raw geolocation into dim_geography.

    Grain:
        One row per zip_code_prefix.

    Inputs:
        geolocation: Polars DataFrame of raw geolocation coordinates.

    Returns:
        Polars DataFrame with zip_code_prefix, city_name, state_code, latitude, longitude.
    """
    try:
        logger.info("Transforming dim_geography...")
        return (
            geolocation
            .rename({
                "geolocation_zip_code_prefix": "zip_code_prefix",
                "geolocation_city": "city_name",
                "geolocation_state": "state_code",
                "geolocation_lat": "latitude",
                "geolocation_lng": "longitude"
            })
            .group_by("zip_code_prefix")
            .agg([
                pl.col("city_name").first(),
                pl.col("state_code").first(),
                pl.col("latitude").mean(),
                pl.col("longitude").mean()
            ])
        )
    except Exception as e:
        raise TransformationError(f"Failed in transform_geography: {e}")

def transform_customer(customers: pl.DataFrame, dim_geography_mysql: pl.DataFrame) -> pl.DataFrame:
    """
    Transform raw customers and map geography_key from MySQL.

    Grain:
        One row per customer_id.
    """
    try:
        logger.info("Transforming dim_customer...")
        return (
            customers
            .join(
                dim_geography_mysql,
                left_on="customer_zip_code_prefix",
                right_on="zip_code_prefix",
                how="left"
            )
            .select([
                pl.col("customer_id"),
                pl.col("customer_unique_id"),
                pl.col("geography_key")
            ])
        )
    except Exception as e:
        raise TransformationError(f"Failed in transform_customer: {e}")

def transform_seller(sellers: pl.DataFrame, dim_geography_mysql: pl.DataFrame) -> pl.DataFrame:
    """
    Transform raw sellers and map geography_key from MySQL.

    Grain:
        One row per seller_id.
    """
    try:
        logger.info("Transforming dim_seller...")
        return (
            sellers
            .join(
                dim_geography_mysql,
                left_on="seller_zip_code_prefix",
                right_on="zip_code_prefix",
                how="left"
            )
            .select([
                pl.col("seller_id"),
                pl.col("geography_key")
            ])
        )
    except Exception as e:
        raise TransformationError(f"Failed in transform_seller: {e}")

def transform_product(products: pl.DataFrame, categories: pl.DataFrame) -> pl.DataFrame:
    """
    Transform raw products, enrich with category translation, and compute product_volume_cm3.

    Grain:
        One row per product_id.
    """
    try:
        logger.info("Transforming dim_product...")
        return (
            products
            .join(categories, on="product_category_name", how="left")
            .with_columns(
                (pl.col("product_length_cm") * pl.col("product_height_cm") * pl.col("product_width_cm"))
                .alias("product_volume_cm3")
            )
            .select([
                pl.col("product_id"),
                pl.col("product_category_name"),
                pl.col("product_category_name_english"),
                pl.col("product_name_lenght").alias("product_name_length"),
                pl.col("product_description_lenght").alias("product_description_length"),
                pl.col("product_photos_qty"),
                pl.col("product_weight_g"),
                pl.col("product_length_cm"),
                pl.col("product_height_cm"),
                pl.col("product_width_cm"),
                pl.col("product_volume_cm3")
            ])
        )
    except Exception as e:
        raise TransformationError(f"Failed in transform_product: {e}")

def transform_date(orders: pl.DataFrame) -> pl.DataFrame:
    """
    Generate continuous calendar date dimension spanning min purchase date and max delivery date.

    Grain:
        One row per calendar date (full_date).
    """
    try:
        logger.info("Transforming dim_date...")
        orders_dt = orders.with_columns([
            pl.col("order_purchase_timestamp").str.strptime(pl.Datetime, "%Y-%m-%d %H:%M:%S", strict=False),
            pl.col("order_estimated_delivery_date").str.strptime(pl.Datetime, "%Y-%m-%d %H:%M:%S", strict=False)
        ])
        
        min_date = orders_dt["order_purchase_timestamp"].min().date()
        max_date = orders_dt["order_estimated_delivery_date"].max().date()
        
        dates_series = pl.date_range(min_date, max_date, "1d", eager=True).alias("full_date")
        
        return (
            pl.DataFrame([dates_series])
            .with_columns([
                pl.col("full_date").dt.strftime("%Y%m%d").cast(pl.Int32).alias("date_key"),
                pl.col("full_date").dt.day().cast(pl.UInt8).alias("day_number"),
                pl.col("full_date").dt.strftime("%A").alias("day_name"),
                pl.col("full_date").dt.week().cast(pl.UInt8).alias("week_number"),
                pl.col("full_date").dt.month().cast(pl.UInt8).alias("month_number"),
                pl.col("full_date").dt.strftime("%B").alias("month_name"),
                pl.col("full_date").dt.strftime("%b").alias("month_short_name"),
                pl.col("full_date").dt.strftime("%Y-%m").alias("month_year"),
                pl.col("full_date").dt.quarter().cast(pl.UInt8).alias("quarter_number"),
                ("Q" + pl.col("full_date").dt.quarter().cast(pl.String)).alias("quarter_name"),
                (pl.col("full_date").dt.year().cast(pl.String) + "Q" + pl.col("full_date").dt.quarter().cast(pl.String)).alias("quarter_label"),
                pl.col("full_date").dt.year().cast(pl.UInt16).alias("year_number"),
                pl.col("full_date").dt.ordinal_day().cast(pl.UInt16).alias("day_of_year"),
                (pl.col("full_date").dt.weekday() >= 6).alias("is_weekend"),
                (pl.col("full_date").dt.day() == 1).alias("is_month_start")
            ])
            .with_columns(
                (pl.col("full_date").dt.month() != (pl.col("full_date") + pl.duration(days=1)).dt.month()).alias("is_month_end")
            )
        )
    except Exception as e:
        raise TransformationError(f"Failed in transform_date: {e}")

def aggregate_payments(order_payments: pl.DataFrame) -> pl.DataFrame:
    """Pre-aggregate payments to order_id level to prevent grain fan-out."""
    try:
        logger.info("Aggregating order_payments...")
        return (
            order_payments
            .group_by("order_id")
            .agg([
                pl.col("payment_value").sum().round(2).alias("payment_total"),
                pl.col("payment_installments").max().alias("payment_installments_max"),
                pl.col("payment_type").first().alias("primary_payment_type"),
                pl.col("payment_sequential").count().alias("payment_count")
            ])
        )
    except Exception as e:
        raise TransformationError(f"Failed in aggregate_payments: {e}")

def aggregate_reviews(order_reviews: pl.DataFrame) -> pl.DataFrame:
    """Pre-aggregate reviews to order_id level to handle multiple reviews gracefully."""
    try:
        logger.info("Aggregating order_reviews...")
        return (
            order_reviews
            .group_by("order_id")
            .agg([
                pl.col("review_score").mean().round(2).alias("review_score_avg"),
                pl.col("review_comment_message").count().alias("review_comment_count")
            ])
        )
    except Exception as e:
        raise TransformationError(f"Failed in aggregate_reviews: {e}")

def lookup_customer(df: pl.DataFrame, dim_cust: pl.DataFrame) -> pl.DataFrame:
    """Lookup Customer surrogate key from dim_customer."""
    return df.join(dim_cust.select(["customer_id", "customer_key"]), on="customer_id", how="left")

def lookup_seller(df: pl.DataFrame, dim_sell: pl.DataFrame) -> pl.DataFrame:
    """Lookup Seller surrogate key from dim_seller."""
    return df.join(dim_sell.select(["seller_id", "seller_key"]), on="seller_id", how="left")

def lookup_product(df: pl.DataFrame, dim_prod: pl.DataFrame) -> pl.DataFrame:
    """Lookup Product surrogate key from dim_product."""
    return df.join(dim_prod.select(["product_id", "product_key"]), on="product_id", how="left")

def lookup_date(df: pl.DataFrame, dim_date: pl.DataFrame) -> pl.DataFrame:
    """Parse purchase date and lookup Date surrogate key from dim_date."""
    df = df.with_columns(
        pl.col("order_purchase_timestamp")
        .str.strptime(pl.Datetime, "%Y-%m-%d %H:%M:%S", strict=False)
        .dt.strftime("%Y%m%d")
        .cast(pl.Int32)
        .alias("purchase_date_key")
    )
    return df.join(
        dim_date.select(["date_key"]).rename({"date_key": "purchase_date_key"}),
        on="purchase_date_key",
        how="left"
    )

def calculate_measures(df: pl.DataFrame) -> pl.DataFrame:
    """Calculate derived financial measures."""
    return df.with_columns([
        pl.lit(1).cast(pl.UInt16).alias("quantity"),
        pl.col("price").cast(pl.Float64).round(2),
        pl.col("freight_value").cast(pl.Float64).round(2),
        (pl.col("price") + pl.col("freight_value")).round(2).alias("total_sales_amount")
    ])

def transform_fact_sales(
    order_items: pl.DataFrame,
    orders: pl.DataFrame,
    payments_agg: pl.DataFrame,
    reviews_agg: pl.DataFrame,
    dim_cust: pl.DataFrame,
    dim_sell: pl.DataFrame,
    dim_prod: pl.DataFrame,
    dim_date: pl.DataFrame
) -> pl.DataFrame:
    """
    Build the central fact_sales table.

    Grain:
        One row per order item (order_id, order_item_id).
    """
    try:
        logger.info("Transforming fact_sales table...")
        
        # 1. Join transaction tables
        unified_tx = (
            order_items
            .join(orders, on="order_id", how="inner")
            .join(payments_agg, on="order_id", how="left")
            .join(reviews_agg, on="order_id", how="left")
        )
        
        # 2. Perform atomic dimension lookups
        unified_tx = lookup_customer(unified_tx, dim_cust)
        unified_tx = lookup_seller(unified_tx, dim_sell)
        unified_tx = lookup_product(unified_tx, dim_prod)
        unified_tx = lookup_date(unified_tx, dim_date)
        
        # 3. Calculate measures
        unified_tx = calculate_measures(unified_tx)
        
        # 4. Select final columns
        return unified_tx.select([
            pl.col("order_id"),
            pl.col("order_item_id").cast(pl.UInt8),
            pl.col("customer_key").cast(pl.Int32),
            pl.col("product_key").cast(pl.Int32),
            pl.col("seller_key").cast(pl.Int32),
            pl.col("purchase_date_key").cast(pl.Int32),
            pl.col("quantity").cast(pl.UInt16),
            pl.col("price").cast(pl.Float64),
            pl.col("freight_value").cast(pl.Float64),
            pl.col("total_sales_amount").cast(pl.Float64)
        ])
    except Exception as e:
        raise TransformationError(f"Failed in transform_fact_sales: {e}")
