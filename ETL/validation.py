"""
Validation Module
Contains reusable data quality checks, schema assertions, date sequence checks,
revenue reconciliation, and database referential integrity test suites.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import polars as pl
from sqlalchemy import text, Engine
from ETL.config import get_logger
from ETL.exceptions import ValidationError

logger = get_logger("Validation")

def validate_schema(df: pl.DataFrame, expected_columns: list, dataset_name: str) -> None:
    """Validate DataFrame schema, ensuring all required columns exist."""
    missing_cols = [c for c in expected_columns if c not in df.columns]
    if missing_cols:
        msg = f"Schema validation failed for {dataset_name}! Missing columns: {missing_cols}"
        logger.error(msg)
        raise ValidationError(msg)
    logger.info(f"Schema validation passed for {dataset_name}.")

def validate_row_counts(df: pl.DataFrame, expected_count: int, dataset_name: str) -> None:
    """Validate that DataFrame height equals expected row count."""
    if df.height != expected_count:
        msg = f"Row count validation failed for {dataset_name}! Expected {expected_count}, got {df.height}"
        logger.error(msg)
        raise ValidationError(msg)
    logger.info(f"Row count validation passed for {dataset_name} ({df.height:,} rows).")

def validate_grain_uniqueness(df: pl.DataFrame, grain_cols: list, dataset_name: str) -> None:
    """Assert zero duplicate keys exist for the specified grain columns."""
    dup_count = df.select(grain_cols).is_duplicated().sum()
    if dup_count > 0:
        msg = f"Grain uniqueness validation failed for {dataset_name}! Found {dup_count} duplicate keys on {grain_cols}."
        logger.error(msg)
        raise ValidationError(msg)
    logger.info(f"Grain uniqueness validation passed for {dataset_name} on {grain_cols}.")

def validate_null_keys(df: pl.DataFrame, key_cols: list, dataset_name: str, allow_orphans: bool = False) -> int:
    """Analyze and validate NULL foreign key occurrences. Returns total orphan count."""
    total_orphans = 0
    for col in key_cols:
        null_count = df.filter(pl.col(col).is_null()).height
        total_orphans += null_count
        if null_count > 0:
            msg = f"Found {null_count:,} NULL/orphan keys in '{col}' for {dataset_name}."
            if allow_orphans:
                logger.warning(msg)
            else:
                logger.error(msg)
                raise ValidationError(msg)
        else:
            logger.info(f"Key completeness passed for '{col}' in {dataset_name} (0 nulls).")
    return total_orphans

def validate_business_rules(df: pl.DataFrame) -> None:
    """Assert non-negative monetary values and valid quantities."""
    logger.info("Validating business rules...")
    if df.filter(pl.col("price") < 0).height > 0:
        raise ValidationError("Negative price values detected!")
    if df.filter(pl.col("freight_value") < 0).height > 0:
        raise ValidationError("Negative freight values detected!")
    if df.filter(pl.col("total_sales_amount") < 0).height > 0:
        raise ValidationError("Negative total sales amount detected!")
    if df.filter(pl.col("quantity") <= 0).height > 0:
        raise ValidationError("Invalid quantity values detected!")
    logger.info("Business rule validation passed cleanly.")

def validate_revenue_reconciliation(order_items_df: pl.DataFrame, fact_sales_df: pl.DataFrame) -> None:
    """Reconcile raw price sum vs fact total sales amount."""
    logger.info("Executing revenue reconciliation validation...")
    raw_item_revenue = round(order_items_df["price"].sum(), 2)
    raw_freight = round(order_items_df["freight_value"].sum(), 2)
    fact_revenue = round(fact_sales_df["price"].sum(), 2)
    fact_freight = round(fact_sales_df["freight_value"].sum(), 2)
    
    diff_rev = abs(raw_item_revenue - fact_revenue)
    diff_freight = abs(raw_freight - fact_freight)
    
    if diff_rev > 0.01 or diff_freight > 0.01:
        msg = f"Revenue reconciliation failed! Raw items: ${raw_item_revenue:,}, Fact: ${fact_revenue:,}"
        logger.error(msg)
        raise ValidationError(msg)
        
    logger.info(f"Revenue reconciliation passed: ${fact_revenue:,.2f} item revenue matched.")

def validate_mysql_referential_integrity(engine: Engine) -> dict:
    """Query MySQL database to verify referential integrity across all fact foreign keys."""
    logger.info("Executing MySQL database referential integrity checks...")
    results = {}
    with engine.connect() as conn:
        results["customer"] = conn.execute(text(
            "SELECT COUNT(*) FROM fact_sales f LEFT JOIN dim_customer c ON f.customer_key = c.customer_key WHERE c.customer_key IS NULL;"
        )).scalar()
        
        results["seller"] = conn.execute(text(
            "SELECT COUNT(*) FROM fact_sales f LEFT JOIN dim_seller s ON f.seller_key = s.seller_key WHERE s.seller_key IS NULL;"
        )).scalar()
        
        results["product"] = conn.execute(text(
            "SELECT COUNT(*) FROM fact_sales p LEFT JOIN dim_product pr ON p.product_key = pr.product_key WHERE pr.product_key IS NULL;"
        )).scalar()
        
        results["date"] = conn.execute(text(
            "SELECT COUNT(*) FROM fact_sales f LEFT JOIN dim_date d ON f.purchase_date_key = d.date_key WHERE d.date_key IS NULL;"
        )).scalar()

    for fk, orphans in results.items():
        if orphans > 0:
            msg = f"Referential Integrity FAIL: {orphans} orphan {fk} keys in fact_sales!"
            logger.error(msg)
            raise ValidationError(msg)
        else:
            logger.info(f"Referential Integrity PASS: 0 orphan {fk} keys.")
            
    return results
