"""
Loading & Transaction Management Module
Responsible solely for database resets, transactional table deletion,
and multi-strategy loading of DataFrames into MySQL tables.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import polars as pl
from sqlalchemy import text, Engine
from ETL.config import get_logger
from ETL.exceptions import LoadError

logger = get_logger("Load")

def reset_warehouse_reverse(engine: Engine) -> None:
    """Safely wipe data warehouse tables in reverse dependency order."""
    try:
        logger.info("Wiping warehouse data in reverse dependency order...")
        tables_in_reverse = [
            "fact_sales",
            "dim_customer",
            "dim_seller",
            "dim_product",
            "dim_geography",
            "dim_date"
        ]
        with engine.begin() as conn:
            for t in tables_in_reverse:
                conn.execute(text(f"DELETE FROM {t};"))
        logger.info("Warehouse reset complete.")
    except Exception as e:
        raise LoadError(f"Failed to reset warehouse: {e}")

def delete_table(table_name: str, engine: Engine) -> None:
    """Delete all records from a single table within a transaction."""
    try:
        logger.info(f"Deleting existing records from MySQL table '{table_name}'...")
        with engine.begin() as conn:
            conn.execute(text(f"DELETE FROM {table_name};"))
    except Exception as e:
        raise LoadError(f"Failed to delete records from {table_name}: {e}")

def append_dataframe(df: pl.DataFrame, table_name: str, engine: Engine) -> int:
    """Append Polars DataFrame records into MySQL table."""
    try:
        logger.info(f"Appending {df.height:,} records to '{table_name}'...")
        df_pandas = df.to_pandas()
        with engine.begin() as conn:
            df_pandas.to_sql(table_name, conn, if_exists="append", index=False)
        return len(df_pandas)
    except Exception as e:
        raise LoadError(f"Failed to append records to {table_name}: {e}")

def replace_dataframe(df: pl.DataFrame, table_name: str, engine: Engine) -> int:
    """Replace entire table contents with new DataFrame records."""
    try:
        logger.info(f"Replacing contents of '{table_name}' with {df.height:,} records...")
        df_pandas = df.to_pandas()
        with engine.begin() as conn:
            conn.execute(text(f"DELETE FROM {table_name};"))
            df_pandas.to_sql(table_name, conn, if_exists="append", index=False)
        return len(df_pandas)
    except Exception as e:
        raise LoadError(f"Failed to replace records in {table_name}: {e}")

def load_dataframe_to_mysql(df: pl.DataFrame, table_name: str, engine: Engine, delete_first: bool = True) -> int:
    """Load a Polars DataFrame into a MySQL table."""
    if delete_first:
        return replace_dataframe(df, table_name, engine)
    else:
        return append_dataframe(df, table_name, engine)
