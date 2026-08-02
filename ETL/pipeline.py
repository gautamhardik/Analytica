"""
Pipeline Orchestrator Module
Master entrypoint to execute the end-to-end Data Warehouse ETL pipeline.
Usage: python -m ETL.pipeline OR python ETL/pipeline.py
"""

import sys
import time
from pathlib import Path

# Fix sys.path for direct execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ETL.config import get_db_engine, get_logger, REPORT_DIR
from ETL.exceptions import ETLError
from ETL.metrics import MetricsCollector
from ETL.extract import (
    load_all_sources, fetch_dimension_keys
)
from ETL.transform import (
    transform_geography, transform_customer, transform_seller,
    transform_product, transform_date, aggregate_payments,
    aggregate_reviews, transform_fact_sales
)
from ETL.validation import (
    validate_schema, validate_row_counts, validate_grain_uniqueness,
    validate_null_keys, validate_business_rules, validate_revenue_reconciliation,
    validate_mysql_referential_integrity
)
from ETL.load import reset_warehouse_reverse, load_dataframe_to_mysql

logger = get_logger("Pipeline")

def run_geography(sources: dict, engine, collector: MetricsCollector):
    """Execute Geography Dimension ETL Stage."""
    t0 = time.time()
    logger.info("--- STAGE 1: Geography Dimension ETL ---")
    geolocation = sources["geolocation"]
    dim_geo = transform_geography(geolocation)
    validate_grain_uniqueness(dim_geo, ["zip_code_prefix"], "dim_geography")
    loaded = load_dataframe_to_mysql(dim_geo, "dim_geography", engine)
    collector.record_stage("Geography Dimension", geolocation.height, loaded, time.time() - t0, 0, "PASS")
    return fetch_dimension_keys("dim_geography", engine)

def run_customer(sources: dict, dim_geo_mysql, engine, collector: MetricsCollector):
    """Execute Customer Dimension ETL Stage."""
    t0 = time.time()
    logger.info("--- STAGE 2: Customer Dimension ETL ---")
    customers = sources["customers"]
    dim_cust = transform_customer(customers, dim_geo_mysql)
    validate_row_counts(dim_cust, customers.height, "dim_customer")
    validate_grain_uniqueness(dim_cust, ["customer_id"], "dim_customer")
    warns = validate_null_keys(dim_cust, ["geography_key"], "dim_customer", allow_orphans=True)
    loaded = load_dataframe_to_mysql(dim_cust, "dim_customer", engine)
    collector.record_stage("Customer Dimension", customers.height, loaded, time.time() - t0, warns, "PASS")

def run_seller(sources: dict, dim_geo_mysql, engine, collector: MetricsCollector):
    """Execute Seller Dimension ETL Stage."""
    t0 = time.time()
    logger.info("--- STAGE 3: Seller Dimension ETL ---")
    sellers = sources["sellers"]
    dim_seller = transform_seller(sellers, dim_geo_mysql)
    validate_row_counts(dim_seller, sellers.height, "dim_seller")
    validate_grain_uniqueness(dim_seller, ["seller_id"], "dim_seller")
    warns = validate_null_keys(dim_seller, ["geography_key"], "dim_seller", allow_orphans=True)
    loaded = load_dataframe_to_mysql(dim_seller, "dim_seller", engine)
    collector.record_stage("Seller Dimension", sellers.height, loaded, time.time() - t0, warns, "PASS")

def run_product(sources: dict, engine, collector: MetricsCollector):
    """Execute Product Dimension ETL Stage."""
    t0 = time.time()
    logger.info("--- STAGE 4: Product Dimension ETL ---")
    products = sources["products"]
    categories = sources["categories"]
    dim_prod = transform_product(products, categories)
    validate_row_counts(dim_prod, products.height, "dim_product")
    validate_grain_uniqueness(dim_prod, ["product_id"], "dim_product")
    warns = validate_null_keys(dim_prod, ["product_category_name_english"], "dim_product", allow_orphans=True)
    loaded = load_dataframe_to_mysql(dim_prod, "dim_product", engine)
    collector.record_stage("Product Dimension", products.height, loaded, time.time() - t0, warns, "PASS")

def run_date(sources: dict, engine, collector: MetricsCollector):
    """Execute Date Dimension ETL Stage."""
    t0 = time.time()
    logger.info("--- STAGE 5: Date Dimension ETL ---")
    orders = sources["orders"]
    dim_date = transform_date(orders)
    validate_grain_uniqueness(dim_date, ["date_key"], "dim_date")
    loaded = load_dataframe_to_mysql(dim_date, "dim_date", engine)
    collector.record_stage("Date Dimension", dim_date.height, loaded, time.time() - t0, 0, "PASS")

def run_fact(sources: dict, engine, collector: MetricsCollector):
    """Execute Fact Sales ETL Stage."""
    t0 = time.time()
    logger.info("--- STAGE 6: Fact Sales ETL ---")
    
    # Fetch dimension surrogate keys
    dim_cust = fetch_dimension_keys("dim_customer", engine)
    dim_sell = fetch_dimension_keys("dim_seller", engine)
    dim_prod = fetch_dimension_keys("dim_product", engine)
    dim_date = fetch_dimension_keys("dim_date", engine)
    
    order_items = sources["order_items"]
    orders = sources["orders"]
    order_payments = sources["order_payments"]
    order_reviews = sources["order_reviews"]
    
    payments_agg = aggregate_payments(order_payments)
    reviews_agg = aggregate_reviews(order_reviews)
    
    fact_sales = transform_fact_sales(
        order_items, orders, payments_agg, reviews_agg,
        dim_cust, dim_sell, dim_prod, dim_date
    )
    
    # Validations
    validate_schema(fact_sales, ["order_id", "order_item_id", "customer_key", "seller_key", "product_key", "purchase_date_key", "quantity", "price", "freight_value", "total_sales_amount"], "fact_sales")
    validate_row_counts(fact_sales, order_items.height, "fact_sales")
    validate_grain_uniqueness(fact_sales, ["order_id", "order_item_id"], "fact_sales")
    validate_null_keys(fact_sales, ["customer_key", "seller_key", "product_key", "purchase_date_key"], "fact_sales")
    validate_business_rules(fact_sales)
    validate_revenue_reconciliation(order_items, fact_sales)
    
    loaded = load_dataframe_to_mysql(fact_sales, "fact_sales", engine)
    collector.record_stage("Fact Sales Table", order_items.height, loaded, time.time() - t0, 0, "PASS")

def run_pipeline():
    """Execute the complete Data Warehouse ETL pipeline end-to-end."""
    collector = MetricsCollector()
    collector.start_pipeline()
    logger.info("Starting Brazilian E-Commerce Data Warehouse ETL Pipeline...")
    
    try:
        engine = get_db_engine()
        
        # Reset Warehouse
        reset_warehouse_reverse(engine)
        
        # Batch Extract All Sources
        sources = load_all_sources()
        
        # Modular Stage Runs
        dim_geo_mysql = run_geography(sources, engine, collector)
        run_customer(sources, dim_geo_mysql, engine, collector)
        run_seller(sources, dim_geo_mysql, engine, collector)
        run_product(sources, engine, collector)
        run_date(sources, engine, collector)
        run_fact(sources, engine, collector)
        
        # Final Database Referential Integrity Validation
        validate_mysql_referential_integrity(engine)
        
        collector.end_pipeline()
        
        # Output Summary Dashboard
        print("\n" + "="*60)
        print("      PIPELINE EXECUTION SUMMARY DASHBOARD      ")
        print("="*60)
        summary_df = collector.generate_summary_dataframe()
        print(summary_df.to_string(index=False))
        
        # Export metrics
        metrics_csv = REPORT_DIR / "etl_pipeline_metrics.csv"
        collector.export_csv(metrics_csv)
        logger.info(f"Exported pipeline execution report to '{metrics_csv}'.")
        
        print("\n" + "="*60)
        print(f"PIPELINE COMPLETED SUCCESSFULLY IN {collector.get_total_duration():.2f} SECONDS")
        print("WAREHOUSE STATUS: READY FOR POWER BI")
        print("="*60 + "\n")
        
    except ETLError as e:
        logger.critical(f"Pipeline Execution Terminated due to ETL Failure: {e}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Unhandled Exception in ETL Pipeline: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_pipeline()
