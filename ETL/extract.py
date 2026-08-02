"""
Data Extraction Module
Responsible solely for extracting raw CSV datasets into Polars DataFrames
and fetching generated dimension surrogate keys from MySQL.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import polars as pl
from ETL.config import RAW_DATA_DIR, get_db_engine, get_logger
from ETL.exceptions import ExtractionError

logger = get_logger("Extract")

def load_orders() -> pl.DataFrame:
    """Extract raw orders dataset."""
    try:
        logger.info("Extracting raw orders dataset...")
        return pl.read_csv(RAW_DATA_DIR / "olist_orders_dataset.csv")
    except Exception as e:
        raise ExtractionError(f"Failed to extract orders: {e}")

def load_order_items() -> pl.DataFrame:
    """Extract raw order items dataset."""
    try:
        logger.info("Extracting raw order_items dataset...")
        return pl.read_csv(RAW_DATA_DIR / "olist_order_items_dataset.csv")
    except Exception as e:
        raise ExtractionError(f"Failed to extract order_items: {e}")

def load_payments() -> pl.DataFrame:
    """Extract raw order payments dataset."""
    try:
        logger.info("Extracting raw order_payments dataset...")
        return pl.read_csv(RAW_DATA_DIR / "olist_order_payments_dataset.csv")
    except Exception as e:
        raise ExtractionError(f"Failed to extract order_payments: {e}")

def load_reviews() -> pl.DataFrame:
    """Extract raw order reviews dataset."""
    try:
        logger.info("Extracting raw order_reviews dataset...")
        return pl.read_csv(RAW_DATA_DIR / "olist_order_reviews_dataset.csv")
    except Exception as e:
        raise ExtractionError(f"Failed to extract order_reviews: {e}")

def load_customers() -> pl.DataFrame:
    """Extract raw customers dataset."""
    try:
        logger.info("Extracting raw customers dataset...")
        return pl.read_csv(RAW_DATA_DIR / "olist_customers_dataset.csv")
    except Exception as e:
        raise ExtractionError(f"Failed to extract customers: {e}")

def load_products() -> pl.DataFrame:
    """Extract raw products dataset."""
    try:
        logger.info("Extracting raw products dataset...")
        return pl.read_csv(RAW_DATA_DIR / "olist_products_dataset.csv")
    except Exception as e:
        raise ExtractionError(f"Failed to extract products: {e}")

def load_sellers() -> pl.DataFrame:
    """Extract raw sellers dataset."""
    try:
        logger.info("Extracting raw sellers dataset...")
        return pl.read_csv(RAW_DATA_DIR / "olist_sellers_dataset.csv")
    except Exception as e:
        raise ExtractionError(f"Failed to extract sellers: {e}")

def load_geolocation() -> pl.DataFrame:
    """Extract raw geolocation dataset."""
    try:
        logger.info("Extracting raw geolocation dataset...")
        return pl.read_csv(RAW_DATA_DIR / "olist_geolocation_dataset.csv")
    except Exception as e:
        raise ExtractionError(f"Failed to extract geolocation: {e}")

def load_categories() -> pl.DataFrame:
    """Extract raw product category translations dataset."""
    try:
        logger.info("Extracting raw category translation dataset...")
        return pl.read_csv(RAW_DATA_DIR / "product_category_name_translation.csv")
    except Exception as e:
        raise ExtractionError(f"Failed to extract category translation: {e}")

def load_all_sources() -> dict:
    """Extract all raw transaction and entity CSV datasets into a single dictionary."""
    logger.info("Batch extracting all raw source datasets...")
    return {
        "orders": load_orders(),
        "order_items": load_order_items(),
        "order_payments": load_payments(),
        "order_reviews": load_reviews(),
        "customers": load_customers(),
        "products": load_products(),
        "sellers": load_sellers(),
        "geolocation": load_geolocation(),
        "categories": load_categories()
    }

def fetch_dimension_keys(table_name: str, engine=None) -> pl.DataFrame:
    """Fetch surrogate keys and natural keys from a loaded MySQL dimension table."""
    if engine is None:
        engine = get_db_engine()
        
    try:
        logger.info(f"Fetching dimension lookup keys from MySQL table '{table_name}'...")
        query = f"SELECT * FROM {table_name};"
        with engine.connect() as conn:
            return pl.read_database(query, conn)
    except Exception as e:
        raise ExtractionError(f"Failed to fetch dimension keys from '{table_name}': {e}")
